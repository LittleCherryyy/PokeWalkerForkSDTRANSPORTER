"""V7.8 passive ARM9 ROM callback context checks. Not a Wi-Fi test.

Reviews source invariants while the device-specific toolchain is checked by
the separate full cross-build. No game/phone data or IRQ writes involved.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2] / "core/bootstrap/retail"
ARM9 = ROOT / "cardenginei/arm9/source/cardengine.c"
MENU = ROOT / "cardenginei/arm9_igm/source/inGameMenu.c"
SNAP = ROOT / "common/include/walker_arm9_snapshot.h"


class Arm9TaskContextTests(unittest.TestCase):
    def test_snapshot_append_only_abi_and_consistent_producer(self):
        header = SNAP.read_text()
        fields = re.findall(r"\bu32 (\w+);", header)
        self.assertEqual(fields[:4], ["magic", "timer3", "ie", "ime"])
        self.assertEqual(fields[4:], [
            "romReadCalls", "eligibleReadCalls", "lastReadCpsrMode",
            "lastReadIme", "postReadEligibleCalls", "dryRunQueued",
            "dryRunDone", "dryRunPending"])
        arm9 = ARM9.read_text()
        self.assertIn("walkerArm9RomReadCalls,", arm9)
        self.assertIn("walkerArm9EligibleReadCalls,", arm9)
        self.assertIn("walkerArm9LastReadCpsrMode,", arm9)
        self.assertIn("walkerArm9LastReadIme", arm9)
        self.assertIn("exRegisters, &preMenu9", arm9)
        menu = MENU.read_text()
        self.assertIn("walkerArm9PreWrapper = *preMenu9;", menu)

    def test_context_sampling_occurs_at_rom_read_entry_before_critical_section(self):
        source = ARM9.read_text()
        card = source.index("void cardRead(u32* cacheStruct")
        end = source.index("enableIPC_SYNC();", card)
        code = source[card:end]
        self.assertIn('walkerArm9GetCpsrMode();', code)
        self.assertIn('__attribute__((target("arm"),noinline))', source)
        self.assertIn('mrs %0, cpsr', source)
        self.assertIn('REG_IME & 1u', code)
        self.assertIn('mode == 0x10u || mode == 0x13u || mode == 0x1fu', code)
        self.assertIn('walkerArm9EligibleReadCalls++', code)
        self.assertNotIn('Wifi_Init(', code)
        self.assertNotIn('SOC_Connect(', code)
        self.assertNotIn('REG_IE =', code)
        self.assertEqual(source.count(
            "#if !defined(TWLSDK) && !defined(B4DS) && !defined(DLDI) && !defined(GSDD)"),4)
        self.assertIn("const WalkerArm9Snapshot*)0", source)
        self.assertIn("#if defined(DLDI) || defined(GSDD)", source)
        self.assertIn("#if !defined(TWLSDK) && !defined(DLDI) && !defined(GSDD)", source)

        self.assertNotIn('walkerWrite(', code)
        self.assertLess(code.index('walkerArm9GetCpsrMode();'), code.index('initialize();'))

    def test_diagnostic_is_read_only_and_wifi_stays_disabled(self):
        source = MENU.read_text()
        menu = source[
            source.index("static void walkerArm9PreWrapperMenu(void)"):
            source.index("static void walkerRadioResourcesMenu(void)")
        ]
        self.assertIn("romReadCalls", menu)
        self.assertIn("postReadEligibleCalls", menu)
        self.assertIn("dryRunQueued", menu)
        self.assertIn("dryRunDone", menu)
        self.assertIn("Dry run: no network I/O", menu)
        self.assertIn("Wi-Fi: NOT ENABLED", menu)
        self.assertNotIn("WCM_Init(", menu)
        self.assertNotIn("REG_IE =", menu)
        self.assertNotIn("walkerWrite(", menu)
        self.assertIn("R: ARM9 task context", source)
        self.assertIn("if(KEYS & KEY_R){showTaskContext=true;break;}", source)
        self.assertIn("walkerArm9PreWrapperMenu();", source)


if __name__ == "__main__":
    unittest.main()
