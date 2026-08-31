# Build and validation status

## Passed offline

- Snapshot archive SHA-256 values match the recorded recovery and stock hashes.
- All seven stock EROFS logical partitions extracted successfully.
- `tools/inventory_device.py` completed VINTF, module, ELF, init, property,
  partition and runtime-snapshot inventories.
- Inventory, extraction, generated makefiles and audit output are deterministic;
  clean repeated runs are byte-identical.
- Offline proprietary extraction: **1,891/1,891 files**, zero missing, zero
  duplicate entries and no mutable NV/userdata/persist partition payloads.
- Generated vendor integration: 1,583 exact-path copies, 21 presigned APK
  imports, 38 explicitly requested AOSP service/binary/permission modules,
  205 explicit AOSP replacement paths, and build-system-assembled VINTF.
- ELF runtime closure: zero unresolved required first-order dependencies, zero
  unresolved required transitive dependencies, zero unexplained dependencies.
- Device audit: 21 PASS, zero FAIL, and one explicit warning for ten unique
  dead stock init executable paths used by factory/alternate-BOM RC files.
- `m selinux_policy` passes for both products. The recovery monolithic policy is
  byte-identical to the pre-split baseline (`bcc760fe38c76c1d…`), while the
  full-ROM policy now contains the common TrustKernel device/storage rules.
- Full product lunch and strict `m nothing` pass for
  `lineage_gq5012bf1-ap2a-userdebug`.
- Recovery lunch and `m nothing` pass for `twrp_gq5012bf1-ap2a-eng` with ROM
  EROFS/super/vendor integration excluded.
- `git diff --check` and Python bytecode compilation pass.

## Build blocker outside this device tree

A `vendorimage` attempt reached the host ART build and stopped because the
current recovery-oriented Android 14 checkout lacks `libvixld`, required by
`libdex2oatd_static`. This checkout is not a complete LieppOS full-ROM source
baseline. The failure occurred before a final vendor image could be produced
and is not recorded as a successful device build.

## Not hardware-tested in this session

No full ROM image was flashed. New ROM-side graphics, radio/IMS, camera,
ThermoVue, rear display, fingerprint, audio, sensors, charging, NFC, OTA and
SELinux behavior remain hardware validation work. Existing recovery/security
claims retain their earlier hardware evidence only.
