#
# Full-ROM-only partition and AVB configuration.
# Included from BoardConfig.mk for non-TWRP products.
#

-include vendor/ulefone/gq5012bf1/BoardConfigVendor.mk

# The initial vendor generator installs retained ELF blobs at their exact stock
# paths. Converting the complete dependency closure to typed Soong prebuilts is
# future hardening work; APKs and VINTF already use proper module integration.
BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES := true

TARGET_COPY_OUT_PRODUCT := product
TARGET_COPY_OUT_SYSTEM_EXT := system_ext
TARGET_COPY_OUT_SYSTEM_DLKM := system_dlkm
TARGET_COPY_OUT_VENDOR_DLKM := vendor_dlkm
TARGET_COPY_OUT_ODM_DLKM := odm_dlkm

# Stock logical partitions are EROFS. Userdata and metadata remain F2FS via the
# stock-derived fstab; ext4 remains enabled for tooling/fallback compatibility.
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_SYSTEM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_VENDOR_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_ODM_DLKMIMAGE_FILE_SYSTEM_TYPE := erofs
BOARD_EROFS_COMPRESSOR := lz4hc,9
BOARD_EROFS_PCLUSTER_SIZE := 262144

# Decoded from stock super_raw.img using lpdump. The group maximum leaves the
# stock 2 MiB metadata/alignment reserve outside the dynamic group.
BOARD_SUPER_PARTITION_SIZE := 9663676416
BOARD_SUPER_PARTITION_GROUPS := main
BOARD_MAIN_SIZE := 9661579264
BOARD_MAIN_PARTITION_LIST := \
    system \
    system_ext \
    product \
    vendor \
    system_dlkm \
    vendor_dlkm \
    odm_dlkm
BOARD_BUILD_SUPER_IMAGE_BY_DEFAULT := true

# Preserve the stock vbmeta split. Release builds must provide intentional
# project keys; never copy or fabricate Ulefone private signing material.
BOARD_AVB_ENABLE := true
BOARD_AVB_VBMETA_SYSTEM := system system_ext product
BOARD_AVB_VBMETA_VENDOR := vendor vendor_dlkm odm_dlkm
BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION := 1
BOARD_AVB_VBMETA_VENDOR_ROLLBACK_INDEX_LOCATION := 2
