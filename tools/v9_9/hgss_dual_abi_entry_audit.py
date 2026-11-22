#!/usr/bin/env python3
"""V9.9 — compare V9.8's unknown-call model against ARM call-preservation hypothesis.

Original HGSS USA Rev0 ROMs only; read-only. Uses the original V9.8 analyzer
without replacing it: reruns its bounded abstract interpretation using a
hypothetical ARM AAPCS-style convention where calls preserve r4-r8/r10-r11
(r9 platform-specific). Our tracked r7/r8 are consequently preserved.
This is NOT proof that Nintendo's game/SDK follows this ABI at these calls.
Also tests alternative V9.7 candidate prologues to identify wrong entry guesses.
Never changes a ROM, save, patch, Android app, DSi, or Wi-Fi settings.
"""
from __future__ import annotations
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
# Each entry is a V9.7 candidate prologue, not a proven function boundary.
ENTRY_HYPOTHESES = {
    "scheduler_list_store_a": (0x020D1808, 0x020D1690),
    "scheduler_list_store_b": (0x020D1FA0, 0x020D1F84),
    "scheduler_list_store_c": (0x020D2058, 0x020D1FA0),
}
CALL_VOLATILE_REGS = (0, 1, 2, 3, 12)
FORBIDDEN = {".nds", ".sav", ".dsv", ".srm", ".walker", ".dat"}

