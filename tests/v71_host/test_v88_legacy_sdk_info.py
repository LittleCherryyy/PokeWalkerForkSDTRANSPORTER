"""V8.8 legacy NitroSDK2 OSThreadInfo identity hypothesis; no ROM bytes.

User physical V8.7 evidence:
  0x021E16A0 = 0x00000000, +4 = 0x021E1770,
  +8 = 0x021E3864, +12 = 0x00000000.
Source NitroSDK OS thread.h distinguishes SDK_VERSION_MAJOR >=3,
SDK_THREAD_INFINITY, from the earlier 16-slot layout. HGSS pret
build selects NitroSDK 2.0. Thus another candidate base is A0-4:
  legacy current=base+8=A4, list=base+12=A8,
  switchCallback=base+16=AC, entry[0]=base+20=B0.
These are hypotheses. V8.8 probes two extra *fixed* words after
the V8.3/6/7 guards, without dereferencing any candidate pointer.
"""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SRC=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/walker_arm9_wifi_sig.c").read_text()
HDR=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/include/walker_arm9_wifi_sig.h").read_text()
MENU=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c").read_text()


class LegacyThreadInfoProbe(unittest.TestCase):
    def test_legacy_offsets_are_consistent_with_real_v87_values(self):
        legacy=0x021E169C
        self.assertEqual(legacy+4,0x021E16A0)
        self.assertEqual(legacy+8,0x021E16A4)
        self.assertEqual(legacy+12,0x021E16A8)
        self.assertEqual(legacy+16,0x021E16AC)
        self.assertEqual(legacy+20,0x021E16B0)
        self.assertEqual(0x021E1770%4,0)
        self.assertEqual(0x021E3864%4,0)
        for a in (legacy,legacy+20):
            self.assertTrue(0x02000000<=a<=0x023ffffc)
            self.assertEqual(a%4,0)

    def test_two_new_fixed_words_only_after_verified_v87_snapshot(self):
        self.assertIn("int walkerArm9LegacyThreadInfoWords(uint32_t out[6]);",HDR)
        fn=SRC[SRC.index("int walkerArm9LegacyThreadInfoWords("):]
        for fragment in (
            "if (!out) return 0;",
            "for (unsigned i=0;i<6;i++) out[i]=0u;",
            "#if defined(B4DS) || defined(TWLSDK)",
            "if (!walkerArm9ThreadHeaderWords(middle))",
            "middle[1]!=0x021E1770u",
            "middle[2]!=0x021E3864u",
            "out[0]=*(const volatile uint32_t *)(uintptr_t)0x021E169Cu;",
            "out[5]=*(const volatile uint32_t *)(uintptr_t)0x021E16B0u;",
            "out[1]=middle[0];",
            "out[2]=middle[1];",
            "out[3]=middle[2];",
            "out[4]=middle[3];",
        ):
            self.assertIn(fragment,fn)
        self.assertLess(
            fn.index("middle[2]!=0x021E3864u"),
            fn.index("0x021E169Cu;"),
        )
        self.assertEqual(fn.count("*(const volatile uint32_t *)(uintptr_t)0x021E169Cu"),1)
        self.assertEqual(fn.count("*(const volatile uint32_t *)(uintptr_t)0x021E16B0u"),1)
        for forbidden in (
            "*(const volatile uint32_t *)(uintptr_t)middle[",
            "*(const volatile uint32_t *)(uintptr_t)out[",
            "OS_CreateThread(",
            "OS_WakeupThreadDirect(",
            "WCM_Init(",
            "SOC_Socket(",
            "REG_IE =",
            "REG_IME =",
            "walkerWrite(",
            "sharedAddr[",
        ):
            self.assertNotIn(forbidden,fn)

    def test_v83_and_v86_guards_not_bypassed(self):
        h=SRC[SRC.index("int walkerArm9ThreadHeaderWords("):
              SRC.index("int walkerArm9LegacyThreadInfoWords(")]
        self.assertIn("walkerArm9ThreadAliasWords(pair)",h)
        a=SRC[SRC.index("int walkerArm9ThreadAliasWords("):
              SRC.index("int walkerArm9ThreadHeaderWords(")]
        self.assertIn("walkerArm9ThreadAvailabilityRaw(&enabled)",a)
        self.assertIn("enabled!=1u",a)
        o=SRC[SRC.index("int walkerArm9ThreadAvailabilityRaw("):
              SRC.index("int walkerArm9ThreadAliasWords(")]
        for marker in ("0x020D1AC4u","0xE59F0004u","0xE5900000u",
                       "0xE12FFF1Eu","0x021E1688u"):
            self.assertIn(marker,o)

    def test_six_rows_in_same_small_igm_menu_and_wifi_off(self):
        m=MENU[MENU.index("static void walkerArm9WifiCodeMenu(void) {"):
               MENU.index("\n#endif\n\nstatic void virtualPokewalkerMenu(void) {")]
        for marker in ("V8.8 OS LAYOUT 2.X","walkerArm9LegacyThreadInfoWords(words)",
                       '"9C:0x","A0:0x","A4:0x","A8:0x","AC:0x","B0:0x"',
                       "printHex(7,y,words[i],4", "OS gate FAILED",
                       "Wi-Fi: NOT ENABLED","B: Back"):
            self.assertIn(marker,m)
        self.assertIn("V7.9 ARM9 DEFERRED",MENU)
        self.assertNotIn("OS_CreateThread(",m)
        self.assertNotIn("SOC_Connect(",m)
        self.assertNotIn("REG_IE =",m)
        self.assertNotIn("REG_IME =",m)


if __name__=="__main__":
    unittest.main()
