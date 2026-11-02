# NFC Lab platform integration — source/build delivery

## Scope and status

**PARTIAL platform integration, disabled by default.** The new owner-service Java sources and Binder contracts compile against Android37 SDK; native cache/compatibility helpers pass host sanitizer tests; exact JNI getter typechecks; the generated patch passes `git apply --check` against the actual source revision. This is **not** a full NFC APEX, Soong product, SELinux-policy rebuild, installation or RF test.

No production NFC configuration, firmware, routing, controller state, live labels or enforcement was changed. The only fresh phone inspection was read-only storage-label metadata, described below.

## Exact source baseline

Located read-only reference projects in the existing Lineage24 tree:

| Project | Actual inspected revision |
|---|---|
| packages/modules/Nfc | `5b3b95382170fde2d778f8521e6ae3fcbc73307a` |
| hardware/st/nfc | `7cf8d50bd425329cff555fe94dd64b20c89ad18a` |
| hardware/interfaces | `1b92b77fe1f2f2c820c51b0b1e366c17d6b9911b` |

These supersede blindly using the older upstream research revisions as a patch base. They do not independently prove binary identity with the installed APEX. The canonical framework source checkouts are absent. The root-owned Lineage reference remains unmodified; patches belong to this device repository's existing patch mechanism, not an arbitrary new Android clone.

`overlay/` is the authoritative source for **new** patch files. `prepare_patch.py` combines those files with narrowly anchored edits to this exact reference revision and reproducibly generates:

`patches/packages_modules_Nfc/0001-lieppos-nfc-lab-cache-and-type4-compat.patch`

Do not hand-edit generated patch contents or apply it blindly to another revision. There is no auto-apply or deployment hook.

## Implemented paths

### Read-only diagnostics

`LabDiagnosticsService` is part of **com.android.nfc**, not a competing process opening `/dev/st21nfc`. A separate signature permission protects binding and every Binder call. Client and server AIDL contracts are checked byte-for-byte.

Native adaptation observes ordinary incoming NCI messages. A bounded40-integer cache retains only recognized reset identity, NCI revision, CORE_INIT status/interface IDs/capacities, generation/counts and effective Type4 configuration. Narrow ST decoding requires the known manufacturer/layout/HW04 pattern. Unknown/truncated/fragmented/unrecognized layouts stay UNKNOWN. No AID, UID, credential, APDU or general RF payload is retained.

The diagnostics getter does not call getRoutingTable, perform NFCEE discovery, query IRQ by ioctl, start recovery or initialize the controller. Route contents, physical SE status, IRQ level and recovery outcome remain unknown until a trustworthy passive cache exists. Driver sysfs reads fail closed when denied; no SELinux grant is added to force them through.

### Legacy HAL / Mainline Type4 bridge

The actual ST source inspected still does not populate `t4tNfceeEnable`. The patch preserves frozen AIDL and makes the compatibility fallback true **only** when:

1. `ro.product.vendor.device` is exactly `gq5012bf1`;
2. nonpersistent `nfc.lieppos.st21_t4t_compat` is explicitly enabled (defaultfalse);
3. the existing ST config identifies `nfc_nci.st21nfc` and `st21nfc_fw7.bin`;
4. `NDEF_NFCEE_ENABLE` is exactly1, without duplicate/conflicting entries.

A HAL already advertising true is preserved. Missing/denied/oversized/ambiguous config fails closed. Nothing writes the property or ST config. The property uses the existing platform `nfc.`/`nfc_prop` namespace; no broad new property permission is introduced. The normal product profile leaves it false.

### Operational controller NDEF API

`LabType4Service` is separate from diagnostics and has a distinct signature permission. The service component is disabled by a build resource (`lieppos_nfc_lab_type4_enabled=false`). It additionally requires the effective Type4 configuration and existing native readiness flags.

- Explicit Binder lifetime, caller UID, unpredictable token,60-second authorization and per-session write consent.
- Fixed E103 CC / E104 NDEF access only; no arbitrary file IDs, raw NCI, route tables, erase, reset or firmware commands.
- Mapping2.0 CC/file/access/capacity checks, maximum8190-byte NDEF message, Android NDEF validation and write readback.
- A shared manager monitor spans the lab transaction. Existing read/write/clear native Java entrypoints become synchronized on that same manager to prevent primitive interleaving with normal Type4 clients.
- Uses existing NativeT4tNfcee setup/cleanup, not a second transport. Native setup/cleanup can temporarily change discovery. This is why **even a read is an approved operational device test**, not passive diagnostics.
- Errors fail-stop without automatic retries or recovery. Cleanup returning is not proof that normal RF behavior was restored. Binder death/expiry/token handling is explicit; no global route-restoration claim is made without device validation.

