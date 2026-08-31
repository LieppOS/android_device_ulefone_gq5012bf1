# CODEX.md — Ulefone Armor 29 Pro Thermal / GQ5012BF1

## Mission

Build and maintain a **maximum-completeness Android/LieppOS device tree** for the **Ulefone Armor 29 Pro Thermal**, Android product/codename **`GQ5012BF1`**, MediaTek **MT6878**.

This is **not** a minimal "boots a GSI" tree and **not** only an OrangeFox/TWRP tree.

The end state is a production-quality device bring-up that accounts for every stock hardware block and every Android/vendor interface that can reasonably be reproduced using AOSP/Lineage/LieppOS code plus extracted proprietary components.

The existing OrangeFox work is a verified hardware/security foundation. **Do not regress it while expanding the tree into a full ROM device tree.**

---

# 1. Non-negotiable goals

The finished tree should support, document, or explicitly account for:

- boot
- `init_boot`
- `vendor_boot`
- DTB
- DTBO
- AVB
- A/B
- Virtual A/B
- dynamic partitions / `super`
- fastbootd
- OTA
- EROFS
- ext4
- F2FS
- metadata partition
- metadata encryption
- Android FBE v2
- TrustKernel TEE
- KeyMint
- Gatekeeper
- Keystore2 integration
- SELinux enforcing
- BootControl
- main display
- display refresh modes
- brightness / HBM where exposed
- main touchscreen
- secondary display
- secondary touchscreen
- graphics/composer/gralloc
- media codecs
- DRM integration where proprietary support permits
- cameras
- night-vision camera
- thermal camera
- thermal-camera userspace/service stack
- audio
- speakers
- microphones
- 3.5 mm headset path
- vibrator/haptics
- fingerprint
- sensors
- accelerometer
- gyroscope
- magnetometer
- proximity
- ambient light
- barometer
- step/pedometer path if present
- power HAL
- thermal HAL
- health HAL
- battery reporting
- fuel gauge
- charging state
- high-power / fast charging
- USB-PD or other charger negotiation used by stock
- reverse charging / OTG power where supported
- USB configfs
- ADB
- MTP
- USB tethering
- USB OTG
- external SD
- Wi-Fi
- Bluetooth
- GNSS
- NFC
- modem / RIL
- dual-SIM behavior
- IMS / VoLTE / VoWiFi where stock proprietary stack permits
- notification/status LEDs
- auxiliary/work light hardware
- red/blue warning lights if Android exposes them
- physical keys
- programmable/action keys
- RTC / alarm
- suspend / doze
- power hints
- thermal throttling
- kernel module loading
- firmware loading
- calibration ownership
- recovery
- backup/restore prerequisites
- sideload
- reboot targets

If stock Android exposes a hardware block, daemon, HAL, kernel module, configuration file, VINTF declaration, framework feature, or persistent calibration dependency, it must be either:

1. implemented in the device/vendor tree;
2. intentionally inherited from a shared platform component;
3. retained as a proprietary component; or
4. documented as unresolved with evidence describing what is still missing.

Do not silently omit stock functionality.

---

# 2. Device identity

Retail identity:

```text
Manufacturer: Ulefone
Retail model: Armor 29 Pro Thermal
```

Android product/codename:

```text
GQ5012BF1
```

Platform:

```text
MediaTek MT6878
arm64
UFS
```

Stock firmware:

```text
Android 15
Ulefone/GQ5012BF1_EEA/GQ5012BF1:15/AP3A.240905.015.A2/1761131274:user/release-keys
GQ5012BF1_EEA_V15_user_20251022
```

Observed stock-derived kernel:

```text
Linux 6.1.115-android14-11-g6b18f0b574ab-ab12901745
Android 14 KMI generation
aarch64
```

## Critical TrustKernel product identity rule

For the Android security/product model, use:

```text
Armor 29 Pro
```

Do **not** change the security-facing product model to:

```text
Armor 29 Pro Thermal
```

A controlled recovery experiment proved that `Armor 29 Pro` produces the working TrustKernel verification state while `Armor 29 Pro Thermal` does not.

Documentation may use the retail name. Security-facing Android identity must preserve the verified value unless new evidence proves otherwise.

---

# 3. Source-of-truth priority

**Rank evidence by the class of fact being asked, not by a single global
order.** The live stock snapshot is the best source for some questions and
actively misleading for others. See the contamination warning below.

### Hardware topology

Bus bindings, bound drivers, loaded modules, DRM/display topology, input
devices, power supplies, device nodes, running services, camera nodes, sensor
topology, LED class devices, block/partition layout.

1. **Current live stock snapshot**
2. **Current live recovery snapshot** (the only place `/sys/class/leds` is readable)
3. **Exact stock firmware files/images**
4. **Directly decoded DTB / module / ELF / VINTF evidence**
5. **Current working source tree and actual git history**
6. **`everything_i_know_about_this_phone.md`**
7. inference
8. generic MediaTek assumptions

### Android build identity and version

`ro.build.*`, `ro.product.*`, API level, fingerprint, shipping API level.

