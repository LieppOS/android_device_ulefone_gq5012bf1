# GQ5012BF1 Findings

Detailed hardware, firmware, partition, recovery, encryption, and bring-up findings for the **Ulefone Armor 29 Pro Thermal / GQ5012BF1**.

This file intentionally contains the long-form investigation material that does not belong in the main device-tree README.

## Evidence classes

Findings are classified as:

- **Verified on hardware** — observed directly on the physical device.
- **Verified from stock firmware** — obtained from stock images, DTB, fstab, binaries, manifests, or vendor configuration.
- **Strong inference** — supported by multiple observations but not directly proven.
- **Unknown / needs testing** — unresolved.

---

# Hardware and firmware

## Device identity

**Verified on hardware / stock firmware**

```text
Manufacturer: Ulefone
Retail model: Armor 29 Pro Thermal
Product / codename: GQ5012BF1
Platform: MediaTek MT6878
Architecture: arm64
Stock Android: Android 15
Storage: UFS
A/B: yes
Virtual A/B: yes
Dynamic partitions: yes
```

Observed stock-derived kernel:

```text
6.1.115-android14-11-g6b18f0b574ab-ab12901745
```

The Android product-model string required by the TrustKernel verification path is:

```text
Armor 29 Pro
```

The retail product name may still be documented as Armor 29 Pro Thermal.

## Stock firmware fingerprint

```text
Ulefone/GQ5012BF1_EEA/GQ5012BF1:15/AP3A.240905.015.A2/1761131274:user/release-keys
```

Bring-up firmware package:

```text
GQ5012BF1_EEA_V15_user_20251022
```

---

# Boot architecture

## A/B and dynamic partitions

Observed properties:

```text
ro.boot.slot_suffix=_a
ro.virtual_ab.enabled=true
ro.boot.dynamic_partitions=true
```

Logical mapper devices observed include:

```text
odm_dlkm_a
odm_dlkm_b
product_a
product_b
system_a
system_b
system_dlkm_a
system_dlkm_b
system_ext_a
system_ext_b
vendor_a
vendor_b
vendor_dlkm_a
vendor_dlkm_b
scratch
```

## vendor_boot

**Verified from stock firmware and hardware readback**

Header version:

```text
4
```

Geometry:

```text
page size:        4096
base:             0x00000000
kernel offset:    0x40000000
ramdisk offset:   0x66f00000
tags offset:      0x47c80000
dtb offset:       0x47c80000
vendor cmdline:   bootopt=64S3,32N2,64N2
partition size:   67108864 bytes
```

Vendor ramdisk table contains:

```text
type 1: PLATFORM
type 2: recovery
```

The stock PLATFORM fragment is device-critical and must be preserved when rebuilding recovery.

Known stock component hashes:

```text
PLATFORM SHA256:
9201a4e5c1b7cb1fc0ce35375af10a3d966dac8b84615a226f98b7d7be2aec00

DTB SHA256:
bc156c29c33d8226230f07888df0a3d7a1e9c4b85c5fd550a4c4bd1a3134c0d4

stock full vendor_boot SHA256:
c8953d16b7a47976362aa23b53d0a08dde451f25cab4c552fa70c43e56ee0756
```

A live `vendor_boot_a` readback returned exactly 64 MiB and matched the flashed image byte-for-byte during bring-up.

Important packaging result:

> The normal generated `out/target/product/gq5012bf1/vendor_boot.img` may contain only a tiny generated PLATFORM fragment. It must not be flashed directly. The authoritative OrangeFox payload is the type-2 `recovery.cpio.lz4` fragment, merged with the stock PLATFORM and DTB into a full 64 MiB image.

---

# Kernel and DTB

The device currently uses the stock prebuilt kernel.

No complete maintainable matching kernel source tree has been established.

## DTB wrapper

**Verified from stock firmware**

The stock DTB has a 64-byte MediaTek/proprietary wrapper before the FDT.

```text
FDT magic offset: 64
FDT magic:         d00dfeed
FDT version:       17
FDT total size:    342331 bytes
wrapped DTB size:  342395 bytes
```

