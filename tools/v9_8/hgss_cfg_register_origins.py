#!/usr/bin/env python3
"""V9.8: candidate control-flow and abstract register origins at three HGSS stores.

Original USA Rev0 ROM verification is inherited from V9.6/V9.2.
The three function ENTRY addresses are *candidates* from V9.7, not proved
boundaries. Branches, conditional execution, and call clobbers are explored
conservatively. We never evaluate RAM, run ARM instructions, patch the game,
write saves, or enable Wi-Fi. An abstract path is NOT a real executed path.
"""
from __future__ import annotations
import argparse
from collections import Counter, deque
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
# Entry guesses are the nearest prologue+direct-BL candidates in user's V9.7.
ANCHORS=(
    ("scheduler_list_store_a",0x020D1808,0x020D189C,0,0x020D18A4),
    ("scheduler_list_store_b",0x020D1FA0,0x020D202C,8,0x020D2034),
    ("scheduler_list_store_c",0x020D2058,0x020D20CC,7,0x020D20D4),
)
MAX_WORDS=160
MAX_ITERATIONS=30000
MAX_ORIGINS_PER_REG=24
FORBIDDEN={".nds",".sav",".dsv",".srm",".walker",".dat"}
REG_COUNT=13

def hx(n):
    return f"0x{n:08X}"

def w32(data,offset):
    return struct.unpack_from("<I",data,offset)[0]

def branch(word,pc):
    if (word>>28)==15 or ((word>>25)&7)!=5:
        return None
    disp=word&0xffffff
    if disp&0x800000:
        disp-=0x1000000
    return ((pc+8+(disp<<2))&0xffffffff, bool(word&(1<<24)))

def initial_state():
    return tuple(frozenset({f"entry_unknown_r{r}"}) for r in range(REG_COUNT))

def write(state,reg,values):
    if reg>=REG_COUNT:
        return state
    result=list(state)
    result[reg]=frozenset(values)
    return tuple(result)

def opaque(state,tag,registers=range(REG_COUNT)):
    result=list(state)
    for r in registers:
        if r<REG_COUNT:
            result[r]=frozenset({tag})
    return tuple(result)

def join(a,b):
    if a is None:
        return b
    merged=[]
    for x,y in zip(a,b):
        both=x|y
        merged.append(frozenset({"many_possible_origins"}) if
                      len(both)>MAX_ORIGINS_PER_REG else both)
    return tuple(merged)

def literal_load(word,pc,image,base):
    """Conservative ARM A32 AL/conditional word LDR literal without writeback."""
    if ((word>>26)&3)!=1 or (word&(1<<25)) or not(word&(1<<24)) or (
          word&(1<<21)) or not(word&(1<<20)) or (word&(1<<22)) or (
          (word>>16)&15)!=15:
        return False
    target=pc+8+((word&0xfff) if word&(1<<23) else -(word&0xfff))
    return target%4==0 and base<=target and target+4<=base+len(image)

def action(word,pc,state,image,base):
    """Return (kind, resulting_state, next_pc), or a stop reason."""
    here=pc+4
    if (word>>28)==15:
        return ("stop_reserved_condition",state,None)
    if (word&0x0ffffff0) in (0x012fff10,0x012fff30):
        if (word&0x0ffffff0)==0x012fff30:
            return ("indirect_call_abi_unknown",opaque(state,"indirect_call@"+hx(pc)),here)
        return ("stop_indirect_branch",state,None)
    b=branch(word,pc)
    if b:
        dest,link=b
        if link:
            return ("direct_call_abi_unknown",opaque(state,"call@"+hx(pc)),here)
        return ("direct_branch",state,dest)
    if ((word>>24)&15)==15:
        return ("stop_swi",state,None)
    cls=(word>>25)&7
    if cls==4:
        # LDM/STM: loaded general registers and writeback may redefine values.
        result=state
        if word&(1<<20):
            if word&(1<<15):
                return ("stop_indirect_PC_load",state,None)
            regs=[r for r in range(REG_COUNT) if word&(1<<r)]
            result=opaque(result,"ldm_unknown@"+hx(pc),regs)
        if word&(1<<21):
            result=opaque(result,"block_writeback@"+hx(pc),
                          [((word>>16)&15)])
        return ("block_memory",result,here)
    if ((word>>26)&3)==1:
        rd=(word>>12)&15
        rn=(word>>16)&15
        load=bool(word&(1<<20))
        if load and rd==15:
            return ("stop_PC_load",state,None)
        result=state
        if load:
            label=("original_ROM_literal@"+hx(pc) if
                   literal_load(word,pc,image,base) else "runtime_load@"+hx(pc))
            result=write(result,rd,{label})
        if word&(1<<21) or not(word&(1<<24)):
            result=write(result,rn,{"memory_writeback@"+hx(pc)})
        return ("memory",result,here)
    if cls==5:
        return ("stop_unsupported_branch",state,None)
    if (word>>26)&3:
        return ("stop_unmodeled_class",state,None)
    if (word&0x90)==0x90 and not(word&(1<<25)):
        return ("stop_multiply_or_extra_memory",state,None)
    op=(word>>21)&15
    rd=(word>>12)&15
    rn=(word>>16)&15
    if op in (8,9,10,11):
        return ("flags_only",state,here)
    if rd==15:
        return ("stop_PC_write",state,None)
    imm=bool(word&(1<<25))
    if op==13:
        if imm:
            result=write(state,rd,{"mov_immediate@"+hx(pc)})
        elif word&0xff0:
            result=write(state,rd,{"mov_shift_unknown@"+hx(pc)})
        else:
            rm=word&15
            result=write(state,rd,state[rm] if rm<REG_COUNT else
                         {"mov_PC_unknown@"+hx(pc)})
        return ("move",result,here)
    if op in (2,4):
        # Arithmetic can change a pointer, so keep an operation origin,
        # not the original register's value as though it were unchanged.
        result=write(state,rd,{"arithmetic@"+hx(pc)})
        return ("arithmetic",result,here)
    return ("data_processing_opaque",write(state,rd,{"data_op@"+hx(pc)}),here)

