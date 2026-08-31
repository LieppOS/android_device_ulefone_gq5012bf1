# Evidence sources

Status labels in these reports mean:

- **VERIFIED** — directly observed in current stock/recovery runtime or decoded stock files.
- **STRONG INFERENCE** — multiple independent clues agree, but the full functional path is not proven.
- **UNKNOWN** — evidence is incomplete or contradictory.

## Immutable inputs

| Source | SHA-256 / identity | Status |
|---|---|---|
| `gq5012bf1-live-recovery-20260831-113044.tar.gz` | `d8e8aa3c44d7906abad25310be99400fe2feaa897b38dba6f2421b2b84d92fbe` | VERIFIED |
| `gq5012bf1-live-stock-20260831-113332.tar.gz` | `d2a18e4f0eefd6d419db9332eed4cf9a494b874931c6721a27744ffb0d0b4144` | VERIFIED |
| Stock build | `GQ5012BF1_EEA_V15_user_20251022` | VERIFIED |
| Stock fingerprint | `Ulefone/GQ5012BF1_EEA/GQ5012BF1:15/AP3A.240905.015.A2/1761131274:user/release-keys` | VERIFIED |

A second read-only rooted ADB capture was collected under
`.work/gq5012bf1/snapshots/live-stock-adb-20260831-115649`. It contains no
userdata payloads and is intentionally not committed.

## Generated evidence

`tools/inventory_device.py` generated machine-readable inventories under
`.work/gq5012bf1/reports/inventory` from seven extracted EROFS partitions, the
unpacked stock `vendor_boot` platform ramdisk, and both snapshots. The run found:

- 734 VINTF HAL records across manifests and compatibility matrices;
- 471 module copies across DLKM and vendor_boot inputs;
- 3,583 ELF files with `DT_NEEDED` metadata;
- 263 init services;
- 1,814 reviewed proprietary entries after manifest/init/module/config roots and ELF closure.

Generated output is reproducible evidence, not a hardware-working claim.
