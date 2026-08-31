#!/usr/bin/env python3
"""Audit the GQ5012BF1 tree against generated stock evidence and invariants."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class Check:
    id: str
    status: str
    detail: str


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def text(path: Path) -> str:
    return path.read_text(errors="replace") if path.is_file() else ""


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


def proprietary_entries(path: Path) -> set[str]:
    entries: set[str] = set()
    for line in text(path).splitlines():
        value = line.split("#", 1)[0].strip()
        if not value:
            continue
        value = value.split(";", 1)[0]
        value = value.split(":", 1)[0]
        entries.add(value.lstrip("-"))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    device = args.device.resolve()
    metadata = load(args.inventory / "metadata.json")
    stock_root = Path(metadata["inputs"]["stock_root"])
    vintf = load(args.inventory / "vintf.json")
    modules = load(args.inventory / "modules.json")
    init = load(args.inventory / "init.json")
    entries = proprietary_entries(device / "proprietary-files.txt")
    aosp_replaced = proprietary_entries(device / "aosp-replaced-files.txt")
    checks: list[Check] = []

    def check(identifier: str, ok: bool, detail: str, fail: str = "FAIL") -> None:
        checks.append(Check(identifier, "PASS" if ok else fail, detail))

    board = text(device / "BoardConfig.mk")
    fstab = text(device / "recovery/root/system/etc/recovery.fstab")
    security_rc = text(device / "recovery/root/init.recovery.gq5012bf1.security.rc")
    policy = text(device / "sepolicy/vendor/trustkernel.te")
    product_files = [device / "lineage_gq5012bf1.mk", device / "liepp_gq5012bf1.mk"]

    check("full-product", any(path.is_file() for path in product_files), "full ROM product makefile exists")
    check("extraction", (device / "extract-files.py").is_file() and (device / "setup-makefiles.py").is_file(), "modern extraction entry points exist")
    check("proprietary-list", bool(entries), f"{len(entries)} proprietary entries")
    check("aosp-replacements", bool(aosp_replaced) and aosp_replaced <= entries, f"{len(aosp_replaced)} stock paths intentionally inherited from AOSP modules")
    check("ab-ota", "AB_OTA_UPDATER := true" in board and "vendor_boot" in board, "A/B OTA and vendor_boot configured")
    check("dynamic-partitions", "PRODUCT_USE_DYNAMIC_PARTITIONS := true" in text(device / "device.mk"), "dynamic partitions enabled")
    check("metadata", "BOARD_USES_METADATA_PARTITION := true" in board and "/metadata f2fs" in fstab, "metadata partition contract retained")
    check("fbe-v2", "fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized" in fstab, "stock FBE v2 and inlinecrypt contract retained")
    check("trustkernel-model", "PRODUCT_MODEL := Armor 29 Pro" in "\n".join(text(path) for path in product_files + [device / "twrp_gq5012bf1.mk"]), "security-facing product model is Armor 29 Pro")
    check("trustkernel-order", "init.svc.vendor.keymint-3-0-trustkernel=running" in security_rc and "start vendor.gatekeeper" in security_rc, "verified KeyMint then Gatekeeper ordering retained")
    check("trustkernel-link", "tkcore_protect_data_file:file link" in policy, "TrustKernel persistent-object hard-link permission retained")
    check("usb-configfs", "TW_EXCLUDE_DEFAULT_USB_INIT := true" in board and "11201000.usb0" in text(device / "recovery/root/init.recovery.mt6878.rc"), "recovery configfs USB invariant retained")
    check("bootcontrol-misc", "/dev/block/sdc1" in text(device / "sepolicy/vendor/file_contexts") and "misc_block_device" in text(device / "sepolicy/vendor/file_contexts"), "physical misc inode labeling retained")

    manifest_docs = [doc for doc in vintf["documents"] if "manifest" in doc["path"] and doc["partition"] in {"vendor", "odm"}]
    accounted_docs = [doc for doc in manifest_docs if f"{doc['partition']}/{doc['path']}" in entries]
    checks.append(Check("vintf-coverage", "PASS" if len(accounted_docs) == len(manifest_docs) and manifest_docs else "WARN", f"{len(accounted_docs)}/{len(manifest_docs)} stock vendor/odm manifest documents listed"))

    stock_dlkm = [item for item in modules["modules"] if item["partition"] in {"vendor_dlkm", "odm_dlkm"}]
    accounted_modules = [item for item in stock_dlkm if f"{item['partition']}/{item['path']}" in entries]
    checks.append(Check("module-coverage", "PASS" if len(accounted_modules) == len(stock_dlkm) and stock_dlkm else "WARN", f"{len(accounted_modules)}/{len(stock_dlkm)} stock DLKM modules listed"))

    stock_services = [service for service in init["services"] if service["partition"] in {"vendor", "odm"}]
    listed_executables = 0
    executable_services = 0
    dead_references: set[str] = set()
    for service in stock_services:
        if not service["command"] or not service["command"][0].startswith("/"):
            continue
        runtime = service["command"][0].lstrip("/")
        if not runtime.startswith(("vendor/", "odm/")):
            continue
        if stock_source(stock_root, runtime) is None:
            dead_references.add(runtime)
            continue
        executable_services += 1
        if runtime in entries:
            listed_executables += 1
    checks.append(Check("init-executable-coverage", "PASS" if listed_executables == executable_services and executable_services else "WARN", f"{listed_executables}/{executable_services} present vendor/odm init executables listed"))
    checks.append(Check("dead-init-references", "WARN" if dead_references else "PASS", f"{len(dead_references)} init executable paths are absent from stock payload (factory/alternate-BOM references)"))

    counts = {status: sum(item.status == status for item in checks) for status in ("PASS", "WARN", "FAIL")}
    result = {"counts": counts, "checks": [asdict(item) for item in checks]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# GQ5012BF1 device-tree audit",
        "",
        f"PASS: **{counts['PASS']}** · WARN: **{counts['WARN']}** · FAIL: **{counts['FAIL']}**",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for item in checks:
        lines.append(f"| `{item.id}` | **{item.status}** | {item.detail} |")
    lines += ["", "Warnings identify evidence not yet fully accounted for; they are not silently accepted.", ""]
    args.out.write_text("\n".join(lines))
    print(f"audit: {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
