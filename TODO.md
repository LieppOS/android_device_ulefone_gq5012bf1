# GQ5012BF1 OrangeFox — outstanding work

Status as of Build36, commit `7976adc`.

Everything listed here is **unverified**, not known-broken. Nothing in this file
should be described as working until it has been exercised on hardware.

---

## 1. Untested features

Quick to check, low risk. Each needs only a few minutes with the device.

- [ ] **USB OTG** — no OTG adapter or storage was ever attached. `/dev/block/sda`
      and `sdb` exist but are UFS LUNs, not OTG. The fstab already has wildcard
      `voldmanaged=usbotg` entries for the xhci controllers, which is where
      `/auto1` to `/auto3` come from. Attach a stick, confirm it is detected,
      mounted, browsable, and can round-trip a harmless file.
- [ ] **ADB sideload** — the transport and command path were never exercised.
      Verify `adb sideload` connects and transfers. Do not flash an arbitrary
      package to test it.
- [ ] **Brightness slider** — the node works
      (`/sys/class/leds/lcd-backlight/brightness`, currently 1024 of max 2047),
      but the UI slider was never moved. Check the minimum does not black the
      screen out permanently.
- [ ] **Screenshot** — never triggered. Check the binding works and where the
      file lands.

Higher risk. Get explicit agreement before attempting.

- [ ] **Restore** — never run. Only test against a small target with trivial
      rollback. A backup of `boot` exists as a known-good source: backup itself
      is verified working (64 MB, digest generated, 2 s).
- [ ] **Reboot targets** — only Recovery and Fastbootd are exercised. System,
      Bootloader and Power off are untested. Low risk individually, but each
      ends the debugging session.

## 2. Never in scope, entirely untested

These were never part of the bring-up and must not be assumed functional:

- [ ] Zip / package flashing
- [ ] Magisk installation
- [ ] Backup and restore of a decrypted `/data`
- [ ] Theming engine
- [ ] Wipe and format menus — mappings were audited, but nothing was formatted.
      `/data` was deliberately never formatted as an acceptance test.

---

## 3. Known defects

### 3.1 USB drops for ~40 s after the PIN is entered

Adding a FunctionFS function to a live gadget requires unbinding and rebinding
the UDC, so the host re-enumerates and ADB reconnects.
`gq5012bf1-mtp-bind.sh` itself takes 0.149 s; the remainder is host-side.

This is inherent to composing MTP at runtime. MTP cannot start before `/data`
is decrypted, because TWRP's MTP storage is `/data/media/0`. The only way to
avoid the rebind is to compose both functions before the gadget is first bound,
which would withhold ADB until the PIN is entered — a worse trade.

Possible improvement, unproven: have the bind script wait for the gadget to
settle, or find whatever re-asserts `idProduct` and cooperate with it rather
than rebinding blind.

### 3.2 Cosmetic `/auto0` mount error at login

`recovery/root/system/etc/recovery.fstab:56` uses a wildcard `voldmanaged`
entry that expands to both the raw SD disk `mmcblk0`, which carries a partition
table rather than a filesystem, and `mmcblk0p1`, which mounts correctly as
`/auto0-1`. Mounting the raw disk returns `EOVERFLOW`, surfaced by the GUI as a
value-too-large error.

Pre-existing and harmless: `operation_end - status=0`, and the SD card works.
MTP only made it visible because it enumerates every storage entry. Lines 58-60
do the same for OTG.

Deliberately left alone — the fix touches the fstab that also governs
first-stage mounting and FBE. If it is ever addressed, the low-risk option is a
separate `twrp.fstab` with explicit storage entries, which then needs a full
decrypt retest.

### 3.3 Post-install vibration does not fire

`bootable/recovery/data.cpp:1761` writes a duration value to
`/sys/class/timed_output/vibrator/enable`, which does not exist on this device.

Left as is on purpose. This device's vibrator is a brightness node with no
auto-stop, so writing a duration would set the brightness to that number and
vibrate continuously. Failing harmlessly is better. UI haptics are unaffected
and work via the `minuitwrp/events.cpp` patch.

A proper fix would route this through the same timed helper used by `vibrate()`.

### 3.4 Two benign enforcing denials

```text
u:r:hal_health_default:s0 -> u:object_r:rootfs:s0 [dir]
u:r:hal_bootctl_default:s0 -> u:object_r:rootfs:s0 [dir]
```

Both HALs function correctly. Granting `rootfs` directory read was rejected as
too broad for no functional benefit. Only worth revisiting if a real failure is
ever traced to them.

---

## 4. Build environment hazards

- [x] **The former `PRODUCT_SHIPPING_API_LEVEL := 35` recovery-build conflict
  is resolved.** The production device tree no longer sets that value and
  Build36 compiled successfully. If parallel ROM work adds it again, keep it
  outside recovery products with the same `twrp_%` guard used around
  `BoardConfigRom.mk`.

- **`.work/` must stay pruned from soong.** Inventory tooling clones
  `erofs-utils` there. The path is gitignored, but soong does not read
  `.gitignore` and scans every directory for `Android.bp`, aborting the build
  with `module ... already defined`. `vendorsetup.sh` now drops a
  `.find-ignore` marker automatically; recreate it if the tooling removes it.

---

## 5. Open questions

- **What re-asserts `idProduct`?** Writing `0x4ee2` succeeds and reads back
  correctly immediately after rebinding, then reverts to `0xd001` unprompted.
  Something outside recovery owns USB identity. The same actor recomposed the
  gadget when `sys.usb.config` was written, which is why that property must not
  be touched here. Finding it would explain both behaviours.

- **Is the Gatekeeper/KeyMint settle time tunable?** Gatekeeper is started five
  seconds after KeyMint reports running. Serialising the two trusted-application
  sessions is what fixes decryption; the *length* of the delay is empirical, not
  derived. The minimum safe value has not been characterised, and every probe
  costs a flash plus a manual PIN entry.

- **MTP is post-PIN only.** TWRP starts the MTP server once its persisted
  settings load and storage exists, and its storage is `/data/media/0`. Whether
  pre-decrypt MTP against the SD card is worth exposing has not been explored.
