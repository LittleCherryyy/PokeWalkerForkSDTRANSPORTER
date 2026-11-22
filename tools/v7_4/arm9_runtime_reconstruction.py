#!/usr/bin/env python3
"""Reconstruct HGSS's static ARM9 executable image locally, without writing ROM bytes.

This is a *bounded* BLZ decoder matching nds-bootstrap's backwards decoding
logic. Only exact, published US HGSS SHA-1 revisions are accepted by default.
Successful byte reconstruction does not verify an in-game Wi-Fi ABI or authorize
execution of WCM/SOC calls.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

_TOOL = Path(__file__).resolve().parent.parent / "v7_3" / "hgss_wifi_abi_audit.py"
_spec = importlib.util.spec_from_file_location("v73_hgss_audit", _TOOL)
_v73 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_v73)

MAX_DECOMPRESSED_BYTES = 0x3E0000
BASE = 0x02000000
END = 0x02400000


class BLZError(ValueError):
    pass


def decompress_backwards(encoded: bytes, compressed_end: int,
                         load_address: int = BASE):
    """Decode the NitroSDK backward-LZ region; return reconstructed static bytes.

    The 'compressed_end' value is taken from module params in the ARM9 raw
    image, *not* from the ROM file footer by heuristic. The 8-byte footer
    contains (24-bit compressed span | 8-bit header length) and expansion size.
    All indices are checked before dereference, preventing malformed ROMs
    from writing outside a bounded bytearray.
    """
    code_len = len(encoded)
    if code_len < 32 or compressed_end != load_address + code_len:
        raise BLZError("compressed-static-end differs from ARM9 raw image end")
    header_word, expansion = struct.unpack_from("<II", encoded, code_len - 8)
    header_size = header_word >> 24
    packed_span = header_word & 0xFFFFFF
    if not 8 <= header_size <= 11:
        raise BLZError("BLZ footer header length is invalid")
    if not header_size < packed_span <= code_len:
        raise BLZError("BLZ compressed span outside image")
    if not 0 < expansion <= MAX_DECOMPRESSED_BYTES - code_len:
        raise BLZError("BLZ output would exceed safe DS main RAM capacity")
    if not BASE <= load_address < END or load_address + code_len + expansion > END:
        raise BLZError("BLZ output exceeds DS main RAM")
    source_pos = code_len - header_size
    source_floor = code_len - packed_span
    destination_pos = code_len + expansion
    result = bytearray(encoded)
    result.extend(b"\0" * expansion)
    flags = 0
    while source_pos > source_floor:
        source_pos -= 1
        flags = result[source_pos]
        for _ in range(8):
            if source_pos <= source_floor:
                break
            if not flags & 0x80:
                source_pos -= 1
                destination_pos -= 1
                if source_pos < source_floor or destination_pos < source_floor:
                    raise BLZError("BLZ literal underflow")
                result[destination_pos] = result[source_pos]
            else:
                if source_pos - 2 < source_floor:
                    raise BLZError("BLZ truncated backreference")
                high = result[source_pos - 1]
                low = result[source_pos - 2]
                source_pos -= 2
                backwards_offset = (((high & 0x0F) << 8) | low) + 2
                count = (high >> 4) + 3
                for _ in range(count):
                    if destination_pos <= source_floor:
                        raise BLZError("BLZ backreference underflow")
                    offset = destination_pos + backwards_offset
                    if not destination_pos <= offset < len(result):
                        raise BLZError("BLZ backreference outside written region")
                    byte = result[offset]
                    destination_pos -= 1
                    result[destination_pos] = byte
            flags = (flags << 1) & 0xFF
    if source_pos != source_floor or destination_pos != source_floor:
        raise BLZError("BLZ stream ended without matching its declared output length")
    return result, {
        "compressed_span_bytes": packed_span,
        "compression_footer_header_bytes": header_size,
        "growth_bytes": expansion,
        "static_file_bytes": code_len,
        "static_runtime_bytes": len(result),
    }


def reconstruct(path, *, include_runtime_image=False):
    path = Path(path)
    report = _v73.audit_rom(path)
    if not report["matching_known_us_reference"]:
        raise BLZError("not an exact verified US HGSS reference ROM")
    raw = report["arm9"]
    if int(raw["ram_load"], 16) != BASE:
        raise BLZError("unsupported ARM9 RAM load address")
    params = report["arm9_nitro_module_params"]
    if params["raw_marker_matches"] != 1 or not params["unique_raw_candidate"]:
        raise BLZError("unique NitroSDK module marker not available")
    candidate = params["unique_raw_candidate"]
    params_at = int(candidate["raw_arm9_file_offset"], 16)
    raw_length = raw["file_bytes"]
    file_at = int(raw["rom_offset"], 16)
    end = int(candidate["compressed_static_end_candidate"], 16)
    if params_at + 0x24 > raw_length:
        raise BLZError("module params outside ARM9 binary")
    with path.open("rb") as f:
        encoded = _v73.read_exact(f, file_at, raw_length, "ARM9 static image")
    if hashlib.sha256(encoded).hexdigest() != raw["raw_file_sha256"]:
        raise BLZError("raw ARM9 fingerprint mismatch")
    # The stock nds-bootstrap clears compressed_static_end after decoding.
    runtime, meta = decompress_backwards(encoded, end)
    struct.pack_into("<I", runtime, params_at + 0x14, 0)
    module_marker = runtime[params_at + 0x1C:params_at + 0x24]
    if module_marker != bytes.fromhex("2106c0dede c00621"):
        raise BLZError("module marker changed during decompression")
    report["arm9"]["runtime_decompressed_sha256"] = hashlib.sha256(runtime).hexdigest()
    report["arm9"]["runtime_reconstructed_bytes"] = len(runtime)
    report["arm9"]["runtime_reconstruction_method"] = "Nintendo BLZ backward LZ + cleared compressed_static_end"
    report["arm9"]["executable_address_verified"] = False
    report["arm9_nitro_module_params"]["runtime_params_validated"] = True
    report["arm9_nitro_module_params"]["compressed_static_end_zeroed_in_hash"] = True
    report["network_abi"]["arm9_main_runtime_decompression_verified"] = True
    report["network_abi"]["wifi_calls_permitted"] = False
    report["blz_reconstruction"] = meta
    report["next_gate"] = ("Independently map exact WCM/SOC instructions and ABI in the "
                           "reconstructed runtime image; no network calls yet.")
    # For local offline analyzers only. The image is never written to JSON.
    if include_runtime_image:
        return report, runtime
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", type=Path, help="Your own exact US HGSS .nds (opened read-only)")
    ap.add_argument("--output", type=Path, help="Write JSON report (no ROM bytes)")
    args = ap.parse_args(argv)
    try:
        if args.output and args.output.resolve() == args.rom.resolve():
            raise BLZError("the JSON output must never overwrite the ROM")
        result = reconstruct(args.rom)
        out = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(out, encoding="utf-8")
        print(out, end="")
        return 0
    except (OSError, BLZError, ValueError, struct.error) as e:
        print("ERROR: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
