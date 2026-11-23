#!/usr/bin/env python3
"""Interpret only *raw* ARM7 IRQ-region words photographed on real DSi.

Never read console memory or assume 25 IRQ entries exist because 100 bytes
fit into RAM. A "plausible pointer" is only a weak heuristic, not proof
of dispatcher layout, handler ownership, or permission to hook IRQ_WIFI.
"""
import argparse
import json

# Conservative examples of ordinary NTR executable RAM, not an exhaustive
# list of all mappings, overlays, hardware vectors, or encoded dispatchers.
ORDINARY_NTR_RANGES = (
    (0x02000000, 0x02400000, "NTR main RAM"),
    (0x03000000, 0x03008000, "shared WRAM"),
    (0x037F8000, 0x03810000, "ARM7 WRAM"),
)

def assess_word(word):
    if not isinstance(word, int) or not 0 <= word <= 0xFFFFFFFF:
        raise ValueError("raw word must be an unsigned 32-bit integer")
    address = word & ~1  # LSB sometimes identifies Thumb entry points.
    match = next((label for low, high, label in ORDINARY_NTR_RANGES
                  if low <= address < high), None)
    return {
        "raw": f"0x{word:08X}",
        "looks_like_ordinary_ntr_code_pointer": bool(match),
        "potential_range": match,
        "interpretation": ("Plausible address only; table layout NOT verified"
                           if match else
                           "Not an ordinary NTR RAM handler pointer; raw data unexplained"),
    }

def analyze(table, image_start, image_bytes, method, words):
    if len(words) != 3:
        raise ValueError("provide exactly slot0, slot16, slot24")
    for field in (table, image_start, image_bytes, method):
        if not isinstance(field, int) or not 0 <= field <= 0xFFFFFFFF:
            raise ValueError("all snapshot fields must be unsigned 32-bit")
    if table & 3 or image_start & 3:
        raise ValueError("misaligned table or ARM7 image")
    in_image = (table >= image_start and image_bytes >= 100 and
                table - image_start <= image_bytes - 100)
    mapped = {name: assess_word(word)
              for name, word in zip(("slot0", "slot16", "slot24"), words)}
    return {
        "table": f"0x{table:08X}",
        "image_start": f"0x{image_start:08X}",
        "image_bytes": f"0x{image_bytes:08X}",
        "source": {1: "cached address", 2: "known SDK location",
                   3: "signature scan", 4: "relative literal"}.get(method, "unverified"),
        "slot24_candidate_address": f"0x{table + 96:08X}" if table <= 0xFFFFFF9F else "OVERFLOW",
        "25_slots_fit_image_numerically": in_image,
        "raw_words": mapped,
        "raw_words_all_look_like_ordinary_code_addresses":
            all(x["looks_like_ordinary_ntr_code_pointer"] for x in mapped.values()),
        "verified_irq_table": False,
        "irq_wifi_hook_allowed": False,
        "required_next_evidence": [
            "Compare IRQ words as located at boot with words after HGSS startup",
            "Confirm cache key/version against current ROM/ARM7 binary and patch offsets",
            "Identify actual IRQ dispatch layout and whether slot24 is a handler entry",
            "Verify original handler ownership/chaining and timer3/DSWifi resource use",
        ],
        "caveat": (
            "Raw memory samples are not guaranteed to be function pointers. "
            "Out-of-range data could be stale cache, overwritten memory, "
            "an encoded/different table format, or a measurement issue. "
            "No write or radio initialization is authorized."
        )
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("table", "image-start", "image-bytes", "method",
                 "slot0", "slot16", "slot24"):
        ap.add_argument("--"+name, required=True, type=lambda s: int(s,0))
    args=ap.parse_args()
    report=analyze(args.table, args.image_start, args.image_bytes,
                   args.method, [args.slot0,args.slot16,args.slot24])
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
