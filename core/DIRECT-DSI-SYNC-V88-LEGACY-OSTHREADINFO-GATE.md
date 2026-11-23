# Virtual Pokéwalker V8.8 — test original HGSS NitroSDK 2.x legacy OSThreadInfo hypothesis

## User's V8.7 actual Nintendo DSi screenshot, November 22 2026

Inside the Goldenrod Pokémon Center, HeartGold running under the
experimental V8.7 Nightly bootstrap displayed:

| Exact RAM address | Raw 32-bit word |
| --- | --- |
| 0x021E16A0 | 0x00000000 |
| 0x021E16A4 | 0x021E1770 |
| 0x021E16A8 | 0x021E3864 |
| 0x021E16AC | 0x00000000 |

This was a successful exact-guarded, read-only diagnostic; it did not
invoke any NitroSDK thread function or enable Wi-Fi. V8.6 had
previously observed the same two middle words in Goldenrod and on
Route 35. The V8.3 flag at 0x021E1688 was 1 and its original three
ARM instructions + address literal matched the original ROM.

**Critical revision of the initial hypothesis:** Four values
coinciding with the `SDK_THREAD_INFINITY` layout at base
`0x021E16A0` do NOT prove that version or base. The published
NitroSDK header defines `SDK_THREAD_INFINITY` only if
`SDK_VERSION_MAJOR >= 3`. The public source build for original
HGSS selects **NitroSDK 2.0** via `mwrap_sdk = 2.0/sp1p2`.
The older, fixed thread-limit layout is therefore a stronger
hypothesis; it places the start of `OSThreadInfo` **four bytes earlier**
at `0x021E169C`.

Sources:
- https://github.com/pret/pokeheartgold/blob/master/meson.build
- https://github.com/ljtpetersen/ntrtwl-NitroSDK/blob/main/include/nitro/os/common/thread.h

## Two competing layouts; why legacy looks stronger

| Raw memory address | SDK 3.x Infinity at A0 | SDK 2.x legacy at 9C |
| --- | --- | --- |
| 0x021E169C | not part of this header | flags + max_entry |
| 0x021E16A0 | rescheduling + irqDepth | irqDepth + padding |
| 0x021E16A4 | current thread pointer | current thread pointer |
| 0x021E16A8 | thread list pointer | thread list pointer |
| 0x021E16AC | switch callback | switch callback |
| 0x021E16B0 | unrelated or nearby data | entry[0] pointer |

The pointer fields coincide at the same addresses because the
candidate **base address differs by four bytes**. Current and list
therefore cannot distinguish the two alternatives alone.

V8.4 additionally found two static ARM literals to `0x021E16B0`.
This is an interesting clue that `entry[0]` begins there in the
fixed-limit layout; the opcode usage has not yet been proved to
represent the `OSThreadInfo.entry` array.

The first word at `0x021E169C` could encode low 16-bit
`isNeedRescheduling` and high 16-bit `max_entry`. The latter is
not *necessarily* 16; it is a field maintained by the SDK and its
semantics must not be guessed from the array capacity. Neither a
positive `max_entry` nor a plausible `entry[0]` would by itself
prove safe memory capacity for another thread.

## V8.8 implementation (strictly read-only)

`walkerArm9LegacyThreadInfoWords(out[6])` calls the existing,
experimentally validated V8.7 `walkerArm9ThreadHeaderWords`:

1. Fails closed on B4DS, TWLSDK, NULL output, failed original
   V8.3 ARM opcode/literal validation or OS availability flag != 1.
2. Reuses V8.7's already known four fixed raw words, and verifies
   the user-observed current/list values are respectively
   `0x021E1770` and `0x021E3864`.
3. ONLY then reads two NEW, hard-coded, aligned addresses:
   `0x021E169C` and `0x021E16B0`.
4. The result is SIX raw 32-bit words in physical-address order,
   not dereferenced or interpreted by the runtime.
5. The Virtual Pokewalker in-game menu, **L**, displays:

```
V8.8 OS LAYOUT 2.X
9C:0x ????????
A0:0x 00000000
A4:0x 021E1770
A8:0x 021E3864
AC:0x 00000000
B0:0x ????????
Wi-Fi: NOT ENABLED
```

The known displayed values above are examples from the single V8.7
photo; they are not hard-coded as the output. A pointer-pair mismatch
correctly displays `OS gate FAILED`, rather than attempting any new
read. This experiment deliberately targets the previously observed
HGSS USA Rev0 session; it is not a universal scheduler introspector.

No read follows the pointers 0x021E1770 / 0x021E3864 or reads
the object at 0x021E16B0's value. No ROM/save/.walker content
changes, no IRQ hook, OS_CreateThread, WCM or SOC call.

## Hardware test, after full Actions build

1. Back up `sd:/_nds/nds-bootstrap-nightly.nds` and .sav/.walker.
2. Download the V8.8 **test-only** artifact, extract
   `nds-bootstrap.nds`, rename it `nds-bootstrap-nightly.nds`
   and replace ONLY the same nightly path on the DSi SD.
3. Run the same original USA Rev0 HeartGold under TWiLight Menu++
   Nightly. Open **Virtual Pokewalker -> L**.
4. Photograph all six raw values. If the OS gate fails, take the
   screenshot and do not bypass the check.
5. Return the photo; no Android APK update, hotspot or ROM patch.

## What the screenshot will and will not establish

A compatible high-half of 9C and plausible entry[0] B0 would
further support legacy NitroSDK 2.x. We still require compiled-code
ABI analysis to confirm `OSi_ThreadInfo` identity and the
`OSThread` field offsets/slot semantics. We must establish
bootstrap-owned long-lived memory and a non-IRQ, non-cardRead
scheduler dispatch point before calling any OS thread APIs.

Even after a scheduler structure is confirmed, Wi-Fi requires
independent ARM7 hardware/driver/IRQ coexistence proof in NTR HGSS
mode and a real, bounded no-save DSi-to-Android hotspot PING.

**V8.8 does not enable Wi-Fi or access Pokéwalker save data.**
