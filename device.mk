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

# The retained stock vendor still uses HIDL. Android 17's minimal product
# does not install these legacy runtime services implicitly; without them
# vendor HAL registration/allocation cannot reproduce the working slot B.
PRODUCT_PACKAGES += \
    hwservicemanager \
    android.hidl.allocator@1.0-service \
    android.hidl.memory@1.0-impl

# Camera
PRODUCT_PACKAGES += \
    android.hardware.camera.concurrent.prebuilt.xml

# Aperture: 720p/1080p60 on the main camera through MediaTek HFPS (overlay plus
# patches/packages_apps_Aperture/0001, which sets the hfpsMode vendor tag).
PRODUCT_PACKAGES += \
    ApertureOverlayGq5012bf1

# The stock HAL advertises 3840x2160 constrained high-speed video (60-120 and
# 120 fps) on camera 0 but has no sensor mode for it and aborts when such a
# session is configured. cameraserver drops these entries
# (patches/frameworks_av/0001), so the framework rejects such sessions instead.
PRODUCT_VENDOR_PROPERTIES += \
    ro.vendor.camera.drop_high_speed_video_sizes=0:3840x2160

# DRM
PRODUCT_PACKAGES += \
    android.hardware.drm-service.clearkey

# Display refresh-rate controls in Settings
PRODUCT_PACKAGES += \
    SettingsOverlayGq5012bf1

# Front RGB notification/battery LED (AW2013 via the MediaTek lights HAL)
PRODUCT_PACKAGES += \
    FrameworksResOverlayGq5012bf1 \
    LineageSdkOverlayGq5012bf1

# Keep the full refresh range (up to 120 Hz) in battery saver. Needs
# patches/frameworks_base/0001 (AOSP otherwise always caps rendering at 60 Hz).
PRODUCT_SYSTEM_PROPERTIES += \
    ro.lieppos.low_power_limits_refresh_rate=false

# A status bar clock with seconds otherwise keeps the panel at 120 Hz: on this
# multi-refresh-rate panel the status bar only casts NoVote, and "no layers with
# votes" picks the maximum rate on every tick. Needs patches/frameworks_native/0001
# (active NoVote-only layers keep the current mode). Verified live: static home
# 60 Hz with seconds shown; touch, scrolling and app launches still 120 Hz.
PRODUCT_SYSTEM_PROPERTIES += \
    ro.lieppos.sf.novote_keeps_mode=true

# Smooth display: drop to the lowest allowed rate (60 Hz) after 750 ms without
# new frames, jump back to 120 Hz on touch, and match video frame rates.
# Without these SurfaceFlinger stays at the top of the range (120 Hz) even on
# a static screen. Verified live: static 60 Hz, touch/scroll 120 Hz, no flicker.
# 750 ms (not 1 s) so the idle timer expires between 1 Hz status bar clock
# ticks (seconds shown) instead of racing them.
# Product partition, not vendor: our flash set is system/system_ext/product.
PRODUCT_PRODUCT_PROPERTIES += \
    ro.surface_flinger.use_content_detection_for_refresh_rate=true \
    ro.surface_flinger.set_idle_timer_ms=750 \
    ro.surface_flinger.set_touch_timer_ms=300 \
    ro.surface_flinger.set_display_power_timer_ms=1000

# ThermoVue may open the built-in thermal camera (InfiRay 3474:4321) without the
# per-connection USB dialog (patches/frameworks_base/0002).
PRODUCT_SYSTEM_PROPERTIES += \
    ro.lieppos.usb_device_allowlist=com.energy.tc2c:3474:4321

# Quick Settings tiles: super flashlight (off/lowest/max), red light, blue light (parts/).
# F1/F2 are deliberately left unbound (free for apps such as Key Mapper).
PRODUCT_PACKAGES += \
    ArmorPartsGq5012bf1

# Battery saver CPU cap: ArmorParts sets sys.lieppos.powersave, this rc caps
# the big cluster (the stock MediaTek power HAL has no low-power scenario).
PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/rootdir/etc/init/lieppos-powersave.rc:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/init/lieppos-powersave.rc

# Charge limit (Settings > Battery > Charge limit in ArmorParts): this rc
# applies ArmorParts' sys.lieppos.charge_pause to the MediaTek charger.
PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/rootdir/etc/init/lieppos-chargelimit.rc:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/init/lieppos-chargelimit.rc

