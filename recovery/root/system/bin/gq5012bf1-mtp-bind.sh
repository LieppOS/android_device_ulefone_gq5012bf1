#!/system/bin/sh
#
# Stage 2 of MTP bring-up: add the MTP function to the live gadget.
#
# Triggered by sys.usb.ffs.mtp.ready=1, which MtpDescriptors.cpp sets after the
# MTP server has written the FunctionFS descriptors to ep0. Only at that point
# can the gadget bind the function; doing it earlier makes the UDC write fail
# and would leave USB down entirely.
#
# A configfs gadget cannot be modified while bound, so the UDC is unbound,
# ffs.mtp is linked into the existing config next to ffs.adb, and the UDC is
# rebound. USB drops for a moment and the host re-enumerates the device with
# both MTP and ADB interfaces present. ADB reconnects on its own.

G=/config/usb_gadget/g1
CONFIG="$G/configs/b.1"
LINK="$CONFIG/f2"

log() { echo "mtp-bind: $*"; }

[ -d "$G" ] || { log "no configfs gadget, nothing to do"; exit 0; }

# Already linked (for example the service ran twice) - do not disturb USB.
if [ -e "$LINK" ]; then
    log "ffs.mtp already linked, leaving the gadget alone"
    exit 0
fi

if [ ! -d "$G/functions/ffs.mtp" ]; then
    log "ffs.mtp function missing, stage 1 did not complete"
    exit 1
fi

UDC="$(cat "$G/UDC" 2>/dev/null)"
[ -n "$UDC" ] || UDC="$(ls /sys/class/udc 2>/dev/null | head -1)"
if [ -z "$UDC" ]; then
    log "no UDC available"
    exit 1
fi

# Preserve the identifiers. Build33 came back as 18d1:0000 because the gadget
# was recomposed behind our back, so they are captured and restored explicitly.
VID="$(cat "$G/idVendor" 2>/dev/null)"
PID="$(cat "$G/idProduct" 2>/dev/null)"
log "UDC $UDC, ids ${VID}:${PID}"

# Unbind, add the function, rebind.
echo "" > "$G/UDC" 2>/dev/null

# ADB must survive. If its function link is missing, put it back before binding,
# otherwise the gadget comes up as MTP-only and the device drops off ADB.
if [ ! -e "$CONFIG/f1" ] && [ -d "$G/functions/ffs.adb" ]; then
    log "ffs.adb link was missing, restoring it"
    ln -s "$G/functions/ffs.adb" "$CONFIG/f1" 2>/dev/null
fi

if ! ln -s "$G/functions/ffs.mtp" "$LINK" 2>/dev/null; then
    log "failed to link ffs.mtp, restoring previous gadget"
    echo "$UDC" > "$G/UDC" 2>/dev/null
    exit 1
fi

# Restore identifiers in case anything cleared them while unbound.
[ -n "$VID" ] && echo "$VID" > "$G/idVendor" 2>/dev/null
[ -n "$PID" ] && echo "$PID" > "$G/idProduct" 2>/dev/null

if echo "$UDC" > "$G/UDC" 2>/dev/null; then
    log "gadget rebound: $(ls $CONFIG | grep '^f' | tr '\n' ' ')ids $(cat $G/idVendor 2>/dev/null):$(cat $G/idProduct 2>/dev/null)"
    exit 0
fi

# Binding failed with MTP present. Roll back so ADB is not lost.
log "rebind failed with ffs.mtp, rolling back to adb only"
rm -f "$LINK" 2>/dev/null
echo "$UDC" > "$G/UDC" 2>/dev/null
exit 1
