# IMS (VoLTE / VoNR)

Tested on the phone (Android 17, LieppOS slot B, SELinux enforcing, both SIMs:
Bite LT 246-02 / carrier id 893 and Telia LT 246-01 / carrier id 892):
IMS registers over LTE on both SIMs, calls go over IMS (`type:ims`), and the
VoNR switch works in both directions. An actual VoNR call needs 5G SA coverage
and has not been observed yet (the phone was camped on LTE during testing).

## Why not the stock ImsService

The stock `com.mediatek.ims` (vendor blob, versionCode 35) references 24 classes
from the `mediatek-*` framework jars (`mediatek-ims-base`, `mediatek-common`, ...),
which this AOSP system does not ship on the boot classpath. The vendor makefile's
`ImsService` module is therefore overridden.

## What is used instead

| Piece | Where | Why |
|---|---|---|
| `prebuilt/ImsService.apk` | `/system_ext/priv-app` | community unified MediaTek ImsService (needs only AOSP telephony) + `classes2.dex` with a no-op `TelephonyMetrics` (class removed in Android 17; it was the only unresolved class). Platform-signed (shared uid `android.uid.phone`). Rebuild: `stub/build-imsservice.sh` |
| `permissions/privapp-permissions-com.mediatek.ims.xml` | `/system_ext/etc/permissions` | 7 signature\|privileged permissions it requests |
| `../sepolicy/system_ext/private/service_contexts` | | `imsa mtkIms GbaService mwis wfo` -> `radio_service` (same as stock). Without `mwis` the service dies with "SELinux denied for service" |
| `overlays/framework` | `config_device_volte_available=true` | |
| `overlays/phone` | `config_ims_mmtel_package=com.mediatek.ims` | default MMTEL ImsService, bound automatically |
| `overlays/carrierconfig` (`res/xml/vendor.xml`) | `carrier_volte_available_bool=true` globally; `vonr_enabled_bool` + `vonr_setting_visibility_bool` for carrier ids 892/893 | no AOSP carrier file exists for these carriers. (mcc/mnc filters did not match on this phone; carrier-id filters do.) |
| `persist.vendor.mtk_dynamic_ims_switch=0` (device.mk) | product build.prop | see below |

No `persist.dbg.*_avail_ovr` debug overrides are needed.

## The MediaTek RIL VoNR gate

`libmtk-ril.so` `RtcImsConfigController::setVoNREnable` writes the per-SIM bit in
`persist.vendor.mtk.vonr.enable` (bitmask: bit0 = slot 0, bit1 = slot 1), then
`triggerImsCfgCommand` recomputes it. With `persist.vendor.mtk_dynamic_ims_switch=1`
(vendor default) the result comes from a per-carrier capability table that the
stock MediaTek IMS framework fills; the AOSP-side ImsService never reports VoNR
capability, so every enable is ANDed back to 0 ("can be switched off, never on").
With the switch at 0 the RIL uses the per-SIM bits Android sets.

Note: CarrierConfig results are cached per carrier in
`/data/user_de/0/com.android.phone/files/carrierconfig-*.xml` keyed only by the
CarrierConfig version; after changing the overlay on an existing install, delete
those files (or change SIM) to pick it up.

## Not enabled

- Wi-Fi calling: no `wfca`/ePDG daemon in the vendor partition.
- Video calling (ViLTE): not tested; left off.
