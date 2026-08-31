#!/system/bin/sh
#
# TrustKernel secure-storage stage 2.
#
# teed is started with --datapath /data/vendor/t6/fs and --sptapath
# /data/vendor/t6/app, so TrustKernel secure file storage lives on /data.
# In recovery /data is metadata-encrypted and is mounted by OrangeFox some
# time after init has already run the boot triggers.
#
# Stock trustkernel.rc creates these directories in the fs.state=prepare
# handler and only then sets fs.state=ready. Doing it any earlier makes the
# trusted application fail with CreatePersistentObject 0xf0100003
# (TEE_ERROR_STORAGE_NOT_AVAILABLE), which in turn prevents Gatekeeper from
# committing its state and leaves Keystore2 with "No suitable auth token
# found". tee_userinit runs once per secure-world lifetime, so storage has to
# be correct before teed starts for the first time.

# NOTHING IN THE BOOT PATH IS GATED ON THIS SCRIPT. It runs in the background
# and only stages the teed datapath if and when /data appears. Recovery must
# never wait on a property that only this script can set.
WAIT=0
LIMIT=90

# Wait for the real, decrypted /data (metadata-encrypted f2fs on a dm device).
# This is FAIL-OPEN on purpose: teed and KeyMint are already running by now, so
# if /data never appears we must still declare ready and let Gatekeeper and
# Keystore2 start. Never leave recovery gated on a property that only this
# script can set, or the splash deadlocks.
while :; do
    if grep -q " /data " /proc/mounts 2>/dev/null; then
        break
    fi
    WAIT=$((WAIT + 1))
    if [ "$WAIT" -ge "$LIMIT" ]; then
        echo "tee-storage: timeout waiting for /data after ${LIMIT}s, declaring ready anyway"
        setprop vendor.trustkernel.fs.state ready
        exit 10
    fi
    sleep 1
done

echo "tee-storage: /data available after ${WAIT}s"

mkdir -p /data/vendor/t6/fs /data/vendor/t6/app
chown system:system /data/vendor/t6 /data/vendor/t6/fs /data/vendor/t6/app
chmod 0700 /data/vendor/t6 /data/vendor/t6/fs /data/vendor/t6/app
restorecon -R /data/vendor/t6 2>/dev/null

# Persistent (non-/data) stores. teed needs to traverse both mount roots;
# the device vendor policy defines persist_data_file and protect_f_data_file
# so those roots are no longer resolved as "unlabeled".
restorecon /mnt/vendor/persist /mnt/vendor/protect_f 2>/dev/null
mkdir -p /mnt/vendor/persist/t6 /mnt/vendor/protect_f/tee
chown system:system /mnt/vendor/persist/t6 /mnt/vendor/protect_f/tee
restorecon -R /mnt/vendor/persist/t6 /mnt/vendor/protect_f/tee 2>/dev/null

echo "tee-storage: secure storage staged, declaring ready"
setprop vendor.trustkernel.fs.state ready
exit 0
