#
# Full LieppOS / Lineage-compatible product for Ulefone GQ5012BF1.
# Recovery remains a separate twrp_gq5012bf1 product.
#

DEVICE_PATH := device/ulefone/gq5012bf1

# Inherit from the standard phone product definitions. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

# Inherit the device integration.
$(call inherit-product, $(DEVICE_PATH)/device.mk)

# Inherit the ROM phone configuration. The fallback keeps this device tree
# usable in both LieppOS and LineageOS source checkouts; the current recovery
# checkout intentionally contains neither complete ROM vendor tree.
ifneq ($(wildcard vendor/lieppos/config/common_full_phone.mk),)
$(call inherit-product, vendor/lieppos/config/common_full_phone.mk)
else ifneq ($(wildcard vendor/lineage/config/common_full_phone.mk),)
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)
endif

PRODUCT_NAME := lineage_gq5012bf1
PRODUCT_DEVICE := gq5012bf1
PRODUCT_BRAND := Ulefone
PRODUCT_MANUFACTURER := Ulefone

# TrustKernel/KeyMint identity was verified with this exact model. Retail-facing
# documentation may say "Thermal"; security-facing Android identity must not.
PRODUCT_MODEL := Armor 29 Pro
PRODUCT_GMS_CLIENTID_BASE := android-ulefone
