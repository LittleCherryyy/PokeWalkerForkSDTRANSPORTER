#!/usr/bin/env python3
"""V10.0 — original HGSS ARM9 ABI/caller evidence, no ROM or save writes.

Local-only static ROM analysis of the V9.9 provenance hypotheses:
 - inspect the memory addressing at the candidate r8 load (020D1FB4)
 - verify the r7 <- r0 move (020D2060)
 - find all direct A32 callers of tentative entrypoints in the whole ARM9
 - inspect nearby r0 writes before those calls, without claiming execution
 - inspect candidate prologues/epilogues and blockers for A/B/C

All A32 classifications are syntax-only; no actual path, scheduler identity,
Nintendo ABI compliance, or Wi-Fi compatibility is inferred. No source
opcodes/ROM bytes are exported. Requires original US Rev0 pair with upstream
V9.2/V9.6 verification; never changes ROM, save, DSi, Android or bootstrap.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
PROHIBITED={".nds",".sav",".dsv",".srm",".walker",".dat"}
ENTRIES={
    "A":{"candidate_entry":0x020D1808,"source_pc":0x020D189C,
         "store_pc":0x020D18A4,"register":0},
    "B":{"candidate_entry":0x020D1FA0,"source_pc":0x020D202C,
         "store_pc":0x020D2034,"register":8},
    "C":{"candidate_entry":0x020D2058,"source_pc":0x020D20CC,
         "store_pc":0x020D20D4,"register":7},
}
REG_NAMES=tuple(f"r{i}" for i in range(13))+("sp","lr","pc")
CALLER_SCAN_BEFORE=48
BLOCKER_SCAN_MAX=144
MAX_CALLERS=256
MAX_NEAREST_WRITERS=6

def hx(x): return f"0x{x:08X}"

def word(img,base,pc):
    pos=pc-base
    if pos<0 or pos+4>len(img) or pc&3:
        raise ValueError(f"ARM9 PC out of bounds: {hx(pc)}")
    return struct.unpack_from("<I",img,pos)[0]

def direct_branch(w,pc):
    if (w>>28)==15 or ((w>>25)&7)!=5:
        return None
    imm=w&0xffffff
    if imm&0x800000: imm-=1<<24
    target=(pc+8+(imm<<2))&0xffffffff
    return {"pc":hx(pc),"target_pc":hx(target),
            "kind":"BL" if w&(1<<24) else "B",
            "conditional":(w>>28)!=14}

def memory_access(w):
    if (w>>28)==15 or ((w>>26)&3)!=1:
        return None
    reg=(w>>12)&15
    rn=(w>>16)&15
    imm=not bool(w&(1<<25))
    up=bool(w&(1<<23))
    return {"kind":"ldr" if w&(1<<20) else "str",
            "dest_or_source":REG_NAMES[reg],
            "base":REG_NAMES[rn],
            "offset_kind":"immediate" if imm else "register_or_shift",
            "signed_immediate_offset":(
                (w&0xfff)*(1 if up else -1)) if imm else None,
            "preindexed":bool(w&(1<<24)),
            "writeback":bool(w&(1<<21)),
            "byte_access":bool(w&(1<<22)),
            "conditional":(w>>28)!=14,
            "may_change_pc":bool(w&(1<<20) and reg==15)}

def register_mask(w):
    if (w>>28)==15 or ((w>>25)&7)!=4:
        return None
    mask=w&0xffff
    return {"kind":"ldm" if w&(1<<20) else "stm",
            "base":REG_NAMES[(w>>16)&15],
            "reglist":[REG_NAMES[r] for r in range(16) if mask&(1<<r)],
            "writeback":bool(w&(1<<21)),
            "preindexed":bool(w&(1<<24)),
            "up":bool(w&(1<<23)),
            "conditional":(w>>28)!=14}

def simple_mov(w):
    if (w>>28)==15 or (w>>26)&3 or ((w>>21)&15)!=13:
        return None
    if w&(1<<25):
        return {"destination":REG_NAMES[(w>>12)&15],
                "origin":"immediate","unshifted_register":False}
    no_shift=not bool(w&0xff0)
    return {"destination":REG_NAMES[(w>>12)&15],
            "origin":REG_NAMES[w&15] if no_shift else "shifted_register",
            "unshifted_register":no_shift,
            "conditional":(w>>28)!=14}

def possible_writer(w,pc,reg):
    """A one-instruction syntactic candidate only; excludes flags-only."""
    if (w>>28)==15: return None
    branch=direct_branch(w,pc)
    if branch and branch["kind"]=="BL" and reg in (0,1,2,3,12):
        return {"pc":hx(pc),"kind":"call_result_or_clobber_hypothesis",
                "actual_writer_proven":False}
    if branch: return None
    if (w&0x0ffffff0)==0x012fff30 and reg in (0,1,2,3,12):
        return {"pc":hx(pc),"kind":"indirect_call_clobber_hypothesis",
                "actual_writer_proven":False}
    mem=memory_access(w)
    if mem:
        if (mem["kind"]=="ldr" and mem["dest_or_source"]==REG_NAMES[reg]):
            return {"pc":hx(pc),"kind":"memory_load",
                    "addressing":mem,"actual_writer_proven":False}
        if mem["base"]==REG_NAMES[reg] and (mem["writeback"] or not mem["preindexed"]):
            return {"pc":hx(pc),"kind":"memory_base_writeback",
                    "addressing":mem,"actual_writer_proven":False}
        return None
    multi=register_mask(w)
    if multi:
        if multi["kind"]=="ldm" and REG_NAMES[reg] in multi["reglist"]:
            return {"pc":hx(pc),"kind":"block_load","actual_writer_proven":False}
        if multi["writeback"] and multi["base"]==REG_NAMES[reg]:
            return {"pc":hx(pc),"kind":"block_base_writeback","actual_writer_proven":False}
        return None
    if (w>>26)&3 or (w&0x90)==0x90 and not(w&(1<<25)):
        return {"pc":hx(pc),"kind":"unknown_class_possible_write",
                "actual_writer_proven":False}
    op=(w>>21)&15
    if op in (8,9,10,11): return None
    if ((w>>12)&15)!=reg: return None
    mov=simple_mov(w)
    if mov:
        return {"pc":hx(pc),"kind":"mov","source":mov["origin"],
                "actual_writer_proven":False}
    return {"pc":hx(pc),"kind":"data_processing",
            "actual_writer_proven":False}

def nearby_call_argument(img,base,call_pc):
    begin=max(base,call_pc-CALLER_SCAN_BEFORE*4)
    writers=[]; control=0
    for pc in range(begin,call_pc,4):
        w=word(img,base,pc)
        row=possible_writer(w,pc,0)
        if row: writers.append(row)
        if direct_branch(w,pc) or (w&0x0ffffff0) in (0x012fff10,0x012fff30):
            control+=1
    writers.reverse()
    return {"caller_pc":hx(call_pc),
            "nearest_possible_r0_writes":writers[:MAX_NEAREST_WRITERS],
            "nearest_writer_count_in_window":len(writers),
            "syntactic_control_transfers_in_window":control,
            "register_value_at_call_proven":False,
            "caller_to_callee_actual_execution_proven":False}

def prologue_evidence(img,base,entry):
    w=word(img,base,entry)
    multi=register_mask(w)
    lr_store=(w==0xe52de004)
    stack_push=bool(multi and multi["kind"]=="stm" and
                    multi["base"]=="sp" and multi["preindexed"] and
                    not multi["up"] and multi["writeback"])
    if not stack_push and not lr_store:
        raise ValueError("V9.7 candidate prologue changed: "+hx(entry))
    return {"pc":hx(entry),"stack_push_candidate":stack_push,
            "store_lr_candidate":lr_store,
            "saved_register_names":multi["reglist"] if stack_push else ["lr"],
            "explicitly_saves_r7":bool(stack_push and "r7" in multi["reglist"]),
            "explicitly_saves_r8":bool(stack_push and "r8" in multi["reglist"]),
            "function_entry_confirmed":False}

def blockers(img,base,entry,source):
    blockers=[];prologues=[];epilogues=[]
    if source-entry>BLOCKER_SCAN_MAX*4:
        raise ValueError("source too far from candidate entry")
    for pc in range(entry,source,4):
        w=word(img,base,pc)
        b=direct_branch(w,pc)
        if b and (b["kind"]=="B" and int(b["target_pc"],16) > source):
            blockers.append({"pc":hx(pc),"kind":"forward_branch_past_source",
                             "target_pc":b["target_pc"],
                             "conditional":b["conditional"]})
        mul=register_mask(w)
        if mul and mul["kind"]=="ldm" and "pc" in mul["reglist"]:
            epilogues.append({"pc":hx(pc),"kind":"load_pc_via_block_memory",
                              "conditional":mul["conditional"],
                              "restored_regs":mul["reglist"]})
        elif (w&0x0ffffff0)==0x012fff10:
            epilogues.append({"pc":hx(pc),"kind":"indirect_branch",
                              "source_register":REG_NAMES[w&15]})
        if pc!=entry and (w&0xffff0000)==0xe92d0000:
            prologues.append(hx(pc))
    return {"range_first_pc":hx(entry),"range_last_pc":hx(source-4),
            "conditional_or_unconditional_forward_branch_past_target":blockers[:32],
            "possible_returns_or_indirect_exits":epilogues[:32],
            "other_stack_save_candidates_inside_interval":prologues[:32],
            "true_function_boundary_or_runtime_path_proven":False}

def analyze(rom,v96,v92):
    validated=v96.analyze(rom,v92)
    meta,img=v92.v90.v75.v74.reconstruct(rom,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"]!=validated["arm9_runtime_sha256"]:
        raise ValueError("ARM9 image digest mismatch")
    base=int(meta["arm9"]["ram_load"],16)
    # Each incoming direct BL is indexed over the *whole* ARM9 image.
    direct_callers={row["candidate_entry"]:[] for row in ENTRIES.values()}
    for off in range(0,len(img)-3,4):
        pc=base+off
        b=direct_branch(struct.unpack_from("<I",img,off)[0],pc)
        if b is None or b["kind"]!="BL": continue
        target=int(b["target_pc"],16)
        if target in direct_callers:
            direct_callers[target].append(b)
    output={}
    for name,record in ENTRIES.items():
        entry,source,store=(record[k] for k in (
            "candidate_entry","source_pc","store_pc"))
        checked=validated["original_v90_anchors"]["scheduler_list_store_"+name.lower()]
        if int(checked["access_pc"],16)!=store:
            raise ValueError("V9.0 anchor mismatch: "+name)
        callers=direct_callers[entry]
        if len(callers)>MAX_CALLERS:
            raise ValueError("unexpected number of direct call candidates")
        output[name]={
            "candidate_entry":hx(entry),
            "source_pc":hx(source),
            "store_pc":hx(store),
            "prologue":prologue_evidence(img,base,entry),
            "direct_BL_candidates_count":len(callers),
            "direct_callsite_r0_origin_hypotheses":[
                nearby_call_argument(img,base,int(b["pc"],16))
                for b in callers],
            "branch_and_return_blockers_before_source":
                blockers(img,base,entry,source),
            "actual_call_graph_proven":False,
        }
    bw=memory_access(word(img,base,0x020D1FB4))
    if bw is None or bw["kind"]!="ldr" or bw["dest_or_source"]!="r8":
        raise ValueError("V9.9 candidate r8 load did not decode")
    cw=simple_mov(word(img,base,0x020D2060))
    if cw is None or cw["destination"]!="r7" or cw["origin"]!="r0" or (
            not cw["unshifted_register"]):
        raise ValueError("V9.9 candidate r7<-r0 move did not decode")
    output["B"]["r8_origin_instruction"]={
        "pc":"0x020D1FB4",
        "memory_addressing":bw,
        "origin_is_actual_runtime_pointer":False,
        "source_base_writer_candidates_before_load":[
            row for row in (
                possible_writer(word(img,base,pc),pc,int(bw["base"][1:]))
                for pc in range(0x020D1FA0,0x020D1FB4,4)
            ) if row is not None] if bw["base"].startswith("r") else [],
    }
    output["C"]["r7_origin_instruction"]={
        "pc":"0x020D2060","operation":"MOV r7, r0",
        "condition_is_unconditional":not cw["conditional"],
        "actual_parameter_r0_value_known":False,
    }
    return {"game_code":validated["game_code"],
            "original_rom_sha1":validated["rom_sha1"],
            "arm9_runtime_sha256":validated["arm9_runtime_sha256"],
            "regions":output}

def compare(hg,ss):
    by={hg["game_code"]:hg,ss["game_code"]:ss}
    if set(by)!={"IPKE","IPGE"}:
        raise ValueError("requires original USA HeartGold and SoulSilver")
    a,b=by["IPKE"],by["IPGE"]
    same={name:a["regions"][name]==b["regions"][name] for name in ENTRIES}
    return {"tool":"hgss-v10.0-whole-arm9-caller-and-abi-evidence",
            "heartgold":a,"soulsilver":b,
            "comparison":{"equal_region_semantics":same,
                          "all_equal":all(same.values())},
            "scope":"whole ARM9 A32 direct BL search + bounded caller arg and prologue syntax",
            "warnings":["All aligned words are only potential ARM instructions",
                        "No Thumb or indirect caller resolution",
                        "Nearest register writer need not reach the callsite",
                        "No direct observation of ABI preservation or execution",
                        "Nearby prologues and epilogues need not belong to the same function"],
            "actual_code_path_proven":False,
            "Nintendo_ABI_verified":False,
            "worker_thread_safe":False,
            "ARM7_radio_irq_ownership_verified":False,
            "wifi_enabled":False,"rom_or_save_modified":False,
            "next_gate":"Use decoded r8 memory base and incoming r0 caller candidates to prioritize an actual runtime trace before resident Wi-Fi."}

def self_test():
    assert direct_branch(0xeb000001,0x02000000)=={
        "pc":"0x02000000","target_pc":"0x0200000C",
        "kind":"BL","conditional":False}
    assert direct_branch(0xea000001,0x02000000)["kind"]=="B"
    assert direct_branch(0xfa000000,0x02000000) is None
    saved=register_mask(0xe92d41f0)
    assert "r7" in saved["reglist"] and "r8" in saved["reglist"]
    assert saved["kind"]=="stm" and saved["base"]=="sp"
    assert memory_access(0xe5908008)["signed_immediate_offset"]==8
    assert memory_access(0xe5908008)["dest_or_source"]=="r8"
    assert simple_mov(0xe1a07000)["origin"]=="r0"
    assert simple_mov(0xe1a07000)["destination"]=="r7"
    print("V10.0 synthetic instruction-decoder tests: PASS")
    return 0

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("heartgold",nargs="?",type=Path)
    parser.add_argument("soulsilver",nargs="?",type=Path)
    parser.add_argument("--rom-dir",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args(argv)
    try:
        if args.self_test: return self_test()
        def load(alias,path):
            spec=importlib.util.spec_from_file_location(alias,path)
            if spec is None or spec.loader is None:
                raise ValueError("missing previous version: "+str(path))
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        v96=load("v100_v96",HERE.parent/"v9_6"/"hgss_full_arm9_effective_xrefs.py")
        v92=load("v100_v92",HERE.parent/"v9_2"/"hgss_store_value_backtrace.py")
        if args.rom_dir:
            if args.heartgold or args.soulsilver:
                raise ValueError("use --rom-dir OR positional ROMs, not both")
            v95=load("v100_v95",HERE.parent/"v9_5"/"hgss_full_rom_index.py")
            hg,ss=v95.discover_roms(args.rom_dir)
        elif args.heartgold and args.soulsilver:
            hg,ss=args.heartgold.resolve(),args.soulsilver.resolve()
        else:
            raise ValueError("provide original ROM pair or --rom-dir")
        if hg==ss: raise ValueError("two distinct original ROMs required")
        if args.output and (args.output.resolve() in (hg,ss) or
                            args.output.suffix.lower() in PROHIBITED):
            raise ValueError("refusing overwrite of ROM/save")
        result=compare(analyze(hg,v96,v92),analyze(ss,v96,v92))
        payload=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
            print("V10.0 report generated:",args.output)
            for label,info in result["heartgold"]["regions"].items():
                print(label,"direct callers:",info["direct_BL_candidates_count"])
        else:
            print(payload,end="")
        return 0
    except (OSError,ValueError,struct.error) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
