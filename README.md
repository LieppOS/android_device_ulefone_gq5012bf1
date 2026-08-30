# Ulefone Armor 29 Pro Thermal — GQ5012BF1 Device Tree

Device information and Android device-tree work for the **Ulefone Armor 29 Pro Thermal** (`GQ5012BF1`).

This repository is intended to document and maintain **device-specific hardware, firmware, partition, kernel, and Android configuration knowledge**.

Recovery-specific implementation, build scripts, and release files should live in a separate recovery repository.

---

## Device

| Property | Value |
|---|---|
| Manufacturer | Ulefone |
| Model | Armor 29 Pro Thermal |
| Product / codename | `GQ5012BF1` |
| SoC / platform | MediaTek MT6878 |
| Architecture | arm64 |
| Stock Android | Android 15 |
| Kernel | Linux 6.1.115 |
| Kernel KMI generation | Android 14 |
| Partition scheme | A/B + Virtual A/B |
| Dynamic partitions | Yes |
| Storage | UFS |

Observed stock-derived kernel:

```text
Linux localhost 6.1.115-android14-11-g6b18f0b574ab-ab12901745 #1 SMP PREEMPT Fri Jan 10 22:12:05 UTC 2025 aarch64
```

---

## Boot and partition architecture

The device uses:

- A/B slots
- Virtual A/B
- Dynamic partitions
- `super`
- `boot`
- `init_boot`
- `vendor_boot`
- `dtbo`
- `vbmeta`
- `vbmeta_system`
- `vbmeta_vendor`

Observed properties:

```text
ro.boot.slot_suffix=_a
ro.virtual_ab.enabled=true
ro.boot.dynamic_partitions=true
```

The tested active slot during bring-up has been slot A.

### vendor_boot

`vendor_boot` uses header version 4.

Known geometry:

```text
header version:   4
page size:        4096
base:             0x00000000
kernel offset:    0x40000000
ramdisk offset:   0x66f00000
tags offset:      0x47c80000
dtb offset:       0x47c80000
vendor cmdline:   bootopt=64S3,32N2,64N2
partition size:   67108864 bytes
```

The stock `vendor_boot` contains separate vendor ramdisk fragments, including:

```text
type 1: PLATFORM
type 2: recovery
```

The stock PLATFORM fragment is important because it contains device-specific kernel modules and early userspace required by the hardware.

---

## Kernel and DTB

The device currently uses the stock prebuilt kernel.

No complete maintainable kernel source tree has been established in this repository.

If full kernel source becomes available later, it should preferably live in a separate repository such as:

```text
android_kernel_ulefone_gq5012bf1
```

### DTB

The stock DTB has a 64-byte MediaTek/proprietary wrapper before the actual FDT.

Observed:

```text
FDT magic offset: 64
FDT magic:         d00dfeed
FDT version:       17
FDT total size:    342331 bytes
```

The wrapped DTB file is approximately:

```text
342395 bytes
```

The tree contains roughly 1390 nodes.

---

## Display

The main display is confirmed working with the stock kernel and DTB.

Known display/touch coordinate range:

```text
1080 x 2400
```

Further panel identification and exact panel vendor/model are not yet fully documented here.

---

## Touch hardware

Multiple touchscreen controller nodes exist in the stock DTB.

### Main touchscreen — confirmed

The main display touchscreen is a **FocalTech FT3680** connected over SPI3.

Device-tree node:

```text
/soc/spi3@11013000/focaltech@39
```

Compatible:

```text
focaltech,fts
```

Observed DT properties include:

```text
spi-max-frequency = 6000000
focaltech,max-touch-number = 10
focaltech,display-coords = <0 0 1080 2400>
```

Normal Android binds it as:

```text
driver: /sys/bus/spi/drivers/fts_ts
module: /sys/module/focaltech_touch_spi_ft3680
```

Kernel module:

```text
focaltech_touch_spi_ft3680.ko
```

Known module SHA-256:

```text
6629ec6148ac361a5f0085b8b19efa9d591426679f58262c4998345f41931162
```

Observed controller ID:

```text
0x5662
```

The driver reports:

```text
FocalTech V4.2 20240407
```

The module contains an embedded firmware fallback and can initialize the touchscreen even when the external firmware file is not present.

### Secondary touch controller — confirmed present

A Hynitron controller also binds in normal Android.

Device-tree node:

```text
/soc/i2c@11c20000/hynitron@15
```

Compatible:

```text
hynitron,hyn_ts
```

Observed DT properties:

```text
hynitron,display-coords = <340 340>
hynitron,max-touch-number = <1>
```

Normal Android binds it as:

```text
driver: /sys/bus/i2c/drivers/hyn_ts
module: /sys/module/hynitron
```

Strong inference:

The Hynitron controller is likely associated with a small or secondary display/touch surface rather than the main 1080x2400 panel.

This is supported by:

- `340x340` coordinates
- single-touch capability
- dependency relationships involving `spi_tiny_co5300_lcd.ko`

The exact hardware role should still be documented more carefully.

### Other touch-compatible nodes present but not bound

The stock DTB also contains:

#### Ilitek

```text
compatible=tchip,ilitek
reg=0x41
```

#### Chipone

```text
compatible=chipone-tddi
reg=0x48
chipone,x-res=1080
chipone,y-res=2460
```

In the tested normal Android state, neither was bound to a driver.

These may represent alternative panel/controller configurations supported by the common firmware tree.

---

## YFT touch/device infrastructure

The firmware includes YFT-specific device and touch helper modules.

Observed modules include:

```text
yft_devinfo.ko
yft_tpd_gesture.ko
yft_gpio_keys.ko
```

`yft_devinfo.ko` appears to provide device detection / touch-device bookkeeping.

Relevant strings include:

```text
yft_set_touch_device_used
yft_touchpanel_device_add
yft_spitouchpanel_device_add
yft_touchpanel_spi_device_add
touch_fw_version
second_touch_fw_version
```

`yft_tpd_gesture.ko` is a gesture/wake helper rather than the real touchscreen-controller driver.

---

## vendor_dlkm

The device uses a logical `vendor_dlkm` partition.

On slot A:

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

The partition contains many device-specific loadable kernel modules.

Touch-related modules found there include:

```text
focaltech_touch_spi_ft3680.ko
hynitron.ko
mtk_ioctl_touch_boost.ko
touch_boost.ko
```

A full module-tree inspection found approximately 219 module files.

---

## Storage and filesystems

### metadata

Block device:

```text
/dev/block/by-name/metadata -> /dev/block/sdc16
```

Filesystem:

```text
F2FS
```

Manual read-only F2FS mounting has been verified successfully.

Observed mount result:

```text
/dev/block/sdc16 on /metadata type f2fs
```

The metadata filesystem contains normal Android metadata directories including:

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

### userdata

Block device:

```text
/dev/block/by-name/userdata -> /dev/block/sdc76
```

Filesystem:

```text
F2FS
```

Kernel support for both `f2fs` and `ext4` is present.

---

## Encryption

The stock userdata configuration uses Android file-based encryption and metadata encryption.

Known userdata encryption flags:

```text
fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized
keydirectory=/metadata/vold/metadata_encryption
```

Known details:

```text
contents encryption: aes-256-xts
filename encryption: aes-256-cts
fscrypt policy: v2
inline crypto optimization: enabled
```

Metadata encryption key directory:

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

Observed keymaster generation:

```text
4.x
```

This area still needs deeper documentation of the exact KeyMint / Keymaster / Gatekeeper implementation and dependencies.

---

<!-- DT-CRYPTO-BUILD-VALIDATION-START -->
## Encryption integration status

The device tree now reflects the stock userdata encryption model and metadata-partition requirements.

Current `BoardConfig.mk` settings under validation:

```make
BOARD_USES_METADATA_PARTITION := true
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
TW_USE_FSCRYPT_POLICY := 2
```

These settings match the already verified stock storage layout:

```text
/metadata -> F2FS
/data     -> F2FS

fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized
keydirectory=/metadata/vold/metadata_encryption
```

### Build-time validation

A clean recovery ramdisk build with the encryption configuration enabled completed successfully.

Validated recovery fragment:

```text
size:    approximately 33 MiB
entries: 3939
SHA-256: ba0e3989b1a75d57ba52118a87f82904a6d4940d37875b2eb6ffe1f4591b89ea
```

The build contains crypto/FBE userspace and libraries including:

```text
fscryptpolicyget
keystore2
keystore_cli_v2
android.hardware.gatekeeper@1.0
android.hardware.keymaster@3.0
android.hardware.keymaster@4.0
android.hardware.keymaster@4.1
android.hardware.security.keymint-V3-ndk
libfscrypt
libgatekeeper
libkeymaster4support
libkeymaster4_1support
libkeymint
libkeymint_support
```

This confirms that the device-tree encryption flags cause the required generic Android crypto stack to be included in the built ramdisk.

The build also preserved all previously required core files:

```text
system/bin/init
system/bin/recovery
system/bin/adbd
system/bin/fastbootd
sepolicy
file_contexts
system/etc/recovery.fstab
init.recovery.mt6878.rc
```

The known main touchscreen module was also preserved byte-for-byte:

```text
recovery/root/lib/modules/focaltech_touch_spi_ft3680.ko
SHA-256: 6629ec6148ac361a5f0085b8b19efa9d591426679f58262c4998345f41931162
```

Its init-time load rule is still present.

### What this proves

Verified:

- the device tree builds successfully with FBE support enabled
- metadata-partition support is enabled
- fscrypt policy v2 is selected
- Keymaster 3.0/4.0/4.1 compatibility libraries are present
- KeyMint V3 interfaces are present
- Gatekeeper and Keystore2 components are present
- `libfscrypt` is present
- the userdata fstab still carries the stock `v2+inlinecrypt_optimized` policy
- existing touchscreen support remains intact

Not yet verified on hardware:

- automatic metadata mount during early recovery startup
- metadata key unwrap through the device's real TEE/Keymaster implementation
- creation of the decrypted userdata block device
- successful F2FS `/data` mount
- DE/CE FBE key handling
- PIN/password decryption
- `/data/media/0` access
- persistent settings stored on real userdata

The compile-time result is therefore considered **verified**, while runtime decryption remains **under investigation**.
<!-- DT-CRYPTO-BUILD-VALIDATION-END -->

## USB

The device uses Android USB configfs.

Observed controller:

```text
11201000.usb0
```

Relevant stock-style properties:

```text
sys.usb.configfs=1
sys.usb.controller=11201000.usb0
```

Legacy `/sys/class/android_usb/android0` style initialization is not appropriate for the tested MediaTek configuration.

---

## Physical input

Confirmed input devices include:

```text
gpio-keys
mtk-pmic-keys
yft-gpio-keys
madev
fts_ts
```

`madev` is associated with the Microarray fingerprint/input stack.

Exact fingerprint sensor model and full biometric architecture are not yet documented.

---

## Battery and charging

Confirmed battery power-supply nodes include:

```text
/sys/class/power_supply/battery
/sys/class/power_supply/3rd-gauge
```

Both have reported a correct battery capacity value during testing.

Example observed state:

```text
capacity: 63
status: Charging
```

Additional MediaTek charging / gauge nodes exist, including:

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

Charging-related logs identify components such as:

```text
mt6375
sc8571
```

Exact charger IC topology and battery gauge architecture should still be documented properly.

---

## Dynamic partitions

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

This confirms a modern Android dynamic-partition layout backed by `super`.

---

## Stock firmware fingerprint

Observed stock firmware fingerprint:

```text
Ulefone/GQ5012BF1_EEA/GQ5012BF1:15/AP3A.240905.015.A2/1761131274:user/release-keys
```

Observed stock firmware package used during bring-up:

```text
GQ5012BF1_EEA_V15_user_20251022
```

---

## Verified hardware / firmware facts

The following are considered confirmed from real device testing or direct stock-firmware inspection:

- Device product is `GQ5012BF1`.
- Platform is MediaTek MT6878.
- Architecture is arm64.
- Stock Android is Android 15.
- Stock-derived kernel is Linux 6.1.115 with Android 14 KMI.
- Device uses UFS storage.
- Device uses A/B.
- Device uses Virtual A/B.
- Device uses dynamic partitions.
- Device uses `vendor_boot` v4.
- `vendor_boot` partition size is 64 MiB.
- Stock DTB contains a 64-byte wrapper before the FDT.
- Main touchscreen is FocalTech FT3680 on SPI3.
- Main touchscreen coordinates are 1080x2400.
- Main touchscreen supports 10 touches.
- FocalTech controller ID `0x5662` is detected.
- A Hynitron touch controller is also present and bound in Android.
- Hynitron DT coordinates are 340x340 and single-touch.
- Ilitek and Chipone alternative touch nodes exist but are not bound in the tested configuration.
- Real touch controller modules live in `vendor_dlkm`.
- `/metadata` is F2FS.
- `/data` is F2FS.
- `/metadata` can be mounted successfully.
- Android metadata-encryption key material exists.
- Userdata uses FBE v2 with inline crypto optimization.
- Keymaster generation is reported as 4.x.
- USB uses configfs with controller `11201000.usb0`.
- Battery capacity can be read from standard power-supply sysfs nodes.

---

## Strong inferences

These are well-supported but should not yet be treated as final hardware documentation:

- Hynitron is probably the touch controller for a secondary/small display.
- Ilitek and Chipone nodes are probably alternate hardware configurations included in a shared vendor DTB.
- `spi_tiny_co5300_lcd.ko` is likely part of the small secondary display subsystem.
- The vendor firmware tree appears to support multiple possible panel/touch combinations selected at runtime.
- Some YFT modules perform hardware identification and device-selection bookkeeping.

---

## Still to discover

The following hardware and firmware areas remain incomplete or undocumented.

### Display

- exact main display panel vendor
- exact panel controller/model
- display timing information
- refresh-rate modes
- DSC configuration, if used
- secondary display exact panel model
- secondary display interface and full DT configuration

### Touch

- exact role of the Hynitron 340x340 controller
- whether secondary touch should be exposed independently to Android userspace
- complete touch firmware versions
- relationship between YFT touch selection logic and board BOM variants
- purpose of inactive Ilitek and Chipone nodes

### Cameras

