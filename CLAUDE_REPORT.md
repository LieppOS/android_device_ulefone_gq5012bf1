# Build19 logo-hang investigation report

## Executive finding

**Build19 hangs at the OrangeFox splash because `start vendor.boot-default` stopped being unconditional.** In Build18, `on boot` unconditionally executed `stop vendor.boot-default` **and** `start vendor.boot-default`, so the MediaTek recovery BootControl HAL was always (re)started regardless of whether security-prep succeeded. Build19 keeps the unconditional `stop vendor.boot-default` in `on boot` but moves the matching `start` (together with `restart logd` and `start teed`) into `on property:vendor.trustkernel.fs.state=ready`. That property is set **only by the final line (line 106) of `gq5012bf1-security-setup.sh`**, a script guarded by ~14 early-exit paths, including a brand-new `exit 10` 60-second dynamic-mapper timeout. This repository's own Build17 analysis proves that recovery *synchronously* requests `android.hardware.boot.IBootControl/default` and then blocks in `futex_wait_queue` **while sitting on the splash logo** when that HAL is unavailable — precisely the reported Build19 symptom. Confidence: **High** that the failure is this init/property gating regression, and **not** FBE, not SELinux policy, and not ramdisk corruption. The delta is a pure policy+rc delta: **no binary in the recovery ramdisk changed**.

**The likely failure is unrelated to FBE.** FBE/metadata encryption is downstream of the gate that never opens.

## Artifact integrity

- **Build18 recovery fragment**: `/home/armol/android/gq5012bf1-artifacts/build18/orangefox-build18-recovery.lz4`
  - size `33571785`, SHA256 `2e0b627d32ad0266aa477d773ad364070d116e9e418f42d7497548ea859f7e3f` — **matches the stated known-good value exactly (verified)**.
  - Decompressed CPIO: `94239744` bytes, **3943 entries** (3569 regular files).
- **Build19 recovery fragment**: **no standalone `.lz4` exists.** `build19/` contains only the two images. The authoritative fragment was extracted directly from the flashed image at ramdisk-table entry `[1] type=RECOVERY, offset=28759822`:
  - size `33572202`, SHA256 `4251932e0842d09e8f5991578169f0076cdd98425ca616f309536c8aa2027857`
  - Decompressed CPIO: `94268416` bytes, **3943 entries** (3569 regular files).
  - Identical fragment bytes in **both** `vendor_boot-build19-raw.img` and `vendor_boot_a-orangefox-FULL64M-BUILD19.img` (verified).
- **Was the flashed Build19 fragment current or stale?** **Current, not stale (verified).** All seven boot-relevant files inside the flashed CPIO byte-match `out/target/product/gq5012bf1/recovery/root/` at commit `da6c614`, including `vendor_property_contexts` = `ec23a1a236202eaa2a68cfb71297183cb851a6d216dd72d06eb908712f63cdc6` (size `1382`, the expected value).
- **Stock preservation constraint honoured (verified).** PLATFORM ramdisk fragment SHA256 `9201a4e5c1b7cb1fc0ce35375af10a3d966dac8b84615a226f98b7d7be2aec00` and DTB SHA256 `bc156c29c33d8226…` are **byte-identical** between Build18 and Build19, as is header geometry (v4, page 4096, dtb_size 342395). Only the recovery fragment differs (+417 bytes compressed).

## Earliest boot-relevant differences

The entire Build18→Build19 ramdisk delta is **10 files, 0 added, 0 removed, symlinks identical**. Four are non-functional build stamps.

1. **`init.recovery.gq5012bf1.security.rc`** (1432 → 1741) — `exec_start` → `start`, and `restart logd` / `start teed` / `start vendor.boot-default` moved out of `on boot` into a property trigger. **This is the regression.**
2. **`system/bin/gq5012bf1-security-setup.sh`** (3709 → 3836) — added a blocking 60 s wait for `/dev/block/mapper/system_a` + `vendor_a` with a new `exit 10`; removed the runtime `chcon` of the resolved `misc` node.
3. **`vendor_file_contexts`** (21549 → 22818) — +16 TrustKernel labels and `/dev/block/sdc1 → misc_block_device`.
4. `vendor_property_contexts` (826 → 1382) — +4 TrustKernel property labels. *(Note: this file already existed in Build18; the patch enriched it rather than adding it.)*
5. `sepolicy` (688418 → 691537) and `file_contexts.bin` (1256157 → 1279461) — recompiled.
6. Non-functional: `prop.default`, `system/etc/fox.cfg` (build date/UUID only — verified by diff), `ramdisk-files.txt`, `ramdisk-files.sha256sum` (derived manifests).

