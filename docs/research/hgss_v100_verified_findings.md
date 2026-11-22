# HGSS V10.0 — Caller and ABI syntax analysis (2026-11-22)

Source: user-supplied `wifi_v100_hgss_callsite_abi.json` from both original USA Rev0 ROMs. Both variants match across all three analyzed regions. All findings are *static A32 candidates*, with no runtime execution or Nintendo ABI proof.

## Main observation: candidate return boundaries invalidate naive linear provenance

| Region | Previously selected candidate entry | Potential return before source | Source before store | Direct BL caller candidates to old entry |
| --- | --- | --- | --- | ---: |
| A | `0x020D1808` | `0x020D1898` (`BX LR`) | `0x020D189C` / store `0x020D18A4` | 2 |
| B | `0x020D1FA0` | `0x020D2018` (`LDM ... PC`) | `0x020D202C` / store `0x020D2034` | 8 |
| C | `0x020D2058` | `0x020D20AC` (`LDM ... PC`) | `0x020D20CC` / store `0x020D20D4` | 6 |

A candidate source after a return need not be in the same function as a nearby earlier prologue. A's `0x020D1898` is an especially clear syntax boundary: immediately preceding `0x020D189C`. The earlier V9.9 conclusions regarding `r8` origin at `0x020D1FB4` and `r7` origin at `0x020D2060` are **hypotheses that may cross unrelated function boundaries**. Do not claim true dataflow from these results.

## Confirmed decode candidates

- Region B candidate entry `0x020D1FA0`: stack-save includes `r4`, `r5`, `r6`, `r7`, `r8`, `lr`.
- Region C candidate entry `0x020D2058`: same register-save list.
- Original A32 instruction `0x020D1FB4` decodes as `LDR r8, [r0, #40]` (before the intervening return).
- Original A32 instruction `0x020D2060` decodes as `MOV r7, r0` (before the intervening return).
- At `0x020D1FA4` there is a PC-relative `r0` load with signed immediate displacement **+168**, whose literal word address is `0x020D2054`. The value of this word **is not in V10.0's JSON**.

The "nearest r0 writers" are scanned in local code windows; because of branches and calls, **proximity is not validated reaching-definition provenance**.

## V10.1 audit

`tools/v10_1/hgss_function_boundary_literals.py` now scans inbound syntactic A32 direct `B`/`BL` targets around the three source/store sites, enumerates return barriers, and resolves original PC-relative literal pool words for selected sites, including `0x020D1FA4`.

The first executed in-game Wi-Fi packet to Android remains unverified; do not modify the ROM, save or nds-bootstrap based on candidate boundaries, ABI guesses, or literal values.
