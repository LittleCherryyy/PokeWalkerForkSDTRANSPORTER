# Pokéwalker Virtual V8.6 — guarded original HGSS thread-alias raw-word probe

## Confirmed V8.5 results supplied by user (2026-11-22)

Original USA Rev0 HeartGold (IPKE) and SoulSilver (IPGE) matched in
**37 out of 37** direct one-instruction ARM pointer-offset accesses,
with no HG-only or SS-only patterns. Their earlier 101 original static
xref records per ROM also matched.

| Literal base candidate | Direct instruction uses | Breakdown |
| --- | ---: | --- |
| `0x021E16A0` | 24 | 20 word reads at offset +4, 4 word reads at +8 |
| `0x021E167C` | 13 | word reads at +0,+4,+8 (4x),+12,+32,+44,+48; 3 word stores at +44 |

The standout **proven arithmetic alias** is:

```
  0x021E16A0 + 0x08 = 0x021E16A8
  0x021E167C + 0x2C = 0x021E16A8
```

Thus code in two regions reads the same **absolute 32-bit word**,
and one of the source regions also writes that word. This does
not prove a particular runtime struct, a thread count, or the meaning
of the stored word. Nearby `0x021E16A4` has twenty direct static
load references via base `0x021E16A0 + 4`.

According to the public NitroSDK header:
https://github.com/ljtpetersen/ntrtwl-NitroSDK/blob/main/include/nitro/os/common/thread.h

`OSThreadInfo` has different offsets depending on
`SDK_THREAD_INFINITY`; in the newer layout, `current` is +4 and
`list` is +8, while the older fixed-limit layout puts them at +8
and +12 respectively. The matching offsets are a hypothesis only:
the **base of the game's real `OSThreadInfo` is not proven**.

## V8.6 implementation

The V8.3 diagnostic already proved by a DSi photograph:

- The original `OS_IsThreadAvailable` ARM entry at
  `0x020D1AC4` matches four exact code/literal words.
- The word at `0x021E1688` was `0x00000001` while the
  in-game menu was open, implying a positive original OS
  thread-initialization predicate.

The V8.6 `walkerArm9ThreadAliasWords(out)` routine:

1. Requires a valid output buffer and a supported NTR ARM9 build
   (fails closed for B4DS and TWLSDK).
2. Zeros both output words.
3. Invokes the already-guarded **read-only** V8.3
   `walkerArm9ThreadAvailabilityRaw` and requires its return value
   to be exactly `1`.
4. If and only if that validation passes, reads exactly one
   32-bit aligned word at `0x021E16A4` and one at
   `0x021E16A8`. Both are fixed NTR main-RAM addresses; they
   were located in the user's original US Rev0 static analyses.
5. The in-game menu displays raw hexadecimal values without
   treating either as an executable pointer. No additional
   dereference, IPC, thread creation, interrupts, or writes occur.

Open **Virtual Pokewalker -> L** to display
`V8.6 ARM9 THREAD RAM` with:

- `OS flag: 1` when the original guarded readiness probe succeeds
- `A0+4:0xXXXXXXXX`: raw RAM at `0x021E16A4`
- `A0+8:0xXXXXXXXX`: raw RAM at `0x021E16A8`
- `A0+8 = 7C+44` reminds us of the overlapping static accesses
- `Wi-Fi: NOT ENABLED` is mandatory and not changed by a sample

If the original code guard fails, no alias RAM is read, and the
screen displays a failure instead. If the OS readiness flag is not
one, the two-word snapshot remains unavailable.

The V7.9 ROM-read deferred dry-run diagnostics remain on **R**,
unchanged. The V8.3 L screen is extended/replaced by V8.6.

## Physical test

Only after the full GitHub Actions DSi cross-build succeeds:

1. Back up `sd:/_nds/nds-bootstrap-nightly.nds` and both `.sav`
   / `.walker` data. The test does not change saves.
2. Download the separate V8.6 artifact; extract the compiled
   `nds-bootstrap.nds`, rename to `nds-bootstrap-nightly.nds`
   and replace only that nightly binary on the DSi SD card.
3. Launch the same unmodified USA Rev0 HGSS ROM through
   TWiLight Menu++ Nightly.
4. Open `Virtual Pokewalker -> L`. Photograph the screen.
5. Resume normal gameplay, enter another map/route, reopen
   `Virtual Pokewalker -> L`, and photograph again.
6. Share both photos for a **read-only** interpretation. Do not
   send your ROM or save files. No Android APK or hotspot change.

The readings show the values while the in-game menu is active, not
a synchronized snapshot of a running standalone thread. A value
within NTR main RAM can be described only as a *plausible pointer*,
never dereferenced automatically. Even matching stable raw words
do not authorize any `OS_CreateThread`, `OS_WakeupThreadDirect`,
WCM or SOC calls. The ARM7 Wi-Fi radio/IRQ ownership remains unknown.

## Next gate

If the two words are plausible, establish the actual original
`OSThreadInfo` object and field semantics from compiled function
behavior, validate the memory allocation of an independent worker,
and identify a non-IRQ task creation point. Only then investigate
whether ARM7 can safely support a direct NTR-mode DSi-to-Android
hotspot association and bounded PING on TCP port 30821.

**V8.6 is not a functional network transport.**
