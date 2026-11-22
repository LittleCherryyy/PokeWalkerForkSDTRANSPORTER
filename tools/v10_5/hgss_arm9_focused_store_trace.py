#!/usr/bin/env python3
"""V10.5 — summarize HGSS V10.4 emulator trace and generate store-only ARM9 GDB probes.

Read-only analysis and script generation. No ROM, save, or emulator is opened.
The optional GDB script, when run manually, observes original instruction PCs.
A hit confirms execution of that PC in melonDS only, not DSi networking.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

STORES = (
    ("A_STORE", 0x020D18A4),
    ("B_STORE", 0x020D2034),
    ("C_STORE", 0x020D20D4),
)
BASE = "pw_v105_arm9_stores"
LOG = BASE + ".log"
TAG_PATTERN = re.compile(r"\btag=([A-Z0-9_]+)\b")


def summarize_v104(text: str) -> str:
    tags = Counter()
    for line in text.splitlines():
        if line.startswith("PW_V104_HIT "):
            match = TAG_PATTERN.search(line)
            if match:
                tags[match.group(1)] += 1
    out = [
        "V10.4 logged hits: " + str(sum(tags.values())),
        "V10.4 hit limit reached: " + str("PW_V104_LIMIT_REACHED" in text),
    ]
    for name in (
        "A_ENTRY_ALT", "A_BXNE_LR", "A_STORE",
        "B_ENTRY", "B_CALL", "B_BYPASS", "B_STORE",
        "C_ENTRY", "C_CALL", "C_BYPASS", "C_STORE",
    ):
        out.append(f"{name}: {tags[name]}")
    if not tags:
        out.append("WARNING: no V10.4 hit lines; check the log path.")
    out.append(
        "Interpretation: hits prove emulator reached listed ARM9 PCs only. "
        "No-hit is inconclusive, especially when a limit was reached."
    )
    return "\n".join(out)


def script(port: int, max_hits: int, already_connected: bool) -> str:
    if not 1 <= port <= 65535:
        raise ValueError("invalid ARM9 GDB port")
    if not 1 <= max_hits <= 1000:
        raise ValueError("max_hits must be 1..1000")
    lines = [
        "# V10.5 melonDS ARM9 original ROM store-only trace; never a DSi Wi-Fi proof.",
        "set confirm off",
        "set pagination off",
        "set architecture arm",
        "set logging overwrite on",
        f"set logging file {LOG}",
        "set logging enabled on",
        "set $pw_v105_hits = 0",
    ]
    if already_connected:
        lines.append(
            f'printf "PW_V105_EXISTING_CONNECTION arm9_port={port}\\n"'
        )
    else:
        lines.extend(
            [
                f"target remote localhost:{port}",
                f'printf "PW_V105_CONNECTED arm9_port={port}\\n"',
            ]
        )
    for name, addr in STORES:
        lines.extend(
            [
                f"break *0x{addr:08X}",
                "commands",
                "  silent",
                "  set $pw_v105_hits = $pw_v105_hits + 1",
                (
                    f'  printf "PW_V105_STORE tag={name} site=0x{addr:08X} '
                    'hit=%u pc=0x%08x cpsr=0x%08x '
                    'r0=0x%08x r1=0x%08x r2=0x%08x r3=0x%08x '
                    'r7=0x%08x r8=0x%08x lr=0x%08x sp=0x%08x\\n", '
                    '$pw_v105_hits, $pc, $cpsr, $r0, $r1, $r2, $r3, '
                    '$r7, $r8, $lr, $sp'
                ),
                "  x/i $pc",
                f"  if $pw_v105_hits >= {max_hits}",
                '    printf "PW_V105_LIMIT_REACHED - disabling trace breakpoints\\n"',
                "    disable breakpoints",
                "    set logging enabled off",
                "  end",
                "  continue",
                "end",
            ]
        )
    lines.extend(
        ['printf "PW_V105_BREAKPOINTS_READY\\n"', "continue"]
    )
    return "\n".join(lines) + "\n"


def generate(output: Path, port: int, max_hits: int) -> None:
    output.mkdir(parents=True, exist_ok=True)
    original = script(port, max_hits, False)
    attached = script(port, max_hits, True)
    (output / (BASE + ".gdb")).write_text(original, encoding="utf-8")
    (output / (BASE + "_attached.gdb")).write_text(attached, encoding="utf-8")
    manifest = {
        "version": "v10.5",
        "target": "melonDS ARM9 only",
        "purpose": "target store PCs without frequent entry/call/bypass probes",
        "breakpoints": [
            {"tag": name, "pc": f"0x{pc:08X}"} for name, pc in STORES
        ],
        "max_total_hits": max_hits,
        "logs_to": LOG,
        "original_rom_and_save_modified": False,
        "runtime_DSi_or_in_game_WiFi_proven": False,
    }
    (output / "pw_v105_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (output / "README_v105.txt").write_text(
        "V10.5 focused HGSS ARM9 emulator trace\n\n"
        "1. Optionally summarize the prior V10.4 log with --summarize-v104 PATH.\n"
        "2. Reboot melonDS with GDB stub ARM9 and test-copy USA Rev0 ROM/save.\n"
        "3. Start ARM-capable GDB from output folder; first connect manually:\n"
        f"   target remote localhost:{port}\n"
        "   info registers pc\n"
        f"4. Keep the connection: source {BASE}_attached.gdb\n"
        f"5. Read {LOG} after reaching Pokewalker menu; this records only\n"
        "   A_STORE, B_STORE, C_STORE PCs, not hot-path entry/call hits.\n"
        "The attached script NEVER reconnects. The alternate .gdb script\n"
        "connects by itself in a fresh GDB session. Do not use both scripts.\n"
        "Do not run GDB on a real DSi. No Wi-Fi, IR, Android or ROM patches.\n"
        "An emulator store hit still does NOT prove the field written or\n"
        "that a thread or in-game Wi-Fi bridge is present.\n",
        encoding="utf-8",
    )


def self_test() -> None:
    a = script(3333, 96, True)
    b = script(3333, 96, False)
    assert a.count("\nbreak *") == 3
    assert "target remote localhost" not in a
    assert "target remote localhost:3333" in b
    assert "PW_V105_STORE tag=C_STORE" in a
    assert "pw_v105_arm9_stores.log" in a
    s = summarize_v104(
        "PW_V104_HIT tag=C_ENTRY hit=1\n"
        "PW_V104_HIT tag=C_STORE hit=2\n"
        "PW_V104_LIMIT_REACHED\n"
    )
    assert "C_ENTRY: 1" in s and "C_STORE: 1" in s
    print("V10.5 synthetic generation and log-summary self-test: PASS")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--summarize-v104", type=Path)
    p.add_argument("--output-dir", type=Path)
    p.add_argument("--arm9-port", type=int, default=3333)
    p.add_argument("--max-hits", type=int, default=96)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    try:
        if args.self_test:
            self_test()
        if args.summarize_v104:
            print(summarize_v104(
                args.summarize_v104.read_text(encoding="utf-8", errors="replace")
            ))
        if args.output_dir:
            generate(args.output_dir, args.arm9_port, args.max_hits)
            print("V10.5 focused GDB scripts created:", args.output_dir)
        if not (args.self_test or args.summarize_v104 or args.output_dir):
            p.error("choose --self-test, --summarize-v104 and/or --output-dir")
        return 0
    except (OSError, ValueError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