def examine(image,base,entry,source_pc,reg,store_pc):
    if entry%4 or source_pc%4 or source_pc<=entry or (
         source_pc-entry)//4>MAX_WORDS:
        raise ValueError("candidate interval is outside bounded limits")
    if entry<base or store_pc+4>base+len(image):
        raise ValueError("candidate interval outside ARM9 image")
    # Guard this as the actual source load discovered by V9.3.
    source=w32(image,source_pc-base)
    if ((source>>26)&3)!=1 or not(source&(1<<20)) or (
         (source>>16)&15)!=reg or ((source>>12)&15)!=1 or (
         source&0xfff)!=104 or (source>>28)==15:
        raise ValueError("original V9.3 A8 source LDR no longer matches")
    start_word=w32(image,entry-base)
    if (start_word&0xffff4000)!=0xe92d4000 and start_word!=0xe52de004:
        raise ValueError("V9.7 nearest entry prologue no longer matches")
    states={entry:initial_state()}
    queue=deque([entry])
    transitions=Counter()
    writer_sites={}
    blocked=Counter()
    processed=0
    outside_edges=set()
    while queue:
        pc=queue.popleft()
        state=states[pc]
        if pc==source_pc:
            continue
        processed+=1
        if processed>MAX_ITERATIONS:
            raise ValueError("abstract CFG failed bounded convergence")
        word=w32(image,pc-base)
        cond=word>>28
        kind,executed,next_pc=action(word,pc,state,image,base)
        transitions[kind]+=1
        successors=[]
        if next_pc is not None:
            successors.append((next_pc,executed))
        else:
            blocked[kind]+=1
        if cond not in (14,15):
            # CPSR predicates are unknown. Both execute and skip are possible.
            successors.append((pc+4,state))
            transitions["conditional_skip_possible"]+=1
        if executed!=state and executed[reg]!=state[reg]:
            writer_sites[hx(pc)]={"instruction_class":kind,
                                  "condition":"al" if cond==14 else "conditional",
                                  "possible_new_origins":sorted(executed[reg]),
                                  "actual_writer_proven":False}
        for dst,newstate in successors:
            if not entry<=dst<=source_pc or dst%4:
                outside_edges.add((hx(pc),hx(dst)))
                continue
            merged=join(states.get(dst),newstate)
            if merged!=states.get(dst):
                states[dst]=merged
                queue.append(dst)
    reached=source_pc in states
    result_origins=sorted(states[source_pc][reg]) if reached else []
    return {
        "candidate_function_entry":hx(entry),
        "source_load_pc":hx(source_pc),
        "following_store_pc":hx(store_pc),
        "source_base_register":f"r{reg}",
        "bounded_instruction_count":(source_pc-entry)//4,
        "syntactic_source_reachable_from_candidate_entry":reached,
        "possible_source_base_origins":result_origins,
        "potential_register_writer_sites":dict(sorted(writer_sites.items())),
        "abstract_nodes_visited":len(states),
        "abstract_transitions":dict(sorted(transitions.items())),
        "blocked_instruction_classes":dict(sorted(blocked.items())),
        "edges_outside_candidate_interval_count":len(outside_edges),
        "edges_outside_candidate_interval":sorted(
            [{"from":a,"to":b} for a,b in outside_edges],
            key=lambda row:(row["from"],row["to"]))[:16],
        "outside_edge_list_truncated":len(outside_edges)>16,
        "all_incoming_edges_known":False,
        "candidate_entry_is_real_function_proven":False,
        "predicate_flags_or_live_registers_known":False,
        "real_reaching_definitions_proven":False
    }