def hx(n):
    return f"0x{n:08X}"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("missing upstream analysis dependency: " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def call_model_action(v98, original):
    """An injected static hypothesis for BL and BLX(register), not emulator."""
    def assumed_action(word, pc, state, image, base):
        if word >> 28 == 15:
            return original(word, pc, state, image, base)
        direct = v98.branch(word, pc)
        if direct is not None and direct[1]:
            # LR is not tracked. r4-r8/r10-r11 are modeled as unchanged.
            result = v98.opaque(state, "call_volatile@" + hx(pc),
                                CALL_VOLATILE_REGS)
            return ("direct_call_preserve_callee_saved_hypothesis",
                    result, pc + 4)
        if (word & 0x0ffffff0) == 0x012fff30:
            result = v98.opaque(state, "indirect_call_volatile@" + hx(pc),
                                CALL_VOLATILE_REGS)
            return ("indirect_call_preserve_callee_saved_hypothesis",
                    result, pc + 4)
        return original(word, pc, state, image, base)
    return assumed_action

def examine_mode(v98, image, base, entry, source_pc, reg, store_pc, mode):
    if mode == "unknown":
        return v98.examine(image, base, entry, source_pc, reg, store_pc)
    if mode != "preserve_hypothesis":
        raise ValueError("invalid call model")
    # The upstream analyzer has no injectable action argument. Patch its
    # isolated, dynamically imported module only during this synchronous
    # single-threaded call; always restore it, including on exceptions.
    original = v98.action
    v98.action = call_model_action(v98, original)
    try:
        return v98.examine(image, base, entry, source_pc, reg, store_pc)
    finally:
        v98.action = original

def compact(row):
    return {
        "entry": row["candidate_function_entry"],
        "source_load_pc": row["source_load_pc"],
        "source_base_register": row["source_base_register"],
        "source_reachable_from_entry_in_model":
            row["syntactic_source_reachable_from_candidate_entry"],
        "source_base_origin_tags": row["possible_source_base_origins"],
        "potential_register_writer_sites": row["potential_register_writer_sites"],
        "nodes_visited": row["abstract_nodes_visited"],
        "stopped_instruction_classes": row["blocked_instruction_classes"],
        "edges_outside_interval": row["edges_outside_candidate_interval"],
        "actual_execution_proven": False,
        "real_register_provenance_proven": False,
    }

def analyze(rom, v98, v96, v92):
    upstream = v96.analyze(rom, v92)
    meta, image = v92.v90.v75.v74.reconstruct(
        rom, include_runtime_image=True)
    if (meta["arm9"]["runtime_decompressed_sha256"] !=
            upstream["arm9_runtime_sha256"]):
        raise ValueError("original ARM9 digest mismatch")
    base = int(meta["arm9"]["ram_load"], 16)
    anchors = {name: (source, reg, store) for
               name, primary, source, reg, store in v98.ANCHORS}
    output = {}
    for name, entries in ENTRY_HYPOTHESES.items():
        source, reg, store = anchors[name]
        if int(upstream["original_v90_anchors"][name]["access_pc"],16) != store:
            raise ValueError("verified V9.0 anchor mismatch: " + name)
        candidates = []
        for i, entry in enumerate(entries):
            original = examine_mode(
                v98, image, base, entry, source, reg, store, "unknown")
            assumed = examine_mode(
                v98, image, base, entry, source, reg, store,
                "preserve_hypothesis")
            candidates.append({
                "entry_hypothesis": hx(entry),
                "priority": "V9.7_closest" if i == 0 else "V9.7_alternative",
                "fully_unknown_call_model": compact(original),
                "r7_r8_preserving_call_hypothesis": compact(assumed),
                "effect_of_call_convention_assumption": {
                    "changes_source_reachability": (
                        original["syntactic_source_reachable_from_candidate_entry"]
                        != assumed["syntactic_source_reachable_from_candidate_entry"]),
                    "changes_possible_register_origins": (
                        original["possible_source_base_origins"]
                        != assumed["possible_source_base_origins"])
                },
            })
        output[name] = candidates
    return {
        "game_code": upstream["game_code"],
        "rom_sha1": upstream["rom_sha1"],
        "arm9_runtime_sha256": upstream["arm9_runtime_sha256"],
        "entry_hypotheses": output,
    }

def compare(hg,ss):
    by = {hg["game_code"]: hg, ss["game_code"]: ss}
    if set(by) != {"IPKE","IPGE"}:
        raise ValueError("expected one original USA HeartGold and SoulSilver")
    a,b = by["IPKE"],by["IPGE"]
    matching = {name: a["entry_hypotheses"][name] == b["entry_hypotheses"][name]
                for name in ENTRY_HYPOTHESES}
    return {
        "tool": "hgss-v9.9-dual-call-convention-entry-hypotheses",
        "heartgold": a,
        "soulsilver": b,
        "comparison": {
            "same_abstract_results_for_all_entry_hypotheses": all(matching.values()),
            "equal_regions": matching
        },
        "assumptions": {
            "full_unknown_model": "all tracked registers become unknown after any call",
            "r7_r8_preserving_model":
                "hypothetical ARM procedure-call convention; only r0-r3,r12 "
                "become unknown after a call; never claimed verified for HGSS",
            "r9_status": "platform-specific and not analyzed",
            "candidate_entries": "stack-save prologue patterns, not verified",
            "conditional_flags": "not known; both execute and skip possible",
        },
        "limitations": [
            "V9.8 abstract CFG remains bounded and lacks external incoming edges",
            "No actual CPU path, register data, RAM values, or function identity",
            "Call targets are not evaluated and conventions are unverified",
            "Unrecognized A32, Thumb, indirect PC loads and overlays remain gaps"
        ],
        "safe_to_create_resident_thread": False,
        "arm7_radio_irq_ownership_verified": False,
        "wifi_enabled": False,
        "rom_or_save_modified": False,
        "next_gate": "Confirm likely r7/r8 origin under both assumptions, then verify scheduler ABI and runtime execution without game modifications."
    }

def self_test():
    class Mock:
        @staticmethod
        def branch(word, pc):
            if (word >> 28) == 15 or ((word >> 25) & 7) != 5:
                return None
            return pc + 8, bool(word & (1 << 24))
        @staticmethod
        def opaque(state, tag, registers):
            result=list(state)
            for register in registers:
                result[register] = frozenset({tag})
            return tuple(result)
    states = tuple(frozenset({f"orig_r{r}"}) for r in range(13))
    def passthrough(word,pc,state,image,base):
        return ("original",state,pc+4)
    action = call_model_action(Mock,passthrough)
    kind,after,pc=action(0xEB000000,0x02000000,states,b"",0)
    assert kind.startswith("direct_call_preserve")
    assert pc == 0x02000004
    assert all(after[r] == states[r] for r in range(4,12))
    assert all(after[r] != states[r] for r in CALL_VOLATILE_REGS)
    kind,after,pc=action(0xE12FFF33,0x02000004,states,b"",0)
    assert kind.startswith("indirect_call_preserve")
    assert after[7] == states[7] and after[8] == states[8]
    assert action(0xEA000000,0x02000008,states,b"",0)[0] == "original"
    print("V9.9 synthetic call-convention self-test: PASS")
    return 0

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold", nargs="?", type=Path)
    p.add_argument("soulsilver", nargs="?", type=Path)
    p.add_argument("--rom-dir", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.self_test:
            return self_test()
        v98=load("v99_v98",HERE.parent/"v9_8"/"hgss_cfg_register_origins.py")
        v96=load("v99_v96",HERE.parent/"v9_6"/"hgss_full_arm9_effective_xrefs.py")
        v92=load("v99_v92",HERE.parent/"v9_2"/"hgss_store_value_backtrace.py")
        if args.rom_dir:
            if args.heartgold or args.soulsilver:
                raise ValueError("choose --rom-dir or two file paths")
            v95=load("v99_v95",HERE.parent/"v9_5"/"hgss_full_rom_index.py")
            hg,ss=v95.discover_roms(args.rom_dir)
        elif args.heartgold and args.soulsilver:
            hg,ss=args.heartgold.resolve(),args.soulsilver.resolve()
        else:
            raise ValueError("provide original ROM pair or --rom-dir")
        if hg == ss:
            raise ValueError("two distinct original ROMs required")
        if args.output and (args.output.resolve() in (hg,ss) or
                            args.output.suffix.lower() in FORBIDDEN):
            raise ValueError("refusing to overwrite ROM or save")
        result=compare(analyze(hg,v98,v96,v92),analyze(ss,v98,v96,v92))
        data=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(data,encoding="utf-8")
            print("V9.9 report written:", args.output)
            for name,rows in result["heartgold"]["entry_hypotheses"].items():
                for row in rows:
                    print(name,row["entry_hypothesis"],
                          "unknown:", row["fully_unknown_call_model"]["source_base_origin_tags"],
                          "preserving:",row["r7_r8_preserving_call_hypothesis"]["source_base_origin_tags"])
        else:
            print(data,end="")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
