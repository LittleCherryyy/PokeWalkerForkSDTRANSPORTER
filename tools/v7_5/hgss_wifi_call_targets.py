#!/usr/bin/env python3
"""Read-only HGSS wireless call-target proof from published overlay callsites.

The published pret/pokeheartgold US disassembly labels five exact callsites:
- overlay 72 Thumb WCM_GetPhase   @ 0x02237E0C
- overlay 13 Thumb WCM_Init       @ 0x02223712
- overlay 13 Thumb WCM_StartupAsync @ 0x02223736
- overlay 39 ARM   SOC_Socket     @ 0x02229AE8
- overlay 39 ARM   SOC_Connect    @ 0x02229C5C

The tool validates actual instruction encodings and known neighboring opcodes
against *the user's own unmodified ROM*, decodes the immediate BL target and
classifies the target region. A BL may target a linker veneer, not the API.
This research tool NEVER executes/patches game code, produces game bytes, or
authorizes Wi-Fi/IRQ operations.

Sources: github.com/pret/pokeheartgold asm/overlay_72.s,
asm/overlay_13_thumb_2.s, lib/NitroDWC/asm/overlay_39_arm.s.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
V74 = HERE.parent / "v7_4" / "arm9_runtime_reconstruction.py"
spec = importlib.util.spec_from_file_location("v74_callsite", V74)
v74 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v74)

SITES = (
    ("WCM_GetPhase", 72, "thumb", 0x02237E0C, 0x2809),
    ("WCM_Init", 13, "thumb", 0x02223712, 0x2800),
    ("WCM_StartupAsync", 13, "thumb", 0x02223736, 0x2803),
    ("SOC_Socket", 39, "arm", 0x02229AE8, 0xE3A02000),
    ("SOC_Connect", 39, "arm", 0x02229C5C, 0xE1A01006),
)
MAX_OVERLAY_IMAGE = 0x200000


class CallsiteError(ValueError):
    pass


def thumb_call(h1, h2, pc):
    """ARMv5 Thumb-1 BL, BLX(imm), *no* Thumb-2 J1/J2 encoding."""
    if (h1 & 0xF800) != 0xF000:
        raise CallsiteError("not a Thumb-1 BL/BLX high halfword")
    second = h2 & 0xF800
    if second not in (0xF800, 0xE800):
        raise CallsiteError("not a Thumb-1 BL/BLX low halfword")
    delta = ((((h1 & 0x7FF) << 11) | (h2 & 0x7FF)) << 1)
    if delta & 0x400000:
        delta -= 0x800000
    if second == 0xE800:
        if h2 & 1:
            raise CallsiteError("invalid Thumb BLX(imm) reserved low bit")
        return (((pc + 4) & ~3) + delta) & 0xFFFFFFFF, "ARM (BLX)"
    return (pc + 4 + delta) & 0xFFFFFFFF, "Thumb (BL)"


def arm_bl(word, pc):
    """ARM-state unconditional BL branch target. Reject conditional/BLX."""
    if (word & 0xFF000000) != 0xEB000000:
        raise CallsiteError("not an unconditional ARM BL")
    imm = word & 0x00FFFFFF
    if imm & 0x00800000:
        imm -= 0x01000000
    return (pc + 8 + (imm << 2)) & 0xFFFFFFFF, "ARM (BL)"


def get_overlay(f, h, fat, rom_size, overlay_id):
    table_at, table_bytes = struct.unpack_from("<II", h, 0x50)
    v74._v73.require_range(rom_size, table_at, table_bytes, "ARM9 overlay table")
    if table_bytes == 0 or table_bytes % 32 or table_bytes > 32 * 2048:
        raise CallsiteError("invalid ARM9 overlay table")
    table = v74._v73.read_exact(f, table_at, table_bytes, "ARM9 overlay table")
    matches = []
    for i in range(table_bytes // 32):
        values = struct.unpack_from("<8I", table, 32 * i)
        if values[0] == overlay_id:
            matches.append(values)
    if len(matches) != 1:
        raise CallsiteError(f"expected one overlay {overlay_id}, found {len(matches)}")
    (_id, ram, declared_ram, bss, sinit_start, sinit_end, file_id, flags) = matches[0]
    if file_id >= len(fat) // 8:
        raise CallsiteError("overlay references invalid FAT ID")
    first, end = struct.unpack_from("<II", fat, file_id * 8)
    if end < first or end - first == 0:
        raise CallsiteError("overlay empty/invalid file range")
    v74._v73.require_range(rom_size, first, end-first, "overlay file")
    if declared_ram == 0 or declared_ram > MAX_OVERLAY_IMAGE:
        raise CallsiteError("overlay RAM length unreasonable")
    encoded = v74._v73.read_exact(f, first, end-first, "overlay image")
    packed = bool(flags & 0x01000000)
    if packed:
        if len(encoded) >= declared_ram:
            raise CallsiteError("compressed overlay not smaller than RAM image")
        try:
            runtime, info = v74.decompress_backwards(encoded, ram + len(encoded), ram)
        except v74.BLZError as exc:
            raise CallsiteError(str(exc)) from exc
    else:
        runtime = encoded
        info = {"growth_bytes": 0}
    if len(runtime) != declared_ram:
        raise CallsiteError(f"overlay {overlay_id} decoded to unexpected size")
    return ram, runtime, {
        "overlay_id": overlay_id,
        "packed": packed,
        "packed_bytes": len(encoded),
        "declared_runtime_bytes": declared_ram,
        "unpacked_bytes": len(runtime),
        "bss_bytes": bss,
        "expansion_bytes": info["growth_bytes"],
    }


def region_of(addr, main_load, main_len, overlays):
    p = addr & ~1
    if main_load <= p < main_load + main_len:
        return "ARM9 static executable range (not ABI-verified)"
    for number, (load, img, _) in overlays.items():
        if load <= p < load + len(img):
            return f"overlay {number} (could be a veneer; not resident-verified)"
    if 0x02000000 <= p < 0x02400000:
        return "DS main RAM other area (unverified)"
    return "outside ordinary DS main RAM (unverified)"


def resolve_site(image, load, name, pc, instruction_set, neighbor):
    offset = pc - load
    if offset < 0 or offset + 4 > len(image):
        raise CallsiteError(name + " callsite is outside overlay RAM")
    if instruction_set == "thumb":
        if offset & 1 or offset + 6 > len(image):
            raise CallsiteError("unaligned or truncated Thumb callsite")
        lo, hi, next_halfword = struct.unpack_from("<HHH", image, offset)
        if next_halfword != neighbor:
            raise CallsiteError(name + ": documented post-call cmp does not match")
        target, mode = thumb_call(lo, hi, pc)
    else:
        if offset & 3 or offset < 4:
            raise CallsiteError("unaligned/truncated ARM callsite")
        prev = struct.unpack_from("<I", image, offset - 4)[0]
        if prev != neighbor:
            raise CallsiteError(name + ": documented pre-call instruction does not match")
        target, mode = arm_bl(struct.unpack_from("<I", image, offset)[0], pc)
    return {"name": name, "caller_address": f"0x{pc:08X}",
            "decoded_immediate_target": f"0x{target:08X}",
            "target_mode": mode, "neighbor_opcode_validated": True,
            "target_is_callable_wifi_api": False,
            "note": "Immediate BL destination may be a linker veneer, not the final API."}


def analyze(path):
    # Verifies exact full-image SHA1 and a validated BLZ ARM9 static image.
    report = v74.reconstruct(path)
    main = report["arm9"]
    main_load = int(main["ram_load"], 16)
    main_length = main["runtime_reconstructed_bytes"]
    rom_size = report["image_bytes"]
    overlays = {}
    with Path(path).open("rb") as f:
        h = v74._v73.read_exact(f, 0, 0x200, "NDS header")
        fat_at, fat_bytes = struct.unpack_from("<II", h, 0x48)
        if fat_bytes == 0 or fat_bytes % 8 or fat_bytes > 65536 * 8:
            raise CallsiteError("invalid NDS FAT size")
        v74._v73.require_range(rom_size, fat_at, fat_bytes, "FAT")
        fat = v74._v73.read_exact(f, fat_at, fat_bytes, "FAT")
        for ov_id in (13, 39, 72):
            overlays[ov_id] = get_overlay(f, h, fat, rom_size, ov_id)
    resolved = []
    for name, overlay_id, mode, pc, neighbor in SITES:
        load, image, _ = overlays[overlay_id]
        entry = resolve_site(image, load, name, pc, mode, neighbor)
        destination = int(entry["decoded_immediate_target"], 16)
        entry["target_region"] = region_of(destination, main_load, main_length, overlays)
        resolved.append(entry)
    return {
        "tool": "hgss-wifi-callsite-audit-v7.5",
        "game_code": report["game_code"],
        "reference_rom_sha1": report["image_sha1"],
        "arm9_runtime_sha256": main["runtime_decompressed_sha256"],
        "arm9_static_bytes": main_length,
        "overlays": {str(i): ov[2] for i, ov in overlays.items()},
        "callsites": resolved,
        "wifi_abi_verified": False,
        "resident_wifi_ready": False,
        "function_execution_allowed": False,
        "physical_dsi_android_ping_verified": False,
        "security": "The program only reads local unmodified ROM; no game bytes are exported, and no Wi-Fi or saves are touched.",
        "next_gate": "Resolve linker veneers; verify final ABI and loaded-code residency before any actual WCM/SOC call.",
    }


def compare_reports(first, second):
    """Compare exactly HG+SS without treating matching addresses as an ABI proof."""
    codes = {first["game_code"], second["game_code"]}
    if codes != {"IPKE", "IPGE"}:
        raise CallsiteError("compare mode requires one original US HeartGold and one SoulSilver")
    if first["arm9_static_bytes"] != second["arm9_static_bytes"]:
        raise CallsiteError("ARM9 runtime sizes differ; address mapping cannot be assumed")
    by_game = {first["game_code"]: first, second["game_code"]: second}
    hg = {x["name"]: x for x in by_game["IPKE"]["callsites"]}
    ss = {x["name"]: x for x in by_game["IPGE"]["callsites"]}
    if set(hg) != set(ss) or len(hg) != len(first["callsites"]) or len(ss) != len(second["callsites"]):
        raise CallsiteError("callsite lists are incomplete or contain duplicates")
    pairs = []
    for name in sorted(hg):
        a = hg[name]
        b = ss[name]
        if a["caller_address"] != b["caller_address"]:
            raise CallsiteError(name + " has inconsistent public callsite location")
        same = a["decoded_immediate_target"] == b["decoded_immediate_target"]
        pairs.append({
            "name": name,
            "public_callsite": a["caller_address"],
            "heartgold_immediate_target": a["decoded_immediate_target"],
            "soulsilver_immediate_target": b["decoded_immediate_target"],
            "same_immediate_target": same,
            "target_region_heartgold": a["target_region"],
            "target_region_soulsilver": b["target_region"],
            "verified_callable_wifi_api": False,
        })
    return {
        "tool": "hgss-wifi-cross-title-callsite-audit-v7.5",
        "games": by_game,
        "comparisons": pairs,
        "same_targets": sum(1 for x in pairs if x["same_immediate_target"]),
        "total_sites": len(pairs),
        "wifi_abi_verified": False,
        "function_execution_allowed": False,
        "physical_dsi_to_android_ping_verified": False,
        "next_gate": "Resolve code veneers and cross-check the final network API ABI before enabling resident wireless.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path, help="Exact, original US HGSS .nds backup")
    parser.add_argument("--compare", type=Path, help="Second exact US HGSS .nds for cross-title comparison")
    parser.add_argument("--output", type=Path, help="Metadata-only JSON output")
    args = parser.parse_args(argv)
    try:
        if args.output and (args.output.resolve() == args.rom.resolve()
                            or (args.compare and args.output.resolve() == args.compare.resolve())):
            raise CallsiteError("refusing to overwrite source ROM")
        if args.compare:
            if args.rom.resolve() == args.compare.resolve():
                raise CallsiteError("two different HGSS ROMs are required")
            data = compare_reports(analyze(args.rom), analyze(args.compare))
        else:
            data = analyze(args.rom)
        payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        print(payload, end="")
        return 0
    except (ValueError, OSError, struct.error) as e:
        print("ERROR: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
