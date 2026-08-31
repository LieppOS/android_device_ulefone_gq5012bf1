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

- APKs are emitted as presigned `android_app_import` modules, never
  `PRODUCT_COPY_FILES` APKs.
- Stock `.odex`, `.vdex` and `.art` files are accounted but deliberately not
  installed; they are tied to the stock framework build.
- `build.prop`, `default.prop` and `prop.default` are evidence only; the target
  build generates its own partition properties.
- VINTF XML is assembled via `DEVICE_MANIFEST_FILE` and the dual-SIM
  `ODM_MANIFEST_FILES`, not copied as opaque metadata.
- The downloadable `uSmartCamera.apk` stock resource is accounted but not
  silently promoted to an installed system app.
- No binary fixup is currently applied because evidence has not justified one.
  `extract-files.py` provides a path-scoped fixup hook for future proven needs.
- Strict build-graph analysis found 205 stock paths produced by AOSP modules:
  all 198 original replacements remain, and seven vendor-available biometrics /
  codec2 libraries were reclassified after exact Soong module matching and a
  duplicate-install build failure proved that copying them was wrong. The paths
  remain accounted in `proprietary-files.txt`, are explicitly overlaid by
  `aosp-replaced-files.txt`, and are not duplicated into the generated vendor
  package. `setup-makefiles.py` requests the 38 service/binary/permission modules
  whose names are unambiguous; their libraries arrive transitively.
- `tools/elf_closure.py` enforces the transitive runtime dependency graph. The
  original 90 concrete candidates are classified in [elf-closure.md](elf-closure.md):
  47 required stock paths, 23 conservatively retained parent dependencies,
  14 AOSP/ROM-provided paths and six factory/META-only exclusions. Final
  required and unexplained unresolved counts are zero.
- The remaining exact-path ELF generator still uses the scoped
  `BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES` compatibility switch.
  Converting retained ELF files to typed prebuilts is future hardening.

## Licensing

Presence in the extraction recipe does not grant redistribution rights. The
public device repository can retain the recipe while binary publication remains
a project/legal decision.
