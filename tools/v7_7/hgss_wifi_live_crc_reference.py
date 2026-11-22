#!/usr/bin/env python3
"""V7.7: compute noncopyright code-window CRC32 references for exact US HGSS.

Opens two user-owned original ROMs read-only; validates exact SHA-1 ROM
identity and the V7.4 bounded BLZ reconstructed ARM9. Then verifies exact
V7.6 32-byte SHA-256 entry-window hashes and emits *only* CRC32 integers
for comparison with the DSi's read-only V7.7 in-game-menu display.
Does not write ROM data, patch files, start networking or read saves.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zlib

HERE=Path(__file__).resolve().parent
V74=HERE.parent/"v7_4"/"arm9_runtime_reconstruction.py"
spec=importlib.util.spec_from_file_location("v74_crc_reference",V74)
v74=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v74)

ENTRIES={
    "WCM_Init":(0x020AD850,"6369f74947b51749f41b1dc42db9f0d10e989d24518127300ea55879176a89fa"),
    "WCM_StartupAsync":(0x020AD9C0,"20af5f8f43b8fa2f1b7747e115b41bda5a876f3406341dc5ccb78c7f7ac8dac8"),
    "WCM_GetPhase":(0x020AE420,"50a48e8d3c3605adc7f1e46386654ec05e1a4fa6af163bd40d665126c22f0aff"),
    "SOC_Socket":(0x020A2EAC,"856fb418640b96d191c34c16da2011da5f10da499fa42eb1785241364b0e3dc0"),
    "SOC_Connect":(0x020A2F04,"c0c3988ea2f7f0f199d8a5c393682f1749d129812599aa66611e7aa28f3642ff"),
}

class ReferenceError(ValueError):
    pass


def inspect_one(path):
    report,arm9=v74.reconstruct(path,include_runtime_image=True)
    game=report["game_code"]
    if game not in ("IPKE","IPGE"):
        raise ReferenceError("not original US HeartGold/SoulSilver revision 0")
    if report["arm9"]["runtime_reconstructed_bytes"]!=1122040:
        raise ReferenceError("unexpected ARM9 runtime size")
    base=int(report["arm9"]["ram_load"],16)
    windows={}
    for label,(addr,sha) in ENTRIES.items():
        off=addr-base
        if off<0 or off+32>len(arm9):
            raise ReferenceError(label+": window outside reconstructed ARM9")
        block=bytes(arm9[off:off+32])
        if hashlib.sha256(block).hexdigest()!=sha:
            raise ReferenceError(label+": V7.6 SHA256 reference mismatch; aborting")
        windows[label]={
            "address":f"0x{addr:08X}",
            "bytes":32,
            "crc32":f"{zlib.crc32(block)&0xffffffff:08X}",
            "v76_sha256_verified":True,
        }
    return {
        "game_code":game,
        "rom_sha1":report["image_sha1"],
        "arm9_runtime_sha256":report["arm9"]["runtime_decompressed_sha256"],
        "windows":windows,
    }


def compare(a,b):
    by_game={a["game_code"]:a,b["game_code"]:b}
    if set(by_game)!={"IPKE","IPGE"} or a["game_code"]==b["game_code"]:
        raise ReferenceError("one original US HeartGold and one original US SoulSilver are required")
    hg=by_game["IPKE"]
    ss=by_game["IPGE"]
    matches={}
    for label in ENTRIES:
        ac=hg["windows"][label]["crc32"]
        bc=ss["windows"][label]["crc32"]
        matches[label]={"heartgold_crc32":ac,"soulsilver_crc32":bc,
                        "equal":ac==bc}
    return {
        "tool":"hgss-v7.7-arm9-live-crc32-reference",
        "scope":"read-only offline CRC reference for DSi menu comparison",
        "heartgold":hg,
        "soulsilver":ss,
        "cross_title_crc32":matches,
        "all_five_crc_equal":all(x["equal"] for x in matches.values()),
        "v76_rom_source_sha256_windows_checked":True,
        "resident_code_verified_on_dsi":False,
        "wifi_abi_verified":False,
        "radio_or_network_enabled":False,
        "game_save_or_walker_accessed":False,
        "next_gate":"Compare DSi V7.7 five live CRC32 values against this report for each title.",
    }


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("first",type=Path,help="First original US .nds")
    ap.add_argument("second",type=Path,help="Second original US .nds")
    ap.add_argument("--output",type=Path,help="JSON path (never a ROM path)")
    args=ap.parse_args(argv)
    try:
        paths={args.first.resolve(),args.second.resolve()}
        if len(paths)!=2:
            raise ReferenceError("two different original ROMs required")
        if args.output and args.output.resolve() in paths:
            raise ReferenceError("refusing to overwrite a ROM")
        result=compare(inspect_one(args.first),inspect_one(args.second))
        text=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(text,encoding="utf-8")
        print(text,end="")
        return 0
    except (OSError,ValueError) as e:
        print("ERROR: "+str(e),file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
