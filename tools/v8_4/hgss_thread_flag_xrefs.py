#!/usr/bin/env python3
"""V8.4 HGSS exact-USA-Rev0 NitroSDK thread-flag cross-reference map.

The DSi V8.3 read the live 32-bit word at 0x021E1688 as 0x00000001
after verifying the original three ARM instructions and one literal
at OS_IsThreadAvailable (0x020D1AC4). Per NitroSDK documentation the
function reports whether the thread subsystem is initialized.

This OFFLINE scan does not call any thread API and does not access the
live DSi. It locates literal references to 0x021E1688 and immediately
neighboring candidate thread state data addresses (within +/-0x40).
Every use requires a genuine unconditional ARM PC-relative LDR which
resolves to an in-bounds literal within the reconstructed ARM9 image.
This is a syntax-level cross-reference, NOT a proof that the referencing
word is executable code or that a particular nearby field is OSThread.

Only addresses, counts, categories and bounded SHA256 metadata are
emitted. Game instructions and raw ROM bytes are never exported.
The full V8.2 checks are rerun, including original ROM SHA1 and the
V8.0/V8.1 thread caller ABI/entry checks.
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
P82=HERE.parent/"v8_2"/"hgss_thread_scheduler_refs.py"
spec=importlib.util.spec_from_file_location("hgss_v84_v82",P82)
v82=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v82)
v81=v82.v81
v75=v82.v75

FLAG_ADDR=0x021E1688
ENTRY=0x020D1AC4
ENTRY_OPCODES=(0xE59F0004,0xE5900000,0xE12FFF1E,FLAG_ADDR)
NEARBY_RADIUS=0x40
MAX_LITERAL_SITES=128
MAX_XREFS=256
NEARBY_START=FLAG_ADDR-NEARBY_RADIUS
NEARBY_END=FLAG_ADDR+NEARBY_RADIUS


class ThreadXrefError(ValueError):
    pass


def verify_original_entry(img,base):
    offset=ENTRY-base
    if ENTRY&3 or offset<0 or offset+16>len(img):
        raise ThreadXrefError("ARM9 entry guard not within original static image")
    words=struct.unpack_from("<4I",img,offset)
    if words!=ENTRY_OPCODES:
        raise ThreadXrefError("V8.3 OS_IsThreadAvailable original opcode/literal guard mismatch")
    if v82.decode_pc_literal(words[0],ENTRY)!=(0,ENTRY+12):
        raise ThreadXrefError("V8.3 OS_IsThreadAvailable literal decoder disagreement")
    if v82.decode_r0_memory_offset(words[1])!={
        "signed_offset":0,"access":"load","offset_is_verified_osthread_field":False
    }:
        raise ThreadXrefError("V8.3 OS_IsThreadAvailable dereference semantics mismatch")
    return True


def scan_candidate_literal_sites(image,base):
    """Enumerate STATIC words that happen to fall inside candidate range.

    A literal is only considered a *reference* when a separately decoded
    ARM LDR instruction reaches its exact 4-byte address.
    """
    sites={}
    if len(image)%4:
        # The original reconstruction can include trailing bytes; only
        # aligned words are relevant; ignore 1-3 trailing data bytes.
        pass
    for off in range(0,len(image)-3,4):
        val=struct.unpack_from("<I",image,off)[0]
        if NEARBY_START<=val<=NEARBY_END and val%4==0:
            if len(sites)>=MAX_LITERAL_SITES:
                raise ThreadXrefError("too many scheduler-range literal candidates; fail closed")
            sites[base+off]=val
    return sites


def find_pc_relative_xrefs(image,base,literal_sites):
    """Return ONLY syntactically justified ARM literal uses.

    No reverse disassembly, instruction execution, pointer following,
    non-ARM Thumb guess, overlay dereference or arbitrary memory read.
    """
    if not literal_sites:
        raise ThreadXrefError("no static literal candidates for the known global")
    xrefs=[]
    for off in range(0,len(image)-3,4):
        pc=base+off
        instr=struct.unpack_from("<I",image,off)[0]
        decoded=v82.decode_pc_literal(instr,pc)
        if not decoded:
            continue
        reg,lit=decoded
        if lit not in literal_sites:
            continue
        if len(xrefs)>=MAX_XREFS:
            raise ThreadXrefError("too many matching ARM literal readers; fail closed")
        dest=literal_sites[lit]
        start=off-16
        end=off+16
        window_hash=(hashlib.sha256(image[start:end]).hexdigest()
                     if start>=0 and end<=len(image) else None)
        xrefs.append({
            "instruction_address":f"0x{pc:08X}",
            "literal_address":f"0x{lit:08X}",
            "literal_value":f"0x{dest:08X}",
            "address_delta_from_thread_flag":dest-FLAG_ADDR,
            "register":f"r{reg}",
            "nearest_32byte_sha256":window_hash,
            "exact_original_available_flag_reference":dest==FLAG_ADDR,
            "validated_executable_instruction":False,
            "validated_osthread_field":False,
        })
    return xrefs


def analyze_image(image,base,game):
    verify_original_entry(image,base)
    sites=scan_candidate_literal_sites(image,base)
    refs=find_pc_relative_xrefs(image,base,sites)
    # At least the original function must be found.
    if not any(x["instruction_address"]==f"0x{ENTRY:08X}" and
               x["literal_value"]==f"0x{FLAG_ADDR:08X}" for x in refs):
        raise ThreadXrefError(f"{game}: known original function reference not recovered")
    return {
        "game_code":game,
        "known_os_is_thread_available_entry":f"0x{ENTRY:08X}",
        "known_read_address":f"0x{FLAG_ADDR:08X}",
        "entry_opcode_guard_passed":True,
        "static_literal_site_count":len(sites),
        "syntactic_arm_ldr_xref_count":len(refs),
        "literal_xrefs":refs,
        "xrefs_are_not_live_thread_list":True,
        "nearby_field_offsets_are_unverified":True,
    }


def analyze_game(rom):
    # Full V8.2 gated identity verification and known original ABI.
    previous=v82.analyze(rom)
    report,image=v75.v74.reconstruct(rom,include_runtime_image=True)
    if previous["arm9_runtime_sha256"]!=report["arm9"]["runtime_decompressed_sha256"]:
        raise ThreadXrefError("V8.2 and V8.4 reconstructed ARM9 disagree")
    base=int(report["arm9"]["ram_load"],16)
    result=analyze_image(image,base,previous["game_code"])
    result["rom_sha1"]=previous["rom_sha1"]
    result["arm9_runtime_sha256"]=previous["arm9_runtime_sha256"]
    return result


def compare(first,second):
    by_code={first["game_code"]:first,second["game_code"]:second}
    if set(by_code)!={"IPKE","IPGE"} or len(by_code)!=2:
        raise ThreadXrefError("requires one original USA HeartGold and one original USA SoulSilver")
    hg=by_code["IPKE"]
    ss=by_code["IPGE"]
    def key(x):
        return x["instruction_address"],x["literal_address"],x["literal_value"]
    a={key(x):x for x in hg["literal_xrefs"]}
    b={key(x):x for x in ss["literal_xrefs"]}
    shared=sorted(set(a)&set(b))
    return {
        "tool":"hgss-v8.4-original-thread-global-offline-crossrefs",
        "reference_live_dsi_v83_raw_word":"0x00000001",
        "reference_live_dsi_v83_original_opcodes_verified":True,
        "flag_means_thread_system_initialized_according_to_nitrosdk":True,
        "heartgold":hg,
        "soulsilver":ss,
        "shared_xrefs":[{
            "instruction_address":k[0],
            "literal_address":k[1],
            "referenced_address":k[2],
            "same_context_sha256":a[k]["nearest_32byte_sha256"] is not None
                and a[k]["nearest_32byte_sha256"]==b[k]["nearest_32byte_sha256"],
            "verified_scheduler_field":False,
        } for k in shared],
        "shared_xref_count":len(shared),
        "game_thread_list_address_proven":False,
        "osthread_struct_layout_proven":False,
        "safe_to_create_or_reuse_thread":False,
        "safe_worker_stack_allocation_proven":False,
        "arm7_radio_ownership_proven":False,
        "wifi_enabled":False,
        "rom_save_walker_modified":False,
        "next_gate":"Correlate cross-reference candidates with NitroSDK implementation; do not dereference nearby RAM or call OS APIs until separately verified.",
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("heartgold",type=Path)
    parser.add_argument("soulsilver",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    try:
        originals=[args.heartgold.resolve(),args.soulsilver.resolve()]
        if originals[0]==originals[1]:
            raise ThreadXrefError("two different original ROM backups required")
        if args.output and args.output.resolve() in originals:
            raise ThreadXrefError("refusing to overwrite the user's ROM")
        result=compare(analyze_game(args.heartgold),analyze_game(args.soulsilver))
        data=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(data,encoding="utf-8")
        print(data,end="")
        return 0
    except (ValueError,OSError,struct.error) as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
