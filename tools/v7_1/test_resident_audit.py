import tempfile
import unittest
from pathlib import Path
from resident_audit import inspect

PREFIX = "core/bootstrap/retail/"


def sources(root, **overrides):
    content = {
        "common/include/walker_emu.h": "typedef struct WalkerControl { unsigned magic; } WalkerControl;",
        "cardengine/arm9/source/walker_direct_transport.c":
            "void walkerDirectTransportTickArm9(void) { /* no sockets */ }",
        "common/source/walker_hgss_net.c":
            "int walkerResolveHgssNet(void) { return 1; }",
        "cardenginei/arm7/source/walker_direct_bridge.c":
            "__attribute__((weak)) bool walkerDirectTransportAvailable(void) { return false; }",
        "bootloaderi/source/arm7/walker_boot.c":
            "void walkerBoot(void) {}",
        "bootloaderi/source/arm7/walker_net_resolve.c":
            "void walkerResolveNetworkApi(void) {}",
        "cardenginei/arm9_igm/source/inGameMenu.c":
            "Wi-Fi in game: NOT READY",
        "cardenginei/arm9/Makefile": "SOURCES := source source_ext",
    }
    content.update(overrides)
    for name, value in content.items():
        target = root / PREFIX / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8")


class ResidentAuditTests(unittest.TestCase):
    def test_unwired_sources_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources(root)
            report = inspect(root)
        self.assertEqual(report["status"], "RESIDENT_NETWORK_BLOCKED")
        self.assertFalse(report["requirements"]["shared_layout_ready"])
        self.assertFalse(report["requirements"]["resident_transport_ready"])
        self.assertFalse(report["requirements"]["resolver_ready"])
        self.assertTrue(report["checks"]["bridge_uses_placeholder_backend"])

    def test_resolver_definition_alone_is_not_callsite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources(root)
            report = inspect(root)
        self.assertFalse(report["checks"]["bootloader_calls_network_resolver"])
        self.assertTrue(report["checks"]["resolver_defines_network_api"])

    def test_gate_detection_is_only_static(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources(root, **{
                "common/include/walker_emu.h":
                    "WalkerDirectBridge direct; WalkerHgssNetApi hgssNet;",
                "cardengine/arm9/source/walker_direct_transport.c":
                    "socConnect(fd); socSend(fd); socRecv(fd);",
                "common/source/walker_hgss_net.c":
                    "out->wcmInit = 1; out->socSocket = 2;",
                "cardenginei/arm7/source/walker_direct_bridge.c":
                    "bool walkerDirectTransportAvailable(void) { return true; }",
                "bootloaderi/source/arm7/walker_boot.c":
                    "walkerResolveNetworkApi(c, h);",
                "cardenginei/arm9/Makefile":
                    "SOURCES := source ../../common/source ",
            })
            report = inspect(root)
        self.assertTrue(all(report["requirements"].values()))
        self.assertEqual(report["status"], "STATIC_GATES_CANDIDATE_ONLY")


if __name__ == "__main__":
    unittest.main()
