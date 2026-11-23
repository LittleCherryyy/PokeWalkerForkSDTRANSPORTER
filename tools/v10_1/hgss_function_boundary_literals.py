#!/usr/bin/env python3
"""V10.1: original HGSS ARM9 function-boundary and literal-pool audit (read-only).

Examines suspected function boundaries around the three V9.6 stores. Reports
unconditional returns before a source site, direct B/BL inbound candidates
at/near those sites, and resolves PC-relative A32 word-load literal values.
Crucially, returns invalidate the *naive straight-line assumption* that
an earlier candidate entry owns a later store. They do not by themselves
prove that any function is unreachable. Scans reconstructed original ARM9
only; no code, ROM chunks, saves or Pokemon data are exported.

Uses original US Rev0 ROM verification via the project's V9.6 / V9.2 chain.
No writes to ROMs, saves, patches, Android, bootstrap or DSi.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
FORBIDDEN={".nds",".sav",".dsv",".srm",".walker",".dat"}
ANCHORS={
    "A":{"old_candidate_entry":0x020D1808, "source":0x020D189C,
         "store":0x020D18A4,"expected_last_return":0x020D1898},
    "B":{"old_candidate_entry":0x020D1FA0, "source":0x020D202C,
         "store":0x020D2034,"expected_last_return":0x020D2018},
    "C":{"old_candidate_entry":0x020D2058, "source":0x020D20CC,
         "store":0x020D20D4,"expected_last_return":0x020D20AC},
}
# B's speculative origin is BEFORE a return; deliberately label as
# belonging to the *old candidate*, not to the post-return store.
FOCUSED_LITERAL_PCS=(0x020D1FA4,0x020A3C9C,0x020A3CAC)
INBOUND_BEFORE=0x40
INBOUND_AFTER=0x18
LITERAL_BEFORE=0x70
LITERAL_AFTER=0x18
MAX_NEARBY_EDGES=100
MAX_LITERAL_EXPORT=28

def hx(n): return f"0x{n:08X}"

def w32(img,base,pc):
    off=pc-base
    if pc&3 or off<0 or off+4>len(img):
        raise ValueError("invalid original ARM9 address "+hx(pc))
    return struct.unpack_from("<I",img,off)[0]

def return_candidate(word,pc):
    cond=(word>>28)&15
    if cond==15: return None
    unconditional=cond==14
    bx=(word&0x0ffffff0)==0x012fff10
    if bx:
        rm=word&15
        return {"pc":hx(pc),
                "kind":"BX_LR" if rm==14 else "BX_register",
                "unconditional":unconditional,
                "condition_code":cond,
                "register":f"r{rm}" if rm<13 else ("sp" if rm==13 else
                           "lr" if rm==14 else "pc"),
                "definite_return_without_dynamic_values":False}
    # ARM LDM/POP ... PC: potential return, but stack content unknown.
    if (word>>25)&7==4 and (word&(1<<20)) and (word&(1<<15)):
        return {"pc":hx(pc),"kind":"LDM_loading_PC",
                "unconditional":unconditional,
                "condition_code":cond,
                "definite_return_without_dynamic_values":False}
    # MOV PC,LR direct (no shift), possible return sequence.
    if (word & 0x0fffffff)==0x01a0f00e:
        return {"pc":hx(pc),"kind":"MOV_PC_LR",
                "unconditional":unconditional,
                "condition_code":cond,
                "definite_return_without_dynamic_values":False}
    return None

def pc_literal(word,pc,image,base):
    cond=word>>28
    # A32 immediate, pre-index, word LDR [pc,+/-imm], no writeback.
    if cond==15 or ((word>>26)&3)!=1 or (word&(1<<25)) or (
          not(word&(1<<24))) or (word&(1<<21)) or (
          not(word&(1<<20))) or (word&(1<<22)) or (
          ((word>>16)&15)!=15):
        return None
    off=(word&0xfff)*(1 if word&(1<<23) else -1)
    addr=(pc+8+off)&0xffffffff
    if addr&3 or addr<base or addr+4>base+len(image):
        return {"load_pc":hx(pc),"literal_pc":hx(addr),
                "within_original_ARM9_image":False,
                "value_available":False,
                "executed_in_game":False}
    val=w32(image,base,addr)
    return {"load_pc":hx(pc),"loaded_register":"r"+str((word>>12)&15),
            "literal_pc":hx(addr),
            "literal_value":hx(val),
            "possible_main_ram_pointer":0x02000000<=val<0x02400000,
            "within_original_ARM9_image":True,
            "value_available":True,
            "conditional":cond!=14,
            "executed_in_game":False}

def direct_branch(word,pc):
    cond=word>>28
    if cond==15 or ((word>>25)&7)!=5:
        return None
    disp=word&0xffffff
    if disp&0x800000: disp-=1<<24
    to=(pc+8+(disp<<2))&0xffffffff
    return {"from_pc":hx(pc),"to_pc":hx(to),
            "kind":"BL" if word&(1<<24) else "B",
            "conditional":cond!=14}

def branch_index(image,base):
    dests=defaultdict(list)
    for pos in range(0,len(image)-3,4):
        pc=base+pos
        b=direct_branch(struct.unpack_from("<I",image,pos)[0],pc)
        if b is not None:
            dests[int(b["to_pc"],16)].append(b)
    return dests

def site_report(image,base,label,site,edge_index):
    old,source,store,expected=(site[k] for k in (
        "old_candidate_entry","source","store","expected_last_return"))
    if old>source or source>store or store>=base+len(image):
        raise ValueError("anchor order invalid: "+label)
    if source-old>0x500:
        raise ValueError("old candidate window unexpectedly large")
    exits=[]
    for pc in range(old,source,4):
        ret=return_candidate(w32(image,base,pc),pc)
        if ret: exits.append(ret)
    # V10.0 tagged BX/LDM syntax but did not prove that the CPSR
    # condition was AL. A mismatched hypothesis is evidence to REPORT,
    # not a reason to abort reading the user's original ROMs.
    expected_ret=return_candidate(w32(image,base,expected),expected)
    qualifying=[ret for ret in exits if ret["unconditional"] and
                ret["kind"] in ("BX_LR","MOV_PC_LR","LDM_loading_PC")]
    expected_kind_found=bool(expected_ret is not None and
                             expected_ret["kind"] in
                             ("BX_LR","MOV_PC_LR","LDM_loading_PC"))
    low=max(base,source-INBOUND_BEFORE)
    high=min(base+len(image)-4,store+INBOUND_AFTER)
    incoming=[]
    targets=[]
    for pc in range(low,high+1,4):
        rows=edge_index.get(pc,[])
        if rows:
            incoming.extend(rows)
            targets.append({"target_pc":hx(pc),
                            "inbound_total":len(rows),
                            "direct_BL":sum(x["kind"]=="BL" for x in rows),
                            "direct_B":sum(x["kind"]=="B" for x in rows)})
    incoming.sort(key=lambda x:(x["to_pc"],x["from_pc"]))
    # A conditional return candidate may or may not execute. Do not label
    # it an unconditional boundary. Keep both views in the report.
    immediate_any=any(
        int(row["pc"],16)==source-4 and
        row["kind"] in ("BX_LR","MOV_PC_LR","LDM_loading_PC")
        for row in exits)
    immediate_boundary=any(
        int(row["pc"],16)==source-4 and row["unconditional"] and
        row["kind"] in ("BX_LR","MOV_PC_LR","LDM_loading_PC")
        for row in exits)
    lit=[]
    for pc in range(max(base,source-LITERAL_BEFORE),
                    min(base+len(image)-4,store+LITERAL_AFTER)+1,4):
        row=pc_literal(w32(image,base,pc),pc,image,base)
        if row: lit.append(row)
    return {
        "old_candidate_function_entry":hx(old),
        "original_source_pc":hx(source),
        "original_store_pc":hx(store),
        "old_entry_to_source_unconditional_returns":qualifying,
        "all_syntactic_exit_candidates":exits,
        "expected_return_pc_from_v100":hx(expected),
        "expected_return_syntax_observed":expected_kind_found,
        "expected_return_observation":expected_ret,
        "expected_return_condition_confirmed_unconditional":bool(
            expected_kind_found and expected_ret["unconditional"]),
        "expected_return_hypothesis_mismatch":not expected_kind_found,
        "immediately_preceded_by_any_return_candidate":immediate_any,
        "immediately_preceded_by_unconditional_return_candidate":
            immediate_boundary,
        "incoming_target_summary_near_source_and_store":targets,
        "incoming_direct_branch_count_in_window":len(incoming),
        "incoming_direct_branch_list_truncated":len(incoming)>MAX_NEARBY_EDGES,
        "incoming_direct_branch_edges":incoming[:MAX_NEARBY_EDGES],
        "nearby_literal_loads":lit[:MAX_LITERAL_EXPORT],
        "nearby_literal_list_truncated":len(lit)>MAX_LITERAL_EXPORT,
        "old_candidate_entry_owns_source_proven":False,
        "new_function_start_proven":False,
        "actual_source_execution_proven":False
    }

def analyze(path,v96,v92):
    checked=v96.analyze(path,v92)
    meta,img=v92.v90.v75.v74.reconstruct(path,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"]!=checked["arm9_runtime_sha256"]:
        raise ValueError("original ARM9 runtime hash mismatch")
    base=int(meta["arm9"]["ram_load"],16)
    branches=branch_index(img,base)
    byregion={}
    for label,site in ANCHORS.items():
        key="scheduler_list_store_"+label.lower()
        if int(checked["original_v90_anchors"][key]["access_pc"],16)!=site["store"]:
            raise ValueError("original V9.0/V9.6 store anchor mismatch: "+label)
        byregion[label]=site_report(img,base,label,site,branches)
    focused={}
    for pc in FOCUSED_LITERAL_PCS:
        parsed=pc_literal(w32(img,base,pc),pc,img,base)
        if parsed is None:
            raise ValueError("expected original A32 PC-relative literal missing: "+hx(pc))
        focused[hx(pc)]=parsed
    return {
        "game_code":checked["game_code"],
        "rom_sha1":checked["rom_sha1"],
        "arm9_runtime_sha256":checked["arm9_runtime_sha256"],
        "regions":byregion,
        "focused_pc_literal_values":focused
    }

def compare(hg,ss):
    by={hg["game_code"]:hg,ss["game_code"]:ss}
    if set(by)!={"IPKE","IPGE"}:
        raise ValueError("requires original US Rev0 HeartGold and SoulSilver")
    a,b=by["IPKE"],by["IPGE"]
    names={name:a["regions"][name]==b["regions"][name] for name in ANCHORS}
    literals={pc:a["focused_pc_literal_values"][pc]==b["focused_pc_literal_values"][pc]
              for pc in a["focused_pc_literal_values"]}
    return {
        "tool":"hgss-v10.1-original-ARM9-boundary-and-literal-audit",
        "heartgold":a,"soulsilver":b,
        "comparison":{
            "identical_candidate_boundary_evidence_by_region":names,
            "equal_focused_literal_values":literals,
            "all_boundary_evidence_equal":all(names.values())
        },
        "read_only":True,
        "caveats":[
            "A return before an instruction challenges the old candidate entry, not the instruction's existence",
            "Nearby inbound branches are syntax-only; no runtime branch path is proven",
            "The start of a function may lack a prologue and can be reached by indirect calls",
            "Literal values may be constants or pointers, never actual live RAM contents",
            "All static decoding is A32; Thumb, overlays, ARM7 runtime and Wi-Fi not covered"
        ],
        "old_candidate_entries_certified":False,
        "scheduler_ABI_proven":False,
        "safe_to_create_resident_thread":False,
        "ARM7_WIFI_IRQ_owned":False,
        "in_game_wifi_verified":False,
        "rom_or_save_modified":False,
        "next_gate":"Re-evaluate the three store sites as possibly distinct routines after the intervening unconditional returns. Do not infer runtime execution from these static sites."
    }

def self_test():
    assert return_candidate(0xe12fff1e,0x02000000)["kind"]=="BX_LR"
    assert return_candidate(0x112fff1e,0x02000000)["unconditional"] is False
    assert return_candidate(0xe12fff1e,0x02000000)["unconditional"] is True
    # Regression: previous V10.1 incorrectly raised for a conditional BX LR.
    synthetic=struct.pack("<16I",0xe1a00000,0x112fff1e,0xe1a00000,
                          *([0]*13))
    simulated=site_report(synthetic,0x02000000,"TEST",{
        "old_candidate_entry":0x02000000,
        "source":0x02000008,"store":0x0200000C,
        "expected_last_return":0x02000004},defaultdict(list))
    assert simulated["expected_return_syntax_observed"] is True
    assert simulated["expected_return_condition_confirmed_unconditional"] is False
    assert simulated["immediately_preceded_by_any_return_candidate"] is True
    assert simulated["immediately_preceded_by_unconditional_return_candidate"] is False
    assert return_candidate(0xe8bd81f0,0x02000004)["kind"]=="LDM_loading_PC"
    assert return_candidate(0x08bd81f0,0x02000004)["unconditional"] is False
    assert return_candidate(0xe1a0f00e,0x02000008)["kind"]=="MOV_PC_LR"
    assert direct_branch(0xeb000001,0x02000000)=={
        "from_pc":"0x02000000","to_pc":"0x0200000C",
        "kind":"BL","conditional":False}
    image=struct.pack("<8I",0xe59f0004,0,0,0x021e16a8,0,0,0,0)
    row=pc_literal(0xe59f0004,0x02000000,image,0x02000000)
    assert row["literal_pc"]=="0x0200000C"
    assert row["literal_value"]=="0x021E16A8"
    assert pc_literal(0xe5901004,0x02000000,image,0x02000000) is None
    print("V10.1 synthetic return and literal decoder tests: PASS")
    return 0

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",nargs="?",type=Path)
    p.add_argument("soulsilver",nargs="?",type=Path)
    p.add_argument("--rom-dir",type=Path)
    p.add_argument("--output",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args(argv)
    try:
        if args.self_test: return self_test()
        def load(alias,path):
            spec=importlib.util.spec_from_file_location(alias,path)
            if spec is None or spec.loader is None:
                raise ValueError("required read-only dependency absent: "+str(path))
            obj=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(obj)
            return obj
        v96=load("v101_v96",HERE.parent/"v9_6"/"hgss_full_arm9_effective_xrefs.py")
        v92=load("v101_v92",HERE.parent/"v9_2"/"hgss_store_value_backtrace.py")
        if args.rom_dir:
            if args.heartgold or args.soulsilver:
                raise ValueError("use --rom-dir OR two original ROM filenames")
            v95=load("v101_v95",HERE.parent/"v9_5"/"hgss_full_rom_index.py")
            hg,ss=v95.discover_roms(args.rom_dir)
        elif args.heartgold and args.soulsilver:
            hg,ss=args.heartgold.resolve(),args.soulsilver.resolve()
        else:
            raise ValueError("provide original ROM pair or --rom-dir")
        if hg==ss:
            raise ValueError("need two distinct ROM files")
        if args.output and (args.output.resolve() in (hg,ss) or
                            args.output.suffix.lower() in FORBIDDEN):
            raise ValueError("refusing to overwrite ROM/save files")
        report=compare(analyze(hg,v96,v92),analyze(ss,v96,v92))
        payload=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
            print("V10.1 boundary and literal report:",args.output)
            for label,row in report["heartgold"]["regions"].items():
                print(label,"unconditional_return_candidates:",
                      len(row["old_entry_to_source_unconditional_returns"]),
                      "expected_syntax_observed:",
                      row["expected_return_syntax_observed"],
                      "expected_unconditional:",
                      row["expected_return_condition_confirmed_unconditional"])
        else:
            print(payload,end="")
        return 0
    except (OSError,ValueError,struct.error) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
