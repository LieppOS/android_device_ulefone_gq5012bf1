#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate a pinned NFC source patch without modifying the reference checkout."""
import argparse
import difflib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
REVISION = "5b3b95382170fde2d778f8521e6ae3fcbc73307a"


def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError("Source anchor is absent/ambiguous; do not apply to another revision: " + old[:80])
    return text.replace(old, new, 1)


def generate(source):
    result = subprocess.check_output(["git", "-c", "safe.directory=" + str(source), "--no-optional-locks", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if result != REVISION:
        raise RuntimeError("Expected NFC revision " + REVISION + "; found " + result)
    changes = {}
    def edit(path, old, new):
        before = (source / path).read_text()
        current = changes.get(path, (before, before))[1]
        changes[path] = (before, replace(current, old, new))
    p = "libnfc-nci/src/adaptation/NfcAdaptation.cc"
    edit(p, "#include <android-base/logging.h>", "#include <android-base/logging.h>\n#include <android-base/file.h>\n#include \"LiepposNfcLab.h\"")
    edit(p, '      return ::ndk::ScopedAStatus::ok();\n    }\n    if (sVndExtnsPresent) {', '      return ::ndk::ScopedAStatus::ok();\n    }\n    lieppos::nfc_lab::Observe(copy.data(), copy.size());\n    if (sVndExtnsPresent) {')
    edit(p, '    configMap.emplace(NAME_T4T_NFCEE_ENABLE,\n                      ConfigValue(aidlConfigValue.t4tNfceeEnable ? 1 : 0));', '''    // Frozen AIDL V1 remains unchanged. Only this board's explicitly opted-in,
    // already-enabled ST NFCEE profile may compensate for the legacy false field.
    const auto labBoard = android::base::GetProperty("ro.product.vendor.device", "");
    const bool labOptIn = android::base::GetBoolProperty(
        "nfc.lieppos.st21_t4t_compat", false);
    std::string stConfig;
    if (!aidlConfigValue.t4tNfceeEnable && labOptIn && labBoard == "gq5012bf1") {
      if (!android::base::ReadFileToString("/vendor/etc/libnfc-hal-st.conf", &stConfig)) {
        stConfig.clear();  // Fail closed; no policy relaxation or file write.
      }
    }
    const bool labType4Configured = lieppos::nfc_lab::EffectiveT4t(
        aidlConfigValue.t4tNfceeEnable, labBoard, labOptIn, stConfig);
    lieppos::nfc_lab::SetType4Configured(labType4Configured);
    configMap.emplace(NAME_T4T_NFCEE_ENABLE, ConfigValue(labType4Configured ? 1 : 0));''')
    p = "NfcNci/nci/jni/NativeNfcManager.cpp"
    edit(p, '#include "NfcAdaptation.h"', '#include "NfcAdaptation.h"\n#include "LiepposNfcLab.h"')
    edit(p, 'static JNINativeMethod gMethods[] = {', '''static jintArray nfcManager_getLabControllerMetadata(JNIEnv* env, jobject) {
  const auto snapshot = lieppos::nfc_lab::Snapshot();
  jintArray result = env->NewIntArray(snapshot.size());
  if (result) env->SetIntArrayRegion(result, 0, snapshot.size(), snapshot.data());
  return result;
}

static JNINativeMethod gMethods[] = {
    {"getLabControllerMetadata", "()[I", (void*)nfcManager_getLabControllerMetadata},''')
    p = "NfcNci/nci/src/com/android/nfc/dhimpl/NativeNfcManager.java"
    edit(p, '        sInstance = this;', '''        sInstance = this;
        com.android.nfc.lab.LabDiagnosticsService.attachSource(this::getLabControllerMetadata);
        com.android.nfc.lab.LabType4Service.attachPort(new com.android.nfc.lab.Type4LabController.Port() {
            public Object mutex() { return mT4tNfceeMgr; }
            public boolean ready() {
                int[] cache = getLabControllerMetadata();
                return cache != null && cache.length == 40 && cache[34] == 1
                        && mT4tNfceeMgr.isNdefNfceefeatureEnabled()
                        && mT4tNfceeMgr.isNdefNfceeEmulationSupported();
            }
            public byte[] read(int fileId) {
                if (mT4tNfceeMgr.isNdefOperationOngoing()) throw new IllegalStateException("NDEF endpoint busy");
                return mT4tNfceeMgr.doReadData(new byte[] {(byte)(fileId >> 8), (byte)fileId});
            }
            public int write(int fileId, byte[] data) {
                if (mT4tNfceeMgr.isNdefOperationOngoing()) throw new IllegalStateException("NDEF endpoint busy");
                return mT4tNfceeMgr.doWriteData(new byte[] {(byte)(fileId >> 8), (byte)fileId}, data);
            }
        });''')
    edit(p, '    public native boolean initializeNativeStructure();', '    public native int[] getLabControllerMetadata();\n\n    public native boolean initializeNativeStructure();')
    p = "NfcNci/nci/src/com/android/nfc/dhimpl/NativeT4tNfceeManager.java"
    for signature in ['int doWriteData(byte[] fileId, byte[] data)', 'byte[] doReadData(byte[] fileId)', 'boolean doClearNdefData()']:
        edit(p, 'public native ' + signature, 'public synchronized native ' + signature)
    p = "NfcNci/Android.bp"
    edit(p, '    name: "nfc-sources",\n    srcs: [\n        "src/**/*.java",', '    name: "nfc-sources",\n    srcs: [\n        "src/**/*.java",\n        "src/**/*.aidl",')
    p = "NfcNci/AndroidManifest.xml"
    edit(p, '    <application android:name=".NfcApplication"', '    <permission android:name="org.lieppos.permission.NFC_LAB_DIAGNOSTICS" android:protectionLevel="signature" />\n    <permission android:name="org.lieppos.permission.NFC_LAB_TYPE4" android:protectionLevel="signature" />\n    <application android:name=".NfcApplication"')
    edit(p, '    </application>', '''        <service android:name="com.android.nfc.lab.LabDiagnosticsService"
                 android:exported="true"
                 android:permission="org.lieppos.permission.NFC_LAB_DIAGNOSTICS" />
        <service android:name="com.android.nfc.lab.LabType4Service"
                 android:exported="true" android:enabled="@bool/lieppos_nfc_lab_type4_enabled"
                 android:permission="org.lieppos.permission.NFC_LAB_TYPE4" />
    </application>''')
    for path in sorted((ROOT / "overlay").rglob("*")):
        if path.is_file():
            rel = path.relative_to(ROOT / "overlay").as_posix()
            if (source / rel).exists():
                raise RuntimeError("Overlay would replace existing source: " + rel)
            changes[rel] = ("", path.read_text())
    parts = ["From: LieppOS NFC Lab\nSubject: [PATCH] nfc: cached lab diagnostics and opt-in ST21 Type4 compatibility\n\n",
             "Base: " + REVISION + " (Lineage packages/modules/Nfc)\nNo raw commands, frozen AIDL changes, or default RF enablement.\nOperational Type4 access is separately permissioned and build-disabled.\n\n"]
    for rel, (before, after) in sorted(changes.items()):
        parts.append("diff --git a/" + rel + " b/" + rel + "\n")
        if not before:
            parts.append("new file mode 100644\n")
        # Git accepts an empty context line without its optional space prefix.
        # Preserve real source whitespace, without trailing whitespace in patch files.
        diff = difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="a/" + rel if before else "/dev/null", tofile="b/" + rel)
        parts.extend("\n" if line == " \n" else line for line in diff)
    return "".join(parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--check", action="store_true", help="Compare committed patch without changing it")
    args = parser.parse_args()
    text = generate(args.source.resolve())
    dest = ROOT.parent / "patches/packages_modules_Nfc/0001-lieppos-nfc-lab-cache-and-type4-compat.patch"
    if args.check:
        if dest.read_text() != text:
            raise SystemExit("Patch differs from canonical overlay/recipe")
        print("PASS reproducible pinned NFC patch")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        print(dest)
