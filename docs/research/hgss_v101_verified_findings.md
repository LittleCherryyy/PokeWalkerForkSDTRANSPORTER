# HGSS V10.1 — conditional return and bypass findings (2026-11-22)

Evidence: user-produced `wifi_v101_hgss_boundaries.json` from original US Rev0
`IPKE` and `IPGE` ROMs, using the corrected V10.1 decoder.
The report confirms **equal** boundary metadata and focused literal values for
both games. These are decoded code syntax, not in-game executed paths.

## Correction to earlier interpretation

The V10.0 report of three "returns before stores" did not establish
that the store sites necessarily belong to unrelated functions.
**An unconditional return can be bypassed by a conditional direct branch;
a conditional return can fall through when its condition is false.**

| Region | Previously guessed entry | Return-like PC | Condition | Candidate bypass/fallthrough |
|---|---|---|---|---|
| A | `0x020D1808` | `0x020D1898`: BX LR | `NE` (condition code 1), **conditional** | falls through to `0x020D189C` if NE false |
| B | `0x020D1FA0` | `0x020D2018`: LDM loading PC | AL, unconditional | conditional B at `0x020D200C` jumps to `0x020D201C` |
| C | `0x020D2058` | `0x020D20AC`: LDM loading PC | AL, unconditional | conditional B at `0x020D209C` jumps to `0x020D20B0` |

A also has an earlier unconditional LDM-PC candidate at `0x020D1860`,
before the alternative entry `0x020D1868`. The latter receives **two
syntactic direct BL callers**: `0x020D1CB8`, `0x020D1D30`. An entry
therefore need not have the stack-save prologue that older scripts expected.

**Important:** These bypass edges do not prove execution, CPSR predicate
satisfaction, function entry ownership, or value provenance. The older
bounded CFG results for A that started at `0x020D1808` may still be
correct for *that entry* while missing a separately called region.

## Literal pool words resolved (identical for both games)

- PC-relative load at `0x020D1FA4` reads word `0x021E167C`
  from ROM literal address `0x020D2054`.
- At `0x020A3C9C`, source word from `0x020A3CC0` is `0x021D4888`.
- At `0x020A3CAC`, source word from `0x020A3CC4` is `0x021D47C8`.
- The `0x021E167C` base literal is repeated near A, B, C. Its presence
  confirms *encoded pointers*, not a live RAM value or real scheduler ABI.

## V10.2 next stage

`tools/v10_2/hgss_cfg_path_probes.py` adds a **bounded A32
path-witness analyzer** with unknown CPSR flags. It explores taken/untaken
conditional branches, stops on unconditional BX/LDM-PC/unknown PC
transfers and marks BL fallthrough as an explicit unproved assumption.
It compares paths from two A entries (`0x020D1808`, `0x020D1868`), plus
the B and C candidate entries, to both source and store sites.

Synthetic decoder tests pass. **No ROM-based V10.2 results yet.**
Do not patch HGSS, modify saves, start resident threads, or claim
Wi-Fi availability based on these static possibilities.
