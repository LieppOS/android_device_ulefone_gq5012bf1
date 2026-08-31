# Ulefone Armor 29 Pro Thermal — GQ5012BF1

Android/OrangeFox device tree for the **Ulefone Armor 29 Pro Thermal** (`GQ5012BF1`), based on the MediaTek MT6878 platform.

This repository contains the device-specific configuration required to build recovery for the device. Detailed hardware research, partition discoveries, bring-up history, security/FBE analysis, and unresolved research notes are kept in [`Findings.md`](Findings.md).


## Production status — Build32

| item | value |
|---|---|
| commit | `52d2f09` |
| build number | 32 |
| full vendor_boot sha256 | `cd2aeaa315090d74206a837afba1ce2cb86671c2e7fe94cd01dba84ae5ab9671` |
| recovery fragment sha256 | `58cb516f80d10f2800807950042e9a869793fde0b456c2c40cec6f4c0fda3104` |
| image size | 67108864 bytes (exactly 64 MiB) |

| feature | status |
|---|---|
| cold-boot decrypt | working — one PIN, no ADB intervention |
| SELinux | working — Enforcing, no functional `permissive=0` denials |
| battery | working — real percentage, live updates, correct charging state while plugged |
| touch | working — confirmed on hardware |
| display / orientation | working |
| brightness | node verified (`/sys/class/leds/lcd-backlight/brightness`, 1024 of max 2047); UI slider not exercised |
| ADB | working — devices, shell, push, pull |
| MTP | not supported — see limitations |
| ADB sideload | not tested |
| fastbootd | working — `is-userspace: yes`, `fastboot flash vendor_boot_a` verified |
| internal storage | working — `/data/media/0` readable and writable after decrypt |
| external SD | working — 59 GB exFAT auto-mounted at `/auto0-1` via `exfat-fuse`, read/write verified |
| USB OTG | not tested — no OTG device attached |
| dynamic partitions | working — `system`, `system_ext`, `product`, `vendor` mount read-only |
| slot display | working — active slot `_a`, matches `ro.boot.slot_suffix` |
| backup | working — boot partition, 64 MB, digest generated, completed in 2 s |
| restore | not destructively tested |
| reboot targets | recovery and fastbootd verified; system, bootloader and power off not exercised |
| logs | working — `/tmp/recovery.log`, `dmesg`, `logcat` all populated, `logd` running |
| time / RTC | working — device UTC matches host wall clock |
| thermal | battery temperature sane (28-37 C), no thermal HAL crash loop |
| vibration | not tested |
| screenshot | not tested |

### Battery deliverable

```text
OrangeFox source path used : GetBatteryInfo() in recovery_utils/battery_utils.cpp
                             (health HAL path; TW_USE_LEGACY_BATTERY_SERVICES is NOT set)
health HAL/service used    : android.hardware.health-service.example_recovery
                             (init.svc.vendor.health-default)
actual battery node        : /sys/class/power_supply/battery
  real path                : /sys/devices/platform/soc/11280000.i2c/i2c-5/5-0034/
                             11280000.i2c:mt6375@34:mtk-gauge/power_supply/battery
capacity path              : <battery>/capacity          (percent)
status path                : <battery>/status            (Charging / Discharging / ...)
temperature path           : <battery>/temp              (deci-degC, e.g. 290 = 29.0 C)
voltage path               : <battery>/voltage_now       (microvolts, e.g. 8372000 = 8.372 V)
current path               : <battery>/current_now       (microamps)
charger online path        : /sys/class/power_supply/primary_chg/online   (type=USB)
                             /sys/class/power_supply/mtk-master-charger/online
charger type node          : /sys/devices/platform/charger/gftk_charger_type
SELinux changes            : genfscon labelling of every power_supply real path and
                             gftk_charger_type as sysfs_batteryinfo. No new allow rule:
                             hal_health.te already grants
                             r_dir_file(hal_health_server, sysfs_batteryinfo).
before                     : "No battery devices found" -> getCapacity() fails ->
                             "Using fake battery capacity 100" while real level was 78
after                      : GetBatteryInfo() reports capacity 78 then 79, matching sysfs
plugged result             : status=Charging, charging=1, capacity tracks sysfs
UI update result           : value changed 78 -> 79 across the session, not frozen
unplugged result           : NOT TESTED - charger could not be removed during this session
```

