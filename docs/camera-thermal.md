# Camera, night vision and ThermoVue

## Android camera stack — VERIFIED

Stock camera provider is AIDL `android.hardware.camera.provider.ICameraProvider/internal/0`.
`camerahalserver` enumerated four public physical/virtual camera IDs:

| ID | Facing | Sensor driver | Flash |
|---:|---|---|---|
| 0 | Back | `SENSOR_DRVNAME_IMX989_MIPI_RAW` | yes |
| 1 | Front | `SENSOR_DRVNAME_S5KJN1_MIPI_RAW` | no |
| 2 | Back | `SENSOR_DRVNAME_S5KJN1MAIN2_MIPI_RAW` | yes |
| 3 | Back | `SENSOR_DRVNAME_OV64B_MIPI_RAW` | yes |

The stock snapshot also proves four `imgsensor` I2C bindings, EEPROM devices,
VCM/OIS devices and AW36515/AW36518-family illumination drivers. Which rear
sensor is marketed as night vision requires a functional capture/illumination
test; sensor enumeration alone is not enough.

## ThermoVue — VERIFIED components

- Stock APK: `system/app/M170infisens/M170infisens.apk`.
- Package/label: `com.energy.tc2c`, **ThermoVue Pro**.
- Launch activity: `com.energy.usbCamera.ui.splash.SplashActivity`.
- Native stack includes AC020, UVC/USB, IR camera/command, image processing,
  dual calibration and temperature libraries for arm64 and arm32.
- The APK embeds 17 calibration assets, including high/low B, K, KT/BT, NUC,
  OOC, RMVC and private data sets.
- Kernel side binds `tiny2c_usb-sensor` at I2C 8-003c through
  `yft_tiny2c_usb`; live sysfs exposes `tiny2c_usb_mode`/`tiny2c_mode`.

## STRONG INFERENCE

The thermal sensor is presented to ThermoVue through its private AC020/UVC
native stack, with YFT tiny2c controlling USB/sensor mode. It is separate from
the four normal Camera2 devices.

## UNKNOWN / required tests

- Exact device node and mode-transition sequence used by the APK.
- Whether calibration assets are generic to this module or complemented by
  device-unique persistent calibration. Never package unique calibration.
- Preview, radiometry, measurement accuracy, recording and suspend/resume under
  LieppOS remain hardware tests.
