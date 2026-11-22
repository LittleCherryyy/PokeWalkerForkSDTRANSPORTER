#!/usr/bin/env python3
"""Offline WCM/SOC ARM9 target entry and veneer auditor (US HGSS Rev 0).

Reconstructs *only in memory* the two original binaries, checks all five
public decomp callsites using the V7.5 parser, and examines the machine code
at their already-verified immediate targets. Recognizes only simple ARM-state
branch and PC-literal veneers. Not a general disassembler and not proof of
callability, ABI, runtime residency, interrupt safety, or actual Wi-Fi.

Does not patch ROMs, write game code, load a network stack, or read saves.
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
spec=importlib.util.spec_from_file_location("hgss_v75_entry",V75)
v75=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v75)

# These exact user-observed US revision-0 immediate destinations are
# themselves verified anew by the V7.5 overlay BL reader every run.
EXPECTED={
    "WCM_GetPhase":0x020AE420,
    "WCM_Init":0x020AD850,
    "WCM_StartupAsync":0x020AD9C0,
    "SOC_Socket":0x020A2EAC,
    "SOC_Connect":0x020A2F04,
}
MAX_HOPS=4
FINGERPRINT_BYTES=32


class EntryAuditError(ValueError):
    pass


def read_arm(image, base, address):
    """Return one aligned 32-bit ARM instruction; reject out-of-image reads."""
    p=address-base
    if address & 3 or p < 0 or p+4 > len(image):
        raise EntryAuditError(f"ARM word outside reconstructed image: 0x{address:08X}")
    return struct.unpack_from("<I",image,p)[0]


def decode_entry_veneer(image, base, pc):
    """One *unconditional* ARM B or PC-literal jump, if provable.

    Recognize B, LDR pc,[pc,+/-#imm], and LDR ip,[pc,+/-#imm];
    BX ip. Deliberately do not follow BL (which usually is a call)
    or guess arbitrary register-indirect jumps.
    """
    word=read_arm(image,base,pc)

    if (word & 0xFF000000)==0xEA000000:  # unconditional B
        sign=word & 0xFFFFFF
        if sign & 0x800000:
            sign-=0x1000000
        dest=(pc+8+(sign<<2))&0xFFFFFFFF
        return ("ARM unconditional B",dest)

    # Simple ARM PC-relative literal jumps; only AL condition and word loads.
    is_ldr_pc=(word & 0xFFFFF000) in (0xE59FF000,0xE51FF000)
    is_ldr_ip=(word & 0xFFFFF000) in (0xE59FC000,0xE51FC000)
    if is_ldr_pc or is_ldr_ip:
        signed=(word & 0xFFF)*(1 if word & 0x00800000 else -1)
        literal=(pc+8+signed)&0xFFFFFFFF
        try:
            dest=read_arm(image,base,literal)
        except EntryAuditError:
            return ("ARM literal points outside static image",None)
        if is_ldr_pc:
            return ("ARM LDR pc, [pc, offset]", dest)
        try:
            bx=read_arm(image,base,pc+4)
        except EntryAuditError:
            return ("ARM LDR ip, [pc, offset] without in-range BX",None)
        if bx==0xE12FFF1C:
            return ("ARM LDR ip + BX ip",dest)
    return (None,None)


def classify_entry(image,base,pc):
    word=read_arm(image,base,pc)
    if (word & 0xFFFF0000)==0xE92D0000:
        return "ARM stack-saving prologue (compatible with function entry)"
    if (word & 0xFFFFF000)==0xE24DD000:
        return "ARM stack frame allocation (compatible with function entry)"
    if word==0 or word==0xFFFFFFFF:
        return "empty/erased memory (unexpected executable entry)"
    if (word & 0xFF000000)==0xEB000000:
        return "ARM BL at entry (not assumed to be veneer)"
    if (word & 0xFFFFFFF0)==0xE12FFF10:
        return "ARM BX register at entry (indirect; not followed)"
    return "other ARM instruction (not proof of function identity)"


def trace_target(image,base,start):
    """Walk at most four recognized jumps, no execution or arbitrary indirection."""
    seen=set()
    current=start
    chain=[]
    for _ in range(MAX_HOPS+1):
        if current in seen:
            chain.append({"address":f"0x{current:08X}","finding":"veneer cycle"})
            return chain,None,"cycle"
        seen.add(current)
        if current & 3 or not base<=current<=base+len(image)-FINGERPRINT_BYTES:
            chain.append({"address":f"0x{current:08X}","finding":"outside static ARM9 range"})
            return chain,None,"outside static image"
        offset=current-base
        fingerprint=hashlib.sha256(image[offset:offset+FINGERPRINT_BYTES]).hexdigest()
        step={"address":f"0x{current:08X}",
              "code_window_sha256":fingerprint,
              "window_bytes":FINGERPRINT_BYTES}
        kind,target=decode_entry_veneer(image,base,current)
        if kind is None:
            step["finding"]=classify_entry(image,base,current)
            chain.append(step)
            return chain,current,"stopped at unclassified or prologue entry"
        step["finding"]=kind
        if target is not None:
            step["next_address"]=f"0x{target:08X}"
        chain.append(step)
        if target is None:
            return chain,None,"unresolvable literal or register jump"
        if target & 1:
            return chain,None,"odd target address; execution mode unverified"
        current=target
    return chain,None,"maximum veneer depth exceeded"


def inspect_rom(rom):
    # V7.5 revalidates every overlay callsite in the exact verified US ROM.
    sites=v75.analyze(rom)
    report,image=v75.v74.reconstruct(rom,include_runtime_image=True)
    if sites["arm9_runtime_sha256"] != report["arm9"]["runtime_decompressed_sha256"]:
        raise EntryAuditError("ARM9 reconstruction differs from V7.5")
    base=int(report["arm9"]["ram_load"],16)
    verified_sites={x["name"]:x for x in sites["callsites"]}
    if set(verified_sites)!=set(EXPECTED) or len(sites["callsites"])!=len(EXPECTED):
        raise EntryAuditError("expected exactly five WCM/SOC callsites")
    targets={}
    for name,expected in EXPECTED.items():
        observed=verified_sites[name]
        actual=int(observed["decoded_immediate_target"],16)
        if actual!=expected:
            raise EntryAuditError(f"{name} callsite disagrees with pinned V7.5 target")
        if not observed["neighbor_opcode_validated"] or not observed["target_mode"].startswith("ARM"):
            raise EntryAuditError(f"{name}: callsite/instruction state mismatch")
        chain,end,reason=trace_target(image,base,actual)
        targets[name]={
            "immediate_target":f"0x{actual:08X}",
            "callsite_mode":observed["target_mode"],
            "entry_trace":chain,
            "terminal_candidate_address":f"0x{end:08X}" if end is not None else None,
            "trace_stop":reason,
            "abi_verified":False,
            "safe_to_call":False
        }
    return {
        "game_code":report["game_code"],
        "rom_sha1":report["image_sha1"],
        "arm9_runtime_sha256":sites["arm9_runtime_sha256"],
        "target_entries":targets,
    }


def compare(hg,ss):
    pairs=[]
    for name in sorted(EXPECTED):
        a=hg["target_entries"][name]; b=ss["target_entries"][name]
        af=a["entry_trace"][-1].get("code_window_sha256")
        bf=b["entry_trace"][-1].get("code_window_sha256")
        pairs.append({
            "function_label":name,
            "same_immediate_address":a["immediate_target"]==b["immediate_target"],
            "same_terminal_candidate":a["terminal_candidate_address"] is not None and a["terminal_candidate_address"]==b["terminal_candidate_address"],
            "same_terminal_32byte_fingerprint":af is not None and af==bf,
            "heartgold":a,
            "soulsilver":b,
            "callable_abi_proven":False,
        })
    return {
        "tool":"hgss-v7.6-arm9-entry-veneer-audit",
        "heartgold":{"game_code":hg["game_code"],"rom_sha1":hg["rom_sha1"],
                    "arm9_runtime_sha256":hg["arm9_runtime_sha256"]},
        "soulsilver":{"game_code":ss["game_code"],"rom_sha1":ss["rom_sha1"],
                    "arm9_runtime_sha256":ss["arm9_runtime_sha256"]},
        "comparisons":pairs,
        "wifi_abi_verified":False,
        "arm9_wifi_driver_residency_verified":False,
        "wifi_irq_ownership_verified":False,
        "resident_wifi_ready":False,
        "function_execution_allowed":False,
        "physical_dsi_to_android_ping_verified":False,
        "no_rom_bytes_exported":True,
        "next_gate":"Validate exact ABI and ARM7 radio ownership, then build a bounded non-save test.",
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",type=Path,help="Original US HeartGold .nds")
    p.add_argument("soulsilver",type=Path,help="Original US SoulSilver .nds")
    p.add_argument("--output",type=Path,help="JSON metadata report path")
    args=p.parse_args(argv)
    try:
        paths=[args.heartgold.resolve(),args.soulsilver.resolve()]
        if paths[0]==paths[1]:
            raise EntryAuditError("two different original US ROMs required")
        if args.output and args.output.resolve() in paths:
            raise EntryAuditError("refusing to overwrite a ROM")
        a=inspect_rom(args.heartgold)
        b=inspect_rom(args.soulsilver)
        by_code={a["game_code"]:a,b["game_code"]:b}
        if set(by_code)!={"IPKE","IPGE"} or a["game_code"]==b["game_code"]:
            raise EntryAuditError("must supply one original US HeartGold and one SoulSilver")
        result=compare(by_code["IPKE"],by_code["IPGE"])
        out=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(out,encoding="utf-8")
        print(out,end="")
        return 0
    except (EntryAuditError,ValueError,OSError,struct.error) as exc:
        print("ERROR: "+str(exc),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
