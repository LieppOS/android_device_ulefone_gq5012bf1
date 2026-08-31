# CLAUDE_FIX_REPORT.md

Offline remediation report for the Ulefone Armor 29 Pro Thermal / GQ5012BF1
full LieppOS device tree.

```text
Device tree: device/ulefone/gq5012bf1
Generated vendor tree: vendor/ulefone/gq5012bf1
Platform: MediaTek MT6878 / arm64
Stock launch API: 35 (Android 15)
Phone access: NONE -- no phone command, write or flash was performed
```

---

# EXECUTIVE SUMMARY

All three audited issues that can be corrected offline are resolved:

```text
DT-ELF-001  CLOSED
  Runtime DT_NEEDED graph now has zero unresolved required first-order,
  transitive or unexplained dependencies. The generated vendor tree is
  deterministic and contains 1,891 stock files.

DT-SEC-001  CLOSED OFFLINE
  The TrustKernel hardware/storage policy is now shared by recovery and the
  full ROM. Recovery-specific rootfs/Binder/FBE workarounds remain inside
  recovery_only(). The recovery monolithic policy is byte-identical to its
  pre-change baseline; the full-ROM policy now contains the missing rules.

DT-EVID-001 CLOSED
  Snapshot trust is now assigned by data class. KernelSU/property contamination
  is documented and automatically detected; good /sys and /proc hardware
  evidence remains usable. Spoofed Pixel 9 Pro attestation properties are not
  carried into the tree.
```

Both products pass `m nothing`; both products pass SELinux policy compilation
and neverallow/static tests. The final audit is:

```text
21 PASS
1 WARN   (the existing ten dead factory/alternate-BOM init references)
0 FAIL
```

No runtime claim was added. The full ROM remains BUILD-VALIDATED only and still
needs a complete Android 15+ LieppOS checkout plus hardware testing.

---

# DT-ELF-001

## Original state

The original extraction had 1,814 listed paths and every listed file existed in
stock, but that only proved list-to-stock path validity. It did not prove that a
retained ELF could load.

The independent audit parsed 1,461 retained ELF objects and found:

```text
46 first-order proprietary dependency names missing
81 transitive proprietary libraries implicated
90 concrete candidate paths in the original generated ledger
```

Important broken paths included boot control (`libmtk_bsg.so`),
`camerahalserver` (`libmtkcam_hal_aidl_provider.so` and helpers), MTK codec2
vdec/venc plugins, `libisetrusty.so`, modem-init libraries, GNSS libraries and
the Ulefone `vendor.yft.hardware.*` ODM interfaces.

## Classification totals

Every one of the original 90 concrete paths is classified in
[`docs/elf-closure.md`](docs/elf-closure.md) and in the updated
`MISSING_BLOBS_DT-ELF-001.txt` ledger:

```text
REQUIRED_STOCK_BLOB:                           47 paths
UNUSED_PARENT_BLOB, added conservatively:      23 paths
AOSP_OR_ROM_PROVIDED:                          14 paths
ALTERNATE_BOM_OR_FACTORY_ONLY, excluded:        6 paths
SHIM_OR_FIXUP_REQUIRED:                         0
DEVICE_UNIQUE_OR_CALIBRATION_DO_NOT_PACKAGE:    0
UNKNOWN:                                        0
                                                  --
TOTAL:                                         90 paths
```

`UNUSED_PARENT_BLOB` means unused by the current skeleton, not proven useless
hardware. These 23 libraries are dependencies of retained `system_ext` parents
(VT/IMS, charger UI, AEE/logging) whose stock init rc files are not integrated.
They were added conservatively so that a complete LieppOS product can activate
the parents without introducing a hidden linker failure.

## Blobs added

The complete stock inventory changed:

```text
proprietary-files.txt:  1,814 -> 1,891 paths   (+77 inventory paths)
```

Of those 77 paths:

```text
70 are copied from immutable stock into the generated vendor image
 7 are exact AOSP modules and remain inventory entries only
```

The 70 copied libraries close active and conservatively retained parents,
including:

```text
Boot / OTA:       libmtk_bsg.so
Camera:           libmtkcam_hal_aidl_{common,device,provider,utils}.so
Codec2:           libcodec2_mtk_{c2store,vdec,venc}.so and plugin closure
TEE storage:      libisetrusty.so
Modem:            libccci_util.so, libsysenv.so, libstorage_otp.so
GNSS/LBS:         libDR.so, libmnl.so, mtk_lbs_service-impl.so
Connectivity:     libconnfem.so, libforkexecwrap.so, libifcutils_mtk.so
Display/GPU/NN:   libmmlpqImpl.so, libmtkgpuserv.so,
                  libneuralnetworks_sl_driver_mtk_prebuilt.so
Ulefone ODM:      vendor.yft.hardware.{changenode,gesturewake,obtainvendor}@1.0.so
```

All additions are ELF files from the immutable stock partitions. The safety
sweep for nvram, nvdata, nvcfg, persist, protect1/2, keybox, IMEI, serial,
certificate/key and calibration paths returned zero hits.

## Blobs intentionally excluded

Six paths are reachable only through stock factory/META components:

```text
libfft_vendor.so       <- vendor/bin/factory
libminiui.so           <- vendor/bin/factory
libpixelflinger.so     <- libminiui.so
libhfmanagerwrapper.so <- vendor/bin/factory / vendor/bin/meta_tst
libkmsetkey.so         <- vendor/bin/meta_tst
libMcClient.so         <- libkmsetkey.so
```

`factory_no_image` and `meta_tst` are disabled factory/META services; the other
launchers occur only in `factory_init*.rc` or `meta_init*.rc`. They are not
normal-boot or VINTF HAL roots. They remain explicitly classified rather than
silently missing.

## AOSP replacements changed

All 198 original AOSP replacements remain; none was reverted.

Seven stock vendor paths were newly reclassified as AOSP-provided:

```text
android.hardware.biometrics.common.thread.so
android.hardware.biometrics.common.util.so
libcodec2_hidl@1.0.so
libcodec2_hidl@1.1.so
libcodec2_hidl@1.2.so
libcodec2_hidl_plugin.so
libcodec2_soft_common.so
```

This is proven by exact Soong module names, not filename similarity. Copying the
stock biometrics helpers produced a duplicate output rule during `m nothing`,
empirically proving that AOSP already installs the same module. Removing the
copy fixed the build.

Frozen AIDL backends are accepted only at the exact encoded ABI/SONAME version
(e.g. `-V1-ndk.so`, `-V3-ndk.so`). Their owning AOSP HAL modules and matching
VINTF versions provide the interface contract.

Final AOSP overlay:

```text
original replacements retained: 198
new AOSP reclassifications:        7
replacements reverted:             0
final overlay:                    205 paths
```

A second defect was fixed: excluding a stock path because AOSP provides it does
not itself request the module. `setup-makefiles.py` now emits
`PRODUCT_PACKAGES` for 38 unambiguously named service/binary/permission modules;
shared libraries arrive through their dependency graph.

## Tooling

`tools/elf_closure.py` now:

- parses ELF program headers without external Python dependencies;
- derives active normal-boot roots from init declarations and triggers;
- keeps property-gated and lazy HALs active even when declared `disabled`;
- separates factory/META roots;
- treats hw/egl/soundfx modules as dlopen roots;
- stops at AOSP system libraries rather than following MTK-patched stock copies;
- scans exact Soong module names for vendor-available AOSP libraries;
- classifies every unresolved SONAME using the required seven labels;
- fails with `--check` when any required dependency remains.

Negative test: removing `vendor/lib64/libmtk_bsg.so` makes the new audit fail
`elf-closure` with one unresolved required dependency.

## Final closure result

```text
ELF objects in generated proprietary tree:       1,538
  64-bit:                                        1,529
  legacy 32-bit:                                     9
active runtime roots:                              165
factory/META-only roots:                             5
unresolved REQUIRED_STOCK_BLOB:                     0
unresolved required transitive dependencies:        0
unexplained dependencies:                           0
classified AOSP_OR_ROM_PROVIDED SONAMEs:           122
classified factory/META-only SONAMEs:                6
```

The nine non-AArch64 files are the known legacy 32-bit/firmware objects; no
32-bit normal-boot consumer was found. No shim or blob fixup is currently
required.

---

# DT-SEC-001

## Original problem