1. **Exact stock firmware `build.prop`**
2. **Stock firmware images / manifests**
3. **Current working source tree and actual git history**
4. **`everything_i_know_about_this_phone.md`**
5. **Live snapshot properties** — LOWEST, see the warning below

### Security and product identity

Attestation identity, TrustKernel/KeyMint behaviour, security-facing model.

1. **Verified TrustKernel hardware experiments**
2. **Exact stock firmware files/images**
3. **Current working source tree and actual git history**
4. **Live snapshot properties** — LOWEST, see the warning below

Do not let an older report override a newer verified hardware result.

## Critical warning: the live stock snapshot is property-contaminated

`gq5012bf1-live-stock-20260831-113332` was captured on a device running
**KernelSU** with an active property-spoofing module. `kernelsu` is in its
`proc.txt`, and its properties contradict both the device's own fingerprint
and the extracted stock firmware:

```text
ro.build.version.release          = 16           fingerprint says 15
ro.build.version.sdk              = 36           stock build.prop says 35
ro.product.model_for_attestation  = Pixel 9 Pro  stock leaves it EMPTY
ro.product.brand_for_attestation  = google       stock leaves it EMPTY
ro.product.name_for_attestation   = caiman       stock leaves it EMPTY
ro.product.device_for_attestation = caiman       stock leaves it EMPTY
```

A LieppOS device-patches module also injects a non-stock namespace. These are
**feature flags, not hardware evidence**:

```text
persist.lieppos.device_patches            = armor29
persist.lieppos.armor29.thermal_cam       = true
persist.lieppos.armor29.sub_screen        = true
persist.lieppos.armor29.super_flashlight  = true
persist.lieppos.armor29.camp_lights       = true
persist.lieppos.armor29.charging_control  = true
persist.lieppos.armor29.fm_radio          = true
```

`thermal_cam=true` is not proof a ThermoVue camera is wired up, and
`sub_screen=true` is not proof the rear display is implemented.

Never carry `ro.product.*_for_attestation` into the device tree: shipping the
spoofed Pixel 9 Pro identity in a public tree would be deliberate attestation
spoofing, and stock leaves those properties empty.

The recovery snapshot also shows `kernelsu`, meaning the **boot image** is
patched. No property spoofing was detected there, and its `ro.build.version.*`
legitimately describe the OrangeFox ramdisk, so it stays fully usable for
hardware topology.

Check any snapshot before trusting it:

```bash
python3 tools/snapshot_trust.py <snapshot-dir> \
    --stock-root .work/gq5012bf1/stock/partitions --check
```

## Important stale-report warning

`AI_report_1.md` describes an earlier state where OrangeFox FBE was still broken.

That is obsolete.

The newer engineering record states that FBE was solved and verified under enforcing SELinux with the TrustKernel security path.

Known successful recovery integration baseline:

```text
commit: bbe7af2
```

Verified behavior from a cold boot:

```text
SELinux enforcing
TrustKernel starts
metadata key unwrap succeeds
userdata mapper is created
/data mounts as F2FS
one PIN prompt
Gatekeeper verifies
user-0 CE key is installed
/data/system_ce/0 becomes readable
/data/media/0 becomes readable
no ADB intervention
repeatable across reboots
usable recovery in ~26 seconds
```

**Never "fix" the tree by reverting this solved path.**

---

# 4. Live evidence captured on 2026-08-31

Two read-only phone snapshots were captured before device-tree expansion work.

## Recovery snapshot

```text
/home/armol/android/gq5012bf1-live-recovery-20260831-113044
/home/armol/android/gq5012bf1-live-recovery-20260831-113044.tar.gz

SHA256:
d8e8aa3c44d7906abad25310be99400fe2feaa897b38dba6f2421b2b84d92fbe
```

## Stock Android snapshot

```text
/home/armol/android/gq5012bf1-live-stock-20260831-113332
/home/armol/android/gq5012bf1-live-stock-20260831-113332.tar.gz

SHA256:
d2a18e4f0eefd6d419db9332eed4cf9a494b874931c6721a27744ffb0d0b4144
```

The collector gathered, where available:

- identity
- properties
- kernel/boot state
- `/proc`
- block devices
- device nodes
- power-supply sysfs
- thermal sysfs
- LEDs
- backlight
- DRM
- V4L2
- sound
- inputs
- I2C devices and bound drivers
- SPI devices and bound drivers
- platform devices and drivers
- IIO
- hwmon
- Type-C
- UDC
- extcon
- RTC
- loaded kernel modules
- services/processes
- `getevent -lp`
- `dmesg`
- live flattened device tree

The stock run additionally attempted:

- `lshal`
- Binder service list
- `dumpsys -l`
- battery dump
- thermal service dump
- sensor service dump
- camera service dump
- SurfaceFlinger display IDs
- display dump
- input dump
- vibrator dump
- USB dump

These archives are high-value evidence. Parse them before guessing hardware behavior.

---

# 5. Known local paths

Existing OrangeFox source:

```text
/home/armol/android/fox_14.1
```