The decoded tree contains roughly 1390 nodes.

---

# Display and touch

## Main display

**Verified on hardware**

```text
logical coordinate range: 1080 x 2400
```

Exact panel vendor/model remains unresolved.

## Main touchscreen — FocalTech FT3680

**Verified on hardware and stock DTB**

DT node:

```text
/soc/spi3@11013000/focaltech@39
```

Compatible:

```text
focaltech,fts
```

Properties:

```text
spi-max-frequency = 6000000
focaltech,max-touch-number = 10
focaltech,display-coords = <0 0 1080 2400>
```

Normal Android binding:

```text
driver: /sys/bus/spi/drivers/fts_ts
module: /sys/module/focaltech_touch_spi_ft3680
```

Module:

```text
focaltech_touch_spi_ft3680.ko
```

SHA-256:

```text
6629ec6148ac361a5f0085b8b19efa9d591426679f58262c4998345f41931162
```

Observed controller ID:

```text
0x5662
```

Driver identification:

```text
FocalTech V4.2 20240407
```

The module contains an embedded firmware fallback and can initialize without an external firmware file.

## Secondary Hynitron touch controller

**Verified present and bound in Android**

DT node:

```text
/soc/i2c@11c20000/hynitron@15
```

Compatible:

```text
hynitron,hyn_ts
```

Properties:

```text
hynitron,display-coords = <340 340>
hynitron,max-touch-number = <1>
```

Binding:

```text
driver: /sys/bus/i2c/drivers/hyn_ts
module: /sys/module/hynitron
```

**Strong inference:** this controller is associated with a small/secondary display or touch surface because it is 340x340, single-touch, and appears alongside dependencies involving `spi_tiny_co5300_lcd.ko`.

Its exact physical role is still unresolved.

## Alternative touch nodes

Present in stock DTB but not bound in the tested configuration:

Ilitek:

```text
compatible=tchip,ilitek
reg=0x41
```

Chipone:

```text
compatible=chipone-tddi
reg=0x48
chipone,x-res=1080
chipone,y-res=2460
```

**Strong inference:** these are alternate BOM/panel configurations supported by the shared vendor DTB.

## YFT support modules

Observed:

```text
yft_devinfo.ko
yft_tpd_gesture.ko
yft_gpio_keys.ko
```

Relevant `yft_devinfo` strings:

```text
yft_set_touch_device_used
yft_touchpanel_device_add
yft_spitouchpanel_device_add
yft_touchpanel_spi_device_add
touch_fw_version
second_touch_fw_version
```

`yft_tpd_gesture.ko` appears to be a gesture/wake helper rather than a controller driver.

---

# vendor_dlkm

**Verified**

Slot-A logical partition:

```text
vendor_dlkm_a -> /dev/block/dm-12
```

Filesystem:

```text
EROFS
```

Approximate size:

```text
16 MiB
```

Approximately 219 kernel modules were observed.

Touch-related modules include:

```text
focaltech_touch_spi_ft3680.ko
hynitron.ko
mtk_ioctl_touch_boost.ko
touch_boost.ko
```

---

# Storage and partitions

## metadata

```text
/dev/block/by-name/metadata -> /dev/block/sdc16
filesystem: F2FS
```

Manual read-only mounting was verified.

Observed directories include:

```text
aconfig
apex
bootstat
gsi
ota
password_slots
phh
prefetch
staged-install
tradeinmode
vold
watchdog
```

## userdata

```text
/dev/block/by-name/userdata -> /dev/block/sdc76
filesystem: F2FS
```

Kernel support for `f2fs` and `ext4` is present.

## Physical misc

```text
/dev/block/by-name/misc -> /dev/block/sdc1
```

The physical node must resolve to:

```text
u:object_r:misc_block_device:s0
```

for the MediaTek BootControl HAL.

## Additional stock firmware partitions

Stock MediaTek fstab data exposes:

```text
protect1
protect2
nvdata
nvcfg
persist
frp
nvram
proinfo
lk1
bootloader2
para
misc
init_boot
boot
vbmeta_vendor
vbmeta_system
logo
expdb
seccfg
tee1
tee2
scp1
scp2
sspm1
sspm2
dpm1
dpm2
mcupm1
mcupm2
modem
md1dsp
md1arm7
md3img
gz1
gz2
ccu
vcp
gpueb
mcf_ota
vendor_boot
mvpu_algo1
mvpu_algo2
apusys1
apusys2
spmfw
pi_img
boot_para
odmdtbo
dtbo
connsys_wifi
connsys_bt
otp
vbmeta
```

Persistent mounts include:

```text
protect1 -> /mnt/vendor/protect_f
protect2 -> /mnt/vendor/protect_s
nvdata   -> /mnt/vendor/nvdata
nvcfg    -> /mnt/vendor/nvcfg
persist  -> /mnt/vendor/persist
```

---

# Encryption

## Stock userdata encryption

**Verified from stock fstab / metadata**

```text
fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized
keydirectory=/metadata/vold/metadata_encryption
```

Details:

```text
contents encryption: aes-256-xts
filename encryption: aes-256-cts
fscrypt policy: v2
inline crypto optimization: enabled
```

Metadata key directory:

```text
/metadata/vold/metadata_encryption/key
```

Observed files:

```text
version
secdiscardable
keymaster_key_blob
encrypted_key
```

Observed sizes:

```text
version              1 byte
secdiscardable       16384 bytes
keymaster_key_blob   565 bytes
encrypted_key        92 bytes
```

The active recovery configuration includes:

```make
BOARD_USES_METADATA_PARTITION := true
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
TW_USE_FSCRYPT_POLICY := 2
```

---

# TrustKernel security stack

## Stock implementation

**Verified from stock Android/vendor**

Binder interfaces:

```text
android.hardware.security.keymint.IKeyMintDevice/default
android.hardware.security.keymint.IRemotelyProvisionedComponent/default
android.hardware.security.secureclock.ISecureClock/default
android.hardware.security.sharedsecret.ISharedSecret/default
android.hardware.gatekeeper.IGatekeeper/default
android.system.keystore2.IKeystoreService/default
```

Implementations:

```text
/vendor/bin/teed
/vendor/bin/hw/android.hardware.security.keymint@3.0-service.trustkernel
/vendor/bin/hw/android.hardware.gatekeeper-service.trustkernel
/system/bin/keystore2
```

Stock TrustKernel state includes:

```text
ro.vendor.mtk_trustkernel_tee_support=1
vendor.trustkernel.ready=true
vendor.trustkernel.fs.mode=3
vendor.trustkernel.fs.state=ready
```

Relevant storage and devices:

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

Stock uevent ownership/modes include:

```text
/dev/teeperf        0660 system system
/dev/tkcore_admin   0600 system system
/dev/tkcore_client  0660 root   system
/dev/tkcore_fp      0660 root   system
/dev/rpmb0          0660 root   system
```

The TEE daemon runs as:

```text
system:system
capability SYS_RAWIO
domain u:r:tee:s0
```

KeyMint:

```text
u:r:hal_keymint_default:s0
```

Gatekeeper:

```text
u:r:hal_gatekeeper_default:s0
```

Keystore2:

```text
u:r:keystore:s0
```

---

# Recovery FBE bring-up — final result

## Final verified state

A cold boot into OrangeFox now reaches the target state:

```text
SELinux enforcing
TrustKernel stack running
metadata-encrypted userdata mapper created
/data mounted as F2FS with inlinecrypt
one correct PIN accepted
user-0 CE fscrypt key installed
/data/system_ce/0 readable
/data/media/0 readable
no ADB intervention
repeatable across reboots
usable recovery in roughly 26 seconds
```

Known-good integration was reported after:

```text
bbe7af2
```

## Actual decisive fixes

### 1. Missing TrustKernel hard-link permission

The final enforcing denial immediately preceding failed persistent-object commits was:

```text
avc: denied { link } for name="block0.1"
scontext=u:r:tee:s0
tcontext=u:object_r:tkcore_protect_data_file:s0
tclass=file
permissive=0
```