**Verified fact:** `/system/bin/recovery`, `/system/bin/init`, `/system/bin/keystore2`, `/system/bin/linker64`, libselinux, libsepol and **every other binary and library are byte-identical**. Hypothesis G (rebuilt binaries) is **falsified** — nothing was rebuilt beyond the policy/rc delta.

## Init/service analysis

**Verified init event graph** (recovery-fragment `init.rc` overrides the platform one; imports resolve as `logd → ldconfig → mksh → usb → service → mt6878 → {project (MISSING), gq5012bf1.security}`, `ro.hardware=mt6878`):

`on boot` actions execute in parse order:

1. `init.rc:77` → `class_start default` (**starts the `recovery` UI process**), `class_start hal`
2. `init.recovery.mt6878.rc` → `exec … mtk_plpath_utils`
3. `init.recovery.gq5012bf1.security.rc` → `stop keystore2`, `stop vendor.boot-default`, `start gq5012bf1-security-prep`

Answers to the required questions:

- `gq5012bf1-security-prep` is `class core`, `disabled`, `oneshot`, `seclabel u:r:recovery:s0` — **identical in both builds**. Only its invocation changed (`exec_start` → `start`).
- `gq5012bf1-security-setup.sh` is its payload; it runs at step 3, **after** the recovery UI process has already been started at step 1 — in *both* builds.
- **`vendor.trustkernel.fs.state=ready` is set only at line 106**, the last executable line of the script, after `exit 10/11/12/13/14/21/22/23/24/31/32/41/42/43`.
- `vendor.trustkernel.ready=true` is raised by `teed` — which itself only starts *after* the `fs.state=ready` trigger. **The whole security chain is serialized behind one property.**
- **Missed-trigger race: not applicable.** On a cold boot the property is unset before parsing, so the trigger is armed correctly. This is *not* an already-set-property race.
- **`vendor.boot-default` = `/system/bin/hw/android.hardware.boot-service.mtk_recovery`, `class early_hal` (verified).** **There is no `class_start early_hal` anywhere in the parsed rc set (verified).** Its only start paths are (a) the explicit `start` in the security rc, and (b) lazy start via its `interface aidl android.hardware.boot.IBootControl/default` declaration. Build19 removed (a) from the unconditional path while *keeping* the unconditional `stop`.
- **Startup dependency cycle: yes, a plausible one.** Recovery blocks on IBootControl → the script waits up to 60 s for mappers that recovery creates during the same startup it is blocked in → timeout `exit 10` → property never set → `vendor.boot-default` never started → recovery never unblocks.
- **Service conflict: real but downstream.** The generic `keystore2` (`system/etc/init/keystore2.rc`, `seclabel u:r:recovery:s0`, started by `on late-init`) and the new `gq5012bf1-keystore2` (`seclabel u:r:keystore:s0`) share the same binary and the same `/tmp/misc/keystore` directory. They are not simultaneously enabled on the failing path, and both are gated behind KeyMint, so this cannot be the logo-stage cause.
- **Does the async change alone prevent OrangeFox startup? No.** `start` is non-blocking and strictly *less* likely to stall init than Build18's blocking `exec_start`. The regression is **not** asynchrony itself — it is that asynchrony was implemented by making three previously unconditional commands conditional.

## Init parser/service validity (offline)

- **No duplicate service names** across the parsed rc set (verified).
- `group keystore readproc log` resolve to fixed Android AIDs; `seclabel u:r:keystore:s0` is valid — the `keystore` type exists in **both** policies (verified via `seinfo -t`).
- `writepid /dev/cpuset/foreground/tasks` is non-fatal if absent in recovery.
- **Pre-existing (not a regression):** `init.recovery.mt6878.rc` imports `/init.recovery.project.rc`, which **does not exist** in either ramdisk. Init logs this and continues; identical in Build18, so it is not the cause.

## SELinux/context analysis

Compiled-policy diff (`sesearch --allow`, setools):

| | Build18 | Build19 |
|---|---|---|
| Types | 1918 | 1930 |
| Allow rules | 33403 | 33542 |
| Permissive domains | 8 | 8 |

