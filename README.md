# Ulefone Armor 29 Pro Thermal — GQ5012BF1

Android/OrangeFox device tree for the **Ulefone Armor 29 Pro Thermal** (`GQ5012BF1`), based on the MediaTek MT6878 platform.

This repository contains the device-specific configuration required to build recovery for the device. Detailed hardware research, partition discoveries, bring-up history, security/FBE analysis, and unresolved research notes are kept in [`Findings.md`](Findings.md).


## Production status — Build34

| item | value |
|---|---|
| commit | `66f5e8c` |
| build number | 34 |
| full vendor_boot sha256 | `c5da1ec87979f09579eb45ba73b5c3d53edccb436297d32cfad71edd6c7272c4` |
| image size | 67108864 bytes (exactly 64 MiB) |

Build32 (`52d2f09`, image `cd2aeaa315090d74206a837afba1ce2cb86671c2e7fe94cd01dba84ae5ab9671`)
is the previous known-good build, identical except that it has no MTP support.

| feature | status |
|---|---|
| cold-boot decrypt | working — one PIN, no ADB intervention |
| SELinux | working — Enforcing, no functional `permissive=0` denials |
| battery | working — real percentage, live updates, correct charging and discharging state |
| touch | working — confirmed on hardware |
| display / orientation | working |
| brightness | node verified (`/sys/class/leds/lcd-backlight/brightness`, 1024 of max 2047); UI slider not exercised |
| ADB | working — devices, shell, push, pull |
| MTP | working — FunctionFS, composed alongside ADB, browsable from a Linux host |
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
| vibration | working — brightness-only LED vibrator, driven with a userspace timeout |
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
unplugged result           : confirmed working by the device owner on hardware. Note that
                             USB is both charger and ADB transport on this device, so
                             unplugging necessarily drops ADB and the transition cannot be
                             captured over adb; it was verified visually in the OrangeFox UI.