- exact image sensor models
- exact number of sensors
- thermal-camera architecture
- ISP routing
- camera EEPROM layout
- autofocus actuator mapping
- calibration partitions/files
- vendor camera HAL structure

### Thermal camera / thermal subsystem

- thermal imaging sensor model
- dedicated interface/bus
- firmware
- userspace service
- calibration data
- relationship to Ulefone thermal application stack

### Fingerprint

- exact fingerprint sensor model
- Microarray controller details
- SPI/I2C interface details
- vendor HAL and trusted-app architecture

### Audio

- codec topology
- speaker amplifier models
- microphone routing
- audio DSP configuration
- exact relationship between MT6369 and external amplifiers

### Battery and charging

- battery cell configuration
- battery capacity/design values
- exact fuel-gauge IC
- exact charging topology
- fast-charge protocols
- SC8571 role
- charge-pump arrangement
- USB-PD implementation

### Connectivity

- exact Wi-Fi chipset configuration
- Bluetooth details
- NFC controller
- GNSS architecture
- modem firmware layout
- antenna/RF configuration

### Sensors

- accelerometer
- gyroscope
- magnetometer
- proximity sensor
- ambient-light sensor
- barometer, if present
- sensor-hub routing

### LEDs / lighting

- notification/status LEDs
- torch/flash controller mapping
- IR hardware
- auxiliary lighting hardware
- programmable side/rear lighting, if present

### Buttons and external hardware

- exact GPIO map for programmable/action buttons
- PTT-style controls, if present
- external accessory detection
- headset detection
- USB accessory behavior

### Partitions and firmware

- complete partition table documentation
- exact sizes of all physical partitions
- complete `super` logical partition layout
- exact ownership of persistent calibration data
- NVRAM/NVDATA layout
- protect partitions
- modem/NV partitions
- factory/calibration partitions

### Boot chain

- exact bootloader stages
- preloader configuration
- LK / U-Boot variant and version
- AVB key hierarchy
- rollback-index locations
- bootloader unlock behavior
- anti-rollback behavior
- download-mode behavior
- SP Flash Tool / MediaTek download-agent requirements

### Kernel

- complete kernel source provenance
- matching kernel defconfig
- matching DTS/DTSI source
- exact module build configuration
- GKI/vendor-module ABI details
- whether Ulefone has published matching GPL sources

### Android vendor implementation

- complete vendor HAL inventory
- KeyMint implementation
- Gatekeeper implementation
- Weaver support
- health HAL implementation
- thermal HAL implementation
- power HAL implementation
- vibrator/haptics HAL
- lights HAL
- fingerprint HAL
- camera HAL
- audio HAL
- USB HAL
- radio/modem HAL structure

### Security and encryption

- exact metadata-encryption implementation
- KeyMint security level
- TEE implementation
- TrustZone vendor
- StrongBox availability
- Gatekeeper key storage
- credential-encryption flow
- wrapped-key support
- rollback-protected key behavior

---

<!-- DT-PARTITION-DISCOVERY-START -->
## Additional firmware partition findings

Stock MediaTek fstab data exposes the following physical firmware and persistent partitions in addition to the normal Android A/B and dynamic-partition layout:

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

The stock fstab also defines persistent mounts for:

```text
protect1 -> /mnt/vendor/protect_f
protect2 -> /mnt/vendor/protect_s
nvdata   -> /mnt/vendor/nvdata
nvcfg    -> /mnt/vendor/nvcfg
persist  -> /mnt/vendor/persist
```

These partitions are important targets for future documentation of modem/NV data, calibration, TEE, firmware, connectivity, and boot-chain ownership.

### vendor_boot readback validation

A live readback of `vendor_boot_a` returned exactly 64 MiB and matched the image previously written to the partition byte-for-byte.

```text
size: 67108864 bytes
SHA-256: 795c19628628dafb4d0b48990c9a0bceae04032387ae0866637233f0e4a27895
```

This independently confirms the physical `vendor_boot` partition size and full-image write/readback behavior.
<!-- DT-PARTITION-DISCOVERY-END -->

## Repository scope

This repository should contain device-specific Android configuration and documentation such as:

```text
BoardConfig.mk
AndroidProducts.mk
device makefiles
fstab files
init files
partition definitions
device properties
hardware configuration
device-specific prebuilts when legally appropriate
documentation
```

Recovery-specific packaging, recovery release images, and recovery-only build tooling should live in a separate repository.

Kernel source should also live separately if and when a proper kernel tree is established.

Suggested repository separation:

```text
android_device_ulefone_gq5012bf1
android_kernel_ulefone_gq5012bf1
android_vendor_ulefone_gq5012bf1
```

A recovery-specific repository can be added separately without changing the scope of this device repository.

---

## Research policy

New findings should ideally be classified as one of:

- **Verified on hardware**
- **Verified from stock firmware**
- **Strong inference**
- **Unknown / needs testing**

Avoid turning guesses into permanent device-tree assumptions without confirming them against either the real device or stock firmware.

<!-- DT-SECURITY-STACK-START -->
## Hardware-backed security stack

Stock Android confirms that this device uses a TrustKernel-backed AIDL KeyMint stack.

Verified running Binder services:

```text
android.hardware.security.keymint.IKeyMintDevice/default
android.hardware.security.keymint.IRemotelyProvisionedComponent/default
android.hardware.security.secureclock.ISecureClock/default
android.hardware.security.sharedsecret.ISharedSecret/default
android.hardware.gatekeeper.IGatekeeper/default
android.system.keystore2.IKeystoreService/default
```

Verified running implementations include:

```text
android.hardware.security.keymint@3.0-service.trustkernel
android.hardware.gatekeeper-service.trustkernel
teed
keystore2
gatekeeperd
```

The vendor VINTF manifest selects the TrustKernel implementations for KeyMint and Gatekeeper.

Relevant TEE devices and kernel infrastructure observed on the running system include:

```text
/dev/trusty-ipc-dev0
/dev/gz_kree
/dev/teeperf
trusty kernel worker threads
```

`trustkernel.rc` uses persistent TrustKernel storage below:

```text
/mnt/vendor/protect_f/tee
```

Stock Android metadata encryption creates:

```text
/dev/block/mapper/userdata -> /dev/block/dm-57
```

and mounts that device as F2FS on `/data`.

This confirms that recovery FBE support must interoperate with the device TrustKernel/KeyMint backend rather than relying only on generic Keymaster compatibility libraries.
### TrustKernel startup details

Stock Android runtime additionally verifies:

```text
ro.vendor.mtk_trustkernel_tee_support=1
vendor.trustkernel.ready=true
vendor.trustkernel.fs.mode=3
vendor.trustkernel.fs.state=ready
```

For FBE (`ro.crypto.type=file`, `ro.crypto.state=encrypted`), `trustkernel.rc` selects TrustKernel filesystem mode 3.

The stock init definitions are:

```text
vendor.keymint-3-0-trustkernel
  /vendor/bin/hw/android.hardware.security.keymint@3.0-service.trustkernel
  class early_hal
  user/group system

vendor.gatekeeper
  /vendor/bin/hw/android.hardware.gatekeeper-service.trustkernel
  class hal
  user/group system

teed
  /vendor/bin/teed
  TEE device: /dev/tkcore_admin
  protected storage: /mnt/vendor/persist/t6 and /mnt/vendor/protect_f/tee
  prebuilt TA data: /vendor/app/t6/data
```

