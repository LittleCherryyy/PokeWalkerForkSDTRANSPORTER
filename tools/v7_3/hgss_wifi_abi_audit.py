#!/usr/bin/env python3
"""Read-only layout and fingerprint audit of a locally owned HGSS .nds image.

No game bytes are copied into the report. The script does not patch ROMs,
access save files or try to execute any game network function.
Python 3.8+; stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

EXPECTED_CODES = {
    "IPKE": "HeartGold (USA)", "IPGE": "SoulSilver (USA)",
    "IPKJ": "HeartGold (Japan)", "IPGJ": "SoulSilver (Japan)",
    "IPKP": "HeartGold (Europe)", "IPGP": "SoulSilver (Europe)",
}
KNOWN_US_SHA1 = {
    "4fcded0e2713dc03929845de631d0932ea2b5a37": "HeartGold US reference",
    "f8dc38ea20c17541a43b58c5e6d18c1732c7e582": "SoulSilver US reference",
}
HEADER_BYTES = 0x200
MAX_ROM_BYTES = 512 * 1024 * 1024
MAX_OVERLAYS = 2048
# HGSS decomp identifies overlay 72 as Nintendo WFC application. Presence
# on the ROM does not establish that the overlay is loaded in the overworld.
WFC_APP_OVERLAY_ID = 72


def hex32(n: int) -> str:
    return f"0x{n:08X}"


def crc16_nitro(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc >> 1) ^ (0xA001 if crc & 1 else 0)) & 0xFFFF
    return crc


def require_range(file_size, at, count, description, *, min_offset=HEADER_BYTES):
    if at < min_offset or count < 0 or at > file_size or count > file_size - at:
        raise ValueError(description + ": offset/length outside image")


def read_exact(f, at, count, description):
    f.seek(at)
    data = f.read(count)
    if len(data) != count:
        raise ValueError(description + ": premature end of ROM")
    return data


def hash_range(f, at, count, algorithm="sha256"):
    digest = hashlib.new(algorithm)
    f.seek(at)
    while count:
        chunk = f.read(min(1024 * 1024, count))
        if not chunk:
            raise ValueError("truncated ROM during hashing")
        digest.update(chunk)
        count -= len(chunk)
    return digest.hexdigest()


def code_segment(f, header, start, file_size, name):
    at, entry, load, size = struct.unpack_from("<4I", header, start)
    if size == 0:
        raise ValueError(name + ": empty executable")
    require_range(file_size, at, size, name)
    return {
        "rom_offset": hex32(at), "ram_entry": hex32(entry),
        "ram_load": hex32(load), "file_bytes": size,
        "raw_file_sha256": hash_range(f, at, size),
        "runtime_decompressed_sha256": None,
        "executable_address_verified": False,
    }


def overlays(f, header, table_at, fat, size, name):
    at, length = struct.unpack_from("<2I", header, table_at)
    if not length:
        return {"count": 0, "ids": [], "selected": []}
    require_range(size, at, length, name + " overlay table")
    if length % 32 or length // 32 > MAX_OVERLAYS:
        raise ValueError(name + ": malformed overlay table length")
    table = read_exact(f, at, length, name + " overlay table")
    seen = set()
    selected = []
    for ix in range(length // 32):
        (overlay_id, ram, ram_bytes, bss, init_begin,
         init_end, file_id, flags) = struct.unpack_from("<8I", table, 32 * ix)
        if overlay_id in seen:
            raise ValueError(name + ": repeated overlay ID")
        seen.add(overlay_id)
        if file_id >= len(fat) // 8:
            raise ValueError(name + ": overlay references missing FAT file ID")
        file_begin, file_end = struct.unpack_from("<2I", fat, 8 * file_id)
        if file_end < file_begin:
            raise ValueError(name + ": FAT file end before start")
        require_range(size, file_begin, file_end - file_begin, name + " overlay file")
        if init_begin > init_end:
            raise ValueError(name + ": overlay initializer range reversed")
        if name == "ARM9" and overlay_id == WFC_APP_OVERLAY_ID:
            selected.append({
                "overlay_id": overlay_id, "file_id": file_id,
                "rom_file_start": hex32(file_begin),
                "rom_file_bytes": file_end - file_begin,
                "runtime_ram_load_candidate": hex32(ram),
                "declared_ram_bytes": ram_bytes,
                "declared_bss_bytes": bss,
                "packed_flags_raw": hex32(flags),
                "raw_file_sha256": hash_range(f, file_begin, file_end - file_begin),
                "resident_during_overworld_verified": False,
                "callable_wifi_abi_verified": False,
            })
    return {"count": len(seen), "ids": sorted(seen), "selected": selected}


def audit_rom(path):
    path = Path(path)
    size = path.stat().st_size
    if not HEADER_BYTES <= size <= MAX_ROM_BYTES:
        raise ValueError("file size outside supported NDS range")
    with path.open("rb") as f:
        h = read_exact(f, 0, HEADER_BYTES, "NDS header")
        try:
            game_code = h[0x0C:0x10].decode("ascii")
        except UnicodeError:
            raise ValueError("invalid non-ASCII game code")
        if not game_code.startswith(("IPK", "IPG")):
            raise ValueError("not a HeartGold/SoulSilver game code")
        arm9 = code_segment(f, h, 0x20, size, "ARM9")
        arm7 = code_segment(f, h, 0x30, size, "ARM7")
        fat_at, fat_len = struct.unpack_from("<2I", h, 0x48)
        if not fat_len or fat_len % 8 or fat_len > 8 * 65536:
            raise ValueError("FAT malformed/absent")
        require_range(size, fat_at, fat_len, "FAT")
        fat = read_exact(f, fat_at, fat_len, "FAT")
        ov9 = overlays(f, h, 0x50, fat, size, "ARM9")
        ov7 = overlays(f, h, 0x58, fat, size, "ARM7")
        sha1 = hash_range(f, 0, size, "sha1")
        stored_crc = struct.unpack_from("<H", h, 0x15E)[0]
        actual_crc = crc16_nitro(h[:0x15E])
    return {
        "tool": "hgss-wifi-abi-audit-v1",
        "scope": "read-only ROM identity/overlay layout; not disassembly or Wi-Fi",
        "game_code": game_code,
        "title": EXPECTED_CODES.get(game_code, "HGSS region not verified"),
        "rom_version": h[0x1E], "unit_code": h[0x12],
        "image_bytes": size, "image_sha1": sha1,
        "matching_known_us_reference": KNOWN_US_SHA1.get(sha1),
        "nds_header_crc16": {
            "stored": f"0x{stored_crc:04X}",
            "computed": f"0x{actual_crc:04X}",
            "match": stored_crc == actual_crc,
        },
        "arm9": arm9, "arm7": arm7,
        "overlay_tables": {"arm9": ov9, "arm7": ov7},
        "network_abi": {
            "wcm_socl_function_addresses_verified": False,
            "function_calling_conventions_verified": False,
            "arm9_main_runtime_decompression_verified": False,
            "wifi_stack_resident_during_gameplay_verified": False,
            "physical_dsi_to_android_ping_verified": False,
            "wifi_calls_permitted": False,
            "reason": "Hashes and overlay presence do not establish callable loaded Wi-Fi functions.",
        },
        "copyright_privacy": "Report contains no game bytes or local source path.",
        "next_gate": "Verify exact ARM9 runtime image + NitroWiFi ABI for this ROM revision.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("rom", type=Path, help="Your own .nds backup; opened read-only")
    p.add_argument("--output", type=Path, help="Metadata-only JSON output")
    args = p.parse_args(argv)
    try:
        if args.output and args.output.resolve() == args.rom.resolve():
            raise ValueError("output must not overwrite source ROM")
        report = audit_rom(args.rom)
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0
    except (OSError, ValueError, struct.error) as e:
        print("ERROR: " + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
