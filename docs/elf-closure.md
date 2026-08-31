# Proprietary ELF dependency closure

Final offline classification for the 90 concrete paths originally emitted by
`MISSING_BLOBS_DT-ELF-001.txt`. The stale one-shot list is superseded by this
report and by the reproducible gate in `tools/elf_closure.py`.

## Result

```text
original proprietary inventory:                  1814 paths
original AOSP replacement overlay:                198 paths
original concrete candidate paths:                 90
  REQUIRED_STOCK_BLOB:                             47
  UNUSED_PARENT_BLOB (added conservatively):       23
  AOSP_OR_ROM_PROVIDED:                            14
  ALTERNATE_BOM_OR_FACTORY_ONLY (excluded):         6
  SHIM_OR_FIXUP_REQUIRED:                           0
  DEVICE_UNIQUE_OR_CALIBRATION_DO_NOT_PACKAGE:      0
  UNKNOWN:                                          0

final proprietary inventory:                     1891 paths
final AOSP replacement overlay:                   205 paths
new stock files copied into generated vendor:      70
new AOSP paths reclassified:                        7
required first-order unresolved:                    0
required transitive unresolved:                     0
unexplained unresolved:                             0
```

`proprietary-files.txt` remains the complete stock inventory, while
`aosp-replaced-files.txt` is an overlay. Therefore the seven newly
reclassified AOSP paths appear in both lists but are excluded from
`PRODUCT_COPY_FILES` by `setup-makefiles.py`.

## Classification method

`tools/elf_closure.py` parses ELF program headers directly and walks
`DT_NEEDED` to fixpoint. Runtime roots are evidence-derived:

- an init service enabled by default;
- a disabled service started by a non-factory `on` trigger;
- a lazy service carrying an `interface` declaration;
- a dlopen root under `lib64/{hw,egl,soundfx}`;
- factory/META roots separately identified from `factory_init*`, `meta_init*`,
  `vendor/bin/factory` and `vendor/bin/meta_tst`.

The walk deliberately stops at AOSP-provided system libraries: the stock copy
may carry MediaTek patches and extra dependencies that the ROM build does not.
It also scans Soong module definitions, because installation under `/vendor`
does not prove a library is proprietary.

## AOSP/ROM ABI proof

The 14 AOSP classifications are not based on similar names:

- Seven frozen AIDL backends encode the exact interface version and backend in
  their SONAME (`-Vn-ndk.so`). A consumer requesting that exact SONAME is bound
  to the generated ABI for that frozen AIDL version. Their matching HAL/service
  modules and VINTF versions are requested from AOSP by the generated vendor mk.
- The biometrics common helpers and codec2 wrappers are exact Soong module names
  found in the checkout. Copying the stock files caused a duplicate output rule
  during `m nothing`, empirically proving AOSP already installs the same module.
  Reclassification removed the duplicate and both products build.

## Device-unique safety

Every one of the 70 copied additions is an ELF shared library from the immutable
stock partitions. A path/name sweep for `nvram`, `nvdata`, `nvcfg`, `persist`,
`protect1/2`, keybox, IMEI, serials, certificates and calibration data returned
zero hits. No live mutable state is packaged.

## REQUIRED_STOCK_BLOB (47)

These are reachable from a normal-boot service/HAL or dlopen root and
are copied from stock. Platform-specific duplicate copies under
`vendor/lib64/mt6878/` are retained because stock search paths use them.