Android also runs `mtk_storageproxyd`; its stock init definition uses `/dev/trusty-ipc-dev1` and `/dev/0:0:0:49476`.

These details define the stock TrustKernel startup chain that recovery must reproduce before Keystore2 can use the hardware-backed KeyMint service.

### Recovery-visible TrustKernel prerequisites

Direct inspection from recovery with the stock vendor, persist, and protect1 partitions mounted confirmed:

```text
/vendor                      -> vendor_a (EROFS, read-only)
/mnt/vendor/persist          -> persist (ext4)
/mnt/vendor/protect_f        -> protect1 (ext4)

/dev/tkcore_admin            present
/dev/rpmb0                   present
/dev/teeperf                 present
/dev/0:0:0:49476             present
/dev/trusty-ipc-dev*         absent
/dev/gz_kree                 absent
```

The TrustKernel system TA directory `/vendor/app/t6` is present in stock vendor and contains the device TA payloads and configuration used by `teed`.

Verified stock executables:

```text
/vendor/bin/teed
/vendor/bin/mtk_storageproxyd
/vendor/bin/tee_check_keybox
/vendor/bin/hw/android.hardware.security.keymint@3.0-service.trustkernel
/vendor/bin/hw/android.hardware.gatekeeper-service.trustkernel
```

ELF inspection confirms that `teed`, the TrustKernel KeyMint service, and the TrustKernel Gatekeeper service all depend on `libteec.so`. The KeyMint service additionally depends on the AIDL KeyMint V3, RKP V3, SharedSecret V1, and SecureClock V1 NDK interfaces.

`mtk_storageproxyd` instead depends on `libisetrusty.so` and its stock command line targets `/dev/trusty-ipc-dev1`. No `trusty-ipc-dev*` node is present during recovery boot, so it is not currently treated as a prerequisite for the TrustKernel KeyMint bring-up path.

### Recovery security bring-up observations

Live recovery testing confirms that the stock TrustKernel KeyMint V3 executable can remain running and opens `/dev/binderfs/binder` plus `/dev/tkcore_client`; this does not yet prove successful AIDL service registration.

Manual stock `teed` startup exits with status `253`. The kernel repeatedly reports `teed not ready. id=0x1003` and failure to load TA `9ef77781-7bd5-4e39-965f20f6f211f400` with `0xffff0000`, even though the matching TA exists in `/vendor/app/t6`.

Recovery `keystore2` still crash-loops with `SIGABRT`; its PID changes across the nominal `running` state. During each startup, `servicemanager` also reports missing `/system/etc/vintf/manifest.xml` and a `NULL VINTF MANIFEST`.

These are confirmed recovery bring-up blockers; metadata-key unwrap and creation of `/dev/block/mapper/userdata` have not yet succeeded.

### Framework VINTF compatibility

Live recovery testing confirmed that the active Android 15 system framework VINTF manifest is available at `/system/etc/vintf/manifest.xml` when the system partition is mounted manually, but it declares manifest meta-version `9.0`.

The OrangeFox 14.1 recovery userspace currently contains `libvintf@8.0`. After copying the Android 15 VINTF tree into recovery, `servicemanager` changes from reporting a missing framework manifest to rejecting it with:

```text
Unrecognized manifest.version 9.0 (libvintf@8.0)
```

`keystore2` continues its SIGABRT restart loop, so directly importing the Android 15 framework VINTF tree is not compatible with the current recovery userspace. A recovery-compatible VINTF declaration or newer libvintf userspace is required for further KeyMint/Keystore2 bring-up testing.

### Minimal recovery VINTF test

A recovery-local framework VINTF manifest with meta-version `8.0` is accepted by the current recovery `libvintf@8.0`. With a minimal framework manifest and an `8.0`-inverted `android.system.keystore2` AIDL fragment, `servicemanager` reports:

```text
getFrameworkHalManifest: Successfully processed VINTF information
```

This confirms that the Android 15 meta-version `9.0` incompatibility can be avoided with a recovery-compatible minimal VINTF declaration. However, `keystore2` continues to restart with SIGABRT approximately every five seconds after VINTF parsing succeeds. Therefore, the VINTF meta-version mismatch is a real recovery compatibility issue, but it is not the remaining Keystore2 crash cause.

### Recovery property and process-profile differences

Live recovery inspection confirms the expected device identity properties are present:

```text
ro.board.platform=mt6878
ro.product.brand=Ulefone
ro.product.model=Armor 29 Pro Thermal
```

However, the stock-Android vendor support properties `ro.vendor.mtk_trustkernel_tee_support` and `ro.vendor.mtk_trustonic_tee_support` are unset in recovery.

The mounted Android system contains `/system/etc/task_profiles.json`, `/system/etc/cgroups.json`, and versioned task/cgroup profile files under `/system/etc/task_profiles/`. The recovery root currently lacks `/etc/task_profiles.json` while providing its own `/etc/cgroups.json`. This matches the observed recovery `logd` failures to load `/etc/task_profiles.json` and resolve profiles such as `NormalIoPriority`, `HighPerformance`, and `ServiceCapacityLow`; whether this is the direct cause of the `logd` abort remains under live validation.

### Recovery TEE device-node ownership and logging

Live recovery testing confirmed that the stock Android `task_profiles.json` is sufficient to keep recovery `logd` stable. After copying `/system/etc/task_profiles.json` from the mounted Android system into `/etc/task_profiles.json`, the same `logd` PID remained alive for at least 12 seconds and `logcat` became usable. Some newer task-profile actions/controllers remain unsupported by the recovery userspace, but they are non-fatal for logging.

With working `logcat`, manual stock `teed` startup exposed the immediate TrustKernel failure:

```text
TEED: error opening [/dev/tkcore_admin]: Permission denied(13)
```

The recovery-created TrustKernel device nodes are owned as `root:root`, including `/dev/tkcore_admin`, while stock Android exposes `/dev/tkcore_admin` as `system:system`. Stock `teed` is configured to run as `system:system` with `SYS_RAWIO`, so recovery must reproduce the stock device-node ownership/permissions before TrustKernel userspace can initialize. The current TA-load error and `teed not ready` state occur downstream of this failed `/dev/tkcore_admin` open.

### TrustKernel uevent rules and live `teed` behavior

The stock vendor uevent rules define the TrustKernel/RPMB nodes as:

```text
/dev/teeperf       0660 system system
/dev/tkcore_admin  0600 system system
/dev/tkcore_client 0660 root   system
/dev/tkcore_fp     0660 root   system
/dev/rpmb0         0660 root   system
```

The stock storage-proxy init path also changes `/dev/0:0:0:49476` owner to `system`.

A live recovery test changed only `/dev/tkcore_admin` to the stock `system:system 0600` ownership/mode. After that change, stock `teed` no longer exited immediately with status 253 and no longer logged `error opening [/dev/tkcore_admin]: Permission denied(13)`; it remained running in the foreground for more than six minutes until manually interrupted. This verifies that recovery device-node ownership was the first `teed` startup blocker. TrustKernel ready state and downstream KeyMint/Keystore2 operation still require separate validation.