Current device tree:

```text
/home/armol/android/fox_14.1/device/ulefone/gq5012bf1
```

GitHub repository:

```text
git@github.com:LieppOS/android_device_ulefone_gq5012bf1.git
```

Observed stock firmware directory:

```text
/home/armol/androido_dalykai/Ulefone_Armor_29_Thermal/Ka as turiu/m170b-gq-gq5012-512g16g-fhdp-V0-bom103-cts-eu_GQ5012BF1_EEA_V15_user_20251022/
```

Stock unpack working directory:

```text
/home/armol/android/ulefone29-stock-unpack
```

Existing artifacts:

```text
/home/armol/android/gq5012bf1-artifacts
```

Existing touch work:

```text
/home/armol/android/gq5012bf1-touch
```

Do not assume every path exists forever. Detect paths and fail clearly rather than silently substituting unrelated inputs.

---

# 6. Repository state at start of full-tree work

The public repository is currently recovery-oriented.

Important current facts:

- `BoardConfig.mk` is already substantial and contains verified MT6878/recovery geometry.
- `device.mk` is still a tiny recovery product file.
- `twrp_gq5012bf1.mk` exists.
- stock kernel/DTB/DTBO prebuilts exist.
- `recovery/root` exists.
- device-specific TrustKernel SELinux policy exists under `sepolicy/vendor`.
- recovery-specific patches exist.
- full ROM proprietary extraction infrastructure does not yet exist.
- no complete `proprietary-files.txt` exists yet for full Android bring-up.
- no generated `vendor/ulefone/gq5012bf1` full proprietary tree exists yet.
- no complete LieppOS/Lineage product makefile exists yet.

Do not replace verified recovery work with a generic template.

Expand around it.

---

# 7. Git and workspace rules

Before every meaningful change:

```bash
git status --short
git log --oneline -20
```

Rules:

- Preserve uncommitted user work.
- Never use `git reset --hard`.
- Never force-push.
- Never rewrite history unless explicitly requested.
- Never delete unknown user files just because they are untracked.
- Do not amend commits you did not create unless explicitly requested.
- Prefer small, reviewable, atomic commits.
- Use commit messages such as:

```text
gq5012bf1: add stock HAL inventory tooling
gq5012bf1: add proprietary extraction skeleton
gq5012bf1: configure MT6878 dynamic partitions
gq5012bf1: import stock audio policy
gq5012bf1: add ThermoVue vendor stack
```

Before altering a working recovery/security file, identify which commit introduced the current behavior and understand why it exists.

---

# 8. Phone safety rules

Assume the phone may be physically unavailable.

The normal workflow is offline against stock firmware and captured snapshots.

Do **not** perform phone-side writes unless the user explicitly asks for a test.

Prohibited by default:

```text
fastboot flash
fastboot erase
fastboot set_active
adb push to system/vendor/product partitions
adb remount
mount -o rw on phone partitions
dd of=/dev/block/...
wipe
format
factory reset
setprop changes for experiments
chmod/chcon mutations on live phone
insmod/rmmod experiments without explicit approval
```

Read-only phone inspection is acceptable when the user explicitly has the phone available.

Do not dump or request userdata contents. Device bring-up must not require personal data.

---

# 9. Stock firmware safety rules

Treat stock firmware as immutable source material.

Do not modify files in place.

Use a work directory such as:

```text
.work/
out-analysis/
stock-extracted/
```

and keep generated analysis out of git unless it is small and intentionally documented.

Verify hashes for critical source images before and after analysis when practical.

---

# 10. Boot architecture — verified facts

The device uses:

```text
A/B
Virtual A/B
dynamic partitions
super
vendor_boot v4
```

Observed:

```text
ro.boot.slot_suffix=_a
ro.virtual_ab.enabled=true
ro.boot.dynamic_partitions=true
```

There is no traditional standalone recovery partition.

Recovery is a type-2 RECOVERY vendor ramdisk fragment inside `vendor_boot`.

Known geometry:

```text
vendor_boot header: v4
partition size: 67108864 bytes
page size: 4096
base: 0x00000000
kernel offset: 0x40000000
ramdisk offset: 0x66f00000
tags offset: 0x47c80000
dtb offset: 0x47c80000
vendor cmdline: bootopt=64S3,32N2,64N2
```

Important A/B OTA partitions already identified:

```text
boot
init_boot
vendor_boot
dtbo
vbmeta
vbmeta_system
vbmeta_vendor
system
system_ext
vendor
product
vendor_dlkm
odm_dlkm
system_dlkm
```

---

# 11. Recovery vendor_boot invariant

The stock vendor ramdisk PLATFORM fragment is required.

For OrangeFox/recovery packaging:

```text
stock PLATFORM
+ custom RECOVERY ramdisk fragment
+ stock DTB
+ stock-compatible vendor_boot v4 geometry
+ valid AVB footer
+ exact full 64 MiB image
```

Known stock hashes:

