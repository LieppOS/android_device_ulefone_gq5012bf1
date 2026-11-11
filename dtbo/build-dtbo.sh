#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
#
# Build the GQ5012BF1 dtbo.img from source.
#
#   kernel DTS (arch/arm64/boot/dts/mediatek/gq5012bf1.dts + includes)
#     -> C preprocessor + dtc -@        (same flags as Kbuild)
#     -> Android DT table (mkdtboimg)   entry 0, id 0, rev 0, page 2048
#     -> MediaTek cert blocks           only if the stock cert2 still
#                                       authenticates the new bytes
#     -> optional AVB hash footer       (the ROM build adds its own)
#
# The script never copies the stock image as its result: the output table is
# always compiled from source. The stock image is only (a) the comparison
# reference and (b) the donor of the original MediaTek cert1/cert2 blocks,
# which are appended only when cert2's SHA-256 values match the newly built
# bytes, i.e. when Ulefone's own signature still covers them. Nothing is
# re-signed and no signature is fabricated.
#
# LK checks the dtbo partition with img_auth (pl_lk: "lk_dtbo cert chain vfy
# pass ... image dtbo auth pass", img_auth_required = 1). Whether LK still
# boots an image without valid MediaTek certs on this unlocked unit is
# UNTESTED, so a build whose bytes differ from stock fails unless
# --allow-unsigned is given.
#
# usage: build-dtbo.sh --kernel-src DIR --out DIR [options]
#   --stock IMG          stock reference dtbo.img (default: ../prebuilt/dtbo.img)
#   --dtc PATH           dtc binary (default: $DTC, dtc in PATH)
#   --cpp "CMD"          preprocessor (default: $DTBO_CPP, "clang -E", "cpp")
#   --mkdtboimg CMD      mkdtboimg (default: $MKDTBOIMG, mkdtboimg in PATH, or
#                        <lineage>/system/libufdt/utils/src/mkdtboimg.py)
#   --allow-unsigned     accept a result the stock MediaTek cert cannot cover
#   --avbtool CMD        also write dtbo-avb.img with an AVB hash footer
#   --partition-size N   AVB partition size (default 8388608)
#   --salt HEX           AVB salt (default: random)
#   --avb-extra "ARGS"   extra add_hash_footer arguments (e.g. --prop ...)
#   To reproduce the complete stock 8 MiB partition image, pass the stock
#   salt, its dtbo fingerprint prop and --internal_release_string
#   'avbtool 1.3.0' (see README.md, "Reproducing stock exactly").
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KSRC="" OUT="" STOCK="$HERE/../prebuilt/dtbo.img"
DTC_BIN="${DTC:-}" CPP_CMD="${DTBO_CPP:-}" MKDTBOIMG_CMD="${MKDTBOIMG:-}"
ALLOW_UNSIGNED=0 AVBTOOL_CMD="" PART_SIZE=8388608 SALT="" AVB_EXTRA=()
PAGE_SIZE=2048

die() { echo "build-dtbo: ERROR: $*" >&2; exit 1; }
while [ $# -gt 0 ]; do
    case "$1" in
        --kernel-src) KSRC="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --stock) STOCK="$2"; shift 2 ;;
        --dtc) DTC_BIN="$2"; shift 2 ;;
        --cpp) CPP_CMD="$2"; shift 2 ;;
        --mkdtboimg) MKDTBOIMG_CMD="$2"; shift 2 ;;
        --allow-unsigned) ALLOW_UNSIGNED=1; shift ;;
        --avbtool) AVBTOOL_CMD="$2"; shift 2 ;;
        --partition-size) PART_SIZE="$2"; shift 2 ;;
        --salt) SALT="$2"; shift 2 ;;
        --avb-extra) eval "AVB_EXTRA+=($2)"; shift 2 ;;
        -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
        *) die "unknown argument: $1" ;;
    esac
done
[ -n "$KSRC" ] && [ -n "$OUT" ] || die "--kernel-src and --out are required"
DTS="$KSRC/arch/arm64/boot/dts/mediatek/gq5012bf1.dts"
[ -f "$DTS" ] || die "board DTS not found: $DTS"
[ -f "$STOCK" ] || die "stock reference not found: $STOCK"