In this AOSP policy generation, `create_file_perms` does **not** include `link`.

The exact missing permission therefore had to be granted explicitly:

```te
allow tee tkcore_protect_data_file:file link;
```

This was a real root cause.

### 2. TrustKernel mount-root traversal

The two `teed --prot` mount roots resolved to types missing from recovery policy:

```text
/mnt/vendor/persist
/mnt/vendor/protect_f
```

Observed raw contexts included:

```text
persist_data_file
protect_f_data_file
```

Without matching recovery policy types they resolved as `unlabeled`, and `tee` could not traverse them.

The final policy:

- declares the stock parent types,
- labels the mount roots,
- grants `tee` only the needed `dir search`,
- leaves the TrustKernel payload itself under `tkcore_protect_data_file`.

### 3. KeyMint / Gatekeeper TA session ordering

The decisive startup constraint is **serialization**, not a particular long delay.

Working order:

```text
teed
  -> KeyMint
     -> Gatekeeper
        -> Keystore2
```

Starting KeyMint and Gatekeeper together reproduced:

```text
No suitable auth token found
KEY_USER_NOT_AUTHENTICATED
```

Build30 starts Gatekeeper only after KeyMint is already running. Keystore2 starts after Gatekeeper.

The earlier 90-second `/data` wait was incidental and caused slow/hanging boots. It is not a required part of the final FBE mechanism.

### 4. Product model requirement

A controlled hardware test established that the TrustKernel verification state depends on the Android product-model string.

Recovery with:

```text
Armor 29 Pro Thermal
```

produced the wrong TrustKernel verification state.

Recovery with:

```text
Armor 29 Pro
```

reached the same verification state as working Android even while the actual recovery verified-boot state remained orange.

Therefore:

> Retail documentation name: Armor 29 Pro Thermal  
> Android security/product model used by recovery: `Armor 29 Pro`

### 5. VINTF compatibility

OrangeFox 14.1 recovery uses an older libvintf generation than the mounted Android framework.

The Android framework manifest using meta-version 9 was rejected by recovery libvintf 8.

A minimal recovery-compatible framework VINTF declaration at meta-version 8, including the required Keystore2 AIDL declaration, allowed service registration.

This was necessary to make the recovery security stack usable.

### 6. Task profiles

The working recovery task profile input matched the active Android system copy:

```text
/system/etc/task_profiles.json
size: 15069 bytes
SHA256:
f230763e7676dfb39397c2d909def41ddd59d73ff7b334718b885ce24095bf21
```

Using the active system copy stabilized recovery logging sufficiently for bring-up.

### 7. Keystore2 domain

Running Keystore2 in the dedicated platform:

```text
u:r:keystore:s0
```

was proven to register the service successfully once the ramdisk executable and recovery runtime access were correctly integrated.

Recovery-specific accesses observed on the successful synthetic-password path include:

```te
allow recovery keystore:keystore2 add_auth;
allow recovery locksettings_key:keystore2_key { get_info use req_forced_op };
```

### 8. Metadata-key read-only policy

OrangeFox executes the metadata-encryption vold logic inside the recovery process.

The metadata key bundle is labelled:

```text
vold_metadata_file
```

The verified recovery requirement is read-only:

```text
dir: search
file: read getattr open
```

No create/write/rename/unlink permission was justified.

The recovery-specific platform policy patch was designed around that read-only contract.

### 9. BootControl physical misc label

The MediaTek BootControl HAL dereferences `/dev/block/by-name/misc` to the physical inode:

```text
/dev/block/sdc1
```

Labelling only the symlink is insufficient.

The physical node must be:

```text
misc_block_device
```

Once correctly labelled, BootControl registered and:

```text
bootctl get-current-slot
```

returned slot 0 successfully under enforcing SELinux.

---

# Important withdrawn hypotheses

The following were useful during investigation but are **not final requirements**.

## Withdrawn: Gatekeeper at Android 14 / KeyMint at Android 16

A late manual decrypt once appeared to require:

```text
Gatekeeper initialized at release 14
KeyMint initialized at release 16
```

