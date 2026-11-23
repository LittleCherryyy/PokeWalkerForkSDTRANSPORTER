"""Photo-based V7.2.1 regression tests for conservative DSWifi resource gating."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
FILE=ROOT/"tools/v7_2/analyze_arm9_dma_snapshot.py"
spec=importlib.util.spec_from_file_location("pw_v72_arm9_audit", FILE)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class Arm9DmaAuditTests(unittest.TestCase):
    def test_actual_dsi_photo_and_irq_decode(self):
        r=audit.analyze(0,0,0,0x00C1,0x00050049,0)
        self.assertFalse(r["arm7_dma3"]["enabled_at_pre_menu_snapshot"])
        self.assertFalse(r["arm7_dma3"]["ownership_verified"])
        self.assertTrue(r["arm9"]["timer3_enabled"])
        self.assertTrue(r["arm9"]["timer3_irq_configured"])
        self.assertEqual(r["arm9"]["timer3_prescaler"],64)
        self.assertEqual(r["arm9"]["irq_mask_sources"],[
            "VBlank","Timer 0","Timer 3","IPC sync","IPC receive FIFO"])
        self.assertFalse(r["arm9"]["irq_master_enabled_in_menu"])
        self.assertEqual(r["arm9"]["gameplay_irq_master_state"],"NOT CAPTURED")
        self.assertIn("BLOCKED",r["dswifi_timer3_default_compatibility"])
        self.assertFalse(r["wifi_resident_ready"])

    def test_idle_dma_and_timer_are_not_approval(self):
        r=audit.analyze(0,0,0,0,0,0)
        self.assertFalse(r["wifi_resident_ready"])
        self.assertIn("UNVERIFIED",r["dswifi_timer3_default_compatibility"])

    def test_active_dma_is_reported_not_reassigned(self):
        r=audit.analyze(0x80000000,0x02000000,0x02001000,0,0,1)
        self.assertTrue(r["arm7_dma3"]["enabled_at_pre_menu_snapshot"])
        self.assertFalse(r["arm7_dma3"]["ownership_verified"])
        self.assertFalse(r["wifi_resident_ready"])

    def test_reject_bad_register_values(self):
        for vals in [(-1,0,0,0,0,0),(0,0,0,0x10000,0,0),
                     (0,0,0,0,1<<32,0)]:
            with self.assertRaises(ValueError):
                audit.analyze(*vals)

if __name__=="__main__":
    unittest.main()
