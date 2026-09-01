# LineageOS structure normalization — Ulefone Armor 29 Pro Thermal / GQ5012BF1

Structural refactor of `device/ulefone/gq5012bf1` into the layout and
implementation pattern of an official modern LineageOS device tree.

This was a **structural** change. No hardware configuration was redesigned, no
verified MT6878/Ulefone value was replaced with a generic MediaTek default, and
no new runtime claim is made anywhere in this document.

---

## BEFORE

```text
device/ulefone/gq5012bf1/
├── AndroidProducts.mk           lineage_ + twrp_ products, lunch combos
├── BoardConfig.mk               arch, boot image, GKI, partitions, recovery UI,
│                                  TW_* block, sepolicy dir, include BoardConfigRom.mk
├── BoardConfigRom.mk            parallel full-ROM board config (EROFS, super, AVB)
├── device.mk                    30 lines: two inherits, dynamic partitions,
│                                  three DLKM image flags, namespace, Treble
├── lineage_gq5012bf1.mk         product bases + VINTF/API level + identity
├── twrp_gq5012bf1.mk            recovery product
├── proprietary-files.txt        1,891 paths, evidence in inline `# ...` comments
├── aosp-replaced-files.txt      205 stock paths owned by AOSP modules
├── extract-files.py             custom extractor (adb/dir copy loop)
├── setup-makefiles.py           custom vendor makefile generator
│                                  (hand-written Android.bp, BoardConfigVendor.mk,
│                                   *-vendor.mk, DEVICE_MANIFEST_FILE, AOSP module list)
├── sepolicy/vendor/             TrustKernel, battery genfs, file/property contexts
├── recovery/root/               fstab, recovery rc, FT3680 module, helper scripts
├── prebuilt/                    kernel, dtbo.img, stock.dtb
├── patches/                     bootable_recovery + system_sepolicy patches
├── tools/                       inventory, audit, ELF closure, snapshot trust, vb*
├── docs/                        subsystem evidence documents
└── *.md                         CODEX, audits, findings, TODO, README
```

No `Android.bp`, no `lineage.dependencies`, no `vintf/`. VINTF, blob install
rules and AOSP module ownership were all produced by device-tree Python code.

## AFTER

```text
device/ulefone/gq5012bf1/
├── Android.bp                   soong_namespace
├── AndroidProducts.mk           unchanged (product makefiles + lunch combos)
├── BoardConfig.mk               single board contract, full-ROM section guarded
├── device.mk                    subsystem-organized runtime integration
├── lineage_gq5012bf1.mk         inheritance + product identity only
├── twrp_gq5012bf1.mk            recovery product (unchanged)
├── lineage.dependencies         [] — no external Lineage device dependency
├── proprietary-files.txt        extract-utils syntax, 1,891 stock paths
├── aosp-replaced-files.txt      211 stock paths owned by AOSP/ROM modules
├── extract-files.py             ExtractUtilsModule + blob_fixups + lib_fixups
├── setup-makefiles.py           #!./extract-files.py --regenerate_makefiles
├── vintf/                       device manifest, dsds manifest, 3 merged fragments
├── sepolicy/vendor/             unchanged (byte-identical)
├── recovery/root/               unchanged (recovery-only, byte-identical)
├── prebuilt/                    unchanged
├── patches/                     unchanged (recovery source patches)
├── tools/                       unchanged responsibilities, parsers updated
├── docs/                        unchanged except blob-map.md
└── *.md                         unchanged + this report
```

---

## FILES MOVED

| From | To | Reason |
|---|---|---|
| `BoardConfigRom.mk` (whole file) | `BoardConfig.mk`, guarded full-ROM section | one obvious place for board configuration |
| `setup-makefiles.py` AOSP module list | `device.mk` subsystem sections | hand-owned integration is not extraction output |
| `setup-makefiles.py` `DEVICE_MANIFEST_FILE`/`ODM_MANIFEST_FILES` emission | `BoardConfig.mk` + `vintf/` | VINTF belongs in the board contract and a visible directory |
| stock `vendor/etc/vintf/manifest.xml` | `vintf/manifest.xml` | build/make forbids VINTF metadata in `PRODUCT_COPY_FILES` |
| stock `vendor/odm/etc/vintf/manifest_dsds.xml` | `vintf/manifest_dsds.xml` | same |
| stock `cas-service` / `fingerprint-example` / `gnss-default` fragments | `vintf/` | AOSP defines modules with those exact names |

No file was moved for aesthetics. `sepolicy/`, `recovery/`, `prebuilt/`,
`patches/`, `tools/` and `docs/` keep their existing locations because Lineage
would keep them there too.

## FILES REMOVED

```text
BoardConfigRom.mk          merged into BoardConfig.mk
```

Nothing else was deleted. No audit tool, document, recovery asset or policy file
was removed.

## FILES ADDED

```text
Android.bp                              soong_namespace {}
lineage.dependencies                    []
vintf/manifest.xml                      verbatim stock vendor manifest
vintf/manifest_dsds.xml                 verbatim stock odm dual-SIM manifest
vintf/android.hardware.cas-service.xml  verbatim stock fragment
vintf/fingerprint-example.xml           verbatim stock fragment
vintf/gnss-default.xml                  verbatim stock fragment
LINEAGE_STRUCTURE_REPORT.md             this report
```

## BOARD CONFIG CHANGES

`BoardConfig.mk` is now the only board contract, with commented sections:

```text
Architecture · Platform · Kernel · Android boot image v4 · GKI/vendor_boot ·
Partitions · Ramdisk · Filesystems · Recovery UI/debugging (twrp_ guarded) ·
SELinux · VINTF · Full-ROM partitions and AVB (full-ROM guarded)
```

* Every verified value is unchanged: boot header v4, the four explicit mkbootimg
  offsets, `bootopt=64S3,32N2,64N2`, LZ4 ramdisks, the A/B partition list, the
  metadata partition, the recovery fstab path, the panel geometry, all TW_*
  values, the OrangeFox plugin allowlist and the FBE flags.
* Moved in from `BoardConfigRom.mk` unchanged: `TARGET_COPY_OUT_*`, the seven
  EROFS filesystem types, `lz4hc,9` / 256 KiB pcluster, super size 9663676416,
  group `main` 9661579264 with its seven partitions, and the stock vbmeta split
  with rollback index locations 1 and 2.
* Added to the full-ROM section: `DEVICE_MANIFEST_FILE`, `ODM_MANIFEST_FILES`,
  `BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES` (previously in
  `BoardConfigRom.mk`) and the generated `BoardConfigVendor.mk` include.
* `BOARD_VENDOR_SEPOLICY_DIRS` is unchanged in effect; only the literal path was
  replaced by `$(DEVICE_PATH)`. It stays **unguarded**, which is what keeps the
  TrustKernel labels present in both policies.

No `BoardConfigDevice.mk`, `BoardConfigPlatform.mk` or common tree was created.

## DEVICE.MK ORGANIZATION

Shared, unguarded (recovery inherits exactly what it inherited before):

```text
A/B (virtual_ab_ota) · Internal storage (emulated_storage) · Partitions
(PRODUCT_USE_DYNAMIC_PARTITIONS) · Soong namespaces · Treble override
```

Full-ROM only, behind the existing `twrp_` guard, in Lineage section order:

```text
API · Boot control · Camera · DRM · Fingerprint/face · GNSS · Health · IR ·
Partitions (DLKM images) · Sensors · Telephony · USB · VINTF · Wi-Fi ·
Shipping API level · Proprietary
```

The 38 AOSP modules that own a stock path now live in the subsystem section they
belong to instead of being appended to generated vendor output, and the file
ends with:

```make
$(call inherit-product, vendor/ulefone/gq5012bf1/gq5012bf1-vendor.mk)
```

No TWRP/OrangeFox variable appears in `device.mk`.

## PRODUCT MAKEFILE CHANGES

`lineage_gq5012bf1.mk` keeps only inheritance and identity. `PRODUCT_MODEL`
remains **`Armor 29 Pro`** — the model TrustKernel/KeyMint was verified with —
and the marketing "Thermal" name is still deliberately absent.
`PRODUCT_ENFORCE_VINTF_MANIFEST` and the `PLATFORM_SDK_VERSION`-guarded
`PRODUCT_SHIPPING_API_LEVEL := 35` moved to `device.mk` so they sit with the
runtime integration; their effect is unchanged. The LieppOS/Lineage phone-base
fallback is retained, and `twrp_gq5012bf1.mk` is untouched.

## EXTRACTION FRAMEWORK CHANGES

The canonical LineageOS path is now in place:

```text
extract-files.py    ExtractUtilsModule('gq5012bf1', 'ulefone', blob_fixups=…,
                                       lib_fixups=…, namespace_imports=…,
                                       check_elf=False)
