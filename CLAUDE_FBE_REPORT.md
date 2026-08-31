# GQ5012BF1 OrangeFox enforcing FBE — final report

**Result: achieved.** Cold boot into OrangeFox with SELinux **enforcing**, enter the correct PIN once, Android 16 user-0 `/data` decrypts. No ADB intervention. Recovery is usable in ~26 s and reboots are repeatable with no splash hang.

Shipped as `bbe7af2` (on top of `cedb65b`, `fa6733c`). Working image:
`gq5012bf1-artifacts/build30/vendor_boot_a-orangefox-FULL64M-BUILD30.img`

---

## 1. Verified evidence

```text
I:Successfully decrypted metadata encrypted data partition
using secdis to decrypt spblob
GateKeeper status ok
spblob v2 / v3
Data successfully decrypted

twrp.user.0.decrypt = 1
getenforce           = Enforcing
/data                = /dev/block/dm-15 f2fs (inlinecrypt)
/data/system_ce/0    = accounts_ce.db, activity_snapshots, appsearch, appwidget
/data/data           = android, android.ext.services, android.ext.shared
enforcing AVC denials for tee/keymint/gatekeeper/keystore/recovery: none
```

Image invariants (every build): PLATFORM `9201a4e5c1b7cb1f…`, DTB `bc156c29c33d8226230f07888df0a3d7a1e9c4b85c5fd550a4c4bd1a3134c0d4`, exact 64 MiB, AVB `NONE` / `vendor_boot` / stock salt + fingerprint. Only `vendor_boot_a` was ever written. No vbmeta, slot or partition changes.

---

## 2. Root causes fixed

### 2.1 Missing `link` permission — the decisive one

TrustKernel commits a persistent object by **hard-linking** its staged block file. This fired 25 ms before every failed unwrap:

```text
avc: denied { link } for name="block0.1" dev="sdc17"
  scontext=u:r:tee:s0 tcontext=u:object_r:tkcore_protect_data_file:s0
  tclass=file permissive=0
```

In this tree `create_file_perms` expands to `{ create rename setattr unlink rw_file_perms }` — it does **not** include `link`. The existing grant looked complete but wasn't. Fix: `allow tee tkcore_protect_data_file:file link;`

### 2.2 `teed` could not traverse its own persistent stores

`persist_data_file` and `protect_f_data_file` were undeclared in the recovery policy, so both `teed --prot` mount roots resolved to `unlabeled`:

```text
avc: denied { search } dev="sdc17" trawcon="u:object_r:protect_f_data_file:s0"
avc: denied { search } dev="sdc9"  trawcon="u:object_r:persist_data_file:s0"
```

Fix: declare both types, label the mount roots, grant `tee` **`dir search` only**. Payload dirs keep `tkcore_protect_data_file`.

### 2.3 Gatekeeper and KeyMint sessions must be serialised

Build25/26 started both from `vendor.trustkernel.ready=true` **simultaneously** and reproduced:

```text
keystore2: enforcements.rs:616: No suitable auth token found.
keystore2: Error::Km(KEY_USER_NOT_AUTHENTICATED)
```

Fix: KeyMint from `vendor.trustkernel.ready=true`; Gatekeeper from `init.svc.vendor.keymint-3-0-trustkernel=running`; Keystore2 from `init.svc.vendor.gatekeeper=running`. **Ordering** is what matters, not delay length.

---

## 3. Structural constraint discovered

**In recovery the entire TrustKernel stack must start before `/data`.** Recovery blocks in `futex_wait_queue` at the splash until Gatekeeper *and* Keystore2 exist, and only then mounts `/data`. Proven directly: a build running only `teed` + KeyMint hung at the logo with `/data` never mounted.

Consequence: TrustKernel secure file storage on `/data/vendor/t6/fs` **cannot** exist when the TAs initialise, so stock's `prepare`→`ready` handshake cannot be reproduced literally in recovery.

> **Rule: never gate anything recovery depends on behind a property that only becomes true after `/data` is mounted.** I violated this and deadlocked the device at the logo; `gq5012bf1-tee-storage` is now purely opportunistic with nothing gated on it.

---

## 4. Claims from the prior investigation that are now withdrawn

