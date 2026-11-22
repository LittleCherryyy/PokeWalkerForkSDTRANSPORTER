"""V8.3 no-radio ARM9 scheduler flag read — fail-closed source contracts.

The original user's V8.2 HG/SS report showed:
  OS_IsThreadAvailable at 0x020D1AC4;
  static word at 0x020D1AD0 is 0x021E1688;
  the function loads the word once and returns it.

No ARM9 game RAM can be tested on host, so this checks the narrow
instruction guard and B4DS-disabled C probe; cross-build checks real ARM.
"""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
C=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/walker_arm9_wifi_sig.c").read_text()
H=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/include/walker_arm9_wifi_sig.h").read_text()
MENU=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c").read_text()

class LiveSchedulerGuard(unittest.TestCase):
    def test_exact_original_opcode_and_literal_guard(self):
        f=C[C.index("int walkerArm9ThreadAvailabilityRaw("):]
        for needle in (
            "if (!out) return 0;",
            "*out = 0u;",
            "#if defined(B4DS) || defined(TWLSDK)",
            "0x020D1AC4u",
            "code[0] != 0xE59F0004u",
            "code[1] != 0xE5900000u",
            "code[2] != 0xE12FFF1Eu",
            "code[3] != 0x021E1688u",
            "candidate < 0x02000000u",
            "candidate > 0x02400000u - 4u",
        ):
            self.assertIn(needle,f)
        # Only one target RAM word is read after all instructions match.
        self.assertLess(f.index("code[3] != 0x021E1688u"),f.index("const uint32_t candidate"))
        self.assertLess(f.index("candidate > 0x02400000u - 4u"),
                        f.index("*out = *(const volatile uint32_t *)(uintptr_t)candidate;"))
        self.assertEqual(f.count("*(const volatile uint32_t *)(uintptr_t)candidate"),1)
        self.assertNotIn("REG_IE =",f)
        self.assertNotIn("REG_IME =",f)
        self.assertNotIn("OS_CreateThread(",f)
        self.assertNotIn("OS_IsThreadAvailable(",f)
        self.assertNotIn("WCM_",f)
        self.assertNotIn("SOC_",f)
        self.assertNotIn("walkerWrite(",f)
        self.assertNotIn("sharedAddr[",f)

    def test_runtime_display_remains_read_only(self):
        self.assertIn("int walkerArm9ThreadAvailabilityRaw(uint32_t *out);",H)
        start=MENU.index("static void walkerArm9WifiCodeMenu(void) {")
        end=MENU.index("\n#endif\n\nstatic void virtualPokewalkerMenu(void) {",start)
        view=MENU[start:end]
        self.assertIn("V8.6 ARM9 THREAD RAM",view)
        self.assertIn("walkerArm9ThreadAvailabilityRaw(&raw)",view)
        self.assertIn("OS:0x",view)
        self.assertIn("OS guard FAILED",view)
        self.assertIn("walkerArm9ThreadAliasWords(words)",view)
        self.assertIn("Wi-Fi: NOT ENABLED",view)
        self.assertIn("V7.9 ARM9 DEFERRED",MENU)
        self.assertNotIn("REG_IE =",view)
        self.assertNotIn("REG_IME =",view)
        self.assertNotIn("OS_CreateThread(",view)

if __name__=="__main__":
    unittest.main()
