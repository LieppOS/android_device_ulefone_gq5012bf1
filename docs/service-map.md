# Init and service map

`tools/inventory_device.py` parsed 263 init services. It found 113 distinct
present vendor/odm executable paths and 13 references whose payload is absent
from the stock image (factory-mode or alternate-BOM paths such as unused
fingerprint/gralloc variants). Generated `init.json` retains each command,
class, user/group, capabilities, seclabel, interfaces and triggers.

## VERIFIED critical ordering

Recovery security ordering remains:

1. `teed` starts after stock identity/mount preparation;
2. KeyMint starts after TrustKernel readiness;
3. Gatekeeper starts only after KeyMint is running;
4. Keystore2 starts after Gatekeeper.

This serialization, not a long `/data` timeout, is the hardware-verified FBE
path. `gq5012bf1-tee-storage` may stage `/data` storage opportunistically but
must never gate recovery boot.

## Stock full-ROM service families

The inventory accounts for camera, audio, sensors, graphics, thermal, power,
health, radio/IMS, connectivity, NFC, TrustKernel security, fingerprint, USB,
media/DRM and vendor diagnostics. Service RC files are extraction candidates;
they are not copied into the device tree blindly.

## Current gap

The initial full product can generate a vendor repository from the extraction
recipe, but service-by-service SELinux and framework compatibility must be
validated in a complete LieppOS source checkout.
