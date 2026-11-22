"""V7.2.9: reject confusing a working resident callback with Wi-Fi.

This test validates source contracts and observed hardware counters; it does
not pretend to exercise DSi Wi-Fi or prove Android connectivity.
"""
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC = BASE / "core/bootstrap/retail"


class TransportReadinessTests(unittest.TestCase):
    def test_physical_heartbeat_evidence_has_matching_deltas(self):
        first = {"vblank": 0x5BD, "bridge": 0x5BC, "ipc": 0x6BC8}
        second = {"vblank": 0xB15, "bridge": 0xB14, "ipc": 0xE0B2}
        self.assertEqual(second["vblank"] - first["vblank"], 1368)
        self.assertEqual(second["bridge"] - first["bridge"], 1368)
        self.assertEqual(first["vblank"] - first["bridge"], 1)
        self.assertEqual(second["vblank"] - second["bridge"], 1)
        self.assertEqual(second["ipc"] - first["ipc"], 29930)

    def test_existing_bridge_polls_only_if_backend_reports_available(self):
        code = (SRC / "cardenginei/arm7/source/walker_direct_bridge.c").read_text()
        self.assertIn("bool walkerDirectTransportAvailable(void) { return false; }", code)
        self.assertIn("if(!walkerDirectTransportAvailable()) return;", code)
        self.assertLess(code.index("if(!walkerDirectTransportAvailable()) return;"),
                        code.index("switch(c->direct.state)"))
        self.assertIn("if(!durableImageStable(c,crcSeq)) return;", code)

    def test_unresolved_hgss_wifi_abi_remains_fail_closed(self):
        resolver = (SRC / "common/source/walker_hgss_net.c").read_text()
        self.assertIn("memset(out, 0, sizeof(*out));", resolver)
        self.assertIn("out->ready = walkerHgssNetMissingMask(out) == 0u;", resolver)
        self.assertNotIn("out->ready = 1;", resolver)

    def test_heartbeat_is_not_radio_writes(self):
        menu = (SRC / "cardenginei/arm7/source/inGameMenu.c").read_text()
        excerpt = menu[menu.index("static void walkerHeartbeatReadOnlyDiagnostics(void)"):
                       menu.index("static void walkerIrqTableReadOnlyDiagnostics(void)")]
        self.assertIn("walkerVblankCallbackCount", excerpt)
        self.assertIn("walkerBridgeTickCount", excerpt)
        self.assertNotIn("REG_IE =", excerpt)
        self.assertNotIn("Wifi_Init", excerpt)


if __name__ == "__main__":
    unittest.main()
