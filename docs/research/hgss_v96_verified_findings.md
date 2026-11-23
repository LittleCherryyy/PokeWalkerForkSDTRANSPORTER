# HGSS original ARM9 full-image effective-address audit — V9.6

Source: user-generated `wifi_v96_hgss_effective_xrefs.json`, read-only, for original USA Rev0 dumps. Analysis date: 2026-11-22. No ROM or save bytes included.

## Verified against provided output

- HeartGold IPKE ROM SHA-1: `4fcded0e2713dc03929845de631d0932ea2b5a37`.
- SoulSilver IPGE ROM SHA-1: `f8dc38ea20c17541a43b58c5e6d18c1732c7e582`.
- Reconstructed ARM9: **280,510** aligned words scanned per game.
- **4,056** syntactic ARM literal loads examined; **528** literal followed by modeled immediate memory access candidates per game.
- **31** modeled one-step accesses with an effective address in `0x021E169C..0x021E16B0` per game.
- Both games have 31 identical semantic access sites and matching original V9.0 anchor sets (8 anchors).

| Computed effective address | Sites per game |
|---|---:|
| `0x021E169C` | 1 |
| `0x021E16A0` | 1 |
| `0x021E16A4` | 20 |
| `0x021E16A8` | 8 |
| `0x021E16AC` | 1 |

The eight direct-next-access sites to `0x021E16A8` are:

| Access PC | Type | Loaded base | Offset |
|---|---|---|---:|
| `0x020A38C8` | load | `0x021E16A0` | +8 |
| `0x020A53A0` | load | `0x021E16A0` | +8 |
| `0x020A7648` | load | `0x021E16A0` | +8 |
| `0x020AB9C8` | load | `0x021E16A0` | +8 |
| `0x020D18A4` | store | `0x021E167C` | +44 |
| `0x020D1F60` | load | `0x021E167C` | +44 |
| `0x020D2034` | store | `0x021E167C` | +44 |
| `0x020D20D4` | store | `0x021E167C` | +44 |

## Interpretation boundaries

The V9.5 exact-literal count of zero for `0x021E16A8` was not a contradiction: V9.6 finds **effective** accesses using base literals and signed offsets. None of the 31 static sites is proof of executed paths, correct OSThreadInfo ABI, actual thread objects, resident stack safety, or IRQ/radio ownership. Matching PCs across games do not prove runtime behavior.

## Next research instrument

`tools/v9_7/hgss_arm9_branch_topology.py` (new) takes the same original dumps and uses the V9.6 verification chain to identify direct ARM A32 B/BL branch targets near these 31 sites and approximate stack-save prologues. Such branch edges/function entries are only **candidates**: no Thumb/indirect execution path coverage and no gameplay or save changes. The V9.7 script has not been run on user dumps yet.
