"""V7.2.8 source contracts for passive ARM7 callback/bridge counters.

These are static host checks; successful compilation is not evidence that
HeartGold invokes the callbacks on real hardware.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2] / "core/bootstrap/retail"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ResidentHeartbeatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = read("cardenginei/arm7/source/cardengine.c")
        cls.arm7 = read("cardenginei/arm7/source/inGameMenu.c")
        cls.arm9 = read("cardenginei/arm9_igm/source/inGameMenu.c")

    def test_counters_are_passive_in_existing_callback_paths(self):
        s = self.engine
        for decl in (
            "volatile u32 walkerVblankCallbackCount = 0;",
            "volatile u32 walkerBridgeTickCount = 0;",
            "volatile u32 walkerFifoCallbackCount = 0;",
        ):
            self.assertIn(decl, s)
        self.assertIn("void myIrqHandlerVBlank(void) {\n  #ifndef TWLSDK\n  walkerVblankCallbackCount++;", s)
        self.assertIn("void myIrqHandlerFIFO(void) {\n//---------------------------------------------------------------------------------\n#ifndef TWLSDK\n    walkerFifoCallbackCount++;", s)
        self.assertIn("walkerBridgeTickCount++;\n\twalkerDirectBridgeTick();", s)
        self.assertLess(s.index("walkerVblankCallbackCount++;"), s.index("walkerBridgeTickCount++;"))

    def test_bounded_menu_ipc_preserves_reply_until_arm9_receives_it(self):
        a7, a9 = self.arm7, self.arm9
        for expected in (
            "#define WALKER_HEARTBEAT_REQUEST 0x51485057u",
            "#define WALKER_HEARTBEAT_REPLY   0x4B485057u",
            "case WALKER_HEARTBEAT_REQUEST:",
            "sharedAddr[0] = walkerVblankCallbackCount;",
            "sharedAddr[1] = walkerBridgeTickCount;",
            "sharedAddr[2] = walkerFifoCallbackCount;",
            "sharedAddr[3] = walkerControl ? 1u : 0u;",
            "sharedAddr[4] = WALKER_HEARTBEAT_REPLY;",
            "&& sharedAddr[4] != WALKER_HEARTBEAT_REPLY",
            "&& sharedAddr[4] != WALKER_BOOT_SNAPSHOT_REPLY",
        ):
            self.assertIn(expected, a7)
        self.assertIn("walkerReadFourWords(0x51485057u,0x4B485057u,counts)", a9)

    def test_heartbeat_screen_is_safe_and_no_handler_assumptions(self):
        a9 = self.arm9
        section = a9[a9.index("static void walkerHeartbeatMenu(void) {"):
                     a9.index("/* V7.2.6: show raw, bounded ARM7 words.")]
        for label in ("V7.2.8 ARM7 HEARTBEAT", "VBlank calls: 0x",
                      "Bridge ticks: 0x", "IPC callbacks:0x",
                      "No Wi-Fi/IRQ ownership proof", "Wi-Fi: NOT ENABLED"):
            self.assertIn(label, section)
        self.assertNotIn("Wifi_Init(", section)
        self.assertNotIn("REG_IE =", section)
        self.assertNotIn("IRQ_WIFI", section)
        self.assertNotIn("walkerWrite(", section)
        self.assertIn("Y: ARM7 heartbeat counters", a9)
        self.assertIn("walkerHeartbeatMenu();", a9)


if __name__ == "__main__":
    unittest.main()
