#!/usr/bin/env python3
"""V8.0 offline HGSS (USA Rev0) NitroSDK thread callsite comparison.

Before *any* experiment scheduling a separate ARM9 thread, map the existing
thread scheduler calls from the game's own communications overlays 13 and 39.

Public source:
  https://github.com/pret/pokeheartgold/blob/master/asm/overlay_13_thumb_2.s
  https://github.com/pret/pokeheartgold/blob/master/lib/NitroDWC/asm/overlay_39_arm.s

No game code/ROM data is exported. No game thread, wireless function, or
save is accessed. An immediate branch address does not prove its final
identity, ABI, live overlay residency, scheduler availability or safety.
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
V75=HERE.parent/"v7_5"/"hgss_wifi_call_targets.py"
module=importlib.util.spec_from_file_location("v80_v75",V75)
v75=importlib.util.module_from_spec(module)
module.loader.exec_module(v75)

# ARMv5 Thumb-1 / ARM instructions from the published original US
# assembly. Each callsite independently checks the neighboring opcode.
# (symbol, overlay, ISA, callsite, neighbor_side, neighbor_opcode)
SITES=(
    ("OS_IsThreadAvailable",13,"thumb",0x02226DD4,"after",0x2801),
    ("OS_CreateThread",13,"thumb",0x02226E00,"before",0x18EB),
    ("OS_WakeupThreadDirect",13,"thumb",0x02226E36,"after",0x4902),
    ("OS_CreateThread",39,"arm",0x022299AC,"before",0xE58DC004),
    ("OS_WakeupThreadDirect",39,"arm",0x022299B4,"after",0xE3A00001),
)
FINGERPRINT=32


class ThreadAuditError(ValueError):
    pass


def resolve_thread_callsite(img,load,site):
    name,ov,isa,pc,neighbor_side,opcode=site
    off=pc-load
    instrbytes=4
    align=2 if isa=="thumb" else 4
    neighbor_offset=-align if neighbor_side=="before" else instrbytes
    npos=off+neighbor_offset
    if off<0 or pc%align or off+instrbytes>len(img):
        raise ThreadAuditError(f"{name} overlay {ov}: invalid callsite bounds")
    if npos<0 or npos+align>len(img):
        raise ThreadAuditError(f"{name} overlay {ov}: neighbor out of bounds")
    observed=struct.unpack_from("<H" if isa=="thumb" else "<I",img,npos)[0]
    if observed!=opcode:
        raise ThreadAuditError(
            f"{name} overlay {ov}: documented {neighbor_side}-call opcode "
            f"mismatch at 0x{pc:08X} (expected 0x{opcode:X}, got 0x{observed:X})"
        )
    if isa=="thumb":
        h1,h2=struct.unpack_from("<HH",img,off)
        try:
            dest,mode=v75.thumb_call(h1,h2,pc)
        except v75.CallsiteError as e:
            raise ThreadAuditError(f"{name} overlay {ov}: {e}") from e
    else:
        word=struct.unpack_from("<I",img,off)[0]
        try:
            dest,mode=v75.arm_bl(word,pc)
        except v75.CallsiteError as e:
            raise ThreadAuditError(f"{name} overlay {ov}: {e}") from e
    return {
        "name":name,
        "overlay":ov,
        "callsite":f"0x{pc:08X}",
        "target":f"0x{dest:08X}",
        "target_mode":mode,
        "neighbor_validated":True,
        "scheduler_abi_verified":False,
        "safe_to_create_thread":False
    }


def read_arm9_window(image,load,addr):
    p=addr-load
    if p<0 or p+FINGERPRINT>len(image):
        return None
    return hashlib.sha256(image[p:p+FINGERPRINT]).hexdigest()


def analyze(rom):
    # Enforces both the exact authentic ROM SHA1 and the earlier five WCM/SOC
    # callsite checks, before trusting any upstream overlay coordinate.
    earlier=v75.analyze(rom)
    report,arm9=v75.v74.reconstruct(rom,include_runtime_image=True)
    if earlier["arm9_runtime_sha256"]!=report["arm9"]["runtime_decompressed_sha256"]:
        raise ThreadAuditError("V7.5 and V8.0 ARM9 reconstruction disagree")
    rom_size=report["image_bytes"]
    with Path(rom).open("rb") as f:
        header=v75.v74._v73.read_exact(f,0,0x200,"NDS header")
        fat_at,fat_size=struct.unpack_from("<II",header,0x48)
        if not fat_size or fat_size%8 or fat_size>524288:
            raise ThreadAuditError("invalid ROM FAT size")
        v75.v74._v73.require_range(rom_size,fat_at,fat_size,"FAT")
        fat=v75.v74._v73.read_exact(f,fat_at,fat_size,"FAT")
        overlays={
            ov:v75.get_overlay(f,header,fat,rom_size,ov)
            for ov in (13,39)
        }
    load=int(report["arm9"]["ram_load"],16)
    resolved=[]
    for site in SITES:
        base,img,_metadata=overlays[site[1]]
        entry=resolve_thread_callsite(img,base,site)
        target=int(entry["target"],16)
        entry["target_region"]=v75.region_of(target,load,len(arm9),overlays)
        sig=read_arm9_window(arm9,load,target)
        entry["static_arm9_32byte_sha256"]=sig
        entry["static_code_window_present"]=sig is not None
        entry["static_code_window_is_execution_proof"]=False
        resolved.append(entry)
    return {
        "game_code":report["game_code"],
        "rom_sha1":report["image_sha1"],
        "arm9_runtime_sha256":report["arm9"]["runtime_decompressed_sha256"],
        "callsites":resolved
    }


def compare(one,two):
    by_code={one["game_code"]:one,two["game_code"]:two}
    if set(by_code)!={"IPKE","IPGE"} or one["game_code"]==two["game_code"]:
        raise ThreadAuditError("requires one original USA HeartGold and one USA SoulSilver")
    a=by_code["IPKE"]
    b=by_code["IPGE"]
    lhs={(x["name"],x["overlay"]):x for x in a["callsites"]}
    rhs={(x["name"],x["overlay"]):x for x in b["callsites"]}
    if len(lhs)!=len(SITES) or len(rhs)!=len(SITES) or set(lhs)!=set(rhs):
        raise ThreadAuditError("thread callsite records missing or duplicated")
    rows=[]
    for name,overlay,isa,pc,side,opcode in SITES:
        aa=lhs[(name,overlay)]
        bb=rhs[(name,overlay)]
        rows.append({
            "api":name,
            "overlay":overlay,
            "callsite":f"0x{pc:08X}",
            "heartgold_target":aa["target"],
            "soulsilver_target":bb["target"],
            "same_immediate_target":aa["target"]==bb["target"],
            "same_static_window_sha256":(
                aa["static_arm9_32byte_sha256"] is not None
                and aa["static_arm9_32byte_sha256"]==bb["static_arm9_32byte_sha256"]
            ),
            "heartgold_region":aa["target_region"],
            "soulsilver_region":bb["target_region"],
            "decoded_execution_mode":aa["target_mode"],
            "function_call_approved":False,
        })
    return {
        "tool":"hgss-v8.0-original-thread-scheduler-callsite-audit",
        "heartgold":a,
        "soulsilver":b,
        "comparison":rows,
        "validated_callsites":len(rows),
        "same_immediate_targets":sum(x["same_immediate_target"] for x in rows),
        "network_enabled":False,
        "game_scheduler_abi_verified":False,
        "independent_arm9_worker_verified":False,
        "arm7_wm_radio_owned_by_bridge":False,
        "nds_bootstrap_or_rom_patched":False,
        "source_code_bytes_exported":False,
        "next_gate":"Resolve NitroSDK thread ABI and callback lifetime; independent thread scheduling and ARM7 radio ownership are not yet proven."
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",type=Path)
    p.add_argument("soulsilver",type=Path)
    p.add_argument("--output",type=Path,help="Only noncopyright metadata JSON")
    args=p.parse_args(argv)
    try:
        roms=[args.heartgold.resolve(),args.soulsilver.resolve()]
        if roms[0]==roms[1]:
            raise ThreadAuditError("need two different original ROM backups")
        if args.output and args.output.resolve() in roms:
            raise ThreadAuditError("will not overwrite a game ROM")
        result=compare(analyze(args.heartgold),analyze(args.soulsilver))
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
