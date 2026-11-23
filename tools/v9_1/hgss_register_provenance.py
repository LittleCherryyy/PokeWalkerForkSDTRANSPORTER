#!/usr/bin/env python3
"""V9.1 — exact-ROM, bounded ARM9 register data-origin audit.

Goal: refine eight original HGSS scheduler-related code windows reported
by V9.0. For each original PC-relative literal LDR, track:
  * the *static address* held in a register, but NEVER follow pointers;
  * values read from that static address as abstract provenance tags;
  * immediate +/- constants applied to tagged read values;
  * whether a following STR writes a tagged value to the SAME address;
  * whether CMP/TST compares a tagged read value against zero.

All analysis is done offline on user's original US Rev0 ROM files.
No actual ROM instructions, Pokémon payloads or saves are exported.
Only conservative ARM A32 straight-line semantics, max 8 words,
stop on branch, conditional, PC write, memory indirect/unrecognized.
Syntactic matches are NOT proof of executed game code or safe threads.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
P90=HERE.parent/"v9_0"/"hgss_arm9_thread_trace_windows.py"
spec=importlib.util.spec_from_file_location("v91_v90",P90)
v90=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v90)

WINDOW=v90.WINDOW_INSTRUCTIONS
SAVE_SUFFIXES={".nds",".sav",".dsv",".walker",".srm",".dat"}

class ProvenanceError(ValueError):
    pass


def _hex(x):
    return f"0x{x:08X}"


def _tag_copy(tags,r):
    return copy.deepcopy(tags.get(r))


def trace_provenance(img,base,source_pc,reg,literal_address):
    """Read bounded *instruction words from local ROM image* only.

    Abstractly propagate register *provenance* but do not look up any
    value stored at the calculated RAM address. Pointer-like data loaded
    from game RAM remain opaque non-address values.
    """
    off=source_pc-base
    if not (0<=reg<=12 and source_pc%4==0 and off>=0 and
            off+WINDOW*4<=len(img)):
        raise ProvenanceError("invalid or out-of-range original ARM window")
    pointer_regs={reg:literal_address}
    value_regs={}
    steps=[]
    for i in range(1,WINDOW):
        pc=source_pc+i*4
        w=struct.unpack_from("<I",img,pc-base)[0]
        here=_hex(pc)
        if (w>>28)!=0xE:
            steps.append({"pc":here,"kind":"stop_conditional_instruction"})
            break
        if ((w>>25)&7)==5 or (w&0x0ffffff0) in (0x012fff10,0x012fff30):
            steps.append({"pc":here,"kind":"stop_control_flow"})
            break
        if ((w>>24)&15)==15:
            steps.append({"pc":here,"kind":"stop_software_interrupt"})
            break
        a=v90.safe_mem_access(w)
        if a:
            rn=(w>>16)&15
            rt=(w>>12)&15
            rw=a["access"]
            if rt==15 or rn==15:
                steps.append({"pc":here,"kind":"stop_pc_register_access"})
                break
            base_addr=pointer_regs.get(rn)
            location=(
                (base_addr+a["signed_offset"])&0xffffffff
                if base_addr is not None else None
            )
            # Save provenance of STORE register BEFORE invalidating
            # anything; load register and base register can coincide.
            prior=_tag_copy(value_regs,rt)
            source_literal=pointer_regs.get(rt)
            op={
                "pc":here,
                "kind":"memory_read" if rw=="load" else "memory_write",
                "width":a["width"],
                "effective_address":_hex(location) if location is not None else None,
                "effective_address_derived_from_literal":location is not None,
                "runtime_ram_value_read":False,
                "executed_instruction_proven":False,
            }
            if rw=="load":
                pointer_regs.pop(rt,None)
                value_regs.pop(rt,None)
                if location is not None:
                    value_regs[rt]={
                        "read_address":_hex(location),
                        "width":a["width"],
                        "transforms":[],
                    }
            else:
                op["value_provenance"]=prior
                op["value_originates_at_same_address"]=bool(
                    prior is not None and location is not None and
                    prior["read_address"]==_hex(location)
                )
                op["value_is_known_original_literal"]=(
                    _hex(source_literal)
                    if source_literal is not None else None
                )
                op["read_modify_write_candidate"]=bool(
                    op["value_originates_at_same_address"] and
                    prior["transforms"]
                )
            steps.append(op)
            continue
        # Only register-neutral operations are permitted below.
        if (w>>26)&3 or ((w&0x90)==0x90 and not(w&(1<<25))):
            steps.append({"pc":here,"kind":"stop_unrecognized_instruction"})
            break
        opcode=(w>>21)&15
        dst=(w>>12)&15
        rn=(w>>16)&15
        immediate=bool(w&(1<<25))
        if not immediate and (w&0xff0):
            steps.append({"pc":here,"kind":"stop_register_shift"})
            break
        src=w&15 if not immediate else None
        n=v90.imm_operand2(w) if immediate else None
        if opcode in (8,10):  # TST or CMP, no register write
            observed=_tag_copy(value_regs,rn)
            steps.append({
                "pc":here,
                "kind":"test_value" if opcode==8 else "compare_value",
                "immediate":n,
                "register_value_provenance":observed,
                "compares_loaded_value_to_zero":bool(
                    opcode==10 and immediate and n==0 and
                    observed is not None and
                    observed["transforms"]==[]
                ),
                "actual_test_outcome_known":False,
            })
            continue
        if dst==15:
            steps.append({"pc":here,"kind":"stop_pc_write"})
            break
        if opcode==13 and not immediate:  # MOV, Rm no shift
            previous_ptr=pointer_regs.get(src)
            previous_tag=_tag_copy(value_regs,src)
            pointer_regs.pop(dst,None)
            value_regs.pop(dst,None)
            if previous_ptr is not None:
                pointer_regs[dst]=previous_ptr
            if previous_tag is not None:
                value_regs[dst]=previous_tag
            steps.append({
                "pc":here,"kind":"move_register",
                "pointer_literal_propagated":previous_ptr is not None,
                "read_value_provenance":previous_tag,
            })
            continue
        if opcode in (2,4) and immediate: # SUB/ADD, Operand2 rotate imm
            previous_ptr=pointer_regs.get(rn)
            previous_tag=_tag_copy(value_regs,rn)
            pointer_regs.pop(dst,None)
            value_regs.pop(dst,None)
            if previous_ptr is not None:
                pointer_regs[dst]=(
                    previous_ptr+n if opcode==4 else previous_ptr-n
                )&0xffffffff
            if previous_tag is not None:
                # No actual value of RAM ever flows through the tool.
                previous_tag["transforms"].append({
                    "operation":"add" if opcode==4 else "sub",
                    "immediate":n,
                })
                value_regs[dst]=previous_tag
            steps.append({
                "pc":here,
                "kind":"increment_or_decrement",
                "operation":"add" if opcode==4 else "sub",
                "immediate":n,
                "transforms_loaded_ram_value":previous_tag is not None,
                "known_literal_address_modified":
                    previous_ptr is not None,
            })
            continue
        steps.append({"pc":here,"kind":"stop_unrecognized_instruction"})
        break
    matched_rmw=[]
    matched_compare_zero=[]
    for step in steps:
        if step.get("read_modify_write_candidate"):
            matched_rmw.append({
                "store_pc":step["pc"],
                "effective_address":step["effective_address"],
                "provenance":step["value_provenance"],
            })
        if step.get("compares_loaded_value_to_zero"):
            matched_compare_zero.append({
                "compare_pc":step["pc"],
                "provenance":step["register_value_provenance"],
            })
    return {
        "instructions_after_source_examined":len(steps),
        "steps":steps,
        "read_modify_write_same_address_candidates":matched_rmw,
        "compare_loaded_halfword_or_word_to_zero_candidates":matched_compare_zero,
        "instructions_executed_on_hardware_proven":False,
        "true_scheduler_fields_proven":False,
        "live_RAM_dereferences":False,
    }


def analyze_image(img,base,v90_result):
    if v90_result["game_code"] not in ("IPKE","IPGE"):
        raise ProvenanceError("unknown original title")
    records={}
    for name,(pc,expected_addr,expected_direction,expected_width) in v90.ANCHORS.items():
        prior=v90_result["records"][name]
        off=pc-base
        if off<0 or pc%4 or off+WINDOW*4>len(img):
            raise ProvenanceError("source window outside original ARM9")
        source_word=struct.unpack_from("<I",img,off)[0]
        literal_pc=int(prior["source_literal"],16)
        source_reg=v90.v84.v82.decode_pc_literal(source_word,pc)
        if (source_reg is None or source_reg[1]!=literal_pc or
            source_reg[0]>12):
            raise ProvenanceError("original PC-literal LDR mismatch")
        lit_off=literal_pc-base
        if lit_off<0 or lit_off+4>len(img):
            raise ProvenanceError("source literal outside image")
        candidate=struct.unpack_from("<I",img,lit_off)[0]
        if candidate!=int(prior["loaded_candidate_ram_base"],16):
            raise ProvenanceError("source literal changed")
        result=trace_provenance(img,base,pc,source_reg[0],candidate)
        first=result["steps"][0] if result["steps"] else {}
        if (
            first.get("kind")!=(
                "memory_read" if expected_direction=="load" else "memory_write"
            ) or first.get("width")!=expected_width or
            first.get("effective_address")!=_hex(expected_addr)
        ):
            raise ProvenanceError(f"original first memory access mismatched: {name}")
        original_steps=prior["semantic_steps"]
        if not original_steps or original_steps[0]["pc"]!=first["pc"]:
            raise ProvenanceError("V9.0 first access semantic mismatch")
        records[name]={
            "source_instruction":_hex(pc),
            "verified_initial_access":_hex(expected_addr),
            **result,
        }
    return {
        "game_code":v90_result["game_code"],
        "all_eight_original_anchor_checks_passed":True,
        "records":records,
        "original_arm_code_or_rom_bytes_exported":False,
        "verified_OSThreadInfo_base":False,
        "wifi_enabled":False,
    }


def analyze_game(rom):
    # Mandatory chain: original SHA-1 and exact ARM9/OS ABI signature
    # revalidated by the V9.0 analyzer. No untrusted ROM allowed.
    previous=v90.analyze_game(rom)
    meta,img=v90.v75.v74.reconstruct(rom,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"]!=previous["arm9_runtime_sha256"]:
        raise ProvenanceError("original ARM9 reconstruction mismatch")
    base=int(meta["arm9"]["ram_load"],16)
    result=analyze_image(img,base,previous)
    result["rom_sha1"]=previous["rom_sha1"]
    result["arm9_runtime_sha256"]=previous["arm9_runtime_sha256"]
    return result


def compare(first,second):
    by_code={first["game_code"]:first,second["game_code"]:second}
    if set(by_code)!={"IPKE","IPGE"} or first["game_code"]==second["game_code"]:
        raise ProvenanceError("both original USA Rev0 HG and SS required")
    hg,ss=by_code["IPKE"],by_code["IPGE"]
    consistency={}
    for name in v90.ANCHORS:
        a,b=hg["records"][name],ss["records"][name]
        consistency[name]={
            "source_instruction":a["source_instruction"],
            "same_instruction_provenance":a["steps"]==b["steps"],
            "same_rmw_candidates":a["read_modify_write_same_address_candidates"]==
                                  b["read_modify_write_same_address_candidates"],
            "same_zero_comparisons":a["compare_loaded_halfword_or_word_to_zero_candidates"]==
                                    b["compare_loaded_halfword_or_word_to_zero_candidates"],
            "confirmed_executed_game_function":False,
        }
    return {
        "tool":"hgss-v9.1-original-arm9-register-value-provenance",
        "heartgold":hg,
        "soulsilver":ss,
        "cross_title":consistency,
        "eight_anchor_provenance_equal":all(
            c["same_instruction_provenance"] for c in consistency.values()
        ),
        "legacy_OSThreadInfo_at_0x021E169C_confirmed":False,
        "OSi_ThreadInfo_at_0x021E16A0_confirmed":False,
        "thread_list_dereferenced":False,
        "proven_non_irq_thread_context":False,
        "bootstrap_owned_worker_stack_proven":False,
        "safe_to_create_or_wakeup_threads":False,
        "ARM7_wifi_driver_or_irq_owned":False,
        "wifi_enabled":False,
        "rom_or_save_modified":False,
        "next_gate":"Review provenance of the 169C increment, the A0 compare-to-zero and stores to A8/AC. No live pointer reads, thread creation or Wi-Fi until actual scheduler ABI/ownership is proven.",
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
            raise ProvenanceError("require two distinct original ROMs")
        if args.output and (
            args.output.resolve() in (hg,ss) or
            args.output.suffix.lower() in SAVE_SUFFIXES
        ):
            raise ProvenanceError("refusing to overwrite ROM or save extension")
        result=compare(analyze_game(hg),analyze_game(ss))
        output=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(output,encoding="utf-8")
        print(output,end="")
        return 0
    except (OSError,ValueError,struct.error) as exc:
        print("ERROR: "+str(exc),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
