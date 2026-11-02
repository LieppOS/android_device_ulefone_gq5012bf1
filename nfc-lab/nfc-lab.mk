# SPDX-License-Identifier: Apache-2.0
# No change to ordinary product builds. Sync the app and review/apply the pinned
# packages/modules/Nfc patch before opting in. This does not enable NFCEE RF access.
ifeq ($(LIEPPOS_NFC_LAB),true)
ifneq ($(PLATFORM_SDK_VERSION),37)
$(error LieppOS NFC Lab platform integration is pinned to Android 17 / API 37)
endif
PRODUCT_PACKAGES += LieppOSNfcLab
PRODUCT_SYSTEM_PROPERTIES += nfc.lieppos.st21_t4t_compat=false
PRODUCT_COPY_FILES += \
    $(DEVICE_PATH)/nfc-lab/init.lieppos-nfc-lab.rc:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/init/init.lieppos-nfc-lab.rc
endif
