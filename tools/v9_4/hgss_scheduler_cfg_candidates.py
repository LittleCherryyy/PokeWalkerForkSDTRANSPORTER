#!/usr/bin/env python3
"""V9.4: read-only, bounded ARM9 candidate writer and local CFG audit.
Requires original USA Rev0 HGSS ROMs and existing V9.2 verification chain.
Candidate writers != reaching definitions. No gameplay, RAM or Wi-Fi claims.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
CONDITIONS=("eq","ne","cs","cc","mi","pl","vs","vc","hi","ls","ge","lt","gt","le","al","nv")
TARGETS=(("scheduler_list_store_a",0x020D189C,0),
         ("scheduler_list_store_b",0x020D202C,8),
         ("scheduler_list_store_c",0x020D20CC,7))
BEFORE=64
AFTER=3
FORBIDDEN={".nds",".sav",".dsv",".srm",".walker",".dat"}

def hx(n): return f"0x{n:08X}"

def classify(word, pc):
    cond=CONDITIONS[word>>28]
    row={"pc":hx(pc),"condition":cond}
    if (word>>25)&7==5:
        displacement=word&0xffffff
        if displacement&0x800000: displacement-=0x1000000
        row.update(kind="branch",target=hx((pc+8+(displacement<<2))&0xffffffff),
                   link=bool(word&(1<<24)))
    elif (word&0x0ffffff0) in (0x012fff10,0x012fff30):
        row.update(kind="branch_register",source_register=f"r{word&15}")
    elif ((word>>24)&15)==15:
        row["kind"]="software_interrupt"
    elif ((word>>25)&7)==4:
        row.update(kind="block_memory",possible_register_writes=True)
    elif ((word>>26)&3)==1:
        row.update(kind="memory",load=bool(word&(1<<20)),
                   base_register=f"r{(word>>16)&15}",
                   target_register=f"r{(word>>12)&15}",
                   writeback_possible=bool(word&(1<<21)) or not bool(word&(1<<24)))
    elif (word>>26)&3:
        row.update(kind="unknown",possible_register_writes=True)
    elif (word&0x90)==0x90 and not (word&(1<<25)):
        row.update(kind="extra_memory_or_multiply",possible_register_writes=True)
    else:
        op=(word>>21)&15
        if op in (8,9,10,11):
            row["kind"]="flags_only"
        else:
            row.update(kind="data_processing",target_register=f"r{(word>>12)&15}",
                       opcode_class={13:"mov",4:"add",2:"sub"}.get(op,"other"),
                       source_register=f"r{(word>>16)&15}",
                       immediate=bool(word&(1<<25)))
    return row

def writer(row, reg):
    target=f"r{reg}"
    kind=row["kind"]
    if kind=="data_processing" and row["target_register"]==target:
        return "write_if_executed"
    if kind=="memory" and ((row["load"] and row["target_register"]==target)
          or (row["writeback_possible"] and row["base_register"]==target)):
        return "write_if_executed"
    if kind in ("block_memory","unknown","extra_memory_or_multiply"):
        return "unmodeled_possible_write"
    return None

def inspect(image,base,pc,reg):
    first,last=pc-BEFORE*4,pc+AFTER*4
    if pc&3 or first<base or last+4>base+len(image):
        raise ValueError("bounded original ARM9 window outside image")
    writers=[];edges=[];conditions=[]
    for addr in range(first,last+1,4):
        row=classify(struct.unpack_from("<I",image,addr-base)[0],addr)
        if addr<pc:
            category=writer(row,reg)
            if category:
                writers.append({"pc":row["pc"],"condition":row["condition"],
                                "instruction_class":row["kind"],"category":category})
        if row["kind"]=="branch":
            target=int(row["target"],16)
            edges.append({"from_pc":row["pc"],"to_pc":row["target"],
                          "inside_window":first<=target<=last,
                          "conditional":row["condition"]!="al","link":row["link"]})
        elif row["kind"]=="branch_register":
            edges.append({"from_pc":row["pc"],"to_pc":None,"indirect":True})
        if row["condition"]!="al" or row["kind"] in (
            "branch","branch_register","block_memory","unknown"):
            conditions.append(row)
    return {"source_load_pc":hx(pc),"source_base_register":f"r{reg}",
            "first_pc":hx(first),"last_pc":hx(last),
            "candidate_writers":writers,"local_branch_edges":edges,
            "conditional_or_control_flow_sites":conditions,
            "incoming_edges_exhaustively_known":False,
            "condition_flags_known":False,
            "candidate_writers_are_reaching_definitions":False,
            "live_register_values_known":False,
            "executed_path_verified":False}

def analyze(path,v92):
    previous=v92.analyze_game(path)
    meta,image=v92.v90.v75.v74.reconstruct(path,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"]!=previous["original_runtime_sha256"]:
        raise ValueError("ARM9 runtime digest changed")
    base=int(meta["arm9"]["ram_load"],16)
    return {"game_code":previous["game_code"],"original_rom_sha1":previous["original_rom_sha1"],
            "original_runtime_sha256":previous["original_runtime_sha256"],
            "records":{name:inspect(image,base,pc,reg) for name,pc,reg in TARGETS}}

def compare(first,second):
    games={first["game_code"]:first,second["game_code"]:second}
    if set(games)!={"IPKE","IPGE"}:
        raise ValueError("requires original USA Rev0 IPKE and IPGE")
    hg,ss=games["IPKE"],games["IPGE"]
    return {"tool":"hgss-v9.4-bounded-cfg-candidate-audit",
            "heartgold":hg,"soulsilver":ss,
            "cross_title":{name:{
                k:hg["records"][name][k]==ss["records"][name][k]
                for k in ("candidate_writers","local_branch_edges",
                          "conditional_or_control_flow_sites")}
                for name,_,_ in TARGETS},
            "runtime_execution_verified":False,
            "scheduler_ABI_proven":False,"safe_to_create_worker_thread":False,
            "bootstrap_owned_persistent_stack_proven":False,
            "ARM7_WiFi_IRQ_or_radio_owned":False,
            "wifi_enabled":False,"rom_or_save_modified":False,
            "next_gate":"Determine incoming CFG edges and predicate-aware reaching definitions before any thread or Wi-Fi code."}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",type=Path)
    p.add_argument("soulsilver",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args(argv)
    try:
        if args.heartgold.resolve()==args.soulsilver.resolve():
            raise ValueError("two distinct original ROMs required")
        if args.output and (args.output.suffix.lower() in FORBIDDEN or
              args.output.resolve() in (args.heartgold.resolve(),args.soulsilver.resolve())):
            raise ValueError("refusing ROM/save output path")
        dep=HERE.parent/"v9_2"/"hgss_store_value_backtrace.py"
        spec=importlib.util.spec_from_file_location("v94_v92",dep)
        if spec is None or spec.loader is None:
            raise ValueError("V9.2 chain not available")
        v92=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v92)
        result=compare(analyze(args.heartgold,v92),analyze(args.soulsilver,v92))
        payload=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
        print(payload,end="")
        return 0
    except (OSError,ValueError,struct.error) as e:
        print("ERROR: "+str(e),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