The app has a real separate client and read/write controls. Debug signing does not grant either signature permission. Source/build gates remain off; no live enablement or controller-memory operation was run.

## Product/SELinux integration

`device.mk` includes `nfc-lab.mk`; it changes package/property/init selection only with `LIEPPOS_NFC_LAB=true` on API37. The source app module must be synchronized into the actual Android build tree; otherwise the explicit opt-in should fail, not silently omit the app. This task does not alter manifest project ownership or clone new framework trees.

The opt-in profile includes the lab app, sets the compatibility gate **false**, and includes a narrowly scoped init storage fix. It does not change ST firmware/configuration or enable the operational resource flag.

**VERIFIED fresh passive finding:** `/data/nfc` exists as nfc:nfc, mode0770, context `system_data_file`, with SELinux Enforcing. Installed context declarations inspected did not contain an NFC-specific mapping for that path. Actual `NfcInjector.java` uses `/data/nfc`; platform policy grants nfc access to `nfc_data_file`, not blanket access to system_data_file. This establishes a remaining label mismatch, **not a new successful persistence-write test**.

Source fix:

- `sepolicy/system_ext/private/file_contexts`: `/data/nfc(/.*)? -> nfc_data_file` only.
- Opt-in `init.lieppos-nfc-lab.rc`: correct owner/mode plus restorecon of that directory at post-fs-data.
- No new allow rule, direct-controller permission, permissive domain or live relabel.

The regex compiled with `sefcontext_compile`; `checkfc` accepted its type against an existing host reference policy. That is not a complete policy rebuild. `/data` labels are shared across slots: deployment/relabeling and Slot A compatibility require explicit approval and tests before booting such a build.

## Offline reproduction

With the app repository and read-only pinned NFC reference already present:

```sh
python3 nfc-lab/prepare_patch.py /path/to/packages/modules/Nfc --check
python3 nfc-lab/test_offline.py /path/to/packages/modules/Nfc \
  --app /path/to/NFC-ESP32-Android
```

Optionally supply `--policy /path/to/existing/precompiled_sepolicy` for `checkfc` type validation. Source/reference files remain unmodified. Outputs go to canonical `build/nfc-lab-platform/` by default; override `NFC_LAB_PLATFORM_OUT` if needed.

Recorded checks: patch reproducibility/application, native ASan/UBSan parser/gating tests with20000 malformed frames and concurrent snapshots; both Binder contracts/new owner services API-compilation;21 Type4 policy/ownership/CC/bounds/read-only/fail-stop simulation checks; exact JNI getter compilation; default-off product profile/API-version rejection; narrow context compilation/reference-policy type validation. Mock port tests are explicitly not hardware verification.

## Remaining engineering

1. Obtain the normal writable full Android source/build ownership and synchronize the app/framework projects through the canonical manifest process.
2. Apply/review the patch there, build the complete NFC APEX and product, run real framework Binder/lifecycle/native integration tests, and validate full VINTF/SELinux/product integration.
3. Audit existing native Type4 cleanup on all error paths before enabling its lab resource. The new layer refuses retries; it does not magically fix native restoration.
4. Review the kernel exclusive-open race and recovery error paths with ABI/KMI/module builds before any source change; none was made just to claim kernel work.
5. Only after separate approval, perform owned-reader NFCEE RF/read/write/persistence and normal-reader/HCE regression tests. No automatic approval is implied.
6. Generic exclusive RF/Type2/UID/SAK/P2P/low-power controls, full routing/SE/IRQ diagnostics and external instrument transports remain unimplemented/unverified; the app catalogue lists all59 original features explicitly.

Origin: new lab sources/tests are **INDEPENDENT**, Apache-2.0; the generated patch is **UPSTREAM_MODIFIED** against the exact Lineage/AOSP sources and retains their notices. No proprietary firmware, calibration payload, secret or raw diagnostic dump is included. Local commits only; no push.
