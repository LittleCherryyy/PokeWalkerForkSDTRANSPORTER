#!/usr/bin/env python3
"""Offline, read-only ARM-state BL callsite inventory for extracted HGSS ARM9.

Does not identify WCM/SOCL functions, patch ROMs, or inspect game saves.
Use on an extracted/decompressed ARM9 binary that you have the right to inspect.
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def sign_extend_24(value: int) -> int:
    value &= 0xFFFFFF
    return value - 0x1000000 if (value & 0x800000) else value


def arm_bl_target(pc: int, opcode: int) -> int | None:
    """Return target of ARM-state conditional BL, excluding BLX-immediate."""
    # bits 27:25 = 101; bit 24 = link; cond 0xF is BLX-immediate, not BL.
    if (opcode & 0x0F000000) != 0x0B000000 or (opcode >> 28) == 0xF:
        return None
    offset = sign_extend_24(opcode) << 2
    return (pc + 8 + offset) & 0xFFFFFFFF


def inventory(data: bytes, base: int) -> dict:
    if base % 4:
        raise ValueError('ARM9 load address must be 4-byte aligned')
    if len(data) < 4 or len(data) % 4:
        raise ValueError('ARM9 binary size must be a nonzero multiple of 4 bytes')
    if base < 0 or base + len(data) > 0x100000000:
        raise ValueError('ARM9 address span exceeds the 32-bit address space')
    counts: Counter[int] = Counter()
    sites: dict[int, list[int]] = {}
    in_span = 0
    outside = 0
    for off in range(0, len(data), 4):
        insn = int.from_bytes(data[off:off + 4], 'little')
        dest = arm_bl_target(base + off, insn)
        if dest is None:
            continue
        if base <= dest < base + len(data) and dest % 4 == 0:
            counts[dest] += 1
            sites.setdefault(dest, []).append(base + off)
            in_span += 1
        else:
            outside += 1
    entries = [{'target': f'0x{t:08X}', 'count': n,
                'callsites': [f'0x{x:08X}' for x in sites[t]]}
               for t, n in sorted(counts.items(), key=lambda p: (-p[1], p[0]))]
    return {'load_address': f'0x{base:08X}', 'size': len(data),
            'arm_bl_in_span': in_span, 'arm_bl_outside_span': outside,
            'candidates': entries,
            'warning': 'Call frequency alone never establishes function identity, API signature, ABI, or safe resident execution.'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arm9', type=Path, help='extracted and decompressed ARM9 image')
    parser.add_argument('--load-address', required=True, type=lambda s: int(s, 0),
                        help='verified RAM load address of this exact ARM9 image, e.g. 0x02000000')
    parser.add_argument('--output', type=Path, help='write JSON inventory to this path (default: stdout)')
    args = parser.parse_args()
    report = inventory(args.arm9.read_bytes(), args.load_address)
    result = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        print(result, end='')


if __name__ == '__main__':
    main()
