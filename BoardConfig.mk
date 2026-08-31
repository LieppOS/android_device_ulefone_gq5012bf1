#
# Ulefone Armor 29 Pro Thermal
# GQ5012BF1 / MediaTek MT6878
#

DEVICE_PATH := device/ulefone/gq5012bf1

# -------------------------------------------------
# Architecture
# -------------------------------------------------

TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_SUPPORTS_64_BIT_APPS := true

TARGET_KERNEL_ARCH := arm64
TARGET_KERNEL_HEADER_ARCH := arm64

# -------------------------------------------------
# Platform
# -------------------------------------------------

TARGET_BOARD_PLATFORM := mt6878
TARGET_BOOTLOADER_BOARD_NAME := mt6878

TARGET_NO_BOOTLOADER := true
TARGET_NO_RADIOIMAGE := true

# GQ5012BF1 is a Treble device with a real (logical) vendor partition.
# Without this, build/make defaults TARGET_COPY_OUT_VENDOR to system/vendor,
# system/core/rootdir then creates root/vendor as a symlink to /system/vendor,
# and the recovery ramdisk staging rsync fails because modules (health HAL
# vintf manifest, vendor selinux contexts) already installed real files into
# $(TARGET_RECOVERY_ROOT_OUT)/vendor/etc.
# Only sets BOARD_USES_VENDORIMAGE; BUILDING_VENDOR_IMAGE stays off because
# BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE is deliberately not defined.
TARGET_COPY_OUT_VENDOR := vendor

# -------------------------------------------------
# Kernel - stock Ulefone/Google GKI
# -------------------------------------------------

TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel

# Stock kernel is already LZ4 compressed.
BOARD_KERNEL_IMAGE_NAME := Image.lz4

# -------------------------------------------------
# Android boot image v4
#
# Exact values obtained using AOSP unpack_bootimg.py
# against stock GQ5012BF1_EEA_V15 images.
# -------------------------------------------------

BOARD_BOOT_HEADER_VERSION := 4
BOARD_KERNEL_PAGESIZE := 4096

BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOT_HEADER_VERSION)
BOARD_MKBOOTIMG_ARGS += --pagesize $(BOARD_KERNEL_PAGESIZE)

# build/make/core/Makefile only emits --base and --pagesize from board
# variables (INTERNAL_VENDOR_BOOTIMAGE_ARGS).  BOARD_KERNEL_OFFSET /
# BOARD_RAMDISK_OFFSET / BOARD_KERNEL_TAGS_OFFSET / BOARD_DTB_OFFSET are NOT
# consumed anywhere in this tree, so the four offsets must be passed through
# BOARD_MKBOOTIMG_ARGS explicitly, otherwise mkbootimg falls back to its
# defaults (0x8000 / 0x1000000 / 0x100 / 0x1f00000) and the generated header
# does not match stock.
BOARD_KERNEL_BASE := 0x00000000
BOARD_KERNEL_OFFSET := 0x40000000
BOARD_RAMDISK_OFFSET := 0x66f00000
BOARD_KERNEL_TAGS_OFFSET := 0x47c80000
BOARD_DTB_OFFSET := 0x47c80000

BOARD_MKBOOTIMG_ARGS += --kernel_offset $(BOARD_KERNEL_OFFSET)
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_MKBOOTIMG_ARGS += --dtb_offset $(BOARD_DTB_OFFSET)

# Stock vendor_boot cmdline
BOARD_MKBOOTIMG_ARGS += --vendor_cmdline "bootopt=64S3,32N2,64N2"

# -------------------------------------------------
# GKI / vendor_boot-as-recovery
# -------------------------------------------------

BOARD_USES_GENERIC_KERNEL_IMAGE := true

# Recovery is NOT stored in boot and there is no
# standalone recovery partition.
BOARD_USES_RECOVERY_AS_BOOT :=

