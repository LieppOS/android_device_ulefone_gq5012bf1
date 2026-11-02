#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Host/API compilation and patch checks, not a complete Android platform/APEX build."""
import argparse
import os
import re
import shutil
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


def run(label, args, cwd=None):
    print(label, flush=True)
    r = subprocess.run([str(x) for x in args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode:
        print(r.stdout[-18000:], file=sys.stderr)
        raise SystemExit(r.returncode)
    if r.stdout.strip():
        print(r.stdout[-4000:])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path, help="Read-only pinned packages/modules/Nfc reference")
    p.add_argument("--app", type=Path, required=True)
    p.add_argument("--policy", type=Path, help="Existing reference policy for narrow file_contexts type validation, not a policy rebuild")
    args = p.parse_args()
    source, app = args.source.resolve(), args.app.resolve()
    out = Path(os.environ.get("NFC_LAB_PLATFORM_OUT", str(app.parents[1] / "build/nfc-lab-platform")))
    out.mkdir(parents=True, exist_ok=True)
    contexts = ROOT.parent / "sepolicy/system_ext/private/file_contexts"
    rule = next(line.split()[0] for line in contexts.read_text().splitlines() if line and not line.startswith('#'))
    assert re.fullmatch(rule, '/data/nfc') and re.fullmatch(rule, '/data/nfc/sub/file')
    assert not re.fullmatch(rule, '/data/nfc-other') and not re.fullmatch(rule, '/data/vendor/nfc')
    if shutil.which('sefcontext_compile'):
        run("Compile narrow NFC file-context regex", ['sefcontext_compile', '-o', out / 'nfc-file-contexts.bin', contexts])
    else:
        print('SKIP file-context compiler unavailable')
    if args.policy:
        checkfc = source.parents[2] / 'out/host/linux-x86/bin/checkfc'
        run("Check context type against existing reference policy (not a rebuild)", [checkfc, args.policy, contexts])
    resource = ET.parse(ROOT / 'overlay/NfcNci/res/values/lieppos_nfc_lab.xml')
    assert resource.find('bool').text == 'false', 'Operational backend must remain build-disabled'
    fixture = out / 'profile-test.mk'
    fixture.write_text('DEVICE_PATH := device/ulefone/gq5012bf1\nTARGET_COPY_OUT_SYSTEM_EXT := system_ext\ninclude ' + str(ROOT / 'nfc-lab.mk') + '\nall:\n\t@echo "PACKAGES=$(PRODUCT_PACKAGES) PROPS=$(PRODUCT_SYSTEM_PROPERTIES)"\n')
    default = subprocess.check_output(['make', '-s', '-f', str(fixture), 'PLATFORM_SDK_VERSION=37'], text=True)
    assert 'LieppOSNfcLab' not in default and 'st21_t4t_compat' not in default
    enabled = subprocess.check_output(['make', '-s', '-f', str(fixture), 'PLATFORM_SDK_VERSION=37', 'LIEPPOS_NFC_LAB=true'], text=True)
    assert 'LieppOSNfcLab' in enabled and 'st21_t4t_compat=false' in enabled
    rejected = subprocess.run(['make', '-s', '-f', str(fixture), 'PLATFORM_SDK_VERSION=36', 'LIEPPOS_NFC_LAB=true'], text=True, capture_output=True)
    assert rejected.returncode != 0, 'Wrong-platform lab opt-in must fail'
    print('PASS profile defaults/API guard and disabled operational service')
    run("Verify reproducible pinned patch", [sys.executable, ROOT / "prepare_patch.py", source, "--check"])
    patch = ROOT.parent / "patches/packages_modules_Nfc/0001-lieppos-nfc-lab-cache-and-type4-compat.patch"
    run("Check exact patch application (no files changed)", ["git", "-c", "safe.directory=" + str(source), "apply", "--check", patch], source)
    header = ROOT / "overlay/libnfc-nci/src/include"
    run("Compile native cache/compatibility test with ASan/UBSan", ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-pthread", "-I", header, ROOT / "tests/native_test.cc", "-o", out / "native-test"])
    run("Run native parser, gating and concurrency tests", [out / "native-test"])
    contracts = sorted((ROOT / "overlay/NfcNci/src/org/lieppos/nfclab/ipc").glob("*.aidl"))
    for contract in contracts:
        assert contract.read_bytes() == (app / "src/main/aidl/org/lieppos/nfclab/ipc" / contract.name).read_bytes(), "Binder contracts diverged"
    sdk = Path(os.environ.get("ANDROID_HOME", str(Path.home() / "Android/Sdk")))
    tools = sdk / "build-tools/36.0.0"
    platform = sdk / "platforms/android-37.0"
    gen, classes = out / "gen", out / "classes"
    gen.mkdir(exist_ok=True); classes.mkdir(exist_ok=True)
    for contract in contracts:
        run("Compile NFC-owner Binder contract", [tools / "aidl", "-I" + str(ROOT / "overlay/NfcNci/src"), "-p" + str(platform / "framework.aidl"), "-o" + str(gen), contract])
    services = sorted((ROOT / "overlay/NfcNci/src/com/android/nfc/lab").glob("*.java"))
    run("Compile real owner services against Android37 SDK (not platform build)", ["javac", "--release", "11", "-cp", platform / "android.jar", "-d", classes, *services, *gen.rglob("*.java")])
    run("Compile pure Type4 ownership simulation", ["javac", "--release", "11", "-d", classes, ROOT / "overlay/NfcNci/src/com/android/nfc/lab/Type4LabController.java", ROOT / "tests/Type4ControllerTest.java"])
    run("Run Type4 ownership simulation", ["java", "-ea", "-cp", classes, "Type4ControllerTest"])
    # Compile the exact added JNI function body against real JDK JNI types, not fake Android stubs.
    text = patch.read_text()
    lines = []
    capture = False
    for line in text.splitlines():
        if line.startswith("+static jintArray nfcManager_getLabControllerMetadata"):
            capture = True
        if capture and line.startswith("+"):
            lines.append(line[1:])
            if line == "+}":
                break
    assert lines, "JNI function missing from patch"
    jni = out / "jni-boundary.cc"
    jni.write_text('#include <jni.h>\n#include "LiepposNfcLab.h"\n' + "\n".join(lines) + '\nvoid* test_reference = reinterpret_cast<void*>(&nfcManager_getLabControllerMetadata);\n')
    settings = subprocess.run(["java", "-XshowSettings:properties", "-version"], text=True, capture_output=True, check=True)
    actual_home = next(line.split("=", 1)[1].strip() for line in settings.stderr.splitlines() if "java.home =" in line)
    java_home = Path(os.environ.get("JAVA_HOME", actual_home)).resolve()
    if not (java_home / "include/jni.h").is_file():
        raise SystemExit("JDK JNI headers unavailable: " + str(java_home))
    run("Compile exact JNI cache getter boundary", ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", "-I", header, "-I", java_home / "include", "-I", java_home / "include/linux", jni])
    print("PASS offline native/API checks. Reference checkout unmodified. Full NFC APEX/SELinux/product build and RF tests remain pending.")


if __name__ == "__main__":
    main()