`BOARD_VENDOR_SEPOLICY_DIRS` and TrustKernel `file.te` / `file_contexts` applied
to both products, but all 56 statements in `trustkernel.te` were inside one
`recovery_only()` block. For `target_recovery=false`, m4 expanded the file to
zero allow rules. A full ROM would therefore receive labelled tkcore/RPMB/store
objects and no permission for teed, KeyMint or Gatekeeper to access them.

## Common rules

34 source statements are now common to recovery and the full ROM:

- tkcore admin/client device-node access;
- teei/rpmb char/block access and the stock ioctl xperm set;
- tkcore data, protected, system-TA, SP-TA and log stores;
- `/proc/tkcore` and TrustKernel property access;
- KeyMint/Gatekeeper client-device access;
- traversal of `/mnt/vendor/persist` and `/mnt/vendor/protect_f` using the real
  `persist_data_file` and `protect_f_data_file` types;
- the critical non-redundant hard-link rule:

```te
allow tee tkcore_protect_data_file:file link;
```

TrustKernel commits a persistent object by hard-linking its staged block file;
`create_file_perms` excludes `link`. This behaviour belongs to TrustKernel, not
to recovery, so the full ROM needs the rule too.

## Recovery-only rules

22 source statements stay within `recovery_only()`:

- rootfs read/execute for tee, KeyMint and Gatekeeper, because the recovery
  linker/runtime lives on the ramdisk;
- recovery-specific TrustKernel property setting;
- recovery as KeyMint/Gatekeeper client and Keystore2/FBE host;
- HAL-to-recovery Binder direction fixes;
- recovery access to keystore service-manager entries;
- selinuxfs / `kernel:security compute_av` for recovery Keystore2;
- recovery `vold_key` management;
- Keystore2 rootfs runtime access;
- recovery synthetic-password unwrap permissions.

Normal Android runs those components from properly labelled `/system` and
`/vendor`, while vold/system_server perform the FBE flow. Sharing these rules
would be unnecessary widening.

## ROM-only rules

None were added. No ROM-only device-specific denial exists because the full ROM
has not run on hardware. AOSP core policy already handles the normal Android
vold/system_server/gatekeeper clients. No permission was invented.

## Validation

Source-level accounting:

```text
rule statements before: 56
rule statements after:  56
lost:                     0
invented:                 0
common:                   34
recovery-only:            22
ROM-only:                  0
```

M4 expansion:

```text
                         BEFORE   AFTER
target_recovery=false       0       37 expanded allow rules
target_recovery=true       76       76 expanded allow rules
```

Recovery regression proof:

```text
pre-change sepolicy.recovery SHA-256:  bcc760fe38c76c1d4190b456979d6dd8…
post-change sepolicy.recovery SHA-256: bcc760fe38c76c1d4190b456979d6dd8…
result: BYTE-IDENTICAL
```

`sesearch` also reports the tee, recovery and hal_keymint_default rule sets
identical before/after (245 / 413 / 238 rules respectively). The common
hard-link and mount-root traversal rules and recovery-only vold/locksettings
rules remain present.

Full-ROM proof:

```cil
(allow tee_202404 tkcore_protect_data_file (file (link)))
```

is now present in the compiled full-ROM `vendor_sepolicy.cil`. Recovery-only
`locksettings_key` and `vold_key` rules are absent from that policy.

Both products pass `m selinux_policy`, including `sepolicy_test`,
`sepolicy_dev_type_test`, property/file-context tests and neverallow checks.
SELinux remains enforcing. No permissive domain, broad generic allow,
`unlabeled` workaround or neverallow bypass was added.

Negative test: the pre-fix policy still passes the old `trustkernel-link` grep
because the text exists, while the new `trustkernel-rom-scope` check correctly
fails because the rule is unreachable by the ROM.

---

# DT-EVID-001

## Spoofed evidence identified

The live stock snapshot is useful hardware evidence but is not pristine stock
identity evidence:

```text
kernelsu                              present in proc.txt
ro.build.version.release              16; fingerprint encodes 15
ro.build.version.sdk                  36; stock firmware says 35
ro.product.model_for_attestation      Pixel 9 Pro; stock leaves empty
ro.product.brand_for_attestation      google; stock leaves empty
ro.product.name/device_for_attestation caiman; stock leaves empty
```

A LieppOS device-patches module also injects `persist.lieppos.*` flags for
thermal camera, secondary screen, lights, charging, FM, NFC and other features.
These are configuration flags, not proof that those hardware paths work.

