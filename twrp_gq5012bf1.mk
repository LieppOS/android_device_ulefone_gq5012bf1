#
# Ulefone Armor 29 Pro Thermal
#

PRODUCT_RELEASE_NAME := gq5012bf1

DEVICE_PATH := device/ulefone/$(PRODUCT_RELEASE_NAME)

# Recovery-only product base and packages. Keep these out of device.mk so the
# full LieppOS/Lineage product cannot accidentally inherit TWRP components.
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)
$(call inherit-product, vendor/twrp/config/common.mk)
$(call inherit-product, $(DEVICE_PATH)/device.mk)

# Common TWRP/OrangeFox recovery configuration

PRODUCT_NAME := twrp_$(PRODUCT_RELEASE_NAME)
PRODUCT_DEVICE := $(PRODUCT_RELEASE_NAME)
PRODUCT_BRAND := Ulefone
PRODUCT_MANUFACTURER := Ulefone
PRODUCT_MODEL := Armor 29 Pro