if [ -z "$DTC_BIN" ]; then DTC_BIN="$(command -v dtc || true)"; fi
[ -x "$DTC_BIN" ] || die "dtc not found (use --dtc)"
if [ -z "$CPP_CMD" ]; then
    if command -v clang >/dev/null; then CPP_CMD="clang -E"; else CPP_CMD="cpp"; fi
fi
if [ -z "$MKDTBOIMG_CMD" ]; then
    if command -v mkdtboimg >/dev/null; then MKDTBOIMG_CMD="mkdtboimg"
    else
        for t in "$HERE/../../../.." "$HERE/../../../../../../lineage-24.0"; do
            f="$t/system/libufdt/utils/src/mkdtboimg.py"
            [ -f "$f" ] && { MKDTBOIMG_CMD="python3 $(cd "$(dirname "$f")" && pwd)/mkdtboimg.py"; break; }
        done
    fi
fi
[ -n "$MKDTBOIMG_CMD" ] || die "mkdtboimg not found (use --mkdtboimg)"

mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
D="$KSRC/arch/arm64/boot/dts"
TOOL="python3 $HERE/dtbo_tool.py"

# 1. Preprocess + compile exactly like scripts/Makefile.lib cmd_dtc.
$CPP_CMD -nostdinc -I"$D" -I"$D/mediatek" -I"$KSRC/scripts/dtc/include-prefixes" \
    -I"$KSRC/include" -undef -D__DTS__ -x assembler-with-cpp \
    -MD -MF "$OUT/gq5012bf1.d" -MT "$OUT/gq5012bf1.dtbo" \
    -o "$OUT/gq5012bf1.dts.tmp" "$DTS"
"$DTC_BIN" -O dtb -b 0 -i "$D/mediatek" -i "$D" \
    -Wno-interrupt_provider -Wno-unit_address_vs_reg -Wno-avoid_unnecessary_addr_size \
    -Wno-alias_paths -Wno-graph_child_address -Wno-simple_bus_reg -Wno-unique_unit_address \
    -Wno-avoid_default_addr_size -Wno-reg_format -Wno-graph_endpoint -Wno-pci_device_bus_num \
    -Wno-pci_device_reg -Wno-spi_bus_reg \
    -@ -o "$OUT/gq5012bf1.dtbo" "$OUT/gq5012bf1.dts.tmp"

# 2. Android DT table. mkdtboimg pads the file to the page size; the table
#    itself ends at the header's total_size, which is what stock ships.
$MKDTBOIMG_CMD create "$OUT/dtbo-table.padded" --page_size=$PAGE_SIZE \
    --id=0 --rev=0 --version=0 "$OUT/gq5012bf1.dtbo"
python3 - "$OUT/dtbo-table.padded" "$OUT/dtbo-table.img" <<'EOF'
import struct, sys
d = open(sys.argv[1], "rb").read()
total = struct.unpack(">I", d[4:8])[0]
assert not any(d[total:]), "non-zero bytes after total_size"
open(sys.argv[2], "wb").write(d[:total])
EOF
rm -f "$OUT/dtbo-table.padded"

# 3. MediaTek cert blocks: reuse the stock ones only if they cover these bytes.
#    cert2 binds sha256(table[0:32]) and sha256(table+pad16 [32:cert1]).
CERT_STATUS="$(python3 - "$OUT/dtbo-table.img" "$STOCK" "$OUT/dtbo.img" <<'EOF'
import hashlib, struct, sys
table = open(sys.argv[1], "rb").read()
stock = open(sys.argv[2], "rb").read()
total = struct.unpack(">I", stock[4:8])[0]
end = len(stock)
if stock[-64:-60] == b"AVBf":
    end = struct.unpack(">Q", stock[-52:-44])[0]