# Android boot header v4 recovery ramdisk lives
# inside vendor_boot.
BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT := true
BOARD_MOVE_GSI_AVB_KEYS_TO_VENDOR_BOOT := true
BOARD_INCLUDE_RECOVERY_RAMDISK_IN_VENDOR_BOOT := true

# DTB is carried by vendor_boot.
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
BOARD_PREBUILT_DTBIMAGE_DIR := $(DEVICE_PATH)/prebuilt/dtbs

# Stock DTBO partition.
BOARD_PREBUILT_DTBOIMAGE := $(DEVICE_PATH)/prebuilt/dtbo.img

# -------------------------------------------------
# Partitions
# -------------------------------------------------

AB_OTA_UPDATER := true

# build/make/core/Makefile requires AB_OTA_PARTITIONS whenever AB_OTA_UPDATER
# is true.  List verified from MT6878_Android_scatter.txt (physical A/B
# partitions) and recovery.fstab (logical partitions inside super).
AB_OTA_PARTITIONS += \
    boot \
    init_boot \
    vendor_boot \
    dtbo \
    vbmeta \
    vbmeta_system \
    vbmeta_vendor \
    system \
    system_ext \
    vendor \
    product \
    vendor_dlkm \
    odm_dlkm \
    system_dlkm

BOARD_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE := 8388608
BOARD_DTBOIMG_PARTITION_SIZE := 8388608

BOARD_FLASH_BLOCK_SIZE := 262144

BOARD_USES_METADATA_PARTITION := true
BOARD_SUPPRESS_SECURE_ERASE := true

# -------------------------------------------------
# Ramdisk
# -------------------------------------------------

# Stock GQ5012BF1 uses LZ4 ramdisks.
BOARD_RAMDISK_USE_LZ4 := true

# -------------------------------------------------
# Filesystems
# -------------------------------------------------

TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true

# We will replace this with the stock-derived fstab.
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery/root/system/etc/recovery.fstab

# Main display geometry. Besides documenting the verified panel size, these
# let the globally scanned OrangeFox Soong plugin select a harmless theme while
# parsing a full-ROM product in a mixed recovery checkout.
TARGET_SCREEN_WIDTH := 1080
TARGET_SCREEN_HEIGHT := 2400

# -------------------------------------------------
# Recovery UI / debugging
# -------------------------------------------------

# Everything in this section is recovery-specific. A full ROM target must not
# inherit OrangeFox plugins, TW_* behavior, permissive missing-dependency flags,
# or recovery-only crypto/UI configuration.
ifneq ($(filter twrp_%,$(TARGET_PRODUCT)),)

TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888

# Panel is 1080x2400, density 480 (verified live: `wm size` / `wm density`).
TW_THEME := portrait_hdpi

# Backlight, verified from the stock vendor_boot DTB:
#   mtk-leds { compatible = "mediatek,disp-leds";
#     backlight { label = "lcd-backlight";
#                 max-brightness  = <0x7ff>;   /* 2047 */
#                 min-brightness  = <0x4>;
#                 max-hw-brightness = <0x7ff>; } }
# The driver behind it (leds-mtk-disp.ko) is in the stock
# modules.load.recovery list, so the class device exists in recovery.
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 1024
TW_BRIGHTNESS_PATH := /sys/class/leds/lcd-backlight/brightness

# HW TEST 1 (build 10) finding: the recovery USB gadget enumerated as
# 18d1:d001 "Ulefone / Armor 29 Pro Thermal" and was then torn down ~2s later,
# so adbd never became reachable.
#
# Cause: two USB stacks fighting for the same UDC.
#   - stock init.recovery.mt6878.rc  -> setprop sys.usb.configfs 1
#                                       setprop sys.usb.controller 11201000.usb0
#     i.e. the modern configfs gadget path in init.rc
#   - TWRP's init.recovery.usb.rc    -> writes /sys/class/android_usb/android0/*
#     i.e. the legacy android_usb gadget path
#
# Drop the legacy one and keep the stock MediaTek configfs path.
# bootable/recovery/etc/Android.mk:17 and Android.mk:624 gate the install of
# init.recovery.usb.rc on exactly this variable.
TW_EXCLUDE_DEFAULT_USB_INIT := true