Later binary/source inspection showed the stock Gatekeeper HAL contains no Android build-property strings and has no mechanism to consume `ro.build.version.release`.

Successful final decrypt also occurred with release reading 14.

Therefore the split-release model is withdrawn.

## Withdrawn: 90-second delay is load-bearing

A successful decrypt occurred after a long wait, which initially suggested the delay was required.

Later testing proved that:

- the long wait was a timeout/fail-open artifact,
- it made subsequent boots appear stuck,
- the actual requirement is KeyMint/Gatekeeper session serialization.

Build30 removed the `/data` dependency from the boot path and retained reliable decrypt at approximately 26 seconds.

## Withdrawn: RPMB diagnostic is fatal

Both working Android and recovery logged:

```text
Verify RPMB Key failed with 0x7
```

Working Android still decrypts userdata.

Therefore that diagnostic alone is not the FBE blocker.

---

# Bring-up chronology

This is retained as investigation history, not as a list of current requirements.

## Early crypto integration

The device tree first enabled:

```make
BOARD_USES_METADATA_PARTITION := true
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
TW_USE_FSCRYPT_POLICY := 2
```

Build-time inspection confirmed generic KeyMint/Keymaster, Gatekeeper, Keystore2, and fscrypt components were included.

Runtime decryption still required the stock TrustKernel backend.

## Build17 phase

Build17 established most of the architecture through live tests:

- corrected Android product model to `Armor 29 Pro`,
- brought up TrustKernel `teed`,
- identified device-node ownership differences,
- stabilized logging with the active system task profile file,
- created a recovery-compatible VINTF manifest,
- registered KeyMint and Keystore2,
- created the metadata-encrypted userdata mapper,
- validated the decrypted F2FS mapper,
- fixed BootControl through physical misc labelling,
- mounted `/data`,
- started TrustKernel Gatekeeper,
- verified the correct credential,
- installed the user-0 CE key,
- exposed `/data/system_ce/0` and `/data/media/0`.

This proved end-to-end FBE was possible before persistence was integrated.

## Build18 phase

Build18 attempted to persist the live sequence.

It exposed two independent integration defects:

1. security preparation ran before dynamic partition mappers existed;
2. proper-domain TrustKernel services could not execute/map the recovery rootfs linker under enforcing SELinux.

Live permissive testing proved the service definitions themselves were otherwise sufficient for full FBE.

## Build19 phase

Build19 converted the live work into a proper recovery SELinux architecture:

- device TrustKernel types and contexts,
- property contexts,
- RPMB types,
- protected storage types,
- proper KeyMint/Gatekeeper HAL clients,
- dedicated Keystore2 domain,
- read-only metadata-key policy carveout,
- recovery property-context packaging dependencies.

This phase removed the need for broad generic `device`, `unlabeled`, or `vendor_default_prop` permissions.

## Build20–22 phase

These builds isolated startup blockers.

Build22 proved the rootfs linker execution fix for TrustKernel proper domains and then exposed missing HAL-to-recovery Binder calls for KeyMint and Gatekeeper.

Those Binder directions were added narrowly.

## Build23–26 phase

These builds chased misleading symptoms around:

```text
DEAD_OBJECT
INVALID_KEY_BLOB
KEY_USER_NOT_AUTHENTICATED
```

Some live sequences appeared to implicate Android release identity.

Later evidence showed these conclusions were incomplete because late-boot successful tests inherited TrustKernel state created earlier in the same secure-world lifetime.

The split-release theory was ultimately withdrawn.

## Build27 audit

Direct stock binary/source audit established:

- KeyMint consumes Android identity/property inputs.
- Gatekeeper does not consume build properties.
- KeyMint `TEE return -33` maps to AOSP `INVALID_KEY_BLOB`.
- Gatekeeper `Verify invoke command return -1` is a trusted-application return, not a Linux Binder/SELinux error.
- TrustKernel persistent storage behavior and once-per-secure-world initialization explained why late manual retries differed from cold boot.

## Build28 breakthrough

Build28 identified the real enforcing storage failures:

