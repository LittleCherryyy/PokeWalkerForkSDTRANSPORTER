"""Offline regression tests for the real DSi 2026-11-22 V7.2 snapshot."""
import importlib.util
from pathlib import Path
import unittest

FILE=Path(__file__).resolve().parents[2]/"tools/v7_2/analyze_irq_snapshot.py"
SPEC=importlib.util.spec_from_file_location("v72_irq_audit",FILE)
audit=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

class IrqAuditTests(unittest.TestCase):
    def test_real_dsi_photo(self):
        result=audit.analyze(0x00050019, 1, [0x00C1,0x00C1,0,0])
        self.assertEqual(result["irq_enabled"],
            ["VBlank","Timer 0","Timer 1","IPC sync","IPC receive FIFO"])
        self.assertTrue(result["irq_master_enabled"])
        self.assertFalse(result["wifi_irq_enabled"])
        self.assertEqual(result["readiness"],"NOT VERIFIED")
        for i in (0,1):
            t=result["timers"][i]
            self.assertTrue(t["enabled"])
            self.assertTrue(t["irq_requested"])
            self.assertEqual(t["prescaler"],64)
            self.assertFalse(t["cascade"])
        for i in (2,3):
            self.assertFalse(result["timers"][i]["enabled"])
        self.assertTrue(any("ARM9" in s for s in result["evidence_still_required"]))
        self.assertTrue(any("DMA3" in s for s in result["evidence_still_required"]))

    def test_reserved_irq_bit_does_not_claim_safe_radio(self):
        result=audit.analyze(1<<24,1,[0,0,0,0])
        self.assertTrue(result["wifi_irq_enabled"])
        self.assertEqual(result["readiness"],"NOT VERIFIED")
        self.assertIn("disabled timers are not guaranteed free", result["interpretation"])

    def test_width_and_timer_count(self):
        with self.assertRaises(ValueError):
            audit.analyze(1<<32,0,[0,0,0,0])
        with self.assertRaises(ValueError):
            audit.analyze(0,0,[0,0,0])
        with self.assertRaises(ValueError):
            audit.decode_timer(0x10000)

if __name__=="__main__":
    unittest.main()
