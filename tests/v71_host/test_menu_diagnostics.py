"""Source-level safety contracts for the DSi in-game diagnostic handshake.

The actual ARM7/ARM9 shared-memory protocol must still be compiled with
devkitARM and validated on hardware; these tests catch mismatched command
IDs, accidental writes, and unbounded wait regressions.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
ARM7 = ROOT / "core/bootstrap/retail/cardenginei/arm7/source/inGameMenu.c"
ARM9 = ROOT / "core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c"

def command(source, name):
    match = re.search(r"^\s*#define\s+" + re.escape(name) + r"\s+(0x[0-9A-Fa-f]+)u", source, re.M)
    if not match:
        raise AssertionError("Missing command " + name)
    return int(match.group(1), 16)

class MenuDiagnosticTests(unittest.TestCase):
    def test_handshake_command_ids(self):
        a7, a9 = ARM7.read_text(), ARM9.read_text()
        self.assertEqual(command(a7, "WALKER_DIAG_REQUEST"), command(a9, "WALKER_DIAG_REQUEST"))
        self.assertEqual(command(a7, "WALKER_DIAG_REPLY"), command(a9, "WALKER_DIAG_REPLY"))
        self.assertNotEqual(command(a7, "WALKER_DIAG_REQUEST"), command(a7, "WALKER_DIAG_REPLY"))
        self.assertEqual(command(a9, "WALKER_DIAG_MENU"), 0x554E454D)

    def test_arm7_reply_is_read_only(self):
        source = ARM7.read_text()
        begin = source.index("static void walkerReadOnlyDiagnostics(void)")
        end = source.index("#endif", begin)
        function = source[begin:end]
        self.assertIn("walkerControlAddressReadable(address)", function)
        self.assertIn("if(address) sharedAddr[0] |= 2u;", function)
        self.assertIn("sharedAddr[0] |= 4u;", function)
        self.assertIn("c->magic==WALKER_MAGIC", function)
        self.assertIn("c->version==WALKER_VERSION", function)
        self.assertIn("walkerHgssNetMissingMask(&c->hgssNet)", function)
        self.assertIn("sharedAddr[4] = WALKER_DIAG_REPLY;", function)
        # No storage, bridge-state, or network writes in the diagnostic handler.
        self.assertNotRegex(function, r"c->\w+\s*(?<![=!<>])=(?!=)")
        self.assertNotIn("fileWrite(", function)
        self.assertNotIn("SOC_", function)
        self.assertIn("sharedAddr[4] != WALKER_DIAG_REPLY", source)

    def test_arm9_timeout_and_unconditional_disabled_status(self):
        source = ARM9.read_text()
        begin = source.index("static void virtualPokewalkerMenu(void)")
        end = source.index("static void optionsMenu(", begin)
        view = source[begin:end]
        self.assertIn("frames<90", view)
        self.assertIn("WALKER_DIAG_REQUEST", view)
        self.assertIn("WALKER_DIAG_REPLY", view)
        self.assertIn("sharedAddr[4]=WALKER_DIAG_MENU;", view)
        self.assertIn("Wi-Fi: NOT ENABLED", view)
        self.assertIn("Missing net APIs: 0x", view)
        self.assertIn("Walker: hook not published", view)
        self.assertIn("Walker: RAM addr rejected", view)
        self.assertIn("Walker: invalid header", view)
        self.assertNotIn("socConnect(", view)
        self.assertNotIn("wifiInit(", view)

if __name__ == "__main__":
    unittest.main()