### Live recovery security-stack milestone

A live OrangeFox recovery session confirmed the recovery splash deadlock can be removed without changing the kernel or DTB.

After restoring the stock TrustKernel device-node ownership/modes, `teed` stays alive and reports:

```text
vendor.trustkernel.log.state=ready
vendor.trustkernel.ready=true
```

The stock TrustKernel KeyMint V3 service then opens its TEE session successfully and registers the device AIDL services:

```text
android.hardware.security.keymint.IKeyMintDevice/default
android.hardware.security.secureclock.ISecureClock/default
android.hardware.security.sharedsecret.ISharedSecret/default
android.hardware.security.keymint.IRemotelyProvisionedComponent/default
```

With a recovery-compatible framework VINTF declaration and working `logd` task profiles, `keystore2` remains alive and reports `Successfully registered Keystore 2.0 service.` Recovery subsequently leaves its previous crypto wait and the OrangeFox UI becomes usable.

This does not yet mean userdata decryption works. The same session still has no `/dev/block/mapper/userdata`. TrustKernel reports the recovery environment/device as unverified, KeyMint commands fail with `0xffff000f`, Keystore2 reports `SECURE_HW_COMMUNICATION_FAILED`, and recovery logs `decryptWithKeystoreKey failed`. Thus the UI/splash blocker and userdata-decryption blocker are now proven to be separate stages.

### TrustKernel verification gate after successful bring-up

Live recovery testing confirmed that `teed` runs as UID/GID `system:system` with effective capability `SYS_RAWIO` (`CapEff=0x20000`), matching the stock service requirement.

With the stock TrustKernel device-node permissions restored, `teed` reaches:

```text
vendor.trustkernel.log.state=ready
vendor.trustkernel.ready=true
```

The TrustKernel KeyMint V3 service opens its TEE session successfully and registers KeyMint, SecureClock, SharedSecret, and RemotelyProvisionedComponent. `keystore2` remains on a stable PID and successfully registers `android.system.keystore2.IKeystoreService/default`, which removes the previous OrangeFox splash deadlock.

The remaining metadata-decryption failure is downstream of a TrustKernel secure-world verification gate. `tee_check_keybox` exits with status 1 and all of its KPH verification operations fail with `0xffff000f`; it sets the TrustKernel deployment-status properties to false. The kernel repeatedly reports:

```text
TrustKernel OS running on un-verified devices
```

KeyMint operations fail with the same `0xffff000f`, Keystore2 maps this to `SECURE_HW_COMMUNICATION_FAILED`, `decryptWithKeystoreKey` fails, and `/dev/block/mapper/userdata` is not created.

This verifies that the recovery UI/startup blocker is solved independently from userdata decryption. The current direct decryption blocker is TrustKernel refusing secure-world KeyMint/KPH commands after classifying the recovery environment/device as unverified.

### Android vs recovery TrustKernel verification comparison

A controlled comparison between the working Android boot and the live recovery security stack confirms that the TrustKernel RPMB diagnostic is not the userdata-decryption blocker. Both environments report:

```text
RPMB: RPMB size is 16777216 Bytes
RPMB: Reliable Write Sector Count is 64
Using provisioned key
Verify RPMB Key failed with 0x7
Truststore DEFAULT Setup ... Done
Load Secondary cert success
```

Despite the same RPMB verification error, Android continues with:

```text
VERIFY_STATE: 1 TRIAL_STATE: 1
```

while recovery previously reported:

```text
VERIFY_STATE: 2 TRIAL_STATE: 0
Device [Ulefone Armor 29 Pro Thermal mt6878] not verified
```

Android also runs `tee_check_keybox` as a oneshot service which exits with status 1, yet its TrustKernel deployment properties include `vendor.trustkernel.keybox.deployed=true`, `vendor.trustkernel.attestation_ids.deployed=true`, `vendor.trustkernel.rkp.uploaded=true`, and `vendor.trustkernel.productionline.state=ready`. Therefore the `tee_check_keybox` exit status by itself is not a fatal condition.

The working Android boot exposes `/dev/block/mapper/userdata -> /dev/block/dm-57` and mounts `/data` as F2FS, while recovery does not create the userdata mapper. The decisive TrustKernel divergence is therefore the secure-world verification state, not the shared RPMB diagnostic or the keybox-check process exit code.

The two environments also differ in boot and identity inputs. Recovery exposes `ro.boot.verifiedbootstate=orange`, `ro.boot.mode=recovery`, and `ro.product.model=Armor 29 Pro Thermal`, while the working Android boot exposes `ro.boot.verifiedbootstate=green`, `ro.boot.vbmeta.device_state=locked`, `ro.boot.flash.locked=1`, `ro.boot.veritymode=enforcing`, `ro.boot.mode=normal`, and `ro.product.model=Armor 29 Pro`. Further testing is required to determine which of these inputs drives TrustKernel from `VERIFY_STATE: 1` to `VERIFY_STATE: 2`.

### Recovery product-model source

The recovery product makefile `twrp_gq5012bf1.mk` explicitly defines:

```make
PRODUCT_MODEL := Armor 29 Pro Thermal
```

The working Android userspace reports `ro.product.model=Armor 29 Pro`, while the recovery runtime reports `ro.product.model=Armor 29 Pro Thermal`. A targeted source search found no other non-documentation `Armor 29 Pro Thermal` product-model definition in the device tree. The generated recovery `prop.default` and partition `build.prop` files do not contain a direct top-level `ro.product.model=` assignment, so the makefile product identity remains the controlled source-level variable to test. This does not yet prove that the model string alone determines TrustKernel verification state.

### Recovery product-model propagation

A controlled recovery build changed only the product identity from `PRODUCT_MODEL := Armor 29 Pro Thermal` to `PRODUCT_MODEL := Armor 29 Pro`.

The Android build system resolved `PRODUCT_MODEL=Armor 29 Pro` and regenerated all recovery/product partition model properties accordingly:

```text
ro.product.system.model=Armor 29 Pro
ro.product.vendor.model=Armor 29 Pro
ro.product.odm.model=Armor 29 Pro
ro.product.product.model=Armor 29 Pro
ro.product.system_ext.model=Armor 29 Pro
```

No generated `Armor 29 Pro Thermal` model value remained. This provides a clean build for testing whether TrustKernel verification depends on the product model while leaving the actual recovery/verified-boot state unchanged.

Hardware testing confirmed that the recovery product model must be `Armor 29 Pro`: with this identity TrustKernel reaches `VERIFY_STATE: 1 TRIAL_STATE: 1` even while recovery remains in the real `orange` verified-boot state.

### Build17 model-test recovery fragment

The controlled `Armor 29 Pro` model-test build produced a fresh vendor-boot recovery fragment:

```text
recovery.cpio.lz4: 33570655 bytes
SHA256: 0c89d1e82ff0155da3b2f4a76cd132d9ab53b8a89f2b097fa98d7e77e7d2e873
```

The generated vendor-boot image contains a 4-byte type-1 PLATFORM fragment and therefore is not suitable for flashing directly. Its type-2 `recovery` fragment is the Build17 recovery payload.

The generated DTB is 342395 bytes with SHA256 `bc156c29c33d8226230f07888df0a3d7a1e9c4b85c5fd550a4c4bd1a3134c0`, byte-identical to the previously verified stock DTB.

