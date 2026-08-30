#
# Ulefone Armor 29 Pro Thermal
# GQ5012BF1 / MT6878
#

DEVICE_PATH := device/ulefone/gq5012bf1

# Base recovery product
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)

# Native Virtual A/B
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota.mk)

# Internal /data/media storage
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)

# OrangeFox / TWRP
$(call inherit-product, vendor/twrp/config/common.mk)

# Dynamic partitions
PRODUCT_USE_DYNAMIC_PARTITIONS := true

PRODUCT_SOONG_NAMESPACES += \
    $(DEVICE_PATH)

# GQ5012BF1 is a Treble device.
PRODUCT_FULL_TREBLE_OVERRIDE := true
