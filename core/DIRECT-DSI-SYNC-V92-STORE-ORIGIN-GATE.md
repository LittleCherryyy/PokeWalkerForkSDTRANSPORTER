# Virtual Pokéwalker V9.2 — original HGSS ARM9 store-value origin backtrace

## User result: V9.1, original HeartGold and SoulSilver USA Rev0

User-provided `wifi_v91_hgss_register_provenance.json`, inspected on
November 22, 2026, contains eight original bounded ARM9 provenance
windows for each title. Every semantic sequence matched between
HeartGold (`IPKE`) and SoulSilver (`IPGE`) exactly.

### Verified syntactic dataflow

| Address | Original ARM9 PCs | Offline result | Meaning still unknown |
| --- | --- | --- | --- |
| `0x021E169C` | `0x020D16C4`, `16C8`, `16CC` | 32-bit read → original value plus one → **same-word store** | Likely counter, not proven live function |
| `0x021E16A0` | `0x0211190C`, `11910` | 16-bit `LDRH` → **same loaded value compared with zero** | Candidate control flag, not proven SDK symbol |
| `0x021E16A8` | `0x020D18A4`, `2034`, `20D4` | Three separate original code locations contain stores | Stored value register origins unproven |
| `0x021E16AC` | `0x020D21D4`, `21D8` | 32-bit read followed by store to same word | The stored value did NOT have a proven earlier tagged origin |
| `0x021E16A4` | `0x020A687C` | 32-bit read, next opcode unsupported | Candidate current-thread pointer identity unproven |

The V8.8 actual DSi screenshot remains:

```
  RAM 0x021E169C = 0x00000003
  RAM 0x021E16A0 = 0x00000000
  RAM 0x021E16A4 = 0x021E1770
  RAM 0x021E16A8 = 0x021E3864
  RAM 0x021E16AC = 0x00000000
  RAM 0x021E16B0 = 0x0000001F
```

A word that is genuinely incremented by source-code dataflow at
`0x021E169C` is especially hard to reconcile with an `OSThreadInfo`
legacy fixed-array layout whose header and max-entry would occupy
that same word. This is stronger evidence **against that one
specific offset/layout**, not proof of the alternative base or
the game's ABI.

## New, strictly offline V9.2 work

`tools/v9_2/hgss_store_value_backtrace.py` uses the complete
original-ROM identity, decompressed ARM9 SHA-256 and V9.1 exact
instruction guards. For four known original ARM9 32-bit STRs,
it scans at most 12 preceding instruction words without jumping:

- `0x020D18A4` writes to `0x021E16A8`
- `0x020D2034` writes to `0x021E16A8`
- `0x020D20D4` writes to `0x021E16A8`
- `0x020D21D8` writes to `0x021E16AC`

The tool identifies the explicit store value register (Rt) and
attempts to find a nearby syntactic register writer. Recognized
writers include unconditional `MOV` immediate, PC-relative
literal load, `MOV` register, immediate `ADD/SUB`, and
bounded `LDR` word/halfword. It may follow up to three
simple register-copy/arithmetic links, **only backwards within
the same 12-instruction window**.

Unconditional branches, conditional instructions, unsupported
instructions, LDM/STM, PC writes and software interrupt boundaries
STOP analysis. Actual RAM-loaded values are opaque; the code
never dereferences `0x021E1770`, `0x021E3864`, or any unknown
pointer. Arbitrary original ROM literals are classified, not
exported as game code.

A nearest local writer on a contiguous static instruction layout
is not proof of an executed control-flow path; users must not
use the JSON to authorize OS_CreateThread, OS_WakeupThreadDirect,
WCM/SOC radio APIs, game save access, or runtime memory writes.

### Windows procedure

Download the success-tested `Pokewalker-V9_2-ARM9-Store-Origins-Windows`
artifact, keeping all prerequisite `tools/v7_3` through
`tools/v9_2` paths. Select original HeartGold + SoulSilver
USA Rev0 backups and drag both onto

`tools/v9_2/COMPARAR_ESCRITAS_ARM9.bat`.

Return only
`tools/v9_2/wifi_v92_hgss_store_value_backtrace.json`.
The tool rejects saving to ROM or game-save extensions. Do not
upload original ROMs or save files.

**No DSi, nds-bootstrap, SD card, Android APK or hotspot change.**

## Remaining physical/network gates

- Confirm genuine `OSi_ThreadInfo` address, source ABI and safe
  schedule-entry semantics for the original SDK code.
- Prove a dedicated, bootstrap-owned `OSThread` object/stack
  outside overwritten overlays, the original game heaps and
  card-read resident memory.
- Prove non-IRQ/non-`cardRead` execution and clean shutdown.
- Independently prove ARM7 WCM/IRQ and radio ownership under
  the original NTR-mode HGSS game.
- Only then attempt opt-in bounded Android-hotspot PING at
  the user's previously working Android TCP port 30821.

**Wi-Fi and Pokéwalker save-transfer remain OFF in V9.2.**
