# V9.7 original ARM9 topology — observed results (2026-11-22)

Source: user-produced `wifi_v97_hgss_branch_topology.json` for the original USA Rev0 `IPKE` / `IPGE` ROM pair. These results contain **static A32 instruction candidates**, not a validated execution trace.

## Counts

| Metric | HeartGold | SoulSilver |
|---|---:|---:|
| Prior V9.0 anchors rechecked | 8 | 8 |
| V9.6 effective-access sites rechecked | 31 | 31 |
| Syntactic direct A32 B/BL candidates | 19,418 | 19,411 |
| Register-branch syntax candidates | 1,804 | 1,804 |
| BLX-immediate syntax candidates | 3,478 | 3,475 |
| Branch targets outside the reconstructed ARM9 image | 4,398 | 4,390 |

All 31 matching access signatures have identical **local branch-candidate metadata and prologue-candidate metadata**. Differences in global speculative A32 branch counts are expected because the ARM9 runtime hashes differ. The scanner examines aligned words irrespective of data/code distinction; no instruction reachability is proven.

## Priority candidate entry prologues

Three static accesses potentially write to RAM address `0x021E16A8`. V9.7 reports these **closest candidate** stack-saving prologues:

| Store PC | Original source LDR PC, base register | Candidate prologue PC | Syntactic direct BL callers |
|---|---|---|---:|
| `0x020D18A4` | `0x020D189C`, `r0` | `0x020D1808` | 2 |
| `0x020D2034` | `0x020D202C`, `r8` | `0x020D1FA0` | 8 |
| `0x020D20D4` | `0x020D20CC`, `r7` | `0x020D2058` | 6 |

Neither prologues nor true functions have been validated.

## Other interesting metadata

- `0x020D1F60` reads `0x021E16A8`; closest candidate entry `0x020D1F34` with **28** direct syntactic BL callers.
- `0x020D21D4` reads `0x021E16AC`; closest candidate entry `0x020D21C4` with **1** caller.

These are candidates near static references; they cannot establish correct scheduler ABI, thread ownership, runtime values, or in-game Wi-Fi.

## New probe

`tools/v9_8/hgss_cfg_register_origins.py` explores possible flow branches and abstract register-origin tags within the three bounded candidate-entry-to-source-LDR windows. Conditional instruction flags are not known: both predicate outcomes may be modeled. Unknown calls clobber tracked registers conservatively and unknown/indirect transfers stop exploration.

Important: a reachable candidate path is **not evidence that it executes at runtime**, and an unreachable candidate path does not disprove that the true function could be entered from outside the bounded interval.

Do not enable worker threads, ARM7 Wi-Fi IRQ ownership, game patches, save writes, or Pokéwalker transfers based on these static reports.
