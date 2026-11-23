"""Synthetic tests for V7.4 read-only, bounded backwards BLZ decoder.

No commercial game image is required or included in CI.
"""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest


PATH = Path(__file__).resolve().parents[2] / "tools/v7_4/arm9_runtime_reconstruction.py"
spec = importlib.util.spec_from_file_location("v74_blz", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def make_blz():
    # BLZ is decoded backwards: read 3 literal 'A' seed bytes, then four
    # 18-byte backreferences at minimum distance. Output 75 'A' bytes.
    tokens = bytes([0x1E, 65, 65, 65] + [v for _ in range(4) for v in (0xF0, 0x00)])
    prefix = bytearray(b"Z" * 256)
    body = bytes(reversed(tokens))
    packed_span = len(body) + 8
    # In-memory decoded region is 75 bytes; stored compressed region is
    # 12 token bytes + 8 footer bytes, yielding 55 expansion bytes.
    grow = 75 - packed_span
    img = bytes(prefix) + body + struct.pack("<II", (8 << 24) | packed_span, grow)
    expected = bytes(prefix) + b"A" * 75
    return img, expected


class BackwardBlzTests(unittest.TestCase):
    def test_synthetic_backreferences_reconstruct_expected_image(self):
        encoded, expected = make_blz()
        result, metadata = m.decompress_backwards(encoded, m.BASE + len(encoded))
        self.assertEqual(bytes(result), expected)
        self.assertEqual(metadata["growth_bytes"], 55)
        self.assertEqual(metadata["static_runtime_bytes"], len(expected))

    def test_reject_invalid_end_and_overflow(self):
        encoded, _ = make_blz()
        with self.assertRaisesRegex(m.BLZError, "end differs"):
            m.decompress_backwards(encoded, m.BASE + len(encoded) + 4)
        damaged = bytearray(encoded)
        struct.pack_into("<I", damaged, len(damaged) - 4, m.MAX_DECOMPRESSED_BYTES)
        with self.assertRaisesRegex(m.BLZError, "exceed"):
            m.decompress_backwards(bytes(damaged), m.BASE + len(damaged))

    def test_reject_invalid_footer_and_truncated_bitstream(self):
        encoded, _ = make_blz()
        damaged = bytearray(encoded)
        struct.pack_into("<I", damaged, len(damaged) - 8, (7 << 24) | 20)
        with self.assertRaisesRegex(m.BLZError, "header length"):
            m.decompress_backwards(bytes(damaged), m.BASE + len(damaged))
        damaged = bytearray(encoded)
        struct.pack_into("<I", damaged, len(damaged) - 8, (8 << 24) | 9)
        with self.assertRaises(m.BLZError):
            m.decompress_backwards(bytes(damaged), m.BASE + len(damaged))

    def test_reject_unknown_rom_before_reading_runtime_bytes(self):
        from io import StringIO
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "not-a-rom.nds"
            p.write_bytes(b"\0" * 0x200)
            out = Path(tmp) / "report.json"
            self.assertEqual(m.main([str(p), "--output", str(out)]), 2)
            self.assertFalse(out.exists())

    def test_refuse_to_overwrite_rom_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "foo.nds"
            p.write_bytes(b"not a ROM")
            before = p.read_bytes()
            self.assertEqual(m.main([str(p), "--output", str(p)]), 2)
            self.assertEqual(p.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
