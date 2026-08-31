# Hardware map

| Subsystem | Evidence | Status |
|---|---|---|
| SoC | MediaTek MT6878, arm64, UFS | VERIFIED |
| Main panel | Kernel log identifies `yft-lcm-vtdr6115-drv`; 1080×2400, 60/90/120 Hz exposed | VERIFIED |
| Main touch | FocalTech FT3680, SPI3, `fts_ts`, 1080×2400, 10 slots | VERIFIED |
| Rear display | SPI `spi_tiny_lcd_co5300`; stock Android exposes only the main display through HWC/DRM | VERIFIED facts; userspace architecture STRONG INFERENCE |
| Rear touch | Hynitron `hyn_ts`, I2C 0-0015, 340×340, one tracking ID | VERIFIED |
| Fingerprint | SPI1 `madev`, `microarray_fp_tee`, `/dev/madev0`, `/dev/tkcore_fp` | VERIFIED transport; full authentication UNKNOWN |
| NFC | ST21NFC at I2C 6-0008, AIDL NFC service, ST firmware | VERIFIED |
| Sensors | ICM4N607 accel/gyro, MMC5603 mag, STK3A5X ALS/prox, SPL07 pressure | VERIFIED |
| Fuel gauges | MT6375 primary Android battery path; SH366003 secondary `3rd-gauge` | VERIFIED |
| Charge pumps | SC8571 at I2C 11-0066 and 6-0067; SC851x at 6-0069 | VERIFIED binding |
| Cameras | IMX989, S5KJN1, S5KJN1MAIN2, OV64B | VERIFIED enumeration |
| Thermal camera | ThermoVue Pro AC020 userspace with UVC/USB native stack and bundled calibration; `yft_tiny2c_usb` mode path | VERIFIED components; end-to-end ROM integration not tested |
| Audio | MT6369 headset jack and external `speaker_amp` at I2C 6-0034 | VERIFIED; exact amp IC UNKNOWN |
| Notification RGB | AW2013 at I2C 11-0045 | VERIFIED binding |
| Work/warning lights | Stock `YftOutdoorLightUlefone` and `YftRedBlueLight` apps | VERIFIED userspace artifacts; control ABI UNKNOWN |
| Physical action keys | `yft-gpio-keys` emits F1/F2 | VERIFIED |
| USB | configfs, UDC `11201000.usb0` | VERIFIED |

The detailed subsystem reports identify dependencies and remaining tests.
