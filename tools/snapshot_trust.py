#!/usr/bin/env python3
"""Classify how far a live GQ5012BF1 snapshot can be trusted, per data class.

Why this exists
---------------
The `gq5012bf1-live-stock-20260831-113332` snapshot was captured on a device
running KernelSU with an active property-spoofing module. It reports
`ro.build.version.sdk=36` / Android 16 while its own `ro.build.fingerprint`
and the actual stock firmware both say 15, and it reports
`ro.product.*_for_attestation` as Pixel 9 Pro / caiman / google while the real
stock `vendor/build.prop` leaves those properties empty.

That does not make the snapshot worthless. Bus bindings, loaded modules, DRM
and input topology, power-supply nodes and camera enumeration are not targets
of an integrity-spoofing module, and for those questions a live capture beats
any static analysis. What it does mean is that a single global "source of
truth" ranking is wrong: trust has to be assigned per data class.

    hardware topology   live snapshot > stock firmware > DTB/inference
    build identity      stock firmware > stock images  > live properties
    security identity   TrustKernel hardware experiments
                                          > stock firmware > live properties

Usage
-----
    python3 tools/snapshot_trust.py <snapshot-dir> [<snapshot-dir> ...]
        [--stock-root .work/gq5012bf1/stock/partitions] [--check]

`--check` exits non-zero when a snapshot is contaminated but carries no
adjacent TRUST.md marker recording that fact, so an unreviewed capture cannot
quietly become evidence.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

# Indicators that the runtime was modified. Presence of any of these means the
# property namespace cannot be trusted for identity or version questions.
ROOT_INDICATORS = [
    ("kernelsu",        r"\bkernelsu\b"),
    ("sukisu",          r"\bsukisu\b"),
    ("magisk",          r"\bmagisk\b"),
    ("apatch",          r"\bapatch\b"),
    ("zygisk",          r"\bzygisk\b"),
    ("lsposed",         r"\blsposed\b"),
    ("shamiko",         r"\bshamiko\b"),
    ("susfs",           r"\bsusfs\b"),
    ("tricky store",    r"\btricky[_ -]?store\b"),
    ("playintegrityfix", r"\bplay[_ -]?integrity"),
]

# Property classes and how much the snapshot may be trusted for each.
TRUSTED_CLASSES = """\
/sys and /proc hardware topology     bound I2C/SPI drivers      loaded modules
DRM and display topology             input devices              power supplies
device nodes                         running services           camera nodes
sensor topology                      partition/block layout     LED class devices
"""

UNTRUSTED_CLASSES = """\
ro.build.version.*                   ro.build.fingerprint (when inconsistent)
ro.product.*_for_attestation         ro.product.* identity overrides
persist.* namespace                  anything a Play Integrity module rewrites
"""


def read_all(snapshot: str):
    """Return {filename: text} for the snapshot's text captures."""
    blobs = {}
    if not os.path.isdir(snapshot):
        return blobs
    for name in sorted(os.listdir(snapshot)):
        path = os.path.join(snapshot, name)
        if not os.path.isfile(path) or not name.endswith(".txt"):
            continue
        try:
            blobs[name] = open(path, errors="ignore").read()
        except OSError:
            continue
    return blobs


def prop(text, key):
    match = re.search(r"^\[" + re.escape(key) + r"\]:\s*\[(.*)\]\s*$",
                      text, re.M)
    return match.group(1) if match else None


def stock_prop(stock_root, rel, key):
    path = os.path.join(stock_root, rel)
    if not os.path.exists(path):
        return None
    match = re.search(r"^" + re.escape(key) + r"=(.*)$",
                      open(path, errors="ignore").read(), re.M)
    return match.group(1) if match else None


def is_recovery_snapshot(blobs):
    """A recovery capture runs the OrangeFox ramdisk, not the stock system.

    Its ro.build.version.* legitimately describe the recovery build (Android 14
    sources) while ro.build.fingerprint is inherited from the device, so a
    mismatch there is expected and must not be reported as spoofing.
    """
    joined = "\n".join(blobs.values())
    if re.search(r"orangefox|twrp|\brecovery\b", joined, re.I):
        markers = re.search(r"ro\.twrp\.|orangefox|TWRP", joined, re.I)
        if markers:
            return True
    # Fall back on the absence of a booted framework.
    return "services.txt" not in blobs and "camera-dump.txt" not in blobs


