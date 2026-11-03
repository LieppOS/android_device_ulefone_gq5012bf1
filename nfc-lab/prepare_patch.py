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


STAMP = ".lieppos-pinned-revision"


def source_revision(source):
    """Resolve the revision of a checkout, or of a pristine export carrying a stamp."""
    stamp = source / STAMP
    if stamp.is_file():
        return stamp.read_text().strip()
    return subprocess.check_output(["git", "-c", "safe.directory=" + str(source), "--no-optional-locks", "rev-parse", "HEAD"], cwd=source, text=True).strip()


def generate(source):
    result = source_revision(source)
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
    if (!aidlConfigValue.t4tNfceeEnable && labOptIn && lieppos::nfc_lab::IsLabBoard(labBoard)) {
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
                return cache != null && cache.length == 40 && cache[34] == 1 && cache[35] != 1
                        && mT4tNfceeMgr.isNdefNfceefeatureEnabled()
                        && mT4tNfceeMgr.isNdefNfceeEmulationSupported();
            }
            // A degraded native cleanup means RF restoration is unverified, so the
            // operation fails even when the data itself looked correct.
            private void requireCleanLifecycle() {
                int[] cache = getLabControllerMetadata();
                if (cache == null || cache.length != 40 || cache[35] == 1)
                    throw new IllegalStateException("Type4 lifecycle degraded; RF restoration unverified");
            }
            public byte[] read(int fileId) {
                if (mT4tNfceeMgr.isNdefOperationOngoing()) throw new IllegalStateException("NDEF endpoint busy");
                requireCleanLifecycle();
                byte[] value = mT4tNfceeMgr.doReadData(new byte[] {(byte)(fileId >> 8), (byte)fileId});
                requireCleanLifecycle();
                return value;
            }
            public int write(int fileId, byte[] data) {
                if (mT4tNfceeMgr.isNdefOperationOngoing()) throw new IllegalStateException("NDEF endpoint busy");
                requireCleanLifecycle();
                int count = mT4tNfceeMgr.doWriteData(new byte[] {(byte)(fileId >> 8), (byte)fileId}, data);
                requireCleanLifecycle();
                return count;
            }
        });''')
    edit(p, '    public native boolean initializeNativeStructure();', '    public native int[] getLabControllerMetadata();\n\n    public native boolean initializeNativeStructure();')
    p = "NfcNci/nci/src/com/android/nfc/dhimpl/NativeT4tNfceeManager.java"
    for signature in ['int doWriteData(byte[] fileId, byte[] data)', 'byte[] doReadData(byte[] fileId)', 'boolean doClearNdefData()']:
        edit(p, 'public native ' + signature, 'public synchronized native ' + signature)
    # Route the existing setup/cleanup through a re-observed, idempotent lifecycle.
    # No unconditional discovery restart and no replacement of NFCC recovery.
    p = "NfcNci/nci/jni/NativeT4tNfcee.cpp"
    edit(p, '#include "nfc_config.h"', '#include "nfc_config.h"\n\n#include "LiepposT4tLifecycle.h"\n#include "LiepposNfcLab.h"')
    edit(p, 'NativeT4tNfcee NativeT4tNfcee::sNativeT4tNfceeInstance;', '''namespace {
// Adapter over the existing singleton's transport primitives.
class T4tDriver : public lieppos::t4t::Driver {
 public:
  explicit T4tDriver(NativeT4tNfcee& owner) : mOwner(owner) {}
  bool isDiscoveryStarted() override { return android::isDiscoveryStarted(); }
  void startRfDiscovery(bool start) override { android::startRfDiscovery(start); }
  bool openConnection() override { return mOwner.labOpenConnection() == NFA_STATUS_OK; }
  bool closeConnection() override { return mOwner.labCloseConnection() == NFA_STATUS_OK; }
  void setBusy(bool busy) override { mOwner.labSetBusy(busy); }
  bool isNfcOffTriggered() override { return mOwner.labIsNfcOffTriggered(); }
  void notifyNfcOff() override { mOwner.labNotifyNfcOff(); }

 private:
  NativeT4tNfcee& mOwner;
};

lieppos::t4t::Lifecycle& labLifecycle() {
  static lieppos::t4t::Lifecycle lifecycle;
  return lifecycle;
}

void publishLabHealth() {
  lieppos::nfc_lab::SetType4Health(labLifecycle().degraded(),
                                   labLifecycle().degradedCount());
}
}  // namespace

