"""V7.7 real-DSi memory code signatures: static fail-closed safety contract.

Inputs are the SHA256s reported by the user's local V7.6 HGSS USA Rev0
ROM auditors. No copyrighted code, ROM, Wi-Fi or save is used in this test.
"""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SIG=ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/walker_arm9_wifi_sig.c"
UI=ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c"
HASHES=[
    "6369f74947b51749f41b1dc42db9f0d10e989d24518127300ea55879176a89fa",
    "20af5f8f43b8fa2f1b7747e115b41bda5a876f3406341dc5ccb78c7f7ac8dac8",
    "50a48e8d3c3605adc7f1e46386654ec05e1a4fa6af163bd40d665126c22f0aff",
    "856fb418640b96d191c34c16da2011da5f10da499fa42eb1785241364b0e3dc0",
    "c0c3988ea2f7f0f199d8a5c393682f1749d129812599aa66611e7aa28f3642ff",
]
ADDR=["0x020AD850u","0x020AD9C0u","0x020AE420u",
      "0x020A2EACu","0x020A2F04u"]


class ResidentCodeSignatureContracts(unittest.TestCase):
    def test_exact_verified_window_digests_and_addresses(self):
        src=SIG.read_text(encoding="utf-8")
        start=src.index("static const uint8_t expected[WALKER_WIFI_SIG_COUNT][32]")
        end=src.index("uint32_t matches=0;",start)
        matrix=src[start:end]
        rows=re.findall(r"\{((?:\s*0x[0-9a-f]{2}\s*,?)+)\}",matrix)
        parsed=["".join(re.findall(r"0x([0-9a-f]{2})",row)) for row in rows]
        self.assertEqual(parsed,HASHES)
        self.assertEqual(re.findall(r"0x0[0-9A-F]{7}u",src[src.index("static const uint32_t location"):start]),ADDR)

    def test_ram_scanner_does_not_enable_wifi_or_mutate_game(self):
        src=SIG.read_text(encoding="utf-8")
        self.assertIn("walkerSha256Fixed32((const volatile uint8_t *)(uintptr_t)addr,digest);",src)
        self.assertIn("return matches;",src)
        self.assertIn("addr > 0x02400000u-32u",src)
        self.assertIn("#ifdef B4DS",src)
        # The reader may compare only; do not ever call the named API address.
        self.assertNotIn("((void (*",src)
        self.assertNotIn("REG_IE =",src)
        self.assertNotIn("Wifi_Init(",src)
        self.assertNotIn("SOC_Connect(",src)

    def test_menu_contains_explicit_no_wifi_gate(self):
        src=UI.read_text(encoding="utf-8")
        start=src.index("static void walkerArm9WifiCodeMenu(void)")
        end=src.index("static void virtualPokewalkerMenu(void)",start)
        snippet=src[start:end]
        self.assertIn("walkerWifiCheckStaticCode();",snippet)
        self.assertIn("Wi-Fi: NOT ENABLED",snippet)
        self.assertIn("No Wi-Fi/ABI proof",snippet)
        self.assertNotIn("REG_IE =",snippet)
        self.assertNotIn("walkerWrite(",snippet)
        self.assertIn("L: ARM9 Wi-Fi code audit",src)
        self.assertIn("if(KEYS & KEY_L){showWifiCode=true;break;}",src)
        self.assertIn("walkerArm9WifiCodeMenu();",src)


if __name__=="__main__":
    unittest.main()
