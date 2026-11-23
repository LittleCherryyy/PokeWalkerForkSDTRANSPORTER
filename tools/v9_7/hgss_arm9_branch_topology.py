#!/usr/bin/env python3
"""V9.7 — read-only candidate ARM9 branch/call topology around V9.6 sites.

Full reconstructed ARM9 A32 scan; records direct B/BL candidates, nearby
branch targets, and approximate function-entry prologues. The scanner treats
every aligned word as *potential* code and cannot prove execution or ABI.
It uses the existing V9.2 original-ROM verification and V9.6 xref guard.
No ROM, save, .walker, or nds-bootstrap writes; no radio operations.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
CONDITIONS = ("eq","ne","cs","cc","mi","pl","vs","vc","hi","ls",
              "ge","lt","gt","le","al","nv")
FORBIDDEN_OUTPUT = {".nds", ".sav", ".dsv", ".srm", ".walker", ".dat"}
WINDOW_BEFORE = 0x60
WINDOW_AFTER = 0x30
PROLOGUE_BEFORE = 0x600
MAX_EDGE_EXPORT = 64
MAX_PROLOGUES = 4
MAX_CALL_EXPORT = 24

def hx(n: int) -> str:
    return f"0x{n:08X}"

def read_word(img: bytes, base: int, pc: int) -> int:
    offset = pc - base
    if pc & 3 or offset < 0 or offset + 4 > len(img):
        raise ValueError("invalid ARM9 instruction read")
    return struct.unpack_from("<I", img, offset)[0]

def direct_branch(word: int, pc: int):
    """Only A32 B/BL with condition EQ..AL (never BLX immediate)."""
    cond = word >> 28
    if cond == 15 or ((word >> 25) & 7) != 5:
        return None
    disp = word & 0xffffff
    if disp & 0x800000:
        disp -= 1 << 24
    to = (pc + 8 + (disp << 2)) & 0xffffffff
    return {"source_pc": hx(pc), "target_pc": hx(to),
            "kind": "BL" if word & (1 << 24) else "B",
            "condition": CONDITIONS[cond]}

def prologue(word: int):
    """Heuristic A32 AL stack-save; neither unique nor complete."""
    if (word & 0xffff4000) == 0xe92d4000:
        return "stmdb_sp_save_lr"
    if word == 0xe52de004:
        return "str_lr_predecrement_sp"
    return None

def collect_branches(image: bytes, base: int):
    end = base + len(image)
    out = []
    indirect = 0
    thumb_or_blx_not_modeled = 0
    for offset in range(0, len(image) - 3, 4):
        pc = base + offset
        w = struct.unpack_from("<I", image, offset)[0]
        b = direct_branch(w, pc)
        if b:
            target = int(b["target_pc"], 16)
            b["target_in_ARM9_image"] = base <= target < end
            out.append(b)
        elif (w & 0x0ffffff0) in (0x012fff10, 0x012fff30):
            indirect += 1
        elif (w >> 28) == 15 and ((w >> 25) & 7) == 5:
            thumb_or_blx_not_modeled += 1
    out.sort(key=lambda r: (int(r["target_pc"], 16),
                            int(r["source_pc"], 16)))
    return out, {"a32_branch_candidates": len(out),
                 "branch_register_syntax_candidates": indirect,
                 "blx_immediate_syntax_candidates": thumb_or_blx_not_modeled,
                 "branches_outside_ARM9_image": sum(
                     not b["target_in_ARM9_image"] for b in out),
                 "all_results_syntactic_only": True}

def nearby_edges(sorted_edges, targets, low, high):
    i, j = bisect_left(targets, low), bisect_right(targets, high)
    matched = sorted_edges[i:j]
    return {"total_candidates": len(matched),
            "truncated": len(matched) > MAX_EDGE_EXPORT,
            "edges": matched[:MAX_EDGE_EXPORT]}

def locate_prologues(image, base, site_pc, sorted_edges, targets):
    first = max(base, site_pc - PROLOGUE_BEFORE)
    prior = []
    for pc in range(first + ((-first) & 3), site_pc + 1, 4):
        kind = prologue(read_word(image, base, pc))
        if kind:
            i, j = bisect_left(targets, pc), bisect_right(targets, pc)
            calls = [edge for edge in sorted_edges[i:j] if edge["kind"] == "BL"]
            prior.append({
                "candidate_entry_pc": hx(pc),
                "prologue_syntax": kind,
                "distance_bytes_to_access": site_pc - pc,
                "inbound_direct_BL_candidates": len(calls),
                "direct_BL_sources": [c["source_pc"] for c in calls[:MAX_CALL_EXPORT]],
                "BL_source_list_truncated": len(calls) > MAX_CALL_EXPORT,
                "is_verified_function_start": False
            })
    prior.sort(key=lambda r: r["distance_bytes_to_access"])
    return {"candidate_count_in_search_window":len(prior),
            "closest_candidates": prior[:MAX_PROLOGUES],
            "search_window_bytes": PROLOGUE_BEFORE,
            "entry_and_ownership_proven": False}

def inspect(image, base, sites):
    branches, stats = collect_branches(image, base)
    targets = [int(b["target_pc"], 16) for b in branches]
    records = []
    for row in sites:
        pc = int(row["following_access_pc"], 16)
        if pc < base or pc + 4 > base + len(image) or pc & 3:
            raise ValueError("V9.6 access PC out of bounds")
        low = max(base, pc - WINDOW_BEFORE)
        high = min(base + len(image) - 4, pc + WINDOW_AFTER)
        records.append({
            "literal_load_pc": row["literal_load_pc"],
            "access_pc": row["following_access_pc"],
            "effective_address": row["effective_address"],
            "access": row["access"],
            "width": row["width"],
            "nearby_direct_B_BL_targets": nearby_edges(branches,targets,low,high),
            "possible_function_entries": locate_prologues(
                image,base,pc,branches,targets),
            "instruction_reached_at_runtime": False,
            "call_graph_proven": False,
        })
    return {"branch_scan":stats, "records":records, "records_count":len(records)}

def analyze(rom, v96, v92):
    original = v96.analyze(rom,v92)
    meta,image = v92.v90.v75.v74.reconstruct(rom,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"] != original["arm9_runtime_sha256"]:
        raise ValueError("original runtime ARM9 SHA-256 does not match")
    base = int(meta["arm9"]["ram_load"],16)
    result = inspect(image,base,original["interesting_effective_address_sites"])
    if result["records_count"] != original["interesting_site_count"]:
        raise ValueError("V9.6 verified access count changed")
    return {"game_code":original["game_code"],
            "rom_sha1":original["rom_sha1"],
            "arm9_runtime_sha256":original["arm9_runtime_sha256"],
            "original_v90_anchors_confirmed": len(original["original_v90_anchors"]),
            "verified_v96_effective_access_count":original["interesting_site_count"],
            **result}

def comparison(a,b):
    by = {a["game_code"]:a,b["game_code"]:b}
    if set(by) != {"IPKE","IPGE"}:
        raise ValueError("original HeartGold IPKE and SoulSilver IPGE required")
    hg,ss=by["IPKE"],by["IPGE"]
    def key(r):
        return r["access_pc"],r["effective_address"],r["access"],r["width"]
    ha={key(x):x for x in hg["records"]}
    sa={key(x):x for x in ss["records"]}
    if len(ha)!=len(hg["records"]) or len(sa)!=len(ss["records"]):
        raise ValueError("duplicate V9.6 access signature")
    shared = sorted(set(ha) & set(sa))
    return {"tool":"hgss-v9.7-arm9-candidate-branch-call-topology",
            "heartgold":hg,"soulsilver":ss,
            "comparison":{
                "matching_v96_effective_access_signatures":len(shared),
                "heartgold_only_access_signatures":len(set(ha)-set(sa)),
                "soulsilver_only_access_signatures":len(set(sa)-set(ha)),
                "identical_nearby_direct_branch_candidates":sum(
                    ha[k]["nearby_direct_B_BL_targets"] ==
                    sa[k]["nearby_direct_B_BL_targets"] for k in shared),
                "identical_prologue_candidate_metadata":sum(
                    ha[k]["possible_function_entries"] ==
                    sa[k]["possible_function_entries"] for k in shared)},
            "limitations":[
                "All aligned ARM9 words are scanned, including possible data",
                "No executable path or function boundary is verified",
                "No Thumb, BLX immediate, or indirect BX target resolution",
                "No conditional flags or true reaching-definitions analysis",
                "No overlay analysis, scheduler ABI, or Wi-Fi ownership proof"],
            "runtime_execution_proven":False,
            "real_scheduler_ABI_proven":False,
            "safe_to_create_resident_worker":False,
            "ARM7_wifi_IRQ_radio_owned":False,
            "wifi_enabled":False,"rom_or_save_modified":False,
            "next_gate":"Review direct callers and prologue candidates; verify actual execution paths/ABI before any resident Wi-Fi code."}

def load_deps():
    def load(name,path):
        spec=importlib.util.spec_from_file_location(name,path)
        if spec is None or spec.loader is None:
            raise ValueError(f"missing analysis dependency: {path}")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return (load("v97_v96",HERE.parent/"v9_6"/"hgss_full_arm9_effective_xrefs.py"),
            load("v97_v92",HERE.parent/"v9_2"/"hgss_store_value_backtrace.py"))

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",nargs="?",type=Path)
    p.add_argument("soulsilver",nargs="?",type=Path)
    p.add_argument("--rom-dir",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args(argv)
    try:
        v96,v92=load_deps()
        if args.rom_dir:
            if args.heartgold or args.soulsilver:
                raise ValueError("choose --rom-dir OR two original ROM filenames")
            spec=importlib.util.spec_from_file_location(
                "v97_v95",HERE.parent/"v9_5"/"hgss_full_rom_index.py")
            if spec is None or spec.loader is None:
                raise ValueError("V9.5 ROM discovery not available")
            v95=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(v95)
            first,second=v95.discover_roms(args.rom_dir)
        elif args.heartgold and args.soulsilver:
            first,second=args.heartgold.resolve(),args.soulsilver.resolve()
        else:
            raise ValueError("supply both ROMs or --rom-dir")
        if first==second:
            raise ValueError("two different original ROM paths required")
        if args.output and (args.output.resolve() in (first,second) or
                            args.output.suffix.lower() in FORBIDDEN_OUTPUT):
            raise ValueError("refusing to overwrite original ROM/save")
        report=comparison(analyze(first,v96,v92),analyze(second,v96,v92))
        payload=json.dumps(report,indent=2,ensure_ascii=False)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
            print(f"V9.7 candidate call topology completed: {args.output}")
            print("Shared V9.6 reference signatures:",
                  report["comparison"]["matching_v96_effective_access_signatures"])
        else:
            print(payload,end="")
        return 0
    except (OSError,ValueError,struct.error) as exc:
        print("ERROR:",str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