magic = b"\x88\x16\x88\x58"
c1 = stock.find(magic, total, end)
padded = table + b"\0" * ((-len(table)) % 16)
status = "MTK_CERT_ABSENT"
if c1 >= 0:
    c2 = stock.find(magic, c1 + 4, end)
    certs = stock[c1:end]
    der_off = c2 + 512
    der_len = struct.unpack("<I", stock[c2 + 4:c2 + 8])[0]
    der = stock[der_off:der_off + der_len]
    def oidval(tail):
        k = b"\x06\x07\x60\x86\x76\x93\x16" + tail
        i = der.find(k)
        return der[i + 12:i + 44] if i >= 0 and der[i + 9:i + 11] == b"\x03\x21" else None
    ok = (len(padded) == c1
          and oidval(b"\x02\x04") == hashlib.sha256(padded[0:32]).digest()
          and oidval(b"\x02\x01") == hashlib.sha256(padded[32:]).digest())
    if ok:
        open(sys.argv[3], "wb").write(padded + certs)
        status = "STOCK_MTK_CERT_VALID"
if status != "STOCK_MTK_CERT_VALID":
    open(sys.argv[3], "wb").write(table)
print(status)
EOF
)"
if [ "$CERT_STATUS" != "STOCK_MTK_CERT_VALID" ] && [ "$ALLOW_UNSIGNED" != 1 ]; then
    die "built DT table differs from the bytes the stock MediaTek cert2 covers;
    LK img_auth acceptance of an uncertified dtbo is untested on GQ5012BF1.
    Re-run with --allow-unsigned (LIEPPOS_DTBO_ALLOW_UNSIGNED=true) only for a
    planned hardware test. Output left in $OUT/dtbo.img."
fi

# 4. Optional AVB footer (hash descriptor, partition name dtbo, no key: the
#    descriptor lives in the root vbmeta, as on stock).
if [ -n "$AVBTOOL_CMD" ]; then
    cp "$OUT/dtbo.img" "$OUT/dtbo-avb.img"
    $AVBTOOL_CMD add_hash_footer --image "$OUT/dtbo-avb.img" --partition_name dtbo \
        --partition_size "$PART_SIZE" ${SALT:+--salt "$SALT"} "${AVB_EXTRA[@]}"
fi

# 5. Report.
ENTRY_SHA=$(sha256sum "$OUT/gq5012bf1.dtbo" | cut -d' ' -f1)
STOCK_ENTRY_SHA=$($TOOL --entry 0 extract "$STOCK" "$OUT/stock-entries" >/dev/null && \
    sha256sum "$OUT/stock-entries/entry-00-id-00000000-rev-00000000.dtbo" | cut -d' ' -f1)
{
    echo "LIEPPOS_DTBO_SOURCE=source"
    echo "built_from=$DTS"
    echo "kernel_src_git=$(git -C "$KSRC" -c safe.directory='*' rev-parse HEAD 2>/dev/null || echo unknown)$(git -C "$KSRC" -c safe.directory='*' status --porcelain -- arch/arm64/boot/dts 2>/dev/null | grep -q . && echo -dirty || true)"
    echo "dtc=$("$DTC_BIN" --version | head -1)"
    echo "entry_sha256=$ENTRY_SHA"
    echo "stock_entry_sha256=$STOCK_ENTRY_SHA"
    echo "entry_vs_stock=$([ "$ENTRY_SHA" = "$STOCK_ENTRY_SHA" ] && echo BYTE_IDENTICAL || echo DIFFERS)"
    echo "mtk_cert=$CERT_STATUS"
    echo "dtbo_img=$OUT/dtbo.img $(stat -c %s "$OUT/dtbo.img") bytes sha256 $(sha256sum "$OUT/dtbo.img" | cut -d' ' -f1)"
    [ -n "$AVBTOOL_CMD" ] && echo "dtbo_avb_img=$OUT/dtbo-avb.img sha256 $(sha256sum "$OUT/dtbo-avb.img" | cut -d' ' -f1)"
    true
} > "$OUT/BUILD-REPORT.txt"
rm -rf "$OUT/stock-entries" "$OUT/gq5012bf1.dts.tmp"
cat "$OUT/BUILD-REPORT.txt"