```

Note that the battery is a dual-cell pack: `voltage_now` reads about 8.37 V and
`charge_full_design` is 8578000. The `3rd-gauge` node reports the same values in
millivolts and mAh rather than micro units.

### MTP over FunctionFS

MTP works and is composed alongside ADB. Both interfaces are present at once:

```text
/config/usb_gadget/g1/configs/b.1/f1 -> ffs.adb
/config/usb_gadget/g1/configs/b.1/f2 -> ffs.mtp
host: bNumInterfaces 2, iInterface "ADB Interface" + iInterface "MTP"
```

No MTP server code was changed. `mtp_MtpServer.cpp` already prefers FunctionFS
whenever `/dev/usb-ffs/mtp/ep0` is writable and only falls back to the legacy
`/dev/mtp_usb` node otherwise. The legacy node cannot exist here: the kernel has
no MTP gadget function, `mtp.gs0` cannot be instantiated and `/proc/devices`
lists no MTP entry. So the work is gadget composition plus one recovery patch.

Sequencing is the whole problem. A FunctionFS function cannot be bound to the
UDC until its descriptors are written, and that only happens once the server
opens `ep0`. Binding earlier makes the UDC write fail and takes USB down
completely, ADB included. The bring-up is therefore split in two:

1. `gq5012bf1-mtp-setup.sh` at `on boot` creates the `ffs.mtp` function and
   mounts FunctionFS at `/dev/usb-ffs/mtp`. It does not touch the UDC.
2. `gq5012bf1-mtp-bind.sh`, triggered by `sys.usb.ffs.mtp.ready=1` which
   `MtpDescriptors.cpp` sets after writing descriptors, unbinds the UDC, links
   `ffs.mtp` next to `ffs.adb`, restores the identifiers and rebinds.

`patches/bootable_recovery/0002-mtp-skip-legacy-usb-when-functionfs.patch` makes
`Enable_MTP()` skip its legacy `android_usb` sequence when the FunctionFS
endpoint exists, leaving gadget composition to init.

#### Why the obvious approach fails

Build33 instead pre-set `sys.usb.config=mtp,adb` so that `Enable_MTP()` would
skip the legacy block on its own. Something outside recovery acts on
`sys.usb.config` and recomposed the gadget as MTP-only, dropping `ffs.adb` and
resetting the product id. The host enumerated:

```text
idProduct 0x0000, bNumInterfaces 1, bInterfaceClass 6 Imaging, iInterface MTP
```

MTP worked, but ADB was gone. `sys.usb.config` must not be written on this
device. The same active USB manager also reverts `idProduct`: writing `0x4ee2`
succeeds and reads back correctly immediately after rebinding, then returns to
`0xd001` on its own.

#### Host-side note

A Linux host runs both an ADB server and a desktop MTP client, and both claim
the USB device, so `mtp-detect` and `gio` report
`libusb_claim_interface() reports device is busy`. Browsing from the desktop
file manager works while ADB stays connected. `libmtp` also misidentifies
`18d1:d001` as a Meizu Pro 5, which is cosmetic.

### Build system note: .work must not be scanned by soong

Device inventory tooling clones `erofs-utils` into `device/ulefone/gq5012bf1/.work/`.
That path is in `.gitignore`, but soong does not read `.gitignore` and scans every
directory for `Android.bp`, so the build fails with:

```text
error: external/erofs-utils/Android.bp:34:1: module "external_erofs-utils_license" already defined
```

`.work/.find-ignore` marks the subtree as pruned. `finder.go` treats `.out-dir`
and `.find-ignore` as prune markers. Keep that file in place, and recreate it if
the inventory tooling ever removes it.

### Vibration on a brightness-only LED vibrator

The device exposes its vibrator as a plain LED class device:

```text
/sys/class/leds/vibrator/brightness      writing >0 starts the motor
/sys/class/leds/vibrator/max_brightness  255
```

TWRP knows only two vibrator interfaces, `timed_output/vibrator/enable` and the
`leds/vibrator/duration` plus `activate` pair. This device has neither, so
haptics silently failed with `Cannot find file /sys/class/timed_output/vibrator/enable`.

`patches/bootable_recovery/0003-vibrate-support-brightness-only-led-vibrator.patch`
adds a third branch to `vibrate()` in `minuitwrp/events.cpp`. A brightness node
never stops on its own, so the timeout is enforced in userspace: write
`max_brightness`, then clear it from a detached thread so the input path never
blocks. An atomic counter separate from the QTI `vib_on_count`, which only exists
under `USE_QTI_AIDL_HAPTICS_FIX_OFF`, prevents an earlier timer from cutting a
later buzz short.

### Known limitations

- **MTP requires the host to not fight over the device.** On a Linux host both
  the ADB server and the desktop MTP client (KDE `kiod6`, or `gvfsd-mtp`) hold
  the USB device. `mtp-detect` and `gio` therefore report
  `libusb_claim_interface() reports device is busy`. This is host-side
  contention, not a device fault: browsing from the desktop file manager works
  while ADB stays connected.
- **`odm` has no logical partition.** `/dev/block/mapper` exposes `odm_dlkm_a/b`
  but no `odm_a`, so an `odm` mount attempt fails by design, not by fault.
- Two harmless enforcing denials remain, both directory reads of `rootfs` by
  `hal_health_default` and `hal_bootctl_default`. Both HALs function correctly;
  granting `rootfs` directory read was rejected as too broad for no benefit.
- **USB drops for roughly 40 seconds right after the PIN is entered.** Adding a
  FunctionFS function to a live gadget requires unbinding and rebinding the UDC,
  so the host re-enumerates and ADB reconnects. The bind script itself takes
  0.149 s; the rest is host-side re-enumeration. This is inherent to composing
  MTP at runtime: MTP cannot start before `/data` is decrypted, so the only
  alternative would be withholding ADB until the PIN is entered.
- **A `/auto0` mount error appears at login.** `recovery.fstab:56` uses a
  wildcard `voldmanaged` entry that expands to both the raw SD disk `mmcblk0`,
  which has a partition table rather than a filesystem, and `mmcblk0p1`, which
  mounts correctly as `/auto0-1`. Mounting the raw disk returns `EOVERFLOW`,
  reported by the GUI as a value-too-large error. It is cosmetic and
  pre-existing; MTP only made it visible because it enumerates every storage
  entry. The SD card works. Lines 58-60 do the same for USB OTG, producing
  `/auto1` to `/auto3`.
- **Post-install vibration does not fire.** `data.cpp:1761` writes a duration
  value to `/sys/class/timed_output/vibrator/enable`, which does not exist here.
  It was left alone deliberately: this device's vibrator is a brightness node
  with no auto-stop, so writing a duration to it would set the brightness to
  that number and vibrate continuously. UI haptics are unaffected.

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
