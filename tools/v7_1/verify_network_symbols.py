#!/usr/bin/env python3
"""Verify that Wi-Fi research notes do not authorize unproven in-game calls.

This deliberately reports BLOCKED and exits successfully when no addresses
are published. It fails (nonzero exit) on accidental unsigned/unreviewed
changes to the list of entrypoints.
"""
import json
from pathlib import Path


EXPECTED = {
    "WCM_Init", "WCM_StartupAsync", "WCM_SearchAsync",
    "WCM_ConnectAsync", "WCM_GetPhase", "WCM_PointApList",
    "SOCL_Startup", "SOCL_Socket", "SOCL_Connect",
    "SOCL_Send", "SOCL_Recv", "SOCL_Close",
}


def verify_manifest(path: Path) -> None:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("schema") != 1:
        raise ValueError("Unsupported manifest schema")
    entries = obj.get("functions", [])
    if not isinstance(entries, list):
        raise ValueError("Function entries must be a list")
    names = [entry.get("symbol") for entry in entries]
    if len(names) != len(set(names)) or set(names) != EXPECTED:
        raise ValueError("Incorrect, missing or duplicate WCM/SOCL function names")
    for entry in entries:
        if entry.get("address") is not None or entry.get("residency") != "unverified":
            raise ValueError(
                "Symbol address/residency needs revision-specific proof, a "
                "separate code review and new explicit authorization gate: "
                + str(entry.get("symbol"))
            )
    if not obj.get("blocked_reason"):
        raise ValueError("Research blocker must be recorded")


def main() -> int:
    path = Path(__file__).with_name("network_symbols.json")
    verify_manifest(path)
    print("PASS: HGSS Wi-Fi symbols remain research-only, no in-game calls enabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
