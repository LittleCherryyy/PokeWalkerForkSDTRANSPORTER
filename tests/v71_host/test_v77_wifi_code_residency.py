"""V7.7 source wiring checks: passive ARM9 CRC32 fingerprints, not Wi-Fi.

The user's V7.6 report supplied the five target addresses. CRC reference
numbers are computed offline with a separate exact-ROM identity gate.
"""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SIG=ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/walker_arm9_wifi_sig.c"
UI=ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c"
ADDR=["0x020AD850u","0x020AD9C0u","0x020AE420u",
      "0x020A2EACu","0x020A2F04u"]


class ResidentCodeFingerprintContracts(unittest.TestCase):
    def test_five_exact_verified_target_addresses(self):
        src=SIG.read_text(encoding="utf-8")
        start=src.index("static const uint32_t address[WALKER_WIFI_SIG_COUNT]")
        end=src.index("uint32_t entryMask=0u;",start)
        values=re.findall(r"0x0[0-9A-F]{7}u",src[start:end])
        self.assertEqual(values,ADDR)

    def test_bounded_runtime_scanner_never_starts_radio(self):
        src=SIG.read_text(encoding="utf-8")
        self.assertIn("walkerCrc32Fixed32(p);",src)
        self.assertIn("for(unsigned i=0;i<32;i++)",src)
        self.assertIn("if((first & 0xffff0000u)==0xe92d0000u)",src)
        self.assertIn("a>0x02400000u-32u",src)
        self.assertIn("#ifdef B4DS",src)
        self.assertNotIn("Wifi_Init(",src)
        self.assertNotIn("SOC_Connect(",src)
        self.assertNotIn("REG_IE =",src)
        self.assertNotIn("walkerWrite(",src)
        self.assertNotIn("walkerDirectTransportAvailable",src)
        self.assertNotIn("((void (*",src)

    def test_menu_displays_crc_and_explicit_wifi_disabled_status(self):
        src=UI.read_text(encoding="utf-8")
        start=src.index("static void walkerArm9WifiCodeMenu(void)")
        end=src.index("static void virtualPokewalkerMenu(void)",start)
        snippet=src[start:end]
        self.assertIn("walkerArm9ThreadAvailabilityRaw(&raw)",snippet)
        self.assertIn("printHex(6,4,raw,4",snippet)
        self.assertIn("Wi-Fi: NOT ENABLED",snippet)
        self.assertNotIn("REG_IE =",snippet)
        self.assertNotIn("walkerWrite(",snippet)
        self.assertIn("L: ARM9 OS raw status",src)
        self.assertIn("if(KEYS & KEY_L){showWifiCode=true;break;}",src)
        self.assertIn("walkerArm9WifiCodeMenu();",src)


if __name__=="__main__":
    unittest.main()
