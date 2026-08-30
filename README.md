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
