#!/usr/bin/env python3
"""V9.3 — find the *base register* of three original HGSS ARM9 source loads.

The user's V9.2 audit proved three identical HG/SS patterns (static):
  STR r1 -> 0x021E16A8 after LDR r1,[r0] at 0x020D189C;
  STR r1 -> 0x021E16A8 after LDR r1,[r8] at 0x020D202C;
  STR r1 -> 0x021E16A8 after LDR r1,[r7] at 0x020D20CC.
The fourth store to 0x021E16AC has unresolved r5 provenance
behind a branch; this script does NOT cross that branch.

This read-only offline auditor validates the exact original US Rev0 ROM,
ARM9 digest, preceding V9.2 static source and memory-load instruction,
then looks backwards at most 16 A32 instructions to find a possible
writer of r0/r8/r7. V9.2's conservative register-writer routine
stops at a branch, condition, unknown instruction or bound. The
source load's base register may be overwritten AFTER the load by
the literal LDR of the store destination: this is explicitly recorded
and never mistaken for the source-load address.

No live RAM, pointer dereferences, game save access, thread creation,
Wi-Fi, radio ownership inference, or original ROM opcode export.
Static nearest-writer syntax does not prove actual control flow.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
P92=HERE.parent/"v9_2"/"hgss_store_value_backtrace.py"
spec=importlib.util.spec_from_file_location("v93_v92",P92)
v92=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v92)
v90=v92.v90

BACKWARD_WORDS=16
SOURCES={
    "scheduler_list_store_a":(0x020D189C,0,1,0x020D18A4),
    "scheduler_list_store_b":(0x020D202C,8,1,0x020D2034),
    "scheduler_list_store_c":(0x020D20CC,7,1,0x020D20D4),
}
BLOCKED_CALLBACK=("callback_candidate_read",0x020D21CC)
FORBIDDEN_OUTPUT_SUFFIXES={".nds",".sav",".dsv",".walker",".srm",".dat"}

class BaseOriginError(ValueError):
    pass


def analyze_image(img,base,v92_result):
    if v92_result["game_code"] not in ("IPKE","IPGE"):
        raise BaseOriginError("unrecognized original USA title")
    records={}
    for name,(source_load_pc,expected_base,expected_value,store_pc) in SOURCES.items():
        upstream=v92_result["records"][name]
        upstream_origin=upstream["source_register_origin"]
        if (upstream["store_pc"]!=v92.hx(store_pc) or
            upstream["destination"]!="0x021E16A8" or
            upstream["store_value_register"]!=f"r{expected_value}" or
            upstream_origin.get("kind")!="load_from_unknown_runtime_memory" or
            upstream_origin.get("writer_pc")!=v92.hx(source_load_pc) or
            upstream_origin.get("address_register")!=f"r{expected_base}"):
            raise BaseOriginError(f"V9.2 source writer no longer matches: {name}")
        off=source_load_pc-base
        store_off=store_pc-base
        if (source_load_pc&3 or store_pc&3 or
            not(0<=off and off+4<=len(img)) or
            not(0<=store_off and store_off+4<=len(img)) or
            not source_load_pc<store_pc):
            raise BaseOriginError("source load/store outside original image")
        load=struct.unpack_from("<I",img,off)[0]
        mem=v90.safe_mem_access(load)
        if (mem is None or mem["access"]!="load" or
            mem["width"]!="word" or
            (load>>16)&15!=expected_base or
            (load>>12)&15!=expected_value):
            raise BaseOriginError(f"source-load opcode mismatch: {name}")

        # Observe whether the destination literal load overwrites the
        # original source address register *after* the source RAM load.
        # It MUST NOT be attributed to the earlier source-load address.
        destpc=int(upstream["source_pc"],16)
        dest_off=destpc-base
        if not(0<=dest_off and dest_off+4<=len(img)):
            raise BaseOriginError("destination literal LDR outside original image")
        dest_word=struct.unpack_from("<I",img,dest_off)[0]
        dest=v90.v84.v82.decode_pc_literal(dest_word,destpc)
        if dest is None or not(0<=dest[0]<=12):
            raise BaseOriginError("original store-destination source LDR invalid")
        if not(source_load_pc<destpc<store_pc):
            raise BaseOriginError("source/store PC order changed")

        earliest=max(base,source_load_pc-BACKWARD_WORDS*4)
        candidate=v92._origin(img,base,expected_base,
                             source_load_pc-4,earliest,0)

        # We record a possible effective address only for a literal
        # aligned NTR RAM address loaded directly into source base.
        # Never read data at that address or follow it as a pointer.
        static_target=None
        if (candidate.get("kind")=="pc_literal_value" and
            candidate.get("constant_class")==
            "aligned_ntr_ram_address_constant"):
            constant=int(candidate["safe_constant"],16)
            static_target=v92.hx(
                (constant+mem["signed_offset"])&0xffffffff
            )
        records[name]={
            "source_load_pc":v92.hx(source_load_pc),
            "source_load_value_register":f"r{expected_value}",
            "source_load_base_register":f"r{expected_base}",
            "source_load_signed_offset":mem["signed_offset"],
            "store_pc":v92.hx(store_pc),
            "store_target":"0x021E16A8",
            "store_destination_literal_pc":v92.hx(destpc),
            "store_literal_destination_register":f"r{dest[0]}",
            "source_base_overwritten_by_later_store_literal":
                dest[0]==expected_base,
            "source_base_origin_before_load":candidate,
            "static_address_if_direct_original_literal":static_target,
            "static_address_is_not_a_runtime_memory_read":True,
            "preceding_window_words":BACKWARD_WORDS,
            "executed_path_proven":False,
            "live_runtime_address_register_known":False,
            "real_thread_object_proven":False,
        }

    callback=v92_result["records"][BLOCKED_CALLBACK[0]]
    source=callback["source_register_origin"]
    if (callback["destination"]!="0x021E16AC" or
        source.get("kind")!="unresolved" or
        source.get("stop_pc")!=v92.hx(BLOCKED_CALLBACK[1])):
        raise BaseOriginError("callback source branch barrier mismatch")
    return {
        "game_code":v92_result["game_code"],
        "three_original_a8_load_bases_verified":True,
        "records":records,
        "callback_0x021E16AC":{
            "stop_pc":source["stop_pc"],
            "source_register":"r5",
            "reason":"control-flow boundary; deliberately not crossed",
            "source_value_unknown":True,
        },
        "original_rom_code_bytes_exported":False,
        "runtime_RAM_followed":False,
    }


def analyze_game(rom):
    # Re-run strict original ROM SHA1/ARM9 reconstruction/ABI/PC
    # fingerprints and static V9.2 writer verification from scratch.
    previous=v92.analyze_game(rom)
    meta,img=v90.v75.v74.reconstruct(rom,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"]!=previous["original_runtime_sha256"]:
        raise BaseOriginError("original ROM ARM9 image SHA-256 changed")
    result=analyze_image(img,int(meta["arm9"]["ram_load"],16),previous)
    result["original_rom_sha1"]=previous["original_rom_sha1"]
    result["original_runtime_sha256"]=previous["original_runtime_sha256"]
    return result


def compare(first,second):
    codes={first["game_code"]:first,second["game_code"]:second}
    if (set(codes)!={"IPKE","IPGE"} or
        first["game_code"]==second["game_code"]):
        raise BaseOriginError("original USA Rev0 HG and SS are both required")
    hg,ss=codes["IPKE"],codes["IPGE"]
    checks={}
    for name in SOURCES:
        left,right=hg["records"][name],ss["records"][name]
        checks[name]={
            "same_source_load_pc":left["source_load_pc"]==right["source_load_pc"],
            "same_static_address_register_origin":
                left["source_base_origin_before_load"]==
                right["source_base_origin_before_load"],
            "same_source_overwrite_after_load":
                left["source_base_overwritten_by_later_store_literal"]==
                right["source_base_overwritten_by_later_store_literal"],
            "runtime_control_flow_verified":False,
        }
    return {
        "tool":"hgss-v9.3-original-arm9-source-load-address-register-origins",
        "heartgold":hg,
        "soulsilver":ss,
        "cross_title":checks,
        "all_three_source_load_base_origins_equivalent":
            all(all(v for k,v in item.items() if k!="runtime_control_flow_verified")
                for item in checks.values()),
        "scheduler_osthreadinfo_base_proven":False,
        "original_thread_object_dereferenced":False,
        "safe_to_create_worker_thread":False,
        "bootstrap_owned_persistent_stack_proven":False,
        "ARM7_WiFi_irq_or_radio_owned":False,
        "wifi_enabled":False,
        "rom_or_save_modified":False,
        "next_gate":"Determine source base registers before the three A8 stores and establish real scheduler ABI; never infer executable paths from this backwards byte-window alone.",
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("heartgold",type=Path)
    parser.add_argument("soulsilver",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    try:
        hg,ss=args.heartgold.resolve(),args.soulsilver.resolve()
        if hg==ss:
            raise BaseOriginError("two distinct original ROMs required")
        if args.output and (
            args.output.resolve() in (hg,ss) or
            args.output.suffix.lower() in FORBIDDEN_OUTPUT_SUFFIXES
        ):
            raise BaseOriginError("refusing ROM or save filename as output")
        data=compare(analyze_game(hg),analyze_game(ss))
        payload=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
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
