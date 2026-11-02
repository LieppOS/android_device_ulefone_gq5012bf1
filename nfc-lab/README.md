# NFC Lab platform integration — source/build delivery

## Scope and status

**PARTIAL runtime integration, disabled by default; full NFC APEX/app host build now verified.** Following scoped owner approval, the patched NFC APEX and app completed a real Android17/arm64 Soong build (25202 actions, exit0), followed by rebuilt SELinux policy/context checks. Artifact signatures and payload AVB integrity verify offline. This is **not** a complete ROM/VINTF qualification, installation, runtime permission/lifecycle test or RF test. Initial SDK/helper checks below remain narrower evidence, not substitutes for this full build.

No production NFC configuration, firmware, routing, controller state, live labels or enforcement was changed. The only fresh phone inspection was read-only storage-label metadata, described below.

## Exact source baseline

Located read-only reference projects in the existing Lineage24 tree:

| Project | Actual inspected revision |
|---|---|
| packages/modules/Nfc | `5b3b95382170fde2d778f8521e6ae3fcbc73307a` |
| hardware/st/nfc | `7cf8d50bd425329cff555fe94dd64b20c89ad18a` |
| hardware/interfaces | `1b92b77fe1f2f2c820c51b0b1e366c17d6b9911b` |

These supersede blindly using the older upstream research revisions as a patch base. They do not independently prove binary identity with the installed APEX. The canonical framework source checkouts are absent. The initial delivery left the Lineage reference unmodified. The owner subsequently authorized scoped NFC/app/device writes and the full APEX build there; source files are now user-writable, while some Git metadata remains root-owned. This task made no permission/remote changes. The exact pinned patch is applied in that existing tree; its HEAD pin is unchanged. Patches still belong to this device repository's existing mechanism, not another Android clone.

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
- The lab controller fails-stop and adds no automatic retry/recovery. Existing native framework watchdogs still apply (see the audit below). Cleanup returning is not proof that normal RF behavior was restored. Binder death/expiry/token handling is explicit; no global route-restoration claim is made without device validation.

The app has a real separate client and read/write controls. Debug signing does not grant either signature permission. Source/build gates remain off; no live enablement or controller-memory operation was run.

## Product/SELinux integration

`device.mk` includes `nfc-lab.mk`; it changes package/property/init selection only with `LIEPPOS_NFC_LAB=true` on API37. The source app module must be synchronized into the actual Android build tree; otherwise the explicit opt-in should fail, not silently omit the app. This task does not alter manifest project ownership or clone new framework trees.

The opt-in profile includes the lab app, sets the compatibility gate **false**, and includes a narrowly scoped init storage fix. It does not change ST firmware/configuration or enable the operational resource flag.

**VERIFIED fresh passive finding:** `/data/nfc` exists as nfc:nfc, mode0770, context `system_data_file`, with SELinux Enforcing. Installed context declarations inspected did not contain an NFC-specific mapping for that path. Actual `NfcInjector.java` uses `/data/nfc`; platform policy grants nfc access to `nfc_data_file`, not blanket access to system_data_file. This establishes a remaining label mismatch, **not a new successful persistence-write test**.

Source fix:

- `sepolicy/system_ext/private/file_contexts`: `/data/nfc(/.*)? -> nfc_data_file` only.
- Opt-in `init.lieppos-nfc-lab.rc`: correct owner/mode plus restorecon of that directory at post-fs-data.
- No new allow rule, direct-controller permission, permissive domain or live relabel.

Initially the regex compiled with `sefcontext_compile` and `checkfc` accepted its type against an existing reference policy. The authorized follow-up rebuilt the actual product policy and passed `system_ext_file_contexts_test`, `sepolicy_neverallows` and `sepolicy_test`; the merged system_ext contexts contain the narrow NFC mapping. See the warnings and limits below. `/data` labels are shared across slots: deployment/relabeling and Slot A compatibility require explicit approval and tests before booting such a build.

## Offline reproduction

With the app repository and read-only pinned NFC reference already present:

```sh
python3 nfc-lab/prepare_patch.py /path/to/packages/modules/Nfc --check
python3 nfc-lab/test_offline.py /path/to/packages/modules/Nfc \
  --app /path/to/NFC-ESP32-Android
```

Optionally supply `--policy /path/to/existing/precompiled_sepolicy` for `checkfc` type validation. Source/reference files remain unmodified. Outputs go to canonical `build/nfc-lab-platform/` by default; override `NFC_LAB_PLATFORM_OUT` if needed.

Recorded checks: patch reproducibility/application, native ASan/UBSan parser/gating tests with20000 malformed frames and concurrent snapshots; both Binder contracts/new owner services API-compilation;21 Type4 policy/ownership/CC/bounds/read-only/fail-stop simulation checks; exact JNI getter compilation; default-off product profile/API-version rejection; narrow context compilation/reference-policy type validation. Mock port tests are explicitly not hardware verification.

## Authorized full-platform build follow-up

The same existing Lineage24 tree was authorized for scoped integration; no extra Git repository/worktree or Android tree was created. The reviewed app commit `61afd2a601173568d91b3faf0fddfd9fa0e7a121` was exported (Android.bp/LICENSE/PROVENANCE/src only) to `packages/apps/LieppOSNfcLab` with source-export metadata. This is a build-only projection, not a new canonical source owner or a completed manifest migration.

A real graph failure exposed missing standard `lineageVarsPlugin` exports. Full-ROM `BoardConfig.mk` now conditionally includes the existing upstream `vendor/lineage/config/BoardConfigSoong.mk`. It exports existing values; it does not inherit kernel-rebuild defaults, add headers, change the prebuilt kernel or alter the separate recovery branch.

Successful build settings, from the authorized Lineage source root:

```sh
OUT_DIR=out-nfc-lab TARGET_PRODUCT=lineage_gq5012bf1 TARGET_RELEASE=cp2a \
TARGET_BUILD_VARIANT=userdebug LIEPPOS_NFC_LAB=true SOONG_NINJA=ninja \
ALLOW_BP_UNDER_SYMLINKS=false build/soong/soong_ui.bash --make-mode -j12 \
    com.android.nfcservices LieppOSNfcLab
```

`out-nfc-lab` is a new output-only symlink to canonical `build/nfc-lab/full-apex`; existing Lineage outputs are preserved. The relative spelling avoids an unrelated absolute-OUT_DIR path-validation error. Supported Ninja was selected after Siso could not load its generated main.star; no dependency, sandbox, API, SELinux, AVB or path check was disabled. All failure/retry logs are preserved.

Actual follow-up results:

- Complete JNI/native adaptation, owner AIDL/Java/resources/R8, APEX/CAPEX and app build: **PASS**,25202 actions.
- APEX/CAPEX/owner/app signatures: **PASS**; app and inner NFC-owner APK certificates match. **Local AOSP test keys**, not production/retail signing authorization.
- Payload AVB signature/hashtree: **PASS**; embedded public key matches the declared source public key.
- Actual AArch64 JNI: metadata getter present and one linked shared cache; libnfc-nci remains statically linked.
- Compiled manifest: distinct signature permissions; host CE components disabled; operational service resolves to `lieppos_nfc_lab_type4_enabled=false`.
- Rebuilt product `sepolicy_test`, `system_ext_file_contexts_test`, `sepolicy_neverallows`: **exit0**,43 actions. The upstream test emitted125 `isolated_compute_allowed_property_type does not exist` diagnostics, and checkpolicy emitted a no-permission-set warning. These are disclosed, not hidden or fixed outside NFC scope; passing tests do not establish complete security coverage.
- Upstream API documentation/link warnings and the current DEX tool's API37 warning are retained in logs; no target API downgrade or warning suppression was used.
- `check-vintf-all` expanded into80689 whole-platform actions. Only that oversized attempt was intentionally stopped; **complete VINTF/ROM validation remains pending**, not passed or proven incompatible.

Outputs and logs are under canonical `build/nfc-lab/`. `full-apex-inputs.json` records1238 platform project SHAs and reviewed app export/board hashes; it does not claim every other platform working tree was clean or a hermetic build. `full-apex-artifact-verification.json` records exact artifact paths/hashes/signature checks. Nothing was installed or pushed.

