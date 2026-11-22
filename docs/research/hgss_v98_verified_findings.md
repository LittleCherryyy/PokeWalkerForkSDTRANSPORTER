# V9.8 HGSS abstract CFG report — read-only findings (2026-11-22)

Source: user's `wifi_v98_hgss_cfg_origins.json` from original US Rev0 HeartGold and SoulSilver dumps. Both ROM reports agree across all three examined regions. **No runtime path, ABI contract or actual thread identity was proven.**

| Region | Candidate entry | Source LDR | Tracked register | V9.8 syntactic reachability | Reported origin |
|---|---|---|---|---|---|
| A | `0x020D1808` | `0x020D189C` | `r0` | false | none |
| B | `0x020D1FA0` | `0x020D202C` | `r8` | true | `call@0x020D1FB8` |
| C | `0x020D2058` | `0x020D20CC` | `r7` | true | `call@0x020D2070` |

The A result is a bounded model limitation, not evidence that the store at `0x020D18A4` is unreachable during the game. Eight modeled indirect-PC-load stopping events were reported, and incoming edges outside the candidate window were not exhaustively known.

## Important false-origin risk in V9.8

The V9.8 call model marks **all** registers unknown at every `BL`/`BLX` call. This intentionally conservative default masks origins of `r7` and `r8`, which *would* be preserved across calls under the usual ARM procedure-call convention. Nintendo's game-specific calling convention for these functions remains unverified.

Potential origin instructions *before* these artificial call barriers:
- B: `0x020D1FB4` reports a memory-load candidate for `r8`; then `0x020D1FB8` masks it
- C: `0x020D2060` reports an `r0`-origin move candidate to `r7`; then `0x020D2070` masks it

**Do not interpret `call@...` as genuine source-memory provenance.**

V9.8 is not a true complete CFG: it cannot resolve predicate flags, entry identity, incoming edges, Thumb, indirect control flow, memory snapshots, or NitroSDK ABI. It neither spawns workers nor enables Wi-Fi.

## V9.9 next step

`tools/v9_9/hgss_dual_abi_entry_audit.py` compares the historical unknown-call model with an explicit, hypothetical ARM callee-saved model under which `r7`/`r8` persist across calls. It also tests alternative V9.7 prologue candidates:
- A: `0x020D1690`
- B: `0x020D1F84`
- C: `0x020D1FA0`

These are **tests of assumptions**, not confirmations of actual execution. If the results implicate stable register origins, a separate ABI/runtime confirmation is necessary before touching ARM7 radio/IRQ ownership or deploying any Wi-Fi hooks.
