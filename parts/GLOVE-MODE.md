# Main-screen glove sensitivity

ArmorParts provides **Settings > Display > Glove sensitivity** and an optional
**Glove sensitivity** Quick Settings tile (add it through the tile editor).

The only device interface used is the main FT3680's existing
`/sys/bus/spi/devices/spi3.0/fts_glove_mode`. The stock vendor init permissions
and `sysfs_yft_file` policy already allow the existing system application to
access it. No new permission, root helper, kernel/firmware update, init trigger
or SELinux relaxation is required.

- Installing/updating the app does not enable the feature. With no saved choice,
  startup does not write the controller at all.
- A user change writes only `1` or `0` and verifies the driver's accepted mode.
  Register0xC0 is diagnostic: on this unit it read1 immediately after enable,
  then0 within about half a second while the driver remained On; the owner
  confirmed glove touch works. Do not use that register as a steady-state mode
  indicator or label the cached driver flag as independent firmware proof.
  Failed changes attempt to restore the previous driver-reported state.
  Missing/ambiguous status is displayed as unavailable, not Off.
- The choice is saved in device-protected app preferences only after successful
  verification. A preference-save failure also attempts hardware rollback.
- The persistent application's startup restores an explicitly saved choice,
  with at most five attempts while the controller becomes available. A later
  user choice takes precedence over a pending restore retry.
- All I/O is serialized off the main thread. The optional tile requires unlock
  before changing sensitivity. Neither component accepts command intents to
  change the hardware.
- More sensitivity can cause unwanted touches. Turn it off when gloves are not
  needed. Firmware readback is not proof that any particular glove works.
- Never walk sysfs to discover alternatives: the rear Hynitron gesture-status
  node is unsafe to read on this device. This control never accesses rear touch.

## Host contract tests

From the device repository, choose a disposable output directory outside source
Git and run under the workspace's required NUMA binding:

```sh
numactl --physcpubind=0-7,16-23,32-39,48-55 --membind=0 -- \
  javac -d "$TEST_OUT" \
  parts/src/org/lieppos/armorparts/GloveModeNode.java \
  parts/tests/GloveModeNodeTest.java
numactl --physcpubind=0-7,16-23,32-39,48-55 --membind=0 -- \
  java -cp "$TEST_OUT" org.lieppos.armorparts.GloveModeNodeTest
```

The fake transport in these tests exercises parsing, idempotence, failed writes,
readback mismatch/loss and rollback/error retention. It is not a hardware test.
Build the real `ArmorPartsGq5012bf1` Android target as well.

## Device validation (separate owner approval)

Preserve the installed APK and its public signing identity before updating it.
Use a matching platform-signed build and keep app data. ArmorParts is persistent,
so Android rejects ordinary APK updates. Use PackageInstaller's supported staged
update path only with separate approval for the apply reboot (and rollback if
needed); do not weaken the persistent-app/signature checks. Inspect other pending
staged sessions before rebooting. Do not touch firmware, change slots, flash
partition images or clear app data.

With permission, open the Display entry and verify Off, toggle On and require
`Glove Mode:On`, then wait beyond half a second and check that the UI still
reports the driver's On state even if register0xC0 reads0. Toggle Off and require
`Glove Mode:Off`. Check process-restart persistence separately from actual reboot
persistence; a persistent process may immediately restart after force-stop.
Leave the original mode restored. Confirm the optional tile's manifest and real
state handling; do not silently add tiles or rearrange the owner's Quick Settings.
Finally the owner should try their actual gloves and check false touches.

Record build, UI, register-toggle, process-restart and real-glove results
separately. A source/build pass must not be described as glove usability or
reboot-persistence validation.

## Validation snapshot (2026-11-19)

- All37 host contract checks pass, and the real Android APK target builds.
- The installed matching-signed correction's APK hash matches the built artifact.
  The supported staged update was already applied at reconnection; no additional
  agent reboot was needed for final validation.
- Live UI Off → On → Off passes. With driver On and diagnostic register0, the
  corrected switch remains enabled and checked On rather than falsely unavailable.
- The saved On choice survives a verified exact-application process restart.
  Final UI, driver and saved choice are Off. Other application preferences were
  preserved. Saved-On restoration across an actual reboot was not tested.
- The owner reports actual glove touch works. Glove-material compatibility and
  quantitative false-touch/error rates were not measured.
- The optional QS tile compiles and uses the same controller manager; interactive
  tile behavior was not separately exercised, and the owner's tiles were not
  added or rearranged.