setup-makefiles.py  #!./extract-files.py --regenerate_makefiles
```

`proprietary-files.txt` was converted to extract-utils syntax with no loss:

| Property | Before | After |
|---|---|---|
| Accounted stock paths | 1,891 | **1,891** |
| List entries | 1,891 | 1,554 |
| `SYMLINK=` aliases (stock symlinks) | 0 (duplicated content) | 337 |
| `EXTRACT_ONLY` (accounted, not installed) | implicit in generator code | 246 |
| `MAKE_COPY_RULE_ONLY` (app-bundled JNI) | implicit | 29 |
| Evidence comments | inline after the path | on the preceding line |

Inline comments had to move: `;` and `:` are argument and destination separators
in this format, and 63 evidence comments contained `;`.

The 205 AOSP-replaced paths are now expressed as `EXTRACT_ONLY` entries instead
of being filtered inside generator code. Six paths were **added** to
`aosp-replaced-files.txt` (211 total): the VINTF fragments of drm-clearkey, ir,
health, sensors-multihal, wifi and the Bluetooth audio provider are installed by
the AOSP/ROM modules that implement those HALs, and shipping the stock copies
too collided on the same install target. This was proven by the build, not
assumed.

`check_elf=False` is deliberate and documented in `extract-files.py`: the stock
payload is an Android 15 image whose `DT_NEEDED` closure references vendor AIDL
versions (`camera.common-V2`, `biometrics.common-V4`, …) that are not source
modules on every branch this tree is parsed in. Blobs install at their exact
stock paths — the state `tools/elf_closure.py` audits. Enabling it is future
hardening for the target Android 15 branch.

Generated output (`vendor/ulefone/gq5012bf1/`, outside this repository) is now
produced entirely by extract-utils:

```text
1,987 proprietary files
  337 install_symlink modules      stock symlinks, no duplicated content
   41 prebuilt_etc_xml modules     per-HAL VINTF fragments, stock layout
   21 android_app_import modules   presigned APKs