Note that the battery is a dual-cell pack: `voltage_now` reads about 8.37 V and
`charge_full_design` is 8578000. The `3rd-gauge` node reports the same values in
millivolts and mAh rather than micro units.

### Known limitations

- **MTP is not supported.** `TW_EXCLUDE_MTP := true` is deliberate.
  `TWPartitionManager::Enable_MTP()` unconditionally sets `sys.usb.config` to
  `none`, writes the legacy `/sys/class/android_usb/android0/idVendor` and
  `idProduct` nodes, then sets `mtp,adb`. This device composes USB through
  configfs, and `/config/usb_gadget/g1/functions` contains only `ffs.adb` and
  `ffs.fastboot`. There is no kernel MTP gadget function: `mtp.gs0` cannot be
  instantiated, and `/proc/devices` has no MTP entry, so the `/dev/mtp_usb`
  control node that `mtp_MtpServer.cpp` opens does not exist. An `ffs.mtp`
  function *can* be created, so a FunctionFS port is theoretically possible, but
  it requires gadget composition work plus init handling. Enabling MTP as-is
  tears down the ADB gadget, which is how the original bring-up regression was
  found. ADB push/pull covers file transfer in the meantime.
- **Charging-state transition is unverified.** Correct `Charging` state was
  observed while plugged, but the charger was never removed, so the transition to
  `Discharging` has not been proven on hardware.
- **`odm` has no logical partition.** `/dev/block/mapper` exposes `odm_dlkm_a/b`
  but no `odm_a`, so an `odm` mount attempt fails by design, not by fault.
- Two harmless enforcing denials remain, both directory reads of `rootfs` by
  `hal_health_default` and `hal_bootctl_default`. Both HALs function correctly;
  granting `rootfs` directory read was rejected as too broad for no benefit.

### gq5012bf1-tee-storage is retained, not obsolete

An audit was performed to remove this service as dead bring-up scaffolding. Current
hardware evidence contradicts that: with the Build30 ordering `/data` mounts early,
and the service now completes successfully rather than timing out.

```text
Service 'gq5012bf1-tee-storage' (pid 489) exited with status 0
  oneshot service took 7.348000 seconds in background
/data/vendor/t6/fs  -> u:object_r:tkcore_data_file:s0
/data/vendor/t6/app -> u:object_r:tkcore_spta_file:s0
```

It stages the teed datapath with the correct labels and is kept. The 90 second
timeout it used to hit was a symptom of the Build28 ordering, which no longer
exists. Nothing in the boot path is gated on it, so it remains fail-open.

### Reproducible packaging

```bash
./device/ulefone/gq5012bf1/build-gq5012bf1.sh 32 full
```

Builds the recovery fragment, splices it into a full vendor_boot v4 preserving the
stock PLATFORM fragment and stock DTB, appends the AVB footer, verifies both
invariants and the exact 64 MiB size, and prints the artifact path and SHA256. It
never flashes. `out/target/product/gq5012bf1/vendor_boot.img` is **not** flashable
and the script warns about it explicitly.


## Device

| Property | Value |
|---|---|
| Manufacturer | Ulefone |
| Retail model | Armor 29 Pro Thermal |
| Android product model used by the security stack | `Armor 29 Pro` |
| Product / codename | `GQ5012BF1` |
| SoC / platform | MediaTek MT6878 |
| Architecture | arm64 |
| Stock Android | Android 15 |
| Tested Android userdata | Android 16 |
| Kernel | Linux 6.1.115 |
| Kernel KMI generation | Android 14 |
| Storage | UFS |
| Partition scheme | A/B + Virtual A/B |
| Dynamic partitions | Yes |
| Recovery layout | `vendor_boot` v4 recovery ramdisk fragment |

