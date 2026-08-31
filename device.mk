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

# GQ5012BF1 is a Treble device. Keep this shared with recovery: it prevents the
# recovery product from being treated as a legacy non-Treble target.
PRODUCT_FULL_TREBLE_OVERRIDE := true

# Recovery inherits only the shared board/storage contract above. Everything
# below integrates the normal Android runtime and generated proprietary stack.
ifeq ($(filter twrp_%,$(TARGET_PRODUCT)),)

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
PRODUCT_PACKAGES += \
    boringssl_self_test64 \
    vndservicemanager

# Camera
PRODUCT_PACKAGES += \
    android.hardware.camera.concurrent.prebuilt.xml

# DRM
PRODUCT_PACKAGES += \
    android.hardware.drm-service.clearkey

# Fingerprint / face
PRODUCT_PACKAGES += \
    android.hardware.biometrics.face-service.example

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

# USB
PRODUCT_PACKAGES += \
    android.hardware.usb.accessory.prebuilt.xml \
    android.hardware.usb.host.prebuilt.xml \
    lsusb

# VINTF
PRODUCT_ENFORCE_VINTF_MANIFEST := true

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
