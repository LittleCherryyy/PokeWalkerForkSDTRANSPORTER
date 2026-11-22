#!/usr/bin/env python3
"""Read-only HGSS ARM9 overlay table inspection.

Reads only the NDS header, overlay table, and optional 8-byte FAT entries
from a local legally obtained game dump. Never writes, extracts overlays,
executes game code, or uploads ROM bytes. Overlay metadata proves *where*
a module may load, NOT whether it is resident during the Pokewalker menu.
"""
import argparse
import json
from pathlib import Path

OVERLAY_ENTRY_SIZE = 32
MAX_ENTRIES = 8192


def u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "little")


def read_region(stream, file_size: int, offset: int, size: int) -> bytes:
    if offset < 0 or size < 0 or offset + size > file_size:
        raise ValueError("Overlay/FAT table extends outside ROM")
    stream.seek(offset)
    data = stream.read(size)
    if len(data) != size:
        raise ValueError("Truncated overlay/FAT table")
    return data


def inspect_overlays(path: Path, overlay_id: int | None = 0) -> dict:
    if overlay_id is not None and not 0 <= overlay_id <= 0xFFFFFFFF:
        raise ValueError("Overlay id is out of range")
    with path.open("rb") as stream:
        stream.seek(0, 2)
        file_size = stream.tell()
        if file_size < 0x200:
            raise ValueError("Truncated NDS header")
        stream.seek(0)
        hdr = stream.read(0x200)
        game_code = hdr[0x0C:0x10]
        if len(game_code) != 4 or game_code[:3] not in (b"IPK", b"IPG"):
            raise ValueError("Only HeartGold/SoulSilver NDS dumps supported")
        try:
            code = game_code.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError("Invalid game code") from exc

        offset = u32(hdr, 0x50)
        size = u32(hdr, 0x54)
        if not offset or not size or offset < 0x200 or offset % 4:
            raise ValueError("Missing or invalid ARM9 overlay table")
        if size % OVERLAY_ENTRY_SIZE or size > OVERLAY_ENTRY_SIZE * MAX_ENTRIES:
            raise ValueError("ARM9 overlay table length is invalid")
        table = read_region(stream, file_size, offset, size)
        fat_offset = u32(hdr, 0x48)
        fat_size = u32(hdr, 0x4C)
        fat_valid = fat_offset >= 0x200 and fat_offset % 4 == 0 and fat_size % 8 == 0
        if fat_valid:
            if fat_offset + fat_size > file_size:
                raise ValueError("FAT exceeds ROM size")
        else:
            if fat_offset or fat_size:
                raise ValueError("Malformed FAT header")
        rows = []
        seen = set()
        for pos in range(0, size, OVERLAY_ENTRY_SIZE):
            row = table[pos:pos + OVERLAY_ENTRY_SIZE]
            ident = u32(row, 0)
            if ident in seen:
                raise ValueError("Duplicate ARM9 overlay ID")
            seen.add(ident)
            if overlay_id is not None and ident != overlay_id:
                continue
            ram = u32(row, 4)
            code_size = u32(row, 8)
            bss = u32(row, 12)
            init_start = u32(row, 16)
            init_end = u32(row, 20)
            file_id = u32(row, 24)
            flags = u32(row, 28)
            end = ram + code_size + bss
            if code_size == 0 or ram % 4 or end > 0x100000000:
                raise ValueError("Invalid overlay RAM address or length")
            if init_start > init_end:
                raise ValueError("Invalid overlay initializer range")
            item = {
                "overlay_id": ident,
                "ram_address": f"0x{ram:08X}",
                "initialized_bytes": code_size,
                "bss_bytes": bss,
                "ram_end_exclusive": f"0x{end:08X}",
                "static_init_start": f"0x{init_start:08X}",
                "static_init_end": f"0x{init_end:08X}",
                "file_id": file_id,
                "flags_raw": f"0x{flags:08X}",
            }
            if fat_valid:
                if (file_id + 1) * 8 > fat_size:
                    raise ValueError("Overlay file ID exceeds NDS FAT")
                fat = read_region(stream, file_size, fat_offset + file_id * 8, 8)
                file_begin, file_end = u32(fat, 0), u32(fat, 4)
                if file_begin > file_end or file_end > file_size:
                    raise ValueError("Overlay stored file range invalid")
                item["stored_file_offset"] = f"0x{file_begin:08X}"
                item["stored_file_length"] = file_end - file_begin
            else:
                item["stored_file_offset"] = None
                item["stored_file_length"] = None
            rows.append(item)

        return {
            "game_code": code,
            "header_rom_revision": hdr[0x1E],
            "total_arm9_overlays": size // OVERLAY_ENTRY_SIZE,
            "requested_id": overlay_id,
            "matches": rows,
            "note": (
                "ROM metadata only: addresses are possible load targets, "
                "not evidence that the DWC overlay, WCM/SOC library or radio "
                "is active during HGSS Pokewalker IR use. This report "
                "contains no executable game data."
            ),
        }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", type=Path, help="local owned HGSS .nds dump; do not upload")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--overlay-id", type=int, default=0)
    group.add_argument("--all", action="store_true", help="list metadata for all ARM9 overlays")
    ap.add_argument("--output", type=Path, help="optional local JSON report")
    args = ap.parse_args()
    result = inspect_overlays(args.rom, None if args.all else args.overlay_id)
    output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
