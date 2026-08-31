#
# Full LieppOS / Lineage-compatible product for Ulefone GQ5012BF1.
# Recovery remains a separate twrp_gq5012bf1 product.
#

DEVICE_PATH := device/ulefone/gq5012bf1

$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product, $(DEVICE_PATH)/device.mk)
$(call inherit-product-if-exists, vendor/ulefone/gq5012bf1/gq5012bf1-vendor.mk)

# Prefer the native LieppOS product base, with a Lineage-compatible fallback.
ifneq ($(wildcard vendor/lieppos/config/common_full_phone.mk),)
$(call inherit-product, vendor/lieppos/config/common_full_phone.mk)
else ifneq ($(wildcard vendor/lineage/config/common_full_phone.mk),)
$(call inherit-product, vendor/lineage/config/common_full_phone.mk)
endif

PRODUCT_ENFORCE_VINTF_MANIFEST := true
# Stock launched on Android 15 (API 35). Keep recovery-source parsing possible
# on the current Android 14 tree, while setting the real launch level on every
# supported Android 15+ LieppOS branch.
ifneq ($(filter 35 36 37,$(PLATFORM_SDK_VERSION)),)
PRODUCT_SHIPPING_API_LEVEL := 35
endif

PRODUCT_NAME := lineage_gq5012bf1
PRODUCT_DEVICE := gq5012bf1
PRODUCT_BRAND := Ulefone
PRODUCT_MANUFACTURER := Ulefone

# TrustKernel/KeyMint identity was verified with this exact model. Retail-facing
# documentation may say "Thermal"; security-facing Android identity must not.
PRODUCT_MODEL := Armor 29 Pro
PRODUCT_GMS_CLIENTID_BASE := android-ulefone
