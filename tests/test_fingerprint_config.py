# SPDX-License-Identifier: Apache-2.0
"""Offline C59 regression tests; never executes the ARM64 adapter or uses ADB.

Run with Lineage tools/extract-utils on PYTHONPATH. Set
GQ5012BF1_STOCK_ADAPTER to the preserved stock ELF to enable actual-ELF tests.
"""
from hashlib import sha256
import os
from pathlib import Path
import runpy
import tempfile
import unittest
import xml.etree.ElementTree as ET

from extract_utils.file import File
from extract_utils.fixups_blob import BlobFixupCtx

DEVICE = Path(__file__).resolve().parents[1]
RELATIVE = "vendor/bin/hw/android.hardware.biometrics.fingerprint-service.example"
MODULE = runpy.run_path(str(DEVICE / "extract-files.py"), run_name="test_extract")
STOCK = os.environ.get("GQ5012BF1_STOCK_ADAPTER")


class FingerprintConfigurationTest(unittest.TestCase):
    def test_manifest_is_physical_default_v3(self):
        root = ET.parse(DEVICE / "vintf/fingerprint-example.xml").getroot()
        hal = root.find("hal")
        self.assertEqual(hal.get("format"), "aidl")
        self.assertEqual(hal.findtext("name"), "android.hardware.biometrics.fingerprint")
        self.assertEqual(hal.findtext("version"), "3")
        self.assertEqual(hal.findtext("fqname"), "IFingerprint/default")

    def test_source_owned_init(self):
        lines = [s.strip() for s in (DEVICE / "rootdir/etc/init/fingerprint-example.rc").read_text().splitlines() if s.strip() and not s.lstrip().startswith("#")]
        self.assertEqual(lines[0], "service vendor.fingerprint-example /" + RELATIVE)
        self.assertIn("disabled", lines)
        self.assertNotIn("oneshot", lines)
        self.assertIn("user system", lines)
        self.assertIn("group system input uhid", lines)
        self.assertIn("setenv LD_LIBRARY_PATH /vendor/lib64/fingerprint", lines)
        # Do not permit demand-start to bypass the two TEE readiness gates.
        self.assertFalse(any(s.startswith("interface ") for s in lines))
        self.assertEqual([s for s in lines if s.startswith("on ")], ["on property:vendor.trustkernel.ready=true && property:vendor.trustkernel.fs.state=ready"])
        self.assertEqual([s for s in lines if s.startswith("start ")], ["start vendor.fingerprint-example"])
        self.assertFalse(any("ro.vendor.fps.support" in s for s in lines))

    def test_one_rc_install_owner(self):
        manifest = (DEVICE / "proprietary-files.txt").read_text().splitlines()
        self.assertIn("vendor/etc/init/fingerprint-example.rc;EXTRACT_ONLY", manifest)
        mk = (DEVICE / "device.mk").read_text()
        install = "$(DEVICE_PATH)/rootdir/etc/init/fingerprint-example.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/fingerprint-example.rc"
        self.assertEqual(mk.count(install), 1)
        self.assertGreater(mk.index(install), mk.index("ifeq ($(filter twrp_%,$(TARGET_PRODUCT)),)"))
        self.assertLess(mk.index(install), mk.index("endif # full-ROM product"))

    def test_preserved_cpp_and_v3_ndk_dependencies_are_installed(self):
        manifest = (DEVICE / "proprietary-files.txt").read_text().splitlines()
        for name in ["android.hardware.biometrics.fingerprint-V3-ndk.so",
                     "android.hardware.biometrics.common-V3-ndk.so",
                     "android.hardware.biometrics.common.thread.so",
                     "android.hardware.biometrics.common.util.so",
                     "android.hardware.keymaster-V4-ndk.so"]:
            self.assertIn("vendor/lib64/" + name + ":vendor/lib64/fingerprint/" + name, manifest)
            self.assertNotIn("vendor/lib64/" + name, manifest)
            self.assertNotIn("vendor/lib64/" + name + ";EXTRACT_ONLY", manifest)

    def test_binary_fixup_is_path_scoped(self):
        self.assertEqual(list(MODULE["blob_fixups"]), [RELATIVE])

    def test_no_duplicate_platform_domain(self):
        text = (DEVICE / "sepolicy/vendor/hal_fingerprint_default.te").read_text()
        self.assertNotIn("type hal_fingerprint_default,", text)
        self.assertNotIn("permissive ", text)
        self.assertIn("tkcore_client_device", text)
        self.assertNotIn("tkcore_admin_device", text)
        self.assertNotIn("tkcore_protect_data_file", text)


class FingerprintFixupTest(unittest.TestCase):
    def apply(self, path):
        MODULE["blob_fixups"][RELATIVE].run(BlobFixupCtx(str(DEVICE)), File(RELATIVE), str(path))

    def test_unknown_input_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "unknown"
            data = b"unknown OEM /virtual\x00 binary"
            p.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "Unknown fingerprint adapter"):
                self.apply(p)
            self.assertEqual(p.read_bytes(), data)

    @unittest.skipUnless(STOCK, "set GQ5012BF1_STOCK_ADAPTER for actual-ELF test")
    def test_audited_elf_only_changes_registration_suffix(self):
        raw = Path(STOCK).read_bytes()
        self.assertEqual(sha256(raw).hexdigest(), MODULE["FINGERPRINT_ADAPTER_STOCK_SHA256"])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "adapter"
            p.write_bytes(raw)
            self.apply(p)
            fixed = p.read_bytes()
            self.assertEqual(len(raw), len(fixed))
            self.assertEqual(sha256(fixed).hexdigest(), MODULE["FINGERPRINT_ADAPTER_DEFAULT_SHA256"])
            self.assertEqual(raw.count(b"/virtual\x00"), 1)
            self.assertEqual(raw.index(b"/virtual\x00"), 0x2DCB)
            self.assertEqual(fixed, raw[:0x2DCB] + b"/default\x00" + raw[0x2DD4:])
            self.assertEqual(sum(a != b for a, b in zip(raw, fixed)), 6)
            mtime = p.stat().st_mtime_ns
            self.apply(p)
            self.assertEqual(p.stat().st_mtime_ns, mtime)
            self.assertEqual(p.read_bytes(), fixed)
        self.assertEqual(Path(STOCK).read_bytes(), raw)  # preserved reference

    @unittest.skipUnless(STOCK, "set GQ5012BF1_STOCK_ADAPTER for actual-ELF test")
    def test_tampered_elf_rejected_without_writing(self):
        raw = bytearray(Path(STOCK).read_bytes())
        raw[-1] ^= 1
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tampered"
            p.write_bytes(raw)
            with self.assertRaises(ValueError):
                self.apply(p)
            self.assertEqual(p.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
