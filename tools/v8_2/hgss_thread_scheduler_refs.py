#!/usr/bin/env python3
"""V8.2 bounded *offline* HGSS USA thread-state reference audit.

Input: two user-owned original HGSS USA Rev0 ROMs.
Checks V8.1 original callsites, entries and ov39 six-argument thread setup.
Inspects at most 128 bytes from each of three OS_* ARM9 function entries.
Extracts only ARM unconditional PC-relative literal *address references*
and possible r0-base immediate memory offsets. It does NOT trace unknown
branches or infer an OSThread structure layout. Bytes/words of game code
are NEVER included in the JSON; possible pointer values are metadata only.

In particular, an address or field offset is NOT a validated global
scheduler state, a safe OS thread pointer, or permission to execute a
NitroSDK function. No network, ROM edits, save access, or executable
code export.  ROM bytes are processed in memory only.
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
P81=HERE.parent/"v8_1"/"hgss_thread_abi_context.py"
spec=importlib.util.spec_from_file_location("v82_v81",P81)
v81=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v81)
v75=v81.v75

WINDOW_BYTES=128
MAX_REFS=20
MAX_OFFSETS=32


class SchedulerRefError(ValueError):
    pass


def classify_pointer(word,arm9_base,arm9_len):
    if not 0x02000000 <= word < 0x02400000:
        return "not ordinary NTR main RAM"
    if arm9_base<=word<arm9_base+arm9_len:
        return "inside reconstructed main ARM9 image (data/code unknown)"
    return "other NTR main RAM (not proven allocated)"


def decode_pc_literal(word,pc):
    """Return (rd, literal_addr) only for AL ARM LDR Rd,[pc,+/-imm12]."""
    rd=(word>>12)&15
    try:
        addr=v81.decode_literal_ldr_arm(word,pc,rd)
    except v81.ThreadContextError:
        return None
    return rd,addr


def decode_r0_memory_offset(word):
    """Syntactic candidate offsets only, not validated OSThread fields."""
    if (word>>28)!=0xE or ((word>>26)&3)!=1:
        return None
    # ARM single-data-transfer, imm12, pre-index, word, no writeback
    if (word&(1<<25)) or not (word&(1<<24)) or (word&(1<<22)) or (word&(1<<21)):
        return None
    rn=(word>>16)&15
    if rn!=0:
        return None
    disp=word&0xfff
    if disp>0x400:
        return None
    if not (word&(1<<23)):
        disp=-disp
    return {
        "signed_offset":disp,
        "access":"load" if (word&(1<<20)) else "store",
        "offset_is_verified_osthread_field":False,
    }


def inspect_entry(image,base,entry,expected_hash,game):
    """Strict read bounds, 128-byte hash match and conservative ISA scan."""
    off=entry-base
    if entry&3 or off<0 or off+WINDOW_BYTES>len(image):
        raise SchedulerRefError(f"{game}: ARM9 entry outside safe window")
    window=memoryview(image)[off:off+WINDOW_BYTES]
    if hashlib.sha256(window).hexdigest()!=expected_hash:
        raise SchedulerRefError(f"{game}: V8.1 128-byte entry hash mismatch")
    references=[]
    offsets=[]
    stop_reason="128-byte window exhausted (not a function boundary)"
    for idx in range(WINDOW_BYTES//4):
        pc=entry+4*idx
        instr=struct.unpack_from("<I",window,idx*4)[0]
        lit=decode_pc_literal(instr,pc)
        if lit is not None and len(references)<MAX_REFS:
            rd,lit_addr=lit
            ptr_offset=lit_addr-base
            item={
                "instruction_address":f"0x{pc:08X}",
                "destination_register":f"r{rd}",
                "literal_address":f"0x{lit_addr:08X}",
                "literal_within_static_arm9":False,
                "pointer_value":None,
                "pointer_classification":"not dereferenced",
                "verified_scheduler_global":False,
            }
            # Read *only* an in-range static literal, never read the pointer target.
            if lit_addr%4==0 and 0<=ptr_offset<=len(image)-4:
                item["literal_within_static_arm9"]=True
                val=struct.unpack_from("<I",image,ptr_offset)[0]
                item["pointer_value"]=f"0x{val:08X}"
                item["pointer_classification"]=classify_pointer(val,base,len(image))
            references.append(item)
        offset=decode_r0_memory_offset(instr)
        if offset is not None and len(offsets)<MAX_OFFSETS:
            offsets.append({"instruction_address":f"0x{pc:08X}",**offset})
        # Stop the linear scan at an unambiguous unconditional return/branch.
        # A forward PC-relative LDR in the last basic block is still reported.
        if instr==0xE12FFF1E: # BX LR
            stop_reason=f"unconditional BX LR at 0x{pc:08X}"
            break
        if (instr&0xFF000000)==0xEA000000: # ARM B (not BL)
            stop_reason=f"unconditional ARM B at 0x{pc:08X}, target not followed"
            break
        if (instr&0xFFFF8000)==0xE8BD8000: # LDMIA sp!,{...,pc}
            stop_reason=f"unconditional ARM pop PC at 0x{pc:08X}"
            break
    return {
        "entry":f"0x{entry:08X}",
        "v81_128byte_sha256_verified":True,
        "linear_scan_bytes":4*(idx+1),
        "stop_reason":stop_reason,
        "pc_relative_literal_references":references,
        "candidate_r0_base_offsets":offsets,
        "scheduler_initialized_proven":False,
        "osthread_field_layout_proven":False,
        "function_safe_to_invoke":False,
        "code_bytes_exported":False,
    }


def check_overlay39_storage(setup):
    """Arithmetic check: all observed objects are overlay-lifetime-bound.

    No assumption is made about the actual OSThread C struct sizeof.
    """
    try:
        static_end=int(setup["overlay_static_end"],16)
        bss_end=int(setup["overlay_static_plus_bss_end"],16)
        obj=int(setup["arg1_thread_structure"],16)
        bot=int(setup["stack_lower_bound"],16)
        top=int(setup["arg4_stack_top"],16)
    except (KeyError,ValueError) as e:
        raise SchedulerRefError("invalid overlay39 storage metadata") from e
    size=setup.get("arg5_stack_bytes")
    if (not isinstance(size,int) or size!=0x800 or
        not (static_end<=obj<bot<top<=bss_end) or
        top-bot!=size or min(obj,bot,top)%4):
        raise SchedulerRefError("overlay39 thread / stack allocation bounds disagree")
    return {
        "static_data_end":f"0x{static_end:08X}",
        "thread_object_start":f"0x{obj:08X}",
        "stack_lower_bound":f"0x{bot:08X}",
        "stack_top":f"0x{top:08X}",
        "reserved_gap_between_object_start_and_stack":bot-obj,
        "gap_is_not_proven_struct_size":True,
        "stack_size":size,
        "stack_and_thread_object_valid_only_while_overlay39_loaded":True,
        "safe_to_allocate_new_worker_here":False,
    }


def analyze(rom):
    # Full V8.1 gate: authentic ROM hashes, static callsites,
    # 32-byte function hashes, six caller arguments, overlay lifetime.
    check=v81.inspect_game(rom)
    report,image=v75.v74.reconstruct(rom,include_runtime_image=True)
    if check["arm9_runtime_sha256"]!=report["arm9"]["runtime_decompressed_sha256"]:
        raise SchedulerRefError("ARM9 reconstruction does not agree with V8.1")
    base=int(report["arm9"]["ram_load"],16)
    signatures={}
    for name,(entry,sha32) in v81.THREAD_ENTRIES.items():
        earlier=check["scheduler_function_entries"][name]
        if int(earlier["entry"],16)!=entry or earlier["fixed_32byte_sha256"]!=sha32:
            raise SchedulerRefError("V8.1 fixed function identity mismatch")
        signatures[name]=inspect_entry(
            image,base,entry,earlier["additional_128byte_sha256"],
            check["game_code"])
    return {
        "game_code":check["game_code"],
        "rom_sha1":check["rom_sha1"],
        "arm9_runtime_sha256":check["arm9_runtime_sha256"],
        "functions":signatures,
        "overlay39_allocation":check_overlay39_storage(check["overlay39_thread_setup"]),
    }


def compare(first,second):
    by_code={first["game_code"]:first,second["game_code"]:second}
    if set(by_code)!={"IPKE","IPGE"} or first["game_code"]==second["game_code"]:
        raise SchedulerRefError("one original USA HeartGold and one SoulSilver required")
    hg=by_code["IPKE"]
    ss=by_code["IPGE"]
    comparisons={}
    for name in v81.THREAD_ENTRIES:
        a=hg["functions"][name]
        b=ss["functions"][name]
        comparisons[name]={
            "same_128byte_entry_hash_and_offsets":
                a["v81_128byte_sha256_verified"] and b["v81_128byte_sha256_verified"]
                and a["candidate_r0_base_offsets"]==b["candidate_r0_base_offsets"],
            "same_literal_references":
                a["pc_relative_literal_references"]==b["pc_relative_literal_references"],
            "same_linear_stop":a["stop_reason"]==b["stop_reason"],
            "runtime_scheduler_state_verified":False,
        }
    return {
        "tool":"hgss-v8.2-offline-scheduler-pointer-candidate-map",
        "heartgold":hg,
        "soulsilver":ss,
        "comparisons":comparisons,
        "overlay39_object_stack_layout_same":
            hg["overlay39_allocation"]==ss["overlay39_allocation"],
        "candidate_addresses_are_NOT_live_memory_reads":True,
        "osthread_struct_size_proven":False,
        "osthread_field_layout_proven":False,
        "scheduler_runtime_initialized_proven":False,
        "independent_worker_lifetime_proven":False,
        "safe_to_call_thread_apis":False,
        "wifi_driver_enabled":False,
        "arm7_radio_ownership_proven":False,
        "rom_save_walker_modified":False,
        "next_gate":"Review candidates and establish a bounded read-only DSi live scheduler probe, with independent safe worker memory still to be proven."
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("heartgold",type=Path,help="Exact original USA HeartGold .nds")
    parser.add_argument("soulsilver",type=Path,help="Exact original USA SoulSilver .nds")
    parser.add_argument("--output",type=Path,help="Metadata-only JSON path")
    args=parser.parse_args(argv)
    try:
        paths=[args.heartgold.resolve(),args.soulsilver.resolve()]
        if paths[0]==paths[1]:
            raise SchedulerRefError("two distinct original ROMs required")
        if args.output and args.output.resolve() in paths:
            raise SchedulerRefError("refusing to overwrite a ROM file")
        result=compare(analyze(args.heartgold),analyze(args.soulsilver))
        payload=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
        print(payload,end="")
        return 0
    except (ValueError,OSError,struct.error) as e:
        print("ERROR: "+str(e),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
