#!/usr/bin/env python3
"""Generate a reviewable proprietary-file candidate list from inventory JSON.

This does not claim redistribution permission and does not blindly select every
stock file. It selects hardware-facing roots and closes their in-partition ELF
DT_NEEDED dependencies. Maintainers must review the result before promoting it
to proprietary-files.txt.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

HARDWARE_TERMS = re.compile(
    r"audio|bluetooth|camera|composer|display|drm|finger|gatekeeper|gnss|gps|"
    r"graphics|gralloc|health|ims|keymint|light|media|microarray|nfc|power|radio|"
    r"ril|sensor|thermal|thermo|tiny|usb|vibrator|wifi|trustkernel|co5300|hynitron",
    re.IGNORECASE,
)
DEVICE_APP_NAMES = re.compile(
    r"M170infisens|YftMiniScreen|YftOutdoorLight|YftRedBlueLight|"
    r"YftSensorCalibration|YftStepRecord|YftBarometer|YftTorch|"
    r"YftSuperScreen|uSmartCamera",
    re.IGNORECASE,
)
CONFIG_PREFIXES = (
    "etc/audio", "etc/bluetooth", "etc/camera", "etc/gnss", "etc/gps",
    "etc/media", "etc/nfc", "etc/power", "etc/sensors", "etc/thermal",
    "etc/usb", "etc/wifi", "etc/permissions", "etc/sysconfig", "etc/firmware",
    "firmware/",
)
CORE_STOCK_FILES = (
    "vendor/etc/fstab.emmc",
    "vendor/etc/fstab.enableswap",
    "vendor/etc/fstab.mt6878",
    "vendor/etc/ueventd.rc",
)
DEVICE_SYSTEM_APPS = (
    "system/system/app/M170infisens/M170infisens.apk",
    "system/system/app/YftMiniScreen/YftMiniScreen.apk",
    "system/system/app/YftOutdoorLightUlefone/YftOutdoorLightUlefone.apk",
    "system/system/app/YftRedBlueLight/YftRedBlueLight.apk",
    "system/system/app/YftSensorCalibration/YftSensorCalibration.apk",
    "system/system/app/YftStepRecord/YftStepRecord.apk",
    "system/system/app/YftBarometer/YftBarometer.apk",
    "system/system/app/YftTorch/YftTorch.apk",
    "system/system/app/YftSuperScreen/YftSuperScreen.apk",
    "system/system/media/resource/Download/uSmartCamera.apk",
)


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def stock_source(root: Path, runtime: str) -> Path | None:
    candidate = root / runtime
    for _ in range(16):
        if candidate.is_file():
            return candidate
        if not candidate.is_symlink():
            return None
        target = Path(os.readlink(candidate))
        candidate = root / target.as_posix().lstrip("/") if target.is_absolute() else candidate.parent / target
    return None


def normalized_runtime_path(value: str) -> str | None:
    value = value.lstrip("-")
    if not value.startswith("/"):
        return None
    parts = value.lstrip("/").split("/", 1)
    if len(parts) != 2 or parts[0] not in {
        "vendor", "odm", "product", "system_ext", "vendor_dlkm", "odm_dlkm"
    }:
        return None
    return value.lstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    metadata = load(args.inventory / "metadata.json")
    stock_root = Path(metadata["inputs"]["stock_root"])
    broad_candidates = set(load(args.inventory / "proprietary-candidates.json"))
    vintf = load(args.inventory / "vintf.json")
    init = load(args.inventory / "init.json")
    elf = load(args.inventory / "elf.json")
    modules = load(args.inventory / "modules.json")
    properties = load(args.inventory / "properties.json")

    reasons: dict[str, set[str]] = defaultdict(set)

    def add(path: str | None, reason: str) -> None:
        if path:
            reasons[path].add(reason)

    for doc in vintf["documents"]:
        if doc["partition"] in {"vendor", "odm"} and "manifest" in doc["path"]:
            add(f"{doc['partition']}/{doc['path']}", "VINTF manifest")

    for doc in init["documents"]:
        if doc["partition"] in {"vendor", "odm"}:
            add(f"{doc['partition']}/{doc['path']}", "init service definition")
    for service in init["services"]:
        if not service["command"]:
            continue
        executable = normalized_runtime_path(service["command"][0])
        # Every real stock vendor/odm init executable is accounted, not only
        # names that happen to contain an obvious hardware keyword. Broken
        # alternate-BOM service paths are deliberately excluded by resolving
        # against the immutable extracted stock tree.
        if executable and stock_source(stock_root, executable):
            add(executable, f"stock init service {service['name']}")

    for item in elf["elfs"]:
        runtime = f"{item['partition']}/{item['path']}"
        path = item["path"]
        if item["partition"] in {"vendor", "odm"} and (
            path.startswith(("bin/hw/", "lib/hw/", "lib64/hw/")) or HARDWARE_TERMS.search(path)
        ):
            add(runtime, "hardware-facing ELF")

    for item in modules["modules"]:
        if item["partition"] in {"vendor_dlkm", "odm_dlkm"}:
            add(f"{item['partition']}/{item['path']}", "DLKM module")
    for item in modules["metadata"]:
        if item["partition"] in {"vendor_dlkm", "odm_dlkm"}:
            add(f"{item['partition']}/{item['path']}", "DLKM module metadata")

    for prop in properties["files"]:
        if prop["partition"] in {"vendor", "odm", "product", "system_ext"}:
            add(f"{prop['partition']}/{prop['path']}", "partition properties")

    # Add hardware configuration and device-specific applications from the
    # broad candidate inventory generated by inventory_device.py.
    for runtime in broad_candidates:
        partition, path = runtime.split("/", 1)
        if partition in {"vendor", "odm"} and path.startswith(CONFIG_PREFIXES):
            if HARDWARE_TERMS.search(path) or path.startswith(("etc/permissions", "etc/sysconfig", "firmware/", "etc/firmware")):
                add(runtime, "hardware configuration")
        if partition in {"product", "system_ext", "vendor"} and path.startswith(("app/", "priv-app/")) and HARDWARE_TERMS.search(path):
            add(runtime, "device application")
        # Stock places Ulefone/YFT hardware applications in system_a. These are
        # explicit names rather than a broad request to retain arbitrary system
        # applications. M170infisens is the ThermoVue Pro AC020 stack.
        if partition == "system" and DEVICE_APP_NAMES.search(path):
            add(runtime, "device hardware application")

    for runtime in CORE_STOCK_FILES:
        if stock_source(stock_root, runtime):
            add(runtime, "stock mount/device-node contract")
    for runtime in DEVICE_SYSTEM_APPS:
        add(runtime, "device hardware application")

    # Resolve in-stock ELF dependencies. Prefer the same partition and ABI
    # directory, but retain all equally plausible vendor-side providers.
    by_runtime = {f"{item['partition']}/{item['path']}": item for item in elf["elfs"]}
    by_name: dict[str, list[str]] = defaultdict(list)
    for runtime, item in by_runtime.items():
        by_name[Path(item["path"]).name].append(runtime)
        if item.get("soname"):
            by_name[item["soname"]].append(runtime)

    queue = deque(path for path in reasons if path in by_runtime)
    visited: set[str] = set()
    while queue:
        runtime = queue.popleft()
        if runtime in visited:
            continue
        visited.add(runtime)
        source = by_runtime[runtime]
        source_partition = source["partition"]
        source_lib64 = "/lib64/" in f"/{source['path']}"
        for needed in source.get("needed", []):
            providers = by_name.get(needed, [])
            preferred = [
                provider for provider in providers
                if by_runtime[provider]["partition"] == source_partition
                and ("/lib64/" in f"/{by_runtime[provider]['path']}") == source_lib64
            ]
            if not preferred:
                preferred = [
                    provider for provider in providers
                    if by_runtime[provider]["partition"] in {"vendor", "odm", "product", "system_ext"}
                    and ("/lib64/" in f"/{by_runtime[provider]['path']}") == source_lib64
                ]
            for provider in preferred:
                if provider not in reasons:
                    reasons[provider].add(f"DT_NEEDED by {runtime}")
                    queue.append(provider)

    grouped: dict[str, list[str]] = defaultdict(list)
    for runtime in sorted(reasons):
        grouped[runtime.split("/", 1)[0]].append(runtime)

    lines = [
        "# GQ5012BF1 proprietary candidates — generated, requires review",
        "# Redistribution status is not implied by inclusion in this file.",
        "# Generated from stock VINTF/init/HAL/module/config evidence and ELF closure.",
        "",
    ]
    # Evidence is emitted as a preceding comment line, never as an inline
    # comment: Lineage extract-utils parses `;` and `:` inside an entry as
    # argument/destination separators, so evidence text must not share the line.
    for partition in sorted(grouped):
        lines += [f"# {partition}"]
        for runtime in grouped[partition]:
            why = "; ".join(sorted(reasons[runtime]))
            lines.append(f"# {why}")
            lines.append(runtime)
        lines.append("")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines))

    report = {
        "count": len(reasons),
        "by_partition": {name: len(paths) for name, paths in sorted(grouped.items())},
        "reasons": {path: sorted(value) for path, value in sorted(reasons.items())},
    }
    args.out.with_suffix(".json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(reasons)} reviewed candidates to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