1,246 PRODUCT_COPY_FILES rules     exact stock paths
```

## INIT/ROOTDIR CHANGES

None, deliberately. The full ROM ships no device-tree init file: every stock
`init*.rc`, `ueventd.rc` and fstab comes from the vendor payload. The only init
assets in the tree are recovery-only and stay under `recovery/root/`, which is
where the OrangeFox ramdisk staging expects them. Creating a `rootdir/` with an
`Android.bp` would have produced a second, empty init tree.

## VINTF CHANGES

```text
vintf/manifest.xml                       -> DEVICE_MANIFEST_FILE
vintf/manifest_dsds.xml                  -> ODM_MANIFEST_FILES
vintf/android.hardware.cas-service.xml   -> DEVICE_MANIFEST_FILE
vintf/fingerprint-example.xml            -> DEVICE_MANIFEST_FILE
vintf/gnss-default.xml                   -> DEVICE_MANIFEST_FILE
vendor/etc/vintf/manifest/*.xml (41)     -> generated prebuilt_etc_xml modules
manifest_ss/tsts/qsqs.xml                -> EXTRACT_ONLY, evidence only
```

The four assembled/merged manifests are build inputs — `build/make` rejects
VINTF metadata in `PRODUCT_COPY_FILES` — and the three named fragments are
merged because AOSP defines modules with those exact names. The remaining 41
per-HAL fragments keep the stock `vendor/etc/vintf/manifest/` layout, which is
closer to stock than the previous single assembled manifest.

Offline coverage is unchanged: **55/55 stock vendor/odm manifest documents
accounted, 0 static coverage errors**.

## SELINUX CHANGES

**None.** `git diff` over `sepolicy/` is empty; all six files are byte-identical.
The TrustKernel split (34 common statements, 22 recovery-only, 0 speculative
ROM-only rules), `persist_data_file`, `protect_f_data_file`, the `tkcore_*`
types, RPMB types, TrustKernel properties and the BootControl `misc` labeling are
untouched, and policy remains enforcing.

Verified by compiling both products after the refactor:

```text
recovery sepolicy.recovery  sha256 bcc760fe38c76c1d4190b456979d6dd8…  BYTE-IDENTICAL
                                    to the recorded verified baseline
full ROM vendor_sepolicy.cil        (allow tee_202404 tkcore_protect_data_file (file (link)))  PRESENT
full ROM vendor_sepolicy.cil        locksettings_key / vold_key rules             ABSENT (0)
```

## OVERLAY CHANGES

None. The device has no resource override that evidence justifies today, so no
`overlay/`, `overlay-lineage/` or RRO package was invented. When an override is
proven necessary, it belongs in a named RRO package (for example
`FrameworksResGq5012bf1`) under `overlay/`.

## RECOVERY ISOLATION

* `twrp_gq5012bf1.mk` is unchanged and still inherits `device.mk`; the guard
  means it receives only the shared board/storage contract.
* All TW_*/OrangeFox/`ALLOW_MISSING_DEPENDENCIES`/plugin configuration stays in
  the `twrp_`-guarded section of `BoardConfig.mk`; none of it reaches the ROM.