Observed stock-derived kernel:

```text
Linux localhost 6.1.115-android14-11-g6b18f0b574ab-ab12901745 #1 SMP PREEMPT Fri Jan 10 22:12:05 UTC 2025 aarch64
```

## Recovery status

Current bring-up has reached a usable OrangeFox recovery baseline.

Verified on hardware:

- OrangeFox boots from `vendor_boot_a`.
- SELinux remains enforcing.
- Main display and touchscreen work.
- FocalTech FT3680 main touch works in recovery.
- USB/ADB works with the MediaTek configfs controller.
- Fastbootd is available.
- Metadata encryption is handled successfully.
- `/data` mounts through the decrypted metadata mapper.
- Android 16 user-0 FBE/CE storage decrypts with one correct PIN entry.
- `/data/media/0` becomes readable after credential decryption.
- TrustKernel `teed`, KeyMint, Gatekeeper, Keystore2, and MediaTek BootControl operate together in recovery.
- Cold-boot decrypt is repeatable without ADB intervention.
- Battery percentage, charging state and temperature are correct and update live.
- External SD (exFAT) auto-mounts and is readable and writable.
- Backup runs successfully against a real partition.

Known-good FBE/security integration was verified after commit:

```text
bbe7af2
```

Detailed root-cause analysis and bring-up history are in [`Findings.md`](Findings.md).

## Important build notes

The device does **not** use a standalone recovery partition. Recovery is carried as the type-2 recovery vendor-ramdisk fragment inside `vendor_boot` v4.

The stock `vendor_boot` contains:

```text
type 1: PLATFORM
type 2: recovery
```

The stock PLATFORM fragment must be preserved. The normal generated target:

```text
out/target/product/gq5012bf1/vendor_boot.img
```

is not the authoritative flashable image for this device because its generated PLATFORM fragment is not the full stock PLATFORM payload.

The recovery fragment used for final packaging is:

```text
out/target/product/gq5012bf1/obj/PACKAGING/vendor_ramdisk_fragments_intermediates/recovery.cpio.lz4
```

A full flashable image must combine:

1. the stock PLATFORM vendor-ramdisk fragment,
2. the newly built OrangeFox recovery fragment,
3. the stock DTB,
4. the stock-compatible `vendor_boot` v4 geometry,
5. a valid AVB hash footer for the full 64 MiB partition.

Never flash the short generated `out/.../vendor_boot.img` directly.

## Build

From the OrangeFox source tree:

```bash
cd ~/android/fox_14.1

unset OUT OUT_DIR OUT_DIR_COMMON_BASE
unset LEX YACC M4 BISON FLEX

export OUT_DIR="$PWD/out"

source build/envsetup.sh
lunch twrp_gq5012bf1-ap2a-eng
m vendorbootimage
```

Relevant recovery configuration includes:

```make
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
TW_USE_FSCRYPT_POLICY := 2
TW_EXCLUDE_DEFAULT_USB_INIT := true
```

## Flashing

Only `vendor_boot_a` has been used for recovery testing.

From recovery:

```bash
adb reboot fastboot
```

Wait until fastbootd is visibly running, then flash the correctly reconstructed full 64 MiB image:

```bash
fastboot flash vendor_boot_a <full-vendor_boot-image>
fastboot reboot recovery
```

Do not erase `vendor_boot`, switch slots, or modify vbmeta as part of normal recovery testing.

## Boot / partition summary

`vendor_boot` uses header version 4.

```text
page size:        4096
base:             0x00000000
kernel offset:    0x40000000
ramdisk offset:   0x66f00000
tags offset:      0x47c80000
dtb offset:       0x47c80000
vendor cmdline:   bootopt=64S3,32N2,64N2
partition size:   67108864 bytes
```

The tested active slot during bring-up is slot A.

Important storage mappings:

