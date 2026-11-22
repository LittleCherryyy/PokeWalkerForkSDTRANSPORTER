# Pokéwalker Virtual V9.0 — bounded static ARM9 scheduler instruction windows

## V8.9 user-supplied original ROM audit (2026-11-22)

The uploaded `wifi_v89_hgss_thread_field_xrefs.json` was inspected
directly. HeartGold (IPKE) and SoulSilver (IPGE), both original US
Rev0 backups, each contained:

- 101 static candidate ARM PC-literal cross-references
- 38 direct single-instruction accesses (37 former V8.5 word +
  **one new halfword** access)
- 38/38 matching source PCs, literal locations, access direction,
  width and calculated effective addresses between both ROMs
- zero title-only direct accesses

**New:** in both titles, original source LDR at
`0x02111908` loads literal from `0x02111A08` whose value is
`0x021E16A0`. The immediately following instruction at
`0x0211190C` is syntactically an unconditional ARM `LDRH`
reading `0x021E16A0` (16 bits).

This is consistent with a 16-bit status field near the suggested
scheduler state. The on-device V8.8 word there was
`0x00000000`. A static LDRH match alone does **not** prove a
real thread flag field or whether the instruction is executed in
the running game.

V8.9 did **not** find an immediate-next-instruction LDRH/STRH
at `0x021E169E`, where a `max_entry` u16 would be expected
if the old fixed-limit `OSThreadInfo` started at
`0x021E169C`. It cannot rule out access over multiple
instructions or through another base register. Combined with
the V8.8 live raw values (legacy candidate `max_entry=0`,
`entry[0]=0x1F`), the old layout at that specific base is
disfavored, not categorically disproven.

Original V8.8 DSi six-word snapshot:

| Address | Value |
| --- | --- |
| `0x021E169C` | `0x00000003` |
| `0x021E16A0` | `0x00000000` |
| `0x021E16A4` | `0x021E1770` |
| `0x021E16A8` | `0x021E3864` |
| `0x021E16AC` | `0x00000000` |
| `0x021E16B0` | `0x0000001F` |

The source build of pret/pokeheartgold uses NitroSDK 2.0, whereas
the public NitroSDK header normally selects `SDK_THREAD_INFINITY`
at version >=3. The observed data superficially resemble the
other variant, making it particularly important to identify actual
compiled-code semantics before assuming either C struct layout.

## V9.0 implementation

`tools/v9_0/hgss_arm9_thread_trace_windows.py` reconstructs
the original HGSS ARM9 and fully re-runs established exact SHA1/
scheduler ABI/source opcode/literal verification through V8.9.

Eight **fixed and verified** source sites are examined:

| Original ARM9 source | Candidate access |
| --- | --- |
| `0x02111908` | LDRH `0x021E16A0` |
| `0x020D16C0` | LDR `0x021E169C` |
| `0x020D18A0` | STR `0x021E16A8` |
| `0x020D2030` | STR `0x021E16A8` |
| `0x020D20D0` | STR `0x021E16A8` |
| `0x020D1F5C` | LDR `0x021E16A8` |
| `0x020A6878` | LDR `0x021E16A4` |
| `0x020D21D0` | LDR `0x021E16AC` |

For each reference it validates the exact original ARM PC-relative
literal and first immediately following memory access, then traces
at most **8 A32 words total** in a straight line (one source
instruction plus up to seven successors). Recognizes only a
narrow subset of AL unconditionals: LDR/STR/LDRH/STRH,
MOV register, ADD/SUB immediate and CMP/TST.
Stops on control-flow changes, conditional code, PC writes
or unknown instructions. It tracks a known literal-address
register only for syntactically safe operations.

The tool exports only derived metadata, instruction PCs, semantic
operation categories and bounded code-window SHA-256; never ROM
code bytes or opcodes. It does **not** execute original code or
access live game RAM, and false positives caused by data resembling
code remain possible. Cross-title matching does not establish
actual code execution.

## User test

After successful GitHub Actions host tests, extract
`Pokewalker-V9_0-ARM9-Scheduler-Windows-Offline` with its original
relative `tools/` directory structure. Drag the original USA
Rev0 `HeartGold.nds` and `SoulSilver.nds` backups onto

`tools/v9_0/COMPARAR_JANELAS_ARM9.bat`

Return ONLY `tools/v9_0/wifi_v90_hgss_scheduler_windows.json`.
Never share the user's original ROMs or save files.

Do not update the V8.8 nds-bootstrap or Android APK; no console
test or hotspot is required for V9.0.

## Remaining gates

- Identify true `OSi_ThreadInfo` field semantics from compiled
  code beyond simple syntactic xrefs; do not dereference the observed
  `0x021E1770` or `0x021E3864` pointer candidates.
- Prove an original `OSThread` ABI and independently-owned
  non-overlay, long-lived ARM9 thread object + stack.
- Prove non-IRQ thread dispatch without using `cardRead` hooks.
- Separately prove ARM7 Wi-Fi/IRQ ownership during NTR HGSS and
  DSi hotspot connectivity.
- Only after these gates, attempt opt-in bounded no-save Android
  bridge PING on the user's established TCP port 30821.

**The Wi-Fi radio and any Pokéwalker save transfer remain disabled.**
