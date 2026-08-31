# Evidence sources

Status labels in these reports mean:

- **VERIFIED** — directly observed in current stock/recovery runtime or decoded stock files.
- **STRONG INFERENCE** — multiple independent clues agree, but the full functional path is not proven.
- **UNKNOWN** — evidence is incomplete or contradictory.

Proof labels are kept distinct and must not be collapsed:

```text
IDENTIFIED         a component was named from a driver, module or string
CONFIGURED         the device tree wires it up
BUILD-VALIDATED    it survives m nothing / policy compilation
RUNTIME-VALIDATED  it was exercised on hardware
```

---

## Source-of-truth ordering is per data class

A single global ranking of evidence is wrong for this device, because the
live stock snapshot is trustworthy for some questions and actively misleading
for others. Rank by **what is being asked**, not by where it came from.

### Hardware topology

Bus bindings, bound drivers, loaded modules, DRM/display topology, input
devices, power supplies, device nodes, running services, camera nodes, sensor
topology, LED class devices, block/partition layout.

```text
1. live stock snapshot        (and live recovery snapshot, which is the only
                               place /sys/class/leds is readable)
2. extracted stock firmware
3. decoded DTB / kernel modules / VINTF / ELF
4. inference
5. generic MediaTek assumptions
```

An integrity-spoofing module does not rewrite `/sys` or `/proc`. For these
questions a live capture beats any static analysis.

### Android build identity and version

`ro.build.*`, `ro.product.*`, API level, fingerprint, shipping API level.

```text
1. extracted stock firmware build.prop
2. stock firmware images / manifests
3. the device tree's own product makefiles
4. live snapshot properties        <-- LOWEST, see the warning below
```

### Security and product identity

Attestation identity, TrustKernel/KeyMint behaviour, the security-facing model.

```text
1. verified TrustKernel hardware experiments (recorded in CLAUDE_FBE_REPORT.md)
2. extracted stock firmware
3. live snapshot properties        <-- LOWEST, see the warning below
```

---

## Warning: the live stock snapshot is property-contaminated

`gq5012bf1-live-stock-20260831-113332` was captured on a device running
**KernelSU** with an active property-spoofing module. `kernelsu` is present in
its `proc.txt`, and its property namespace contradicts both the device's own
build fingerprint and the extracted stock firmware:

| property | snapshot says | reality |
|---|---|---|
| `ro.build.version.release` | `16` | fingerprint says `15` |
| `ro.build.version.sdk` | `36` | stock `system/build.prop` says `35` |
| `ro.product.model_for_attestation` | `Pixel 9 Pro` | stock leaves it **empty** |
| `ro.product.brand_for_attestation` | `google` | stock leaves it **empty** |
| `ro.product.name_for_attestation` | `caiman` | stock leaves it **empty** |
| `ro.product.device_for_attestation` | `caiman` | stock leaves it **empty** |

A LieppOS device-patches module is also active and injects a non-stock
property namespace that must never be mistaken for stock evidence:

```text
persist.lieppos.device_patches               = armor29
persist.lieppos.armor29.thermal_cam          = true
persist.lieppos.armor29.sub_screen           = true
persist.lieppos.armor29.super_flashlight     = true
persist.lieppos.armor29.camp_lights          = true
persist.lieppos.armor29.charging_control     = true
persist.lieppos.armor29.fm_radio             = true
persist.lieppos.armor29.nfc_routing_watchdog = true
persist.lieppos.armor29.touchscreen_grabber  = true
persist.lieppos.armor_mini20.aux_cameras     = false
```

`persist.lieppos.armor29.thermal_cam=true` is a LieppOS **feature flag**, not
proof that a thermal camera is wired up. The same applies to `sub_screen` and
the rear display.

Consequences already applied:

- `PRODUCT_SHIPPING_API_LEVEL := 35` is correct because it follows the stock
  firmware (`ro.product.first_api_level=35`), not the snapshot's `36`.
- No `ro.product.*_for_attestation` value is carried into the device tree.
  Shipping the spoofed Pixel 9 Pro identity in a public tree would be
  deliberate attestation spoofing; stock leaves those properties empty.

The recovery snapshot `gq5012bf1-live-recovery-20260831-113044` also shows
`kernelsu`, which means the **boot image** is patched. No property spoofing
was detected there, and its `ro.build.version.*` legitimately describe the
OrangeFox ramdisk rather than the device, so it stays fully usable for
hardware topology.

### Checking this automatically

```bash
python3 tools/snapshot_trust.py <snapshot-dir> \
    --stock-root .work/gq5012bf1/stock/partitions [--check]
```

`--check` fails when a contaminated snapshot has no adjacent `TRUST.md`
recording the limitation, so an unreviewed capture cannot quietly become
evidence. Both current snapshots carry a `TRUST.md`.

---

## Immutable inputs

| Source | SHA-256 / identity | Trust |
|---|---|---|
| `gq5012bf1-live-recovery-20260831-113044.tar.gz` | `d8e8aa3c44d7906abad25310be99400fe2feaa897b38dba6f2421b2b84d92fbe` | hardware topology only |
| `gq5012bf1-live-stock-20260831-113332.tar.gz` | `d2a18e4f0eefd6d419db9332eed4cf9a494b874931c6721a27744ffb0d0b4144` | hardware topology only |
| Stock build | `GQ5012BF1_EEA_V15_user_20251022` | authoritative for identity |
| Stock fingerprint | `Ulefone/GQ5012BF1_EEA/GQ5012BF1:15/AP3A.240905.015.A2/1761131274:user/release-keys` | authoritative for identity |
| Stock `ro.build.version.sdk` / `release` | `35` / `15` | authoritative |
| Stock `ro.product.first_api_level` | `35` | authoritative |

A second read-only rooted ADB capture was collected under
`.work/gq5012bf1/snapshots/live-stock-adb-20260831-115649`. It contains no
userdata payloads, is intentionally not committed, and carries the same
contamination caveat.

## Generated evidence

`tools/inventory_device.py` generated machine-readable inventories under
`.work/gq5012bf1/reports/inventory` from seven extracted EROFS partitions, the
unpacked stock `vendor_boot` platform ramdisk, and both snapshots. The run found:

- 734 VINTF HAL records across manifests and compatibility matrices;
- 471 module copies across DLKM and vendor_boot inputs;
- 3,583 ELF files with `DT_NEEDED` metadata;
- 263 init services;
- 1,884 reviewed proprietary entries after manifest/init/module/config roots
  and a closed ELF runtime dependency graph.

`tools/elf_closure.py` maintains that closure and classifies every unresolved
SONAME; see `docs/blob-map.md`.

Generated output is reproducible evidence, not a hardware-working claim.
