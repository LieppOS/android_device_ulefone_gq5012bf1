#!/system/bin/sh

LOG=/tmp/gq5012bf1-security-setup.log
exec >>"$LOG" 2>&1

echo "===== gq5012bf1 security setup ====="

SLOT="$(getprop ro.boot.slot_suffix)"
[ -n "$SLOT" ] || SLOT="_a"

SYSTEM_DEV="/dev/block/mapper/system${SLOT}"
VENDOR_DEV="/dev/block/mapper/vendor${SLOT}"
SYSTEM_MNT="/mnt/system${SLOT}"

WAIT=0
while [ ! -e "$SYSTEM_DEV" ] || [ ! -e "$VENDOR_DEV" ]; do
    WAIT=$((WAIT + 1))
    if [ "$WAIT" -ge 60 ]; then
        echo "mapper wait timeout: system=$SYSTEM_DEV vendor=$VENDOR_DEV"
        exit 10
    fi
    sleep 1
done
echo "mappers ready after ${WAIT}s"

mkdir -p "$SYSTEM_MNT" /vendor /mnt/vendor/persist /mnt/vendor/protect_f

grep -q " $SYSTEM_MNT " /proc/mounts ||
    mount -t erofs -o ro "$SYSTEM_DEV" "$SYSTEM_MNT" ||
    exit 11

grep -q " /vendor " /proc/mounts ||
    mount -t erofs -o ro "$VENDOR_DEV" /vendor ||
    mount -t erofs -o ro /dev/block/by-name/vendor /vendor ||
    exit 12

grep -q " /mnt/vendor/persist " /proc/mounts ||
    mount -t ext4 -o rw /dev/block/by-name/persist /mnt/vendor/persist ||
    exit 13

grep -q " /mnt/vendor/protect_f " /proc/mounts ||
    mount -t ext4 -o rw /dev/block/by-name/protect1 /mnt/vendor/protect_f ||
    exit 14

SYSTEM_PROP="$SYSTEM_MNT/system/build.prop"
VENDOR_PROP=/vendor/build.prop

read_prop() {
    grep -m 1 "^${1}=" "$2" | cut -d= -f2-
}

# KeyMint binds key blobs to the OS version and rejects them with
# ErrorCode::INVALID_KEY_BLOB (TEE return -33) when it does not match. The
# active synthetic-password blobs were created by the installed system, so the
# release must come from that system, not from the Android 14 recovery.
# Gatekeeper reads no build property at all, so there is no split identity.
RELEASE="$(read_prop ro.build.version.release "$SYSTEM_PROP")"
PLATFORM_SPL="$(read_prop ro.build.version.security_patch "$SYSTEM_PROP")"
VENDOR_SPL="$(read_prop ro.vendor.build.security_patch "$VENDOR_PROP")"

[ -n "$RELEASE" ] || exit 21
[ -n "$PLATFORM_SPL" ] || exit 22
[ -n "$VENDOR_SPL" ] || exit 23

RESETPROP=/sbin/resetprop
[ -x "$RESETPROP" ] || RESETPROP=/system/bin/resetprop
[ -x "$RESETPROP" ] || exit 24

"$RESETPROP" ro.build.version.release "$RELEASE"
"$RESETPROP" ro.build.version.security_patch "$PLATFORM_SPL"
"$RESETPROP" ro.vendor.build.security_patch "$VENDOR_SPL"

echo "release=$RELEASE"
echo "platform_spl=$PLATFORM_SPL"
echo "vendor_spl=$VENDOR_SPL"

TASK_PROFILES="$SYSTEM_MNT/system/etc/task_profiles.json"
[ -f "$TASK_PROFILES" ] || exit 31
cp "$TASK_PROFILES" /etc/task_profiles.json || exit 32
chown root:root /etc/task_profiles.json
chmod 0644 /etc/task_profiles.json

rm -rf /system/etc/vintf
mkdir -p /system/etc/vintf/manifest || exit 41
cp /system/etc/gq5012bf1-vintf/manifest.xml /system/etc/vintf/manifest.xml || exit 42
cp /system/etc/gq5012bf1-vintf/android.system.keystore2-service.xml /system/etc/vintf/manifest/android.system.keystore2-service.xml || exit 43
chmod 0644 /system/etc/vintf/manifest.xml /system/etc/vintf/manifest/android.system.keystore2-service.xml

[ ! -e /dev/teeperf ] || { chown system:system /dev/teeperf; chmod 0660 /dev/teeperf; }
[ ! -e /dev/tkcore_admin ] || { chown system:system /dev/tkcore_admin; chmod 0600 /dev/tkcore_admin; }
[ ! -e /dev/tkcore_client ] || { chown root:system /dev/tkcore_client; chmod 0660 /dev/tkcore_client; }
[ ! -e /dev/tkcore_fp ] || { chown root:system /dev/tkcore_fp; chmod 0660 /dev/tkcore_fp; }
[ ! -e /dev/rpmb0 ] || { chown root:system /dev/rpmb0; chmod 0660 /dev/rpmb0; }
[ ! -e /dev/0:0:0:49476 ] || chown system /dev/0:0:0:49476

restorecon /mnt/vendor/persist 2>/dev/null
mkdir -p /mnt/vendor/persist/t6
chown system:system /mnt/vendor/persist/t6
restorecon /mnt/vendor/persist/t6 2>/dev/null

restorecon /mnt/vendor/protect_f 2>/dev/null
mkdir -p /mnt/vendor/protect_f/tee
chown system:system /mnt/vendor/protect_f/tee
restorecon /mnt/vendor/protect_f/tee 2>/dev/null

# Stage 1 ends here. TrustKernel secure file storage lives on /data
# (teed --datapath /data/vendor/t6/fs), which is still encrypted at this
# point, so we must not claim it is ready yet. Stock trustkernel.rc uses the
# same two-stage handshake: announce "prepare", create the storage once /data
# exists, and only then announce "ready". Declaring "ready" early is what
# produced CreatePersistentObject 0xf0100003 (TEE_ERROR_STORAGE_NOT_AVAILABLE).
setprop vendor.trustkernel.fs.mode 3
setprop vendor.trustkernel.fs.state prepare

echo "security setup complete (stage 1, awaiting /data)"
exit 0