```text
PLATFORM:
9201a4e5c1b7cb1fc0ce35375af10a3d966dac8b84615a226f98b7d7be2aec00

DTB:
bc156c29c33d8226230f07888df0a3d7a1e9c4b85c5fd550a4c4bd1a3134c0d4

full stock vendor_boot:
c8953d16b7a47976362aa23b53d0a08dde451f25cab4c552fa70c43e56ee0756
```

The raw generated:

```text
out/target/product/gq5012bf1/vendor_boot.img
```

must not automatically be assumed to be the safe final recovery image.

The authoritative generated recovery payload is the recovery ramdisk fragment, after which the full vendor_boot must be reconstructed and validated.

Do not regress these protections.

---

# 12. DTB facts

The stock DTB has a 64-byte MediaTek/proprietary wrapper.

Observed:

```text
FDT magic offset: 64
FDT magic: d00dfeed
FDT version: 17
FDT total size: 342331
wrapped size: 342395
~1390 nodes
```

When extracting DTS data, account for the wrapper rather than declaring the image corrupt.

Use DTB evidence aggressively for hardware discovery, but distinguish:

- enabled/bound hardware
- alternate BOM nodes
- unused shared-platform nodes

A node existing in DTB is not proof that the tested device uses it.

---

# 13. Main touch — verified

Main touchscreen:

```text
FocalTech FT3680
SPI3
compatible=focaltech,fts
module=focaltech_touch_spi_ft3680.ko
driver=fts_ts
controller ID=0x5662
display coords=1080x2400
max touches=10
```

DT node:

```text
/soc/spi3@11013000/focaltech@39
```

The stock module contains an embedded firmware fallback and works in recovery without an external firmware file.

Known module SHA256:

```text
6629ec6148ac361a5f0085b8b19efa9d591426679f58262c4998345f41931162
```

Do not replace this with a guessed generic FocalTech configuration.

---

# 14. Secondary display/touch — partially verified

A second touchscreen is bound under stock Android:

```text
Hynitron
compatible=hynitron,hyn_ts
I2C
340x340
max-touch-number=1
module=hynitron.ko
driver=hyn_ts
```

DT node:

```text
/soc/i2c@11c20000/hynitron@15
```

A stock module:

```text
spi_tiny_co5300_lcd.ko
```

depends on:

```text
hynitron.ko
yft_devinfo.ko
```

Strong inference:

The Hynitron 340x340 single-touch surface belongs to the rear/secondary display subsystem.

This is not yet enough to invent a complete userspace implementation.

Use the live stock snapshot, module strings, DTB, DRM/display dumps, init services and vendor libraries to determine the exact architecture.

Also present as apparent alternate BOM configurations:

```text
Ilitek
Chipone
```

They are not bound on the tested unit and must not be treated as active hardware.

---

# 15. vendor_dlkm

The device uses a logical `vendor_dlkm` partition.

Known facts:

```text
EROFS
~16 MiB
~219 module files
```

Relevant modules include:

```text
focaltech_touch_spi_ft3680.ko
hynitron.ko
mtk_ioctl_touch_boost.ko
touch_boost.ko
spi_tiny_co5300_lcd.ko
```

Full-tree work must map:

- all stock module files
- `modules.dep`
- `modules.alias`
- `modules.softdep`
- `modules.load*`
- module signing/vermagic
- partition ownership
- boot/recovery load ordering
- required firmware

Do not copy all modules blindly into the device repo.

Prefer the correct `*_dlkm` partition model.

---

# 16. Storage and encryption — verified

Metadata:

```text
/dev/block/by-name/metadata -> /dev/block/sdc16
F2FS
```

Userdata:

```text
/dev/block/by-name/userdata -> /dev/block/sdc76
F2FS
```

Encryption:

```text
fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized
keydirectory=/metadata/vold/metadata_encryption
fscrypt policy v2
metadata encryption enabled
```

The raw userdata block is metadata-encrypted.

The decrypted mapper exposes valid F2FS and mounts successfully after TrustKernel/KeyMint metadata-key unwrap.

The full ROM tree must preserve the stock encryption contract.

Do not "simplify" it into unencrypted userdata.

---

# 17. TrustKernel security stack — do not regress

Verified stock services include:

```text
/vendor/bin/teed
/vendor/bin/hw/android.hardware.security.keymint@3.0-service.trustkernel
/vendor/bin/hw/android.hardware.gatekeeper-service.trustkernel
/system/bin/keystore2
```

Verified interfaces include:

```text
android.hardware.security.keymint.IKeyMintDevice/default
android.hardware.security.keymint.IRemotelyProvisionedComponent/default
android.hardware.security.secureclock.ISecureClock/default
android.hardware.security.sharedsecret.ISharedSecret/default
android.hardware.gatekeeper.IGatekeeper/default
android.system.keystore2.IKeystoreService/default
```

Important paths/devices include:

```text
/dev/tkcore_admin
/dev/tkcore_client
/dev/teeperf
/dev/rpmb0
/dev/mmcblk0rpmb
/vendor/app/t6
/mnt/vendor/persist/t6
/mnt/vendor/protect_f/tee
/data/vendor/t6/fs
/data/vendor/t6/app
```

