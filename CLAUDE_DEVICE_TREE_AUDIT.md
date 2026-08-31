# CLAUDE_DEVICE_TREE_AUDIT.md

Independent red-team audit of `device/ulefone/gq5012bf1` and `vendor/ulefone/gq5012bf1`.

```text
Device            Ulefone Armor 29 Pro Thermal
Codename          GQ5012BF1
Platform          MediaTek MT6878 / arm64
Audit date        2026-08-31
Audit HEAD        407d8ec  (== origin/master)
Auditor scope     offline evidence + host build validation
Device attached   NO (see AUD-ENV-001)
```

---

# EXECUTIVE SUMMARY

This tree is **substantially better than average** for a MediaTek bring-up. The
recovery/security work is not merely plausible — large parts of it are provable
at byte level from the artifacts on disk, and I independently reproduced them.
The SELinux policy is evidence-driven, narrowly scoped, enforcing, and carries
justification comments that survive scrutiny. `vendor_boot` packaging is
*exactly* correct. Git hygiene is clean. The tooling is deterministic. The
project's own `TODO.md` is unusually honest and under-claims rather than
over-claims.

That said, the audit found **three findings that the prior 16 PASS / 1 WARN /
0 FAIL result does not capture**, and one of them invalidates a premise of the
audit brief itself:

1. **DT-ELF-001 (CRITICAL).** The proprietary extraction is **not dependency
   closed**. 46 first-order (81 transitive, 90 concrete paths) genuinely
   proprietary shared libraries that retained blobs link against are absent
   from `proprietary-files.txt`. This includes `libmtk_bsg.so` (boot control
   HAL), `libmtkcam_hal_aidl_provider.so` (camerahalserver), the MTK codec2
   video decode/encode plugins, `libisetrusty.so` (TEE storage proxy),
   `libccci_util.so`/`libsysenv.so`/`libstorage_otp.so` (modem init), the GNSS
   libraries, and all three Ulefone `vendor.yft.hardware.*` ODM HIDL libraries.
   The claim "zero missing files" is true only in the narrow sense that every
   *listed* path exists in stock. It says nothing about completeness, which is
   precisely the trap the brief warned about.

2. **DT-SEC-001 (HIGH).** The entire TrustKernel SELinux policy in
   `sepolicy/vendor/trustkernel.te` is wrapped in `recovery_only(...)`, while
   `sepolicy/vendor/file_contexts` and `file.te` are **not** conditional. A
   full-ROM build therefore gets labelled TrustKernel devices, RPMB nodes and
   `/mnt/vendor/{persist,protect_f}` roots with **zero** corresponding allow
   rules. This is exactly the recovery/full-ROM policy leakage the brief asks
   about, in the direction nobody checked.

3. **DT-EVID-001 (CRITICAL, evidence integrity).** The "live stock Android
   snapshot" — priority **#1** in the brief's source-of-truth order — was
   captured on a device running **KernelSU** with an active property-spoofing
   module. `kernelsu` appears in `/proc/modules`; `ro.build.version.sdk`
   reports **36/Android 16** while `ro.build.fingerprint` and the actual stock
   firmware both say **15**; `ro.product.*_for_attestation` reports
   *Pixel 9 Pro / caiman / google* while the real stock `vendor/build.prop`
   leaves those properties **empty**. Every identity, version and property
   claim sourced from that snapshot must be demoted. Hardware topology facts
   from the same snapshot (bus bindings, drivers, power-supply nodes, camera
   enumeration) remain trustworthy.

Separately, the audit brief's own framing is stale in two places: the branch is
**not** three commits ahead and unpushed (it is level with `origin/master` and
two commits *further along* than the brief describes), and `TODO.md` §4's
`PRODUCT_SHIPPING_API_LEVEL` build hazard has already been fixed.

I **agree** with 16 of the prior result's 17 conclusions and reproduced its
WARN exactly (the "10 dead init paths" count reconciles perfectly with my
independent enumeration). I **disagree** that the result is `0 FAIL`.

```text
MY VERDICT:  Recovery target     — production quality, evidence-backed
             Full ROM target     — honest skeleton, NOT bootable as-is
             Prior 0 FAIL        — not supportable; 1 CRITICAL + 2 HIGH stand
```

---

# CONFIRMED

## DT-VB-001 — vendor_boot packaging is byte-level correct

```text
ID:          DT-VB-001
Severity:    INFO
Category:    C. vendor_boot
Status:      CONFIRMED
```

**Claim:** header v4, 67108864 bytes, stock PLATFORM fragment preserved, stock
DTB preserved, custom RECOVERY fragment only, valid AVB footer.

**Evidence:** I parsed both the stock `vendor_boot.img` and
`build36/vendor_boot_a-orangefox-FULL64M-BUILD36.img` directly:

```text
                        STOCK                            BUILD36
header_version          4                                4
page_size               4096                             4096
image size              67108864                         67108864
kernel_addr             0x40000000                       0x40000000
ramdisk_addr            0x66f00000                       0x66f00000
tags_addr               0x47c80000                       0x47c80000
dtb_addr                0x47c80000                       0x47c80000
vendor_cmdline          bootopt=64S3,32N2,64N2           bootopt=64S3,32N2,64N2
ramdisk fragments       2                                2
  [PLATFORM] size       28759822                         28759822
  [PLATFORM] sha256     9201a4e5c1b7cb1f...              9201a4e5c1b7cb1f...   IDENTICAL
  [RECOVERY] size       4714551                          33582922              (expected)
dtb_size                342395                           342395
dtb sha256              bc156c29c33d8226...              bc156c29c33d8226...   IDENTICAL
AVB footer magic        AVBf                             AVBf
```

`prebuilt/dtbs/stock.dtb` also hashes to `bc156c29c33d8226…`, i.e. the
in-tree DTB is the stock DTB, unmodified.

**Why it matters:** Every boot-geometry value in `BoardConfig.mk` is confirmed
against the real artifact rather than against MTK convention. The PLATFORM
fragment being byte-identical proves the full-ROM work did not disturb recovery
packaging.

**Recommended action:** No change.
**Confidence:** HIGH — byte-level.

## DT-EXT-001 — extraction counts are exactly as claimed

```text
ID:          DT-EXT-001
Severity:    INFO
Category:    D. Proprietary extraction
Status:      CONFIRMED
```

**Evidence:** independent parse of `proprietary-files.txt` (stripping inline
comments, `-` prefixes and `|hash` pins) against the on-disk vendor tree and
against all seven extracted stock partitions:

```text
entries in proprietary-files.txt          1814   (claim: 1,814)
files present in vendor/.../proprietary   1814
entries with no file on disk                 0
files on disk not in the list                0
duplicate destinations                       0
blob paths not found in stock partitions     0
aosp-replaced-files.txt entries            198   (claim: 198)
partition spread   vendor 1500 | vendor_dlkm 219 | system_ext 81 | system 10 | product 4
```

**Recommended action:** No change to the counts. See DT-ELF-001 for what the
counts do *not* prove.
**Confidence:** HIGH.

## DT-INIT-001 — the "10 dead init paths" WARN reconciles exactly

```text
ID:          DT-INIT-001
Severity:    LOW
Category:    H. Init/services
Status:      CONFIRMED
```

**Claim:** 10 dead factory/alternate-BOM init paths absent from stock payload.

