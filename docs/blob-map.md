# Proprietary blob map

## Reproducible set

`proprietary-files.txt` contains 1,891 evidence-selected stock paths across
system, system_ext, product, vendor and vendor_dlkm. It is generated from:

- every stock vendor/odm VINTF manifest;
- every present vendor/odm init executable;
- hardware HAL/configuration roots;
- all vendor_dlkm modules and module metadata;
- explicit Ulefone hardware applications, including ThermoVue and MiniScreen;
- recursive in-stock ELF `DT_NEEDED` providers.

Offline extraction from the seven EROFS partition roots completed with **zero
missing files**. The generated proprietary payload is approximately 1 GB.

## Build integration rules

- `extract-files.py` and `setup-makefiles.py` use the LineageOS 22.2
  `extract-utils` single-device framework and generate standard vendor Soong
  modules and product makefiles.
- APKs are emitted as presigned `android_app_import` modules, never
  `PRODUCT_COPY_FILES` APKs. Retained ELF binaries and libraries are emitted as
  typed Soong prebuilts.
- Stock `.odex`, `.vdex` and `.art` files are accounted but marked
  `EXTRACT_ONLY`; they are tied to the stock framework build.
- `build.prop`, `default.prop` and `prop.default` are evidence only and are also
  `EXTRACT_ONLY`; the target build generates its own partition properties.
- Stock vendor VINTF XML is integrated by generated extract-utils modules. The
  verified dual-SIM manifest remains active; SS/TSTS/QSQS alternate-BOM
  manifests remain inventoried as `EXTRACT_ONLY` evidence.
- The downloadable `uSmartCamera.apk` stock resource is accounted but not
  silently promoted to an installed system app.
- No binary fixup is currently applied because evidence has not justified one.
  `extract-files.py` keeps explicit, path-scoped `blob_fixups` and `lib_fixups`
  maps for future proven changes.
- Strict build-graph analysis found 205 stock paths produced by AOSP modules:
  all 198 original replacements remain, and seven vendor-available biometrics /
  codec2 libraries were reclassified after exact Soong module matching and a
  duplicate-install build failure proved that copying them was wrong. The paths
  remain accounted in `proprietary-files.txt` with `EXTRACT_ONLY`, are audited
  against `aosp-replaced-files.txt`, and are not duplicated in generated vendor
  output. `device.mk` requests the 38 unambiguous owning AOSP modules; their
  libraries arrive transitively.
- `tools/elf_closure.py` enforces the transitive runtime dependency graph. The
  original 90 concrete candidates are classified in [elf-closure.md](elf-closure.md):
  47 required stock paths, 23 conservatively retained parent dependencies,
  14 AOSP/ROM-provided paths and six factory/META-only exclusions. Final
  required and unexplained unresolved counts are zero.

## Licensing

Presence in the extraction recipe does not grant redistribution rights. The
public device repository can retain the recipe while binary publication remains
a project/legal decision.