```text
tee -> tkcore_protect_data_file:file link
tee -> persist/protect_f mount-root traversal
```

Once fixed, cold enforcing FBE decrypt worked.

## Build30 final startup cleanup

Build30 removed the 90-second `/data` dependency and kept only the real service ordering requirement.

Verified result:

```text
usable recovery ~26 s
cold boot
SELinux enforcing
/data mounted
one PIN decrypt
repeatable
no ADB intervention
```

---

# USB

**Verified**

The device uses Android USB configfs:

```text
sys.usb.configfs=1
sys.usb.controller=11201000.usb0
```

Legacy `/sys/class/android_usb/android0` initialization is unsuitable for this platform.

---

# Physical input

Observed input devices include:

```text
gpio-keys
mtk-pmic-keys
yft-gpio-keys
madev
fts_ts
```

`madev` is associated with the Microarray fingerprint/input stack.

Exact fingerprint sensor model remains unresolved.

---

# Battery and charging

## Verified nodes

Power-supply nodes include:

```text
/sys/class/power_supply/battery
/sys/class/power_supply/3rd-gauge
```

Both have returned correct capacity values during testing.

Example:

```text
capacity: 63
status: Charging
```

Additional MediaTek charger/gauge nodes observed:

```text
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

Charging logs identify components including:

```text
mt6375
sc8571
```

## Still unresolved

- exact fuel-gauge IC
- battery cell configuration
- design capacity
- precise charger topology
- SC8571 role
- charge-pump layout
- fast-charge protocols
- USB-PD implementation
- final OrangeFox health HAL / battery UI path and live update behavior

---

# Strong inferences

- Hynitron is probably the touch controller for a secondary 340x340 display.
- Ilitek and Chipone nodes are probably alternate BOM configurations in a shared DTB.
- `spi_tiny_co5300_lcd.ko` is likely part of the secondary-display subsystem.
- YFT modules appear to implement board/component detection and touch-device selection.
- The firmware supports multiple panel/touch combinations selected at runtime.

---

# Still to discover

## Display

- exact main panel vendor/model
- timings
- refresh-rate modes
- DSC configuration
- exact secondary display panel/interface

## Touch

- exact Hynitron hardware role
- secondary-touch userspace behavior
- touch firmware versions
- YFT/BOM selection logic

## Cameras

- image sensors
- thermal-camera architecture
- EEPROM/calibration
- autofocus mapping
- vendor camera HAL structure

## Thermal subsystem

- thermal imaging sensor
- interface/bus
- firmware
- userspace service
- calibration data

## Fingerprint

- exact Microarray sensor/controller
- bus details
- HAL
- trusted-app architecture

## Audio

- codec topology
- amplifier models
- microphones
- DSP routing
- MT6369/external amplifier relationship

## Connectivity

- Wi-Fi chipset/configuration
- Bluetooth details
- NFC
- GNSS
- modem firmware ownership
- RF layout

## Sensors

- accelerometer
- gyroscope
- magnetometer
- proximity
- ambient light
- barometer if present
- sensor-hub routing

## LEDs / lighting

- status LEDs
- torch/flash mapping
- IR hardware
- auxiliary/programmed lighting

## Buttons / accessories

- GPIO mapping for programmable buttons
- PTT controls if present
- accessory detection
- headset detection
- USB accessory behavior

## Boot chain

- exact bootloader stages
- preloader configuration
- LK/U-Boot variant
- AVB key hierarchy
- rollback indices
- anti-rollback behavior
- MediaTek download-agent requirements

## Kernel

- complete source provenance
- matching defconfig
- matching DTS/DTSI
- module configuration
- GKI/vendor ABI details
- matching published GPL sources

## Android vendor implementation

- complete HAL inventory
- health HAL
- thermal HAL
- power HAL
- vibrator/haptics
- lights
- fingerprint
- camera
- audio
- USB
- radio/modem

---

# Research policy

Future findings should continue to be labelled as:

```text
Verified on hardware
Verified from stock firmware
Strong inference
Unknown / needs testing
```

Historical failed hypotheses should remain documented as withdrawn rather than silently converted into permanent assumptions.
