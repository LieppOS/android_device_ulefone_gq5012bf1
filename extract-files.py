#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-License-Identifier: Apache-2.0
#
"""Extract GQ5012BF1 proprietary files with LineageOS extract-utils."""

from extract_utils.fixups_blob import (
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

# Offline ELF and image audits have not justified mutating any stock binary.
# Keep this map explicit so future changes remain path-scoped and reviewable.
blob_fixups: blob_fixups_user_type = {}

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
# offline ELF closure audit in tools/elf_closure.py was validated against.
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