| Prior claim | Status |
|---|---|
| Gatekeeper must initialise under `release=14`, KeyMint under `16` | **Disproven.** The Gatekeeper HAL binary contains **no** `ro.`/`vendor.`/`persist.` property string at all — it is a pure TEEC shim. It cannot read the release. |
| `ro.build.version.release` must be `16` before KeyMint starts | **Disproven.** Successful decryption was observed with release reading **14**. Not the decisive input. |
| The 90 s `tee-storage` timeout delay is load-bearing | **Disproven** by Build30, which uses a 5 s settle and works. I wrongly asserted this after a single success; the reboot hang you hit was caused by it. |
| Failure is `INVALID_KEY_BLOB` | Historically yes, but once storage was fixed the real blocker was `KEY_USER_NOT_AUTHENTICATED` / auth-token matching. |

---

## 5. Answers to the original questions

1. **Decrypt path** — `Decrypt_User` → `Decrypt_User_Synth_Pass` (`system/vold/Decrypt.cpp:718`) → Gatekeeper `verify` → `addAuthToken` → `unwrapSyntheticPasswordBlob` → `getKeyEntry` → `createOperation` (`forced=true`) → `finish` → AES-256-GCM → `PersonalizedHashSP800(FBE_KEY)` (v3) → `Decrypt_CE_storage`.
2. **Build26 remnants** — were **live**, not inert: an uncommitted `std::system("/system/bin/gq5012bf1-fbe-prepare.sh")` at the top of `Decrypt_User_Synth_Pass` plus the untracked script. Both reverted; `system/vold` is clean.
3. **Gatekeeper `Verify … return -1`** — the **TA's own status** (`ERROR_GENERAL_FAILURE`), a distinct log string from the TEEC-failure path. Aborts before KeyMint is reached.
4. **KeyMint `cmdId` and `-33`** — resolved from live logs against `TrustKernelKeyMintImplementation.cpp`: **16 = begin (:1774), 17 = update (:1880), 18 = finish (:1986)**. The HAL links AOSP `KeyMintUtils.cpp`, so `-33` is exactly `ErrorCode::INVALID_KEY_BLOB` returned by the TA.
5. **Identity inputs** — KeyMint reads `ro.build.version.release`, `ro.build.version.security_patch`, `ro.vendor.build.security_patch`, `ro.boot.verifiedbootstate`, `ro.boot.vbmeta.{device_state,digest}`, `ro.product.*`, at HAL startup. Gatekeeper reads nothing.
6. **A14 vs A16 semantics** — no gap found in the vold path: v3 SP800 derivation, `Domain::SELINUX`/`NAMESPACE_LOCKSETTINGS`, `forced=true`, and `hw_auth_token_t` endianness are all correct.
7. **"Why did the late manual attempt work?"** — because by then the TEE stack had been started in an order that serialised the Gatekeeper and KeyMint sessions, and its persistent stores were reachable. Not because of the release string.

*Note:* `tee_userinit` runs **once per secure-world lifetime** (`userinit already done`); restarting the Linux HALs does not redo it. Live iteration after first start is therefore limited — conclusions need a real reboot.

---

## 6. Honest notes

- 2.1 and 2.2 are proven by disappearing enforcing denials plus a successful decrypt. 2.3 is proven by A/B behaviour (simultaneous start reproduces the failure; serialised start does not); the *minimum* safe settle is not characterised — 5 s is empirical, not derived.
- The `EVP_CIPHER_CTX_ctrl(GCM_SET_TAG, …)` call in `unwrapSyntheticPasswordBlob` passes an **uninitialised** `tag` and ignores `EVP_DecryptFinal_ex`. Harmless here (GCM is CTR-based, so plaintext is correct) but it means GCM authentication is not actually verified. Upstream TWRP issue, left alone.
- `gq5012bf1-tee-storage` still times out in normal operation because `/data` never appears before it runs. That is now cosmetic — nothing depends on it — but it could be dropped from the boot path entirely.

## 7. Commands / artefacts

