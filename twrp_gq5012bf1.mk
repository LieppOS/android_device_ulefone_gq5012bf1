#
# Ulefone Armor 29 Pro Thermal
#

PRODUCT_RELEASE_NAME := gq5012bf1

DEVICE_PATH := device/ulefone/$(PRODUCT_RELEASE_NAME)

$(call inherit-product, $(DEVICE_PATH)/device.mk)

# Common TWRP/OrangeFox recovery configuration

PRODUCT_NAME := twrp_$(PRODUCT_RELEASE_NAME)
PRODUCT_DEVICE := $(PRODUCT_RELEASE_NAME)
PRODUCT_BRAND := Ulefone
PRODUCT_MANUFACTURER := Ulefone
PRODUCT_MODEL := Armor 29 Pro Thermal