| Path | Evidence / consumer | Action |
|---|---|---|
| `vendor/lib64/libDR.so` | DT_NEEDED by `vendor/bin/mnld` | copied from immutable stock |
| `vendor/lib64/libasn1c_core.so` | DT_NEEDED by `vendor/lib64/libtranslator_utils.so` | copied from immutable stock |
| `vendor/lib64/libccci_util.so` | DT_NEEDED by `vendor/bin/ccci_mdinit`, `vendor/bin/md_monitor` | copied from immutable stock |
| `vendor/lib64/libcodec2_fsr.so` | DT_NEEDED by `vendor/lib64/libcodec2_mtk_vdec.so`, `vendor/lib64/libcodec2_mtk_venc.so` | copied from immutable stock |
| `vendor/lib64/libcodec2_mtk_c2store.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.media.c2@1.2-mediatek-64b`, `vendor/lib64/libcodec2_mtk_vdec.so`, `vendor/lib64/libcodec2_mtk_venc.so` | copied from immutable stock |
| `vendor/lib64/libcodec2_mtk_vdec.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.media.c2@1.2-mediatek-64b` | copied from immutable stock |
| `vendor/lib64/libcodec2_mtk_venc.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.media.c2@1.2-mediatek-64b` | copied from immutable stock |
| `vendor/lib64/libcodec2_vpp_fa_plugin.so` | DT_NEEDED by `vendor/lib64/libcodec2_mtk_venc.so` | copied from immutable stock |
| `vendor/lib64/libcodec2_vpp_mi_plugin.so` | DT_NEEDED by `vendor/lib64/libcodec2_mtk_vdec.so` | copied from immutable stock |
| `vendor/lib64/libcodec2_vpp_qt_plugin.so` | DT_NEEDED by `vendor/lib64/libcodec2_mtk_vdec.so` | copied from immutable stock |
| `vendor/lib64/libcodec2_vpp_rs_plugin.so` | DT_NEEDED by `vendor/lib64/libcodec2_mtk_vdec.so` | copied from immutable stock |
| `vendor/lib64/libconnfem.so` | DT_NEEDED by `vendor/bin/nvram_daemon` | copied from immutable stock |
| `vendor/lib64/libforkexecwrap.so` | DT_NEEDED by `vendor/bin/ipsec_mon`, `vendor/bin/netdagent` | copied from immutable stock |
| `vendor/lib64/libformatter.so` | DT_NEEDED by `vendor/lib64/libcodec2_mtk_vdec.so`, `vendor/lib64/libcodec2_mtk_venc.so` | copied from immutable stock |
| `vendor/lib64/libhwm.so` | DT_NEEDED by `vendor/bin/hw/vendor.yft.hardware.sensorcali@2.0-service-lazy`, `vendor/bin/nvram_daemon` | copied from immutable stock |
| `vendor/lib64/libicd_decoder.so` | DT_NEEDED by `vendor/bin/dmc_core` | copied from immutable stock |
| `vendor/lib64/libifcutils_mtk.so` | DT_NEEDED by `vendor/bin/frs`, `vendor/bin/ipsec_mon`, `vendor/bin/netdagent` | copied from immutable stock |
| `vendor/lib64/libisetrusty.so` | DT_NEEDED by `vendor/bin/mtk_storageproxyd` | copied from immutable stock |
| `vendor/lib64/libkphhelper.so` | DT_NEEDED by `vendor/lib64/libkphproxy.so` | copied from immutable stock |
| `vendor/lib64/libkphproxy.so` | DT_NEEDED by `vendor/bin/hw/vendor.yft.hardware.obtainvendor@1.0-service`, `vendor/bin/tee_check_keybox` | copied from immutable stock |
| `vendor/lib64/libmmagent.so` | DT_NEEDED by `vendor/bin/hw/vendor.mediatek.hardware.mmagent-service` | copied from immutable stock |
| `vendor/lib64/libmmlpqImpl.so` | DT_NEEDED by `vendor/bin/hw/vendor.mediatek.hardware.mmlpq@V1-service` | copied from immutable stock |
| `vendor/lib64/libmnl.so` | DT_NEEDED by `vendor/bin/mnld` | copied from immutable stock |
| `vendor/lib64/libmtk_bsg.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.boot-service.mtk` | copied from immutable stock |
| `vendor/lib64/libmtkcam_hal_aidl_common.so` | DT_NEEDED by `vendor/lib64/libmtkcam_hal_aidl_device.so`, `vendor/lib64/libmtkcam_hal_aidl_provider.so`, `vendor/lib64/libmtkcam_hal_aidl_utils.so` | copied from immutable stock |
| `vendor/lib64/libmtkcam_hal_aidl_device.so` | DT_NEEDED by `vendor/lib64/libmtkcam_hal_aidl_provider.so` | copied from immutable stock |
| `vendor/lib64/libmtkcam_hal_aidl_provider.so` | DT_NEEDED by `vendor/bin/hw/camerahalserver` | copied from immutable stock |
| `vendor/lib64/libmtkcam_hal_aidl_utils.so` | DT_NEEDED by `vendor/lib64/libmtkcam_hal_aidl_device.so` | copied from immutable stock |
| `vendor/lib64/libmtkgpuserv.so` | DT_NEEDED by `vendor/bin/hw/vendor.mediatek.hardware.gpuserv-service` | copied from immutable stock |
| `vendor/lib64/libneuralnetworks_sl_driver_mtk_prebuilt.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.neuralnetworks-shim-service-mtk` | copied from immutable stock |
| `vendor/lib64/libpl.so` | DT_NEEDED by `vendor/bin/hw/vendor.yft.hardware.obtainvendor@1.0-service`, `vendor/bin/tee_check_keybox`, `vendor/lib64/libkphproxy.so` | copied from immutable stock |
| `vendor/lib64/libstorage_otp.so` | DT_NEEDED by `vendor/bin/ccci_mdinit` | copied from immutable stock |
| `vendor/lib64/libsysenv.so` | DT_NEEDED by `vendor/bin/ccci_mdinit` | copied from immutable stock |
| `vendor/lib64/libtranslator_utils.so` | DT_NEEDED by `vendor/bin/dmc_core` | copied from immutable stock |
| `vendor/lib64/mt6878/libDR.so` | DT_NEEDED by `vendor/bin/mnld` | copied from immutable stock |
| `vendor/lib64/mt6878/libmmagent.so` | DT_NEEDED by `vendor/bin/hw/vendor.mediatek.hardware.mmagent-service` | copied from immutable stock |
| `vendor/lib64/mt6878/libmmlpqImpl.so` | DT_NEEDED by `vendor/bin/hw/vendor.mediatek.hardware.mmlpq@V1-service` | copied from immutable stock |
| `vendor/lib64/mt6878/libmnl.so` | DT_NEEDED by `vendor/bin/mnld` | copied from immutable stock |
| `vendor/lib64/mt6878/libmtkcam_hal_aidl_common.so` | DT_NEEDED by `vendor/lib64/libmtkcam_hal_aidl_device.so`, `vendor/lib64/libmtkcam_hal_aidl_provider.so`, `vendor/lib64/libmtkcam_hal_aidl_utils.so` | copied from immutable stock |
| `vendor/lib64/mt6878/libmtkcam_hal_aidl_device.so` | DT_NEEDED by `vendor/lib64/libmtkcam_hal_aidl_provider.so` | copied from immutable stock |
| `vendor/lib64/mt6878/libmtkcam_hal_aidl_provider.so` | DT_NEEDED by `vendor/bin/hw/camerahalserver` | copied from immutable stock |
| `vendor/lib64/mt6878/libmtkcam_hal_aidl_utils.so` | DT_NEEDED by `vendor/lib64/libmtkcam_hal_aidl_device.so` | copied from immutable stock |
| `vendor/lib64/mt6878/libneuralnetworks_sl_driver_mtk_prebuilt.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.neuralnetworks-shim-service-mtk` | copied from immutable stock |
| `vendor/lib64/mtk_lbs_service-impl.so` | DT_NEEDED by `vendor/bin/mtk_lbs_service` | copied from immutable stock |
| `vendor/lib64/vendor.yft.hardware.changenode@1.0.so` | DT_NEEDED by `vendor/bin/hw/vendor.yft.hardware.changenode@1.0-service` | copied from immutable stock |
| `vendor/lib64/vendor.yft.hardware.gesturewake@1.0.so` | DT_NEEDED by `vendor/bin/hw/vendor.yft.hardware.gesturewake@1.0-service` | copied from immutable stock |
| `vendor/lib64/vendor.yft.hardware.obtainvendor@1.0.so` | DT_NEEDED by `vendor/bin/hw/vendor.yft.hardware.obtainvendor@1.0-service` | copied from immutable stock |

