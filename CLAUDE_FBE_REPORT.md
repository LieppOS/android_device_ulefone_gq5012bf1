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
