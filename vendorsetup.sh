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

# Apply device-required platform source patches.
_gq_apply_patch() {
    local repo="$1"
    local patch="$2"
    local label="$3"

    if git -C "$repo" apply --reverse --check "$patch" >/dev/null 2>&1; then
        return 0
    fi

    if git -C "$repo" apply --check "$patch" >/dev/null 2>&1; then
        echo "[gq5012bf1] Applying $label"
        git -C "$repo" apply "$patch" || return 1
        return 0
    fi

    echo "[gq5012bf1] ERROR: $label does not apply cleanly" >&2
    return 1
}

# Device inventory tooling clones erofs-utils into .work/ inside the device
# tree. That path is gitignored, but soong does not read .gitignore and scans
# every directory for Android.bp, so the build dies with
#   error: external/erofs-utils/Android.bp: module ... already defined
# finder.go treats .out-dir and .find-ignore as prune markers, so drop one in.
if [ -d "$(dirname "${BASH_SOURCE[0]:-$0}")/.work" ]; then
    touch "$(dirname "${BASH_SOURCE[0]:-$0}")/.work/.find-ignore" 2>/dev/null
fi

if [ -n "$ANDROID_BUILD_TOP" ]; then
    _gq_apply_patch "$ANDROID_BUILD_TOP/system/sepolicy" "$ANDROID_BUILD_TOP/device/ulefone/gq5012bf1/patches/system_sepolicy/0001-recovery-read-vold-metadata-key.patch" "recovery metadata SELinux patch" || return 1
    _gq_apply_patch "$ANDROID_BUILD_TOP/bootable/recovery" "$ANDROID_BUILD_TOP/device/ulefone/gq5012bf1/patches/bootable_recovery/0001-twrp-ramdisk-require-vendor-property-contexts.patch" "recovery property-context dependency patch" || return 1
    _gq_apply_patch "$ANDROID_BUILD_TOP/bootable/recovery" "$ANDROID_BUILD_TOP/device/ulefone/gq5012bf1/patches/bootable_recovery/0002-mtp-skip-legacy-usb-when-functionfs.patch" "MTP FunctionFS USB patch" || return 1
    _gq_apply_patch "$ANDROID_BUILD_TOP/bootable/recovery" "$ANDROID_BUILD_TOP/device/ulefone/gq5012bf1/patches/bootable_recovery/0003-vibrate-support-brightness-only-led-vibrator.patch" "brightness-only LED vibrator patch" || return 1
    unset -f _gq_apply_patch
fi