Known stock daemon identity:

```text
teed:
user system
group system
CAP_SYS_RAWIO
SELinux u:r:tee:s0
```

Do not run this stack under broad generic recovery/vendor domains if the proper domains are already known.

---

# 18. TrustKernel SELinux invariants

The recovery bring-up established precise device-specific policy requirements.

Important types include:

```text
persist_data_file
protect_f_data_file
tkcore_protect_data_file
tkcore_systa_file
tkcore_spta_file
tkcore_data_file
tkcore_log_file
tkcore_admin_device
tkcore_client_device
teeperf_device
teei_rpmb_device
rpmb_device
proc_tkcore
vendor_mtk_trustkernel_tee_prop
```

A decisive permission was:

```te
allow tee tkcore_protect_data_file:file link;
```

Why:

TrustKernel commits persistent objects by hard-linking a staged block file.

`create_file_perms` in the relevant policy does not include `link`.

Do not delete this as "redundant".

Also preserve correct traversal of:

```text
/mnt/vendor/persist
/mnt/vendor/protect_f
```

with real stock-derived file types rather than `unlabeled`.

---

# 19. TrustKernel startup ordering

The verified working ordering is effectively:

```text
teed
  -> KeyMint
     -> Gatekeeper
        -> Keystore2
```

The real constraint is serialization/TA readiness, not an arbitrary 90-second sleep.

Do not reintroduce the obsolete long-delay workaround.

TrustKernel secure-world state can persist across Linux service restarts.

Therefore:

**late manual restart experiments are not equivalent to clean cold-boot validation.**

Validate security changes from cold boot where relevant.

---

# 20. BootControl invariant

MediaTek BootControl requires the physical misc inode to have the correct label.

Known:

```text
/dev/block/by-name/misc -> /dev/block/sdc1
```

Physical inode must resolve as:

```text
misc_block_device
```

Do not only label the by-name symlink.

Verified:

```text
android.hardware.boot.IBootControl/default
bootctl get-current-slot -> 0
```

---

# 21. USB invariant

The device uses configfs.

Verified:

```text
sys.usb.configfs=1
sys.usb.controller=11201000.usb0
```

Do not restore the legacy:

```text
/sys/class/android_usb/android0
```

TWRP USB initialization path.

Existing recovery requirement:

```make
TW_EXCLUDE_DEFAULT_USB_INIT := true
```

MTP must eventually be implemented/validated using the correct configfs/FunctionFS architecture.

Do not trade working ADB for legacy MTP behavior.

---

# 22. Battery/charging — high-priority full-tree work

Known power-supply nodes include:

```text
battery
3rd-gauge
mtk-gauge
mtk-master-charger
mtk-mst-div-chg
mtk-mst-hvdiv-chg
mtk-slave-charger
mtk-slv-div-chg
mtk-slv-hvdiv-chg
primary_chg
sc-cp-master
sc-cp-slave
```

Observed charging components include:

```text
mt6375
sc8571
```

Earlier live readings showed sane values such as:

```text
capacity=63
status=Charging
```

Outstanding questions include:

- exact battery cell/topology
- exact design capacity exposed to Android
- exact fuel-gauge IC
- charger topology
- SC8571 master/slave role
- charge-pump arrangement
- 120 W charging implementation
- USB-PD/PPS or OEM protocol details
- reverse charging control
- health HAL implementation
- power HAL interaction
- thermal throttling interaction
- charger-mode behavior
- recovery battery UI live updates

Use the 2026-08-31 stock and recovery snapshots first.

Create a clear battery/charging map, not ad-hoc property fixes.

---

# 23. Camera and ThermoVue workstream

Do not treat the thermal camera as a normal decorative APK.

Map the complete stock stack.

Required investigation:

```text
camera provider HAL
camera device HALs
vendor camera daemons
V4L2/media nodes
kernel drivers
sensor EEPROM/calibration
camera sensor names
actuators
flash/IR illumination
ISP configuration
camera XML/configuration
vendor libraries
JNI libraries
framework-facing services
ThermoVue app/service
thermal sensor transport
thermal calibration ownership
permissions/features
SELinux
```

For the thermal subsystem, determine the actual path:

```text
ThermoVue userspace
-> Binder/HIDL/AIDL/JNI/native vendor layer
-> device node / kernel driver
-> sensor
```

Do not assume the stock app alone is sufficient.

Preserve required proprietary pieces if there is no open replacement.

---

# 24. Audio workstream

Map and implement:

- audio HAL generation/interface
- audio policy
- mixer paths
- volume tables
- microphones
- speaker topology
- external amplifier(s)
- earpiece
- headset jack
- USB audio
- Bluetooth audio integration
- DSP firmware/configuration
- MediaTek audio kernel modules
- voice-call routing
- hotword/audio effects if present
- SELinux and init services

Use stock vendor configs and ELF dependencies as evidence.

Do not substitute a generic MTK audio policy unless it matches the device.

---

# 25. Sensor workstream

Identify every sensor exposed by stock Android using:

