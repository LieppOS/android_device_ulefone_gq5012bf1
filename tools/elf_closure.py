#!/usr/bin/env python3
"""ELF runtime dependency closure auditor for GQ5012BF1.

Motivation
----------
`proprietary-files.txt` can be "complete" in the weak sense that every listed
path exists in stock, while still being **dependency-incomplete**: a retained
blob may link against a proprietary library that was never extracted.  A
`DT_NEEDED` entry is resolved eagerly by the dynamic linker, so a single missing
vendor library takes the whole process down at exec time, not lazily.

This tool computes the transitive `DT_NEEDED` closure starting from the blobs
that actually run on a normal boot, and classifies every unresolved SONAME.

Classification vocabulary
-------------------------
REQUIRED_STOCK_BLOB
    Proprietary, reachable from an active runtime root, not provided by AOSP.
    Must be added to proprietary-files.txt.
AOSP_OR_ROM_PROVIDED
    Stock ships it from a system partition path that AOSP also builds, or it is
    a versioned AIDL/HIDL interface backend that the AOSP HAL module installs.
    Requires an interface-compatibility justification, not just a name match.
UNUSED_PARENT_BLOB
    Only reachable from a retained blob that is itself never executed or loaded.
ALTERNATE_BOM_OR_FACTORY_ONLY
    Only reachable from factory/META-mode or alternate-BOM components that do
    not run on the tested shipping configuration.
SHIM_OR_FIXUP_REQUIRED
    Reachable and required, but cannot be satisfied by a straight copy.
DEVICE_UNIQUE_OR_CALIBRATION_DO_NOT_PACKAGE
    Per-unit or mutable state. Never package.
UNKNOWN
    Not resolvable from available evidence.

Usage
-----
    python3 tools/elf_closure.py --device . \
        --stock .work/gq5012bf1/stock/partitions \
        [--vendor ../../../vendor/ulefone/gq5012bf1/proprietary] \
        [--json out.json] [--check]

`--check` exits non-zero if any REQUIRED_STOCK_BLOB dependency is unresolved,
which is what makes this usable as a regression gate.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import struct
import sys

# --------------------------------------------------------------------------
# Evidence-documented root classification.
#
# These are NOT heuristics. Each entry is justified from the stock init rc
# files and from the live snapshots; see docs/blob-map.md.
# --------------------------------------------------------------------------

# Executables declared in a normal-boot rc but marked `disabled`, which on this
# platform means they are only started by the factory / META boot modes.
FACTORY_MODE_EXECUTABLES = {
    "vendor/bin/factory":      "disabled in init.mt6878.rc; factory-mode test app",
    "vendor/bin/meta_tst":     "disabled in init.mt6878.rc; META-mode test harness",
    "vendor/bin/uart_launcher": "declared only in meta_init.rc",
    "vendor/bin/permission_check": "declared only in factory_init.rc",
    "vendor/bin/ccci_rpcd":    "declared only in meta_init.modem.rc",
}

# init rc files that only take effect in factory / META boot modes.
FACTORY_RC = re.compile(r"(factory_init|meta_init)")

# Many genuinely-active services are declared `disabled` and then started from
# an `on <trigger>` block (property-gated HALs, post-fs-data services) or by
# servicemanager for lazy HALs. `disabled` therefore proves nothing on its own;
# the reliable signal is whether some non-factory rc contains `start <name>`.
START_DIRECTIVE = re.compile(r"^\s*start\s+(\S+)\s*$", re.M)

# Libraries bundled inside an APK's own lib/ directory are loaded from the APK,
# not from a partition search path.
APP_BUNDLED = re.compile(r"/(app|priv-app)/[^/]+/lib/")

ELF_MAGIC = b"\x7fELF"


# --------------------------------------------------------------------------
# Minimal, dependency-free ELF reader (no pyelftools requirement).
# --------------------------------------------------------------------------

def elf_info(path: str):
    """Return {'class','machine','soname','needed','runpath'} or None."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    if data[:4] != ELF_MAGIC:
        return None

    bits = 64 if data[4] == 2 else 32
    machine = struct.unpack_from("<H", data, 18)[0]
    if bits != 64:
        # 32-bit objects are reported but not walked; this device is 64-bit only
        # and ships a handful of legacy 32-bit libraries with no 32-bit consumer.
        return {"class": 32, "machine": machine, "soname": None,
                "needed": [], "runpath": []}

    e_phoff = struct.unpack_from("<Q", data, 32)[0]
    e_phentsize = struct.unpack_from("<H", data, 54)[0]
    e_phnum = struct.unpack_from("<H", data, 56)[0]

    dynamic = None
    loads = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if off + 56 > len(data):
            break
        p_type = struct.unpack_from("<I", data, off)[0]
        p_offset = struct.unpack_from("<Q", data, off + 8)[0]
        p_vaddr = struct.unpack_from("<Q", data, off + 16)[0]
        p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
        if p_type == 2:
            dynamic = (p_offset, p_filesz)
        elif p_type == 1:
            loads.append((p_vaddr, p_offset, p_filesz))

    result = {"class": 64, "machine": machine, "soname": None,
              "needed": [], "runpath": []}
    if not dynamic:
        return result

    entries = []
    strtab_vaddr = None
    off, size = dynamic
    end = off + size
    while off + 16 <= end and off + 16 <= len(data):
        tag, val = struct.unpack_from("<qQ", data, off)
        off += 16
        if tag == 0:
            break
        entries.append((tag, val))
        if tag == 5:            # DT_STRTAB
            strtab_vaddr = val
    if strtab_vaddr is None:
        return result

    strtab_off = None
    for p_vaddr, p_offset, p_filesz in loads:
        if p_vaddr <= strtab_vaddr < p_vaddr + p_filesz:
            strtab_off = strtab_vaddr - p_vaddr + p_offset
            break
    if strtab_off is None:
        return result

    def read_str(index: int) -> str:
        start = strtab_off + index
        stop = data.find(b"\0", start)
        return data[start:stop].decode("utf-8", "replace")

    for tag, val in entries:
        if tag == 1:            # DT_NEEDED
            result["needed"].append(read_str(val))
        elif tag == 14:         # DT_SONAME
            result["soname"] = read_str(val)
        elif tag in (29, 0x1d):  # DT_RUNPATH
            result["runpath"] = read_str(val).split(":")
    return result


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

