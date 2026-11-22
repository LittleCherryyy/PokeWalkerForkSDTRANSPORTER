"""Actual photographed V7.2.6 words must NOT authorize IRQ_WIFI."""
import importlib.util
from pathlib import Path
import unittest

src=Path(__file__).resolve().parents[2]/"tools/v7_2/analyze_irq_words.py"
spec=importlib.util.spec_from_file_location("irq_word_audit",src)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class V726WordAudit(unittest.TestCase):
    def test_real_20261122_dsi_photo_rejected(self):
        r=mod.analyze(0x0238ECF4,0x02380000,0x000276D8,1,
                      [0xCBA77ABC,0x24285A5F,0xBA84DFC5])
        self.assertEqual(r["slot24_candidate_address"],"0x0238ED54")
        self.assertEqual(r["source"],"cached address")
        self.assertTrue(r["25_slots_fit_image_numerically"])
        for word in r["raw_words"].values():
            self.assertFalse(word["looks_like_ordinary_ntr_code_pointer"])
        self.assertFalse(r["verified_irq_table"])
        self.assertFalse(r["irq_wifi_hook_allowed"])

    def test_plausible_addresses_are_not_verified_handlers(self):
        r=mod.analyze(0x0238ECF4,0x02380000,0x000276D8,3,
                      [0x02380C00,0x037F9001,0x02001100])
        self.assertTrue(r["raw_words_all_look_like_ordinary_code_addresses"])
        self.assertFalse(r["verified_irq_table"])
        self.assertFalse(r["irq_wifi_hook_allowed"])

    def test_fit_alone_does_not_help(self):
        r=mod.analyze(0x0238ECF4,0x02380000,0xECF4+99,1,[0,0,0])
        self.assertFalse(r["25_slots_fit_image_numerically"])
        self.assertFalse(r["irq_wifi_hook_allowed"])

    def test_reject_bad_numbers_and_incomplete_record(self):
        with self.assertRaises(ValueError):
            mod.analyze(0x0238ECF4,0x02380000,0x000276D8,1,[0,0])
        with self.assertRaises(ValueError):
            mod.assess_word(0x100000000)
        with self.assertRaises(ValueError):
            mod.analyze(0x0238ECF5,0x02380000,0x000276D8,1,[0,0,0])

if __name__ == "__main__":
    unittest.main()
