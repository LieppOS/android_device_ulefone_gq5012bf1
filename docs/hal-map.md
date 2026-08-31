# HAL and VINTF map

The generated inventory found 55 stock vendor/odm manifest documents and 192
HAL records in manifest-class XML (734 records when framework/device matrices
are included). Machine-readable details are in generated `vintf.json`.

## VERIFIED high-value interfaces

- Camera provider: AIDL `ICameraProvider/internal/0`.
- Graphics composer/allocator/mapper and MediaTek display services.
- Audio core/effects and sound-trigger services.
- Sensors multihal.
- Thermal AIDL default (MediaTek), power and health services.
- BootControl AIDL default.
- USB and USB gadget AIDL defaults.
- NFC AIDL default and secure-element SIM1/SIM2.
- GNSS AIDL default and MediaTek LBS interfaces.
- Bluetooth HCI and audio provider services.
- Radio AIDL family plus MediaTek radio extensions.
- TrustKernel KeyMint, secure clock, shared secret, remotely provisioned
  component and Gatekeeper.
- Fingerprint manifest/service artifacts and Microarray implementation library.
- DRM/CAS, media codec and neural-network services.

## Accounting policy

`proprietary-files.txt` starts from every vendor/odm manifest and hardware init
root, then adds in-stock ELF `DT_NEEDED` closure. This preserves dependency
recipes without asserting that every blob is redistributable.

## UNKNOWN

A declared/listed interface is not yet a satisfied full-ROM interface. Build-
time VINTF checks, service registration, enforcing SELinux and functional tests
must all pass before moving any subsystem from accounted to working.
