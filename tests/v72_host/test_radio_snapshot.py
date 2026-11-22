"""Static checks for the V7.2 pre-menu register-snapshot diagnostic.
Only hardware can establish actual IRQ/timer values. This test ensures
the snapshot path is read-only and that requests/replies match.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
ARM7 = ROOT / "core/bootstrap/retail/cardenginei/arm7/source/inGameMenu.c"
ARM9 = ROOT / "core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c"

class RadioSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arm7=ARM7.read_text()
        cls.arm9=ARM9.read_text()

    def test_arm7_capture_prior_to_interrupt_pause(self):
        s=self.arm7
        m=s[s.index("void inGameMenu(void) {"):s.index("loadInGameMenu();",s.index("void inGameMenu(void) {"))]
        self.assertLess(m.index("radioIeBeforeMenu=REG_IE;"),m.index("enterCriticalSection();"))
        self.assertLess(m.index("radioImeBeforeMenu=REG_IME;"),m.index("enterCriticalSection();"))
        self.assertLess(m.index("TIMER_CR(i);"),m.index("enterCriticalSection();"))
        self.assertIn("radioTimersBeforeMenu[4]",s)
        self.assertNotIn("Wifi_Init",m)
        self.assertNotIn("REG_IE =",m)
        self.assertNotIn("TIMER_CR(i) =",m)

    def test_snapshot_reads_only_and_has_explicit_ack(self):
        s=self.arm7
        m=s[s.index("static void walkerRadioReadOnlyDiagnostics"):s.index("static void walkerReadOnlyDiagnostics")]
        self.assertIn("sharedAddr[4]=WALKER_RADIO_REPLY;",m)
        self.assertIn("radioIeBeforeMenu",m)
        self.assertIn("radioTimersBeforeMenu",m)
        self.assertNotRegex(m,r"Wifi_|Wcm|SOCL|socket\(")
        self.assertIn("case WALKER_RADIO_REQUEST:",s)
        self.assertIn("&& sharedAddr[4] != WALKER_RADIO_REPLY",s)

    def test_command_and_reply_consistent(self):
        a7=self.arm7;a9=self.arm9
        self.assertIn("0x44525057u /* WPRD */",a7)
        self.assertIn("0x4B525057u /* WPRK */",a7)
        self.assertIn("sharedAddr[4]=0x44525057u; /* WPRD */",a9)
        self.assertIn("if(response==0x4B525057u)",a9)
        self.assertIn("frames<90",a9)
        self.assertIn("V7.2 ARM7 IRQ/TIMER SNAPSHOT",a9)
        self.assertIn("Captured before menu pause",a9)
        self.assertIn("IRQ ownership NOT verified",a9)
        self.assertIn("Wi-Fi: NOT ENABLED",a9)
        self.assertIn("VIRTUAL POKEWALKER V7.2.2",a9)

if __name__=="__main__":
    unittest.main()
