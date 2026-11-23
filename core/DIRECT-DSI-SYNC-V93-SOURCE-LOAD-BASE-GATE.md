# Virtual Pokéwalker V9.3 — source address-register origins for HGSS ARM9 scheduler candidates

## Evidence supplied by the user: V9.2 (2026-11-22)

The user's attached `wifi_v92_hgss_store_value_backtrace.json`
reported **four matching static register-writer patterns** in both
original HeartGold USA Rev0 (IPKE) and SoulSilver USA Rev0 (IPGE).
Each V9.1 original ROM instruction anchor and original runtime
ARM9 SHA-256 gate passed.

| Store to RAM | A32 STR PC and registers | Last local source-load instruction |
| --- | --- | --- |
| `0x021E16A8` | `0x020D18A4`, `STR r1,[r0,...]` | `0x020D189C`, `LDR r1,[r0,...]` |
| `0x021E16A8` | `0x020D2034`, `STR r1,[r0,...]` | `0x020D202C`, `LDR r1,[r8,...]` |
| `0x021E16A8` | `0x020D20D4`, `STR r1,[r0,...]` | `0x020D20CC`, `LDR r1,[r7,...]` |
| `0x021E16AC` | `0x020D21D8`, `STR r5,[r1,...]` | **Unresolved**: a branch at `0x020D21CC` stops backward analysis |

All four source/destination register observations are static
instruction semantics. The report did NOT read the original game's
runtime memory or show a live thread object. The source load base
registers `r0`, `r8`, `r7` are especially relevant: their
values at the time of the load remain UNKNOWN.

### Critical register-reuse hazard

For the first store, the original sequence includes:

- `0x020D189C`: source `LDR r1,[r0,...]` uses the earlier contents of `r0`;
- `0x020D18A0`: the V9.0 original literal `LDR r0,...` establishes the destination base;
- `0x020D18A4`: destination `STR r1,[r0,...]` writes to `0x021E16A8`.

It would be unsound to interpret the **destination** value of `r0`
as the **earlier source-load** address. V9.3 marks this difference
explicitly, verifying the exact V9.2 original source-load PC and
destination literal-source PC before constructing any report.

## V9.3 static offline implementation

`tools/v9_3/hgss_store_address_register_origins.py`
reconstructs the two original USA Rev0 ARM9 images through the
full already-tested V7.3 → V9.2 authenticity, compressed ARM9
reconstruction and instruction signature chain.

For the three specific `LDR r1` source instructions it:

1. Re-verifies that the source load is an unconditional,
   pre-index, no-writeback, immediate-offset original ARM
   **word load** with matching Rt/Rn.
2. Re-verifies the corresponding original store destination
   PC-relative literal load and its ordering *after* the source
   load but *before* the final store.
3. Inspects at most **16 preceding 32-bit A32 words** for a
   possible writer of the source base `r0`, `r8` or `r7`.
   The conservative V9.2 origin walker stops on conditional
   instructions, branches, LDM/STM, unknown operations and
   arbitrary control-flow ambiguity.
4. Classifies whether the source base could be a constant
   original ROM literal, a MOV register argument, an
   arithmetic expression, an unknown runtime memory load
   or an unresolved value. Static aligned NTR RAM addresses
   may be printed as numerical constants; **their contents
   are never read**.
5. Flags when the original source-base register is overwritten
   by the later store-destination literal instruction, preventing
   a false source/destination alias inference.
6. Preserves the fourth `0x021E16AC` store as unresolved at
   original branch PC `0x020D21CC`. No attempt to jump over it.

A syntactic producer 16 words earlier is NOT confirmed as an
executed path, a call argument or a live pointer. The tool
emits metadata JSON only, no copyrighted ROM instruction bytes,
no dynamic RAM value, save, `.walker` or Android state.

## Windows test when GitHub Actions host tests pass

Download the successful
`Pokewalker-V9_3-ARM9-Source-Address-Origins-Windows`
artifact. Extract all prerequisite Python packages with their
original `tools/` directory paths intact.

Select user's original `HeartGold.nds` and `SoulSilver.nds`
USA Rev0 backups; drag both onto:

`tools/v9_3/COMPARAR_BASES_LEITURAS_ARM9.bat`

Share only
`tools/v9_3/wifi_v93_hgss_source_load_base_origins.json`.
If the original opcode gate fails, send only the error text.

**No new DSi bootstrap, no SD card modifications, no Android APK
update and no hotspot usage required for this milestone.**

## Remaining invariants

- Never assume `0x021E16A0` is verified `OSi_ThreadInfo`,
  despite original V8.6/V8.7 live pointer-looking values.
- Never follow suspected live `OSThread` pointer candidates
  `0x021E1770` or `0x021E3864` without validated runtime
  object layout, bounds, and safety.
- Never call `OS_CreateThread`, `OS_WakeupThreadDirect` or
  ARM7 `WCM/SOC` APIs from a cardRead/IRQ menu context.
- Independently prove stable, bootstrap-owned ARM9 worker
  object and stack memory without game heap, overlay, original
  scheduler or card-read buffer overlap.
- Independently prove Wi-Fi radio and IRQ ownership for NTR
  mode original HGSS before bounded Android hotspot PING.

**Wi-Fi and Pokéwalker save transfer remain disabled.**
