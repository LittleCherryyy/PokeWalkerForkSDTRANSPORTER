#!/usr/bin/env python3
"""Read-only integration audit for V7.1 source tree.

The 88-byte transport wire format is proven on Android and DSi standalone.
This audit checks the *separate* resident bootstrap path; it cannot certify
ROM compatibility or runtime Wi-Fi, and never modifies saves or source files.
"""
import argparse
import json
from pathlib import Path


def inspect(root: Path) -> dict:
    def read(path: str) -> str:
        return (root / path).read_text(encoding="utf-8")
    common = "core/bootstrap/retail/"
    control = read(common + "common/include/walker_emu.h")
    arm9 = read(common + "cardengine/arm9/source/walker_direct_transport.c")
    net = read(common + "common/source/walker_hgss_net.c")
    bridge = read(common + "cardenginei/arm7/source/walker_direct_bridge.c")
    boot = read(common + "bootloaderi/source/arm7/walker_boot.c")
    resolver = read(common + "bootloaderi/source/arm7/walker_net_resolve.c")
    igm = read(common + "cardenginei/arm9_igm/source/inGameMenu.c")
    build = read(common + "cardenginei/arm9/Makefile")
    # Count call sites outside a function's own declaration/definition.
    def invoked(fn: str, sources: list[str]) -> bool:
        import re
        for source in sources:
            # Intentionally conservative text heuristic, not a linker result.
            for line in source.splitlines():
                line = line.split("//", 1)[0]
                if line.lstrip().startswith(("void " + fn, "int " + fn,
                                             "bool " + fn, "extern ")):
                    continue
                if re.search(r"\b" + re.escape(fn) + r"\s*\(", line):
                    return True
        return False

    checks = {
        "shared_control_declares_direct": "WalkerDirectBridge direct;" in control,
        "shared_control_declares_net_api": "WalkerHgssNetApi hgssNet;" in control,
        "arm9_transport_has_live_network_calls": (
            "socConnect(" in arm9 and "socSend(" in arm9 and "socRecv(" in arm9
        ),
        "bootloader_calls_network_resolver": invoked(
            "walkerResolveNetworkApi", [boot]
        ),
        "resolver_defines_network_api": "void walkerResolveNetworkApi(" in resolver,
        "bridge_uses_placeholder_backend": (
            "__attribute__((weak)) bool walkerDirectTransportAvailable" in bridge
        ),
        "igm_reports_network_not_ready": "Wi-Fi in game: NOT READY" in igm,
        "dsi_arm9_build_includes_runtime_transport_source": (
            "../../common/source " in build or
            "walker_direct_transport.c" in build
        ),
        "resolver_explicitly_disabled": "out->ready = 0;" in net,
        "resolver_does_not_guess_gateway": "out->soclGatewayPtr=" not in net
          and "out->soclGatewayPtr =" not in net,
        "resolver_uses_wcm_search_name": "wcmSearchAsync" in control,

    }
    requirements = {
        "shared_layout_ready": (
            checks["shared_control_declares_direct"]
            and checks["shared_control_declares_net_api"]
        ),
        "resident_transport_ready": (
            checks["arm9_transport_has_live_network_calls"]
            and checks["bootloader_calls_network_resolver"]
            and checks["dsi_arm9_build_includes_runtime_transport_source"]
            and not checks["bridge_uses_placeholder_backend"]
        ),
        "resolver_ready": False,  # no vetted runtime resolver exists yet
    }
    return {
        "safety": {
            "network_fail_closed": checks["resolver_explicitly_disabled"],
            "gateway_not_guessed": checks["resolver_does_not_guess_gateway"],
        },
        "status": "RESIDENT_NETWORK_BLOCKED" if not all(requirements.values())
                  else "STATIC_GATES_CANDIDATE_ONLY",
        "checks": checks,
        "requirements": requirements,
        "notice": (
            "Static source inspection cannot prove Wi-Fi operation in HGSS. "
            "Even a passing static gate requires toolchain/link/ABI review "
            "and console validation before transfers are enabled."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path,
                    default=Path(__file__).resolve().parents[2])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = inspect(args.root)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("V7.1 " + result["status"])
        for name, ok in result["requirements"].items():
            print(("READY" if ok else "BLOCKED") + ": " + name)
        for name, ok in result["safety"].items():
            print(("PASS" if ok else "UNSAFE") + ": " + name)
        print(result["notice"])
    # Always 0: an investigation with blocked gates is an expected result,
    # not a CI failure. Never present it as a passed in-game test.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
