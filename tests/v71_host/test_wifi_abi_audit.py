"""V7.3 local ROM fingerprint safety tests. Synthetic ROMs only."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "tools/v7_3/hgss_wifi_abi_audit.py"
spec = importlib.util.spec_from_file_location("wifi_abi_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def synthetic_rom(path, *, game_code=b"IPKE", duplicate=False, invalid_file_id=False):
    data = bytearray(0x3000)
    data[0:12] = b"POKEMON HG  "
    data[0x0C:0x10] = game_code
    struct.pack_into("<4I", data, 0x20, 0x200, 0x02000000, 0x02000000, 0x400)
    struct.pack_into("<4I", data, 0x30, 0x800, 0x037F8000, 0x037F8000, 0x300)
    struct.pack_into("<2I", data, 0x48, 0x1000, 16)
    struct.pack_into("<2I", data, 0x50, 0x1200, 64 if duplicate else 32)
    struct.pack_into("<4I", data, 0x1000, 0x1800, 0x1900, 0x2000, 0x2100)
    struct.pack_into("<8I", data, 0x1200, 72, 0x02200000, 0x1000,
                     0x100, 0x02200020, 0x02200040,
                     200 if invalid_file_id else 1, 0)
    if duplicate:
        struct.pack_into("<8I", data, 0x1220, 72, 0x02200000,
                         0x1000, 0x100, 0x02200020, 0x02200040, 1, 0)
    data[0x200:0x600] = b"A" * 0x400
    data[0x800:0xB00] = b"B" * 0x300
    data[0x2000:0x2100] = b"C" * 0x100
    struct.pack_into("<H", data, 0x15E, audit.crc16_nitro(data[:0x15E]))
    path.write_bytes(data)


class WifiAbiAuditTests(unittest.TestCase):
    def test_valid_report_is_read_only_and_has_no_code_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.nds"
            synthetic_rom(path)
            before = path.read_bytes()
            report = audit.audit_rom(path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(report["game_code"], "IPKE")
            self.assertTrue(report["nds_header_crc16"]["match"])
            ov = report["overlay_tables"]["arm9"]
            self.assertEqual(ov["count"], 1)
            self.assertEqual(ov["selected"][0]["overlay_id"], 72)
            self.assertEqual(ov["selected"][0]["rom_file_bytes"], 0x100)
            self.assertEqual(report["arm9_nitro_module_params"]["raw_marker_matches"], 0)
            self.assertFalse(report["network_abi"]["wifi_calls_permitted"])
            self.assertFalse(ov["selected"][0]["resident_during_overworld_verified"])
            self.assertNotIn(str(path), str(report))
            self.assertNotIn("AAAAAAAA", str(report))

    def test_rejects_non_hgss_and_invalid_overlay_file_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.nds"
            synthetic_rom(path, game_code=b"ABCD")
            with self.assertRaisesRegex(ValueError, "not a HeartGold"):
                audit.audit_rom(path)
            synthetic_rom(path, invalid_file_id=True)
            with self.assertRaisesRegex(ValueError, "missing FAT"):
                audit.audit_rom(path)

    def test_rejects_duplicate_overlay_and_arm9_out_of_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.nds"
            synthetic_rom(path, duplicate=True)
            with self.assertRaisesRegex(ValueError, "repeated overlay"):
                audit.audit_rom(path)
            synthetic_rom(path)
            data = bytearray(path.read_bytes())
            struct.pack_into("<I", data, 0x20, 0xFFFFFF00)
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "outside image"):
                audit.audit_rom(path)

    def test_raw_module_params_marker_is_only_a_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.nds"
            synthetic_rom(path)
            data = bytearray(path.read_bytes())
            # module params at file 0x250, marker is 0x1C bytes later.
            struct.pack_into("<II", data, 0x250 + 0x14, 0x02110000, 0x03000200)
            data[0x250 + 0x1C:0x250 + 0x24] = bytes.fromhex("2106c0dede c00621")
            path.write_bytes(data)
            result = audit.audit_rom(path)
            params = result["arm9_nitro_module_params"]
            self.assertEqual(params["raw_marker_matches"], 1)
            self.assertEqual(params["unique_raw_candidate"]["compressed_static_end_candidate"], "0x02110000")
            self.assertEqual(params["unique_raw_candidate"]["sdk_version_candidate"], "0x03000200")
            self.assertFalse(params["runtime_params_validated"])
            self.assertFalse(result["network_abi"]["wifi_calls_permitted"])

    def test_never_overwrites_source_rom_even_if_output_is_same(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.nds"
            synthetic_rom(path)
            before = path.read_bytes()
            self.assertEqual(audit.main([str(path), "--output", str(path)]), 2)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