## UNUSED_PARENT_BLOB (23)

Relative to the current skeleton these are only needed by retained
`system_ext` parents whose stock init rc files are not yet integrated.
They are **not excluded**: a complete LieppOS tree may activate those
parents (VT/IMS, charger UI, AEE/logging), so their dependencies were
added conservatively rather than pretending the parents are dead.

| Path | Evidence / consumer | Action |
|---|---|---|
| `system_ext/lib64/libaed.so` | DT_NEEDED by `system_ext/bin/aee_aed64`, `system_ext/bin/aee_aed64_v2`, `system_ext/bin/aee_v2` | copied from immutable stock |
| `system_ext/lib64/libcomutils.so` | DT_NEEDED by `system_ext/lib64/libimsma.so`, `system_ext/lib64/libsink.so`, `system_ext/lib64/libsource.so` | copied from immutable stock |
| `system_ext/lib64/libem_support_jni.so` | DT_NEEDED by `system_ext/bin/em_svr` | copied from immutable stock |
| `system_ext/lib64/libimsma.so` | DT_NEEDED by `system_ext/lib64/libmtk_vt_service.so` | copied from immutable stock |
| `system_ext/lib64/libimsma_adapt.so` | DT_NEEDED by `system_ext/lib64/libimsma_rtp.so` | copied from immutable stock |
| `system_ext/lib64/libimsma_rtp.so` | DT_NEEDED by `system_ext/lib64/libimsma.so`, `system_ext/lib64/libmtk_vt_service.so` | copied from immutable stock |
| `system_ext/lib64/libimsma_socketwrapper.so` | DT_NEEDED by `system_ext/lib64/libimsma_rtp.so` | copied from immutable stock |
| `system_ext/lib64/libmagt.so` | DT_NEEDED by `system_ext/bin/magt` | copied from immutable stock |
| `system_ext/lib64/libmagtsync.so` | DT_NEEDED by `system_ext/lib64/libmagt.so` | copied from immutable stock |
| `system_ext/lib64/libmtk_vt_service.so` | DT_NEEDED by `system_ext/bin/vtservice` | copied from immutable stock |
| `system_ext/lib64/libpcap_bak.so` | DT_NEEDED by `system_ext/bin/netdiag` | copied from immutable stock |
| `system_ext/lib64/libshowlogo.so` | DT_NEEDED by `system_ext/bin/kpoc_charger` | copied from immutable stock |
| `system_ext/lib64/libsignal.so` | DT_NEEDED by `system_ext/lib64/libimsma.so`, `system_ext/lib64/libimsma_rtp.so`, `system_ext/lib64/libsource.so` | copied from immutable stock |
| `system_ext/lib64/libsink.so` | DT_NEEDED by `system_ext/lib64/libimsma.so` | copied from immutable stock |
| `system_ext/lib64/libsource.so` | DT_NEEDED by `system_ext/lib64/libimsma.so`, `system_ext/lib64/libmtk_vt_service.so` | copied from immutable stock |
| `system_ext/lib64/libsysenv_system.so` | DT_NEEDED by `system_ext/bin/em_svr` | copied from immutable stock |
| `system_ext/lib64/libterservice.so` | DT_NEEDED by `system_ext/bin/terservice` | copied from immutable stock |
| `system_ext/lib64/libvcodec_cap.so` | DT_NEEDED by `system_ext/lib64/libimsma.so`, `system_ext/lib64/libimsma_rtp.so`, `system_ext/lib64/libmtk_vt_service.so` | copied from immutable stock |
| `system_ext/lib64/libvcodec_capenc.so` | DT_NEEDED by `system_ext/lib64/libvcodec_cap.so` | copied from immutable stock |
| `system_ext/lib64/libvt_avsync.so` | DT_NEEDED by `system_ext/lib64/libmtk_vt_service.so`, `system_ext/lib64/libsink.so` | copied from immutable stock |
| `system_ext/lib64/vendor.mediatek.framework.mtksf_ext-V4-ndk.so` | DT_NEEDED by `system_ext/lib64/libmagt.so` | copied from immutable stock |
| `system_ext/lib64/vendor.mediatek.hardware.log@1.0.so` | DT_NEEDED by `system_ext/bin/loghidlsysservice` | copied from immutable stock |
| `system_ext/lib64/vendor.mediatek.hardware.videotelephony@1.0.so` | DT_NEEDED by `system_ext/lib64/libmtk_vt_service.so` | copied from immutable stock |

