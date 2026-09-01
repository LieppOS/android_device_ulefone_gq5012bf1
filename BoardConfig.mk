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

# Stock-derived fstab.
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery/root/system/etc/recovery.fstab

# -------------------------------------------------
# Display
# -------------------------------------------------

# Panel is 1080x2400 at density 480.
TARGET_SCREEN_WIDTH := 1080
TARGET_SCREEN_HEIGHT := 2400

# -------------------------------------------------
# SELinux
# -------------------------------------------------

# Device-specific vendor SELinux policy
BOARD_VENDOR_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy/vendor

# -------------------------------------------------
# Full-ROM partitions and AVB
# -------------------------------------------------

# Recovery intentionally does not define logical partition image filesystems:
# doing so makes the recovery ramdisk staging path create conflicting vendor
# outputs. Full ROM products need the stock super/EROFS/AVB contract instead.
ifeq ($(filter twrp_%,$(TARGET_PRODUCT)),)

# Retained stock ELF blobs are installed at their exact stock paths by the
# generated vendor makefile (see check_elf in extract-files.py).
BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES := true

TARGET_COPY_OUT_PRODUCT := product
TARGET_COPY_OUT_SYSTEM_EXT := system_ext
TARGET_COPY_OUT_SYSTEM_DLKM := system_dlkm
TARGET_COPY_OUT_VENDOR_DLKM := vendor_dlkm
TARGET_COPY_OUT_ODM_DLKM := odm_dlkm

# Stock logical partitions are EROFS. Userdata and metadata remain F2FS via the
# stock-derived fstab; ext4 remains enabled for tooling/fallback compatibility.
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDOR_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_ODM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_EROFS_COMPRESSOR := lz4hc,9
BOARD_EROFS_PCLUSTER_SIZE := 262144

# Decoded from stock super_raw.img using lpdump. The group maximum leaves the
# stock 2 MiB metadata/alignment reserve outside the dynamic group.
BOARD_SUPER_PARTITION_SIZE := 9663676416
BOARD_SUPER_PARTITION_GROUPS := main
BOARD_MAIN_SIZE := 9661579264
BOARD_MAIN_PARTITION_LIST := \
    system \
    system_ext \
    product \
    vendor \
    system_dlkm \
    vendor_dlkm \
    odm_dlkm
BOARD_BUILD_SUPER_IMAGE_BY_DEFAULT := true

# Preserve the stock vbmeta split. Release builds must provide intentional
# project keys; never copy or fabricate Ulefone private signing material.
BOARD_AVB_ENABLE := true
BOARD_AVB_VBMETA_SYSTEM := system system_ext product
BOARD_AVB_VBMETA_VENDOR := vendor vendor_dlkm odm_dlkm
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION := 1
BOARD_AVB_VBMETA_VENDOR_ROLLBACK_INDEX_LOCATION := 2

# -------------------------------------------------
# VINTF
#
# The two assembled stock manifests are build inputs, not installable files:
# build/make refuses VINTF metadata in PRODUCT_COPY_FILES. Both are verbatim
# copies of the stock vendor/odm manifests. Retail hardware is dual-SIM; the
# stock SS/TSTS/QSQS variants remain evidence only. The 49 per-HAL fragments
# under vendor/etc/vintf/manifest/ keep their stock layout and are installed
# by the generated extract-utils modules.
# -------------------------------------------------

DEVICE_MANIFEST_FILE := \
    $(DEVICE_PATH)/vintf/manifest.xml \
    $(DEVICE_PATH)/vintf/android.hardware.cas-service.xml \
    $(DEVICE_PATH)/vintf/fingerprint-example.xml \
    $(DEVICE_PATH)/vintf/gnss-default.xml
ODM_MANIFEST_FILES := $(DEVICE_PATH)/vintf/manifest_dsds.xml

# Generated by Lineage extract-utils from proprietary-files.txt.
-include vendor/ulefone/gq5012bf1/BoardConfigVendor.mk

endif # full-ROM product
