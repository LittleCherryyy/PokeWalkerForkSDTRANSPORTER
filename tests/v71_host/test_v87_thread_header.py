"""V8.7 exact-address ARM9 OS header probe; fail-closed source contracts.

Physical V8.6 tests in both a Goldenrod Pokémon Center and Route 35:
+4=0x021E1770 and +8=0x021E3864 with flag=1 in both snapshots.
The probable SDK_THREAD_INFINITY header is not yet identified as a real
OSThreadInfo: code only reads four fixed words, never pointers therein.
"""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SRC=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/walker_arm9_wifi_sig.c").read_text()
HDR=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/include/walker_arm9_wifi_sig.h").read_text()
MENU=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c").read_text()


class V87HeaderProbe(unittest.TestCase):
    def test_v86_user_readings_are_aligned_plausible_ram_not_proven_objects(self):
        for addr in (0x021E1770,0x021E3864):
            self.assertEqual(addr%4,0)
            self.assertTrue(0x02000000<=addr<=0x023ffffc)
        self.assertEqual(0x021E16A0+0,0x021E16A0)
        self.assertEqual(0x021E16A0+4,0x021E16A4)
        self.assertEqual(0x021E16A0+8,0x021E16A8)
        self.assertEqual(0x021E16A0+12,0x021E16AC)

    def test_read_only_header_stays_inside_four_fixed_words(self):
        self.assertIn("int walkerArm9ThreadHeaderWords(uint32_t out[4]);",HDR)
        start=SRC.index("int walkerArm9ThreadHeaderWords(")
        fn=SRC[start:]
        for snippet in (
            "if (!out) return 0;",
            "out[0]=0u;","out[1]=0u;","out[2]=0u;","out[3]=0u;",
            "#if defined(B4DS) || defined(TWLSDK)",
            "if (!walkerArm9ThreadAliasWords(pair))",
            "0x021E16A0u","0x021E16ACu",
            "out[1]=pair[0];","out[2]=pair[1];",
        ):
            self.assertIn(snippet,fn)
        self.assertEqual(
            fn.count("*(const volatile uint32_t *)(uintptr_t)0x021E16A0u"),1)
        self.assertEqual(
            fn.count("*(const volatile uint32_t *)(uintptr_t)0x021E16ACu"),1)
        self.assertNotIn("*(const volatile uint32_t *)(uintptr_t)pair",fn)
        for forbidden in ("REG_IE =","REG_IME =","OS_CreateThread(",
                          "OS_WakeupThreadDirect(","WCM_","SOC_",
                          "walkerWrite(","sharedAddr["):
            self.assertNotIn(forbidden,fn)
        self.assertLess(
            fn.index("if (!walkerArm9ThreadAliasWords(pair))"),
            fn.index("0x021E16A0u;")
        )

    def test_prior_v83_abi_opcode_guard_still_required(self):
        helper=SRC[SRC.index("int walkerArm9ThreadAliasWords("):
                   SRC.index("int walkerArm9ThreadHeaderWords(")]
        self.assertIn("walkerArm9ThreadAvailabilityRaw(&enabled)",helper)
        self.assertIn("enabled!=1u",helper)
        gate=SRC[SRC.index("int walkerArm9ThreadAvailabilityRaw("):
                 SRC.index("int walkerArm9ThreadAliasWords(")]
        for expected in ("0x020D1AC4u","0xE59F0004u","0xE5900000u",
                         "0xE12FFF1Eu","0x021E1688u"):
            self.assertIn(expected,gate)

    def test_screen_keeps_four_raw_values_and_no_radio(self):
        a=MENU.index("static void walkerArm9WifiCodeMenu(void) {")
        b=MENU.index("\n#endif\n\nstatic void virtualPokewalkerMenu(void) {",a)
        v=MENU[a:b]
        for text in ("V8.7 ARM9 OS HEADER","walkerArm9ThreadHeaderWords(words)",
                     "A0+0:0x","A0+4:0x","A0+8:0x","A0+C:0x",
                     "OS gate FAILED","Wi-Fi: NOT ENABLED","B: Back"):
            self.assertIn(text,v)
        self.assertIn("V7.9 ARM9 DEFERRED",MENU)
        self.assertNotIn("OS_WakeupThreadDirect(",v)
        self.assertNotIn("OS_CreateThread(",v)
        self.assertNotIn("SOC_",v)
        self.assertNotIn("REG_IE =",v)
        self.assertNotIn("REG_IME =",v)


if __name__=="__main__":
    unittest.main()