The full hardware-test image must therefore be reconstructed with the stock PLATFORM fragment, stock-identical DTB, and this fresh recovery fragment.

### Build17 full vendor_boot candidate

The Build17 model-test recovery was reconstructed into a full 67108864-byte vendor_boot image using the verified stock PLATFORM fragment and stock DTB.

```text
candidate: vendor_boot_a-orangefox-FULL64M-CANDIDATE-v6-model-test.img
SHA256: 15a840c4b62fc9f49866408b49253913a83db90a21e45e38d86a6cae71e8be1f
PLATFORM SHA256: 9201a4e5c1b7cb1fc0ce35375af10a3d966dac8b84615a226f98b7d7be2aec00
RECOVERY SHA256: 0c89d1e82ff0155da3b2f4a76cd132d9ab53b8a89f2b097fa98d7e77e7d2e873
DTB SHA256: bc156c29c33d8226230f07888df0a3d7a1e9c4b85c5fd550a4c4bd1a3134c0d4
```

Offline unpacking confirmed the PLATFORM fragment, Build17 recovery fragment, and DTB are each byte-identical to their intended inputs. The AVB hash footer uses partition name `vendor_boot` and the image occupies the exact 64 MiB partition size.

### Build17 hardware boot identity

The full Build17 model-test vendor_boot candidate was flashed to `vendor_boot_a` and fetched back byte-identically.

Build17 boots recovery far enough for stable ADB and reports:

```text
ro.product.brand=Ulefone
ro.product.model=Armor 29 Pro
ro.board.platform=mt6878
ro.boot.verifiedbootstate=orange
ro.boot.mode=recovery
ro.boot.slot_suffix=_a
```

OrangeFox initially remains on its splash screen because the previously proven recovery security-stack fixes are still live-only and have not yet been integrated into the ramdisk. This boot therefore provides the intended controlled TrustKernel experiment: the product model is changed to `Armor 29 Pro` while the recovery and orange verified-boot state remain unchanged.

### Build17 TrustKernel model verification result

Hardware testing confirmed the TrustKernel identity requirement. Build17 booted with:

```text
ro.product.brand=Ulefone
ro.product.model=Armor 29 Pro
ro.board.platform=mt6878
ro.boot.verifiedbootstate=orange
ro.boot.mode=recovery
```

After mounting the active vendor logical partition, restoring the verified stock TrustKernel device-node permissions, mounting persist/protect_f, and starting the stock `teed`, TrustKernel userinit reported:

```text
ARCH FEATURE = 0x22f1
Verify RPMB Key failed with 0x7
Truststore DEFAULT Setup ... Done
Load Secondary cert success
VERIFY_STATE: 1 TRIAL_STATE: 1
```

The same RPMB diagnostic occurs during working Android, so it is not the userdata-decryption blocker.

This controlled test proves that the previous `VERIFY_STATE: 2 TRIAL_STATE: 0` condition was caused by using `Armor 29 Pro Thermal` as the Android product model. The real recovery `orange` verified-boot state is compatible with TrustKernel verification state 1 on this device.

The retail/device documentation name remains Ulefone Armor 29 Pro Thermal, but recovery must expose the Android product model `Armor 29 Pro` for the TrustKernel security stack.

### Build17 verified KeyMint bring-up

After correcting the recovery Android product model to `Armor 29 Pro`, TrustKernel reaches `VERIFY_STATE: 1 TRIAL_STATE: 1` and the stock TrustKernel KeyMint V3 service progresses beyond the previous secure-world rejection.

Live Build17 testing confirms:

```text
KeyMintHAL: Open session successfully
KeyMint device is current version (Some(300)) for TRUSTED_ENVIRONMENT
Shared secret negotiation concluded successfully.
```

KeyMint registers its AIDL KeyMint, SecureClock, SharedSecret, and RemotelyProvisionedComponent interfaces. The previous `0xffff000f` unverified-device rejection is no longer present.

The current Keystore2 blocker is now framework VINTF registration: Keystore2 reaches service registration but servicemanager reports that `android.system.keystore2.IKeystoreService/default` is not present in the framework VINTF manifest, causing Keystore2 to abort and restart. No userdata mapper is created yet.

This proves that the TrustKernel verification failure and resulting secure-hardware communication failure have been resolved; framework VINTF declaration is now the immediate blocker.

### Build17 OrangeFox UI and metadata-key blocker

With TrustKernel verified, KeyMint running, logd stabilized, and the minimal framework VINTF reduced to the two required version-8.0 files, Keystore2 remains stable and registers successfully:

```text
getFrameworkHalManifest: Successfully processed VINTF information
Found android.system.keystore2.IKeystoreService/default in framework VINTF manifest.
Shared secret negotiation concluded successfully.
Successfully registered Keystore 2.0 service.
```

Starting Keystore2 at this point immediately allows OrangeFox to leave the splash screen and display its normal UI.

Userdata is still not decrypted. Recovery reads `/metadata/vold/metadata_encryption/key/keymaster_key_blob`, but the Keystore2 createOperation call now returns service-specific error `-33`; AOSP KeyMint defines `-33` as `INVALID_KEY_BLOB`. Recovery then reports `decryptWithKeystoreKey failed` and `read_key failed in mountFstab`, and no `/dev/block/mapper/userdata` is created.

This is progress beyond the previous `SECURE_HW_COMMUNICATION_FAILED` condition: the TrustKernel/KeyMint communication path and Keystore2 service are now operational, and the current blocker is acceptance of the existing metadata-encryption KeyMint blob.

### Build17 KeyMint REE version inputs

With TrustKernel verified and Keystore2 operational, metadata-key use reaches TrustKernel KeyMint but returns `INVALID_KEY_BLOB` (`-33`).

The live recovery property service reports:

```text
ro.build.version.release=14
ro.build.version.sdk=34
ro.build.version.security_patch=2024-09-05
ro.vendor.build.version.release=
ro.vendor.build.version.sdk=
ro.vendor.build.security_patch=
ro.bootimage.build.version.security_patch=
ro.product.first_api_level=
ro.vendor.api_level=34
```

The mounted vendor image itself contains:

```text
ro.vendor.build.version.release=14
ro.vendor.build.version.sdk=34
ro.vendor.build.security_patch=2025-09-05
ro.product.first_api_level=35
```

TrustKernel KeyMint startup reports `patchlevel string does not match expected format. Using patchlevel 0`, and secure world reports `WARNING: Unexpected os version from REE`. The subsequent metadata-key operation reaches KeyMint command 16 and returns `INVALID_KEY_BLOB`.

The metadata KeyMint blob is 565 bytes with SHA256 `1eac61edfe777d0c6fa2f2d4f62ec892b6a031b90cb7064e4d6581c0a944fbca`.

Late mounting `/vendor` does not by itself populate the missing vendor properties in the already-running recovery property service. Whether these missing/version-mismatched REE inputs cause `INVALID_KEY_BLOB` remains to be tested.

### TrustKernel KeyMint version-property inputs

Static inspection of the stock TrustKernel KeyMint V3 service confirms direct references to:

```text
ro.build.version.release
ro.build.version.security_patch
ro.vendor.build.security_patch
```

