#!/usr/bin/env python3
"""Extract GQ5012BF1 proprietary files from stock partitions or a live device."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEVICE = "gq5012bf1"
VENDOR = "ulefone"

# Evidence has not yet justified binary mutation. Keep the fixup hook explicit
# so future shims/patchelf changes are path-scoped and reproducible rather than
# ad-hoc post-extraction edits.
BLOB_FIXUPS: dict[str, tuple[str, ...]] = {}


def blob_fixup(entry: str, destination: Path) -> None:
    operations = BLOB_FIXUPS.get(entry, ())
    if operations:
        raise NotImplementedError(
            f"declared blob fixups are not implemented for {entry}: {operations}"
        )


def build_top(device_dir: Path) -> Path:
    env = os.environ.get("ANDROID_BUILD_TOP")
    if env:
        return Path(env).resolve()
    # .../device/ulefone/gq5012bf1
    return device_dir.parents[2]


def entries(path: Path) -> list[str]:
    result: list[str] = []
    for line in path.read_text().splitlines():
        value = line.split("#", 1)[0].strip().lstrip("-")
        if not value:
            continue
        value = value.split(";", 1)[0].split(":", 1)[0]
        result.append(value)
    return result


def adb_runtime_path(entry: str) -> str:
    # system_a is system-as-root; its extracted `system/...` directory maps to
    # runtime /system/..., not /system/system/....
    if entry.startswith("system/system/"):
        return "/system/" + entry.removeprefix("system/system/")
    partition, relative = entry.split("/", 1)
    return f"/{partition}/{relative}"


def find_source(root: Path, entry: str) -> Path | None:
    candidates = [root / entry]
    partition, relative = entry.split("/", 1)
    candidates += [root / partition / relative]
    if entry.startswith("system/system/"):
        candidates += [root / "system" / entry.removeprefix("system/system/")]
    for candidate in candidates:
        resolved = candidate
        for _ in range(16):
            if resolved.is_file():
                return resolved
            if not resolved.is_symlink():
                break
            target = Path(os.readlink(resolved))
            resolved = (
                root / target.as_posix().lstrip("/")
                if target.is_absolute()
                else resolved.parent / target
            )
    return None


def extract_directory(root: Path, entry: str, destination: Path) -> bool:
    source = find_source(root, entry)
    if source is None:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def extract_adb(entry: str, destination: Path) -> bool:
    runtime = adb_runtime_path(entry)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        result = subprocess.run(
            ["adb", "exec-out", "su", "-c", f"cat {runtime}"],
            stdout=output,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    if result.returncode or destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        default="adb",
        help="`adb` or a directory containing extracted partition roots",
    )
    parser.add_argument("--clean-vendor", action="store_true", help="remove the generated proprietary directory first")
    parser.add_argument("--no-setup", action="store_true", help="do not regenerate vendor makefiles")
    args = parser.parse_args()

    device_dir = Path(__file__).resolve().parent
    top = build_top(device_dir)
    vendor_root = top / "vendor" / VENDOR / DEVICE
    proprietary = vendor_root / "proprietary"
    if args.clean_vendor and proprietary.exists():
        shutil.rmtree(proprietary)
    proprietary.mkdir(parents=True, exist_ok=True)

    source_root = None if args.source == "adb" else Path(args.source).resolve()
    if source_root is not None and not source_root.is_dir():
        parser.error(f"source directory does not exist: {source_root}")

    missing: list[str] = []
    copied = 0
    for entry in entries(device_dir / "proprietary-files.txt"):
        destination = proprietary / entry
        ok = extract_adb(entry, destination) if source_root is None else extract_directory(source_root, entry, destination)
        if ok:
            blob_fixup(entry, destination)
            copied += 1
        else:
            missing.append(entry)

    print(f"extracted {copied} files; missing {len(missing)}")
    if missing:
        report = vendor_root / "missing-files.txt"
        report.write_text("\n".join(missing) + "\n")
        print(f"missing-file report: {report}", file=sys.stderr)
    else:
        (vendor_root / "missing-files.txt").unlink(missing_ok=True)

    if not args.no_setup:
        result = subprocess.run([sys.executable, str(device_dir / "setup-makefiles.py")], check=False)
        if result.returncode:
            return result.returncode
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
