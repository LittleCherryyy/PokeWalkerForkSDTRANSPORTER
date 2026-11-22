"""V7.2.2 test: pre-wrapper register handoff must stay on ARM9, no mailbox use.

Static tests do not establish timer IRQ ownership or Wi-Fi readiness.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
CARD=ROOT/"core/bootstrap/retail/cardenginei/arm9/source/cardengine.c"
MENU=ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c"
HEADER=ROOT/"core/bootstrap/retail/common/include/walker_arm9_snapshot.h"

class Arm9PreWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.card=CARD.read_text()
        cls.menu=MENU.read_text()
        cls.header=HEADER.read_text()

    def test_pre_section_arm9_capture_only_read_registers(self):
        c=self.card
        start=c.index("void inGameMenu(s32* exRegisters) {")
        first_critical=c.index("int oldIME = enterCriticalSection();",start)
        region=c[start:first_critical]
        self.assertIn("const WalkerArm9Snapshot preMenu9",region)
        self.assertIn("WALKER_ARM9_SNAPSHOT_MAGIC",region)
        self.assertIn("(u32)TIMER_CR(3)",region)
        self.assertIn("REG_IE",region)
        self.assertIn("REG_IME",region)
        self.assertNotIn("sharedAddr[",region)
        self.assertNotIn("REG_IE =",region)
        self.assertNotIn("TIMER_CR(3) =",region)
        self.assertIn("myIrqHandlerIPC(void)",c)

    def test_abi_handoff_has_matching_fourth_argument(self):
        c=self.card;m=self.menu
        self.assertIn("const WalkerArm9Snapshot *preMenu9",m)
        self.assertIn("const WalkerArm9Snapshot*) =",c)
        self.assertIn("exRegisters, &preMenu9)",c)
        self.assertIn("#if !defined(B4DS) && !defined(TWLSDK)",m)
        self.assertIn("if(preMenu9 && preMenu9->magic == WALKER_ARM9_SNAPSHOT_MAGIC)",m)
        self.assertIn("walkerArm9PreWrapper = *preMenu9;",m)
        self.assertIn("walkerArm9PreWrapper.magic=0u;",m)
        self.assertIn("#define WALKER_ARM9_SNAPSHOT_MAGIC",self.header)
        self.assertIn("u32 timer3;",self.header)
        self.assertIn("u32 ie;",self.header)
        self.assertIn("u32 ime;",self.header)

    def test_ui_clear_irq_context_and_fail_closed(self):
        m=self.menu
        self.assertIn("V7.9 ARM9 DEFERRED",m)
        self.assertIn("the menu enters from IRQ",m)
        self.assertIn("Post+IME:0x",m)
        self.assertIn("Dry run: no network I/O",m)
        self.assertIn("Queued:   0x",m)
        self.assertIn("Done:     0x",m)
        self.assertIn("Wi-Fi: NOT ENABLED",m)
        self.assertIn("A: ARM9 pre-wrapper view",m)
        self.assertIn("KEY_A | KEY_B",m)
        self.assertIn("walkerArm9PreWrapperMenu();",m)
        self.assertNotIn("Wifi_InitDefault(",m)
        self.assertNotIn("socConnect(",m)
        self.assertIn("VIRTUAL POKEWALKER V7.2.6",m)

if __name__=="__main__":
    unittest.main()
