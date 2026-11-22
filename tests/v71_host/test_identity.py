#!/usr/bin/env python3
"""Synthetic image tests; uses no game files."""
import importlib.util
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tools/v7_1/identify_hgss_nds.py"
spec = importlib.util.spec_from_file_location("hgss_identity", SRC)
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class IdentityTests(unittest.TestCase):
    def test_synthetic_header(self):
        buf = bytearray(0x2400)
        buf[0x0c:0x10] = b"IPKE"
        buf[0x12] = 0
        buf[0x1e] = 1
        import struct
        struct.pack_into("<IIII", buf, 0x20, 0x200, 0x02000000, 0x02000000, 0x200)
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "synthetic.nds"
            p.write_bytes(buf)
            result = identity.identify(p)
        self.assertEqual(result["game_code"], "IPKE")
        self.assertEqual(result["game"], "HeartGold US")
        self.assertEqual(result["arm9_size"], 0x200)
        self.assertIsNone(result["reference_match"])
        self.assertFalse(result["callable_wifi_api_verified"])

    def test_bounds_fail_closed(self):
        buf = bytearray(0x400)
        buf[0x0c:0x10] = b"IPGE"
        import struct
        struct.pack_into("<IIII", buf, 0x20, 0x300, 0, 0x02000000, 0x200)
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "invalid.nds"
            p.write_bytes(buf)
            with self.assertRaises(ValueError):
                identity.identify(p)

    def test_truncated_file(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "small.nds"
            p.write_bytes(b"none")
            with self.assertRaises(ValueError):
                identity.identify(p)


if __name__ == "__main__":
    unittest.main()
