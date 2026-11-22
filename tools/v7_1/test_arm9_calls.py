import unittest
from arm9_calls import arm_bl_target, inventory


def word(op):
    return op.to_bytes(4, 'little')


class ArmCallsTests(unittest.TestCase):
    def test_forward_bl(self):
        self.assertEqual(arm_bl_target(0x02000000, 0xEB000002), 0x02000010)

    def test_backward_bl(self):
        self.assertEqual(arm_bl_target(0x02000010, 0xEBFFFFFA), 0x02000000)

    def test_b_not_link(self):
        self.assertIsNone(arm_bl_target(0x02000000, 0xEA000002))

    def test_blx_not_bl(self):
        self.assertIsNone(arm_bl_target(0x02000000, 0xFB000002))

    def test_external_target_excluded(self):
        r = inventory(word(0xEB000002) + word(0xE1A00000), 0x02000000)
        self.assertEqual(r['arm_bl_in_span'], 0)
        self.assertEqual(r['arm_bl_outside_span'], 1)

    def test_internal_target_and_callsite(self):
        # BL from 0x02000000 to 0x0200000C (pc+8 + 4)
        r = inventory(word(0xEB000001) + word(0xE1A00000) * 3, 0x02000000)
        self.assertEqual(r['arm_bl_in_span'], 1)
        self.assertEqual(r['candidates'][0]['target'], '0x0200000C')
        self.assertEqual(r['candidates'][0]['callsites'], ['0x02000000'])

    def test_reject_bad_input(self):
        with self.assertRaises(ValueError):
            inventory(b'abc', 0x02000000)
        with self.assertRaises(ValueError):
            inventory(word(0), 0x02000001)


if __name__ == '__main__':
    unittest.main()