## AOSP_OR_ROM_PROVIDED (14)

These are not copied as proprietary binaries. Exact frozen interface
versions or exact Soong module definitions provide the ABI.

| Path | Evidence / consumer | Action |
|---|---|---|
| `vendor/lib64/android.frameworks.stats-V1-ndk.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.usb.gadget-aidl-service.mediatekv1.0` | AOSP module; not copied |
| `vendor/lib64/android.hardware.biometrics.common.thread.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.biometrics.face-service.example`, `vendor/bin/hw/android.hardware.biometrics.fingerprint-service.example` | AOSP module; not copied |
| `vendor/lib64/android.hardware.biometrics.common.util.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.biometrics.face-service.example`, `vendor/bin/hw/android.hardware.biometrics.fingerprint-service.example` | AOSP module; not copied |
| `vendor/lib64/android.hardware.biometrics.face-V3-ndk.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.biometrics.face-service.example` | AOSP module; not copied |
| `vendor/lib64/android.hardware.cas-V1-ndk.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.cas-service.example` | AOSP module; not copied |
| `vendor/lib64/android.hardware.contexthub-V2-ndk.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.contexthub-service.tinysys` | AOSP module; not copied |
| `vendor/lib64/android.hardware.ir-V1-ndk.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.ir-service.example` | AOSP module; not copied |
| `vendor/lib64/android.hardware.secure_element-V1-ndk.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.secure_element@1.2-service-mediatek` | AOSP module; not copied |
| `vendor/lib64/android.hardware.tetheroffload-V1-ndk.so` | DT_NEEDED by `vendor/bin/hw/tetheroffloadservice` | AOSP module; not copied |
| `vendor/lib64/libcodec2_hidl@1.0.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.media.c2@1.2-mediatek-64b`, `vendor/lib64/libcodec2_hidl@1.1.so`, `vendor/lib64/libcodec2_hidl@1.2.so` | AOSP module; not copied |
| `vendor/lib64/libcodec2_hidl@1.1.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.media.c2@1.2-mediatek-64b`, `vendor/lib64/libcodec2_hidl@1.2.so` | AOSP module; not copied |
| `vendor/lib64/libcodec2_hidl@1.2.so` | DT_NEEDED by `vendor/bin/hw/android.hardware.media.c2@1.2-mediatek-64b` | AOSP module; not copied |
| `vendor/lib64/libcodec2_hidl_plugin.so` | DT_NEEDED by `vendor/lib64/libcodec2_hidl@1.0.so`, `vendor/lib64/libcodec2_hidl@1.1.so`, `vendor/lib64/libcodec2_hidl@1.2.so` | AOSP module; not copied |
| `vendor/lib64/libcodec2_soft_common.so` | DT_NEEDED by `vendor/lib64/libcodec2_mtk_c2store.so`, `vendor/lib64/libcodec2_mtk_vdec.so`, `vendor/lib64/libcodec2_mtk_venc.so` | AOSP module; not copied |

