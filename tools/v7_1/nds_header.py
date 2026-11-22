#!/usr/bin/env python3
"""Read-only NDS header and ARM9 ROM segment identity report.

No game data is modified, extracted, or included in the report.
This does not decompress compressed ARM9 data or resolve Wi-Fi APIs.
"""
import argparse
import hashlib
import json
from pathlib import Path


def parse_nds_header(header: bytes, file_size: int) -> dict:
    if len(header) < 0x30:
        raise ValueError("Truncated NDS header (need at least 0x30 bytes)")
    if file_size < 0x200:
        raise ValueError("Input is too short to be a complete NDS header")
    code_raw = header[0x0C:0x10]
    try:
        code = code_raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("Game code is not ASCII") from exc
    if not all(c.isalnum() and c.isascii() for c in code):
        raise ValueError("Invalid NDS game code")
    rom_offset = int.from_bytes(header[0x20:0x24], "little")
    entry = int.from_bytes(header[0x24:0x28], "little")
    load = int.from_bytes(header[0x28:0x2C], "little")
    size = int.from_bytes(header[0x2C:0x30], "little")
    if (rom_offset < 0x200 or rom_offset % 4 or size == 0
            or size % 4 or size > 32 * 1024 * 1024):
        raise ValueError("ARM9 ROM offset/size is implausible")
    if rom_offset + size > file_size:
        raise ValueError("ARM9 ROM segment exceeds input file")
    if (load % 4 or entry % 4 or load + size > 0x100000000):
        raise ValueError("ARM9 RAM address/entry is invalid or overflows")
    # Some titles store compressed ARM9 bytes. Do not infer an execution
    # image from these addresses/bytes without checking compression status.
    return {
        "game_code": code,
        "hgss_candidate": code[:3] in ("IPK", "IPG"),
        "arm9_rom_offset": f"0x{rom_offset:08X}",
        "arm9_entry": f"0x{entry:08X}",
        "arm9_ram_address": f"0x{load:08X}",
        "arm9_rom_size": size,
        "warning": (
            "Header metadata is not proof of a decompressed ARM9 runtime "
            "image, code residency, exact revision, or WCM/SOCL function identity."
        ),
    }


def inspect_rom(path: Path) -> dict:
    with path.open("rb") as stream:
        stream.seek(0, 2)
        total = stream.tell()
        stream.seek(0)
        metadata = parse_nds_header(stream.read(0x200), total)
        offset = int(metadata["arm9_rom_offset"], 16)
        stream.seek(offset)
        remaining = metadata["arm9_rom_size"]
        h = hashlib.sha256()
        while remaining:
            chunk = stream.read(min(65536, remaining))
            if not chunk:
                raise ValueError("Truncated ARM9 ROM segment")
            h.update(chunk)
            remaining -= len(chunk)
        metadata["arm9_stored_sha256"] = h.hexdigest()
    return metadata


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", type=Path, help="local legally obtained NDS dump; never upload it")
    ap.add_argument("--output", type=Path, help="optional JSON report path")
    args = ap.parse_args()
    report = inspect_rom(args.rom)
    result = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
