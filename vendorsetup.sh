#!/bin/bash

# Ulefone Armor 29 Pro Thermal - GQ5012BF1

export TARGET_ARCH=arm64

# Native Virtual A/B device.
# This automatically implies several related OrangeFox settings.
export FOX_VIRTUAL_AB_DEVICE=1
export FOX_AB_DEVICE=1

# Android boot header v4 vendor_boot-as-recovery.
export FOX_VENDOR_BOOT_RECOVERY=1

# Install only the recovery ramdisk fragment, never replace the entire
# vendor_boot during normal OrangeFox installation.
export FOX_INSTALLER_VENDOR_BOOT_RAMDISK_INSTALL=1

# Non-Xiaomi A/B device.
export FOX_VANILLA_BUILD=1

# Development safety.
export OF_NO_REFLASH_CURRENT_ORANGEFOX=1

export FOX_BUILD_TYPE=Unofficial

# We deliberately use Ulefone's stock GKI for the first recovery bring-up.
export OF_FORCE_PREBUILT_KERNEL=1

# Stock init_boot and both vendor ramdisk fragments use LZ4.
export OF_USE_LZ4_COMPRESSION=1

export FOX_BUILD_DEVICE=gq5012bf1
export FOX_VARIANT=vBaR