NativeT4tNfcee NativeT4tNfcee::sNativeT4tNfceeInstance;''')
    edit(p, '''tNFA_STATUS NativeT4tNfcee::setup(void) {
  static const char fn[] = "NativeT4tNfcee:setup";
  LOG(DEBUG) << StringPrintf("%s", fn);
  tNFA_STATUS status = NFA_STATUS_FAILED;
  setBusy();
  if (android::isDiscoveryStarted()) {
    android::startRfDiscovery(false);
  }

  status = openConnection();
  if (status != NFA_STATUS_OK) {
    LOG(ERROR) << StringPrintf("%s: openConnection Failed, status = 0x%X", fn,
                               status);
    if (!android::isDiscoveryStarted()) android::startRfDiscovery(true);
    resetBusy();
  }
  return status;
}''', '''tNFA_STATUS NativeT4tNfcee::setup(void) {
  static const char fn[] = "NativeT4tNfcee:setup";
  LOG(DEBUG) << StringPrintf("%s", fn);
  T4tDriver driver(*this);
  // Rejects reentrancy, stops discovery only when it is actually running, and
  // unwinds exactly what it changed when the open fails.
  const bool ready = labLifecycle().begin(driver);
  publishLabHealth();
  if (!ready) {
    LOG(ERROR) << StringPrintf("%s: setup refused or failed; no operation started", fn);
    return NFA_STATUS_FAILED;
  }
  return NFA_STATUS_OK;
}''')
    edit(p, '''void NativeT4tNfcee::cleanup(void) {
  static const char fn[] = "NativeT4tNfcee:cleanup";
  LOG(DEBUG) << StringPrintf("%s", fn);
  if (sIsNfcOffTriggered) {
    SyncEventGuard g(mT4tNfcOffEvent);
    mT4tNfcOffEvent.notifyOne();
    LOG(ERROR) << StringPrintf("%s: Nfc Off triggered", fn);
    return;
  }
  if (closeConnection() != NFA_STATUS_OK) {
    LOG(ERROR) << StringPrintf("%s: closeConnection Failed", fn);
  }
  if (!android::isDiscoveryStarted()) {
    android::startRfDiscovery(true);
  }
  resetBusy();
}''', '''void NativeT4tNfcee::cleanup(void) {
  static const char fn[] = "NativeT4tNfcee:cleanup";
  LOG(DEBUG) << StringPrintf("%s", fn);
  T4tDriver driver(*this);
  // Idempotent: a repeated call performs no further transport work.
  const bool clean = labLifecycle().finish(driver);
  publishLabHealth();
  if (!clean) {
    // Surfaced for the lab gate instead of being logged and discarded. RF
    // restoration is unverified here; callers must fail-stop, not retry.
    LOG(ERROR) << StringPrintf("%s: cleanup degraded; RF restoration unverified", fn);
  }
}

bool NativeT4tNfcee::labCleanupDegraded(void) { return labLifecycle().degraded(); }

tNFA_STATUS NativeT4tNfcee::labOpenConnection(void) { return openConnection(); }

tNFA_STATUS NativeT4tNfcee::labCloseConnection(void) { return closeConnection(); }

void NativeT4tNfcee::labSetBusy(bool busy) {
  if (busy) {
    setBusy();
  } else {
    resetBusy();
  }
}

bool NativeT4tNfcee::labIsNfcOffTriggered(void) { return sIsNfcOffTriggered; }

void NativeT4tNfcee::labNotifyNfcOff(void) {
  SyncEventGuard g(mT4tNfcOffEvent);
  mT4tNfcOffEvent.notifyOne();
}''')
    edit(p, '''    /* Try to close the connection with t4t nfcee, discard the status */
    (void)closeConnection();
    resetBusy();''', '''    /* Try to close the connection with t4t nfcee, discard the status */
    (void)closeConnection();
    /* The shutdown path owns closing here; restoration cannot be confirmed. */
    labLifecycle().abandon();
    publishLabHealth();
    resetBusy();''')
    p = "NfcNci/nci/jni/NativeT4tNfcee.h"
    edit(p, '''  std::vector<uint8_t> getT4TNfceeAid();
''', '''  std::vector<uint8_t> getT4TNfceeAid();

  /* LieppOS lab lifecycle boundary. These expose existing primitives to the
   * setup/cleanup policy object; they add no new controller command. */
  bool labCleanupDegraded(void);
  tNFA_STATUS labOpenConnection(void);
  tNFA_STATUS labCloseConnection(void);
  void labSetBusy(bool busy);
  bool labIsNfcOffTriggered(void);
  void labNotifyNfcOff(void);
''')
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