- stock `dumpsys sensorservice`
- VINTF
- `/vendor/bin/hw`
- `/vendor/lib64/hw`
- IIO/sysfs
- I2C/SPI binding
- sensorhub services
- vendor XML/config
- kernel modules
- DTB

Expected/possible device functions include:

```text
accelerometer
gyroscope
magnetometer
proximity
ambient light
barometer
pedometer/step detector
orientation-related virtual sensors
thermal-related sensors
```

Record exact chip/model where evidence permits.

Do not infer a chip model from retail feature lists.

---

# 26. Connectivity workstream

Map:

```text
Wi-Fi
Bluetooth
GNSS
NFC
RIL/modem
IMS
```

Stock firmware partitions already prove the MediaTek firmware split includes items such as:

```text
connsys_wifi
connsys_bt
modem
md1dsp
md1arm7
md3img
```

For each subsystem determine:

- HAL/interface version
- daemon/service
- kernel driver/module
- firmware/calibration files
- init service
- property dependencies
- SELinux
- permissions/features
- persistent/NV partition ownership

Never wipe, rewrite, or package device-unique NV/calibration data.

---

# 27. Fingerprint workstream

Known input clue:

```text
madev
```

and prior work suggests a Microarray-related stack.

Still determine:

- exact sensor/controller
- bus
- device node
- HAL version
- vendor service
- TEE/trusted-app interaction
- firmware
- calibration
- SELinux
- enrollment/auth behavior

Do not guess the exact sensor model from `madev` alone.

---

# 28. LEDs, work light, and physical controls

Map every stock-exposed LED/light class and vendor service.

Include:

- notification LED
- display backlight
- camera flash
- night-vision IR emitters if applicable
- auxiliary/work light
- warning lights
- programmable keys
- GPIO keys
- vendor YFT key abstraction

Known module clue:

```text
yft_gpio_keys.ko
```

Use stock sysfs, keylayout, input dumps, DTB and services.

---

# 29. Full proprietary extraction deliverable

Create a modern extraction workflow.

Target files should include at least:

```text
proprietary-files.txt
extract-files.py
setup-makefiles.py
Android.bp/Android.mk generation as appropriate
blob fixups
```

Generated proprietary repository should conventionally be:

```text
vendor/ulefone/gq5012bf1
```

Extraction must be reproducible from:

1. mounted/extracted stock images; or
2. a connected stock device when explicitly available.

Prefer stock-image extraction for repeatability.

Do not commit blobs whose redistribution status is uncertain unless the project intentionally permits it.

A public device tree may contain extraction recipes without shipping the proprietary binary itself.

---

# 30. ELF dependency analysis

Automate dependency mapping for every retained vendor binary/library.

For ELF files record:

- partition
- path
- ABI
- SONAME
- `DT_NEEDED`
- interpreter
- exported/imported symbols where needed
- unresolved dependencies
- namespace/apex implications
- linker config implications
- shim/fixup need

Do not discover missing dependencies one build error at a time if they can be mapped systematically.

Generate a machine-readable dependency graph plus a concise human report.

---

# 31. VINTF and HAL audit

Build a complete map from stock:

```text
/vendor/etc/vintf
/odm/etc/vintf
/system/etc/vintf
/system_ext/etc/vintf
```

Also inspect:

```text
/vendor/bin/hw
/odm/bin/hw
/vendor/lib64/hw
/odm/lib64/hw
```

For each stock HAL/interface record:

- AIDL/HIDL
- interface name
- instance
- version
- executable
- init rc
- SELinux domain
- libraries
- kernel/device dependency
- whether it must be shipped as blob
- whether AOSP/Lineage can replace it
- whether the final tree currently satisfies it

Create an audit that fails or warns when stock functionality is unaccounted for.

---

# 32. Init/property/ueventd audit

Inventory and rationalize:

```text
/vendor/etc/init
/odm/etc/init
/system/etc/init
ueventd*.rc
property_contexts
vendor properties
odm properties
```

Do not copy every stock rc file blindly.

For each service determine:

- why it exists
- required user/group/capabilities
- class
- interface declarations
- seclabel/domain
- sockets/device nodes
- mount dependencies
- property triggers
- whether it belongs in vendor blob package or device tree

---

# 33. SELinux rules

Target:

```text
SELinux enforcing
```

Rules:

- no global permissive
- no giant `allow recovery device:* *`
- no generic `unlabeled` workaround when a real type is known
- no disabling neverallows as a bring-up solution
- no broad `dac_override`/`sys_admin` grants without evidence
- keep domains faithful to stock when proprietary services depend on them
- add narrow permissions from actual denials and known stock behavior
- document non-obvious rules

Existing TrustKernel policy is valuable verified work, not boilerplate.

---

# 34. Device tree structure target

The end result will likely resemble:

