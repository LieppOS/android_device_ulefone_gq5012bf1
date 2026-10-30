#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-License-Identifier: Apache-2.0
#
"""Extract GQ5012BF1 proprietary files with LineageOS extract-utils."""

from hashlib import sha256
from pathlib import Path

from extract_utils.fixups_blob import (
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)

# The generated vendor namespace is imported explicitly, matching the standard
# single-device LineageOS extraction pattern.
namespace_imports = [
    "vendor/ulefone/gq5012bf1",
]

FINGERPRINT_ADAPTER_STOCK_SHA256 = "686fd480f96b0360664ef0d490bede1edbc86fda4085d767160879dd879caa81"
FINGERPRINT_ADAPTER_DEFAULT_SHA256 = "174a753e89cb0d157fb603118a56a2e4dc9be59fed0796717202af01aa06752a"


def _fix_fingerprint_instance(ctx, file, file_path, **kwargs):
    """Retarget only the audited OEM registration string, never unknown ELFs.

    Android 17 maps IFingerprint/virtual to the AOSP IVirtualHal controller.
    OEM main appends the unique /virtual literal (file offset 0x2dcb) to the
    IFingerprint descriptor. Both suffixes have eight bytes: no code, ABI,
    offsets, sensor metadata, algorithm or secure-world data changes.
    """
    path = Path(file_path)
    data = path.read_bytes()
    digest = sha256(data).hexdigest()
    if digest == FINGERPRINT_ADAPTER_DEFAULT_SHA256:
        return  # Idempotent regeneration from an already-fixed extraction.
    if digest != FINGERPRINT_ADAPTER_STOCK_SHA256:
        raise ValueError("Unknown fingerprint adapter: re-audit before applying C59 fixup")
    if data.count(b"/virtual\x00") != 1:
        raise ValueError("Fingerprint registration literal is not unique")
    fixed = data.replace(b"/virtual\x00", b"/default\x00")
    if sha256(fixed).hexdigest() != FINGERPRINT_ADAPTER_DEFAULT_SHA256:
        raise ValueError("Fingerprint adapter output identity mismatch")
    path.write_bytes(fixed)


# Applied by extract-utils to the extracted working copy, not the stock input.
# Keep binary registration, source-owned rc and device VINTF on /default.
blob_fixups: blob_fixups_user_type = {
    "vendor/bin/hw/android.hardware.biometrics.fingerprint-service.example": (
        blob_fixup().call(_fix_fingerprint_instance, need_tmp_dir=False)
    ),
}

# Retain extract-utils' standard library fixups. No GQ5012BF1-specific library
# rename has been proven necessary.
lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
}

# check_elf drives generated ELF link metadata. The stock payload is an
# Android 15 MediaTek image whose DT_NEEDED closure references vendor AIDL
# versions (camera.common-V2, biometrics.common-V4, ...) that are not source
# modules on every branch this tree is parsed in, and synthesising link
# metadata for them changes nothing about what is installed. Blobs are
# therefore installed at their exact stock paths, which is also the state the
# offline ELF dependency closure audit was validated against.
# Enabling it is future hardening, to be done with evidence on the target
# Android 15 branch.
module = ExtractUtilsModule(
    "gq5012bf1",
    "ulefone",
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
    check_elf=False,
)

if __name__ == "__main__":
    utils = ExtractUtils.device(module)
    utils.run()
