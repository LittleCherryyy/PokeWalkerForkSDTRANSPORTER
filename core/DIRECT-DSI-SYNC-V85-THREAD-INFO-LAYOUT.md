# Pokéwalker Virtual V8.5 — original NitroSDK thread-info layout hypotheses

## Physical and offline evidence from V8.3 and V8.4

The user tested the V8.3 Nintendo DSi build with the original
HeartGold/SoulSilver. The exact ARM instruction guard around
`OS_IsThreadAvailable` passed and the raw word at
`0x021E1688` was `0x00000001`. That implies the original
NitroSDK `OS_IsThreadAvailable` call would report that its
thread system has been initialized and is available.

The user-provided V8.4 JSON contains the following cross-references,
identical in HG (IPKE) and SS (IPGE), including contextual SHA-256
matches for **all 101 syntactic ARM xrefs**:

| Referenced 32-bit address | Static ARM xrefs per original ROM |
| --- | ---: |
| 0x021E16A0 | 64 |
| 0x021E167C | 29 |
| 0x021E16B0 | 2 |
| 0x021E1688 | 1 |
| Other aligned addresses within +/-64 bytes | 5 |

The exact known `OS_IsThreadAvailable` instruction in ARM9 code
at `0x020D1AC4` is the **one** static reference to `0x021E1688`.
These are static code references, not observed live threads.

**Two strongest candidates:** `0x021E16A0` and `0x021E167C`.
Their *identity remains unproven*. We must never assume either is the
base of a thread struct merely because it is referenced many times.

## Technical reference: NitroSDK OS ThreadInfo variants

Public NitroSDK thread.h from
https://github.com/ljtpetersen/ntrtwl-NitroSDK/blob/main/include/nitro/os/common/thread.h
defines distinct layouts depending on `SDK_THREAD_INFINITY`.
Only the following offsets are used for offline comparison:

| Field | SDK_THREAD_INFINITY | Older fixed thread limit |
| --- | ---: | ---: |
| OSThreadInfo.current | +4 | +8 |
| OSThreadInfo.list | +8 | +12 |
| OSThreadInfo.switchCallback | +12 | +16 |

These offsets follow the header layout, but **the ROM's SDK variant,
the identity of either candidate, and the shape of a live thread
list have NOT been established**.

## V8.5 analysis

`tools/v8_5/hgss_thread_info_layout_audit.py` reads only the
user-owned original USA Rev0 NDS files:

1. Re-runs V8.4's exact original ROM identity, static ARM9
   reconstruction, V8.1 thread callsite/entry signature, and
   V8.3 4-word flag instruction guard.
2. Takes each V8.4 verified static ARM PC-literal xref to
   `0x021E16A0` or `0x021E167C`.
3. Inspects only its *immediately next* 32-bit ARM instruction.
   Records syntax-level unconditional, pre-index, no-writeback,
   immediate-offset, word/byte LDR/STR where base is precisely
   the register that received the literal pointer.
4. Records offset/access/width and compares matches between HG/SS.
   The scan does not follow instructions, dereference target pointers
   or equate a matching offset with a `OSThreadInfo` field.
5. Emits metadata only; no copyrighted ROM code, saves, or Pokéwalker
   data. No ARM game function is called and no Wi-Fi is enabled.

This approach may miss multi-instruction dataflow or Thumb routines.
Matches may come from data that resembles ARM instructions. False
positives remain possible, and the program labels every hypothesis
as unproven.

## Handoff test

Download the GitHub Actions
`Pokewalker-V8_5-Thread-Info-Layout-Windows` artifact and extract
while preserving all prerequisite `tools/v7_3` through `tools/v8_5`
directories that are present. Select original HG + SS USA Rev0 ROM
backups and drag both onto:

`tools/v8_5/COMPARAR_LAYOUT_THREADS.bat`

Return **only** `tools/v8_5/wifi_v85_hgss_thread_layout.json`.
If it errors, send the error text, **not** the ROMs.

No new bootstrap, SD files, Android APK, hotspot or physical DSi
test is necessary for this milestone.

## Next security gates

- Validate true runtime `OSi_ThreadInfo` base and its thread ABI,
  not just address/offset proximity.
- Establish the game-native scheduler context without calling from
  cardRead, VBlank or the IRQ-backed menu.
- Find dedicated, long-lived ARM9 thread object + private stack
  not overlapping game overlays, cache or memory manager.
- Verify ARM7 WCM and Wi-Fi IRQ ownership and legal radio operating
  mode when the NTR HGSS game is resident.
- Only afterwards attempt a bounded, opt-in, no-save DSi-to-Android
  PING; do not enable any Pokéwalker transfer until it passes.

The desired direct Android-hotspot bridge remains the project goal,
but **Wi-Fi is NOT ENABLED** in V8.5.