* All full-ROM package, VINTF, AVB, super and EROFS configuration is behind the
  inverse guard; none of it reaches recovery.
* `recovery/root/`, `patches/` and `vendorsetup.sh` are byte-identical.
* Genuinely shared items — `sepolicy/vendor/`, `prebuilt/`, the recovery fstab
  reference, panel geometry — remain shared rather than forked.

Recovery asset tree hash before and after: `fd83d3d5e3c49707…` (unchanged).

## VALIDATION

All results below are from this workspace, after the refactor.

```text
Proprietary extraction (stock partitions, extract-utils):
  accounted stock paths          1,891   (1,554 entries + 337 symlink aliases)
  extraction errors                  0
  generated vendor files         1,987
Determinism:
  two consecutive setup-makefiles runs   BYTE-IDENTICAL (all four outputs)
Device audit (tools/audit_device_tree.py):
  PASS 18 · WARN 2 · FAIL 1      identical to the pre-refactor baseline
  proprietary-list               1,891 entries
  aosp-replacements              211 stock paths inherited from AOSP modules
  vintf-coverage                 55/55 stock vendor/odm manifests
  module-coverage                215/215 stock DLKM modules
  init-executable-coverage       113/113 present vendor/odm init executables
  trustkernel-link/-rom-scope    PASS
  usb-configfs, bootcontrol-misc PASS
  fbe-v2, metadata, ab-ota       PASS
  dead-init-references           WARN — 10 factory/alternate-BOM paths (expected)
  snapshot-trust                 WARN — pre-existing, see below
  elf-closure                    FAIL — pre-existing, see below
SELinux:
  m selinux_policy (twrp_gq5012bf1)      PASS
  m selinux_policy (lineage_gq5012bf1)   PASS
  recovery policy byte regression        0
Build parsing:
  lineage_gq5012bf1-ap2a-userdebug  m nothing   PASS
  twrp_gq5012bf1-ap2a-eng           m nothing   PASS
```

### The two carried-over problems, not hidden

1. **`elf-closure` FAIL — 27 unresolved required dependencies.** Reproduced
   identically on the pre-refactor tree (`HEAD` in a clean worktree, same
   inventory, same stock payload, same command): **18 PASS / 2 WARN / 1 FAIL,
   27 unresolved**. Every one of the 27 is an Android 15 AOSP `system/lib64`
   library (`audioflinger-aidl-cpp.so`, `audio-permission-aidl-cpp.so`,
   `libaconfig_storage_read_api_cc.so`, `libtinyalsa.so`, …) that exists in the
   stock image but is not a Soong module in this Android 14 recovery checkout,
   so the resolver cannot classify it as ROM-provided. The recorded
   "0 required unresolved" result was produced against an Android 15 resolution
   source. This refactor neither caused nor fixed it; it must be re-measured on
   the target Android 15 branch.
2. **`snapshot-trust` WARN.** The contaminated live snapshot in the untracked
   `.work/` analysis workspace has no adjacent `TRUST.md`. Also reproduced on
   the pre-refactor tree. It is a workspace artifact, not a tree defect, and
   `tools/snapshot_trust.py` still correctly refuses to treat the snapshot's
   identity/attestation properties as authoritative.

The ten factory/alternate-BOM init references remain a WARN, as expected.

## KNOWN DIFFERENCES FROM OFFICIAL LINEAGE STYLE

1. **`twrp_gq5012bf1.mk`, `vendorsetup.sh`, `patches/`, `recovery/root/`** —
   official trees have no OrangeFox product. Kept: this is the historically
   verified, hardware-tested target, and it is isolated behind guards.
2. **`tools/` and the audit/report Markdown at tree root** — official trees are
   leaner. Kept per the project's research value; none of it participates in the
   build, and the tree reads correctly if a maintainer ignores `tools/` and
   `docs/`.
3. **`aosp-replaced-files.txt`** — not a Lineage file. It is the evidence record
   behind the `EXTRACT_ONLY` markers and the `device.mk` AOSP module requests,
   and it is what `tools/audit_device_tree.py` audits against.
4. **`check_elf=False`** — most official trees generate typed ELF prebuilts with
   link metadata. Justified above; the alternative is unbuildable outside the
   target Android 15 branch and changes nothing about installed content.
