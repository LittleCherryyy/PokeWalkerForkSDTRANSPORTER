"""V7.1.3 read-only boot outcome source contract checks.
These do not replace real hardware validation or devkitARM compilation.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2] / "core/bootstrap/retail"
def source(path):
    return (ROOT / path).read_text(encoding="utf-8")

class BootOutcomeTests(unittest.TestCase):
    def test_append_only_shared_cardengine_status(self):
        header = source("common/include/cardengine_header_arm7.h")
        asm = source("cardenginei/arm7/source/card_engine_header.s")
        self.assertIn("u32 gen5RomSize;\n\t/* V7.1.3:", header)
        self.assertIn("u32 walkerBootStatus;", header)
        self.assertIn("u32 walkerIrqTableMethod;", header)
        self.assertIn("u32 walkerDirectLockCluster;", header)
        self.assertLess(header.index("u32 walkerIrqBootInstalledIpc;"),
                        header.index("u32 walkerDirectLockCluster;"))
        self.assertRegex(header, r"u32 walkerDirectLockCluster;\s*}\s*cardengineArm7;")
        self.assertLess(header.index("u32 walkerIrqTableMethod;"),
                        header.index("u32 walkerIrqBootOriginalVblank;"))
        self.assertRegex(asm, r"gen5RomSize: \.word 0\n\.global walkerBootStatus\nwalkerBootStatus: \.word 0")
    def test_fail_closed_boot_stages_are_reported(self):
        code = source("bootloaderi/source/arm7/walker_boot.c")
        expected = [
            "WALKER_BOOT_NO_CLUSTER", "WALKER_BOOT_NO_BASE",
            "WALKER_BOOT_READ_SIG", "WALKER_BOOT_WRITE_SIG",
            "WALKER_BOOT_STATUS_SIG", "WALKER_BOOT_INIT_SIG",
            "WALKER_BOOT_FILE_READ", "WALKER_BOOT_INSTALLED",
        ]
        for symbol in expected:
            self.assertIn(symbol, code)
        self.assertLess(code.index("ce7->walkerControl = (u32)c;"),
                        code.index("ce7->walkerBootStatus = WALKER_BOOT_INSTALLED;"))
        self.assertIn("if (!walkerBase || !walkerCluster) return;", code)
    def test_ipc_preserves_status_until_valid_header(self):
        a7 = source("cardenginei/arm7/source/inGameMenu.c")
        a9 = source("cardenginei/arm9_igm/source/inGameMenu.c")
        self.assertIn("sharedAddr[3] = walkerBootStatus;", a7)
        self.assertIn("sharedAddr[3] = c->flushedSeq;", a7)
        self.assertIn("VIRTUAL POKEWALKER V7.2.6", a9)
        self.assertIn("Boot stage: 0x", a9)
        self.assertIn("walkerBootReason(diag[3])", a9)
        self.assertIn("No .walker file selected", a9)
        self.assertIn("IR receive pattern missing", a9)
        self.assertIn("Wi-Fi: NOT ENABLED", a9)
        self.assertNotIn("socConnect(", a9)

if __name__ == "__main__":
    unittest.main()