The recovery snapshot also exposes KernelSU, proving the kernel/boot image is
patched. Its SDK/release values describe the Android-14-based recovery ramdisk;
that expected difference is not misreported as property spoofing.

## Documentation/tooling changes

- `CODEX.md` now uses a per-data-class hierarchy and contains the contamination
  warning.
- `docs/evidence-sources.md` carries the same hierarchy, exact contradictory
  values and consequences.
- `tools/snapshot_trust.py` detects root/property contamination, distinguishes
  a patched recovery boot image from userspace property spoofing, and fails
  `--check` when a contaminated capture lacks an adjacent `TRUST.md`.
- Both snapshots have local `TRUST.md` markers.
- `tools/audit_device_tree.py` checks snapshot trust markers and rejects any
  `_for_attestation` identity carried by tree config.

## New evidence hierarchy

```text
Hardware topology:
  live stock/recovery snapshots
  > stock firmware
  > decoded DTB/modules/VINTF/ELF
  > inference

Android build identity/version:
  stock firmware build.prop
  > stock images/manifests
  > current source tree
  > live properties

Security/product identity:
  verified TrustKernel hardware experiments
  > stock firmware
  > live properties
```

Hardware topology from `/sys`, `/proc`, I2C/SPI binding, loaded modules, DRM,
inputs, power supplies, nodes, services, cameras and sensors remains usable.

No Pixel/caiman attestation property is packaged. `PRODUCT_SHIPPING_API_LEVEL`
remains 35 because stock `ro.product.first_api_level=35` is authoritative.

---

# OTHER ISSUES FOUND

## AOSP replacement modules were not requested

The original 198 replacement paths were excluded from `PRODUCT_COPY_FILES`, but
`setup-makefiles.py` did not request the owning AOSP modules. A replacement path
could therefore simply be absent. The generator now requests 38 clear
service/binary/permission modules. Original replacement count is not reduced.

## Retained system_ext parents are not yet wired

The current skeleton retains MTK `system_ext` binaries such as VT/IMS, charger
UI and logging tools, while their stock `system_ext/etc/init` files are not
integrated. Their 23 proprietary dependencies were added conservatively, but
the daemons are not claimed active. Integrating their init files is a future
full-ROM decision requiring a complete source baseline and runtime testing.

## Existing dead-init warning remains valid

Ten vendor-rooted init executable references remain absent from the stock
payload. They are factory, META, alternate-BOM or stale V1 paths and remain a
WARN. No file was fabricated to silence the warning.

## Incomplete source checkout remains external

This recovery-oriented checkout still lacks a complete full-ROM baseline,
including `external/vixl`, `libvixld`, `vendor/lieppos` and `vendor/lineage`.
No device-tree hack was added for those external omissions.

---

# VALIDATION RESULTS

```text
Proprietary path validation:
  1,891/1,891 extracted; 0 missing; 0 duplicate destinations
  generated vendor files: 1,891
  generated output: byte-identical across two clean extractions

ELF closure:
  generated ELF objects: 1,538
  required first-order unresolved: 0
  required transitive unresolved: 0
  unexplained unresolved: 0
  factory/META-only exclusions: 6

AOSP replacements:
  original retained: 198
  newly reclassified: 7
  reverted: 0
  final overlay: 205
  explicit owning modules requested: 38

VINTF:
  inventory documents: 75 total
  HAL records: 734
  stock vendor/odm manifest documents listed: 55/55
  static coverage errors: 0

Init/services:
  inventory services: 263
  present vendor/odm service executables listed: 113/113
  static missing-executable errors: 0
  expected dead factory/alternate-BOM references: 10 WARN

Kernel modules:
  inventory copies: 471
  stock DLKM modules listed: 215/215
  static module coverage errors: 0

SELinux:
  full product policy compile: PASS
  recovery policy compile: PASS
  neverallow/static policy errors: 0
  recovery policy byte regression: 0

Determinism:
  inventory output: byte-identical
  generated vendor output: byte-identical
  setup-makefiles output: byte-identical
  device audit output: byte-identical

Build parsing:
  lineage_gq5012bf1 m nothing: PASS
  twrp_gq5012bf1 m nothing: PASS

Final device audit:
  PASS: 21
  WARN: 1
  FAIL: 0
```