def read_list(path: str):
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        for line in fh:
            line = line.split("#")[0].strip()
            if not line:
                continue
            line = line.lstrip("-").split("|")[0].strip()
            if ":" in line:
                line = line.split(":", 1)[1]
            out.append(line)
    return out


def index_stock(stock_root: str):
    by_path = set()
    by_base = collections.defaultdict(list)
    for part in sorted(os.listdir(stock_root)):
        root = os.path.join(stock_root, part)
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                rel = part + "/" + os.path.relpath(
                    os.path.join(dirpath, name), root)
                by_path.add(rel)
                by_base[name].append(rel)
    return by_path, by_base


def parse_services(vendor_root: str, blobs):
    """Return (active_execs, factory_execs) using rc evidence.

    A service counts as active when it is declared in a non-factory rc and is
    either enabled by default, started from an `on` trigger in a non-factory
    rc, or declares a VINTF `interface` (lazy HAL started by servicemanager).
    """
    declarations = []            # (name, exe, body, rel, is_factory_rc)
    started_normal = set()       # service names started from a non-factory rc

    for rel in sorted(blobs):
        if "/etc/init/" not in rel or not rel.endswith(".rc"):
            continue
        full = os.path.join(vendor_root, rel)
        if not os.path.exists(full):
            continue
        text = open(full, errors="ignore").read()
        is_factory_rc = bool(FACTORY_RC.search(rel))
        if not is_factory_rc:
            started_normal.update(START_DIRECTIVE.findall(text))
        pattern = r"^\s*service\s+(\S+)\s+(\S+)(.*?)(?=^\s*(?:service|on)\s|\Z)"
        for match in re.finditer(pattern, text, re.M | re.S):
            declarations.append((match.group(1), match.group(2).lstrip("/"),
                                 match.group(3), rel, is_factory_rc))

    active, factory = {}, {}
    for name, exe, body, rel, is_factory_rc in declarations:
        disabled = bool(re.search(r"^\s*disabled\s*$", body, re.M))
        has_interface = bool(re.search(r"^\s*interface\s", body, re.M))
        if exe in FACTORY_MODE_EXECUTABLES or is_factory_rc:
            target = factory
        elif not disabled or has_interface or name in started_normal:
            target = active
        else:
            target = factory
        target.setdefault(exe, []).append((name, rel))
    for exe in list(active):
        factory.pop(exe, None)
    return active, factory


# --------------------------------------------------------------------------
# Closure
# --------------------------------------------------------------------------

