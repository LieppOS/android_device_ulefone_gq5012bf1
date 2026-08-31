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
