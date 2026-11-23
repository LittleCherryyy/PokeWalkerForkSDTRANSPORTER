#!/usr/bin/env python3
"""V9.0: bounded offline ARM9 scheduler-field instruction windows.

Extends original USA Rev0 HGSS V8.9 field-XREF metadata by tracing
at most 8 straight-line A32 instructions after a VERIFIED literal
load at seven fixed important instruction sites. This does NOT execute
game code. It recognizes only a small safe subset of ARM instructions
(LDR/STR/LDRH/STRH, MOV, ADD/SUB immediate, CMP/TST immediate).
It fails closed on branches, conditional execution, PC writes, or
unknown instructions. Only semantic metadata is exported; no ROM
bytes or disassembled original code are emitted.

Do not follow values in live RAM or infer verified OSThreadInfo from
syntactic matches. No Wi-Fi, save writes or bootstrap changes.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
P89=HERE.parent/"v8_9"/"hgss_scheduler_field_xrefs.py"
spec=importlib.util.spec_from_file_location("v90_v89",P89)
v89=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v89)
v85=v89.v85
v84=v89.v84
v75=v89.v75

WINDOW_INSTRUCTIONS=8  # hard bound, including the source LDR
NTR_RAM_START=0x02000000
NTR_RAM_END=0x023FFFFF

# Validated from the user's actual V8.9 JSON, both original US Rev0
# ROMs. These are syntactic references, not confirmed active functions.
# (source LDR PC, computed accessed word/halfword, access kind, width)
ANCHORS={
    "halfword_header_control":(0x02111908,0x021E16A0,"load","halfword"),
    "legacy_candidate_169c":(0x020D16C0,0x021E169C,"load","word"),
    "scheduler_list_store_a":(0x020D18A0,0x021E16A8,"store","word"),
    "scheduler_list_store_b":(0x020D2030,0x021E16A8,"store","word"),
    "scheduler_list_store_c":(0x020D20D0,0x021E16A8,"store","word"),
    "scheduler_list_read":(0x020D1F5C,0x021E16A8,"load","word"),
    "current_candidate_read":(0x020A6878,0x021E16A4,"load","word"),
    "callback_candidate_read":(0x020D21D0,0x021E16AC,"load","word"),
}


class TraceError(ValueError):
    pass


def imm_operand2(word):
    """Decode ARM Operand2 8-bit-rotate immediate (not a pointer)."""
    v=word&0xff
    shift=((word>>8)&15)*2
    if not shift:
        return v
    return ((v>>shift)|(v<<(32-shift)))&0xffffffff


def safe_mem_access(word):
    """AL / pre-index / no writeback / immediate addressing only."""
    if word>>28!=14:
        return None
    rn=(word>>16)&15
    half=v89.decode_arm_immediate_halfword(word,rn)
    if half:
        return half
    return v85.direct_arm_access(word,rn)


def _record_access(word,pc,tracked):
    access=safe_mem_access(word)
    if access is None:
        return None
    rn=int(access["base_register"][1:])
    target=tracked.get(rn)
    if target is None:
        return {"kind":"untracked_memory_access","pc":f"0x{pc:08X}",
                "width":access["width"],"access":access["access"]}
    address=(target+access["signed_offset"])&0xffffffff
    return {
        "kind":"fixed_base_memory_access",
        "pc":f"0x{pc:08X}",
        "width":access["width"],
        "access":access["access"],
        "effective_address":f"0x{address:08X}",
        "inside_main_ram":NTR_RAM_START<=address<=NTR_RAM_END,
        "inside_header_candidate":0x021E169C<=address<=0x021E16B0,
        "derived_from_original_literal":True,
        "actual_memory_dereferenced":False,
        "scheduler_field_verified":False,
    }


def trace_straight_line(img,base,pc,rd,initial_address):
    if rd<0 or rd>12 or pc&3 or (pc-base)<0:
        raise TraceError("invalid initial ARM9 literal register/address")
    if (pc-base)+WINDOW_INSTRUCTIONS*4>len(img):
        raise TraceError("bounded trace extends outside original ARM9 image")
    tracked={rd:initial_address}
    steps=[]
    for i in range(1,WINDOW_INSTRUCTIONS):
        here=pc+4*i
        word=struct.unpack_from("<I",img,here-base)[0]
        if (word>>28)!=14:
            steps.append({"pc":f"0x{here:08X}","kind":"stop_conditional_instruction"})
            break
        # Never trace a branch, software interrupt, BX/BLX or PC write.
        if ((word>>25)&7)==5 or (word&0x0ffffff0) in (
            0x012fff10,0x012fff30
        ):
            steps.append({"pc":f"0x{here:08X}","kind":"stop_control_flow"})
            break
        if ((word>>24)&15)==15:
            steps.append({"pc":f"0x{here:08X}","kind":"stop_software_interrupt"})
            break
        access=safe_mem_access(word)
        if access is not None:
            rd2=(word>>12)&15
            if rd2==15 and access["access"]=="load":
                steps.append({"pc":f"0x{here:08X}","kind":"stop_pc_load"})
                break
            steps.append(_record_access(word,here,tracked))
            if access["access"]=="load":
                tracked.pop(rd2,None)  # The loaded RAM value is UNKNOWN.
            continue
        # Simple AL ARM data-processing only. Reject multiply/swap and
        # register shifts as unknown rather than making assumptions.
        if (word>>26)&3:
            steps.append({"pc":f"0x{here:08X}","kind":"stop_unrecognized_instruction"})
            break
        if (word&0x00000090)==0x90 and not (word&(1<<25)):
            steps.append({"pc":f"0x{here:08X}","kind":"stop_unrecognized_instruction"})
            break
        op=(word>>21)&15
        dst=(word>>12)&15
        rn=(word>>16)&15
        imm=bool(word&(1<<25))
        if not imm and word&0xff0:
            steps.append({"pc":f"0x{here:08X}","kind":"stop_register_shift"})
            break
        src=(word&15) if not imm else None
        val=imm_operand2(word) if imm else None
        if op in (10,8): # CMP/TST; modifies flags only
            steps.append({
                "pc":f"0x{here:08X}",
                "kind":"compare_immediate" if imm else "compare_register",
                "constant":val if imm else None,
                "tracked_left_operand":rn in tracked,
            })
            continue
        if dst==15:
            steps.append({"pc":f"0x{here:08X}","kind":"stop_pc_write"})
            break
        if op==13 and not imm: # MOV Rd,Rm; no shift
            old=tracked.get(src)
            tracked.pop(dst,None)
            if old is not None:
                tracked[dst]=old
            steps.append({"pc":f"0x{here:08X}","kind":"mov_register",
                          "tracked_pointer_propagated":old is not None})
            continue
        if op in (4,2) and imm: # ADD/SUB immediate
            origin=tracked.get(rn)
            tracked.pop(dst,None)
            if origin is not None:
                new=(origin+val if op==4 else origin-val)&0xffffffff
                tracked[dst]=new
            steps.append({
                "pc":f"0x{here:08X}",
                "kind":"add_immediate" if op==4 else "sub_immediate",
                "immediate":val,
                "tracked_pointer_propagated":origin is not None,
            })
            continue
        steps.append({"pc":f"0x{here:08X}","kind":"stop_unrecognized_instruction"})
        break
    return {
        "max_instructions_including_source":WINDOW_INSTRUCTIONS,
        "instructions_after_source_examined":len(steps),
        "semantic_steps":steps,
        "traced_executable_path_proven":False,
        "thread_pointer_dereferenced":False,
    }


def analyze_image(img,base,upstream):
    v84.verify_original_entry(img,base)
    if upstream["game_code"] not in ("IPKE","IPGE"):
        raise TraceError("original USA game code not verified")
    keyed={}
    for a in upstream["direct_accesses"]:
        k=int(a["source_instruction"],16)
        if k in keyed:
            raise TraceError("duplicate xref source PC")
        keyed[k]=a
    records={}
    for name,(pc,target,access,width) in ANCHORS.items():
        row=keyed.get(pc)
        if row is None:
            raise TraceError(f"required original thread anchor {name} missing")
        if (int(row["effective_address"],16),row["access"],row["width"])!=(target,access,width):
            raise TraceError(f"original V8.9 access semantics mismatch: {name}")
        offset=pc-base
        if offset<0 or pc&3 or offset+4>len(img):
            raise TraceError("original ARM9 anchor out of bounds")
        word=struct.unpack_from("<I",img,offset)[0]
        reg=int(row["base_register"][1:])
        literal=int(row["source_literal"],16)
        if reg>12 or v84.v82.decode_pc_literal(word,pc)!=(reg,literal):
            raise TraceError("source LDR instruction failed original verification")
        lo=literal-base
        if lo<0 or lo+4>len(img):
            raise TraceError("original source literal out of bounds")
        literal_value=struct.unpack_from("<I",img,lo)[0]
        if literal_value!=int(row["literal_value"],16):
            raise TraceError("original ROM source literal value mismatch")
        end=offset+WINDOW_INSTRUCTIONS*4
        if end>len(img):
            raise TraceError("source trace exceeds original image")
        trace=trace_straight_line(img,base,pc,reg,literal_value)
        steps=trace["semantic_steps"]
        # First following access MUST match the user's V8.9 xref
        # and still originate from the verified literal.
        first=steps[0] if steps else {}
        if (first.get("kind")!="fixed_base_memory_access" or
            first.get("effective_address")!=f"0x{target:08X}" or
            first.get("access")!=access or first.get("width")!=width):
            raise TraceError("following ARM access no longer matches V8.9")
        records[name]={
            "original_literal_load_pc":f"0x{pc:08X}",
            "source_literal":f"0x{literal:08X}",
            "loaded_candidate_ram_base":f"0x{literal_value:08X}",
            "first_access_address":f"0x{target:08X}",
            "source_32byte_sha256":hashlib.sha256(img[offset:end]).hexdigest(),
            **trace,
        }
    return {
        "game_code":upstream["game_code"],
        "records":records,
        "all_original_v89_anchors_validated":True,
        "original_static_access_count":upstream["direct_access_count"],
        "original_new_halfword_access_count":
            upstream["newly_recognized_arm_halfword_access_count"],
        "rom_bytes_or_opcodes_exported":False,
        "thread_fields_proven":False,
    }


def analyze_game(rom):
    # Full V8.9 original ROM SHA1, decompressed ARM9 and prior V8.x
    # ABI/function-fingerprint validation are mandatory.
    v89result=v89.analyze_game(rom)
    data,img=v75.v74.reconstruct(rom,include_runtime_image=True)
    if data["arm9"]["runtime_decompressed_sha256"]!=v89result["arm9_runtime_sha256"]:
        raise TraceError("reconstructed original ARM9 digest mismatch")
    base=int(data["arm9"]["ram_load"],16)
    result=analyze_image(img,base,v89result)
    result["rom_sha1"]=v89result["rom_sha1"]
    result["arm9_runtime_sha256"]=v89result["arm9_runtime_sha256"]
    return result


def compare(first,second):
    by_code={first["game_code"]:first,second["game_code"]:second}
    if set(by_code)!={"IPKE","IPGE"} or first["game_code"]==second["game_code"]:
        raise TraceError("requires distinct original USA Rev0 HG and SS ROMs")
    hg,ss=by_code["IPKE"],by_code["IPGE"]
    compared={}
    for key in ANCHORS:
        x,y=hg["records"][key],ss["records"][key]
        compared[key]={
            "original_instruction_pc":x["original_literal_load_pc"],
            "matching_exact_32byte_code_hash":
                x["source_32byte_sha256"]==y["source_32byte_sha256"],
            "matching_semantic_trace":x["semantic_steps"]==y["semantic_steps"],
            "trace_executable_verified":False,
        }
    return {
        "tool":"hgss-v9.0-bounded-original-arm9-scheduler-semantic-windows",
        "reference_v89_shared_direct_accesses":38,
        "heartgold":hg,
        "soulsilver":ss,
        "comparisons":compared,
        "all_eight_anchor_windows_shared":{
            "number":len(compared),
            "matching_code_hash_and_semantics":all(
                x["matching_exact_32byte_code_hash"] and
                x["matching_semantic_trace"] for x in compared.values()),
        },
        "actual_OSi_ThreadInfo_base_proven":False,
        "thread_list_or_current_thread_dereferenced":False,
        "bootstrap_owned_thread_memory_proven":False,
        "safe_to_create_or_wakeup_thread":False,
        "ARM7_radio_ownership_proven":False,
        "wifi_enabled":False,
        "rom_save_walker_modified":False,
        "next_gate":"Review eight source-verified bounded straight-line semantic windows. Static similarities cannot authorize thread creation or WiFi.",
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",type=Path)
    p.add_argument("soulsilver",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args(argv)
    try:
        hg,ss=args.heartgold.resolve(),args.soulsilver.resolve()
        if hg==ss:
            raise TraceError("two distinct original ROMs required")
        if args.output and args.output.resolve() in (hg,ss):
            raise TraceError("refusing to overwrite original ROM")
        out=compare(analyze_game(hg),analyze_game(ss))
        payload=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
        print(payload,end="")
        return 0
    except (OSError,ValueError,struct.error) as ex:
        print("ERROR: "+str(ex),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
