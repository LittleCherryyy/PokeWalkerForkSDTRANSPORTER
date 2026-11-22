import tempfile
import unittest
from pathlib import Path

from nds_overlays import inspect_overlays


def put32(data, at, value):
    data[at:at + 4] = value.to_bytes(4, "little")


def synthetic_rom(with_fat=True, duplicate=False):
    raw = bytearray(0x600)
    raw[0x0C:0x10] = b"IPKE"
    raw[0x1E] = 2
    put32(raw, 0x20, 0x200)
    put32(raw, 0x24, 0x02000000)
    put32(raw, 0x28, 0x02000000)
    put32(raw, 0x2C, 16)
    put32(raw, 0x50, 0x280)
    put32(raw, 0x54, 64)
    if with_fat:
        put32(raw, 0x48, 0x2C0)
        put32(raw, 0x4C, 16)
        put32(raw, 0x2C0, 0x300)
        put32(raw, 0x2C4, 0x320)
        put32(raw, 0x2C8, 0x320)
        put32(raw, 0x2CC, 0x348)
    for index in range(2):
        at = 0x280 + 32 * index
        put32(raw, at + 0, 0 if duplicate else index)
        put32(raw, at + 4, 0x02200000 + 0x8000 * index)
        put32(raw, at + 8, 0x1200)
        put32(raw, at + 12, 0x200)
        put32(raw, at + 16, 0x02200000 + 0x8000 * index)
        put32(raw, at + 20, 0x02200000 + 0x8000 * index + 8)
        put32(raw, at + 24, index)
        put32(raw, at + 28, 0x01001000)
    return raw


class OverlayInspectorTests(unittest.TestCase):
    def inspect(self, raw, overlay_id=0):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "synthetic.nds"
            path.write_bytes(raw)
            return inspect_overlays(path, overlay_id)

    def test_overlay_zero_and_fat_location(self):
        out = self.inspect(synthetic_rom())
        self.assertEqual(out["game_code"], "IPKE")
        self.assertEqual(out["header_rom_revision"], 2)
        self.assertEqual(out["total_arm9_overlays"], 2)
        self.assertEqual(len(out["matches"]), 1)
        ov = out["matches"][0]
        self.assertEqual(ov["overlay_id"], 0)
        self.assertEqual(ov["ram_address"], "0x02200000")
        self.assertEqual(ov["ram_end_exclusive"], "0x02201400")
        self.assertEqual(ov["stored_file_offset"], "0x00000300")
        self.assertEqual(ov["stored_file_length"], 32)

    def test_all_overlays_returns_only_metadata(self):
        out = self.inspect(synthetic_rom(), None)
        self.assertEqual([o["overlay_id"] for o in out["matches"]], [0, 1])
        self.assertEqual(out["matches"][1]["stored_file_length"], 40)
        self.assertNotIn("rom_bytes", str(out))

    def test_missing_requested_overlay(self):
        out = self.inspect(synthetic_rom(), 99)
        self.assertEqual(out["matches"], [])
        self.assertEqual(out["total_arm9_overlays"], 2)

    def test_no_fat_still_reads_overlay_metadata(self):
        out = self.inspect(synthetic_rom(with_fat=False))
        self.assertIsNone(out["matches"][0]["stored_file_length"])

    def test_bad_game_code(self):
        raw = synthetic_rom()
        raw[0x0C:0x10] = b"ABCE"
        with self.assertRaises(ValueError):
            self.inspect(raw)

    def test_invalid_overlay_table_size(self):
        raw = synthetic_rom()
        put32(raw, 0x54, 31)
        with self.assertRaises(ValueError):
            self.inspect(raw)

    def test_overlay_table_outside_rom(self):
        raw = synthetic_rom()
        put32(raw, 0x50, 0x700)
        with self.assertRaises(ValueError):
            self.inspect(raw)

    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):
            self.inspect(synthetic_rom(duplicate=True), None)

    def test_out_of_range_file_id(self):
        raw = synthetic_rom()
        put32(raw, 0x280 + 24, 7)
        with self.assertRaises(ValueError):
            self.inspect(raw)

    def test_file_offset_outside_rom(self):
        raw = synthetic_rom()
        put32(raw, 0x2C4, 0x900)
        with self.assertRaises(ValueError):
            self.inspect(raw)

    def test_init_order_invalid(self):
        raw = synthetic_rom()
        put32(raw, 0x280 + 16, 0x02200010)
        put32(raw, 0x280 + 20, 0x02200008)
        with self.assertRaises(ValueError):
            self.inspect(raw)

    def test_ram_range_overflow(self):
        raw = synthetic_rom()
        put32(raw, 0x280 + 4, 0xFFFFF000)
        with self.assertRaises(ValueError):
            self.inspect(raw)


if __name__ == "__main__":
    unittest.main()