```text
metadata -> /dev/block/sdc16
userdata -> /dev/block/sdc76
misc     -> /dev/block/sdc1
```

Filesystems:

```text
/metadata -> F2FS
/data     -> F2FS
vendor_dlkm -> EROFS
```

The device uses Android dynamic partitions backed by `super`.

## Display and touch

Known display/touch coordinate range:

```text
1080 x 2400
```

Main touchscreen:

```text
Controller: FocalTech FT3680
Bus: SPI3
DT node: /soc/spi3@11013000/focaltech@39
Compatible: focaltech,fts
Max touches: 10
```

Recovery module:

```text
focaltech_touch_spi_ft3680.ko
```

Known SHA-256:

```text
6629ec6148ac361a5f0085b8b19efa9d591426679f58262c4998345f41931162
```

A secondary Hynitron controller is also present in stock Android. Its exact hardware role is documented in [`Findings.md`](Findings.md).

## USB

The device uses Android USB configfs.

```text
sys.usb.configfs=1
sys.usb.controller=11201000.usb0
```

The legacy `/sys/class/android_usb/android0` path is not appropriate for this MediaTek configuration.

## Encryption / security

Stock userdata uses file-based encryption plus metadata encryption:

```text
fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized
keydirectory=/metadata/vold/metadata_encryption
```

The hardware-backed security path is TrustKernel-based and uses the stock vendor implementations of:

```text
teed
android.hardware.security.keymint@3.0-service.trustkernel
android.hardware.gatekeeper-service.trustkernel
keystore2
```

The final recovery FBE implementation is intentionally device-specific because recovery must reproduce the relevant TrustKernel, VINTF, SELinux, device-node, persistent-storage, and service-order requirements.

See [`Findings.md`](Findings.md) for the full investigation.

## Battery

Known power-supply nodes include:

```text
/sys/class/power_supply/battery
/sys/class/power_supply/3rd-gauge
```

Both return a valid capacity value. `battery` is the node the health HAL uses and
reports micro units (`voltage_now` in microvolts, `charge_full_design` in microamp
hours); `3rd-gauge` mirrors the same readings in millivolts and mAh.

Battery reporting is resolved as of Build32. OrangeFox reads the battery through
`GetBatteryInfo()`, which uses the health HAL rather than direct sysfs, because
`TW_USE_LEGACY_BATTERY_SERVICES` is not set.

The HAL enumerates `/sys/class/power_supply/*` and reads each node's `type` file to
locate the battery. Those files were generic `sysfs`, so `hal_health_default` was
denied reading them, healthd logged `No battery devices found`, `getCapacity()`
failed, and recovery substituted a fake 100 percent. Labelling the real power_supply
paths `sysfs_batteryinfo` via `genfscon` fixes it with no new allow rule, because
`hal_health.te` already grants `r_dir_file(hal_health_server, sysfs_batteryinfo)`.

Observed after the fix, matching sysfs exactly and updating live:

```text
capacity: 78 -> 79
status:   Charging
temp:     290 (29.0 C)
voltage:  8372000 uV (dual-cell pack)
```

Full node map, unit notes and the SELinux change are in the Build32 production
status section above. Detailed research notes are in [`Findings.md`](Findings.md).

## Repository layout

Typical device-tree contents include:

```text
AndroidProducts.mk
BoardConfig.mk
device makefiles
recovery fstab
recovery init files
device properties
SELinux policy
device-specific recovery files
```

Kernel source, if a maintainable matching source tree becomes available, should live separately, for example:

```text
android_kernel_ulefone_gq5012bf1
```

Large research notes and hardware reverse-engineering results belong in [`Findings.md`](Findings.md), keeping this README focused on building and using the device tree.

## Research policy

New device facts should be classified as one of:

- **Verified on hardware**
- **Verified from stock firmware**
- **Strong inference**
- **Unknown / needs testing**

Do not turn guesses into permanent device-tree assumptions without confirming them against real hardware or stock firmware.