**Evidence:** I enumerated all `service <name> <exec>` entries across every
retained `vendor/etc/init/**.rc` and `vendor/odm/etc/init/**.rc` — 120 services
— and resolved each executable against blobs ∪ AOSP-replacements. 26 do not
resolve. Filtering to `vendor/`-rooted executables (the tool's scope) yields
**exactly 10**:

```text
/vendor/bin/boringssl_self_test32                              (32-bit; device is 64-bit only)
/vendor/bin/hw/btlfpserver                                     alt-BOM fingerprint
/vendor/bin/hw/vendor.fptool.fingerprint@2.0-service           alt-BOM fingerprint
/vendor/bin/hw/vendor.sw.swfingerprint@1.0-service             alt-BOM fingerprint
/vendor/bin/hw/vendor.focaltech.fingerprint@1.0-service        alt-BOM fingerprint
/vendor/bin/gnss_daemon                                        meta/factory
/vendor/bin/permission_check                                   factory
/vendor/bin/spm_loader                                         meta/factory
/vendor/bin/thermal_manager                                    meta/factory
/vendor/bin/hw/android.hardware.graphics.allocator-V1-service-mediatek   stale V1 rc
```

The remaining 16 are `/system/*` or `/apex/*` paths (`adbd`, `sh`, `dumpstate`,
`ueventd` are legitimately AOSP-provided; `akmd8963`, `msensord`, `mdlogger`,
`dualmdlogger`, `emdlogger1/2/3/5/6`, `osi`, `fingerprintd`, `sdcard` are dead
factory references outside the tool's counting scope).

**Why it matters:** The prior WARN is accurate and correctly refuses to
fabricate files. See DT-INIT-002 for one misclassification inside it.
**Recommended action:** Keep as WARN.
**Confidence:** HIGH.

## DT-SEC-002 — TrustKernel SELinux invariants are intact (recovery)

```text
ID:          DT-SEC-002
Severity:    INFO
Category:    I / J. SELinux, TrustKernel
Status:      CONFIRMED
```

**Evidence:**

- `allow tee tkcore_protect_data_file:file link;` is present in
  `sepolicy/vendor/trustkernel.te`, with a comment explaining that
  `create_file_perms` in this AOSP version excludes `link` and that TrustKernel
  commits persistent objects by hard-linking `block0.1`. **Not redundant. Not
  deleted.**
- `/mnt/vendor/persist` → `persist_data_file` and `/mnt/vendor/protect_f` →
  `protect_f_data_file` in `file_contexts`, with both types declared in
  `file.te`. **Meaningful types, not `unlabeled`.**
- No `permissive`, no `typepermissive`, no `unconfined_domain`, no
  neverallow bypass, no catch-all `allow ... self:*` in the vendor policy.
- Startup order `teed → KeyMint → Gatekeeper → Keystore2` is expressed through
  the policy's binder-call grants and the recovery rc; no 90-second delay
  workaround is present.
- RPMB ioctl allowances are enumerated explicitly
  (`allowxperm ... ioctl { 0x2282 0x2285 0x5388 0x5391 0xb300-0xb301 }`) rather
  than granted wholesale.

**Evidence quality note:** `zero SELinux/sepolicy/*.cil files appear in the
extraction` (I grepped: count 0). That is **correct** — stock policy binaries
must never be shipped in a device tree; policy has to be rebuilt from source.

**Recommended action:** No change for recovery. See DT-SEC-001 for full ROM.
**Confidence:** HIGH.

## DT-FBE-001 — encryption/storage contract matches stock exactly

```text
ID:          DT-FBE-001
Severity:    INFO
Category:    K. Encryption/storage
Status:      CONFIRMED
```

**Evidence:** `recovery/root/system/etc/recovery.fstab` userdata line is
character-for-character identical to stock `vendor/etc/fstab.mt6878`:

```text
fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized
keydirectory=/metadata/vold/metadata_encryption
metadata  f2fs  ... first_stage_mount
userdata  f2fs  ... inlinecrypt,checkpoint=fs,fsverity,quota,latemount
```

`TW_USE_FSCRYPT_POLICY := 2`, `TW_INCLUDE_FBE_METADATA_DECRYPT := true`.
Nothing disables encryption, removes metadata encryption, or downgrades the
policy version.

**Recommended action:** No change.
**Confidence:** HIGH.

## DT-USB-001 — recovery correctly avoids legacy android_usb init

```text
ID:          DT-USB-001
Severity:    INFO
Category:    L. USB
Status:      CONFIRMED
```

**Evidence:** `TW_EXCLUDE_DEFAULT_USB_INIT := true` and
`TW_MTP_DEVICE := /dev/usb-ffs/mtp/ep0`, both inside the
`ifneq ($(filter twrp_%,$(TARGET_PRODUCT)),)` guard. The BoardConfig comment
documents the two-USB-stack conflict and the FunctionFS resolution, matching
commits `66f5e8c` / `8470ea0`. Stock's configfs path
(`sys.usb.configfs=1`, `sys.usb.controller=11201000.usb0`) is retained.

**Recommended action:** No change.
**Confidence:** HIGH.

## DT-HW-001 — main touchscreen is correctly and specifically configured

```text
ID:          DT-HW-001
Severity:    INFO
Category:    M. Main touchscreen
Status:      CONFIRMED — RUNTIME-VALIDATED
```

**Evidence:**

```text
live stock  input.txt : driver=/sys/bus/spi/drivers/fts_ts
live stock  spi.txt   : module=/sys/module/focaltech_touch_spi_ft3680
live stock  getevent  : name: "fts_ts"
in-tree ko sha256     : 6629ec6148ac361a5f0085b8b19efa9d591426679f58262c4998345f41931162
claimed     sha256    : 6629ec6148ac361a5f0085b8b19efa9d591426679f58262c4998345f41931162   MATCH
```

No generic touchscreen configuration replaced this.
**Recommended action:** No change.
**Confidence:** HIGH.

## DT-BUILD-001 — both products pass `m nothing`

```text
ID:          DT-BUILD-001
Severity:    INFO
Category:    10. Build-system verification
Status:      CONFIRMED (with host caveat)
```

**Evidence:** I reproduced both builds.

```text
lunch twrp_gq5012bf1-ap2a-eng        + m nothing  -> build completed successfully (02:25)
lunch lineage_gq5012bf1-ap2a-userdebug + m nothing -> build completed successfully (02:33)
```

Both initially failed with
`make_vars-…mk: error: Soong variable check failed` caused by
`LEX does not match between Make and Soong: Make: flex / Soong: <prebuilt>`.
That is a **host environment defect, not a device-tree defect** — this host
(CachyOS/Gentoo) has `/usr/bin/flex 2.6.4` on PATH and this build/make revision
resolves `LEX` from PATH while Soong uses the prebuilt. Overriding
`LEX=<soong prebuilt path>` makes both products build clean. `external/vixl` is
indeed absent, consistent with the minimal recovery manifest, and per the brief
is not counted against the tree.

**Recommended action:** Document the `LEX` override in `build-gq5012bf1.sh` or
`vendorsetup.sh` so the next person does not misdiagnose it as a tree defect.
**Confidence:** HIGH.

## DT-GIT-001 — commits are atomic and contain no junk

```text
ID:          DT-GIT-001
Severity:    INFO
Category:    11. Git verification
Status:      CONFIRMED
```

**Evidence:** 65 tracked files total. `git ls-files | grep -c pycache` = 0,
`grep -c '^\.work'` = 0. `.gitignore` correctly excludes `.work/`,
`__pycache__/`, `*.pyc`. `git check-ignore -v` confirms both. The 7.2 GB
`.work/` analysis workspace and the `__pycache__` directories exist on disk but
are untracked. Largest tracked files are legitimate device artifacts
(`prebuilt/kernel` 16 MB, `prebuilt/dtbo.img` 8 MB, the FT3680 module 392 KB).
No personal files, no live calibration data, no giant generated artifacts.

Commit contents match their messages:

```text
8376139  .gitignore + tools/ (5 files, +1076)              stock inventory tooling
ec460e8  proprietary-files.txt + aosp-replaced-files.txt
         + extract-files.py + setup-makefiles.py (+2339)   extraction skeleton
75d3c41  AndroidProducts/BoardConfig(+Rom)/device.mk
         + lineage_gq5012bf1.mk + docs/ (22 files, +638)   full ROM skeleton
```

**Recommended action:** No change.
**Confidence:** HIGH.

## DT-TOOL-001 — tooling is deterministic

```text
ID:          DT-TOOL-001
Severity:    INFO
Category:    9. Tooling verification
Status:      CONFIRMED
```

**Evidence:** Ran `tools/audit_device_tree.py` twice against the same
inventory; outputs are byte-identical (`cmp` clean) and both report
`audit: 16 pass, 1 warn, 0 fail`. `tools/README.md` explicitly documents
immutable stock inputs, `.work/` output isolation, and that "a warning is an
explicit gap, not evidence that a subsystem works."

**Recommended action:** No change.
**Confidence:** HIGH.

## DT-ID-001 — security-facing product identity is correct

```text
ID:          DT-ID-001
Severity:    INFO
Category:    A. Product identity
Status:      CONFIRMED
```

**Evidence:** stock `system/build.prop` → `ro.product.system.model=Armor 29 Pro`,
`ro.product.system.device=GQ5012BF1`. Both `lineage_gq5012bf1.mk` and
`twrp_gq5012bf1.mk` set `PRODUCT_MODEL := Armor 29 Pro` (not the marketing
"Thermal" string), `PRODUCT_DEVICE := gq5012bf1`, `PRODUCT_BRAND := Ulefone`,
`PRODUCT_MANUFACTURER := Ulefone`. The comment justifying this is accurate.

## DT-API-001 — `PRODUCT_SHIPPING_API_LEVEL := 35` is correct

```text
ID:          DT-API-001
Severity:    INFO
Category:    A. Product structure
Status:      CONFIRMED
```

**Evidence:** real stock firmware `vendor/build.prop` →
`ro.product.first_api_level=35`; stock `system/build.prop` →
`ro.build.version.sdk=35`, `ro.build.version.release=15`. The tree got this
right by trusting the *firmware*, not the (contaminated — see DT-EVID-001) live
snapshot which reports 36. The `ifneq ($(filter 35 36 37,$(PLATFORM_SDK_VERSION)),)`
guard is also what resolves `TODO.md` §4's recovery-build hazard.

## DT-SUPER-001 — super partition geometry matches the bootloader

```text
ID:          DT-SUPER-001
Severity:    INFO
Category:    B. Partition layout
Status:      CONFIRMED
```

**Evidence:** `fastboot getvar all` →
`partition-size:super: 240000000` (hex) = 9 663 676 416 bytes.
`BoardConfigRom.mk` → `BOARD_SUPER_PARTITION_SIZE := 9663676416`. Exact match.
`BOARD_MAIN_SIZE := 9661579264` leaves a 2 MiB metadata/alignment reserve,
which is the correct convention. `has-slot:super: no` is consistent with
Virtual A/B (single super, no retrofit).

## DT-Z-001 — no device-unique or mutable calibration data is redistributed

```text
ID:          DT-Z-001
Severity:    INFO
Category:    Z. Device-unique data
Status:      CONFIRMED
```

**Evidence:** I regex-swept all 1814 entries for
`nvram|nvdata|nvcfg|persist|protect[12f]|keybox|serial|imei|calib|\.pem|\.pk8|\.x509|certificate|\bnv\b`.
58 hits, and **every one is code or static firmware**, not device state:
`libnvram*.so`, `nvram_daemon`, `fuelgauged_nvram`, `tee_check_keybox`
(binaries); `wfnv_desc_{data,map}_soc70.bin` (static descriptor/map tables);
`st21nfc_fw*.bin`, `soc7_0_ram_*`, `mt66xx_fm_*` (static firmware);
`morphoEISCalibration*.bin` (static EIS tuning shipped in stock).

No `/mnt/vendor/persist` content, no `nvdata`/`nvcfg` partition content, no
`protect1`/`protect2` content, no TEE state, no modem NV, no per-unit Wi-Fi/BT
calibration, no serials, keys or certificates. **Clean.**

---

# QUESTIONABLE

## DT-CAM-001 — "four camera sensors identified" is one interpretation of ambiguous evidence

```text
ID:          DT-CAM-001
Severity:    MEDIUM
Category:    P. Cameras
Status:      QUESTIONABLE
```

**Claim:** four camera sensors identified.

**Evidence:** live `camera-dump.txt` shows **three** MTK-enumerated physical
sensor drivers but **four** `Facing:` blocks:

```text
[00] BACK   SENSOR_DRVNAME_IMX989_MIPI_RAW        hasFlashUnit:1
[01] FRONT  SENSOR_DRVNAME_S5KJN1_MIPI_RAW        hasFlashUnit:0
[02] BACK   SENSOR_DRVNAME_S5KJN1MAIN2_MIPI_RAW   hasFlashUnit:1
Facing: Back / Front / Back / Back   <- 4 camera IDs
```

So: 4 camera IDs, 3 distinct physical sensor driver names, 2 of which are the
same silicon (S5KJN1) in different slots. The 4th back-facing ID is **not**
backed by an MTK sensor enumeration entry and its provenance is unestablished —
it may be the thermal imager, a logical/depth camera, or a macro sensor behind a
different provider.

The `IMX989` identification also deserves suspicion. IMX989 is Sony's 1-inch
flagship sensor; its presence on this device class is implausible on cost
grounds, and the identification rests on a driver **name string** plus
`imx989_mipi_raw_IdxMgr.so` / `imx989cts_mipi_raw_IdxMgr.so` in the blob list.
The `…cts…` variant strongly suggests a CTS-satisfying profile. Driver name is
not silicon identity.

**Why it matters:** The brief explicitly says to flag identification based only
on strings without binding or runtime evidence.

**Recommended action:** Downgrade to `IDENTIFIED (name-string only)` for
IMX989. Record 4 camera IDs / 3 enumerated physical sensors and mark the 4th
ID's provenance UNKNOWN. Bind each ID to a `v4l-subdev` and an I2C/CSI address
from the DTB before claiming a sensor map.
**Confidence:** HIGH that the claim is under-evidenced.

## DT-FP-001 — "Microarray fingerprint transport identified" overstates the evidence, and no working HAL path exists

```text
ID:          DT-FP-001
Severity:    HIGH
Category:    R. Fingerprint
Status:      QUESTIONABLE / functionally WRONG
```

**Evidence:**

```text
VINTF  vendor/etc/vintf/manifest/fingerprint-example.xml
         android.hardware.biometrics.fingerprint  v3  IFingerprint/virtual
binary vendor/bin/hw/android.hardware.biometrics.fingerprint-service.example   (retained blob)
lib    vendor/lib64/hw/microarray.fingerprint.default.so                       (retained blob)
node   /dev/madev0                                                             (live stock)
drivers  fingerprint | ft_fingerprint | yft_finger (module=fingerprint)        (live stock)
init   vendor/etc/init/hw/init.fingerprint.rc declares 5 services, ALL missing:
         btlfpserver, fingerprintd, fptool@2.0, sw@1.0, focaltech@1.0
```

The **declared instance is `virtual`**, i.e. the AOSP example/virtual HAL, not a
vendor implementation. `microarray.fingerprint.default.so` is a legacy
`hw_get_module`-style library that **nothing in the retained set loads** — every
init service that could have loaded it is a dead path. So:

- The *transport* is `/dev/madev0` (madev), which is genuinely Microarray-family.
- The *sensor model* is **not** established.
- There is **no functioning fingerprint HAL path in the extraction at all**.
  Whatever drives the sensor on stock is outside the extracted set (likely an
  ODM app/service or a system_ext component not captured).

**Why it matters:** The brief says: "Do not claim exact sensor model if only
transport/vendor family is known," and section H requires that VINTF-declared
HALs have real services. Both are violated in the optimistic direction.

**Recommended action:** Restate as "transport = madev (`/dev/madev0`), vendor
family = Microarray, sensor model UNKNOWN, no HAL path present." Investigate
what binds `/dev/madev0` on stock before claiming fingerprint support at all.
**Confidence:** HIGH.

## DT-THERM-001 — ThermoVue AC020 is not supported by any binding evidence

```text
ID:          DT-THERM-001
Severity:    HIGH
Category:    Q. ThermoVue thermal camera
Status:      QUESTIONABLE
```

**Claim:** a ThermoVue AC020 stack was identified.

**Evidence found, in full:**

```text
system/system/app/M170infisens/M170infisens.apk        (blob list)
persist.lieppos.armor29.thermal_cam = true             (live snapshot property)
```

**Evidence NOT found, after searching every live snapshot file and all seven
extracted stock partitions for `ac020|thermovue|infisens|thermal_cam|guide|iray`:**

```text
no /dev node                        no kernel module          no driver binding
no service executable               no JNI/native library     no vendor/HIDL/AIDL interface
no SELinux domain or type           no calibration ownership  no init entry
```

Worse, `persist.lieppos.armor29.thermal_cam` is a `persist.lieppos.*` property —
a **custom LieppOS namespace, not a stock Ulefone property** — appearing in a
snapshot that DT-EVID-001 shows is contaminated. It is not stock evidence.

**Why it matters:** The brief says verbatim: "Do not accept 'APK exists' as
proof of thermal-camera support." The current state is exactly that, minus even
the AC020 string.

**Recommended action:** Downgrade ThermoVue to **UNKNOWN**. Remove "AC020" from
documentation until a device node, driver or library string supports it.
Decompiling `M170infisens.apk` for its JNI library names and device paths is the
cheapest next step.
**Confidence:** HIGH.

## DT-AVB-001 — AVB is enabled with chained vbmeta but no keys or algorithms

```text
ID:          DT-AVB-001
Severity:    HIGH
Category:    B. Partition layout / AVB
Status:      QUESTIONABLE
```

**Evidence:** `BoardConfigRom.mk` sets

```make
BOARD_AVB_ENABLE := true
BOARD_AVB_VBMETA_SYSTEM := system system_ext product
BOARD_AVB_VBMETA_VENDOR := vendor vendor_dlkm odm_dlkm
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION := 1
BOARD_AVB_VBMETA_VENDOR_ROLLBACK_INDEX_LOCATION := 2
```

but a tree-wide grep for
`BOARD_AVB_(KEY_PATH|ALGORITHM|VBMETA_SYSTEM_KEY_PATH|VBMETA_SYSTEM_ALGORITHM|VBMETA_VENDOR_KEY_PATH|VBMETA_VENDOR_ALGORITHM)`
returns **nothing**. `build/make/core/Makefile` consumes
`BOARD_AVB_VBMETA_SYSTEM_KEY_PATH` at lines 5027/5067/5147/6071. With it unset,
chained partitions fall back to the AOSP **test key**.

**Why it matters:** Images signed with the AOSP test key will not verify on a
locked bootloader and are not release-grade. The rollback index *locations* are
declared while the rollback indexes themselves are not, which is an incomplete
AVB contract.

**Mitigating:** the file's own comment already says "Release builds must provide
intentional project keys; never copy or fabricate Ulefone private signing
material." The gap is acknowledged, not hidden — hence QUESTIONABLE rather than
WRONG.

**Recommended action:** Add explicit `BOARD_AVB_*_KEY_PATH` /
`BOARD_AVB_*_ALGORITHM` for main, vbmeta_system and vbmeta_vendor pointing at
project keys, or add a hard build-time guard that fails the release build when
they are unset.
**Confidence:** HIGH.

## DT-VABC-001 — Virtual A/B compression is enabled on stock but not configured in the tree

```text
ID:          DT-VABC-001
Severity:    MEDIUM
Category:    B. Partition layout
Status:      QUESTIONABLE
```

**Evidence:** stock properties:

```text
ro.virtual_ab.enabled=true                      ro.virtual_ab.compression.enabled=true
ro.virtual_ab.compression.xor.enabled=true      ro.virtual_ab.userspace.snapshots.enabled=true
ro.virtual_ab.batch_writes=true                 ro.virtual_ab.io_uring.enabled=true
```

`device.mk` inherits only `virtual_ab_ota.mk`, which sets
`PRODUCT_VIRTUAL_AB_OTA := true` and `ro.virtual_ab.enabled=true`. There is no
`virtual_ab_ota_compression.mk` inheritance and no `PRODUCT_VIRTUAL_AB_*`
overrides anywhere in the tree.

**Why it matters:** A full ROM built as-is would produce non-compressed VAB OTA
metadata against a device whose stock configuration expects compressed,
userspace-snapshot, XOR-enabled VABC. OTA behaviour and super space accounting
would diverge from stock.

**Recommended action:** Inherit
`$(SRC_TARGET_DIR)/product/virtual_ab_ota/compression.mk` (or the branch
equivalent) for the full ROM product only, and re-verify `BOARD_MAIN_SIZE`
headroom afterwards.
**Confidence:** MEDIUM — needs a real Android 15+ checkout to confirm the exact
makefile name.

## DT-AOSP-001 — several AOSP replacements are stock-faithful but functionally stubs

```text
ID:          DT-AOSP-001
Severity:    MEDIUM
Category:    E. AOSP replacements
Status:      QUESTIONABLE (correct, but mis-labelled as "safe")
```

**Evidence:** three of the 198 replacements are AOSP *example/virtual* HALs:

```text
Stock component   vendor/bin/hw/android.hardware.biometrics.face-service.example
Replacement       AOSP module of the same name
VINTF             face-default.xml -> android.hardware.biometrics.face v3 IFace/default
Interface compat  YES (same module, same fqname)
Reality           AOSP's face "example" is a VIRTUAL HAL. Stock itself ships it.

Stock component   vendor/bin/hw/android.hardware.ir-service.example
VINTF             ir-service.example.xml -> android.hardware.ir v1
Reality           AOSP virtual/stub IR HAL. Stock itself ships it.

Stock component   vendor/bin/hw/android.hardware.biometrics.fingerprint-service.example
VINTF             IFingerprint/virtual
Reality           AOSP virtual HAL. See DT-FP-001.
```

The **replacement decision is defensible** — stock genuinely shipped the AOSP
module, so substituting the AOSP build of the same module is byte-for-purpose
equivalent. What is *not* defensible is any downstream inference that face
unlock, IR blaster or fingerprint therefore "work". They are declared in VINTF
but backed by virtual implementations.

Also flagged: `vendor/bin/hw/android.hardware.health-service.example` is
AOSP-replaced while the device has a complex charging topology (mt6375 gauge,
sc8571 charge pumps, master/slave + divider/hv-divider chargers, a second
`3rd-gauge`). Commit `52d2f09` ("fix battery reporting") and the extensive
`genfs_contexts` battery labelling show the AOSP health HAL needed substantial
help to find the battery at all. That is a signal the replacement is *thin*, not
*wrong*.

**Recommended action:** Annotate these four in `aosp-replaced-files.txt` as
"stock shipped the AOSP stub — capability NOT implied". Do not revert them.
**Confidence:** HIGH.

## DT-DOOGEE-001 — a DOOGEE calibration blob is being shipped on a Ulefone

```text
ID:          DT-DOOGEE-001
Severity:    LOW
Category:    D. Proprietary extraction
Status:      QUESTIONABLE
```

**Evidence:** `vendor/etc/camera/eis/morphoEISCalibration_DOOGEE_M24PS.bin` is
in the extraction. It is present in stock (ODM shared-BOM leftover) and is
static tuning data, not per-unit state, so it is not a redistribution hazard.

**Recommended action:** Harmless to keep for stock fidelity; worth a comment so
nobody later "fixes" the main `morphoEISCalibration.bin` by pointing at it.
**Confidence:** HIGH.

---

# WRONG

## DT-ELF-001 — the proprietary extraction is not dependency closed

```text
ID:          DT-ELF-001
Severity:    CRITICAL
Category:    F. ELF dependency graph
Status:      WRONG
```

**Claim under test:** "1,814 entries, zero missing files."

**Method:** I parsed `PT_DYNAMIC`/`DT_NEEDED` from all 1461 ELF objects in the
vendor tree, built a provider index from blobs ∪ AOSP-replacements, and
resolved every dependency. Unresolved sonames were then classified by whether
stock provides them from `system/system/lib*` (⇒ AOSP will build them) or only
from `vendor/lib*` / `system_ext/lib*` (⇒ genuinely proprietary, must be
extracted).

**Result:**

```text
distinct unresolved DT_NEEDED sonames                       150
  provided by AOSP/system (safe: libc, libutils, HIDL/NDK…)  91
  AOSP-buildable interface libs (vendor-installed by module)   7
  GENUINELY PROPRIETARY AND ABSENT                            46   <-- defect
transitive closure of the proprietary set                     81
concrete paths to add (incl. lib64/mt6878 variants)           90
```

**Representative impact — this is not a long tail of cosmetics:**

```text
libmtk_bsg.so                     <- android.hardware.boot-service.mtk       A/B slot switching, OTA
libmtkcam_hal_aidl_provider.so    <- camerahalserver (+ mt6878 variant)      ALL cameras
  (pulls libmtkcam_hal_aidl_{common,device,utils}.so transitively)
libcodec2_mtk_vdec.so
libcodec2_mtk_venc.so             <- android.hardware.media.c2@1.2-mediatek-64b   video decode/encode
libcodec2_mtk_c2store.so            (pulls libcodec2_hidl@1.{0,1,2}.so,
                                     libcodec2_vpp_{fa,mi,qt,rs}_plugin.so, …)
libisetrusty.so                   <- mtk_storageproxyd                       TEE/Trusty storage
libMcClient.so                    (transitive)                               Trustonic MobiCore client
libccci_util.so                   <- ccci_mdinit, ccci_rpcd, md_monitor      MODEM INIT / RIL
libsysenv.so, libstorage_otp.so   <- ccci_mdinit                             modem init
libmnl.so, libDR.so               <- mnld                                    GNSS
mtk_lbs_service-impl.so           <- mtk_lbs_service                         GNSS/LBS
libconnfem.so, libhwm.so          <- nvram_daemon                            Wi-Fi/BT calibration access
libmmagent.so                     <- vendor.mediatek.hardware.mmagent-service
libmmlpqImpl.so                   <- vendor.mediatek.hardware.mmlpq@V1-service   display picture quality
libmtkgpuserv.so                  <- vendor.mediatek.hardware.gpuserv-service
libneuralnetworks_sl_driver_mtk_prebuilt.so  <- NN shim (+ lazy)             NNAPI
vendor.yft.hardware.changenode@1.0.so     <- yft changenode service          ULEFONE ODM HAL
vendor.yft.hardware.gesturewake@1.0.so    <- yft gesturewake service         ULEFONE ODM HAL
vendor.yft.hardware.obtainvendor@1.0.so   <- yft obtainvendor service        ULEFONE ODM HAL
libkphproxy.so, libpl.so          <- tee_check_keybox, obtainvendor
libifcutils_mtk.so                <- frs, ipsec_mon, netdagent, thermal_core
libforkexecwrap.so                <- ipsec_mon, netdagent
system_ext: libaed.so, libmagt.so, libshowlogo.so (kpoc_charger), libterservice.so,
            libmtk_vt_service.so, libsysenv_system.so, libem_support_jni.so,
            libpcap_bak.so, vendor.mediatek.hardware.log@1.0.so
            + transitive libimsma*.so, libsink/libsource/libsignal, libvcodec_cap*  IMS/VT
```

**Why it matters:** Every one of these is a hard `DT_NEEDED`. The dynamic linker
fails the process at load time, not lazily. A full ROM built from this tree
would lose boot-control, cameras, hardware video codecs, modem bring-up, GNSS,
NNAPI, the TEE storage proxy, and all three Ulefone-specific ODM HALs. The
"zero missing files" metric measures *list-to-stock path existence*, which is a
different and much weaker property than *closure*.

**Also note the 7 AOSP-buildable interface libs** (`android.hardware.ir-V1-ndk.so`,
`…cas-V1-ndk.so`, `…contexthub-V2-ndk.so`, `…secure_element-V1-ndk.so`,
`…tetheroffload-V1-ndk.so`, `…biometrics.face-V3-ndk.so`,
`android.frameworks.stats-V1-ndk.so`) — these are lower risk because the AOSP
HAL modules normally install their own NDK backend to `/vendor`, but they are
in neither list and should be confirmed rather than assumed.

**Files:** `proprietary-files.txt`, `vendor/ulefone/gq5012bf1/proprietary/**`
**Commands:** custom ELF `DT_NEEDED` walker over 1461 objects; full list written
to `/tmp/missing_blobs.txt` (90 paths).

**Recommended action:**

1. Add the 90 concrete paths to `proprietary-files.txt` (they are already in the
   extracted stock partitions under `.work/gq5012bf1/stock/partitions`, so
   `extract-files.py` can pick them up with no new evidence needed).
2. Re-run the closure to fixpoint after adding, since adding libraries can
   surface a second order.
3. **Add a closure check to `tools/audit_device_tree.py`** so this class of
   defect cannot recur silently. This is the single highest-value change
   available to this tree.

**Confidence:** HIGH. Mechanically derived; independently reproducible.

## DT-SEC-001 — TrustKernel policy is recovery-only while its labels are not

```text
ID:          DT-SEC-001
Severity:    HIGH
Category:    I / J. SELinux, TrustKernel
Status:      WRONG (for the full ROM target)
```

**Evidence:** `BoardConfig.mk` adds the policy directory **unconditionally**:

```make
BOARD_VENDOR_SEPOLICY_DIRS += device/ulefone/gq5012bf1/sepolicy/vendor
```

Inside that directory:

```text
trustkernel.te     ENTIRE FILE wrapped in recovery_only(` … ')
file.te            NOT conditional  — declares tkcore_*, persist_data_file,
                                      protect_f_data_file, rpmb_device, proc_tkcore
file_contexts      NOT conditional  — labels /dev/tkcore_*, /dev/*rpmb*,
                                      /mnt/vendor/persist, /mnt/vendor/protect_f,
                                      /data/vendor/t6, /vendor/app/t6
genfs_contexts     NOT conditional  — proc /tkcore, power_supply nodes
property_contexts  NOT conditional  — vendor.trustkernel.*, ro.boot.rpmb_status
```

**Consequence for `lineage_gq5012bf1`:** the build emits types and file
contexts for every TrustKernel object, and **not one allow rule**. `teed`,
`hal_keymint_default` and `hal_gatekeeper_default` would be denied access to
`/dev/tkcore_client`, `/dev/mmcblk0rpmb`, `/mnt/vendor/persist/t6` and
`/proc/tkcore` under enforcing. Since no stock SELinux binaries are extracted
(correctly — DT-SEC-002), nothing else supplies those rules.

Net effect: **a full ROM would boot with a labelled but completely
unauthorised TrustKernel stack** — no KeyMint, no Gatekeeper, no Keystore2
hardware backing, and therefore no FBE unlock. This is the precise inverse of
the recovery bug that commits `3fa9f31`…`bbe7af2` spent so much effort fixing.

**Why it matters:** The brief's category A asks whether the full ROM
accidentally inherits recovery-only configuration. It does — and category I
asks about recovery/full-ROM policy leakage, which this is, in the
under-privileged direction. Neither the prior audit nor
`tools/audit_device_tree.py` checks it (`trustkernel-link` only greps for the
rule's *presence*, not its reachability from a full-ROM build).

**Recommended action:** Split the policy. Keep genuinely recovery-specific
grants (rootfs execute, `binder_call(recovery, …)`, keystore-on-ramdisk,
synthetic-password unwrap) inside `recovery_only(...)`. Move the
device/file/property access rules that stock also needs — tkcore char devices,
RPMB, tkcore data/protect files, `proc_tkcore`, the `link` permission,
`persist`/`protect_f` search — **outside** the guard so both targets get them.
Then re-run `m selinux_policy` for `lineage_gq5012bf1` and diff the compiled
policy against stock's `vendor_sepolicy.cil` for the `tee` domain.

**Confidence:** HIGH on the mechanism; MEDIUM on runtime blast radius, since a
full-ROM boot has never been attempted.

## DT-EVID-001 — the "live stock" snapshot is from a rooted, property-spoofed device

```text
ID:          DT-EVID-001
Severity:    CRITICAL (evidence integrity)
Category:    2 / 4. Source-of-truth order and evidence
Status:      WRONG (the evidence is mislabelled, not the tree)
```

**Evidence:**

```text
gq5012bf1-live-stock-20260831-113332/proc.txt:484
    kernelsu 319488 0 - Live 0x0000000000000000 (OE)          <-- KernelSU loaded
```

Property contradictions in the same snapshot:

```text
                                  LIVE SNAPSHOT      REAL STOCK FIRMWARE (V15)
ro.build.fingerprint              …GQ5012BF1:15/…    …GQ5012BF1:15/…      (same build)
ro.build.version.release          16                 15                   MISMATCH
ro.build.version.sdk              36                 35                   MISMATCH
ro.system.build.version.sdk       36                 35                   MISMATCH
ro.product.model_for_attestation  Pixel 9 Pro        (empty)              SPOOFED
ro.product.brand_for_attestation  google             (empty)              SPOOFED
ro.product.name_for_attestation   caiman             (empty)              SPOOFED
ro.product.device_for_attestation caiman             (empty)              SPOOFED
persist.lieppos.armor29.thermal_cam = true           (not a stock namespace)
```

The same build fingerprint reporting two different SDK levels is only possible
with runtime property overriding. Combined with the loaded `kernelsu` module,
the `_for_attestation` values pointing at a Pixel 9 Pro, and the artifacts
directory containing `images_pull_sukisu_boot_image/`, this is a **KernelSU
(SukiSU) install with a Play-Integrity-style spoofing module active**.

**Why it matters:** The brief places "live stock Android snapshot" at
**priority #1**, above the stock firmware files. That ordering is unsafe for
this snapshot. Any conclusion about Android version, API level, build
fingerprint, attestation identity or `persist.*`/`ro.*` properties drawn from it
is unreliable. The tree happens to have gotten `PRODUCT_SHIPPING_API_LEVEL`
right (DT-API-001) by using the firmware instead — but that appears to be good
instinct rather than a documented policy.

**What is still trustworthy in that snapshot:** hardware topology. Bus bindings
(`i2c.txt`, `spi.txt`), driver names, `power-supply.txt`, `video4linux.txt`,
`camera-dump.txt`, `input-dump.txt`, `getevent.txt`, `display-ids.txt` and
`/proc/modules` are not targets of integrity spoofing modules.

**Recommended action:**

1. Amend `docs/evidence-sources.md` and the source-of-truth ordering: for
   **identity/version/property** claims, extracted stock firmware outranks the
   live snapshot. For **hardware topology** claims, the live snapshot remains
   authoritative.
2. Re-capture a clean snapshot from an unrooted stock boot if identity evidence
   is ever needed again.
3. Note explicitly that `ro.product.*_for_attestation` are **empty on real
   stock**, so no attestation-spoofing values should be carried into the ROM.

**Confidence:** HIGH.

## DT-ROM-001 — the full ROM product is a skeleton and cannot boot

```text
ID:          DT-ROM-001
Severity:    HIGH
Category:    A. Product and build structure
Status:      WRONG (as a "product"), CONFIRMED (as a "skeleton")
```

**Evidence:** `device.mk` contains, in its entirety: two product inherits
(`virtual_ab_ota.mk`, `emulated_storage.mk`), `PRODUCT_USE_DYNAMIC_PARTITIONS`,
three `PRODUCT_BUILD_*_DLKM_IMAGE` flags, `PRODUCT_SOONG_NAMESPACES`, and
`PRODUCT_FULL_TREBLE_OVERRIDE`. There is **no** `PRODUCT_PACKAGES`, no
`PRODUCT_COPY_FILES`, no fstab installation, no `ueventd.rc`, no HAL packages,
no overlays, no permissions XMLs, no `PRODUCT_PROPERTY_OVERRIDES`, no kernel
module load configuration.

Additionally, `lineage_gq5012bf1.mk` inherits a ROM base only if it exists:

```make
ifneq ($(wildcard vendor/lieppos/config/common_full_phone.mk),)   # absent
else ifneq ($(wildcard vendor/lineage/config/common_full_phone.mk),)  # absent
endif
```

`ls vendor/` in this checkout returns `qcom recovery twrp ulefone` — **neither
base exists**. So the `m nothing` pass for `lineage_gq5012bf1` (DT-BUILD-001)
validates a product with no ROM base at all.

**Why it matters:** Commit `75d3c41`'s message says "skeleton" and is honest.
But the audit brief's status block presents "Full ROM product: `m nothing`
passed" as validation. It is not — it proves makefile syntax, nothing more.

**Recommended action:** Keep the skeleton, but state plainly in
`docs/build-status.md` and `README.md` that the full ROM is BUILD-PARSE-VALID
only, and that `m nothing` on a checkout lacking `vendor/lieppos` proves
approximately nothing about product completeness.
**Confidence:** HIGH.

## DT-INIT-002 — one "dead factory/alternate-BOM" path is actually a stale V1 HAL rc

```text
ID:          DT-INIT-002
Severity:    LOW
Category:    H. Init/services
Status:      WRONG (classification, not the finding)
```

**Evidence:** `vendor/etc/init/android.hardware.graphics.allocator-V1-service-mediatek.rc`
declares `service vendor.gralloc-v1 /vendor/bin/hw/android.hardware.graphics.allocator-V1-service-mediatek`,
which does not exist. It is counted in the "factory/alternate-BOM" WARN bucket.

It is neither factory nor alternate BOM. Stock ships **both** a V1 and a V2 rc;
only the V2 service binary exists, and
`vendor/etc/vintf/manifest/manifest_allocator.xml` declares
`android.hardware.graphics.allocator` **version 2**, `IAllocator/default`. The
V1 rc is simply vendor cruft superseded by V2.

I initially flagged this as a missing critical gralloc binary; that was wrong —
`android.hardware.graphics.allocator-V2-service-mediatek` and its `.mt6878`
variants are all present and VINTF matches. Recording the correction here since
a red-team report should show its own false positives.

**Recommended action:** Re-label this entry in the WARN as "stale V1 rc
superseded by V2" so the bucket stays meaningful.
**Confidence:** HIGH.

---

# UNKNOWN / CANNOT PROVE OFFLINE

## DT-DISP-001 — rear display is IDENTIFIED, not implemented

```text
ID:          DT-DISP-001
Severity:    MEDIUM
Category:    N. Secondary display/touch
Status:      UNKNOWN
```

**Evidence:**

```text
IDENTIFIED     hyn_ts driver on I2C, module=hynitron  (live stock i2c.txt)
               spi_tiny_co5300_lcd.ko in vendor_dlkm
RUNTIME-PROVEN rear TOUCH is active:  input-dump "Device 5: hyn_ts",
               getevent name: "hyn_ts"                      <-- ACTIVE ON TESTED UNIT
NOT PRESENT    display-ids.txt shows exactly ONE display:
               Display 4627039422300187648 (HWC display 0) port=0 pnpId=MTK
               -> the rear panel is NOT registered with SurfaceFlinger
NOT PRESENT    no device-tree config, no HAL, no framework exposure,
               no touch routing, no brightness/power path in this tree
```

**Correct labelling:**

```text
rear touch    IDENTIFIED + RUNTIME-VALIDATED (as a raw input device)
rear display  IDENTIFIED only — NOT CONFIGURED, NOT BUILT, NOT RUNTIME-PROVEN
```

**Recommended action:** Do not describe the rear display as implemented. The
brief's exact warning applies. Route: kernel panel driver → DRM connector →
HWC display → framework `DisplayManager` → touch association. None of these
links is established.

## DT-LED-001 — warning lights have an identified path; the work light does not

```text
ID:          DT-LED-001
Severity:    LOW
Category:    X. LEDs / work light / warning lights / keys
Status:      partly CONFIRMED, partly UNKNOWN
```

**Evidence:** `/sys/class/leds` is unreadable by shell on enforcing stock
(`leds.txt` is 0 bytes in the stock snapshot) but fully readable in the
recovery snapshot:

```text
/sys/class/leds/red
/sys/class/leds/green      -> all three at .../11d71000.i2c/i2c-11/11-0045/leds/
/sys/class/leds/blue
/sys/class/leds/lcd-backlight     <-- confirms TW_BRIGHTNESS_PATH in BoardConfig.mk
/sys/class/leds/vibrator          <-- confirms the brightness-only vibrator (commit 7976adc)
```

The `blue` node exposes charger/gauge triggers
(`primary_chg-online`, `battery-charging`, `sc-cp-master-online`, …).

```text
red/blue/green warning lights   CONTROL PATH IDENTIFIED (sysfs), framework routing UNVERIFIED
work light                      NO /sys/class/leds node found — path NOT identified
                                (YftOutdoorLightUlefone.apk and YftTorch.apk exist;
                                 APK existence is not a control path)
programmable keys               yft_gpio_keys.ko present; keylayout mapping not verified
```

**Recommended action:** Claim the warning lights only as far as sysfs. Leave the
work light UNKNOWN until a node or driver is found.

## DT-RUNTIME-001 — subsystems that remain runtime-unproven

```text
ID:          DT-RUNTIME-001
Severity:    INFO
Category:    17. Runtime validation
Status:      UNKNOWN — legitimately
```

Per the brief, these are **not** counted against the tree. Recording them so the
boundary stays explicit:

```text
main display refresh/HBM/doze    rear display        rear touch (as a display)
ThermoVue thermal imaging        all cameras         night vision / IR
fingerprint                      NFC (stack)         GNSS       Wi-Fi      Bluetooth
SIM/RIL   5G   IMS   VoLTE   VoWiFi                  audio routes   headset jack
microphones     sensors          battery telemetry   120 W charging
reverse charging                 USB OTG             MTP (partially proven in recovery)
work light      warning lights   programmable keys   suspend/wake
thermal throttling               OTA                 fastbootd
```

The tree does **not** claim any of these are proven. `TODO.md` is explicit:
"Everything listed here is unverified, not known-broken. Nothing in this file
should be described as working until it has been exercised on hardware."

## DT-BAT-001 — charging topology is mapped, electrical behaviour is not

```text
ID:          DT-BAT-001
Severity:    MEDIUM
Category:    U. Battery / charging
Status:      UNKNOWN
```

**Confirmed from live evidence** (`power-supply.txt`), and correctly reflected
in `sepolicy/vendor/genfs_contexts` with per-device paths rather than a broad
sysfs label:

```text
battery              mt6375 gauge   .../11280000.i2c/i2c-5/5-0034/…:mtk-gauge/    type=Battery
3rd-gauge            secondary      .../11c24000.i2c/i2c-9/9-0055/
primary_chg          mt6375 chg     .../11280000.i2c/i2c-5/5-0034/…:chg/
mtk-master-charger   + mtk-mst-div-chg, mtk-mst-hvdiv-chg, mtk-slave-charger,
                       mtk-slv-div-chg, mtk-slv-hvdiv-chg  (all /devices/platform/charger/)
sc-cp-master         charge pump    .../11d71000.i2c/i2c-11/11-0066/
sc-cp-slave          charge pump    .../11e01000.i2c/i2c-6/6-0067/
usb_type advertised  [Unknown] SDP DCP CDP PD PD_PPS
```

**Unknown:** design capacity, cell topology, per-rail current limits, the actual
120 W negotiation path, thermal limit tables, reverse-charging/OTG power
control. None of this can be derived offline, and none is hardcoded in the tree
— which is correct behaviour, not a gap.

**Recommended action:** Keep claiming topology only. Do not import 120 W from
marketing material.

---

# SAFETY ISSUES

```text
SAFE-001  No device-unique or mutable calibration state is redistributed.
          Verified by regex sweep of all 1814 entries (DT-Z-001). CLEAN.

SAFE-002  No stock SELinux policy binaries are shipped (grep count: 0). CLEAN.

SAFE-003  No Ulefone private signing material is present. BoardConfigRom.mk
          explicitly forbids fabricating it. CLEAN — but see DT-AVB-001: the
          absence of project keys means test-key signing by default.

SAFE-004  ro.product.*_for_attestation are EMPTY on real stock. The Pixel 9 Pro
          values seen live come from a spoofing module (DT-EVID-001). Do NOT
          carry them into the ROM: that would be shipping deliberate attestation
          spoofing in a public tree.

SAFE-005  No modem NV, Wi-Fi/BT per-unit calibration, TEE state, keybox or
          certificate material in the extraction. CLEAN.

SAFE-006  DT-ELF-001's fix list touches only static vendor libraries already
          present in the stock firmware. Adding them raises no new
          redistribution concern beyond the existing 1814 entries.
```

---

# BUILD RISKS

```text
BR-001  HIGH    DT-ELF-001. Adding 90 paths will surface new Soong/Make
                duplicate-output or ELF-prebuilt conflicts, especially for the
                lib64/mt6878 platform-subdir variants. Expect iteration.
BR-002  HIGH    DT-AVB-001. Release builds silently use the AOSP test key.
BR-003  MEDIUM  DT-ROM-001. No ROM base exists in this checkout; the full-ROM
                m nothing pass is not transferable evidence.
BR-004  MEDIUM  DT-VABC-001. VABC not configured; OTA metadata will diverge.
BR-005  LOW     Host LEX/flex mismatch breaks both products on this machine
                until LEX is overridden. Environmental, but undocumented.
BR-006  LOW     BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES := true is set for
                the full ROM. Acknowledged in-file as future hardening. It
                suppresses exactly the class of check that would have caught
                DT-ELF-001 earlier.
BR-007  LOW     .work/ (7.2 GB) sits inside the device tree. Protected only by
                a .find-ignore marker that vendorsetup.sh recreates. If that
                marker is lost, Soong scans it and aborts on duplicate modules.
                Documented in TODO.md §4.
```

---

# RUNTIME RISKS

```text
RR-001  CRITICAL  DT-ELF-001. Full ROM loses boot control, cameras, HW video
                  codecs, modem init, GNSS, NNAPI, TEE storage proxy and all
                  three Ulefone ODM HALs at dynamic-link time.
RR-002  HIGH      DT-SEC-001. Full ROM gets labelled-but-unauthorised
                  TrustKernel: no KeyMint/Gatekeeper/Keystore2 HW backing,
                  therefore no FBE unlock.
RR-003  HIGH      DT-FP-001. No fingerprint HAL path exists in the extraction;
                  VINTF declares the AOSP virtual instance.
RR-004  MEDIUM    DT-AOSP-001. face/IR/fingerprint declared in VINTF but backed
                  by AOSP virtual HALs. Framework will advertise capabilities
                  that do not exist in hardware terms.
RR-005  MEDIUM    DT-VABC-001. VAB OTA without compression against a device
                  configured for VABC.
RR-006  LOW       Recovery inherits virtual_ab_ota.mk unconditionally via
                  device.mk. Defensible for a VAB device (snapuserd/e2fsck
                  needed), but it is shared config crossing the recovery
                  boundary and should be a conscious, documented choice.
RR-007  LOW       Documented and accepted in TODO.md: ~40 s USB drop after PIN,
                  cosmetic /auto0 mount error, post-install vibration no-op,
                  two benign enforcing denials (hal_health / hal_bootctl on
                  rootfs dir). I independently agree these are correctly
                  triaged and correctly left alone.
```

---

# FILES REVIEWED

```text
device/ulefone/gq5012bf1/
  BoardConfig.mk                BoardConfigRom.mk           device.mk
  lineage_gq5012bf1.mk          twrp_gq5012bf1.mk           AndroidProducts.mk
  proprietary-files.txt         aosp-replaced-files.txt     TODO.md
  extract-files.py              setup-makefiles.py          vendorsetup.sh
  .gitignore
  sepolicy/vendor/{trustkernel.te,file.te,file_contexts,genfs_contexts,
                   property.te,property_contexts}
  recovery/root/system/etc/recovery.fstab
  recovery/root/lib/modules/focaltech_touch_spi_ft3680.ko
  prebuilt/{kernel,dtbo.img,dtbs/stock.dtb}
  tools/{README.md,audit_device_tree.py,inventory_device.py,
         generate_proprietary_candidates.py,vbunpack.py,vbrepack.py}
  docs/ (16 files, spot-checked)

vendor/ulefone/gq5012bf1/
  Android.bp  BoardConfigVendor.mk  gq5012bf1-vendor.mk
  proprietary/**  (1814 files; 1461 ELF objects parsed)

evidence:
  gq5012bf1-live-stock-20260831-113332/     (34 files)
  gq5012bf1-live-recovery-20260831-113044/  (25 files)
  gq5012bf1-fastboot-getvar-all.txt
  gq5012bf1-artifacts/build36/vendor_boot_a-orangefox-FULL64M-BUILD36.img
  .../Ka as turiu/…GQ5012BF1_EEA_V15_user_20251022/vendor_boot.img
  .work/gq5012bf1/stock/partitions/  (7 partitions, 7568 files)
```

---

# COMMANDS RUN

```bash
# git
git status --short; git log --oneline --decorate -30; git branch -vv
git show --stat 8376139 ec460e8 75d3c41 7976adc 407d8ec
git ls-files | wc -l; git check-ignore -v .work __pycache__/…

# integrity
sha256sum gq5012bf1-live-{recovery,stock}-*.tar.gz          # both match the brief
sha256sum recovery/root/lib/modules/focaltech_touch_spi_ft3680.ko

# extraction analysis (python, in-sandbox)
#   parse proprietary-files.txt / aosp-replaced-files.txt
#   index vendor/proprietary + 7 extracted stock partitions
#   duplicate / orphan / missing / partition-prefix checks
#   device-unique + calibration + secret regex sweep

# ELF dependency graph (python, custom PT_DYNAMIC/DT_NEEDED parser)
#   1461 ELF objects; provider index; unresolved classification;
#   transitive closure -> /tmp/missing_blobs.txt (90 paths)

# init / VINTF
#   120 services from retained *.rc resolved against blobs u aosp
#   55 VINTF fragments parsed (166 hal entries)

# vendor_boot (python struct parser)
#   header v4 fields, ramdisk table, fragment sha256, dtb sha256, AVB footer
#   stock vs build36 comparison

# build validation
source build/envsetup.sh
lunch twrp_gq5012bf1-ap2a-eng          && m nothing     # fails on host LEX
LEX=<soong prebuilt flex> m nothing                      # PASSES (02:25)
lunch lineage_gq5012bf1-ap2a-userdebug
LEX=<soong prebuilt flex> m nothing                      # PASSES (02:33)

# tooling determinism
python3 tools/audit_device_tree.py --device . --inventory … --out /tmp/audit1.md
python3 tools/audit_device_tree.py --device . --inventory … --out /tmp/audit2.md
cmp /tmp/audit1.md /tmp/audit2.md                        # identical

# device
adb devices -l; fastboot devices; lsusb                  # NO DEVICE PRESENT
```

---

# RECOMMENDED CHANGES

Ordered by value. **None of these were applied** — per the brief, this audit
establishes what is right and wrong first.

```text
1. DT-ELF-001  Add the 90 missing proprietary paths (list at /tmp/missing_blobs.txt),
               then re-run the closure to fixpoint.
2. DT-ELF-001  Add a DT_NEEDED closure check to tools/audit_device_tree.py.
               Highest-leverage change in the whole tree: it converts a class of
               silent runtime failure into a build-time error.
3. DT-SEC-001  Split trustkernel.te: recovery-specific grants stay inside
               recovery_only(); device/file/property access moves outside.
4. DT-EVID-001 Amend docs/evidence-sources.md with the split source-of-truth
               rule (firmware wins for identity, live snapshot wins for
               hardware topology) and record the KernelSU contamination.
5. DT-AVB-001  Add BOARD_AVB_*_KEY_PATH / _ALGORITHM, or a guard that fails
               release builds when they are unset.
6. DT-FP-001   Restate fingerprint as "transport madev, family Microarray,
               model UNKNOWN, no HAL path present."
7. DT-THERM-001 Downgrade ThermoVue to UNKNOWN; drop "AC020" until a node,
               driver or library string supports it.
8. DT-CAM-001  Downgrade IMX989 to name-string identification; record 4 IDs /
               3 enumerated sensors; bind IDs to v4l-subdev + DTB addresses.
9. DT-VABC-001 Inherit the VABC product makefile for the full ROM only.
10. DT-BUILD-001 Document the host LEX/flex override in build-gq5012bf1.sh.
11. DT-INIT-002 Re-label the stale allocator-V1 rc inside the WARN bucket.
12. DT-AOSP-001 Annotate the four AOSP stub HALs as "capability not implied".
13. DT-ROM-001 State in docs/build-status.md that the full ROM is
               BUILD-PARSE-VALID only.
```

---

# NO-CHANGE FINDINGS

Things that are correct and that a well-meaning refactor might otherwise break:

```text
- allow tee tkcore_protect_data_file:file link;      DO NOT DELETE (DT-SEC-002)
- persist_data_file / protect_f_data_file types      DO NOT replace with unlabeled
- TW_EXCLUDE_DEFAULT_USB_INIT := true                DO NOT restore legacy android_usb
- TW_MTP_DEVICE := /dev/usb-ffs/mtp/ep0              FunctionFS is the only working path
- teed -> KeyMint -> Gatekeeper -> Keystore2         DO NOT reintroduce the 90 s delay
- fileencryption / keydirectory / fscrypt v2         DO NOT weaken
- stock PLATFORM fragment + stock DTB                byte-identical; DO NOT regenerate
- zero SELinux binaries in the extraction            correct; DO NOT "fix" by extracting
- the 10 dead init paths                             correct as WARN; DO NOT fabricate files
- TARGET_COPY_OUT_VENDOR := vendor                   the in-file rationale is accurate
- alternate-BOM touch controllers (Ilitek, Chipone)  DO NOT delete; DO NOT mark active
- vibrator as a brightness-only LED node             correctly handled by 7976adc
- the four TODO.md known defects                     correctly triaged and left alone
- BOARD_SUPER_PARTITION_SIZE / BOARD_MAIN_SIZE       verified against the bootloader
- PRODUCT_MODEL := Armor 29 Pro                      verified against stock build.prop
- PRODUCT_SHIPPING_API_LEVEL := 35 + its guard       verified against real firmware
```

---

# ALTERNATE-BOM CLASSIFICATION

```text
ACTIVE ON TESTED UNIT
  FocalTech FT3680     SPI3, fts_ts, focaltech_touch_spi_ft3680.ko, module hash verified
  Hynitron             I2C, hyn_ts, hynitron.ko — live input device (rear touch)
  ST21NFC              I2C, st21nfc driver + st21nfc module loaded on stock
  mt6375 gauge/charger + sc8571-class charge pumps (sc-cp-master/slave)
  madev fingerprint transport (/dev/madev0)

SUPPORTED ALTERNATE BOM
  Ilitek touch, Chipone touch  (retained; inactive on this unit — correctly kept)

DEAD / FACTORY PATH
  10 vendor-rooted init references (DT-INIT-001), of which 4 are alternate-BOM
  fingerprint HALs (btlfpserver, fptool@2.0, sw@1.0, focatech@1.0), 1 is a
  32-bit boringssl self-test on a 64-bit-only device, 1 is a stale gralloc V1 rc
  (DT-INIT-002), and 4 are meta/factory daemons.
  Plus ~12 further /system-rooted dead references outside the tool's scope.

UNKNOWN
  4th back-facing camera ID           ThermoVue / M170infisens binding
  work light control path             rear DISPLAY (panel/HWC/framework)
```

---

# QUANTITATIVE SUMMARY

```text
CONFIRMED:     14
QUESTIONABLE:   7
WRONG:          5
UNKNOWN:        4
                --
TOTAL:         30 findings
```

```text
CRITICAL:  2      (DT-ELF-001, DT-EVID-001)
HIGH:      6      (DT-SEC-001, DT-ROM-001, DT-FP-001, DT-THERM-001,
                   DT-AVB-001, + RR-001/002 aggregated)
MEDIUM:    6      (DT-CAM-001, DT-VABC-001, DT-AOSP-001, DT-DISP-001,
                   DT-BAT-001, BR-003)
LOW:       5      (DT-INIT-001, DT-INIT-002, DT-LED-001, DT-DOOGEE-001, RR-007)
INFO:     11      (DT-VB-001, DT-EXT-001, DT-SEC-002, DT-FBE-001, DT-USB-001,
                   DT-HW-001, DT-BUILD-001, DT-GIT-001, DT-TOOL-001,
                   DT-ID-001, DT-API-001, DT-SUPER-001, DT-Z-001,
                   DT-RUNTIME-001)
```

## Comparison against the prior result

```text
PRIOR:  16 PASS · 1 WARN · 0 FAIL
MINE:   agree on 16 · agree on the WARN (reconciled exactly) · DISAGREE on 0 FAIL
```

**Where I agree** — all 16 of the prior tool's PASS checks reproduce, and I
independently verified the substantive ones rather than trusting the tool:

```text
full-product · extraction · proprietary-list (1814) · aosp-replacements (198)
ab-ota · dynamic-partitions · metadata · fbe-v2 · trustkernel-model
trustkernel-order · trustkernel-link · usb-configfs · bootcontrol-misc
vintf-coverage (55/55) · module-coverage (215/215) · init-executable-coverage (113/113)
```

I also independently confirmed things the tool does **not** check: byte-level
vendor_boot/DTB equality, the FT3680 module hash, super size against the
bootloader, shipping API level against real firmware, git cleanliness, tooling
determinism, and both `m nothing` builds.

**Where I agree on the WARN:** the "10 dead init paths" figure is exactly right.
My independent enumeration of 120 services produced 26 unresolved executables,
of which precisely 10 are vendor-rooted. That is a genuinely well-calibrated
warning. My only quibble is the classification of one entry (DT-INIT-002).

**Where I disagree — `0 FAIL` is not supportable:**

```text
DT-ELF-001  CRITICAL  46 first-order / 81 transitive proprietary libraries missing.
                      The tool measures list-to-stock path existence, never closure,
                      so this defect is structurally invisible to it. This is the
                      exact trap the brief named: "Do not assume 'zero missing
                      files' means 'correct list'."
DT-SEC-001  HIGH      trustkernel.te is entirely recovery_only() while its labels
                      are not. The tool's trustkernel-link check greps for the
                      rule's presence, not its reachability from a full-ROM build.
DT-EVID-001 CRITICAL  Not a tree defect at all — a defect in the evidence base
                      that the brief ranks #1. Out of the tool's scope by design,
                      but it undermines any identity claim built on that snapshot.
```

Two of the three are invisible to the existing tooling by construction, which is
the honest explanation for the `0 FAIL`: the tool is well-built and deterministic,
but it checks *presence*, not *closure* or *reachability*.

---

# FINAL VERDICT

```text
RECOVERY TARGET (twrp_gq5012bf1)                    PRODUCTION QUALITY

  The security work is real and provable. vendor_boot is byte-exact against
  stock. FBE, TrustKernel, SELinux-enforcing, USB/configfs and the touch stack
  are all evidence-backed rather than assumed. The known defects are correctly
  triaged, honestly documented, and deliberately left alone for good reasons.
  I found nothing in the recovery path that I would call wrong.

FULL ROM TARGET (lineage_gq5012bf1)                 SKELETON — NOT BOOTABLE

  It parses. That is all m nothing proves, and on this checkout it proves it
  against a product with no ROM base at all. Before any boot attempt:
  DT-ELF-001 (dependency closure) and DT-SEC-001 (recovery_only policy) are
  blocking. DT-AVB-001 and DT-VABC-001 are blocking for a releasable image.

EVIDENCE BASE                                       PARTIALLY COMPROMISED

  The live "stock" snapshot is from a KernelSU device with an active property-
  spoofing module. Hardware topology from it remains trustworthy; identity,
  version and property data from it does not. The brief's priority ordering
  needs amending, and the archived snapshot should be re-labelled so nobody
  later treats ro.build.version.sdk=36 or a Pixel 9 Pro attestation identity as
  a fact about this device.

OVERALL

  This is careful, honest work with one significant blind spot. The tree
  consistently under-claims in its own documentation — TODO.md in particular is
  a model of restraint — and the single largest defect (DT-ELF-001) is not a
  failure of rigour but a failure of the *metric*: "zero missing files" was
  measuring the wrong property, confidently and reproducibly, for 1814 entries.
  Fixing the metric is worth more than fixing the 90 paths.

  A truthful WARN is better than a fake PASS. This tree earned most of its
  PASSes. It did not earn 0 FAIL.
```
