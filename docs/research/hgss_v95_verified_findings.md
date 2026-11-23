# HGSS read-only ROM analysis — V9.5 findings (2026-11-22)

Source: user-generated `wifi_v95_full_rom_index.json` from original USA Rev0 dumps, processed locally. This report summarizes **metadata**, not ROM bytes.

## Verified inventory

| Item | HeartGold (IPKE) | SoulSilver (IPGE) |
| --- | ---: | ---: |
| ROM bytes | 134,217,728 | 134,217,728 |
| FAT entries | 513 | 513 |
| Named NitroFS entries | 384 | 384 |
| ARM9 overlays | 129 | 129 |
| ARM7 overlays | 0 | 0 |
| Reconstructed ARM9 bytes | 1,122,040 | 1,122,040 |
| ARM9 V9.5 candidate literal references in target set | 67 | 67 |

ARM7 raw SHA-256 (both): `746355ed51b324933542a7c4fcf109a5f83755a97c95b834ffd08caf6d4fafea`.

ARM9 runtime SHA-256 differs between HG and SS, while all 67 V9.5 candidate literal-reference rows have the same addresses and values.

## Interesting V9.5 literal targets (per game)

- `0x021E16A0`: 64 candidate instruction sites.
- `0x021E16A4`: 1 candidate site.
- `0x021E16B0`: 2 candidate sites.
- Other exact target constants in the V9.5 target list: zero candidate sites.

These are **literal-value matches, not effective memory-access xrefs**. In particular, no exact literal match to `0x021E16A8` DOES NOT disprove V9.0/V9.3's already validated accesses to `0x021E16A8`. A program may load a different base and access it with an immediate offset.

Candidate literal load sites cluster in `0x020A` (36), `0x020D` (11), `0x020E` (18), and `0x0211` (2), with identical cluster counts for the two games.

Five FAT file sizes differ: IDs 1, 12, 60, 112 (overlay files) and ID 262 (`a/1/3/3`); **different size does not establish relevance** to Pokéwalker.

## V9.6 gate

`tools/v9_6/hgss_full_arm9_effective_xrefs.py` scans the whole reconstructed original ARM9 image for a verified A32 PC-relative literal load immediately followed by a direct access with signed displacement. It reports the **effective target** and checks all eight original V9.0 memory-access anchors instead of depending on raw target equality.

It remains syntactic only; it does not resolve incoming CFG edges, indirect branches, Thumb code, overlay instruction code, ABI ownership, or in-game networking. No ROM/save modification or thread creation is authorized from these findings.
