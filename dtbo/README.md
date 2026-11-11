# GQ5012BF1 dtbo.img from source

The dtbo partition holds one Android DT table entry: the board overlay that
LK applies on top of the base DTB from `vendor_boot`. Its source is in the
kernel repository:

| File (android/kernel/ulefone/gq5012bf1/) | Content |
|---|---|
| `arch/arm64/boot/dts/mediatek/gq5012bf1.dts` | main overlay: audio amp, display/panel, USB-C, TEE memory, heaps |
| `arch/arm64/boot/dts/gq5012bf1/cust.dtsi` | DrvGen-style GPIO init, EINTs, SIM, keypad |
| `arch/arm64/boot/dts/mediatek/gq5012bf1-camera.dtsi` | cameras, flash/IR/warning-light drivers, camera thermal zones |
| `arch/arm64/boot/dts/mediatek/gq5012bf1-connfem.dtsi` | Wi-Fi/BT front-end table |

The source was recovered from the stock overlay by decompiling it and
rebuilding it as symbolic source. It follows the layout of MediaTek's
`k6878v1_64.dts`. It is not Ulefone's original text, but it compiles back
to the stock entry **byte for byte**. Research notes are in
`research/ulefone-gq5012bf1/reverse-engineering/device-tree/`.

## Building

Standalone:

```sh
dtbo/build-dtbo.sh \
    --kernel-src ../../../kernel/ulefone/gq5012bf1 \
    --out /tmp/dtbo
cat /tmp/dtbo/BUILD-REPORT.txt
```

This produces the following files:

- `gq5012bf1.dtbo`: the compiled overlay, made with `cpp` then `dtc -@`
  using the same flags as Kbuild.
- `dtbo-table.img`: the Android DT table, made with `mkdtboimg` (entry 0,
  id 0, rev 0, page size 2048). It ends at the header's `total_size`.
- `dtbo.img`: the table plus Ulefone's MediaTek `cert1`/`cert2` blocks,
  **only** if `cert2` still authenticates these bytes (see below).
- `dtbo-avb.img`: written only with `--avbtool`. It is `dtbo.img` with an
  AVB hash footer for an 8 MiB partition.

Kernel Kbuild builds the overlay too:
`make ARCH=arm64 LLVM=1 mediatek/gq5012bf1.dtbo`.

ROM build (`BoardConfig.mk`):

```sh
./build.sh                      # LIEPPOS_DTBO=stock (default): prebuilt/dtbo.img
LIEPPOS_DTBO=source ./build.sh  # compile from the kernel source
```

- In source mode the build runs `dtbo/build-dtbo.sh` using the build's own
  `dtc`, `mkdtboimg` and prebuilt clang. The kernel source path defaults to
  `../LieppOS_kernel/android/kernel/ulefone/gq5012bf1`; set
  `LIEPPOS_KERNEL_SOURCE` to override it.
- A missing source is a build error. The build never falls back to the
  stock image.
- Kati prints `LieppOS DTBO: STOCK ...` or `LieppOS DTBO: SOURCE-BUILT ...`.
- `$(PRODUCT_OUT)/lieppos-dtbo-report.txt` records the mode and the
  hashes.
- The Android build then adds its normal AVB hash footer. The hash
  descriptor goes into the root `vbmeta`, as on stock.

## MediaTek certificate and LK

The stock `dtbo.img` content is 48,320 bytes, made up of:

- the DT table (44,568 bytes);
- zero padding to a 16-byte boundary;
- MediaTek `cert1` at offset 44,576;
- MediaTek `cert2` at offset 46,800.

`cert2` carries two values:

- `sha256(bytes 0..32)`, under OID 2.16.886.2454.2.4;
- `sha256(bytes 32..44576)`, under OID 2.16.886.2454.2.1.

LK checks this on every boot. The `pl_lk` log of slot B on 2026-11-11
shows `img_auth_required = 1`, then `dtbo cert chain vfy pass`, `image dtbo
header auth pass` and `image dtbo auth pass`.

`build-dtbo.sh` appends the original `cert1`/`cert2` only when both hashes
match the newly built bytes. Nothing is re-signed. If the source has
changed, the hashes cannot match, and the build stops unless you pass
`--allow-unsigned` (`LIEPPOS_DTBO_ALLOW_UNSIGNED=true`). This is because
nobody has tested whether LK on this unlocked unit boots a dtbo without
valid certs. `python3 dtbo/dtbo_tool.py mtkcert IMG` checks any image.

## Validation tools

```sh
T="python3 dtbo/dtbo_tool.py"
$T info IMG                       # header, entries, fragments, fixups, certs, AVB
$T compare prebuilt/dtbo.img IMG  # binary, canonical and effective overlay diff
$T labels IMG BASE                # every overlay label exists in the base DTB
$T apply BASE prebuilt/dtbo.img IMG   # fdtoverlay both, compare merged trees
```

`BASE` can be a raw FDT or the `vendor_boot` dtb section (an Android DT
table). The matching bases are:

- the stock `vendor_boot` DTB (slot A);
- `prebuilt/dtbs/gq5012bf1-hbm.dtb` (slot B).

The kernel tree's own `mt6878.dts` is **not** a valid base: it lacks the
labels `typec_mux_switch`, `sky85732` and `rtc7620`.

## Reproducing stock exactly

```sh
dtbo/build-dtbo.sh --kernel-src ... --out /tmp/dtbo \
    --avbtool "python3 <lineage>/external/avb/avbtool.py" \
    --salt 9c02741721a24549180ce75e774265e894e30f7442167b91ef7b06dec913b654 \
    --avb-extra "--prop com.android.build.dtbo.fingerprint:Ulefone/GQ5012BF1_EEA/GQ5012BF1:15/AP3A.240905.015.A2/1761131274:user/release-keys --internal_release_string 'avbtool 1.3.0'"
cmp /tmp/dtbo/dtbo-avb.img prebuilt/dtbo.img   # identical (sha256 90929678...42d3)
```

## Changing the overlay

1. Edit the kernel DTS.
2. Build with `--allow-unsigned`.
3. Run `compare` and `apply` against both base DTBs.
4. Write down every difference.
5. A flash test needs explicit owner approval and must follow
   `research/.../device-tree/HARDWARE-TEST-PLAN.md`. Slot B only, with the
   rollback image ready.