```text
device/ulefone/gq5012bf1/
├── Android.bp
├── AndroidProducts.mk
├── BoardConfig.mk
├── device.mk
├── lineage_gq5012bf1.mk          # or LieppOS product equivalent
├── twrp_gq5012bf1.mk             # retain recovery product as needed
├── lineage.dependencies          # if project uses it
├── proprietary-files.txt
├── extract-files.py
├── setup-makefiles.py
├── configs/
│   ├── audio/
│   ├── bluetooth/
│   ├── camera/
│   ├── gps/
│   ├── media/
│   ├── power/
│   ├── sensors/
│   ├── thermal/
│   ├── usb/
│   └── wifi/
├── init/
├── rootdir/
├── keylayout/
├── permissions/
├── overlay/
├── overlay-lineage/
├── vintf/
├── sepolicy/
│   ├── vendor/
│   ├── private/
│   └── public/
├── recovery/
├── prebuilt/
├── patches/                       # only where unavoidable
├── tools/
└── docs/
```

Do not create empty directories merely to match this sketch.

Use structure that matches the actual build system and evidence.

---

# 35. Recovery coexistence rule

The final full Android tree must not destroy the working OrangeFox target.

Prefer:

- shared verified hardware facts in common device files;
- recovery-specific files under recovery-specific makefiles/config;
- full-ROM product definitions separately;
- conditionals only where necessary and understandable.

A full ROM build must not accidentally inherit TWRP/OrangeFox-only configuration.

A recovery build must not accidentally pull the entire full-ROM product stack.

---

# 36. Automation to build first

Before large manual tree edits, create reusable offline tooling.

Recommended tooling:

```text
tools/inventory_snapshots.py
tools/inventory_stock.py
tools/unpack_images.py
tools/inventory_vintf.py
tools/inventory_modules.py
tools/inventory_elf.py
tools/inventory_init.py
tools/inventory_sysfs.py
tools/generate_proprietary_candidates.py
tools/audit_device_tree.py
```

Exact filenames may differ.

The important behavior is:

1. consume the two live snapshots;
2. consume extracted stock partitions;
3. generate machine-readable inventories;
4. correlate services/HALs/modules/configs/blobs;
5. output a human-readable unresolved list;
6. never mutate source evidence;
7. be rerunnable.

Avoid one-off shell archaeology that cannot be repeated.

---

# 37. Suggested analysis workspace

Use a gitignored workspace such as:

```text
.work/gq5012bf1/
├── snapshots/
│   ├── stock/
│   └── recovery/
├── stock/
│   ├── boot/
│   ├── vendor_boot/
│   ├── vendor/
│   ├── odm/
│   ├── product/
│   ├── system_ext/
│   ├── vendor_dlkm/
│   ├── odm_dlkm/
│   └── system_dlkm/
├── dt/
├── elf/
├── modules/
├── vintf/
└── reports/
```

Never commit giant extracted partition trees to the device repo.

Commit only scripts, small configs, manifests, generated summaries that are useful to maintainers, and intentionally included prebuilts.

---

# 38. Reports Codex should maintain

Create/update concise evidence reports such as:

```text
docs/hardware-map.md
docs/partition-map.md
docs/hal-map.md
docs/service-map.md
docs/module-map.md
docs/blob-map.md
docs/battery-charging.md
docs/camera-thermal.md
docs/display-secondary.md
docs/audio.md
docs/sensors.md
docs/connectivity.md
docs/known-unknowns.md
```

Every uncertain statement should be labelled as:

```text
VERIFIED
STRONG INFERENCE
UNKNOWN
```

Do not turn inference into fact merely because it is plausible.

---

# 39. First execution plan

On the first full-device-tree session, do this in order.

## Phase A — preserve and inspect

1. Read this file completely.
2. Run `git status --short`.
3. Inspect recent commits, especially `bbe7af2` and surrounding recovery/security work.
4. Read current `BoardConfig.mk`, `device.mk`, recovery init, fstab and SELinux.
5. Verify the two live snapshot archive hashes.
6. Extract them into a gitignored analysis directory.
7. Locate and inventory the stock firmware package.
8. Do not edit core device configuration yet.

## Phase B — generate evidence

9. Generate stock/recovery hardware inventories.
10. Generate full VINTF/HAL map.
11. Generate kernel-module map and dependency graph.
12. Generate ELF dependency graph.
13. Generate init/service/property map.
14. Generate partition/filesystem map.
15. Generate device-node/sysfs map.
16. Generate a stock-vs-current-tree coverage report.

## Phase C — establish full ROM skeleton

17. Add full Android product makefile.
18. Refactor `device.mk` so it can serve the full device without breaking recovery.
19. Add extraction/setup tooling.
20. Create initial `proprietary-files.txt` from evidence.
21. Generate vendor makefiles.
22. Add VINTF manifests/matrices as required.
23. Add stock-derived configuration files with provenance comments.

## Phase D — subsystem bring-up

Work through:

```text
boot/partitions
graphics/display
touch/secondary display
audio
sensors
power/thermal/health
battery/charging
USB
Wi-Fi/Bluetooth/GNSS/NFC
RIL/IMS
camera
ThermoVue
fingerprint
LEDs/keys
DRM/media
SELinux
OTA
recovery coexistence
```

Do not skip an item because the ROM boots.

