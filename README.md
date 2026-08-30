# OrangeFox Recovery for Ulefone Armor 29 Pro Thermal

OrangeFox Recovery 14.1 device tree for the Ulefone Armor 29 Pro Thermal.

## Device

- Manufacturer: Ulefone
- Model: Armor 29 Pro Thermal
- Product / codename: `GQ5012BF1`
- Platform: MediaTek MT6878
- Architecture: arm64
- Stock Android: Android 15
- Kernel: Linux 6.1 / Android 14 KMI
- Partition layout: A/B + Virtual A/B
- Recovery: `vendor_boot` v4 recovery ramdisk fragment

## Current status

### Working

- OrangeFox boots
- Display
- ADB
- USB configfs
- Physical keys
- Main touchscreen
- Dynamic partition discovery
- fastbootd

### Work in progress

- `/data` mounting
- `/metadata`
- FBE decryption

## Touchscreen

The main display touchscreen is a FocalTech FT3680 connected over SPI3.

Device-tree compatible:

`focaltech,fts`

Kernel module:

`focaltech_touch_spi_ft3680.ko`

The module is included in the recovery ramdisk and loaded during recovery init from:

`/lib/modules/focaltech_touch_spi_ft3680.ko`

The controller registers as:

`fts_ts`

The main touchscreen has been verified working in OrangeFox with a
1080x2400 coordinate range and multitouch input.

A separate Hynitron controller also exists on this device, but it is not
required for the main OrangeFox interface.

## vendor_boot layout

This device uses vendor boot header version 4 with separate vendor ramdisk
fragments.

When constructing an OrangeFox `vendor_boot` image:

- Preserve the stock PLATFORM vendor ramdisk fragment.
- Preserve the stock DTB.
- Preserve the stock vendor boot configuration.
- Replace only the RECOVERY vendor ramdisk fragment with the OrangeFox
  recovery ramdisk.

## Source tree location

Expected Android source-tree path:

`device/ulefone/gq5012bf1`

## Development status

This device tree is still under active development.

Keep a copy of the stock firmware available and validate generated
`vendor_boot` images before flashing.
