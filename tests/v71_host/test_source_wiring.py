"""Static wiring contract checks for the V7.1 DSi NTR cardengine path.

These checks guard integration against accidental removal, but never replace
devkitARM compilation or real-device testing.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
RETAIL = ROOT / "core" / "bootstrap" / "retail"


def read(relative):
    return (RETAIL / relative).read_text(encoding="utf-8")


class DirectSyncWiringTests(unittest.TestCase):
    def test_dsi_loader_is_fail_closed(self):
        code = read("bootloaderi/source/arm7/walker_boot.c")
        hook = code.index("tonccpy(readRange, walkerStub")
        bridge = code.index("walkerDirectBridgeReset(&c->direct, c->flushedSeq)")
        resolver = code.index("walkerResolveNetworkApi(c, ndsHeader)")
        publish = code.index("ce7->walkerControl = (u32)c")
        self.assertTrue(hook < bridge < resolver < publish)

    def test_only_offer_after_verified_flush(self):
        writer = read("cardenginei/arm7/source/walker_file.c")
        self.assertLess(writer.index("gen5CheckedIO("),
                        writer.index("walkerDirectBridgeCommitted(c, seq)"))
        self.assertIn("if (c->writeSeq == seq)", writer)
        bridge = read("cardenginei/arm7/source/walker_direct_bridge.c")
        self.assertIn("c->writeSeq!=seq", bridge)
        self.assertIn("c->flushedSeq!=seq", bridge)
        self.assertIn("if(c->dirty[i]) return", bridge)

    def test_arm7_tick_follows_sd_flush(self):
        engine = read("cardenginei/arm7/source/cardengine.c")
        self.assertLess(engine.index("slot2EmuFlush(false);"),
                        engine.index("walkerDirectBridgeTick();"))
        self.assertIn('#include "walker_direct_bridge_api.h"', engine)

    def test_no_unverified_socket_calls(self):
        resolver = read("common/source/walker_hgss_net.c")
        self.assertNotIn("out->socSocket =", resolver)
        transport = read("cardengine/arm9/source/walker_direct_transport.c")
        self.assertIn("if(!apiComplete(n))", transport)
        self.assertNotIn("SOC_Socket(", transport)


if __name__ == "__main__":
    unittest.main()
