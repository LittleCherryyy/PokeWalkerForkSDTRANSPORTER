"""V8.6 real DSi fixed-word ARM9 alias probe; host-only safety contracts."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
C=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/walker_arm9_wifi_sig.c").read_text()
H=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/include/walker_arm9_wifi_sig.h").read_text()
M=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c").read_text()

class V86LiveAlias(unittest.TestCase):
    def test_v85_alias_arithmetic_is_single_physical_word(self):
        # Actual HGSS original USA Rev0 V8.5 report: +8 load x4;
        # the same absolute word at 167C+44: 1 load and 3 stores.
        self.assertEqual(0x021E16A0+8,0x021E167C+44)
        self.assertEqual(0x021E16A0+4,0x021E16A4)
        self.assertEqual(0x021E16A0+8,0x021E16A8)
        self.assertEqual(0x021E16A4 % 4,0)
        self.assertEqual(0x021E16A8 % 4,0)
        self.assertTrue(0x02000000<=0x021E16A4<0x02400000)
        self.assertTrue(0x02000000<=0x021E16A8<0x02400000)

    def test_snapshot_is_only_two_fixed_reads_after_existing_hgss_guard(self):
        self.assertIn("int walkerArm9ThreadAliasWords(uint32_t out[2]);",H)
        body=C[C.index("int walkerArm9ThreadAliasWords("):]
        for expected in (
            "if (!out) return 0;",
            "out[0]=0u;",
            "out[1]=0u;",
            "#if defined(B4DS) || defined(TWLSDK)",
            "walkerArm9ThreadAvailabilityRaw(&enabled)",
            "enabled!=1u",
            "0x021E16A4u",
            "0x021E16A8u",
            "return 1;",
        ):
            self.assertIn(expected,body)
        self.assertLess(body.index("enabled!=1u"),body.index("0x021E16A4u;"))
        self.assertEqual(body.count("*(const volatile uint32_t *)(uintptr_t)0x021E16A4u"),1)
        self.assertEqual(body.count("*(const volatile uint32_t *)(uintptr_t)0x021E16A8u"),1)
        for forbidden in ("REG_IE =","REG_IME =","WCM_","SOC_","OS_CreateThread(",
                          "OS_WakeupThreadDirect(","walkerWrite(","sharedAddr[",
                          "out[0] = *(const volatile uint32_t *)(uintptr_t)out[1]"):
            self.assertNotIn(forbidden,body)

    def test_known_original_flag_guard_was_not_bypassed(self):
        f=C[C.index("int walkerArm9ThreadAvailabilityRaw("):
            C.index("int walkerArm9ThreadAliasWords(")]
        for word in ("0x020D1AC4u","0xE59F0004u","0xE5900000u",
                     "0xE12FFF1Eu","0x021E1688u"):
            self.assertIn(word,f)
        self.assertNotIn("OS_IsThreadAvailable(",f)

    def test_igm_is_read_only_and_keeps_older_dryrun(self):
        a=M.index("static void walkerArm9WifiCodeMenu(void) {")
        b=M.index("\n#endif\n\nstatic void virtualPokewalkerMenu(void) {",a)
        view=M[a:b]
        for s in ("V8.8 OS LAYOUT 2.X","walkerArm9LegacyThreadInfoWords(words)",
                  "9C:0x","A0:0x","A4:0x","A8:0x","AC:0x","B0:0x",
                  "Wi-Fi: NOT ENABLED","B: Back"):
            self.assertIn(s,view)
        self.assertIn("V7.9 ARM9 DEFERRED",M)
        self.assertIn("L: ARM9 OS raw status",M)
        for forbidden in ("REG_IE =","REG_IME =","OS_CreateThread(",
                          "WCM_StartupAsync(","SOC_Connect(","walkerWrite("):
            self.assertNotIn(forbidden,view)

if __name__=="__main__":
    unittest.main()