# HW TEST 2 (build 13) finding: the ADB gadget STILL died ~3s after boot, so the
# line above is correct hygiene but was NOT sufficient. The next evidence-backed
# root-cause candidate is automatic MTP startup:
#
#   data.cpp:1449            tw_mtp_enabled defaults to 1 when TW_HAS_MTP
#   twrp.cpp:295             at startup, if tw_mtp_enabled -> Enable_MTP()
#   partitionmanager.cpp     Enable_MTP() does:
#       property_set(sys.usb.config, none)              <- tears the gadget down
#       write /sys/class/android_usb/android0/idVendor  <- LEGACY sysfs path
#       write /sys/class/android_usb/android0/idProduct <- LEGACY sysfs path
#       property_set(sys.usb.config, mtp,adb)           <- recompose
#
# GQ5012BF1 is a configfs device (stock sets sys.usb.configfs=1), so those
# android_usb writes target the wrong interface. If the subsequent mtp,adb
# property transition cannot rebuild the configfs gadget, ADB will remain down.
# Host timing matches this path: 18d1:d001 appears, then a permanent disconnect
# ~3s later as the OrangeFox UI finishes starting. Build 14 tests this hypothesis.
#
# MTP is enabled over FunctionFS, which is the configfs path this device needs.
# The legacy route in the comment above genuinely does not work here: the kernel
# has no MTP gadget function, mtp.gs0 cannot be instantiated, /proc/devices has
# no MTP entry, and so /dev/mtp_usb never exists.
#
# No recovery code change is required. mtp_MtpServer.cpp already prefers
# FunctionFS whenever /dev/usb-ffs/mtp/ep0 is writable and only falls back to
# the legacy node otherwise, so the port is purely gadget composition, done by
# init.recovery.gq5012bf1.usb.rc plus gq5012bf1-mtp-setup.sh and
# gq5012bf1-mtp-bind.sh.
#
# Enable_MTP()'s legacy android_usb sequence is skipped by pre-setting
# sys.usb.config to mtp,adb, which is the condition it checks before running it.
# That is what keeps the ADB gadget from being torn down.
TW_MTP_DEVICE := /dev/usb-ffs/mtp/ep0

TW_INCLUDE_FASTBOOTD := true
TW_INCLUDE_REPACKTOOLS := true
TW_INCLUDE_RESETPROP := true

TWRP_INCLUDE_LOGCAT := true
TARGET_USES_LOGD := true

TW_EXCLUDE_TWRPAPP := true

# Useful for vendor_boot based devices.

# -------------------------------------------------
# Initial bring-up
# -------------------------------------------------

ALLOW_MISSING_DEPENDENCIES := true
BUILD_BROKEN_DUP_RULES := true
BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES := true

# OrangeFox/TWRP legacy Soong plugins required by the Android 14 recovery tree.
BUILD_BROKEN_PLUGIN_VALIDATION := \
    soong-libaosprecovery_defaults \
    soong-libguitwrp_defaults \
    soong-libminuitwrp_defaults \
    soong-vold_defaults

# File-based encryption (FBE)
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
TW_USE_FSCRYPT_POLICY := 2

endif # twrp_* recovery product

# Device-specific vendor SELinux policy
BOARD_VENDOR_SEPOLICY_DIRS += device/ulefone/gq5012bf1/sepolicy/vendor

# Recovery intentionally does not define logical partition image filesystems:
# doing so makes the recovery ramdisk staging path create conflicting vendor
# outputs. Full ROM products need the stock super/EROFS/AVB contract instead.
ifeq ($(filter twrp_%,$(TARGET_PRODUCT)),)
include $(DEVICE_PATH)/BoardConfigRom.mk
endif
