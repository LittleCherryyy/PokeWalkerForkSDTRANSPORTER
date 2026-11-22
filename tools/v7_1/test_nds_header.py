import tempfile
import unittest
from pathlib import Path

from nds_header import inspect_rom, parse_nds_header


def fixture(code=b"IPKE", offset=0x200, size=16, load=0x02000000):
    header = bytearray(0x200)
    header[0x0C:0x10] = code
    header[0x20:0x24] = offset.to_bytes(4, "little")
    header[0x24:0x28] = load.to_bytes(4, "little")
    header[0x28:0x2C] = load.to_bytes(4, "little")
    header[0x2C:0x30] = size.to_bytes(4, "little")
    return bytes(header) + bytes([0xEA] * size)


class NdsHeaderTests(unittest.TestCase):
    def test_heartgold(self):
        raw = fixture()
        report = parse_nds_header(raw[:0x200], len(raw))
        self.assertEqual(report["game_code"], "IPKE")
        self.assertTrue(report["hgss_candidate"])
        self.assertEqual(report["arm9_ram_address"], "0x02000000")

    def test_soulsilver(self):
        raw = fixture(code=b"IPGE")
        self.assertTrue(parse_nds_header(raw[:0x200], len(raw))["hgss_candidate"])

    def test_non_hgss(self):
        raw = fixture(code=b"ABCE")
        self.assertFalse(parse_nds_header(raw[:0x200], len(raw))["hgss_candidate"])

    def test_truncated_header(self):
        with self.assertRaises(ValueError):
            parse_nds_header(b"x" * 16, 1024)

    def test_arm9_segment_outside_file(self):
        raw = fixture(size=16)
        with self.assertRaises(ValueError):
            parse_nds_header(raw[:0x200], len(raw) - 1)

    def test_alignment(self):
        raw = fixture(offset=0x201)
        with self.assertRaises(ValueError):
            parse_nds_header(raw[:0x200], len(raw))

    def test_invalid_game_code(self):
        raw = fixture(code=b"IP\x00E")
        with self.assertRaises(ValueError):
            parse_nds_header(raw[:0x200], len(raw))

    def test_sha256_matches_stored_segment(self):
        raw = fixture()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "synthetic.nds"
            path.write_bytes(raw)
            report = inspect_rom(path)
        import hashlib
        self.assertEqual(report["arm9_stored_sha256"],
                         hashlib.sha256(raw[0x200:]).hexdigest())


if __name__ == "__main__":
    unittest.main()
