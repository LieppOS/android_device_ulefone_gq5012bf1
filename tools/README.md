# GQ5012BF1 offline evidence tooling

These tools consume immutable stock images/extracted partitions and read-only
runtime snapshots. Generated output belongs under `.work/` and is not committed.

## 1. Extract stock EROFS partitions

Build host `erofs-utils` (AOSP has it under `external/erofs-utils`) and extract
each logical `*_a.img` into one directory per partition. Never modify source
images in place.

## 2. Generate inventories

```bash
python3 tools/inventory_device.py \
  --stock-root .work/gq5012bf1/stock/partitions \
  --stock-snapshot .work/gq5012bf1/snapshots/stock \
  --recovery-snapshot .work/gq5012bf1/snapshots/recovery \
  --vendor-boot /path/to/unpacked/vendor_boot/platform_ramdisk \
  --out .work/gq5012bf1/reports/inventory
```

Outputs cover partitions, snapshots, VINTF, modules, ELF dependencies, init,
properties, and broad proprietary candidates. Every JSON file is deterministic
for identical inputs except absolute input paths in `metadata.json`.

## 3. Generate a review list

```bash
python3 tools/generate_proprietary_candidates.py \
  --inventory .work/gq5012bf1/reports/inventory \
  --out .work/gq5012bf1/reports/proprietary-files.review.txt
```

The review list selects every present vendor/odm init executable, HALs,
hardware configuration, DLKM modules, explicit Ulefone hardware applications
and in-stock ELF dependency closure. Dead factory/alternate-BOM init references
remain reported but are not fabricated. Inclusion is not a redistribution
decision. Review before promoting entries to `proprietary-files.txt`.

## 4. Audit the tree

```bash
python3 tools/audit_device_tree.py \
  --device . \
  --inventory .work/gq5012bf1/reports/inventory \
  --out .work/gq5012bf1/reports/device-tree-audit.md
```

The audit protects verified recovery/security invariants and reports stock
VINTF, module, and service-executable coverage. A warning is an explicit gap,
not evidence that a subsystem works.

Pass `--stock-partitions` to enable the ELF closure gate and `--snapshot`
(repeatable) to require a `TRUST.md` beside every live capture:

```bash
python3 tools/audit_device_tree.py \
  --device . \
  --inventory .work/gq5012bf1/reports/inventory \
  --stock-partitions .work/gq5012bf1/stock/partitions \
  --snapshot /path/to/gq5012bf1-live-stock-... \
  --snapshot /path/to/gq5012bf1-live-recovery-... \
  --out .work/gq5012bf1/reports/device-tree-audit.md
```

## 5. Check the ELF runtime dependency closure

```bash
python3 tools/elf_closure.py \
  --device . \
  --stock .work/gq5012bf1/stock/partitions \
  --aosp-source "$ANDROID_BUILD_TOP" \
  --json .work/gq5012bf1/reports/elf-closure.json \
  --check
```

"Every listed path exists in stock" is a much weaker property than "the
runtime dependency graph is closed". `DT_NEEDED` is resolved eagerly, so one
missing vendor library takes the whole process down at exec time. This tool
walks the transitive graph from the blobs that actually run on a normal boot
and classifies every unresolved SONAME as one of:

```text
REQUIRED_STOCK_BLOB                          must be extracted
AOSP_OR_ROM_PROVIDED                         AOSP builds it
UNUSED_PARENT_BLOB                           only a never-run blob needs it
ALTERNATE_BOM_OR_FACTORY_ONLY                factory/META-mode only
SHIM_OR_FIXUP_REQUIRED                       needs more than a copy
DEVICE_UNIQUE_OR_CALIBRATION_DO_NOT_PACKAGE  never package
UNKNOWN                                      unresolved from evidence
```

`--check` exits non-zero when any `REQUIRED_STOCK_BLOB` is unresolved.
`--aosp-source` matters: stock installs several *AOSP* libraries under
`/vendor` (the biometrics common helpers, the codec2 HIDL wrappers), and
adding those to `proprietary-files.txt` produces duplicate install rules and
breaks the build.

## 6. Check how far a live snapshot can be trusted

```bash
python3 tools/snapshot_trust.py <snapshot-dir> \
  --stock-root .work/gq5012bf1/stock/partitions --check
```

The stock snapshot was captured under KernelSU with a property-spoofing
module active, so it is authoritative for hardware topology and *not*
authoritative for build identity, version or attestation properties. This
tool detects that condition and `--check` fails when a contaminated capture
has no adjacent `TRUST.md`. See `docs/evidence-sources.md` for the per-data-class
source-of-truth ordering.
