"""V7.2.1 static contract: DMA3 captured before pause; ARM9 values are menu-only.
No runtime hardware availability can be inferred from these tests.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
ARM7=ROOT/"core/bootstrap/retail/cardenginei/arm7/source/inGameMenu.c"
ARM9=ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c"

class Dma3SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a7=ARM7.read_text()
        cls.a9=ARM9.read_text()

    def test_capture_precedes_irq_mask(self):
        s=self.a7
        begin=s.index("void inGameMenu(void) {")
        end=s.index("enterCriticalSection();",begin)
        capture=s[begin:end]
        for register in ("DMA_CR(3)","DMA_SRC(3)","DMA_DEST(3)"):
            self.assertIn(register,capture)
        self.assertIn("radioDma3BeforeMenu",capture)
        self.assertNotIn("Wifi_Init",capture)
        self.assertNotIn("DMA_CR(3) =",capture)
        self.assertNotIn("DMA_SRC(3) =",capture)
        self.assertNotIn("DMA_DEST(3) =",capture)

    def test_ipc_capture_does_not_modify_dma(self):
        a=self.a7
        start=a.index("static void walkerResourceReadOnlyDiagnostics")
        end=a.index("static void walkerRadioReadOnlyDiagnostics",start)
        function=a[start:end]
        self.assertIn("sharedAddr[0]=radioDma3BeforeMenu[0];",function)
        self.assertIn("sharedAddr[1]=radioDma3BeforeMenu[1];",function)
        self.assertIn("sharedAddr[2]=radioDma3BeforeMenu[2];",function)
        self.assertIn("sharedAddr[4]=WALKER_RESOURCE_REPLY;",function)
        self.assertIn("case WALKER_RESOURCE_REQUEST:",a)
        self.assertIn("&& sharedAddr[4] != WALKER_RESOURCE_REPLY",a)
        self.assertNotIn("REG_IE =",function)
        self.assertNotIn("DMA_CR",function)
        self.assertNotIn("Wifi_",function)

    def test_arm9_snapshot_separates_menu_context(self):
        s=self.a9
        start=s.index("static void walkerRadioResourcesMenu")
        end=s.index("static void walkerRadioSnapshotMenu",start)
        block=s[start:end]
        self.assertIn("const u16 arm9Timer3AtMenu=TIMER_CR(3);",block)
        self.assertIn("const u32 arm9IeAtMenu=REG_IE;",block)
        self.assertIn("const u32 arm9ImeAtMenu=REG_IME;",block)
        self.assertIn("sharedAddr[4]=0x44535057u; /* WPSD */",block)
        self.assertIn("if(response==0x4B535057u)",block)
        self.assertIn("ARM9 TMR3 (menu)",block)
        self.assertIn("DMA3 not enabled at snapshot",block)
        self.assertIn("No IRQ/DMA ownership proof",block)
        self.assertIn("Wi-Fi: NOT ENABLED",block)
        self.assertNotIn("Wifi_Init",block)
        self.assertNotIn("TIMER_CR(3) =",block)
        self.assertIn("Y: DMA3 + ARM9 snapshot",s)
        self.assertIn("VIRTUAL POKEWALKER V7.2.5",s)

if __name__=="__main__":
    unittest.main()
