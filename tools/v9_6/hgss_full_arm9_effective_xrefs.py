#!/usr/bin/env python3
"""V9.6 — whole reconstructed ARM9 literal->next-access effective-address index.

Read-only, exact-ROM gated for HGSS US Rev0. Fixes an important limitation
of V9.5: a LDR can load a base address and the next instruction can access a
different address through a signed immediate displacement. Only syntactic
one-step ARM A32 patterns are indexed; paths, real thread objects, and Wi-Fi
are NOT proven. Doesn't extract copyrighted code or touch saves or games.
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
FIRST=0x021E169C
LAST=0x021E16B0
MAX_SITES=4096
FORBIDDEN={".nds",".sav",".dsv",".srm",".walker",".dat"}

def hx(n): return f"0x{n:08X}"

def scan_arm9(img, base, v90):
    """Scan all 4-byte-aligned A32 words, never infer code execution."""
    sites=[]
    examined=0
    immediate_accesses=0
    for offset in range(0,len(img)-7,4):
        pc=base+offset
        word=struct.unpack_from("<I",img,offset)[0]
        literal=v90.v84.v82.decode_pc_literal(word,pc)
        if literal is None: continue
        examined+=1
        reg,literal_pc=literal
        literal_off=literal_pc-base
        if reg>12 or literal_off%4 or literal_off<0 or literal_off+4>len(img):
            continue
        literal_value=struct.unpack_from("<I",img,literal_off)[0]
        mem=v90.safe_mem_access(struct.unpack_from("<I",img,offset+4)[0])
        if mem is None or mem.get("base_register")!=f"r{reg}":
            continue
        immediate_accesses+=1
        displacement=mem["signed_offset"]
        target=(literal_value+displacement)&0xffffffff
        if not FIRST<=target<=LAST: continue
        if len(sites)>=MAX_SITES:
            raise ValueError("too many matching sites in bounded target region")
        sites.append({
            "literal_load_pc":hx(pc),
            "following_access_pc":hx(pc+4),
            "source_literal_pc":hx(literal_pc),
            "loaded_literal_base":hx(literal_value),
            "signed_offset":displacement,
            "effective_address":hx(target),
            "access":mem["access"],
            "width":mem["width"],
            "base_register":f"r{reg}",
            "control_flow_verified":False,
            "runtime_RAM_followed":False
        })
    return {
        "arm9_words_scanned":len(img)//4,
        "syntactic_literal_loads_examined":examined,
        "one_step_immediate_access_candidates":immediate_accesses,
        "interesting_effective_address_sites":sites,
        "interesting_site_count":len(sites),
        "interesting_by_address":dict(sorted(Counter(
            s["effective_address"] for s in sites).items())),
        "actual_execution_proven":False
    }

def analyze(rom,v92):
    verified=v92.analyze_game(rom)
    meta,img=v92.v90.v75.v74.reconstruct(rom,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"]!=verified["original_runtime_sha256"]:
        raise ValueError("original ARM9 runtime hash mismatch")
    scan=scan_arm9(img,int(meta["arm9"]["ram_load"],16),v92.v90)
    # Mandatory original V9.0 anchors prevent a silent regression in the
    # address decoder. They are known from the verified source ROMs.
    known=v92.v90.ANCHORS
    by_pc={int(x["literal_load_pc"],16):x for x in
           scan["interesting_effective_address_sites"]}
    anchors={}
    for name,(pc,address,access,width) in known.items():
        if not FIRST<=address<=LAST: continue
        row=by_pc.get(pc)
        if row is None or (row["effective_address"],row["access"],row["width"])!=(
                hx(address),access,width):
            raise ValueError(f"original V9.0 anchor missing/mismatched: {name}")
        anchors[name]={"literal_load_pc":hx(pc),
                       "access_pc":row["following_access_pc"],
                       "effective_address":row["effective_address"],
                       "loaded_literal_base":row["loaded_literal_base"],
                       "signed_offset":row["signed_offset"],
                       "access":access,"width":width}
    return {"game_code":verified["game_code"],
            "rom_sha1":verified["original_rom_sha1"],
            "arm9_runtime_sha256":verified["original_runtime_sha256"],
            "original_v90_anchors":anchors,
            **scan}

def compare(hg,ss):
    by={hg["game_code"]:hg,ss["game_code"]:ss}
    if set(by)!={"IPKE","IPGE"}: raise ValueError("need original US IPKE and IPGE")
    a,b=by["IPKE"],by["IPGE"]
    keys=("literal_load_pc","following_access_pc",
          "loaded_literal_base","signed_offset","effective_address",
          "access","width")
    def signature(row): return tuple(row[x] for x in keys)
    sa={signature(x) for x in a["interesting_effective_address_sites"]}
    sb={signature(x) for x in b["interesting_effective_address_sites"]}
    return {
        "tool":"hgss-v9.6-full-arm9-effective-address-xrefs",
        "heartgold":a,"soulsilver":b,
        "cross_title":{"matching_semantic_sites":len(sa&sb),
                       "heartgold_only_semantic_sites":len(sa-sb),
                       "soulsilver_only_semantic_sites":len(sb-sa),
                       "v90_anchor_sets_equal":a["original_v90_anchors"]==b["original_v90_anchors"]},
        "method":"whole ARM9 image A32 scan, one-step literal load then direct immediate access",
        "limitations":["not a complete control-flow graph",
                       "not Thumb disassembly",
                       "not a decompressed-overlay code scan",
                       "not proof of execution or thread object identity"],
        "real_scheduler_ABI_proven":False,
        "safe_to_create_resident_thread":False,
        "ARM7_wifi_ownership_proven":False,
        "wifi_enabled":False,
        "rom_save_or_walker_modified":False,
        "next_gate":"Use effective-address sites to prioritize local CFG and call graph; verify live ARM9/ARM7 ownership before Wi-Fi."
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",nargs="?",type=Path)
    p.add_argument("soulsilver",nargs="?",type=Path)
    p.add_argument("--rom-dir",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args(argv)
    try:
        if args.rom_dir:
            if args.heartgold or args.soulsilver:
                raise ValueError("choose --rom-dir or two ROM paths")
            locator=HERE.parent/"v9_5"/"hgss_full_rom_index.py"
            spec=importlib.util.spec_from_file_location("v96_v95",locator)
            if spec is None or spec.loader is None:
                raise ValueError("V9.5 discovery dependency missing")
            v95=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(v95)
            h,s=v95.discover_roms(args.rom_dir)
        elif args.heartgold and args.soulsilver:
            h,s=args.heartgold.resolve(),args.soulsilver.resolve()
        else:
            raise ValueError("provide both original ROM files or --rom-dir")
        if h==s: raise ValueError("two different original ROM paths required")
        if args.output and (args.output.suffix.lower() in FORBIDDEN or
                            args.output.resolve() in (h,s)):
            raise ValueError("refusing output to ROM/save")
        dep=HERE.parent/"v9_2"/"hgss_store_value_backtrace.py"
        spec=importlib.util.spec_from_file_location("v96_v92",dep)
        if spec is None or spec.loader is None:
            raise ValueError("V9.2 original-ROM verification chain unavailable")
        v92=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v92)
        result=compare(analyze(h,v92),analyze(s,v92))
        payload=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
            print(f"V9.6 completed: {args.output}")
            print("HG effective sites:",result["heartgold"]["interesting_site_count"])
            print("SS effective sites:",result["soulsilver"]["interesting_site_count"])
        else:
            print(payload,end="")
        return 0
    except (ValueError,OSError,struct.error) as e:
        print("ERROR:",e,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
