#
# Ulefone Armor 29 Pro Thermal
# GQ5012BF1 / MT6878
#

DEVICE_PATH := device/ulefone/gq5012bf1

# Shared device contract. Product bases and ROM/recovery-specific configuration
# belong in their product makefiles so a full ROM never inherits TWRP packages
# and recovery never inherits the complete proprietary Android stack.

# Native Virtual A/B
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota.mk)

# Internal /data/media storage
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)

# Dynamic partitions
PRODUCT_USE_DYNAMIC_PARTITIONS := true

# Full-ROM image ownership. Recovery uses the stock PLATFORM vendor ramdisk and
# must not try to build/install the complete logical partition set.
ifeq ($(filter twrp_%,$(TARGET_PRODUCT)),)
PRODUCT_BUILD_SYSTEM_DLKM_IMAGE := true
PRODUCT_BUILD_VENDOR_DLKM_IMAGE := true
PRODUCT_BUILD_ODM_DLKM_IMAGE := true
endif

PRODUCT_SOONG_NAMESPACES += \
    $(DEVICE_PATH)

# GQ5012BF1 is a Treble device.
PRODUCT_FULL_TREBLE_OVERRIDE := true
