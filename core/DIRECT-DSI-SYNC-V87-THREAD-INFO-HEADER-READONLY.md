# Pokéwalker Virtual V8.7 — raw ARM9 ThreadInfo header audit (read-only)

## Real DSi V8.6 evidence — two physical areas (November 22, 2026)

The Nintendo DSi user supplied TWO V8.6 photos, one with the player
inside the Goldenrod City Pokémon Center and one on Route 35.
The on-screen bytes are identical in both snapshots:

| ROM diagnostic | Goldenrod Pokémon Center | Route 35 |
| --- | --- | --- |
| OS initialized flag | 1 | 1 |
| 0x021E16A4 (A0+4) | 0x021E1770 | 0x021E1770 |
| 0x021E16A8 (A0+8) | 0x021E3864 | 0x021E3864 |
| Wi-Fi | NOT ENABLED | NOT ENABLED |

These values are word-aligned and inside NTR main RAM, but merely
being stable and plausible pointers does NOT establish that they
really are OSThread pointers, safe to dereference, or bootstrap-owned
objects.

V8.5 original US Rev0 HG/SS offline analysis also confirmed 37
identical single-instruction RAM access patterns and especially:
- 20 direct `LDR` uses of `0x021E16A0+4 = 0x021E16A4`
- 4 direct `LDR` uses of `0x021E16A0+8 = 0x021E16A8`
- `0x021E167C+44` **aliases the same address** `0x021E16A8`,
  with one direct static load and three stores.

Original published NitroSDK header definitions:
https://github.com/ljtpetersen/ntrtwl-NitroSDK/blob/main/include/nitro/os/common/thread.h

`OSThreadInfo` has two layouts:
- `SDK_THREAD_INFINITY`: `current` at +4, `list` at +8,
  `switchCallback` at +12; first four bytes contain
  `isNeedRescheduling` and `irqDepth`.
- Older fixed-16-thread edition: `current` at +8, `list` at +12,
  `switchCallback` at +16; first bytes additionally contain
  `max_entry`, `irqDepth` and padding.

The observed two plausible pointer words at offsets +4 and +8
are therefore **consistent with the newer SDK layout**. The
identity of `0x021E16A0` as the actual original
`OSi_ThreadInfo` global and the value of `switchCallback`
still require evidence: never label them as confirmed fields.

## V8.7 implementation

`walkerArm9ThreadHeaderWords(out[4])` reuses the existing guarded
`walkerArm9ThreadAliasWords(pair)` which itself calls the exact V8.3
`walkerArm9ThreadAvailabilityRaw` sequence:

1. Validates the original `OS_IsThreadAvailable` instruction/literal
   signature at `0x020D1AC4` and its literal `0x021E1688`.
2. Requires the raw scheduler initialization flag to be exactly 1.
3. Samples the existing `+4` and `+8` raw words **once each**.
4. Reads exactly two ADDITIONAL, fixed, aligned NTR main-RAM words
   at `0x021E16A0` and `0x021E16AC`, forming a bounded 16-byte
   raw candidate header. No pointer chasing or thread-list traversal.
5. Returns only four raw hexadecimal values in the in-game menu;
   unsupported B4DS/TWLSDK builds, null output buffers or a mismatched
   original opcode guard fail closed. The original game and save are
   never written.

Open `Virtual Pokewalker -> L` to see:

```
V8.7 ARM9 OS HEADER
A0+0:0x XXXXXXXX
A0+4:0x XXXXXXXX
A0+8:0x XXXXXXXX
A0+C:0x XXXXXXXX
Wi-Fi: NOT ENABLED
```

The original V7.9 deferred ROM-read task diagnostic remains on `R`.
A zero at `+C` would be consistent with no thread-switch callback
registered, *not* proof of scheduler ownership.

## DSi test — only after full successful cross-build

1. Back up `sd:/_nds/nds-bootstrap-nightly.nds`, `.sav`,
   and `.walker` locally.
2. Extract the separately labeled V8.7 ZIP from successful GitHub
   Actions. Rename `nds-bootstrap.nds` to
   `nds-bootstrap-nightly.nds` and replace only that SD file.
3. Launch original USA Rev0 HeartGold through TWiLight Menu++
   Nightly, open Virtual Pokewalker -> **L**.
4. Photograph all four 32-bit values in the displayed header.
   Optionally move to another map and compare a second snapshot.
5. Share the screenshot(s), but not game ROMs, save files or
   Pokéwalker data. No Android update or hotspot required.

## Remaining gates

- Establish the actual original `OSi_ThreadInfo` identity from
  code behavior and identify the game-native `OSThread` layout.
- Identify a persistent, bootstrap-owned ARM9 `OSThread` and stack
  that does not overlap the original scheduler, overlays, ROM I/O,
  virtual walker IPC or game heap.
- Find a non-IRQ, non-`cardRead` context to create/dispatch a
  bounded independent worker, with safe shutdown.
- Independently establish ARM7 Wi-Fi/WCM ownership in HGSS NTR mode
  before attempting DSi hotspot association or a no-save PING.
- Keep save transfer fail-closed until end-to-end testing succeeds.

This is NOT a functional Wi-Fi transport. The original V8.6 values
are hypotheses about the game's scheduler, not permission to call
NitroSDK functions.