- **140 allow rules added, 0 genuinely removed (verified).** The single `comm` difference — `allow recovery selinuxfs:file` — is a **superset**: Build19 adds `write` to the same rule. 
- **Therefore Hypothesis E is falsified.** The policy delta is purely additive; additive allow rules cannot *block* `recovery`, `init`, `ueventd`, `logd`, `tee`, `hal_keymint_default`, `hal_gatekeeper_default`, `keystore`, or `adbd`.
- `set_prop(recovery, vendor_mtk_trustkernel_tee_prop)` **is** present (`sepolicy/vendor/trustkernel.te:39`), so the relabelled `vendor.trustkernel.fs.state` **is** settable from the script's `u:r:recovery:s0` domain. The "property can no longer be set" theory is **falsified**.
- **The `chcon` → `file_contexts` swap is sound (verified).** `/dev/block/sdc1` is confirmed to be the real `misc` partition (`by-name/misc -> /dev/block/sdc1` in the live capture), and `/dev/block/sdc1 u:object_r:misc_block_device:s0` **is compiled into `file_contexts.bin`** in Build19 (absent in Build18), so ueventd applies it at node creation. This change actually *fixes* the Build17 BootControl labeling defect and is not the regression.

## Build18 vs Build19 ramdisk evidence

- Entry counts identical (3943/3943); no file added, removed, or re-typed; symlink set identical.
- Only the 10 files listed above differ by content; 4 of those are build stamps or derived manifests.
- **Hypothesis 5 (ramdisk composition drift) is falsified.** **Hypothesis 6 (stale/wrong fragment) is falsified** — the flashed fragment matches `out/` at `da6c614`. **Hypothesis 7 (unexpected generated context file) is falsified** — `vendor_property_contexts` matches the expected `ec23a1a2…`/1382 exactly.

## Ranked hypotheses

### 1. Boot-critical `vendor.boot-default` start became conditional — **High confidence**

**Evidence:**
- Build18 `on boot`: `stop vendor.boot-default` … `start vendor.boot-default` — both unconditional (verified in the extracted Build18 CPIO).
- Build19 `on boot`: `stop vendor.boot-default` remains unconditional; `start vendor.boot-default` now lives only under `on property:vendor.trustkernel.fs.state=ready` (verified).
- That property is set **only** at line 106 of `gq5012bf1-security-setup.sh`, behind ~14 early exits (verified).
- No `class_start early_hal` exists in recovery, so nothing else routinely starts this HAL (verified).
- `README.md:1570` "Build17 BootControl SELinux causality proof": with the HAL unavailable, "recovery remained blocked in `futex_wait_queue`"; restarting **only** `vendor.boot-default` made "the same recovery process immediately leave its wait."
- `README.md:1219`: "the recovery splash deadlock can be removed" by exactly this.
- `README.md:1814+`: the setup script has **only ever completed successfully under a temporary permissive window** — it has never been proven to reach line 106 under enforcing SELinux on a cold boot.

**Why it matches a logo-only hang:** recovery reaches the splash, then *synchronously* requests `IBootControl/default` before mounting `/data`, and blocks in `futex_wait_queue`. The UI never advances, and ADB (`class default`, started earlier but gated on `sys.usb.config`) never reaches a usable state. This is the documented signature of this exact device.

**Smallest confirming test:** move `start vendor.boot-default` back into `on boot` (one line), leaving the rest of Build19 untouched. **Requires a new flash.**

### 2. Genuine circular wait between the mapper wait and the blocked recovery process — **Medium confidence**

**Evidence:** the new `exit 10` waits up to 60 s for `/dev/block/mapper/system_a` and `vendor_a`. Those mappers are created **by the recovery process itself** during startup. `README.md:1804` "Build18 late-retry timing proof" confirms recovery creates them *later*, after security-prep has already exited. If recovery blocks on IBootControl (H1) before creating them, the wait times out, the property is never set, and the HAL is never started — the two waits deadlock permanently.

*Verified counter-evidence:* `hwtest3-build14/of-slot-partition-state.txt` shows `system_a -> dm-4` and `vendor_a -> dm-10` do exist in a working session, so the wait *can* be satisfied. This is a refinement of H1 rather than an independent cause, and it is why the fix must decouple the HAL from the script rather than merely lengthen the timeout.

**Smallest confirming test:** same one-line change as H1; if the hang clears while the script still logs `mapper wait timeout`, H2 is confirmed as the specific trip path.

### 3. Enforcing-mode failure of the newly reachable second half of the setup script — **Low/Medium confidence**

