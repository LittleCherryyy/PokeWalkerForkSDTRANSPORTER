#!/usr/bin/env python3
"""Read-only identification of a locally owned HGSS NDS image.

Do not upload/distribute a ROM. This utility never patches or extracts game
data; it records metadata/hashes to scope future ABI research.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

# Published checksums of unchanged US game images (pret/pokeheartgold README).
KNOWN_US_SHA1 = {
    "4fcded0e2713dc03929845de631d0932ea2b5a37": "HeartGold US reference",
    "f8dc38ea20c17541a43b58c5e6d18c1732c7e582": "SoulSilver US reference",
}
EXPECTED_GAME_CODES = {"IPKE": "HeartGold US", "IPGE": "SoulSilver US"}


def _hash_range(handle, at, length, algorithm):
    digest = hashlib.new(algorithm)
    handle.seek(at)
    while length:
        block = handle.read(min(1024 * 1024, length))
        if not block:
            raise ValueError("Unexpected EOF while hashing image.")
        digest.update(block)
        length -= len(block)
    return digest.hexdigest()


def identify(path):
    path = Path(path)
    size = path.stat().st_size
    if size < 0x200:
        raise ValueError("File too short for a Nintendo DS header.")
    with path.open("rb") as f:
        header = f.read(0x200)
        game_code = header[0x0C:0x10].decode("ascii", errors="replace")
        arm9_offset, arm9_entry, arm9_load, arm9_size = struct.unpack_from("<IIII", header, 0x20)
        if arm9_offset < 0x200 or arm9_size == 0 or arm9_offset > size or arm9_size > size - arm9_offset:
            raise ValueError("Invalid ARM9 offset/size in NDS header.")
        image_sha1 = _hash_range(f, 0, size, "sha1")
        arm9_sha256 = _hash_range(f, arm9_offset, arm9_size, "sha256")
    known = KNOWN_US_SHA1.get(image_sha1)
    return {
        "game_code": game_code,
        "game": EXPECTED_GAME_CODES.get(game_code, "Unsupported/unverified region or title"),
        "rom_version": header[0x1E],
        "unit_code": header[0x12],
        "image_size": size,
        "image_sha1": image_sha1,
        "reference_match": known,
        "arm9_rom_offset": f"0x{arm9_offset:08X}",
        "arm9_entry": f"0x{arm9_entry:08X}",
        "arm9_load": f"0x{arm9_load:08X}",
        "arm9_size": arm9_size,
        "arm9_sha256": arm9_sha256,
        "callable_wifi_api_verified": False,
        "warning": "Hashes and title codes do not establish function addresses or Wi-Fi ABI compatibility.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only HGSS identity and ARM9 hash (no ROM patching).")
    ap.add_argument("rom", type=Path, help="Path to a game backup you own; remains local")
    args = ap.parse_args(argv)
    try:
        info = identify(args.rom)
    except (OSError, ValueError) as exc:
        ap.exit(2, f"ERROR: {exc}\n")
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
