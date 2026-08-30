# OrangeFox Recovery for Ulefone Armor 29 Pro Thermal

OrangeFox Recovery 14.1 device tree for the **Ulefone Armor 29 Pro Thermal**.

## Device

| Property | Value |
|---|---|
| Manufacturer | Ulefone |
| Model | Armor 29 Pro Thermal |
| Product / codename | `GQ5012BF1` |
| Platform | MediaTek MT6878 |
| Architecture | arm64 |
| Stock Android | Android 15 |
| Kernel | Linux 6.1 / Android 14 KMI |
| Partition layout | A/B + Virtual A/B |
| Recovery location | `vendor_boot` v4 recovery ramdisk |

## Current status

### Working

- OrangeFox boots
- Display
- ADB
- USB
- Physical keys
- Main touchscreen
- Dynamic partition discovery
- fastbootd

### Work in progress

- `/data` mounting
- `/metadata`
- FBE decryption
- Additional recovery functionality

## Touchscreen

The main display touchscreen is a **FocalTech FT3680** connected through SPI3.

Device-tree compatible:

```text
focaltech,fts
```

Kernel module:

```text
focaltech_touch_spi_ft3680.ko
```

The module is included in the recovery ramdisk and loaded during recovery startup from:

```text
/lib/modules/focaltech_touch_spi_ft3680.ko
```

The driver registers as:

```text
fts_ts
```

The touchscreen has been verified working in OrangeFox with a `1080x2400`
coordinate range and multitouch input.

A separate Hynitron touch controller is also present on the device, but it is
not required for the main OrangeFox interface.

## Build

Place this repository in the OrangeFox source tree at:

```text
device/ulefone/gq5012bf1
```

From the root of the OrangeFox source tree:

```bash
unset LEX YACC M4 BISON FLEX
source build/envsetup.sh
lunch twrp_gq5012bf1-eng
```

Build OrangeFox with:

```bash
mka adbd vendorbootimage -j1
```

The important recovery ramdisk output is:

```text
out/target/product/gq5012bf1/obj/PACKAGING/vendor_ramdisk_fragments_intermediates/recovery.cpio.lz4
```

## vendor_boot layout

This device does **not** have a standalone `recovery` partition.

Recovery is stored inside `vendor_boot` as a separate recovery ramdisk
fragment.

The stock `vendor_boot` contains:

- stock PLATFORM vendor ramdisk
- RECOVERY vendor ramdisk
- stock DTB
- vendor boot metadata

When creating an OrangeFox image:

- preserve the stock PLATFORM vendor ramdisk
- preserve the stock DTB
- preserve the stock bootconfig
- replace only the RECOVERY vendor ramdisk with the newly built OrangeFox
  `recovery.cpio.lz4`

Do **not** assume that this automatically generated file is safe to flash:

```text
out/target/product/gq5012bf1/vendor_boot.img
```

The final `vendor_boot.img` must be reconstructed and validated for this
device.

The final full image must be exactly:

```text
67108864 bytes
```

## Flashing

Reboot into the bootloader and check the current slot:

```bash
fastboot getvar current-slot
```

The currently tested configuration uses **slot A**.

Flash the validated full OrangeFox `vendor_boot.img` to:

```bash
fastboot flash vendor_boot_a vendor_boot.img
```

Then boot directly into recovery:

```bash
fastboot reboot recovery
```

For the tested setup, no `vbmeta` modification is required.

Do not switch slots, erase partitions, or disable verification unless there is
a separately verified reason to do so.

Always keep a copy of the original stock `vendor_boot.img`.

## Known working vendor_boot parameters

```text
Header version:   4
Page size:        4096
Base:             0x00000000
Kernel offset:    0x40000000
Ramdisk offset:   0x66f00000
Tags offset:      0x47c80000
DTB offset:       0x47c80000
Vendor cmdline:   bootopt=64S3,32N2,64N2
Partition size:   67108864 bytes
```

Vendor ramdisk layout:

```text
type 1: PLATFORM
type 2: recovery
```

## Tested touchscreen module

Expected SHA-256:

```text
6629ec6148ac361a5f0085b8b19efa9d591426679f58262c4998345f41931162
```

File:

```text
recovery/root/lib/modules/focaltech_touch_spi_ft3680.ko
```

## Development status

This device tree is still under active development.

Current bring-up focus is storage mounting and FBE decryption.