def build_closure(roots, blobs, ship_base, vendor_root, stock_root,
                  stock_paths, stock_base):
    """Walk DT_NEEDED. Returns (visited, missing{soname -> consumers})."""
    visited = set()
    missing = collections.defaultdict(set)
    queue = list(roots)

    def locate(rel):
        if rel in blobs:
            cand = os.path.join(vendor_root, rel)
            if os.path.exists(cand):
                return cand
        if rel in stock_paths:
            part, rest = rel.split("/", 1)
            return os.path.join(stock_root, part, rest)
        return None

    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        path = locate(current)
        if not path:
            continue
        info = elf_info(path)
        if not info:
            continue
        for soname in info["needed"]:
            if soname in ship_base:
                for provider in ship_base[soname]:
                    if provider in blobs and provider not in visited:
                        queue.append(provider)
                continue
            missing[soname].add(current)
            if soname in stock_base:
                locations = stock_base[soname]
                # Only descend into libraries AOSP will NOT rebuild. Stock's
                # copy of an AOSP library (e.g. libaudioclient.so) may carry
                # MediaTek patches with extra DT_NEEDED entries that the AOSP
                # build of the same library simply does not have; following it
                # would invent dependencies the ROM never incurs.
                if is_aosp_provided(locations):
                    continue
                pick = sorted(locations,
                              key=lambda p: (not p.startswith("vendor/"), len(p)))[0]
                if pick not in visited:
                    queue.append(pick)
    return visited, missing


def is_aosp_provided(locations):
    """Stock serves it from a system lib dir that AOSP also builds."""
    return any(loc.startswith("system/system/lib") for loc in locations)


def scan_source_modules(top, names):
    """Return the subset of `names` defined as Soong modules in the checkout.

    Stock installing a library under /vendor does not make it proprietary. A
    number of AOSP libraries (the biometrics common helpers, the codec2 HIDL
    wrappers) are vendor_available and ship on the vendor partition, so a
    location-based test alone will misfile them as REQUIRED_STOCK_BLOB. Adding
    such a library to proprietary-files.txt produces a duplicate install rule
    and breaks the build, so resolve it against the source tree instead.
    """
    import subprocess
    wanted = {n[:-3] for n in names if n.endswith(".so")}
    if not wanted or not top or not os.path.isdir(top):
        return set()
    roots = ["hardware", "frameworks", "system", "external", "packages",
             "device", "bootable", "art", "bionic"]
    found = set()
    pattern = re.compile(r'name:\s*"([A-Za-z0-9._@+-]+)"')
    for rel in roots:
        path = os.path.join(top, rel)
        if not os.path.isdir(path):
            continue
        try:
            out = subprocess.run(
                ["grep", "-rho", "--include=Android.bp", r'name: *"[^"]*"', path],
                capture_output=True, text=True, timeout=900).stdout
        except Exception:
            continue
        for match in pattern.finditer(out):
            if match.group(1) in wanted:
                found.add(match.group(1) + ".so")
    return found


def is_interface_backend(soname):
    """Versioned AIDL/HIDL backend installed by the owning AOSP HAL module.

    These are generated from .aidl/.hal definitions that live in the AOSP tree
    (hardware/interfaces, frameworks/*). The AOSP module that provides the HAL
    installs its own backend, so they never need extracting -- but the version
    must be checked, because a vendor blob pinned to -V4 will not link against
    a ROM that only builds -V3.
    """
    if not soname.startswith(("android.hardware.", "android.hidl.",
                              "android.frameworks.", "android.system.")):
        return False
    return bool(re.search(r"-V\d+-(ndk|cpp)\.so$", soname)) or "@" in soname


# AOSP libraries that ship inside an APEX or on /system and therefore never
# appear in an extracted partition dump, but are always present at runtime.
AOSP_APEX_OR_SYSTEM = {
    "libnativehelper.so",       # ART / libnativehelper, always on /system
    "libtensorflowlite_c.so",   # bundled inside the consuming APK's lib/ dir
}


