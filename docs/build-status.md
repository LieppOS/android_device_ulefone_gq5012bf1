# Build and validation status

## Passed offline

- Snapshot archive SHA-256 values match the recorded recovery and stock hashes.
- All seven stock EROFS logical partitions extracted successfully.
- `tools/inventory_device.py` completed VINTF, module, ELF, init, property,
  partition and runtime-snapshot inventories.
- Candidate generation is deterministic: regenerated output matches
  `proprietary-files.txt` exactly.
- Offline proprietary extraction: **1,814/1,814 files**, zero missing, zero
  duplicate entries and no mutable NV/userdata/persist partition payloads.
- Generated vendor integration: 1,513 exact-path copies, 21 presigned APK
  imports, 198 explicit AOSP replacements, build-system-assembled VINTF.
- Device audit: 16 PASS, one explicit warning for ten unique dead stock init
  executable paths used by factory/alternate-BOM RC files.
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