## ALTERNATE_BOM_OR_FACTORY_ONLY (6)

These remain outside the runtime closure. Each parent is confined to
factory/META mode and is not started on the tested shipping boot.

| Path | Evidence / consumer | Action |
|---|---|---|
| `vendor/lib64/libMcClient.so` | DT_NEEDED by `vendor/lib64/libkmsetkey.so` | excluded from runtime closure |
| `vendor/lib64/libfft_vendor.so` | DT_NEEDED by `vendor/bin/factory` | excluded from runtime closure |
| `vendor/lib64/libhfmanagerwrapper.so` | DT_NEEDED by `vendor/bin/factory`, `vendor/bin/meta_tst` | excluded from runtime closure |
| `vendor/lib64/libkmsetkey.so` | DT_NEEDED by `vendor/bin/meta_tst` | excluded from runtime closure |
| `vendor/lib64/libminiui.so` | DT_NEEDED by `vendor/bin/factory` | excluded from runtime closure |
| `vendor/lib64/libpixelflinger.so` | DT_NEEDED by `vendor/lib64/libminiui.so` | excluded from runtime closure |

## Factory/META exclusion proof

```text
libfft_vendor.so       <- vendor/bin/factory
libminiui.so           <- vendor/bin/factory
libpixelflinger.so     <- libminiui.so
libhfmanagerwrapper.so <- vendor/bin/factory, vendor/bin/meta_tst
libkmsetkey.so         <- vendor/bin/meta_tst
libMcClient.so         <- libkmsetkey.so
```

`factory_no_image` and `meta_tst` are disabled services in stock
`init.mt6878.rc`; the remaining factory/META launchers live only in
`factory_init*.rc` or `meta_init*.rc`. None is a VINTF HAL or a normal-boot
property-triggered service. Their dependencies are therefore explicitly
`ALTERNATE_BOM_OR_FACTORY_ONLY`, not silently missing.

## Reproduce

```bash
python3 tools/elf_closure.py   --device .   --stock .work/gq5012bf1/stock/partitions   --aosp-source "$ANDROID_BUILD_TOP"   --json .work/gq5012bf1/reports/elf-closure.json   --check
```
