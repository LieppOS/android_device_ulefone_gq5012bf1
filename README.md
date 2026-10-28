# Ulefone Armor 29 Pro Thermal

LineageOS 24.0 / Android 17 device tree for the **Ulefone Armor 29 Pro Thermal**.

## Device

| | |
|---|---|
| Device | Ulefone Armor 29 Pro Thermal |
| Product | `gq5012bf1` |
| Model | Armor 29 Pro |
| SoC | MediaTek MT6878 |
| Architecture | arm64 |
| Display | 1080x2400, 480 dpi |
| Stock Android | 15 (SDK 35), vendor API 202404 / VNDK 34 |
| Build target | LineageOS 24.0 / Android 17 (SDK 37), release `cp2a` |
| Partition layout | A/B, Virtual A/B, dynamic partitions |
| Recovery | inside `vendor_boot` (no recovery partition) |

## Build

```bash
source build/envsetup.sh
lunch lineage_gq5012bf1-cp2a-userdebug
mka bacon
```

`cp2a` is the Android 17 release used by the current LineageOS 24.0 platform
checkout. The old `ap2a` lunch choice was removed because that release config is
marked `disallow_lunch_use` on this platform.

## Proprietary blobs

Extraction uses the standard LineageOS `extract-utils` framework:

```bash
# from a device with the stock ROM
./extract-files.py adb

# or from extracted stock partitions
./extract-files.py <path to extracted stock partitions>
```

`setup-makefiles.py` regenerates the vendor makefiles without re-extracting.

The `android_vendor_ulefone_gq5012bf1` checkout owns the generated
`Android.bp`, `Android.mk`, `BoardConfigVendor.mk` and
`gq5012bf1-vendor.mk`. Its `proprietary/` payload is gitignored and is **not**
committed: extract it from the owner's stock dump before building.

Entries marked `EXTRACT_ONLY` are stock paths that are accounted for but
installed by AOSP/ROM modules, or that are evidence only (stock `build.prop`,
`.odex`/`.vdex`, alternate-BOM VINTF manifests). The AOSP modules that own
those paths are requested from `device.mk`.

## Status

- The product configuration has been evaluated on the LineageOS 24.0 / Android
  17 platform (`PRODUCT_EVALUATED`, Kati product configuration including the
  generated vendor makefiles).
- The stock vendor/odm manifests declare vendor HAL instances that are not in
  the AOSP Android 17 framework matrix. `vintf/framework_compatibility_matrix.xml`
  adds exactly those required instances; `checkvintf --check-compat` reports
  `COMPATIBLE` against the stock vendor metadata.
- `PRODUCT_EXTRA_VNDK_VERSIONS := 34` keeps the v34 prebuilt snapshot available
  for the preserved Android 15 vendor ELF closure.
- Targeted Soong builds are blocked in the current platform checkout by a
  missing `build/soong/config/main.star` (`soong bootstrap failed`). The
  extracted vendor payload is also absent from the vendor repository by policy.
- The full-ROM vendor image is **not** runtime-validated. The stock vendor
  SELinux policy is an Android 14 prebuilt; rebuilding the vendor partition
  from AOSP plus the device policy would drop the MediaTek service policy and
  file contexts until MediaTek sepolicy sources are available. Do not flash a
  rebuilt vendor image.
- The C51 source vibrator HAL remains disabled. The stock
  `vendor.vibrator-default` service, init rc and VINTF fragment are preserved.

Recovery built from this tree has previously been hardware-validated for
display, FocalTech FT3680 touch, USB/ADB, MTP, fastbootd, battery reporting,
vibration, TrustKernel TEE with KeyMint/Gatekeeper/Keystore2, metadata
encryption, FBE decryption and MediaTek BootControl. That recovery validation
does not validate the full-ROM vendor rebuild.

Known limitations:

- The kernel is the stock Ulefone GKI prebuilt in this tree; the published
  C48/C50 source baseline is integrated separately.
- Full-ROM runtime behaviour (camera, audio, telephony, sensors, thermal
  camera, secondary display) is configured but unproven on hardware.

## Related repositories

| Repository | Contents |
|---|---|
| [`OrangeFox-Ulefone-GQ5012BF1`](https://github.com/LieppOS/OrangeFox-Ulefone-GQ5012BF1) | OrangeFox recovery overlay, packaging and releases |
| [`LieppOS-ulefone-gq5012bf1-research`](https://github.com/LieppOS/LieppOS-ulefone-gq5012bf1-research) | reverse-engineering evidence, bring-up history and audit tooling |
| `android_vendor_ulefone_gq5012bf1` | generated vendor configuration; proprietary payload extracted locally |

Building OrangeFox for this device uses this tree plus the overlay from the
OrangeFox repository; see its README.
