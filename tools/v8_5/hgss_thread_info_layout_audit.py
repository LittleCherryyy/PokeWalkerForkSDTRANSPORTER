#!/usr/bin/env python3
"""V8.5 original HGSS ARM9 thread-info *candidate* access analysis.

The user's V8.4 metadata reports 101 matching static ARM LDR
cross-references per game. The strongest candidates are 0x021E16A0
(64 sites) and 0x021E167C (29 sites). This script revalidates exact
original US Rev0 games and their thread-flag opcodes, then checks
*single immediate next ARM instruction* access patterns from each
candidate loading site. It never follows the pointer or reads live RAM.
A one-step syntactic match is NOT proof of execution or field layout.

NitroSDK thread.h publishes two alternative OSThreadInfo layouts:
SDK_THREAD_INFINITY: current +4, list +8, switchCallback +12.
Older SDK: current +8, list +12, switchCallback +16.
We compare syntactic offsets without selecting a version based only
on a nearby address. No ROM bytes / opcodes exported; no Wi-Fi/saves.
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
P84=HERE.parent/"v8_4"/"hgss_thread_flag_xrefs.py"
spec=importlib.util.spec_from_file_location("v85_v84",P84)
v84=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v84)
v75=v84.v75

CANDIDATES=(0x021E16A0,0x021E167C)
MAX_FOLLOW=1
LAYOUTS={
    "SDK_THREAD_INFINITY":{"current":4,"list":8,"switchCallback":12},
    "legacy_fixed_thread_limit":{"current":8,"list":12,"switchCallback":16},
}

class ThreadLayoutError(ValueError):
    pass


def direct_arm_access(word,expected_base):
    """An AL, register-base ARM immediate single word/byte LDR/STR.

    Rejects conditional, register-offset, post-index, writeback and
    potential base modification. Never decodes pointer targets.
    """
    if (word>>28)!=0xe or ((word>>26)&3)!=1:
        return None
    # I=0; P=1; W=0. Rn = previously loaded literal register.
    if (word&(1<<25)) or not (word&(1<<24)) or (word&(1<<21)):
        return None
    rn=(word>>16)&0xf
    if rn!=expected_base:
        return None
    disp=word&0xfff
    if disp>0x80:
        return None
    if not (word&(1<<23)):
        disp=-disp
    return {
        "signed_offset":disp,
        "access":"load" if (word&(1<<20)) else "store",
        "width":"byte" if (word&(1<<22)) else "word",
        "base_register":f"r{rn}",
        "destination_or_source_register":f"r{(word>>12)&15}",
        "candidate_not_verified_osthreadinfo_field":True,
    }


def audit_static_image(image,base,metadata):
    v84.verify_original_entry(image,base)
    if not metadata["entry_opcode_guard_passed"]:
        raise ThreadLayoutError("V8.4 original thread flag validation absent")
    sites=metadata["literal_xrefs"]
    if len(sites)>v84.MAX_XREFS:
        raise ThreadLayoutError("too many upstream cross references")
    rows=[]
    groups=Counter()
    for site in sites:
        try:
            global_addr=int(site["literal_value"],16)
            pc=int(site["instruction_address"],16)
            r=site["register"]
            reg=int(r.removeprefix("r"))
        except (ValueError,KeyError,TypeError) as exc:
            raise ThreadLayoutError("invalid V8.4 xref metadata") from exc
        if global_addr not in CANDIDATES:
            continue
        off=pc-base
        if (pc&3) or not (0<=off and off+8<=len(image)) or not (0<=reg<=12):
            raise ThreadLayoutError("out-of-range xref or register")
        preceding=struct.unpack_from("<I",image,off)[0]
        if v84.v82.decode_pc_literal(preceding,pc)!=(reg,int(site["literal_address"],16)):
            raise ThreadLayoutError("V8.4 xref no longer matches original ARM9")
        nxt=struct.unpack_from("<I",image,off+4)[0]
        access=direct_arm_access(nxt,reg)
        if access is not None:
            groups[(global_addr,access["signed_offset"],access["access"],access["width"])]+=1
            rows.append({
                "literal_load_site":f"0x{pc:08X}",
                "candidate_base":f"0x{global_addr:08X}",
                "following_instruction_address":f"0x{pc+4:08X}",
                **access,
            })
    if not rows:
        # This is not a hard error: the optimizer may use multi-insn setup.
        # Lack of one-step matches must NOT be construed as no references.
        pass
    counters=[]
    for (base_addr,disp,access,width),count in sorted(groups.items()):
        counters.append({
            "candidate_base":f"0x{base_addr:08X}",
            "signed_offset":disp,
            "access":access,
            "width":width,
            "static_one_instruction_matches":count,
            "threadinfo_field_proven":False,
        })
    return {
        "game_code":metadata["game_code"],
        "known_thread_flag_entry_verified":True,
        "v84_syntactic_xref_count":len(sites),
        "candidate_xrefs":{
            f"0x{candidate:08X}":sum(int(site["literal_value"],16)==candidate for site in sites)
            for candidate in CANDIDATES
        },
        "single_immediate_instruction_accesses":rows,
        "groups":counters,
        "following_instruction_window_bytes":4,
        "instruction_values_exported":False,
        "possible_thread_info_struct_verified":False,
    }


def analyze_game(rom):
    upstream=v84.analyze_game(rom)
    report,image=v75.v74.reconstruct(rom,include_runtime_image=True)
    if upstream["arm9_runtime_sha256"]!=report["arm9"]["runtime_decompressed_sha256"]:
        raise ThreadLayoutError("V8.4 / V8.5 ARM9 image mismatch")
    base=int(report["arm9"]["ram_load"],16)
    result=audit_static_image(image,base,upstream)
    result["rom_sha1"]=upstream["rom_sha1"]
    result["arm9_runtime_sha256"]=upstream["arm9_runtime_sha256"]
    return result


def compare(hg,ss):
    by_code={hg["game_code"]:hg,ss["game_code"]:ss}
    if set(by_code)!={"IPKE","IPGE"} or hg["game_code"]==ss["game_code"]:
        raise ThreadLayoutError("one original HG USA and one original SS USA required")
    a,b=by_code["IPKE"],by_code["IPGE"]
    def key(record):
        return (record["candidate_base"],record["literal_load_site"],
                record["signed_offset"],record["access"],record["width"])
    A={key(x) for x in a["single_immediate_instruction_accesses"]}
    B={key(x) for x in b["single_immediate_instruction_accesses"]}
    if len(A)!=len(a["single_immediate_instruction_accesses"]) or len(B)!=len(b["single_immediate_instruction_accesses"]):
        raise ThreadLayoutError("duplicate ambiguous original ARM access")
    return {
        "tool":"hgss-v8.5-original-one-step-threadinfo-field-hypotheses",
        "live_v83_thread_system_initialization_flag":"0x00000001",
        "original_v84_all_101_xrefs_match_across_roms":a["v84_syntactic_xref_count"]==b["v84_syntactic_xref_count"]==101,
        "nitrosdk_public_header_alternative_struct_layouts":LAYOUTS,
        "candidate_bases":[f"0x{x:08X}" for x in CANDIDATES],
        "heartgold":a,
        "soulsilver":b,
        "shared_first_following_instruction_matches":len(A&B),
        "only_hg_matches":len(A-B),
        "only_ss_matches":len(B-A),
        "exact_shared_accesses":[{
            "candidate_base":k[0],
            "load_site":k[1],
            "signed_offset":k[2],
            "access":k[3],
            "width":k[4],
            "is_real_osthreadinfo_field_proven":False
        } for k in sorted(A&B)],
        "game_scheduler_struct_base_verified":False,
        "live_current_thread_pointer_read":False,
        "safe_new_thread_memory_proven":False,
        "safe_to_call_scheduler_api":False,
        "arm7_wifi_owned_by_bridge":False,
        "wifi_enabled":False,
        "rom_or_save_modified":False,
        "next_gate":"Correlate first-access offsets with ARM9 OS scheduler functions and original compiled thread-info fields before any guarded live read."
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",type=Path)
    p.add_argument("soulsilver",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args(argv)
    try:
        a,b=args.heartgold.resolve(),args.soulsilver.resolve()
        if a==b:
            raise ThreadLayoutError("require two distinct original ROMs")
        if args.output and args.output.resolve() in (a,b):
            raise ThreadLayoutError("refusing to overwrite original ROM")
        result=compare(analyze_game(a),analyze_game(b))
        data=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(data,encoding="utf-8")
        print(data,end="")
        return 0
    except (OSError,ValueError,struct.error) as e:
        print("ERROR: "+str(e),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