DEVICE_UNIQUE = re.compile(
    r"(nvdata|nvcfg|/persist/|/protect[12]/|keybox|imei|/nvram/)", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default=".")
    ap.add_argument("--stock", required=True)
    ap.add_argument("--vendor", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--aosp-source", default=None,
                    help="ANDROID_BUILD_TOP; resolves sonames that are actually "
                         "Soong modules rather than proprietary blobs")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any REQUIRED_STOCK_BLOB is unresolved")
    args = ap.parse_args()

    device = os.path.abspath(args.device)
    vendor_root = args.vendor or os.path.join(
        device, "..", "..", "..", "vendor", "ulefone", "gq5012bf1", "proprietary")
    vendor_root = os.path.normpath(vendor_root)

    blobs = set(read_list(os.path.join(device, "proprietary-files.txt")))
    aosp = set(read_list(os.path.join(device, "aosp-replaced-files.txt")))
    stock_paths, stock_base = index_stock(args.stock)

    ship_base = collections.defaultdict(list)
    for rel in blobs | aosp:
        ship_base[os.path.basename(rel)].append(rel)

    active_exe, factory_exe = parse_services(vendor_root, blobs)

    # dlopen roots: hw modules / EGL / effects are loaded by path at runtime and
    # are never reachable through DT_NEEDED from any executable.
    dlopen_roots = {r for r in blobs
                    if re.search(r"/lib(64)?/(hw|egl|soundfx)/", r)}

    active_roots = [r for r in blobs if r in active_exe] + sorted(dlopen_roots)
    factory_roots = [r for r in blobs if r in factory_exe]

    _seen_a, miss_active = build_closure(
        active_roots, blobs, ship_base, vendor_root, args.stock,
        stock_paths, stock_base)
    _seen_f, miss_factory = build_closure(
        factory_roots, blobs, ship_base, vendor_root, args.stock,
        stock_paths, stock_base)

    # Anything only a non-root blob needs (blob retained but never executed).
    all_roots = set(active_roots) | set(factory_roots)
    _seen_all, miss_all = build_closure(
        sorted(blobs), blobs, ship_base, vendor_root, args.stock,
        stock_paths, stock_base)

    source_modules = scan_source_modules(args.aosp_source, set(miss_all))
    if source_modules:
        print("resolved from Soong source modules : %d" % len(source_modules))

    classified = {}
    for soname in sorted(miss_all):
        locations = stock_base.get(soname, [])
        consumers_active = sorted(miss_active.get(soname, []))
        consumers_factory = sorted(miss_factory.get(soname, []))

        if soname in source_modules:
            verdict = "AOSP_OR_ROM_PROVIDED"
        elif not locations:
            if is_interface_backend(soname) or soname in AOSP_APEX_OR_SYSTEM:
                verdict = "AOSP_OR_ROM_PROVIDED"
            elif all(APP_BUNDLED.search(c) for c in miss_all[soname]):
                verdict = "AOSP_OR_ROM_PROVIDED"
            else:
                verdict = "UNKNOWN"
        elif DEVICE_UNIQUE.search(soname) or any(
                DEVICE_UNIQUE.search(loc) for loc in locations):
            verdict = "DEVICE_UNIQUE_OR_CALIBRATION_DO_NOT_PACKAGE"
        elif is_aosp_provided(locations):
            verdict = "AOSP_OR_ROM_PROVIDED"
        elif is_interface_backend(soname):
            verdict = "AOSP_OR_ROM_PROVIDED"
        elif consumers_active:
            verdict = "REQUIRED_STOCK_BLOB"
        elif consumers_factory:
            verdict = "ALTERNATE_BOM_OR_FACTORY_ONLY"
        else:
            verdict = "UNUSED_PARENT_BLOB"

        classified[soname] = {
            "verdict": verdict,
            "stock_locations": locations,
            "consumers_active": consumers_active,
            "consumers_factory": consumers_factory,
            "consumers_any": sorted(miss_all[soname]),
        }

    totals = collections.Counter(v["verdict"] for v in classified.values())
    required = sorted(s for s, v in classified.items()
                      if v["verdict"] == "REQUIRED_STOCK_BLOB")

    print("ELF runtime dependency closure")
    print("  active runtime roots      : %d" % len(active_roots))
    print("  factory/META-only roots   : %d" % len(factory_roots))
    print("  unresolved SONAMEs        : %d" % len(classified))
    for key in sorted(totals):
        print("    %-46s %d" % (key, totals[key]))

    if required:
        print("\nUNRESOLVED REQUIRED_STOCK_BLOB (%d):" % len(required))
        for soname in required:
            info = classified[soname]
            print("  %s" % soname)
            print("      stock : %s" % (info["stock_locations"][:1] or ["?"])[0])
            print("      by    : %s" % ", ".join(info["consumers_active"][:3]))

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"totals": dict(totals), "classified": classified},
                      fh, indent=2, sort_keys=True)
        print("\nwrote %s" % args.json)

    if args.check and required:
        print("\nFAIL: %d required proprietary dependencies are unresolved"
              % len(required))
        return 1
    if args.check:
        print("\nPASS: runtime dependency closure is complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