---

# 40. Build philosophy

Prefer evidence-driven compatibility with the stock vendor implementation.

This device is expected to rely heavily on proprietary MediaTek/Ulefone vendor components.

The goal is not to unnecessarily rewrite every vendor HAL.

The goal is to provide the correct device-side Android contract so stock-compatible vendor components operate correctly under LieppOS.

Where an open-source replacement is mature and compatible, use it deliberately.

Where the stock blob is required, retain/extract it cleanly.

---

# 41. Common failure modes to avoid

Do not:

- copy a random MT6878 device tree and rename it;
- assume all MT6878 phones share camera/audio/sensor topology;
- treat all DTB nodes as populated hardware;
- confuse alternate BOM nodes with active hardware;
- ship a blob without its rc/VINTF/SELinux/property dependencies;
- add dozens of permissive SELinux rules just to reach UI;
- replace working TrustKernel identity with marketing strings;
- mount encrypted userdata raw;
- disable metadata encryption;
- use a legacy USB gadget path;
- load every kernel module in recovery;
- hardcode battery values because one UI is wrong;
- assume the thermal camera is just another Camera2 device;
- assume the secondary display is a normal DRM display before proving it;
- wipe persistent/NV partitions;
- package device-unique calibration or secrets;
- rely on a single late-boot security experiment;
- regress recovery to make a full ROM build easier.

---

# 42. Evidence standard for declaring a subsystem "working"

A subsystem is not complete merely because compilation succeeds.

Prefer at least:

```text
build integration
+ service/HAL registration
+ kernel/device binding
+ real functional test
+ SELinux enforcing
+ reboot persistence
```

Examples:

Battery:

```text
capacity
status
voltage
temperature
current
charger connect/disconnect
fast-charge state where available
```

Display:

```text
boot animation/UI
brightness
sleep/wake
rotation
refresh modes
secondary display if applicable
```

Camera:

```text
enumeration
preview
capture
video
flash/IR where applicable
front/rear switching
thermal-camera path separately
```

Radio:

```text
SIM detection
calls
SMS
mobile data
5G/LTE
IMS if supported
```

Recovery:

```text
cold boot
enforcing
PIN decrypt
internal storage
ADB
fastbootd
MTP
sideload
external SD
OTG
battery
reboots
backup/restore sanity
```

Document what cannot be tested offline and leave explicit hardware-test instructions.

---

# 43. Definition of "maximum device tree"

"Maximum" does not mean maximum line count.

It means:

- maximum factual hardware coverage;
- maximum reproducibility;
- maximum preservation of known-good behavior;
- minimum guessing;
- minimum unnecessary hacks;
- clear provenance;
- complete proprietary dependency accounting;
- maintainable separation between device, vendor and recovery concerns;
- an explicit list of anything still unknown.

If the tree builds but silently loses thermal imaging, rear display, fast charging, fingerprint, sensors or IMS, the mission is not complete.

---

# 44. Current known unknowns

Do not pretend these are already solved unless the new live snapshots/stock analysis prove them:

```text
exact main display panel model
exact secondary panel implementation
secondary display userspace control path
battery cell topology
exact fuel gauge
full high-power charging topology
exact charger protocol path
camera sensor inventory
thermal-camera kernel/userspace architecture
fingerprint sensor/controller details
audio codec/amplifier topology
complete sensor chip inventory
Wi-Fi implementation details
Bluetooth implementation details
NFC controller
GNSS implementation
LED/work-light control path
all programmable key mappings
full modem/NV/calibration ownership
matching maintainable kernel source
complete boot-chain internals
```

The purpose of the new live snapshots is to shrink this list.

---

# 45. Historical findings that are no longer current blockers

Do not waste time re-solving these unless regression evidence appears:

```text
OrangeFox boot architecture
main display
main FT3680 touch
stable ADB
USB configfs controller
fastbootd availability
dynamic partition discovery
metadata filesystem
TrustKernel teed
KeyMint
Gatekeeper
Keystore2
BootControl
metadata decryption
/data F2FS mount
PIN-based user-0 FBE decrypt
SELinux enforcing security stack
```

The recovery/security stack is a working baseline.

---

# 46. Output expectations from Codex

When completing a substantial work session:

1. summarize what was learned;
2. state what changed;
3. list files changed;
4. list commands/tests run;
5. distinguish build-tested vs hardware-tested;
6. note any new unknowns;
7. do not claim hardware functionality without evidence;
8. leave the tree in a coherent state;
9. make appropriate atomic commits if the user requested autonomous repo work.

If blocked, produce the strongest evidence-backed partial result rather than fabricating values.

---

# 47. Final directive

Treat `GQ5012BF1` as a real production device, not a generic MTK target.

Mine the stock firmware and captured runtime state aggressively.

Automate repetitive archaeology.

Preserve the working recovery/security foundation.

Build the full LieppOS-facing device contract subsystem by subsystem.

**The success criterion is not "it boots." The success criterion is "the stock hardware has been systematically accounted for, and every supported function has a traceable implementation path."**