The active Android system mounted from `system_a` currently reports Android 16 / SDK 36 with `ro.build.version.security_patch=2026-06-01`, while the stock vendor image reports Android 14 / SDK 34 with `ro.vendor.build.security_patch=2025-09-05`.

Build17 recovery currently exposes Android 14 / SDK 34 with `ro.build.version.security_patch=2024-09-05`, while `ro.vendor.build.security_patch` is unset because `/vendor` is mounted after recovery property initialization.

This makes REE OS/security-patch identity a concrete candidate for the remaining metadata KeyMint `INVALID_KEY_BLOB` failure.

### Build17 vendor-SPL-only KeyMint test

A live controlled test populated only `ro.vendor.build.security_patch=2025-09-05`, matching the mounted stock vendor image, while keeping recovery at Android 14 with platform SPL `2024-09-05`.

TrustKernel KeyMint restarted successfully, but secure world continued to report `WARNING: Unexpected os version from REE`.

After restarting recovery, a fresh metadata-key operation was forced against the restarted KeyMint service. Setting only `ro.vendor.build.security_patch=2025-09-05` removed the KeyMint HAL warning that the patchlevel string was invalid and no longer caused patchlevel 0 to be used. Secure world still reported `WARNING: Unexpected os version from REE`, however, and the fresh metadata-key createOperation still returned `INVALID_KEY_BLOB` (`-33`). Therefore the missing vendor SPL was a real recovery defect but is not sufficient by itself to make the existing metadata KeyMint blob usable.

### Build17 Android-release KeyMint test

After the vendor SPL was corrected to `2025-09-05`, a second controlled test changed only `ro.build.version.release` from recovery Android 14 to the active-system value Android 16, while leaving `ro.build.version.security_patch=2024-09-05` unchanged.

The restarted TrustKernel KeyMint service opened successfully and the previous secure-world warning `Unexpected os version from REE` disappeared. This proves that the recovery Android release value was the source of that warning.

A fresh recovery startup then retried the metadata key against the same restarted KeyMint service. The operation still returned `INVALID_KEY_BLOB` (`-33`), followed by `decryptWithKeystoreKey failed` and `read_key failed in mountFstab`.

Thus both the missing vendor SPL and mismatched Android release are genuine recovery defects, but correcting them is still insufficient to use the existing metadata KeyMint blob. The remaining directly referenced version mismatch is the platform security patch level.

### Build17 metadata-encryption breakthrough

The final controlled KeyMint REE-version test changed only `ro.build.version.security_patch` from recovery value `2024-09-05` to the active Android value `2026-06-01`, after the previous tests had already established `ro.build.version.release=16` and `ro.vendor.build.security_patch=2025-09-05`.

The resulting KeyMint version tuple was:

```text
ro.build.version.release=16
ro.build.version.security_patch=2026-06-01
ro.vendor.build.security_patch=2025-09-05
```

TrustKernel KeyMint opened successfully without the previous invalid-patchlevel or unexpected-OS-version warnings. Keystore2 remained stable and registered successfully.

A fresh recovery startup then processed the existing metadata encryption key without the previous `INVALID_KEY_BLOB` (`-33`) failure. Recovery entered its key-upgrade path:

```text
Upgrading key: /metadata/vold/metadata_encryption/key/keymaster_key_blob
```

and created the decrypted userdata block mapping:

```text
/dev/block/mapper/userdata -> /dev/block/dm-15
```

This proves that, after correcting the vendor SPL and Android release inputs, the remaining platform security-patch mismatch was the decisive blocker preventing the existing metadata KeyMint blob from being accepted. The metadata-encryption device mapper is now created successfully. F2FS `/data` mounting and userspace FBE state still require separate verification.

### Build17 decrypted userdata mapper without /data mount

With the KeyMint REE version tuple matched to the active Android/vendor environment, recovery successfully creates the metadata-decrypted userdata mapper:

```text
/dev/block/mapper/userdata -> /dev/block/dm-15
dm name: userdata
```

`/data` is not yet mounted, so metadata-encryption success and F2FS mount success are now separate stages.

Before `fscrypt_mount_metadata_encrypted` creates the mapper, recovery probes the raw userdata backing device `/dev/block/sdc76` and receives F2FS magic mismatches. Those probes occur against the metadata-encrypted raw device; the decrypted mapper must be inspected separately.

The on-disk metadata KeyMint blob remains 565 bytes and retains SHA256 `1eac61edfe777d0c6fa2f2d4f62ec892b6a031b90cb7064e4d6581c0a944fbca`, so the logged `Upgrading key` path did not change the observed blob contents.

### Build17 validated decrypted userdata filesystem

The metadata-decrypted userdata mapper was validated independently of OrangeFox mount orchestration.

Raw userdata `/dev/block/sdc76` and decrypted `/dev/block/mapper/userdata` are both 500061667328 bytes. The raw metadata-encrypted device does not contain an F2FS superblock at offset 1024, while the decrypted mapper contains the expected little-endian F2FS magic:

```text
raw sdc76: 3c bb 74 be
mapper dm-15: 10 20 f5 f2
```

Mounting `/dev/block/mapper/userdata` read-only as F2FS succeeds, and the real userdata root is visible with expected Android directories including `data`, `media`, `system`, `user`, `user_de`, `system_ce`, `system_de`, `vendor_ce`, and `vendor_de`.

Kernel logs confirm F2FS successfully mounts `dm-15` and reports a valid checkpoint.

Therefore TrustKernel/KeyMint metadata-key handling and the metadata-encryption mapper are now proven correct. The remaining issue is that OrangeFox does not leave the mapped filesystem mounted at `/data`; subsequent mount orchestration and per-file FBE initialization must be diagnosed separately.

### Build17 /data mount blocked by BootControl HAL

After successfully creating the metadata-decrypted userdata mapper, OrangeFox logs `Mounting metadata-encrypted filesystem:/data` but does not complete the `/data` mount.

The full unfiltered startup sequence shows that immediately after this point recovery synchronously requests `android.hardware.boot.IBootControl/default`. Init starts the MediaTek recovery BootControl service `vendor.boot-default`, but its `hal_bootctl_default` SELinux domain remains enforcing and receives denials while accessing the recovery root filesystem and `/dev/block/sdc1`.

Servicemanager then repeatedly waits for `android.hardware.boot.IBootControl/default` once per second, while the recovery process remains blocked in `futex_wait_queue`.

The decrypted userdata mapper itself is independently proven valid and mountable as F2FS. Therefore the immediate automatic `/data` mount blocker is now the unavailable MediaTek BootControl AIDL service, not metadata encryption or F2FS validity.

### Build17 BootControl SELinux causality proof

The BootControl mount blocker was confirmed experimentally.

With SELinux enforcing, `vendor.boot-default` ran in `u:r:hal_bootctl_default:s0` but hit enforcing AVC denials while accessing the recovery root filesystem and `/dev/block/sdc1` (`misc`). Recovery remained blocked in `futex_wait_queue`, and `/data` was not mounted.

Without restarting recovery, SELinux was temporarily changed to permissive and only `vendor.boot-default` was restarted. The same recovery process immediately left its wait and completed the metadata-encrypted userdata mount:

```text
/dev/block/dm-15 on /data type f2fs (rw,...,inlinecrypt,...)
```

Recovery then traversed the real device-encrypted userdata tree.

This proves that the remaining automatic `/data` mount blocker is SELinux policy/context for the MediaTek recovery BootControl HAL. Global permissive mode is diagnostic only and is not an acceptable permanent solution.

### Build17 BootControl misc-device labeling proof

The physical `misc` partition is `/dev/block/sdc1`, with `/dev/block/by-name/misc` pointing to it. Recovery originally labels both as generic `u:object_r:block_device:s0`.

The SELinux policy contains the standard `misc_block_device` type. In a live test, `/dev/block/sdc1` was relabeled to `u:object_r:misc_block_device:s0`, SELinux was returned to enforcing, and only `vendor.boot-default` was restarted.

After this relabel, the restarted `hal_bootctl_default` process no longer produced the repeated generic `block_device` AVCs for `/dev/block/sdc1`. This confirms that the physical misc block node must receive the `misc_block_device` label in recovery.

One enforcing denial remains for `hal_bootctl_default` reading the recovery rootfs `/bin` directory. BootControl interface registration under this remaining denial still requires explicit verification before adding policy.

### Build17 BootControl enforcing verification

After relabeling physical misc `/dev/block/sdc1` to `u:object_r:misc_block_device:s0`, the MediaTek recovery BootControl HAL was verified fully functional with SELinux enforcing.

The restarted HAL remained in `u:r:hal_bootctl_default:s0`, blocked normally in `binder_thread_read`, registered `android.hardware.boot.IBootControl/default`, and logged `IBootControl AIDL service running...`.

The recovery `bootctl get-current-slot` client returned slot `0` with exit status 0.

The remaining AVC for `hal_bootctl_default` reading the recovery rootfs `/bin` directory is nonfatal and does not prevent BootControl registration or operation. No broad rootfs allow should be added for this diagnostic denial.

Therefore the required permanent BootControl SELinux fix is to label the physical misc block node `/dev/block/sdc1` as `misc_block_device` in recovery.

### Build17 misc physical-node policy source

The mounted stock vendor SELinux `vendor_file_contexts` already labels `/dev/block/by-name/misc` as `misc_block_device`, but contains no rule for the physical recovery node `/dev/block/sdc1`.

Because the MediaTek BootControl HAL dereferences the by-name symlink and accesses `/dev/block/sdc1`, SELinux evaluates the physical inode context. This explains why the by-name rule alone was insufficient and why live relabeling of `/dev/block/sdc1` fixed BootControl under enforcing SELinux.

The eventual recovery policy must therefore add a physical-node file-context rule for `/dev/block/sdc1`; no additional BootControl block-device allow rule is required because `hal_bootctl_default` already has read/write access to `misc_block_device`.

### Build17 FBE DE/CE split and Gatekeeper blocker

After metadata encryption succeeds, `/dev/block/dm-15` is mounted read-write at `/data` with inlinecrypt.

Device-encrypted user 0 data is readable: `/data/system_de/0` exposes normal plaintext filenames including `accounts_de.db` and `persisted_taskIds.txt`.

Credential-encrypted paths remain locked. `/data/system_ce/0` and `/data/media/0` expose fscrypt ciphertext filenames rather than their normal names.

At this stage recovery continuously waits for `android.hardware.gatekeeper.IGatekeeper/default`. Servicemanager attempts to start the AIDL interface once per second, but init reports that no corresponding interface service is known.

Therefore metadata encryption and DE fscrypt are operational, while user 0 CE decryption is now blocked on Gatekeeper / credential handling.

### Build17 full user-0 FBE decryption breakthrough

Starting the stock TrustKernel Gatekeeper service completed the remaining credential-encrypted storage path.

The manually launched `/vendor/bin/hw/android.hardware.gatekeeper-service.trustkernel` opened its TrustKernel TEE session, registered `android.hardware.gatekeeper.IGatekeeper/default`, and successfully verified the existing user credential.

Recovery then immediately continued with:

```text
fscrypt_unlock_ce_storage 0
Trying user CE key /data/misc/vold/user_keys/ce/0/current
Installed fscrypt key ... to /data
Installed CE key for user 0
fscrypt_prepare_user_storage for volume null, user 0, flags 2
```

After CE-key installation, `/data/system_ce/0` exposes normal filenames such as `accounts_ce.db`, and `/data/media/0` exposes normal internal-storage contents including `DCIM`, `Download`, `Documents`, and other user files. OrangeFox can browse the decrypted files directly.

This proves end-to-end user-0 FBE recovery on hardware: TrustKernel verification, KeyMint metadata-key handling, dm-default-key metadata decryption, F2FS `/data` mounting, device-encrypted storage, Gatekeeper credential verification, and credential-encrypted fscrypt key installation all function successfully.

The remaining work is persistence: the currently live-only vendor mounts, TrustKernel services, version properties, VINTF setup, task profiles, device-node permissions/labels, and Gatekeeper startup must be integrated into the recovery image and verified from a cold boot.

### Build17 verified successful live FBE state

The successful live recovery state was captured after full user-0 FBE decryption.

Active security services were TrustKernel `teed`, TrustKernel KeyMint, TrustKernel Gatekeeper, Keystore2, and the MediaTek recovery BootControl HAL.

The KeyMint REE version inputs were `ro.build.version.release=16`, `ro.build.version.security_patch=2026-06-01`, and `ro.vendor.build.security_patch=2025-09-05`.

TrustKernel reported `vendor.trustkernel.ready=true`, filesystem state `ready`, and log state `ready`.

`/vendor` was mounted read-only from `dm-10`; `/mnt/vendor/persist` and `/mnt/vendor/protect_f` were mounted read-write; decrypted userdata `dm-15` was mounted read-write at `/data` with inlinecrypt.

The working device permissions included stock TrustKernel ownership for `/dev/tkcore_admin`, `/dev/tkcore_client`, `/dev/teeperf`, and `/dev/rpmb0`. Physical misc `/dev/block/sdc1` was relabeled `misc_block_device`.

The working recovery VINTF framework consisted of only the minimal framework manifest and Android system Keystore2 fragment. `/etc/task_profiles.json` was present as a 15069-byte mode-0644 root-owned file.

At this point `/data/system_de/0`, `/data/system_ce/0`, and `/data/media/0` were all decrypted and OrangeFox could browse the real user files.

### Build17 active-system KeyMint version source

The successful recovery session uses slot `_a`. Dynamic partition `system_a` is mapped as `/dev/block/mapper/system_a -> /dev/block/dm-4` and is mounted read-only at `/mnt/system_a`.

The active Android build properties required by TrustKernel KeyMint are available directly from `/mnt/system_a/system/build.prop`:

```text
ro.build.version.release=16
ro.build.version.security_patch=2026-06-01
```

The vendor-side input is available from mounted `/vendor/build.prop`:

```text
ro.vendor.build.security_patch=2025-09-05
ro.product.first_api_level=35
```

Therefore recovery can derive the KeyMint REE-version tuple dynamically from the currently active Android system and vendor images instead of hardcoding the current Android 16 release or security patch level.

<!-- DT-SECURITY-STACK-END -->
