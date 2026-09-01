# Ulefone Armor 29 Pro Thermal

LineageOS device tree for the **Ulefone Armor 29 Pro Thermal**.

## Device

| | |
|---|---|
| Device | Ulefone Armor 29 Pro Thermal |
| Product | `gq5012bf1` |
| Model | Armor 29 Pro |
| SoC | MediaTek MT6878 |
| Architecture | arm64 |
| Display | 1080x2400, 480 dpi |
| Stock Android | 15 |
| Partition layout | A/B, Virtual A/B, dynamic partitions |
| Recovery | inside `vendor_boot` (no recovery partition) |

## Build

```bash
source build/envsetup.sh
lunch lineage_gq5012bf1-ap2a-userdebug
mka bacon
```

## Proprietary blobs

Extraction uses the standard LineageOS `extract-utils` framework:

```bash
# from a device with the stock ROM
./extract-files.py adb

# or from extracted stock partitions
./extract-files.py <path to extracted stock partitions>
```

`setup-makefiles.py` regenerates the vendor makefiles without re-extracting.

Entries marked `EXTRACT_ONLY` are stock paths that are accounted for but
installed by AOSP/ROM modules, or that are evidence only (stock `build.prop`,
`.odex`/`.vdex`, alternate-BOM VINTF manifests). The AOSP modules that own
those paths are requested from `device.mk`.

## Status

Bring-up stage: the tree is complete and build-validated, and has **not** been
runtime-validated as a full ROM. `m nothing` and `m selinux_policy` pass, the
proprietary inventory is closed, and VINTF coverage is complete.

Verified on hardware through the OrangeFox recovery built from this tree:
display, FocalTech FT3680 touch, USB/ADB, MTP, fastbootd, battery reporting,
vibration, TrustKernel TEE with KeyMint/Gatekeeper/Keystore2, metadata
encryption, FBE decryption and MediaTek BootControl.

Known limitations:

- The kernel is the stock Ulefone GKI prebuilt; there is no kernel source tree.
- Full-ROM runtime behaviour (camera, audio, telephony, sensors, thermal
  camera, secondary display) is configured but unproven on hardware.
- An offline ELF dependency audit still reports 27 unresolved Android 15
  `system/lib64` dependencies when it is run against an Android 14 checkout.
  This has to be re-evaluated on a LineageOS 22.2 tree.

## Related repositories

| Repository | Contents |
|---|---|
| [`OrangeFox-Ulefone-GQ5012BF1`](https://github.com/LieppOS/OrangeFox-Ulefone-GQ5012BF1) | OrangeFox recovery overlay, packaging and releases |
| [`LieppOS-ulefone-gq5012bf1-research`](https://github.com/LieppOS/LieppOS-ulefone-gq5012bf1-research) | reverse-engineering evidence, bring-up history and audit tooling |

Building OrangeFox for this device uses this tree plus the overlay from the
OrangeFox repository; see its README.
