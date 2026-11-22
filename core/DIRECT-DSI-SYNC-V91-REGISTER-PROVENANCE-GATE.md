# Virtual Pokéwalker V9.1 — original ARM9 register-value provenance

## V9.0 result submitted by the user, 2026-11-22

The uploaded `wifi_v90_hgss_scheduler_windows.json` was directly
inspected. It reports the same eight original ARM9 source windows
in HeartGold USA Rev0 (IPKE) and SoulSilver USA Rev0 (IPGE). For
**all eight**, the original 32-byte code-context SHA-256 and the
conservative semantic steps match between titles.

Important observations:

| Static PC / candidate word | V9.0 syntactic sequence |
| --- | --- |
| `0x020D16C0` / `0x021E169C` | word load, `ADD #1`, store to same word, branch |
| `0x02111908` / `0x021E16A0` | `LDRH` of 16-bit word, `CMP #0`, conditional instruction |
| `0x020D18A0` / `0x021E16A8` | word store, branch |
| `0x020D2030` / `0x021E16A8` | word store, three additional unknown-origin memory operations, branch |
| `0x020D20D0` / `0x021E16A8` | word store, `MOV`, another store, branch |
| `0x020D1F5C` / `0x021E16A8` | word load, branch |
| `0x020A6878` / `0x021E16A4` | word load, unknown instruction |
| `0x020D21D0` / `0x021E16AC` | word load followed by store at same address, branch |

`0x021E169C` behaving as a word increment strengthens the
interpretation of a **counter** at this location. `0x021E16A0`
shows the structure of a tested control word. The original ROM
instructions were not executed by the analyzer; a load/ADD/store
sequence only supports a read-modify-write interpretation if
the same data register carries the loaded value into the addition
and store. V9.0 did not track that register provenance.

These are still static code-shape hypotheses, not verified
function symbols, thread layout or runtime scheduler ownership.

The prior physical V8.8 snapshot on DSi was:

```
021E169C = 00000003
021E16A0 = 00000000
021E16A4 = 021E1770
021E16A8 = 021E3864
021E16AC = 00000000
021E16B0 = 0000001F
```

That snapshot makes the legacy NitroSDK 2.x `OSThreadInfo`
hypothesis at `0x021E169C` difficult to reconcile with
`max_entry=0` and the purported `entry[0]=0x1F`. It does not
prove the alternative `SDK_THREAD_INFINITY` layout: the public
pret/pokeheartgold source still selects NitroSDK 2.0.

## What V9.1 adds

The new offline tool
`tools/v9_1/hgss_register_provenance.py` re-runs the exact
original US Rev0 ROM, ARM9 image, ABI and eight-source verification
chain through V9.0. It then analyzes **only the same eight
bounded source windows**, at most 8 A32 instructions each.

Instead of recording only an `LDR` or `STR` opcode category,
the conservative abstract interpreter tracks:

- registers containing a **known literal address**, without
  ever following the memory values loaded from that address;
- tagged unknown values read from known addresses;
- preservation of a tag through simple register `MOV`;
- a tag transformed by immediate `ADD/SUB`;
- whether `STR` reuses an earlier loaded value, optionally
  transformed, at the **same effective address**;
- whether `CMP #0` compares an unmodified loaded value.

It stops on conditional instructions, branches, writes to PC,
unsupported instruction shapes or end of the eight-instruction
window. Unknown-source loads can never create new known
RAM address registers. The report contains **only derived
operation names and addresses**, not ROM bytes/opcodes,
game data, or save contents.

A positive `read_modify_write_candidate` records syntactic
dataflow only. It does not claim execution, actual memory
ownership, a known numeric register value, or verified symbol
identity. A positive compare-to-zero pattern likewise does
not establish the flag's actual NitroSDK name.

### Windows test

Download the successful GitHub Actions artifact named
`Pokewalker-V9_1-ARM9-Register-Provenance-Windows`, extract
the `tools/v7_3` through `tools/v9_1` directories in
their original relative structure, and drag original USA Rev0
`HeartGold.nds` plus `SoulSilver.nds` to:

`tools/v9_1/COMPARAR_ORIGEM_REGISTRADORES.bat`

Return only `tools/v9_1/wifi_v91_hgss_register_provenance.json`.
If the script errors, send its text, never ROM files.

There is **no new DSi bootstrap or Android APK**. The V8.8
physical diagnostic may remain installed; no Wi-Fi/hotspot is
needed. The user should back up game saves normally, but
this script refuses output file extensions matching
`.nds`, `.sav`, `.dsv`, `.walker` and other known
save formats.

## Safety gates

The original runtime's `OSi_ThreadInfo`, `OSThread`
and scheduler/non-IRQ dispatch contexts remain unverified.
No bootstrap-owned long-lived stack/object has been shown
to coexist with original overlays and game heaps. ARM7
WCM/IRQ ownership for NTR HGSS remains unknown.

**Do not follow candidate thread pointers, call
OS_CreateThread/OS_WakeupThreadDirect, enable Wi-Fi or
transfer Pokéwalker save data from this static report.**

The eventual goal remains a direct DSi-to-Android hotspot
connection over the user's established TCP PING port 30821,
without a homebrew intermediary or game ROM patch.