**Evidence:** on every prior cold boot the script died within milliseconds at the `system_a` mount (`README.md:1790`), so its `mount`/`cp`/`resetprop`/`restorecon` tail had **never** executed on a live enforcing cold boot. Build19's mapper wait lets it reach that tail for the first time, concurrently with recovery startup, where it rewrites `/etc/task_profiles.json` and `/system/etc/vintf/manifest.xml` underneath a running recovery. A non-zero exit anywhere there reproduces the H1 outcome; a bad mutation could additionally destabilise recovery.

**Smallest confirming test:** after applying the H1 fix, read the service's exit status (`init.svc.gq5012bf1-security-prep` / the script's `echo` output in logcat) once ADB is reachable — no extra flash beyond the H1 flash.

## Recommended next action

**One minimal change:** in `recovery/root/init.recovery.gq5012bf1.security.rc`, move `start vendor.boot-default` back into the unconditional `on boot` block, leaving `start gq5012bf1-security-prep` async and leaving `restart logd` / `start teed` on the property trigger:

```rc
on boot
    stop keystore2
    stop vendor.boot-default
    start gq5012bf1-security-prep
    start vendor.boot-default          # <-- restore Build18 guarantee

on property:vendor.trustkernel.fs.state=ready
    restart logd
    start teed
```

This decouples the boot-critical BootControl HAL from security-prep success — restoring the only Build18 behaviour that was lost — while keeping every Build19 policy and packaging improvement. It changes exactly one variable and requires one new flash.

*(Do not simply raise the 60 s timeout: that treats H2's symptom and leaves the HAL hostage to the script's other 13 exit paths.)*

## Commands/evidence used

Read-only inspection; nothing flashed, committed, or modified in the source tree.

```
python3 /tmp/vbunpack.py <both vendor_boot images>      # vendor_boot v4 header + ramdisk table parse
lz4 -d …/ramdisk_1_recovery_type2.lz4 ; cpio -idm       # extract to /tmp/gq-b18 /tmp/gq-b19 /tmp/gq-plat
sha256sum / cmp / diff -u / comm                        # per-file content diff
seinfo <sepolicy> ; sesearch --allow <sepolicy>         # compiled policy diff (setools)
strings file_contexts.bin | grep /dev/block/sdc1        # verify compiled device label
git --no-pager log --oneline -8 ; git status --short    # tree clean at da6c614
```

Key hashes and paths:

| Item | Value |
|---|---|
| Build18 recovery fragment | `build18/orangefox-build18-recovery.lz4`, 33571785, `2e0b627d32ad0266aa477d773ad364070d116e9e418f42d7497548ea859f7e3f` |
| Build19 recovery fragment | *(no standalone file)* extracted from `build19/vendor_boot_a-orangefox-FULL64M-BUILD19.img` @off 28759822, 33572202, `4251932e0842d09e8f5991578169f0076cdd98425ca616f309536c8aa2027857` |
| Build18 FULL64M image | `0b1ab88fb3a4a3e3fff4071e0410b1c481bd9cd633d1c9a327a82f4801861e01` |
| Build19 FULL64M image | `a3f5662a843698afcbcaab3862f0b434466141a9f5f65d6625f3119cf75fb676` |
| Build19 raw image | `3806bfa62c8620d2f2b086ae86815ffac69e91eea3b07ec87840a776fe10643b` |
| PLATFORM fragment (both) | `9201a4e5c1b7cb1fc0ce35375af10a3d966dac8b84615a226f98b7d7be2aec00` (identical) |
| DTB (both) | `bc156c29c33d8226…` (identical) |
| b19 `vendor_property_contexts` | `ec23a1a236202eaa2a68cfb71297183cb851a6d216dd72d06eb908712f63cdc6` (1382) — matches expectation |
| b19 `sepolicy` / `file_contexts.bin` | `8d0e4010747365eddfe2e152ad1826a92e602d79c21509019cef30873e50fe21` / `30246e815e20d7046ad487124de860dd4f3ed902bbfc7261f6dd70499c468d9d` |

Corroborating on-device captures (pre-existing artifacts, not regenerated):
`gq5012bf1-artifacts/live-recovery-working/state.txt`, `hwtest3-build14/of-byname.txt`, `hwtest3-build14/of-slot-partition-state.txt`, and `device/ulefone/gq5012bf1/README.md` §Build17 BootControl (lines 1560–1616), §Build18 cold-boot timing failure (1788–1815).