On this host `LEX` must point to Soong's prebuilt flex to avoid a known
Make-vs-Soong host flex mismatch. This is an environment issue, not a device
failure.

---

# FILES CHANGED

Implementation commits changed or added:

```text
aosp-replaced-files.txt
proprietary-files.txt
setup-makefiles.py
tools/elf_closure.py
sepolicy/vendor/trustkernel.te
docs/evidence-sources.md
tools/snapshot_trust.py
tools/audit_device_tree.py
tools/README.md
```

Final documentation adds/updates:

```text
CODEX.md
CLAUDE_DEVICE_TREE_AUDIT.md
CLAUDE_FIX_REPORT.md
MISSING_BLOBS_DT-ELF-001.txt
docs/README.md
docs/blob-map.md
docs/build-status.md
docs/elf-closure.md
```

Generated, deterministic but intentionally outside this Git repository:

```text
vendor/ulefone/gq5012bf1/Android.bp
vendor/ulefone/gq5012bf1/BoardConfigVendor.mk
vendor/ulefone/gq5012bf1/gq5012bf1-vendor.mk
vendor/ulefone/gq5012bf1/proprietary/**  (1,891 files)
```

---

# COMMITS

```text
52e08a4  gq5012bf1: close proprietary ELF runtime dependencies
de65d56  gq5012bf1: share required TrustKernel policy with the full ROM
f67d886  gq5012bf1: correct the runtime evidence trust model
```

The report/documentation commit containing this file is separate from those
three implementation commits. Nothing was pushed.

---

# BUILD-VALIDATED VS RUNTIME-VALIDATED

## BUILD-VALIDATED in this session

```text
proprietary extraction and generated vendor makefiles
ELF first-order/transitive closure
AOSP replacement integration
VINTF document coverage
init executable coverage
DLKM module coverage
full-ROM TrustKernel policy architecture
recovery policy non-regression
both product makefile/Soong parsing (`m nothing`)
```

## Historically RUNTIME-VALIDATED and preserved

No phone test occurred now. Existing historical evidence remains valid for:

```text
OrangeFox boot                 SELinux enforcing
main display                   FT3680 touch
ADB / configfs USB             fastbootd / BootControl
TrustKernel teed               KeyMint / Gatekeeper / Keystore2
metadata unwrap                userdata mapper / F2FS mount
one-PIN user-0 decrypt         /data/media/0
```

The recovery policy is byte-identical to its pre-change baseline, and both
recovery builds pass, so no static regression was introduced.

## Still UNKNOWN at runtime

```text
full LieppOS boot              full-ROM SELinux behavior
RIL / SIM / 5G                 IMS / VoLTE / VoWiFi
Wi-Fi / Bluetooth / GNSS       NFC
all cameras                    ThermoVue thermal imaging
fingerprint                    rear display / rear touch integration
120 W / reverse charging       audio routes
sensors                        suspend/wake
OTA                            full-ROM fastbootd behavior
```

Static identification or configuration is not runtime proof.

---

# REMAINING BLOCKERS

1. Move the tree into a complete Android 15+ LieppOS checkout containing the
   missing platform and ROM vendor repositories.
2. Resolve any complete-checkout-only Soong/VINTF compatibility issues without
   adding device-local hacks for absent platform repositories.
3. Build real images with intentional project AVB keys; no Ulefone private key
   is available or fabricated.
4. Boot/test on hardware later, starting with enforcing full-ROM boot,
   TrustKernel/KeyMint/FBE, boot control and rollback-safe recovery.
5. Exercise every runtime-UNKNOWN subsystem individually and retain the
   IDENTIFIED / CONFIGURED / BUILD-VALIDATED / RUNTIME-VALIDATED distinction.

---

# FINAL VERDICT

```text
offline proprietary runtime dependency closure:  ACHIEVED
full-ROM TrustKernel SELinux architecture:        CORRECTED AND COMPILED
spoofed runtime identity evidence:                DEMOTED AND TOOL-GUARDED
recovery baseline:                                PRESERVED BYTE-FOR-BYTE
full-ROM runtime support:                         NOT CLAIMED
ready for complete Android 15+ LieppOS checkout:  YES
```

The tree is now ready for the next legitimate stage: integration in a complete
LieppOS source checkout. Hardware behaviour remains explicitly unproven until a
future no-flash test plan is approved and run on the phone.
