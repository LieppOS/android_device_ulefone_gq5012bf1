# Main and secondary display

## Main display — VERIFIED

- DSI/DRM connector: `card0-DSI-1`.
- Kernel probe/runtime log identifies `yft-lcm-vtdr6115-drv`.
- SurfaceFlinger reports one HWC display, physical ID
  `4627039422300187648`, 1080×2400, density 480.
- Exposed refresh rates are 60, 90 and 120 Hz.
- Main touch is FocalTech FT3680 on SPI3.

## Rear display — VERIFIED components

- SPI0 binds `spi_tiny_lcd_co5300` from `spi_tiny_co5300_lcd.ko`.
- `/sys/class/misc/tiny_lcd_miscdev` exists.
- Hynitron `hyn_ts` binds at I2C 0-0015 and exposes 340×340 coordinates with
  one touch tracking ID.
- Stock system contains `YftMiniScreen.apk` (about 84 MB) and several YFT watch-
  face/theme packages.

## STRONG INFERENCE

The rear panel is not exposed as a second SurfaceFlinger/HWC display in the
captured state: only the main physical display appears. The CO5300 misc device,
YFT mini-screen application and Hynitron touch path therefore form a vendor-
managed auxiliary framebuffer/control architecture rather than a normal DRM
secondary display.

## UNKNOWN

- Exact ioctl/sysfs protocol between `YftMiniScreen` and `tiny_lcd_miscdev`.
- Touch routing/gesture ownership while the main display sleeps.
- Suspend, AOD/watch-face and notification update behavior under LieppOS.
