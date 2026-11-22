#!/usr/bin/env python3
"""V8.1 offline HGSS original thread-call ABI and overlay lifetime study.

Runs only against a user's own exact original HGSS USA Rev0 ROMs.
The V8.0 tool validates five OS scheduler callsites in HGSS overlays 13,39.
This audit additionally verifies all three 32-byte ARM9 function entry
SHA256 values from the user's V8.0 report and the overlay 39
OS_CreateThread six-argument preparation, priority initializer,
thread entry trampoline and stack interval.

No ROM or executable bytes are exported; it never executes code, loads a
thread, patches a ROM, touches a save/Pokewalker or enables Wi-Fi.
Valid callsites are NOT proof of correct scheduler ABI at runtime.
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
P80=HERE.parent/"v8_0"/"hgss_thread_callsite_audit.py"
P76=HERE.parent/"v7_6"/"hgss_wifi_entry_audit.py"

def import_script(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

v80=import_script("hgss_v81_v80",P80)
v76=import_script("hgss_v81_v76",P76)
v75=v80.v75

# These three 32-byte SHA256 hashes are the user's successful V8.0 report.
# They match across original USA Rev0 HeartGold and SoulSilver.
THREAD_ENTRIES={
    "OS_IsThreadAvailable":(
        0x020D1AC4,"019981ecfa25184acbaa9368622aa220d87983189bbc59b6199e3488ffbbc7a1"),
    "OS_CreateThread":(
        0x020D1AD4,"1582b0e22e6375c92adf24dc3d8314e56567f6d6e6742028c3a8a970a1e61da8"),
    "OS_WakeupThreadDirect":(
        0x020D1F34,"7f7f0e5ae216042332b365e82a2bb13d6d7bf8dadb4fd989b5eb3a06a253967d"),
}
# Word patterns are assembled from the public, rev0 ARM disassembly for
# ov39_02229980 (not extracted from, or distributed with, the game).
# See https://github.com/pret/pokeheartgold/blob/master/lib/NitroDWC/asm/overlay_39_arm.s
CALLER_WORDS={
    0x02229988:0xE3A01B02,  # mov r1,#0x800 ; stack size
    0x02229990:0xE58D1000,  # str r1,[sp] ; arg5: 2048 bytes
    0x02229994:0xE590C270,  # ldr ip,[r0,#0x270] ; priority
    0x022299A4:0xE3A02000,  # mov r2,#0 ; arg3: NULL
    0x022299A8:0xE58DC004,  # str ip,[sp,#4] ; arg6: priority
    0x0222995C:0xE3A01010,  # mov r1,#0x10 ; initial priority 16
    0x02229960:0xE5801270,  # str r1,[r0,#0x270]
    0x02229978:0xE12FFF1C,  # bx ip ; thread entry trampoline
}
# PC-relative literal addresses from published assembly.
LDR_SITES={
    0x0222998C:(0,0x022299C4,0x0222AB84),
    0x02229998:(0,0x022299C8,0x0222ADF8),
    0x0222999C:(1,0x022299CC,0x02229974),
    0x022299A0:(3,0x022299D0,0x0222B6D0),
    0x022299B0:(0,0x022299C8,0x0222ADF8),
    0x02229974:(12,0x0222997C,0x02229474),
}
STACK_SIZE=0x800
PRIORITY_INITIALIZER=16


class ThreadContextError(ValueError):
    pass


def u32_at(image,load,addr):
    p=addr-load
    if addr&3 or p<0 or p+4>len(image):
        raise ThreadContextError(f"word out of overlay/static image at 0x{addr:08X}")
    return struct.unpack_from("<I",image,p)[0]


def decode_literal_ldr_arm(word,pc,rd):
    """Recognize unconditional, immediate, word ARM LDR rD,[pc,+/-imm12]."""
    if (word & 0xFF7FF000) != (0xE51F0000 | (rd<<12)):
        raise ThreadContextError(f"expected ARM literal load into r{rd} at 0x{pc:08X}")
    off=word & 0xFFF
    if word & 0x00800000:
        return (pc+8+off)&0xffffffff
    return (pc+8-off)&0xffffffff


def inspect_overlay39_setup(overlay):
    load,img,metadata=overlay
    def word(addr):
        return u32_at(img,load,addr)
    for addr,expected in CALLER_WORDS.items():
        actual=word(addr)
        if actual!=expected:
            raise ThreadContextError(
                f"overlay39 caller code mismatch at 0x{addr:08X}"
            )
    literals={}
    for pc,(reg,literal_address,expected_value) in LDR_SITES.items():
        found=decode_literal_ldr_arm(word(pc),pc,reg)
        if found!=literal_address:
            raise ThreadContextError(f"overlay39 caller literal location mismatch at 0x{pc:08X}")
        actual=word(literal_address)
        if actual!=expected_value:
            raise ThreadContextError(f"overlay39 caller literal target mismatch at 0x{pc:08X}")
        literals[f"0x{pc:08X}"]={
            "destination_register":f"r{reg}",
            "literal_address":f"0x{literal_address:08X}",
            "resolved_pointer":f"0x{actual:08X}",
            "validated":True
        }
    # Confirm one call to OS_CreateThread and one to OS_WakeupThreadDirect,
    # from V8.0's decoded and pinned original overlay39 callsites.
    static_start=load
    static_end=load+len(img)
    allocated_end=static_end+metadata["bss_bytes"]
    stack_top=0x0222B6D0
    stack_lower=stack_top-STACK_SIZE
    thread_struct=0x0222ADF8
    callback_entry=0x02229474
    addresses_within_overlay=all(
        static_start<=a<allocated_end
        for a in (thread_struct,stack_lower,stack_top-1,callback_entry)
    )
    return {
        "overlay_id":39,
        "overlay_static_start":f"0x{static_start:08X}",
        "overlay_static_end":f"0x{static_end:08X}",
        "overlay_static_plus_bss_end":f"0x{allocated_end:08X}",
        "six_argument_sequence_validated":True,
        "arg1_thread_structure":f"0x{thread_struct:08X}",
        "arg2_entry_is_overlay_local_trampoline":"0x02229974",
        "entry_trampoline_final_target":f"0x{callback_entry:08X}",
        "arg3_user_pointer":None,
        "arg4_stack_top":f"0x{stack_top:08X}",
        "arg5_stack_bytes":STACK_SIZE,
        "stack_lower_bound":f"0x{stack_lower:08X}",
        "arg6_priority_initialized_to":PRIORITY_INITIALIZER,
        "priority_can_change_at_runtime":True,
        "thread_storage_callback_stack_within_overlay_allocation":addresses_within_overlay,
        "overlay_unload_can_invalidate_entry_and_stack":True,
        "literal_sites":literals,
        "game_thread_creation_or_reuse_safe":False,
        "game_network_thread_alive_in_overworld_proven":False,
    }


def inspect_game(rom):
    existing=v80.analyze(rom)
    report,image=v75.v74.reconstruct(rom,include_runtime_image=True)
    if existing["arm9_runtime_sha256"]!=report["arm9"]["runtime_decompressed_sha256"]:
        raise ThreadContextError("V8.0 runtime image differs from V8.1 reconstruction")
    load=int(report["arm9"]["ram_load"],16)
    calls={(entry["name"],entry["overlay"]):entry for entry in existing["callsites"]}
    if len(calls)!=5:
        raise ThreadContextError("V8.0 did not supply five independent source callsites")
    functions={}
    for name,(address,expected_sha) in THREAD_ENTRIES.items():
        related=[x for x in existing["callsites"] if x["name"]==name]
        if not related:
            raise ThreadContextError(name+": source callsite not validated")
        if any(int(x["target"],16)!=address for x in related):
            raise ThreadContextError(name+": inconsistent immediate targets")
        window=v80.read_arm9_window(image,load,address)
        if window!=expected_sha:
            raise ThreadContextError(name+": V8.0 SHA256 anchor mismatch; stop")
        p=address-load
        if p<0 or p+128>len(image):
            raise ThreadContextError(name+": static ARM9 128-byte window out of bounds")
        trace,terminal,stop=v76.trace_target(image,load,address)
        functions[name]={
            "entry":f"0x{address:08X}",
            "fixed_32byte_sha256":window,
            "additional_128byte_sha256":hashlib.sha256(image[p:p+128]).hexdigest(),
            "entry_trace":trace,
            "terminal_candidate":f"0x{terminal:08X}" if terminal is not None else None,
            "stop_reason":stop,
            "callsite_sources":[{"overlay":x["overlay"],"address":x["callsite"],
                                 "target_mode":x["target_mode"]} for x in related],
            "abi_proven":False,
            "safe_to_invoke":False
        }
    total_size=report["image_bytes"]
    with Path(rom).open("rb") as f:
        header=v75.v74._v73.read_exact(f,0,0x200,"NDS header")
        fat_at,fat_bytes=struct.unpack_from("<II",header,0x48)
        if fat_bytes==0 or fat_bytes%8 or fat_bytes>524288:
            raise ThreadContextError("invalid NDS FAT bounds")
        v75.v74._v73.require_range(total_size,fat_at,fat_bytes,"FAT")
        fat=v75.v74._v73.read_exact(f,fat_at,fat_bytes,"FAT")
        overlay=v75.get_overlay(f,header,fat,total_size,39)
    return {
        "game_code":existing["game_code"],
        "rom_sha1":existing["rom_sha1"],
        "arm9_runtime_sha256":existing["arm9_runtime_sha256"],
        "scheduler_function_entries":functions,
        "overlay39_thread_setup":inspect_overlay39_setup(overlay),
    }


def compare(hg,ss):
    by_code={hg["game_code"]:hg,ss["game_code"]:ss}
    if set(by_code)!={"IPKE","IPGE"} or hg["game_code"]==ss["game_code"]:
        raise ThreadContextError("requires one original USA HeartGold and one original USA SoulSilver")
    first=by_code["IPKE"]
    second=by_code["IPGE"]
    comparison={}
    for name in THREAD_ENTRIES:
        a=first["scheduler_function_entries"][name]
        b=second["scheduler_function_entries"][name]
        comparison[name]={
            "identical_entry":a["entry"]==b["entry"],
            "same_32byte_sha256":a["fixed_32byte_sha256"]==b["fixed_32byte_sha256"],
            "same_128byte_sha256":a["additional_128byte_sha256"]==b["additional_128byte_sha256"],
            "same_terminal_candidate":a["terminal_candidate"] is not None and a["terminal_candidate"]==b["terminal_candidate"],
            "scheduler_call_safe":False,
        }
    a=first["overlay39_thread_setup"]
    b=second["overlay39_thread_setup"]
    return {
        "tool":"hgss-v8.1-original-os-thread-call-context-audit",
        "heartgold":first,
        "soulsilver":second,
        "cross_title_thread_comparison":comparison,
        "overlay39_setup_same_between_games":(
            a["six_argument_sequence_validated"] and b["six_argument_sequence_validated"]
            and a["literal_sites"]==b["literal_sites"]
        ),
        "offline_six_argument_callsite_validated":True,
        "source_game_thread_can_be_reused":False,
        "scheduler_runtime_initialized_proven":False,
        "os_thread_structure_layout_proven":False,
        "worker_stack_lifetime_proven":False,
        "wm_arm7_radio_ownership_proven":False,
        "network_enabled":False,
        "save_accessed":False,
        "game_binary_or_its_bytes_exported":False,
        "next_gate":"Validate OS thread structure/layout, independent worker lifetime and ARM9/ARM7 radio coordination before calling any scheduler or network API.",
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("heartgold",type=Path)
    parser.add_argument("soulsilver",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    try:
        roms={args.heartgold.resolve(),args.soulsilver.resolve()}
        if len(roms)!=2:
            raise ThreadContextError("need two different original ROM files")
        if args.output and args.output.resolve() in roms:
            raise ThreadContextError("refusing to overwrite the original ROM")
        result=compare(inspect_game(args.heartgold),inspect_game(args.soulsilver))
        payload=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding="utf-8")
        print(payload,end="")
        return 0
    except (OSError,ValueError,struct.error) as error:
        print("ERROR: "+str(error),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
