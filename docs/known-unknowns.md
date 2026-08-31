# Known unknowns and required validation

## Reduced by current evidence

The new evidence identifies the main panel driver, four normal camera sensors,
physical sensor ICs, NFC controller, fingerprint transport/module, secondary
fuel gauge, charge pumps, rear-display components and ThermoVue application/
native stack.

## Still UNKNOWN

- Maintainable matching kernel source and vendor-module rebuild path.
- Exact rear-display ioctl protocol and full suspend/notification behavior.
- Fingerprint enrollment/authentication and TrustKernel TA relationship under
  the full ROM (the current live custom environment did not expose a working
  framework fingerprint service).
- Exact external speaker-amplifier IC and complete audio calibration topology.
- Exact 120 W protocol/state machine, cell wiring and reverse-charge ABI.
- Night-vision sensor/illumination mapping by real capture test.
- Thermal sensor device-node transition sequence and ownership of any
  device-unique calibration beyond APK assets.
- Work-light, AW2013 RGB and red/blue warning-light control ABI.
- Complete modem/IMS compatibility and NV/calibration ownership map.
- Production AVB signing and full OTA/snapshot-merge validation.
- Build compatibility with the final LieppOS branch and vendor baseline. The
  current OrangeFox Android 14 checkout parses the full product and completes
  `m nothing`, but `vendorimage` stops in host ART because this checkout lacks
  `libvixld`; that is a source-checkout dependency, not a device blob failure.

## Offline vs hardware-tested

All new full-ROM tree work in this session is offline/static. Existing OrangeFox
boot, enforcing TrustKernel FBE decrypt, ADB, fastbootd, main display/touch and
battery fixes retain their earlier hardware evidence. No new full-ROM hardware
functionality is claimed.