Native audit found a real enablement blocker in the unchanged upstream Type4 path: `setup()`/`cleanup()` can restart discovery without preserving its initial stopped state, and cleanup close failures are logged without being reflected in an otherwise successful data result. Existing `NativeNfcManager::startRfDiscovery()` can also invoke normal NFCC-timeout recovery. The **new layer** adds no automatic retry/recovery, but it cannot promise that the **existing stack** never recovers. Keep the operational resource/configuration gates off until narrowly tested native hardening and explicit runtime/RF approval.

## Reproducible integration (replaces the temporary export)

The app is now a **manifest project**, `packages/apps/LieppOSNfcLab` from
`LieppOS/NFC-ESP32-Android`, declared in `manifests/android_manifest/default.xml`.
The build tree's copy is a real VCS checkout of the reviewed commit, not a
hand-copied export. Integration is one documented, idempotent, reversible step:

```sh
# after the tree is synced; applies the pinned patch only, nothing else
python3 device/ulefone/gq5012bf1/nfc-lab/integrate.py <android-tree> --apply
python3 device/ulefone/gq5012bf1/nfc-lab/integrate.py <android-tree> --revert
```

`integrate.py` verifies the NFC project is at the pinned revision, reports the
app project's checkout and origin, refuses to touch a tree that neither matches
nor accepts the patch, and performs no sync, fetch, push, build, install or
device operation. Applying twice is a no-op; `--revert` restores the tree.

**Honest limitation:** the lab commits are local and unpushed, so a fresh
`repo sync` of `main` does not yet contain them. Until they are reviewed onto
`main` and pushed, a clean-room reproduction needs those commits supplied
explicitly. The patch itself is fully reproducible from `prepare_patch.py`.

## Lifecycle hardening

`overlay/NfcNci/nci/jni/LiepposT4tLifecycle.h` holds the setup/cleanup policy
that the patched `NativeT4tNfcee` now uses. It re-observes discovery state
instead of assuming requests took effect, never starts discovery it did not
itself stop, refuses reentrant operations, closes exactly once, is idempotent,
and reports a degraded verdict when a close fails or restoration cannot be
confirmed. The verdict reaches the lab gate through cache slots 35/36, so a
degraded cleanup closes the session and blocks new ones; it is also shown in
diagnostics as `type4_lifecycle`.

It does **not** replace, suppress or retry the existing NFCC recovery path:
`startRfDiscovery()` can still time out and let the stack recover on its own.
"Degraded" means restoration is unverified, not that it was repaired.

`tests/t4t_lifecycle_test.cc` drives the shipped object through a mock of the
existing stack: nominal round trip, discovery already stopped, ignored stop
request, open failure, close failure, failed restoration, idempotent cleanup,
sticky degraded verdict, reentrancy, NFC-off, shutdown abandon, timeout-shaped
failure, per-session verdict reset and an 8-thread contention invariant.

## Remaining engineering

1. Push the reviewed commits so a plain `repo sync` reproduces the build inputs.
2. Run actual framework Binder/lifecycle/native integration tests and complete VINTF/product qualification; offline build/signature/policy success does not establish runtime behavior.
3. Harden/test the native Type4 discovery/close-error paths before enabling its lab resource. The new layer refuses retries; it does not magically fix native restoration.
4. Review the kernel exclusive-open race and recovery error paths with ABI/KMI/module builds before any source change; none was made just to claim kernel work.
5. Only after separate approval, perform owned-reader NFCEE RF/read/write/persistence and normal-reader/HCE regression tests. No automatic approval is implied.
6. Generic exclusive RF/Type2/UID/SAK/P2P/low-power controls, full routing/SE/IRQ diagnostics and external instrument transports remain unimplemented/unverified; the app catalogue lists all59 original features explicitly.

Origin: new lab sources/tests are **INDEPENDENT**, Apache-2.0; the generated patch is **UPSTREAM_MODIFIED** against the exact Lineage/AOSP sources and retains their notices. No proprietary firmware, calibration payload, secret or raw diagnostic dump is included. Local commits only; no push.
