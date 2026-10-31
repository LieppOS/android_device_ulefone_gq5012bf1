#
# Ulefone Armor 29 Pro / GQ5012BF1
#

DEVICE_PATH := device/ulefone/gq5012bf1

# A/B
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota.mk)

# Internal /data/media storage
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)

# Partitions
PRODUCT_USE_DYNAMIC_PARTITIONS := true

# Soong namespaces
PRODUCT_SOONG_NAMESPACES += \
    $(DEVICE_PATH)

# Android 14/15 recovery/full-ROM trees still need the explicit Treble override.
# Android 16/17 make Treble mandatory and reject the obsolete variable.
ifeq ($(filter 36 37,$(PLATFORM_SDK_VERSION)),)
PRODUCT_FULL_TREBLE_OVERRIDE := true
endif

# Recovery inherits only the shared board/storage contract above. Everything
# below integrates the normal Android runtime and generated proprietary stack.
ifeq ($(filter twrp_%,$(TARGET_PRODUCT)),)

# Android 17 framework compatibility contract for the preserved stock V15
# vendor payload. The stock vendor/odm manifests declare vendor HAL instances
# that are not part of the AOSP Android 17 framework matrix; this file adds
# exactly those required instances. Validated with checkvintf against the stock
# vendor + odm metadata.
DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE += \
    $(DEVICE_PATH)/vintf/framework_compatibility_matrix.xml

# The preserved vendor payload is VNDK 34 / vendor API 202404. Android 17 no
# longer has a current platform VNDK, but the v34 prebuilt snapshot is still
# part of the platform; keep it so the stock ELF closure remains resolvable.
PRODUCT_EXTRA_VNDK_VERSIONS := 34

# API
PRODUCT_PACKAGES += \
    android.hardware.audio.low_latency.prebuilt.xml \
    android.hardware.bluetooth.prebuilt.xml \
    android.hardware.bluetooth_le.prebuilt.xml \
    android.hardware.consumerir.prebuilt.xml \
    android.hardware.faketouch.prebuilt.xml \
    android.hardware.hardware_keystore.xml \
    android.software.device_id_attestation.prebuilt.xml \
    android.software.ipsec_tunnels.prebuilt.xml \
    android.software.opengles.deqp.level-2023-03-01.prebuilt.xml \
    android.software.verified_boot.prebuilt.xml \
    android.software.vulkan.deqp.level-2023-03-01.prebuilt.xml \
    handheld_core_hardware.prebuilt.xml

# Boot control
# Android 17 has no boringssl_self_test64 module. The stock vendor partition
# carries that binary and its init service; do not request an AOSP copy here.
PRODUCT_PACKAGES += \
    vndservicemanager

# Camera
PRODUCT_PACKAGES += \
    android.hardware.camera.concurrent.prebuilt.xml

# DRM
PRODUCT_PACKAGES += \
    android.hardware.drm-service.clearkey

# Display refresh-rate controls in Settings
PRODUCT_PACKAGES += \
    SettingsOverlayGq5012bf1

# Fingerprint / face
# Android 17 ships the example face service only inside the virtual-face APEX
# and marks it installable: false. The stock vendor partition retains the
# device face binary; requesting the APEX-only module breaks Kati validation.

# GNSS
PRODUCT_PACKAGES += \
    android.hardware.location.gps.prebuilt.xml

# Health
PRODUCT_PACKAGES += \
    android.hardware.health-service.example

# IR
PRODUCT_PACKAGES += \
    android.hardware.ir-service.example

# Partitions
PRODUCT_BUILD_SYSTEM_DLKM_IMAGE := true
PRODUCT_BUILD_VENDOR_DLKM_IMAGE := true
PRODUCT_BUILD_ODM_DLKM_IMAGE := true

# Sensors
PRODUCT_PACKAGES += \
    android.hardware.contexthub-service.tinysys \
    android.hardware.sensor.accelerometer.prebuilt.xml \
    android.hardware.sensor.barometer.prebuilt.xml \
    android.hardware.sensor.compass.prebuilt.xml \
    android.hardware.sensor.gyroscope.prebuilt.xml \
    android.hardware.sensor.light.prebuilt.xml \
    android.hardware.sensor.proximity.prebuilt.xml \
    android.hardware.sensor.stepcounter.prebuilt.xml \
    android.hardware.sensor.stepdetector.prebuilt.xml \
    android.hardware.sensors-service.multihal

# Telephony
PRODUCT_PACKAGES += \
    android.hardware.telephony.ims.prebuilt.xml

# WiFi supplicant
# The stock vendor binary is EXTRACT_ONLY; build the Android 17 source
# supplicant at /vendor/bin/hw/wpa_supplicant instead.
PRODUCT_PACKAGES += \
    wpa_supplicant

# USB
# lsusb is provided by the toybox applet set, not as a standalone module.
PRODUCT_PACKAGES += \
    android.hardware.usb.accessory.prebuilt.xml \
    android.hardware.usb.host.prebuilt.xml

# VINTF is always enforced on Android 16/17; keep the explicit declaration for
# the Android 14/15 full-ROM trees.
ifeq ($(filter 36 37,$(PLATFORM_SDK_VERSION)),)
PRODUCT_ENFORCE_VINTF_MANIFEST := true
endif

# Wi-Fi
PRODUCT_PACKAGES += \
    android.hardware.wifi-service-lazy \
    android.hardware.wifi.direct.prebuilt.xml \
    android.hardware.wifi.passpoint.prebuilt.xml \
    android.hardware.wifi.prebuilt.xml

# Stock launched on Android 15 (API 35). Keep this tree parseable in the
# Android 14 recovery checkout while declaring the real launch level on every
# supported Android 15+ LieppOS/Lineage branch.
ifneq ($(filter 35 36 37,$(PLATFORM_SDK_VERSION)),)
PRODUCT_SHIPPING_API_LEVEL := 35
endif

# Proprietary
$(call inherit-product, vendor/ulefone/gq5012bf1/gq5012bf1-vendor.mk)

endif # full-ROM product