5. **`prebuilt/kernel` + `prebuilt/dtbo.img`** — official trees usually build a
   kernel from source. The stock GKI is deliberate for this bring-up stage.
6. **No `configs/`, `overlay/`, `overlay-lineage/`, `props/`, `rootdir/`** — the
   device currently has no device-tree-owned config, overlay, property or init
   file. Empty directories were not created to match a sketch.
7. **`lineage.dependencies` is `[]`** — there is no external Lineage device
   dependency and no `mt6878-common` tree, so none was invented.

## COMMITS

```text
7afff3d gq5012bf1: normalize product and board configuration
c515208 gq5012bf1: organize runtime device configuration
90000ee gq5012bf1: align proprietary extraction with Lineage conventions
0c587f7 gq5012bf1: normalize VINTF into a standard device location
        gq5012bf1: document the Lineage-style tree layout   (this report)
```

Recovery isolation is not a separate commit: it is inseparable from the board
and device configuration changes that introduced the guards. Nothing was pushed.

## FINAL VERDICT

```text
structure recognizable as an official LineageOS tree:   YES
board configuration in one obvious place:               YES
extraction via Lineage extract-utils:                   YES
generated vendor makefiles hand-maintained:             NO (as required)
stock inventory preserved:                              1,891 / 1,891
recovery SELinux policy:                                BYTE-IDENTICAL
TrustKernel full-ROM link rule:                         PRESENT
recovery assets, patches, prebuilts:                    UNCHANGED
full ROM m nothing:                                     PASS
recovery m nothing:                                     PASS
determinism:                                            PASS
audit regressions introduced:                           NONE
new runtime claims:                                     NONE
```

Subsystem status labels are unchanged by this refactor. Everything previously
recorded as **IDENTIFIED**, **CONFIGURED** or **BUILD-VALIDATED** keeps that
label; the main panel, FT3680 touch, CO5300/Hynitron rear display, camera
sensors, ThermoVue AC020, physical sensors, ST21NFC, Microarray fingerprint
transport, gauge/charger ICs, TrustKernel, BootControl, MediaTek codecs, GNSS,
modem and `vendor.yft.hardware.*` stacks are **not** claimed to be
**RUNTIME-VALIDATED** because the tree now looks professional.

## FINAL TREE OUTLINE

```text
device/ulefone/gq5012bf1/
├── Android.bp
├── AndroidProducts.mk
├── BoardConfig.mk
├── device.mk
├── lineage_gq5012bf1.mk
├── twrp_gq5012bf1.mk
├── lineage.dependencies
├── extract-files.py
├── setup-makefiles.py
├── proprietary-files.txt
├── aosp-replaced-files.txt
├── vendorsetup.sh                      recovery build environment
├── build-gq5012bf1.sh                  reproducible recovery packaging
├── vintf/
│   ├── manifest.xml
│   ├── manifest_dsds.xml
│   ├── android.hardware.cas-service.xml
│   ├── fingerprint-example.xml
│   └── gnss-default.xml
├── sepolicy/
│   └── vendor/
│       ├── file.te
│       ├── file_contexts
│       ├── genfs_contexts
│       ├── property.te
│       ├── property_contexts
│       └── trustkernel.te
├── recovery/
│   └── root/
│       ├── first_stage_ramdisk/fstab.emmc
│       ├── init.recovery.mt6878.rc
│       ├── init.recovery.gq5012bf1.security.rc
│       ├── init.recovery.gq5012bf1.usb.rc
│       ├── lib/modules/focaltech_touch_spi_ft3680.ko
│       └── system/{bin,etc}/…
├── prebuilt/
│   ├── kernel
│   ├── dtbo.img
│   └── dtbs/stock.dtb
├── patches/
│   ├── bootable_recovery/…
│   └── system_sepolicy/…
├── tools/
│   ├── inventory_device.py
│   ├── generate_proprietary_candidates.py
│   ├── audit_device_tree.py
│   ├── elf_closure.py
│   ├── snapshot_trust.py
│   ├── vbunpack.py / vbrepack.py
│   └── README.md
├── docs/                               subsystem evidence
└── CODEX.md · README.md · Findings.md · TODO.md ·
    CLAUDE_DEVICE_TREE_AUDIT.md · CLAUDE_FIX_REPORT.md · CLAUDE_REPORT.md ·
    CLAUDE_FBE_REPORT.md · MISSING_BLOBS_DT-ELF-001.txt ·
    LINEAGE_STRUCTURE_REPORT.md
```
