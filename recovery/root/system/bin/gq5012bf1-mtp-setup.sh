#!/system/bin/sh
#
# Stage 1 of MTP bring-up: create the MTP FunctionFS instance.
#
# GQ5012BF1 composes USB through configfs. The gadget ships with only ffs.adb
# and ffs.fastboot, and the kernel has no MTP gadget function at all: mtp.gs0
# cannot be instantiated and /proc/devices lists no MTP entry, so the legacy
# /dev/mtp_usb control node that TWRP falls back to does not exist here.
#
# TWRP's MTP server prefers FunctionFS when /dev/usb-ffs/mtp/ep0 is writable
# (mtp_MtpServer.cpp), so creating the ffs.mtp function and mounting
# FunctionFS on it is enough to get a working transport without any legacy
# android_usb involvement.
#
# This runs before the MTP server starts. It deliberately does NOT touch the
# UDC: the gadget cannot bind a FunctionFS function until its descriptors have
# been written, which only happens once the server opens ep0. Binding is done
# in stage 2 (gq5012bf1-mtp-bind.sh), triggered by sys.usb.ffs.mtp.ready.

G=/config/usb_gadget/g1
FFS=/dev/usb-ffs/mtp

log() { echo "mtp-setup: $*"; }

[ -d "$G" ] || { log "no configfs gadget at $G, nothing to do"; exit 0; }

# Create the FunctionFS function instance named "mtp".
if [ ! -d "$G/functions/ffs.mtp" ]; then
    mkdir "$G/functions/ffs.mtp" 2>/dev/null \
        || { log "cannot create ffs.mtp function"; exit 1; }
    log "created ffs.mtp function"
fi

mkdir -p "$FFS" 2>/dev/null

# Mount FunctionFS. The mount source must match the function instance name.
if ! grep -q " $FFS " /proc/mounts 2>/dev/null; then
    if mount -t functionfs mtp "$FFS" -o rmode=0770,fmode=0660,uid=0,gid=0 2>/dev/null; then
        log "mounted functionfs at $FFS"
    else
        log "failed to mount functionfs at $FFS"
        exit 1
    fi
fi

# Deliberately NOT setting sys.usb.config here.
#
# Build33 set it to "mtp,adb" to make Enable_MTP() skip its legacy path. That
# backfired: something outside recovery acts on sys.usb.config and recomposed
# the gadget as MTP-only, dropping ffs.adb and resetting idProduct to 0x0000.
# The host then enumerated a single Imaging/MTP interface with no ADB:
#
#   idProduct 0x0000, bNumInterfaces 1, bInterfaceClass 6 Imaging, iInterface MTP
#
# Enable_MTP() is instead patched to skip the legacy android_usb sequence when
# the FunctionFS endpoint exists, so nothing touches sys.usb.config at all and
# gadget composition stays entirely with gq5012bf1-mtp-bind.sh.

log "ready, waiting for the MTP server to write descriptors"
exit 0
