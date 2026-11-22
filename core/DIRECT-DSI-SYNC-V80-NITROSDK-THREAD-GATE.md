# Pokéwalker Virtual V8.0 — NitroSDK thread scheduler research gate

## V7.9 actual DSi test — confirmed

Three photos were supplied by the user on November 22, 2026
(HeartGold using the experimental NTR Nightly bootstrap):

| Observation | ROM reads | Post+IME | Deferred one-shot stage |
| --- | --- | --- | --- |
| 1, before exiting menu | 0x00000413 | 0x00000413 | 0x00 |
| 2, following resumed gameplay | 0x000010C9 | 0x000010C9 | 0x02 |
| 3, after reaching Route 35 | 0x00002C42 | 0x00002C42 | 0x02 |

This is the expected successful queue-completion sequence in the
gameplay ROM-read callback. The fake job does not use the radio or read
the Pokéwalker save; it only changes a private ARM9 state variable
from 1 (queued) to 2 (done).

**Important limitation:** This is a bounded callback after ROM I/O,
not a resident independent ARM9 thread. It is not safe evidence for
running blocking or callback-heavy NitroWiFi socket operations.

## Source-level networking-thread evidence

The public US disassembly of HGSS contains the following original
NitroSDK thread call sites in its communications overlays:

| Network module | Assembly callsite | API name |
| --- | --- | --- |
| Overlay 13 (wireless/WCM) | 0x02226DD4 | OS_IsThreadAvailable |
| Overlay 13 (wireless/WCM) | 0x02226E00 | OS_CreateThread |
| Overlay 13 (wireless/WCM) | 0x02226E36 | OS_WakeupThreadDirect |
| Overlay 39 (NitroDWC/SOC) | 0x022299AC | OS_CreateThread |
| Overlay 39 (NitroDWC/SOC) | 0x022299B4 | OS_WakeupThreadDirect |

Public references:
- https://github.com/pret/pokeheartgold/blob/master/asm/overlay_13_thumb_2.s
- https://github.com/pret/pokeheartgold/blob/master/lib/NitroDWC/asm/overlay_39_arm.s
- https://github.com/ntrtwl/NitroWiFi

They show the game has networking-related code designed to use an
actual OS thread, rather than blocking at cartridge-read completion.
The V8.0 Windows tool independently confirms the listed branch opcodes
and their immediate targets from the **user's own original ROMs**.

## V8.0 validation

The tool verifies original US revision-0 HG/SS ROM SHA1 identities,
reconstructs the static ARM9 image with bounded BLZ parsing, validates
the five previously proven WCM/SOC callsites, verifies four local
neighboring ARM/Thumb opcode boundaries for five OS scheduler calls,
decodes their branches and fingerprints 32-byte windows of target code.

No code bytes are exported, no instruction executed, no game ROM
patched, and no .sav or .walker file opened. The output is JSON metadata.

A successful address match does not prove the ABI, ability to start an
OSThread in the overworld, available stack/priority/heap, safe preemption
from the cardengine, loaded overlay lifetime or ARM7 radio ownership.
Each of those must be verified before any physical network experiment.

## Follow-up engineering checklist

- [ ] Confirm exact OS_CreateThread / OS_WakeupThreadDirect immediate
      destinations for HG USA and SS USA and whether a branch veneer is
      present.
- [ ] Validate OS scheduler runtime state and execution context without
      calling thread APIs from IRQ or from cardRead.
- [ ] Establish a bounded, opt-in worker with dedicated stack and clean
      teardown; do not patch or hijack the game's existing threads.
- [ ] Verify ARM7 WM and Wi-Fi driver radio/IRQ ownership, including how
      DS NTR mode and Android hotspot interoperability can be supported.
- [ ] Only after these gates, attempt a no-save one-frame-budgeted
      DSi-to-Android PING against the Android host on port 30821.
- [ ] Keep the save transfer bridge fail-closed until actual successful
      end-to-end testing in HGSS.

Current project status: ARM9 callback dry-run succeeded, offline
scheduler-ABI audit ready for user test; **Wi-Fi remains NOT ENABLED**.