def analyse(snapshot, stock_root):
    blobs = read_all(snapshot)
    findings = []
    recovery = is_recovery_snapshot(blobs)

    for label, pattern in ROOT_INDICATORS:
        for name, text in blobs.items():
            if re.search(pattern, text, re.I):
                # A root module visible in a recovery capture means the boot
                # image / kernel itself is patched, not that recovery userspace
                # is spoofing anything.
                scope = "kernel/boot image is patched" if recovery \
                    else "runtime is modified"
                findings.append(("ROOT", label, f"{name}: {scope}"))
                break

    props = blobs.get("properties.txt", "") + blobs.get("identity.txt", "")
    sdk = prop(props, "ro.build.version.sdk")
    release = prop(props, "ro.build.version.release")
    fingerprint = prop(props, "ro.build.fingerprint")

    if not recovery:
        # A fingerprint encodes its platform version as .../<device>:<release>/...
        if fingerprint and release:
            match = re.search(r":([0-9]+)/", fingerprint)
            if match and match.group(1) != release:
                findings.append((
                    "SPOOF", "version",
                    f"ro.build.version.release={release} but fingerprint says "
                    f"{match.group(1)} ({fingerprint})"))

        if stock_root:
            real_sdk = stock_prop(stock_root, "system/system/build.prop",
                                  "ro.build.version.sdk")
            if real_sdk and sdk and real_sdk != sdk:
                findings.append((
                    "SPOOF", "sdk",
                    f"snapshot ro.build.version.sdk={sdk} but stock firmware "
                    f"system/build.prop says {real_sdk}"))

    for key in ("ro.product.model_for_attestation",
                "ro.product.brand_for_attestation",
                "ro.product.name_for_attestation",
                "ro.product.device_for_attestation"):
        live = prop(props, key)
        if live is None:
            continue
        real = stock_prop(stock_root, "vendor/build.prop", key) if stock_root else None
        if live and (real is not None and real.strip() == ""):
            findings.append((
                "SPOOF", "attestation",
                f"{key}={live} but stock firmware leaves it empty"))

    for match in re.finditer(r"^\[(persist\.lieppos\.[^\]]+)\]:\s*\[(.*)\]",
                             props, re.M):
        findings.append(("NONSTOCK", "property",
                         f"{match.group(1)}={match.group(2)} is not a stock namespace"))

    return findings, blobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshots", nargs="+")
    ap.add_argument("--stock-root", default=None)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    failures = 0
    for snapshot in args.snapshots:
        findings, blobs = analyse(snapshot, args.stock_root)
        name = os.path.basename(os.path.normpath(snapshot))
        kinds = {kind for kind, _label, _detail in findings}
        print("=" * 72)
        print("snapshot: %s" % name)
        print("  captures: %d text files%s"
              % (len(blobs), " (recovery capture)"
                 if is_recovery_snapshot(blobs) else ""))
        if not findings:
            print("  verdict : CLEAN -- usable for all data classes")
            continue
        if kinds == {"ROOT"}:
            print("  verdict : PATCHED BOOT IMAGE -- no property spoofing "
                  "detected; hardware topology fully usable")
            for kind, label, detail in findings:
                print("    [%-8s] %-12s %s" % (kind, label, detail))
            continue

        print("  verdict : CONTAMINATED -- identity/version/attestation "
              "properties are NOT authoritative")
        for kind, label, detail in findings:
            print("    [%-8s] %-12s %s" % (kind, label, detail))
        print()
        print("  still authoritative (hardware topology):")
        for line in TRUSTED_CLASSES.strip().splitlines():
            print("    " + line)
        print("  not authoritative:")
        for line in UNTRUSTED_CLASSES.strip().splitlines():
            print("    " + line)

        marker = os.path.join(snapshot, "TRUST.md")
        if args.check and not os.path.exists(marker):
            print("\n  FAIL: contaminated snapshot has no adjacent TRUST.md "
                  "recording the limitation")
            failures += 1
        elif os.path.exists(marker):
            print("\n  TRUST.md present -- limitation is recorded")

    print("=" * 72)
    if args.check and failures:
        print("FAIL: %d contaminated snapshot(s) lack a TRUST.md marker" % failures)
        return 1
    if args.check:
        print("PASS: every contaminated snapshot is documented")
    return 0


if __name__ == "__main__":
    sys.exit(main())