def analysis(path,v96,v92):
    checked=v96.analyze(path,v92)
    meta,img=v92.v90.v75.v74.reconstruct(path,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"]!=checked["arm9_runtime_sha256"]:
        raise ValueError("original ARM9 digest changed")
    base=int(meta["arm9"]["ram_load"],16)
    original_anchors=checked["original_v90_anchors"]
    rows={}
    for name,entry,pc,reg,store in ANCHORS:
        if int(original_anchors[name]["access_pc"],16)!=store:
            raise ValueError("original store anchor mismatched: "+name)
        rows[name]=examine(img,base,entry,pc,reg,store)
    return {"game_code":checked["game_code"],
            "rom_sha1":checked["rom_sha1"],
            "arm9_runtime_sha256":checked["arm9_runtime_sha256"],
            "candidate_regions":rows}

def compare(hg,ss):
    by={hg["game_code"]:hg,ss["game_code"]:ss}
    if set(by)!={"IPKE","IPGE"}:
        raise ValueError("requires original US HeartGold and SoulSilver")
    a,b=by["IPKE"],by["IPGE"]
    same={name:a["candidate_regions"][name]==b["candidate_regions"][name]
          for name,_,_,_,_ in ANCHORS}
    return {"tool":"hgss-v9.8-candidate-branch-aware-register-origins",
            "heartgold":a,"soulsilver":b,
            "cross_title":{"equivalent_candidate_region_reports":same,
                           "all_equivalent":all(same.values())},
            "limitations":[
                "candidate prologue entries unproven",
                "incoming branches from outside region not included",
                "conditional CPSR flags unknown",
                "BL and BLX conservatively clobber all abstract registers",
                "unrecognized PC/control instructions terminate a path",
                "no Thumb, overlay code or runtime execution trace"],
            "runtime_execution_proven":False,
            "true_scheduler_ABI_proven":False,
            "safe_to_create_resident_worker":False,
            "ARM7_wifi_ownership_proven":False,
            "wifi_enabled":False,
            "rom_save_or_walker_modified":False,
            "next_gate":"Evaluate candidate origin sets, then prove actual control flow and ABI before attempting resident Wi-Fi."}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",nargs="?",type=Path)
    p.add_argument("soulsilver",nargs="?",type=Path)
    p.add_argument("--rom-dir",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args(argv)
    try:
        def load(alias,path):
            spec=importlib.util.spec_from_file_location(alias,path)
            if spec is None or spec.loader is None:
                raise ValueError("dependency missing: "+str(path))
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        v96=load("v98_v96",HERE.parent/"v9_6"/"hgss_full_arm9_effective_xrefs.py")
        v92=load("v98_v92",HERE.parent/"v9_2"/"hgss_store_value_backtrace.py")
        if args.rom_dir:
            if args.heartgold or args.soulsilver:
                raise ValueError("use --rom-dir OR two ROM paths")
            v95=load("v98_v95",HERE.parent/"v9_5"/"hgss_full_rom_index.py")
            hg,ss=v95.discover_roms(args.rom_dir)
        elif args.heartgold and args.soulsilver:
            hg,ss=args.heartgold.resolve(),args.soulsilver.resolve()
        else:
            raise ValueError("provide both ROMs or --rom-dir")
        if hg==ss:
            raise ValueError("two distinct ROM files required")
        if args.output and (args.output.resolve() in (hg,ss) or
                            args.output.suffix.lower() in FORBIDDEN):
            raise ValueError("refusing to overwrite ROM/save file")
        out=compare(analysis(hg,v96,v92),analysis(ss,v96,v92))
        payload=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
            print("V9.8 static analysis written:",args.output)
            for game in ("heartgold","soulsilver"):
                for name,row in out[game]["candidate_regions"].items():
                    print(game,name,"reached:",row["syntactic_source_reachable_from_candidate_entry"],
                          "origin_count:",len(row["possible_source_base_origins"]))
        else:
            print(payload,end="")
        return 0
    except (OSError,ValueError,struct.error) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
