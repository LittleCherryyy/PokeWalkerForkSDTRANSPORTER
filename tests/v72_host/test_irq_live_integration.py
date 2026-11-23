"""V7.2.6 actual source contract: guarded ARM7 reads, no IRQ writes."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]/"core/bootstrap/retail"
A7=ROOT/"cardenginei/arm7/source/inGameMenu.c"
A9=ROOT/"cardenginei/arm9_igm/source/inGameMenu.c"
GUARD=ROOT/"common/include/walker_irq_live_guard.h"

class IrqReadOnlyIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arm7=A7.read_text()
        cls.arm9=A9.read_text()
        cls.guard=GUARD.read_text()

    def test_mmio_and_memory_guard_no_writes(self):
        c=self.arm7
        block=c[c.index("static void walkerIrqPeekReadOnlyDiagnostics(void)"):
                c.index("static u32 radioIeBeforeMenu")]
        self.assertIn("walkerIrqReadOnlyRangeOk(",block)
        self.assertIn("if (safe)",block)
        self.assertIn("entries[0]",block)
        self.assertIn("entries[16]",block)
        self.assertIn("entries[24]",block)
        self.assertIn("const volatile u32* const entries",block)
        self.assertIn("sharedAddr[4] = WALKER_PEEK_REPLY;",block)
        self.assertNotIn("entries[24] =",block)
        self.assertNotIn("Wifi_Init",block)
        self.assertNotIn("REG_IE =",block)
        self.assertNotIn("DMA_CR",block)
        self.assertIn("case WALKER_PEEK_REQUEST:",c)
        self.assertIn("&& sharedAddr[4] != WALKER_PEEK_REPLY",c)

    def test_no_unsafe_external_addresses(self):
        c=self.guard
        for x in ("0x02000000u","0x02400000u","imageBytes",
                  "WALKER_IRQ_25_WORD_BYTES","tableAddr-imageStart"):
            self.assertIn(x,c)
        self.assertNotIn("volatile",c)
        self.assertNotIn("Wifi_",c)
        self.assertNotIn("DMA_",c)

    def test_menu_is_explicitly_candidate_only(self):
        c=self.arm9
        block=c[c.index("static void walkerIrqWordsMenu(void)"):
                c.index("static void walkerIrqTableMenu(void)")]
        for label in ("Slot 0 raw", "Slot16 raw", "Slot24 raw",
                      "Slot24 may NOT be IRQ_WIFI","Raw RAM, NOT handler proof",
                      "Wi-Fi: NOT ENABLED","READ BLOCKED"):
            self.assertIn(label,block)
        self.assertIn("frame<90",block)
        self.assertIn("WPKQ",block)
        self.assertIn("WPKK",block)
        self.assertIn("A: Read bounded IRQ words",c)
        self.assertIn("VIRTUAL POKEWALKER V7.2.6",c)
        self.assertNotIn("*(u32*)",block)

if __name__=="__main__":
    unittest.main()
