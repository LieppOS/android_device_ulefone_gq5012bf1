# Ulefone Armor 29 Pro Thermal — GQ5012BF1

Android/OrangeFox device tree for the **Ulefone Armor 29 Pro Thermal** (`GQ5012BF1`), based on the MediaTek MT6878 platform.

This repository contains the device-specific configuration required to build recovery for the device. Detailed hardware research, partition discoveries, bring-up history, security/FBE analysis, and unresolved research notes are kept in [`Findings.md`](Findings.md).

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

Both have returned a valid capacity value during testing.

Example observed state:

```text
capacity: 63
status: Charging
```

The exact OrangeFox health/battery integration and full MediaTek charger topology are still being finalized. Detailed nodes and research notes are in [`Findings.md`](Findings.md).

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
