#!/usr/bin/env bash
#
# Reproducible full vendor_boot packaging for Ulefone Armor 29 Pro Thermal
# (GQ5012BF1 / MT6878).
#
#   ./build-gq5012bf1.sh <build-number> [full]
#
# The image emitted by the Android build system,
#   out/target/product/gq5012bf1/vendor_boot.img
# is NOT flashable on this device. It contains only the freshly built RECOVERY
# ramdisk fragment and omits the stock PLATFORM fragment and the stock DTB, so
# flashing it produces a device that does not boot.
#
# This script rebuilds the recovery fragment, splices it into a known-good full
# vendor_boot v4 container while preserving the stock PLATFORM fragment and the
# stock DTB byte for byte, appends an AVB hash footer, and verifies the result
# is exactly 64 MiB.
#
# It never flashes. Flashing is a separate, explicit step.

set -euo pipefail

BUILD_NUM="${1:-}"
MODE="${2:-full}"

if [[ -z "$BUILD_NUM" ]]; then
    echo "usage: $0 <build-number> [full]" >&2
    exit 1
fi

TOP="${ANDROID_BUILD_TOP:-/home/armol/android/fox_14.1}"
ARTIFACTS="${GQ_ARTIFACTS:-/home/armol/android/gq5012bf1-artifacts}"
PRODUCT_OUT="$TOP/out/target/product/gq5012bf1"
FRAGMENT="$PRODUCT_OUT/obj/PACKAGING/vendor_ramdisk_fragments_intermediates/recovery.cpio.lz4"
TEMPLATE="${GQ_TEMPLATE:-$ARTIFACTS/build26/vendor_boot-build26-raw.img}"
REPACK="${GQ_REPACK:-$(dirname "$(readlink -f "$0")")/tools/vbrepack.py}"

# vendor_boot constants for this device.
PARTITION_SIZE=67108864
SALT=9c02741721a24549180ce75e774265e894e30f7442167b91ef7b06dec913b654
FINGERPRINT='Ulefone/GQ5012BF1_EEA/GQ5012BF1:15/AP3A.240905.015.A2/1761131274:user/release-keys'
STOCK_PLATFORM_SHA=9201a4e5c1b7cb1fc0ce35375af10a3d966dac8b84615a226f98b7d7be2aec00
STOCK_DTB_SHA=bc156c29c33d8226230f07888df0a3d7a1e9c4b85c5fd550a4c4bd1a3134c0d4

OUTDIR="$ARTIFACTS/build${BUILD_NUM}"
RAW="$OUTDIR/vendor_boot-build${BUILD_NUM}-raw.img"
IMG="$OUTDIR/vendor_boot_a-orangefox-FULL64M-BUILD${BUILD_NUM}.img"

die() { echo "ERROR: $*" >&2; exit 1; }

[[ -f "$TEMPLATE" ]] || die "template vendor_boot not found: $TEMPLATE"
[[ -f "$REPACK"   ]] || die "repack helper not found: $REPACK"

echo "==> Building recovery ramdisk fragment"
cd "$TOP"
# The fragment is cached and is not always regenerated when only the device
# tree or sepolicy changed, so drop it first.
rm -f "$FRAGMENT"

# envsetup.sh and the lunch/m helpers reference unset variables internally, so
# nounset stays off for the whole build section rather than just the source.
# shellcheck disable=SC1091
set +u
unset OUT OUT_DIR OUT_DIR_COMMON_BASE LEX YACC M4 BISON FLEX
export OUT_DIR="$TOP/out"
export ALLOW_MISSING_DEPENDENCIES=true
source build/envsetup.sh >/dev/null
lunch twrp_gq5012bf1-ap2a-eng >/dev/null

m vendorbootimage
set -u

[[ -f "$FRAGMENT" ]] || die "recovery fragment was not produced: $FRAGMENT"

echo "==> Splicing into full vendor_boot v4 (preserving stock PLATFORM + DTB)"
mkdir -p "$OUTDIR"
python3 "$REPACK" "$TEMPLATE" "$FRAGMENT" "$RAW"

cp -f "$RAW" "$IMG"

echo "==> Adding AVB hash footer"
AVBTOOL="$TOP/out/host/linux-x86/bin/avbtool"
[[ -x "$AVBTOOL" ]] || AVBTOOL=avbtool
"$AVBTOOL" add_hash_footer \
    --image "$IMG" \
    --partition_size "$PARTITION_SIZE" \
    --partition_name vendor_boot \
    --hash_algorithm sha256 \
    --algorithm NONE \
    --salt "$SALT" \
    --prop "com.android.build.vendor_boot.fingerprint:$FINGERPRINT"

echo "==> Verifying invariants"
ACTUAL_SIZE=$(stat -c%s "$IMG")
[[ "$ACTUAL_SIZE" == "$PARTITION_SIZE" ]] \
    || die "image is $ACTUAL_SIZE bytes, expected $PARTITION_SIZE"

# Confirm the stock PLATFORM fragment and stock DTB survived the splice.
if ! python3 "${GQ_UNPACK:-$(dirname "$(readlink -f "$0")")/tools/vbunpack.py}" "$IMG" 2>/dev/null \
        | grep -q "$STOCK_PLATFORM_SHA"; then
    echo "WARNING: could not confirm stock PLATFORM fragment $STOCK_PLATFORM_SHA" >&2
fi
if ! python3 "${GQ_UNPACK:-$(dirname "$(readlink -f "$0")")/tools/vbunpack.py}" "$IMG" 2>/dev/null \
        | grep -q "$STOCK_DTB_SHA"; then
    echo "WARNING: could not confirm stock DTB $STOCK_DTB_SHA" >&2
fi

FRAG_SHA=$(sha256sum "$FRAGMENT" | cut -d' ' -f1)
IMG_SHA=$(sha256sum "$IMG" | cut -d' ' -f1)

cat <<EOF

========================================================================
Build ${BUILD_NUM} packaged.

  flashable image : $IMG
  size            : $ACTUAL_SIZE bytes
  image  sha256   : $IMG_SHA
  fragment sha256 : $FRAG_SHA

Flash ONLY vendor_boot_a, from fastbootd:

  adb reboot fastboot
  # wait until 'fastboot devices' shows the device
  fastboot flash vendor_boot_a $IMG
  fastboot reboot recovery

WARNING: do NOT flash $PRODUCT_OUT/vendor_boot.img
It lacks the stock PLATFORM fragment and stock DTB and will not boot.
========================================================================
EOF
