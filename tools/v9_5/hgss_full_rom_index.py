#!/usr/bin/env python3
"""V9.5 — full-ROM metadata/index audit for original HGSS USA Rev0 dumps.

Reads every byte of each supplied ROM, validates partition tables, inventories
NitroFS and overlay tables, and scans whole ARM binaries for static reference
candidates. Uses the project's original ARM9 reconstruction and verification
chain. No game data, executable bytes, saves, or Pokemon records are exported.
Static patterns do not establish actual execution, scheduler ABI or Wi-Fi.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
TARGETS = (0x021E169C, 0x021E16A0, 0x021E16A4, 0x021E16A8,
           0x021E16AC, 0x021E16B0)
PROHIBITED = {".nds", ".sav", ".dsv", ".srm", ".walker", ".dat"}
MAX_ITEMS = 20000
MAX_XREFS = 1500

def u32(data, off):
    if off < 0 or off + 4 > len(data):
        raise ValueError(f"out-of-bounds word at {off:#x}")
    return struct.unpack_from("<I", data, off)[0]

def hx(v): return f"0x{v:08X}"

def section(rom, off, size, label):
    if off < 0 or size < 0 or off > len(rom) or size > len(rom) - off:
        raise ValueError(f"{label} is outside ROM")
    return rom[off:off + size]

def header(rom):
    if len(rom) < 0x200:
        raise ValueError("invalid/truncated NDS header")
    game_code = rom[12:16].decode("ascii", "replace")
    if game_code not in ("IPKE", "IPGE"):
        raise ValueError("expected an original USA HeartGold/SoulSilver ROM")
    parts = {}
    for key, off in (("arm9", 0x20), ("arm7", 0x30)):
        parts[key] = {"offset": u32(rom, off), "entry": u32(rom, off + 4),
                      "load": u32(rom, off + 8), "size": u32(rom, off + 12)}
        section(rom, parts[key]["offset"], parts[key]["size"], key)
    for key, off in (("fnt", 0x40), ("fat", 0x48),
                     ("arm9_overlays", 0x50), ("arm7_overlays", 0x58)):
        parts[key] = {"offset": u32(rom, off), "size": u32(rom, off + 4)}
        section(rom, parts[key]["offset"], parts[key]["size"], key)
    parts["game_code"] = game_code
    parts["rom_size"] = len(rom)
    parts["rom_sha1"] = hashlib.sha1(rom).hexdigest()
    return parts

def fat_index(rom, h):
    off, size = h["fat"]["offset"], h["fat"]["size"]
    if size % 8: raise ValueError("invalid FAT size")
    if size // 8 > MAX_ITEMS: raise ValueError("too many FAT entries")
    out = []
    for fid in range(size // 8):
        start, end = struct.unpack_from("<II", rom, off + fid * 8)
        if end < start: raise ValueError("inverted FAT file extent")
        section(rom, start, end - start, f"FAT entry {fid}")
        out.append({"id": fid, "offset": hx(start), "size": end - start})
    return out

def fnt_names(rom, h, file_count):
    off, size = h["fnt"]["offset"], h["fnt"]["size"]
    blob = section(rom, off, size, "FNT")
    if len(blob) < 8: return {}, {"status": "empty_or_short"}
    count = struct.unpack_from("<H", blob, 6)[0]
    if count < 1 or count > 4096 or count * 8 > len(blob):
        return {}, {"status": "invalid_directory_table"}
    entries = [struct.unpack_from("<IHH", blob, i * 8) for i in range(count)]
    names = {}
    visited = set()
    def visit(index, prefix, depth):
        if index in visited or depth > 32: return
        visited.add(index)
        position, fid, _ = entries[index]
        steps = 0
        while position < len(blob) and steps < 100000:
            steps += 1
            marker = blob[position]; position += 1
            if marker == 0: break
            length = marker & 0x7f
            if position + length > len(blob): break
            name = blob[position:position + length].decode("ascii", "replace")
            position += length
            if marker & 0x80:
                if position + 2 > len(blob): break
                directory = struct.unpack_from("<H", blob, position)[0]
                position += 2
                child = directory & 0xfff
                if child < count: visit(child, prefix + name + "/", depth + 1)
            else:
                if fid < file_count: names[fid] = prefix + name
                fid += 1
    visit(0, "", 0)
    return names, {"status": "parsed", "directory_count": count,
                   "visited_directories": len(visited),
                   "named_files": len(names)}

def overlay_index(rom, h, key, fat):
    p = h[key]
    if p["size"] % 32: raise ValueError("invalid overlay table size")
    rows = []
    for pos in range(p["offset"], p["offset"] + p["size"], 32):
        oid, ram, memsize, bss, init_start, init_end, fid, reserved = (
            struct.unpack_from("<8I", rom, pos))
        rows.append({"id": oid, "ram_address": hx(ram),
                     "ram_size": memsize, "bss_size": bss,
                     "file_id": fid, "file_size": fat[fid]["size"] if fid < len(fat) else None,
                     "fat_entry_valid": fid < len(fat)})
    return rows

def scan_refs(blob, base, key):
    """Syntactic A32 candidates only; arbitrary data may resemble instructions."""
    counts = Counter()
    refs = []
    branches = 0
    literal_loads = 0
    for offset in range(0, len(blob) - 3, 4):
        word = struct.unpack_from("<I", blob, offset)[0]
        pc = base + offset
        if (word >> 28) == 14 and (word & 0x0E500000) == 0x04100000 and (
             (word >> 16) & 15) == 15:
            # ARM literal LDR, immediate pre-index, no writeback.
            literal_loads += 1
            imm = word & 0xfff
            effective = pc + 8 + (imm if word & (1 << 23) else -imm)
            lo = effective - base
            if lo >= 0 and lo + 4 <= len(blob) and lo % 4 == 0:
                value = u32(blob, lo)
                if value in TARGETS and len(refs) < MAX_XREFS:
                    refs.append({"pc": hx(pc), "target": hx(value),
                                 "literal_pc": hx(effective), "kind": "ldr_literal"})
                    counts[hx(value)] += 1
        if (word >> 28) == 14 and ((word >> 25) & 7) == 5:
            branches += 1
    # Count raw values separately; they may be numbers/data, not references.
    raw_counts = {hx(target): sum(1 for offset in range(0, len(blob)-3, 4)
                                 if u32(blob, offset) == target) for target in TARGETS}
    return {"segment": key, "base": hx(base), "size": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "potential_al_branch_opcodes": branches,
            "potential_al_ldr_literal_opcodes": literal_loads,
            "candidate_pointer_constants": raw_counts,
            "candidate_literal_xref_counts": dict(counts),
            "candidate_literal_xrefs": refs,
            "note": "A32 syntactic matches only, including possible false positives"}

def analyze(path, v92):
    rom = path.read_bytes()
    h = header(rom)
    previous = v92.analyze_game(path)  # exact-ROM verification chain
    if previous["original_rom_sha1"] != h["rom_sha1"]:
        raise ValueError("original ROM digest/verification mismatch")
    fat = fat_index(rom, h)
    names, fnt_meta = fnt_names(rom, h, len(fat))
    arm9_overlays = overlay_index(rom, h, "arm9_overlays", fat)
    arm7_overlays = overlay_index(rom, h, "arm7_overlays", fat)
    meta, arm9 = v92.v90.v75.v74.reconstruct(path, include_runtime_image=True)
    if hashlib.sha256(arm9).hexdigest() != previous["original_runtime_sha256"]:
        raise ValueError("reconstructed ARM9 digest mismatch")
    arm7 = section(rom, h["arm7"]["offset"], h["arm7"]["size"], "ARM7")
    indexed_bytes = sum(x["size"] for x in fat)
    paths = [{"id": f["id"], "path": names.get(f["id"]),
              "size": f["size"], "offset": f["offset"]} for f in fat]
    return {"game_code": h["game_code"], "rom_size": len(rom),
            "rom_sha1": h["rom_sha1"],
            "header": {k:v for k,v in h.items() if k not in ("rom_sha1",)},
            "nitrofs": {"files": paths, "file_count": len(paths),
                        "total_file_payload_bytes": indexed_bytes, "fnt": fnt_meta},
            "overlays": {"arm9": arm9_overlays, "arm7": arm7_overlays},
            "arm9_runtime": scan_refs(arm9, h["arm9"]["load"], "arm9_runtime"),
            "arm7_raw": scan_refs(arm7, h["arm7"]["load"], "arm7_raw"),
            "full_rom_scanned_bytes": len(rom),
            "execution_verified": False}

def compare(hg, ss):
    games = {hg["game_code"]:hg, ss["game_code"]:ss}
    if set(games) != {"IPKE", "IPGE"}:
        raise ValueError("requires one IPKE and one IPGE original ROM")
    a, b = games["IPKE"], games["IPGE"]
    af = {f["path"] for f in a["nitrofs"]["files"] if f["path"] is not None}
    bf = {f["path"] for f in b["nitrofs"]["files"] if f["path"] is not None}
    return {"tool": "hgss-v9.5-full-rom-static-index",
            "heartgold": a, "soulsilver": b,
            "comparison": {"shared_nitrofs_paths": len(af & bf),
                           "heartgold_only_paths": len(af - bf),
                           "soulsilver_only_paths": len(bf - af),
                           "arm9_runtime_hash_equal":
                              a["arm9_runtime"]["sha256"] == b["arm9_runtime"]["sha256"],
                           "arm7_raw_hash_equal":
                              a["arm7_raw"]["sha256"] == b["arm7_raw"]["sha256"]},
            "static_analysis_only": True, "runtime_path_verified": False,
            "actual_scheduler_abi_proven": False,
            "safe_to_create_worker_thread": False,
            "wifi_resident_verified": False,
            "rom_or_save_modified": False,
            "next_gate": "Use whole-ROM index and verified ARM9/overlay analysis to narrow candidate functions; prove runtime paths before Wi-Fi."}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("heartgold", type=Path)
    parser.add_argument("soulsilver", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        inputs = [args.heartgold.resolve(), args.soulsilver.resolve()]
        if inputs[0] == inputs[1]: raise ValueError("need two distinct original ROMs")
        if args.output and (args.output.resolve() in inputs or
                            args.output.suffix.lower() in PROHIBITED):
            raise ValueError("refusing to overwrite ROM/save-like output")
        dep = HERE.parent/"v9_2"/"hgss_store_value_backtrace.py"
        spec = importlib.util.spec_from_file_location("v95_v92", dep)
        if spec is None or spec.loader is None: raise ValueError("V9.2 dependency missing")
        v92 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v92)
        result = compare(analyze(args.heartgold,v92), analyze(args.soulsilver,v92))
        output = json.dumps(result,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
            print(f"Indexed both original ROMs into {args.output}")
        else:
            print(output, end="")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