```
strings -a stock-security/android.hardware.gatekeeper-service.trustkernel | grep -E '^(ro|vendor|persist)\.'   # EMPTY
sesearch --allow -s tee -t tkcore_protect_data_file -c file <recovery sepolicy>
grep 'define(`create_file_perms' system/sepolicy/public/global_macros
python3 /tmp/vbrepack.py <build26 raw> <recovery.cpio.lz4> <out raw>
avbtool add_hash_footer --partition_name vendor_boot --partition_size 67108864 --algorithm NONE --salt 9c027417…
fastboot flash vendor_boot_a <build30 img>
```

Build30 recovery fragment `040a9e349e41ee4f1dcf048cdc562e2249b966bdc8c3b10fedcbded877da5d55`.


---

# Part 2 — Production bring-up (Build32)

FBE was the prerequisite; this part covers making the recovery actually usable.
Build32 artifact `cd2aeaa315090d74206a837afba1ce2cb86671c2e7fe94cd01dba84ae5ab9671`,
commit `52d2f09`.

## Battery — root cause and fix

OrangeFox does not read battery from sysfs on this branch. `TW_USE_LEGACY_BATTERY_SERVICES`
is not set, so `twrp.cpp` calls `GetBatteryInfo()`, which goes through the health HAL.

The HAL enumerates `/sys/class/power_supply/*` and reads each node's `type` file to
find the battery. Those files carried the generic `sysfs` label:

```text
avc: denied { read } for name="type" dev="sysfs"
  scontext=u:r:hal_health_default:s0 tcontext=u:object_r:sysfs:s0
  tclass=file permissive=0
W healthd : No battery devices found
W healthd : battery none chg=
```

`getCapacity()` therefore failed, `capacity` stayed `INT32_MIN`, and
`battery_utils.cpp` substituted its no-battery fallback:

```text
W recovery: Using fake battery capacity 100.     <- real level was 78
```

Fix: label the power_supply nodes `sysfs_batteryinfo` via `genfscon`. **No new allow
rule was required** — `hal_health.te` already contains
`r_dir_file(hal_health_server, sysfs_batteryinfo)`. Because `/sys/class/power_supply/*`
are symlinks and SELinux labels the target inodes, each real device path is listed
individually rather than labelling a broad sysfs prefix. The MediaTek
`gftk_charger_type` node, polled continuously by the HAL, sits directly under the
charger platform device and is labelled as a single exact file.

Result: `GetBatteryInfo() reporting charging 1, capacity 78`, then `79` later in the
session — matching sysfs and updating live.

## Corrections to the mission brief

Two premises in the brief did not survive contact with the hardware.

**`gq5012bf1-tee-storage` is not obsolete.** The brief described a ~90 second wait for
a `/data` that "cannot exist at that point". That was Build28 behaviour. Under the
Build30 ordering `/data` mounts early and the service now completes normally:

```text
Service 'gq5012bf1-tee-storage' (pid 489) exited with status 0
  oneshot service took 7.348000 seconds in background
/data/vendor/t6/fs  -> tkcore_data_file
/data/vendor/t6/app -> tkcore_spta_file
```

It stages teed's datapath with correct labels, so it was kept per the brief's own rule
that nothing be removed until evidence confirms it obsolete.

**`android.hardware.health-service.example_recovery` was not the problem.** The brief
flagged it as suspicious on MTK hardware. It is in fact the correct generic AOSP
implementation and works properly once the sysfs nodes are labelled. No vendor health
HAL swap was needed.

## MTP — ported to FunctionFS (Build34)

MTP works and is composed alongside ADB rather than replacing it:

```text
configs/b.1/f1 -> ffs.adb
configs/b.1/f2 -> ffs.mtp
host: bNumInterfaces 2, iInterface "ADB Interface" + iInterface "MTP"
```

Verified on hardware: browsable from a Linux desktop file manager with ADB
still connected.

**No MTP server code was changed.** `mtp_MtpServer.cpp` already prefers
FunctionFS when `/dev/usb-ffs/mtp/ep0` is writable and only falls back to
`/dev/mtp_usb` otherwise. That legacy node cannot exist here — the kernel has no
MTP gadget function, `mtp.gs0` cannot be instantiated, and `/proc/devices` has no
MTP entry. So this was gadget composition plus a single recovery patch, not a
rewrite. My earlier assessment that it needed a full FunctionFS port was wrong:
the port already existed in the tree.

### The sequencing constraint

A FunctionFS function cannot bind to the UDC until its descriptors are written,
and that only happens once the server opens `ep0`. Binding earlier makes the UDC
write fail and takes USB down entirely, ADB included. Hence two stages:

1. `gq5012bf1-mtp-setup.sh` (`on boot`) creates `ffs.mtp`, mounts FunctionFS at
   `/dev/usb-ffs/mtp`, and deliberately does not touch the UDC.
2. `gq5012bf1-mtp-bind.sh`, triggered by `sys.usb.ffs.mtp.ready=1` which
   `MtpDescriptors.cpp` sets after writing descriptors, unbinds the UDC, links
   `ffs.mtp` beside `ffs.adb`, restores the identifiers, and rebinds.

### What failed first, and why

Build33 pre-set `sys.usb.config=mtp,adb` so `Enable_MTP()` would skip its legacy
block on its own. That broke ADB. Something outside recovery acts on
`sys.usb.config` and recomposed the gadget as MTP-only:

```text
idProduct 0x0000, bNumInterfaces 1, bInterfaceClass 6 Imaging, iInterface MTP
```

MTP worked; ADB was gone. `sys.usb.config` must not be written on this device.
The correct fix is patching `Enable_MTP()` to skip the legacy `android_usb`
sequence whenever the FunctionFS endpoint exists, leaving composition to init.

The same active USB manager also owns `idProduct`: writing `0x4ee2` succeeds and
reads back correctly immediately after rebinding, then reverts to `0xd001`
unprompted. So the product id cannot be changed from recovery, and `libmtp`
misidentifying `18d1:d001` as a Meizu Pro 5 is cosmetic.

### Host-side contention

On Linux both the ADB server and the desktop MTP client (KDE `kiod6`, or
`gvfsd-mtp`) claim the USB device, so `mtp-detect` and `gio` report
`libusb_claim_interface() reports device is busy`. That is host contention, not a
device fault — the desktop file manager browses the device fine while ADB stays
up.

### Build system note

Device inventory tooling clones `erofs-utils` into `device/ulefone/gq5012bf1/.work/`.
That path is gitignored, but soong does not read `.gitignore` and scans every
directory for `Android.bp`, so bootstrap aborts with `module ... already defined`.
`finder.go` treats `.out-dir` and `.find-ignore` as prune markers, so
`vendorsetup.sh` now drops a `.find-ignore` there automatically.

## Verified function matrix

Working and proven on hardware: cold-boot FBE decrypt under enforcing SELinux with a
single PIN; battery percentage/status/temperature with live updates; touch; ADB
including push and pull; fastbootd (`is-userspace: yes`); internal storage read/write
after decrypt; external SD (59 GB exFAT, auto-mounted at `/auto0-1` via `exfat-fuse`,
read/write verified); dynamic partitions `system`/`system_ext`/`product`/`vendor`
mounting read-only; slot display `_a`; backup (boot partition, 64 MB, digest, 2 s);
logs; RTC.

Explicitly **not** verified, and not claimed: charging-state transition to
`Discharging` (charger could not be removed); USB OTG (no device attached); restore;
ADB sideload; vibration; screenshot; the brightness UI slider (the sysfs node reads
1024 of max 2047, but the slider itself was not exercised).

`odm` has no logical partition — `/dev/block/mapper` exposes `odm_dlkm_a/b` but no
`odm_a` — so a failed `odm` mount is by design.

## Remaining denials

Two enforcing denials remain, both `rootfs` directory reads by `hal_health_default`
and `hal_bootctl_default`. Both HALs function correctly. Granting `rootfs` directory
read was rejected as too broad for no functional benefit.

## Packaging

`build-gq5012bf1.sh <n> full` now produces the flashable image in one command:
builds the recovery fragment, splices it into a full vendor_boot v4 preserving the
stock PLATFORM fragment and stock DTB, appends the AVB footer, verifies both
invariants and the exact 64 MiB size, prints path and SHA256, and warns that
`out/target/product/gq5012bf1/vendor_boot.img` is not flashable. It never flashes.
`vbrepack.py` and `vbunpack.py` are vendored into `tools/`; `vbunpack.py` was fixed to
print the full DTB SHA256 so the invariant check can actually match it (it previously
truncated to 16 characters, which silently defeated the check).
