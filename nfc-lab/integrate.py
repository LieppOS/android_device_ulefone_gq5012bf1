#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproducible NFC Lab integration step for an Android build tree.

Replaces ad-hoc copying and undocumented local patching:

  * The app is a manifest project at packages/apps/LieppOSNfcLab
    (LieppOS/NFC-ESP32-Android); this script only verifies it, never copies it.
  * The framework change is the pinned patch in this repository, applied here
    with an explicit revision check and an idempotent/reversible contract.

It does not sync, fetch, push, flash or touch the device, and it never edits
the upstream history of the projects it patches.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATCH = ROOT.parent / "patches/packages_modules_Nfc/0001-lieppos-nfc-lab-cache-and-type4-compat.patch"
NFC_PROJECT = "packages/modules/Nfc"
APP_PROJECT = "packages/apps/LieppOSNfcLab"
REVISION = __import__("runpy").run_path(str(ROOT / "prepare_patch.py"))["REVISION"]


def git(repo, *args, check=True):
    return subprocess.run(["git", "-c", "safe.directory=" + str(repo), "--no-optional-locks", *args],
                          cwd=repo, text=True, capture_output=True, check=check)


def state(nfc):
    """applied / clean / foreign, judged by the patch itself, not by guesswork."""
    if git(nfc, "apply", "--check", "-R", str(PATCH), check=False).returncode == 0:
        return "applied"
    if git(nfc, "apply", "--check", str(PATCH), check=False).returncode == 0:
        return "clean"
    return "foreign"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tree", type=Path, help="Android build tree root (already synced)")
    p.add_argument("--apply", action="store_true", help="Apply the pinned patch if it is not applied yet")
    p.add_argument("--revert", action="store_true", help="Reverse the pinned patch")
    args = p.parse_args()
    tree = args.tree.resolve()
    nfc = tree / NFC_PROJECT
    if not (nfc / ".git").exists():
        raise SystemExit("Not a synced Android tree: missing " + NFC_PROJECT)

    head = git(nfc, "rev-parse", "HEAD").stdout.strip()
    if head != REVISION:
        raise SystemExit("NFC project is at " + head + "; this patch is pinned to " + REVISION)

    app = tree / APP_PROJECT
    if not (app / "Android.bp").is_file():
        print("MISS app project absent:", APP_PROJECT,
              "- add LieppOS/NFC-ESP32-Android to the manifest and sync; do not copy sources by hand")
    elif not (app / ".git").exists():
        print("WARN app path exists but is not a VCS checkout:", APP_PROJECT,
              "- this is an unmanaged copy; replace it with the manifest project")
    else:
        origin = git(app, "remote", "get-url", "origin", check=False).stdout.strip()
        commit = git(app, "rev-parse", "HEAD").stdout.strip()
        managed = origin.endswith("NFC-ESP32-Android") or origin.endswith("NFC-ESP32-Android.git")
        print(("OK   " if managed else "WARN ") + "app project checkout:", APP_PROJECT,
              "commit", commit, "origin", origin or "(none)")
        if not managed:
            print("     origin does not look like the canonical app repository")

    current = state(nfc)
    print("Patch state:", current)
    if current == "foreign":
        raise SystemExit("Working tree neither matches the pinned patch nor accepts it; resolve manually")
    if args.apply and current == "clean":
        git(nfc, "apply", str(PATCH))
        print("Applied", PATCH.name)
    elif args.apply:
        print("Already applied; nothing to do (idempotent)")
    if args.revert and current == "applied":
        git(nfc, "apply", "-R", str(PATCH))
        print("Reverted", PATCH.name)
    elif args.revert:
        print("Not applied; nothing to revert")
    if not args.apply and not args.revert:
        print("Dry run only. Use --apply or --revert.")
    print("No sync, fetch, push, build, install or device operation was performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
