#!/usr/bin/env python3
"""V8.9 — Offline original HGSS ARM9 scheduler field-access audit.

Real Nintendo DSi V8.8 fixed-memory read (2026-11-22):
  0x021E169C = 0x00000003
  0x021E16A0 = 0x00000000
  0x021E16A4 = 0x021E1770
  0x021E16A8 = 0x021E3864
  0x021E16AC = 0x00000000
  0x021E16B0 = 0x0000001F

For the public NitroSDK 2.x fixed-limit OSThreadInfo struct at 169C,
max_entry would be 0, while entry[0] would be 31, not an aligned RAM
pointer. That interpretation is DISFAVORED, not "proven impossible"
for a different original binary layout.

This read-only, original-ROM-only audit extends the V8.4/V8.5 static
ARM PC-literal -> next-instruction checks with ARM immediate LDRH/STRH
(width=halfword), needed to assess the SDK's u16 fields.

It never dereferences any literal's target: only records bounded
instruction addresses, operation kind, signed offset and computed
effective *address*. An instruction-shaped byte sequence might be data,
so every match is SYNTACTIC ONLY and not a confirmed code path.
No ROM bytes/opcodes, game save data or Pokemon payload are exported.
No ARM9/ARM7 hardware operation, worker creation, or Wi-Fi.
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
P85=HERE.parent/"v8_5"/"hgss_thread_info_layout_audit.py"
spec=importlib.util.spec_from_file_location("hgss_v89_v85",P85)
v85=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v85)
v84=v85.v84
v75=v85.v75

# These are fixed addresses in the original USA Rev0 game RAM, NOT
# known scheduler structure bases. All already lie in V8.4's +/-0x40.
BASE_CANDIDATES=(
    0x021E167C, 0x021E169C, 0x021E16A0,
    0x021E16A4, 0x021E16A8, 0x021E16AC, 0x021E16B0,
)
REGION_FIRST=0x021E169C
REGION_LAST=0x021E16B0
MAX_SITES=256

# User-supplied V8.8 console photo. Do not read or overwrite ROM saves.
V88_RAW_WORDS={
    0x021E169C:0x00000003,
    0x021E16A0:0x00000000,
    0x021E16A4:0x021E1770,
    0x021E16A8:0x021E3864,
    0x021E16AC:0x00000000,
    0x021E16B0:0x0000001F,
}


class FieldXrefError(ValueError):
    pass


def decode_arm_immediate_halfword(word, expected_base):
    """Only unconditional ARM A32 LDRH/STRH [rN,+/-imm8] (P=1,W=0).

    Format: cond 000 P U 1 W L Rn Rd imm4H 1011 imm4L
    Sign/byte/special addressing forms and register-offset are rejected.
    """
    if (word>>28)!=0xE or ((word>>25)&7)!=0:
        return None
    if (word&0xF0)!=0xB0:
        return None
    if not (word&(1<<24)) or not (word&(1<<22)) or (word&(1<<21)):
        return None
    rn=(word>>16)&15
    if rn!=expected_base:
        return None
    imm=((word>>8)&0xF)*16+(word&0xF)
    if imm>0x80:
        return None
    signed=imm if (word&(1<<23)) else -imm
    return {
        "signed_offset":signed,
        "access":"load" if (word&(1<<20)) else "store",
        "width":"halfword",
        "base_register":f"r{rn}",
        "destination_or_source_register":f"r{(word>>12)&15}",
        "field_identity_proven":False,
    }


def decode_direct_access(word, reg):
    half=decode_arm_immediate_halfword(word,reg)
    if half is not None:
        return half
    other=v85.direct_arm_access(word,reg)
    if other is None:
        return None
    return {
        "signed_offset":other["signed_offset"],
        "access":other["access"],
        "width":other["width"],
        "base_register":other["base_register"],
        "destination_or_source_register":
            other["destination_or_source_register"],
        "field_identity_proven":False,
    }


def analyze_image(image,base,upstream):
    v84.verify_original_entry(image,base)
    if not upstream["entry_opcode_guard_passed"]:
        raise FieldXrefError("V8.4 original availability flag verification missing")
    sites=upstream["literal_xrefs"]
    if len(sites)>MAX_SITES:
        raise FieldXrefError("too many upstream original ARM9 references")
    rows=[]
    grouped=Counter()
    skipped=Counter()
    for site in sites:
        try:
            pc=int(site["instruction_address"],16)
            literal=int(site["literal_address"],16)
            candidate=int(site["literal_value"],16)
            register=site["register"]
            if not (register.startswith("r") and register[1:].isdigit()):
                raise ValueError("register")
            rd=int(register[1:])
        except (KeyError,TypeError,ValueError) as ex:
            raise FieldXrefError("malformed V8.4 reference") from ex
        if candidate not in BASE_CANDIDATES:
            continue
        off=pc-base
        if pc&3 or literal&3 or not (0<=rd<=12) or not(0<=off and off+8<=len(image)):
            raise FieldXrefError("invalid source literal site or register")
        # Re-validate directly from original bounded ROM image instead of
        # trusting the metadata passed by earlier scripts.
        inst=struct.unpack_from("<I",image,off)[0]
        if v84.v82.decode_pc_literal(inst,pc)!=(rd,literal):
            raise FieldXrefError("verified source PC-relative LDR no longer matches")
        lo=literal-base
        if not(0<=lo and lo+4<=len(image)):
            raise FieldXrefError("literal out of original ARM9 image")
        if struct.unpack_from("<I",image,lo)[0]!=candidate:
            raise FieldXrefError("original literal address does not match")
        nxt=struct.unpack_from("<I",image,off+4)[0]
        access=decode_direct_access(nxt,rd)
        if access is None:
            skipped[f"0x{candidate:08X}"]+=1
            continue
        effective=candidate+access["signed_offset"]
        # No data is read at 'effective' — this is arithmetic only.
        field={
            "source_instruction":f"0x{pc:08X}",
            "access_instruction":f"0x{pc+4:08X}",
            "source_literal":f"0x{literal:08X}",
            "literal_value":f"0x{candidate:08X}",
            "effective_address":f"0x{effective:08X}",
            "signed_offset":access["signed_offset"],
            "access":access["access"],
            "width":access["width"],
            "base_register":access["base_register"],
            "operand_register":access["destination_or_source_register"],
            "inside_v88_header_region":REGION_FIRST<=effective<=REGION_LAST,
            "proved_executable":False,
            "proved_scheduler_field":False,
            "data_at_effective_address_read":False,
        }
        rows.append(field)
        grouped[(effective,access["access"],access["width"])]+=1
    return {
        "game_code":upstream["game_code"],
        "v84_syntactic_ldr_xrefs":len(sites),
        "direct_access_count":len(rows),
        "direct_accesses":rows,
        "effective_address_summary":[{
            "effective_address":f"0x{ea:08X}",
            "access":rw,
            "width":width,
            "static_opcode_matches":count,
            "confirmed_scheduler_field":False,
        } for (ea,rw,width),count in sorted(grouped.items())],
        "other_instructions_per_literal":dict(sorted(skipped.items())),
        "newly_recognized_arm_halfword_access_count":sum(
            row["width"]=="halfword" for row in rows),
        "static_matches_may_be_data":True,
        "live_thread_objects_dereferenced":False,
        "rom_bytes_exported":False,
    }


def analyze_game(rom):
    # Re-run the established strict original ROM + exact ARM function
    # fingerprint + ABI chain. Never accept arbitrary ROMs.
    prev=v84.analyze_game(rom)
    meta,image=v75.v74.reconstruct(rom,include_runtime_image=True)
    if meta["arm9"]["runtime_decompressed_sha256"]!=prev["arm9_runtime_sha256"]:
        raise FieldXrefError("V8.4 reconstructed original ARM9 mismatch")
    base=int(meta["arm9"]["ram_load"],16)
    out=analyze_image(image,base,prev)
    out["rom_sha1"]=prev["rom_sha1"]
    out["arm9_runtime_sha256"]=prev["arm9_runtime_sha256"]
    return out


def compare(hg,ss):
    by_code={hg["game_code"]:hg,ss["game_code"]:ss}
    if set(by_code)!={"IPKE","IPGE"} or len(by_code)!=2:
        raise FieldXrefError("requires original USA Rev0 HG and SS ROMs")
    a,b=by_code["IPKE"],by_code["IPGE"]
    def key(row):
        return (row["source_instruction"],row["source_literal"],
                row["effective_address"],row["access"],row["width"])
    A={key(x):x for x in a["direct_accesses"]}
    B={key(x):x for x in b["direct_accesses"]}
    if len(A)!=len(a["direct_accesses"]) or len(B)!=len(b["direct_accesses"]):
        raise FieldXrefError("ambiguous duplicate ARM9 access sites")
    shared=sorted(set(A)&set(B))
    # Diagnostic-only arithmetic against the user-observed V8.8 words.
    low=V88_RAW_WORDS[0x021E169C]&0xFFFF
    max_entry=(V88_RAW_WORDS[0x021E169C]>>16)&0xFFFF
    first_entry=V88_RAW_WORDS[0x021E16B0]
    return {
        "tool":"hgss-v8.9-original-nitrosdk-2x-halfword-and-word-field-crossrefs",
        "heartgold":a,
        "soulsilver":b,
        "shared_direct_access_count":len(shared),
        "heartgold_only_accesses":len(set(A)-set(B)),
        "soulsilver_only_accesses":len(set(B)-set(A)),
        "shared_direct_accesses":[{
            "source_instruction":k[0],
            "source_literal":k[1],
            "effective_address":k[2],
            "access":k[3],
            "width":k[4],
            "validated_executable":False,
            "confirmed_osthreadinfo_field":False,
        } for k in shared],
        "v88_user_photo_raw_header":{
            f"0x{addr:08X}":f"0x{value:08X}"
            for addr,value in sorted(V88_RAW_WORDS.items())
        },
        "hypothesis_legacy_struct_at_0x021e169c":{
            "low_half_possible_is_need_rescheduling":low,
            "upper_half_possible_max_entry":max_entry,
            "entry0_if_legacy_layout":f"0x{first_entry:08X}",
            "entry0_valid_aligned_ntr_ram_pointer":
                (first_entry%4==0 and 0x02000000<=first_entry<=0x023ffffc),
            "interpretation":"disfavored by live raw values; not a verified struct",
            "base_proven":False,
        },
        "hypothesis_newer_struct_at_0x021e16a0":{
            "first_word":f"0x{V88_RAW_WORDS[0x021E16A0]:08X}",
            "current_candidate":f"0x{V88_RAW_WORDS[0x021E16A4]:08X}",
            "list_candidate":f"0x{V88_RAW_WORDS[0x021E16A8]:08X}",
            "callback_candidate":f"0x{V88_RAW_WORDS[0x021E16AC]:08X}",
            "interpretation":"consistent values; no source/SDK version proof",
            "base_proven":False,
        },
        "osthreadinfo_base_confirmed":False,
        "game_native_osthread_layout_proven":False,
        "worker_memory_allocation_safe":False,
        "os_create_thread_safe":False,
        "arm7_wifi_owned_by_bridge":False,
        "network_enabled":False,
        "rom_or_save_modified":False,
        "next_gate":"Review halfword/word effective-address patterns in both original ROMs. Verify source SDK symbol identity and memory ownership before dereferencing any live thread object.",
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("heartgold",type=Path)
    p.add_argument("soulsilver",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args(argv)
    try:
        originals=[args.heartgold.resolve(),args.soulsilver.resolve()]
        if originals[0]==originals[1]:
            raise FieldXrefError("require two distinct original ROMs")
        if args.output and args.output.resolve() in originals:
            raise FieldXrefError("refusing to overwrite original ROM")
        report=compare(analyze_game(args.heartgold),analyze_game(args.soulsilver))
        payload=json.dumps(report,indent=2,ensure_ascii=False)+"\n"
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
