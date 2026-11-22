# V8.3 — bounded read-only OS_IsThreadAvailable global probe

## User-tested V8.2 offline ROM evidence

The original US Rev0 HeartGold and SoulSilver V8.2 JSON reports all
three ARM9 scheduler code signatures identical between versions.

The original `OS_IsThreadAvailable` entry at `0x020D1AC4`:

| Address | ARM instruction / content | Meaning |
| --- | --- | --- |
| 0x020D1AC4 | LDR r0, [pc, #4] | Load literal address at 0x020D1AD0 |
| 0x020D1AC8 | LDR r0, [r0] | Read exactly one word from that address |
| 0x020D1ACC | BX lr | Return the raw word |
| 0x020D1AD0 | 0x021E1688 | NTR main RAM data address |

The V8.2 report validated the literal reference, the r0-base offset
of zero, and BX LR stop; these four ARM instruction/literal words are
now checked exactly by the V8.3 hardware diagnostic before reading the
candidate game RAM address. This gives a *candidate raw return value*
from the function without calling any NitroSDK function.

The addresses 0xFDDB597D and 0x7BF9DD5B that the limited V8.2 linear
scan reported near `OS_CreateThread` are outside NTR main RAM and
must NOT be treated as safe scheduler-global pointers. There were no
literal matches within 40 bytes of `OS_WakeupThreadDirect`. The first
128 bytes of `OS_CreateThread` were insufficient to delimit its
entire function; the candidate r0 offsets -4 and 0 have unverified
semantics. Do not dereference them.

## V8.3 real DSi probe

In `core/bootstrap/retail/cardenginei/arm9_igm/source/walker_arm9_wifi_sig.c`,
`walkerArm9ThreadAvailabilityRaw(out)`:

1. Fails closed for NULL `out`, B4DS and TWLSDK.
2. Reads exactly four fixed, aligned NTR main RAM words starting at
   `0x020D1AC4`, comparing the ARM instruction stream and literal to
   four exact original HGSS USA Rev0 constants.
3. If a word differs, returns false without dereferencing any global.
4. If all match, checks the 32-bit-aligned address
   `0x021E1688` fits in ordinary NTR main RAM (0x02000000–0x023FFFFF).
5. Reads exactly one 32-bit raw word at that known fixed address and
   returns it to the ARM9 in-game menu without writing any RAM.

In the V8.3 in-game menu, open **Virtual Pokewalker -> R**.
The screen `V8.3 ARM9 THREAD FLAG` preserves the earlier V7.9
ROM-read, post-read and deferred-job-stage counters. Additionally:
- `OS raw:0xXXXXXXXX`: exact code guard passed; this is the
  observed word *while the in-game menu is paused*.
- `OS guard mismatch`: the game code does not match expected original
  HGSS USA Rev0; no arbitrary global was read.
- `Read only, not ABI proof`, `Wi-Fi: NOT ENABLED`: no OS thread
  was created, no radio initialised and no game/save data modified.

Even a raw word of `1` would only show that the original
`OS_IsThreadAvailable` implementation would return that value when
consulted at the time of the snapshot. It does **not** prove the
thread scheduler is safe to reuse, that a spare thread object or
stack exists, that a callback can run outside IRQ, or that ARM7
owns the Wi-Fi radio.

## DSi test (after successful GitHub Actions full build)

1. Back up `sd:/_nds/nds-bootstrap-nightly.nds`, `.sav` and
   `.walker` before switching anything.
2. Download the separate V8.3 experimental NTR bootstrap artifact,
   extract `nds-bootstrap.nds`, rename to
   `nds-bootstrap-nightly.nds` and replace that single SD file.
3. In TWiLight Menu++, select Nightly for the unmodified original
   US HeartGold or SoulSilver.
4. Open the game's in-game menu -> Virtual Pokewalker -> **R**.
   Photograph the `V8.3 ARM9 THREAD FLAG` view.
5. Return to gameplay, enter another map/location normally,
   reopen the same menu and photograph again.
6. Send the two photographs. A mismatch is a valid, fail-closed
   result: no attempts to bypass the check.

There are no changes required to Android, hotspot, .walker or any save.

## Next gate

Correlate the observed raw global value with the game state and,
if applicable, a verified NitroSDK thread scheduler implementation.
Any future worker must have dedicated persistent, non-overlay
memory for `OSThread` storage and its stack, its own safe lifetime
and callbacks, and non-IRQ dispatch. A simple ROM-read callback is
**not** an acceptable place for Wi-Fi initialisation.

ARM7 WM/Wi-Fi driver ownership in HGSS NTR mode remains unproven;
therefore the DSi-to-Android transport stays fail-closed.
