#!/usr/bin/env python3
"""V9.2 — bounded backward register-writer audit for original HGSS ARM9.

Look backwards, without control-flow traversal, at source registers used
by three stores to 0x021E16A8 and one to 0x021E16AC. A syntactically
identified value producer is NOT proof of runtime provenance. The
original ROMs are verified by the V9.1 chain. No live RAM reads,
in-game modifications, thread creation, networking, or save access.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
P91=HERE.parent/"v9_1"/"hgss_register_provenance.py"
spec=importlib.util.spec_from_file_location("v92_v91",P91)
v91=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v91)
v90=v91.v90

MAX_BEFORE=12
MAX_CHAINS=3
STORE_ANCHORS=(
    "scheduler_list_store_a",
    "scheduler_list_store_b",
    "scheduler_list_store_c",
    "callback_candidate_read",
)
FORBIDDEN_OUTPUT_EXT={".nds",".sav",".dsv",".srm",".walker",".dat"}


class BacktraceError(ValueError):
    pass


def hx(x):
    return f"0x{x:08X}"


def _source_literal_kind(num):
    if num==0:
        return "zero"
    if num==1:
        return "one"
    if 0x02000000<=num<=0x023ffffc and num%4==0:
        return "aligned_ntr_ram_address_constant"
    return "other_constant_not_exported"


def _stop(reason,pc=None):
    return {"kind":"unresolved","reason":reason,
            "stop_pc":hx(pc) if pc is not None else None}


def _origin(img,base,reg,start,earliest,depth):
    """Conservative backward *syntactic* definition of an ARM register.

    No branching, Thumb, conditional, LDM/STM, memory-indirect pointer
    following or flags-dependent assumption. We never read runtime RAM.
    Any uncertain instruction blocks inference instead of being skipped.
    """
    if reg==15:
        return _stop("PC cannot be a normal value origin")
    if depth>=MAX_CHAINS:
        return _stop("maximum register-copy chain length reached")
    pc=start
    while pc>=earliest:
        off=pc-base
        if pc%4 or off<0 or off+4>len(img):
            return _stop("outside bounded original ARM9 image",pc)
        w=struct.unpack_from("<I",img,off)[0]
        if (w>>28)!=0xE:
            return _stop("conditional instruction blocks static lineage",pc)
        if ((w>>25)&7)==5 or (w&0x0ffffff0) in (0x012fff10,0x012fff30):
            return _stop("branch or BX/BLX boundary",pc)
        if ((w>>24)&15)==15:
            return _stop("software interrupt boundary",pc)

        # Direct original-ROM PC-relative LDR literal to a register.
        literal=v90.v84.v82.decode_pc_literal(w,pc)
        if literal is not None:
            rd,location=literal
            if rd==reg:
                li=location-base
                if li<0 or li+4>len(img):
                    return _stop("source literal outside original ARM9 image",pc)
                constant=struct.unpack_from("<I",img,li)[0]
                return {
                    "kind":"pc_literal_value",
                    "writer_pc":hx(pc),
                    "source_literal_pc":hx(location),
                    "constant_class":_source_literal_kind(constant),
                    # Export only zero/one/aligned RAM addresses, not
                    # arbitrary copyrighted data or executable opcodes.
                    "safe_constant":constant if constant in (0,1) else
                      (hx(constant) if _source_literal_kind(constant)==
                       "aligned_ntr_ram_address_constant" else None),
                    "actual_ram_read":False,
                }
            pc-=4
            continue

        mem=v90.safe_mem_access(w)
        if mem is not None:
            rt=(w>>12)&15
            if mem["access"]=="load" and rt==reg:
                return {
                    "kind":"load_from_unknown_runtime_memory",
                    "writer_pc":hx(pc),
                    "load_width":mem["width"],
                    "address_register":f"r{(w>>16)&15}",
                    "runtime_memory_followed":False,
                }
            # Recognized pre-index, immediate, no-writeback STR or
            # load to another register does not redefine reg.
            pc-=4
            continue

        if ((w>>25)&7)==4:
            return _stop("LDM/STM may modify registers",pc)
        if (w>>26)&3:
            return _stop("unsupported register-effect instruction",pc)
        if (w&0x90)==0x90 and not(w&(1<<25)):
            return _stop("multiply/swap/extra-load class",pc)

        op=(w>>21)&15
        dest=(w>>12)&15
        rn=(w>>16)&15
        immediate=bool(w&(1<<25))
        if not immediate and (w&0xff0):
            return _stop("register shift may affect provenance",pc)
        if op in (8,9,10,11):  # TST TEQ CMP CMN only flags
            pc-=4
            continue
        if dest!=reg:
            # ARM data processing writes only its explicit Rd.
            pc-=4
            continue
        if op==13:
            if immediate:
                constant=v90.imm_operand2(w)
                return {
                    "kind":"mov_immediate",
                    "writer_pc":hx(pc),
                    "constant_class":_source_literal_kind(constant),
                    "safe_constant":constant if constant in (0,1) else None,
                    "actual_ram_read":False,
                }
            source=w&15
            if source==reg:
                pc-=4  # MOV rN,rN is harmless
                continue
            return {
                "kind":"register_copy",
                "writer_pc":hx(pc),
                "from_register":f"r{source}",
                "source":_origin(img,base,source,pc-4,earliest,depth+1),
            }
        if op in (2,4) and immediate:
            amount=v90.imm_operand2(w)
            return {
                "kind":"arithmetic_from_register",
                "writer_pc":hx(pc),
                "operation":"add" if op==4 else "subtract",
                "immediate":amount,
                "from_register":f"r{rn}",
                "source":_origin(img,base,rn,pc-4,earliest,depth+1),
            }
        return _stop("writer opcode not modeled conservatively",pc)
    return _stop("no writer in the bounded straight-line predecessor window")


def analyze_image(img,base,prior):
    if prior["game_code"] not in ("IPKE","IPGE"):
        raise BacktraceError("unknown original US Rev0 title")
    records={}
    for name in STORE_ANCHORS:
        prev=prior["records"][name]
        source_pc=int(prev["source_instruction"],16)
        first=prev["steps"][0]
        store_pc=int(first["pc"],16) if first["kind"]=="memory_write" else None
        if name=="callback_candidate_read":
            first=prev["steps"][1]
            store_pc=int(first["pc"],16)
        if store_pc is None or first["kind"]!="memory_write":
            raise BacktraceError("original V9.1 store anchor missing")
        expected=int(first["effective_address"],16)
        start=store_pc-base
        if store_pc%4 or start<0 or start+4>len(img):
            raise BacktraceError("original store PC out of bounds")
        word=struct.unpack_from("<I",img,start)[0]
        mem=v90.safe_mem_access(word)
        if mem is None or mem["access"]!="store" or mem["width"]!="word":
            raise BacktraceError("original store opcode no longer matches")
        loaded=int(prev["verified_initial_access"],16)
        if expected!=loaded:
            raise BacktraceError("original store target changed")
        # Read only a bounded region *of original ROM instructions*.
        # Source LDR of target base is inside that window by construction.
        earliest=max(base,store_pc-4*MAX_BEFORE)
        rt=(word>>12)&15
        rb=(word>>16)&15
        if rt==15 or rb==15:
            raise BacktraceError("PC register unexpectedly used in store")
        origin=_origin(img,base,rt,store_pc-4,earliest,0)
        records[name]={
            "source_pc":hx(source_pc),
            "store_pc":hx(store_pc),
            "destination":hx(expected),
            "store_value_register":f"r{rt}",
            "store_address_register":f"r{rb}",
            "lookback_limit_instructions":MAX_BEFORE,
            "source_register_origin":origin,
            "executed_path_verified":False,
            "true_thread_field_verified":False,
            "actual_runtime_register_value_known":False,
            "rom_or_ram_write_performed":False,
        }
    return {
        "game_code":prior["game_code"],
        "all_original_v91_store_anchors_validated":True,
        "records":records,
        "syntactic_predecessor_not_control_flow_proof":True,
    }


def analyze_game(rom):
    # Preserve ALL original SHA1, ARM9 digest, ABI opcode, literal xref
    # and V9.1 exact-site guards before inspecting predecessor words.
    earlier=v91.analyze_game(rom)
    meta,img=v90.v75.v74.reconstruct(rom,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"]!=earlier["arm9_runtime_sha256"]:
        raise BacktraceError("original ARM9 runtime SHA-256 mismatch")
    result=analyze_image(img,int(meta["arm9"]["ram_load"],16),earlier)
    result["original_rom_sha1"]=earlier["rom_sha1"]
    result["original_runtime_sha256"]=earlier["arm9_runtime_sha256"]
    return result


def compare(hg,ss):
    by_code={hg["game_code"]:hg,ss["game_code"]:ss}
    if set(by_code)!={"IPKE","IPGE"} or hg["game_code"]==ss["game_code"]:
        raise BacktraceError("requires two original USA Rev0 titles")
    h,s=by_code["IPKE"],by_code["IPGE"]
    equivalent={
        name:{
            "same_store_pc":h["records"][name]["store_pc"]==
                            s["records"][name]["store_pc"],
            "same_store_value_register":
                h["records"][name]["store_value_register"]==
                s["records"][name]["store_value_register"],
            "same_bounded_source_writer":
                h["records"][name]["source_register_origin"]==
                s["records"][name]["source_register_origin"],
        } for name in STORE_ANCHORS
    }
    return {
        "tool":"hgss-v9.2-arm9-original-store-register-backtrace",
        "heartgold":h,"soulsilver":s,
        "cross_title":equivalent,
        "all_four_store_writer_traces_equivalent":all(
            all(v.values()) for v in equivalent.values()),
        "actual_OSi_ThreadInfo_structure_verified":False,
        "actual_thread_objects_read":False,
        "safe_to_create_worker_thread":False,
        "bootstrap_owned_long_lived_stack_verified":False,
        "ARM7_WiFi_IRQ_ownership_proven":False,
        "wifi_enabled":False,
        "rom_save_or_walker_modified":False,
        "next_gate":"Review register writers for A8 and AC, then prove original scheduler ABI before thread/ARM7 network changes.",
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",type=Path)
    p.add_argument("soulsilver",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args(argv)
    try:
        roms=[args.heartgold.resolve(),args.soulsilver.resolve()]
        if roms[0]==roms[1]:
            raise BacktraceError("require two separate original ROMs")
        if args.output and (
            args.output.resolve() in roms or
            args.output.suffix.lower() in FORBIDDEN_OUTPUT_EXT
        ):
            raise BacktraceError("refusing output to original ROM/save extension")
        result=compare(analyze_game(args.heartgold),analyze_game(args.soulsilver))
        payload=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
        print(payload,end="")
        return 0
    except (OSError,ValueError,struct.error) as exc:
        print("ERROR: "+str(exc),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