# FM radio: RevampedFMRadio (fmradio/, iusmac mtk v3.1.3) on the stock
# fmradio_drv_connac2x driver, stock FM firmware and the stock MediaTek audio HAL.
# Replaces the stock YftFmRadio, whose libyftfmjni.so is not in the vendor payload.
# libmtkfmjni reads persist.vendor.connsys.fm_chipid first; this platform reports
# "connac2x", which it does not map, so pin the id the driver returns: it reports
# the MT6637 A-die as 0x6635 "for APP compatible". Band (87.5-108 MHz, 100 kHz)
# and thresholds keep the library defaults, matching fm_cust.cfg. Antenna is the
# headset cable; there is no short-antenna support.
PRODUCT_PACKAGES += \
    RevampedFMRadio

PRODUCT_SYSTEM_EXT_PROPERTIES += \
    ro.fm.chip=0x6635

# ThermoVue Pro for the built-in Tiny2-C thermal camera (thermovue/; 64-bit repack of
# the stock app, replaces M170infisens). ArmorParts powers the camera off if it dies.
PRODUCT_PACKAGES += \
    ThermoVue

# IMS: VoLTE / VoNR through the MediaTek in-modem IMS stack (see ims/README.md).
PRODUCT_PACKAGES += \
    MtkImsServiceGq5012bf1 \
    ImsFrameworkOverlayGq5012bf1 \
    ImsPhoneOverlayGq5012bf1 \
    ImsCarrierConfigOverlayGq5012bf1

# The MediaTek RIL's "dynamic IMS switch" expects per-carrier capability reports
# from the stock MediaTek IMS framework; with the AOSP-side ImsService it forces
# VoNR off. Disabled so Android's per-SIM VoLTE/VoNR switches drive the modem.
PRODUCT_PRODUCT_PROPERTIES += \
    persist.vendor.mtk_dynamic_ims_switch=0

# Physical Microarray fingerprint HAL. The OEM adapter is selected by the
# proprietary manifest; its /default extraction fixup and device VINTF must
# remain aligned with this source-owned, TrustKernel-readiness-started rc.
# proprietary-files.txt installs the matched helpers/V3 NDK chain in a private
# directory selected only by this HAL's rc, avoiding AOSP .vendor collisions.
PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/rootdir/etc/init/fingerprint-example.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/fingerprint-example.rc

# Display: 12-bit backlight (DBV 0..4095, see prebuilt/dtbs) with HBM used only
# for HDR content. Product takes precedence over the stock vendor display config.
PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/rootdir/etc/displayconfig/display_id_4627039422300187648.xml:$(TARGET_COPY_OUT_PRODUCT)/etc/displayconfig/display_id_4627039422300187648.xml

# First-stage mount: the stock fstabs in the vendor ramdisk (vendor_boot), as
# on the stock and current slot-B vendor_boot (content-identical to the copies
# in /vendor/etc). Without them the vendor ramdisk was empty and the build
# failed listing out/.../vendor_ramdisk.
PRODUCT_COPY_FILES += \
    vendor/ulefone/gq5012bf1/proprietary/vendor/etc/fstab.mt6878:$(TARGET_COPY_OUT_VENDOR_RAMDISK)/first_stage_ramdisk/fstab.mt6878 \
    vendor/ulefone/gq5012bf1/proprietary/vendor/etc/fstab.emmc:$(TARGET_COPY_OUT_VENDOR_RAMDISK)/first_stage_ramdisk/fstab.emmc

# Face
# Android 17 ships the example face service only inside the virtual-face APEX
# and marks it installable: false. The stock vendor partition retains the
# device face binary; requesting the APEX-only module breaks Kati validation.

# GNSS
PRODUCT_PACKAGES += \
    android.hardware.location.gps.prebuilt.xml

# The vendor-preserving system update retains the SDK-34 health daemon/rc,
# which has no charger-mode registration. A newly built Android-17 example
# health service integrates charger mode and overrides the standalone charger;
# selecting it without deploying that vendor image would remove charging UI.
ifeq ($(LIEPPOS_PRESERVE_INSTALLED_VENDOR),true)
PRODUCT_PACKAGES += charger
else
PRODUCT_PACKAGES += android.hardware.health-service.example
endif

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

# Disabled-default NFC Lab app/profile; normal NFC and firmware stay unchanged.
$(call inherit-product, $(DEVICE_PATH)/nfc-lab/nfc-lab.mk)

# Proprietary
$(call inherit-product, vendor/ulefone/gq5012bf1/gq5012bf1-vendor.mk)

endif # full-ROM product
