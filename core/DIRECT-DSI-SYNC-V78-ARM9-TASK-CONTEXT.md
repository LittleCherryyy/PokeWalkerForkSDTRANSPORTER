# V7.8 — ARM9 ROM-read execution-context audit (read-only, no Wi-Fi)

## Grounded result from the user's hardware (V7.7)

The real DSi reported the same five CRC32 fingerprints that the
original US Rev0 HeartGold and SoulSilver ROMs produce on PC.

| Function label | Live DSi CRC32 = offline PC CRC32 |
| --- | --- |
| WCM_Init | 3712DE4E |
| WCM_StartupAsync | 79EDF679 |
| WCM_GetPhase | E9FC4230 |
| SOC_Socket | BE74E80E |
| SOC_Connect | 56143021 |

All five also displayed PRO, meaning only an apparent ARM function
prologue. Together the evidence supports identical 32-byte code windows
present in ARM9 RAM while the game was paused. It does *not* prove
NitroWiFi API ABI, callable status, radio ownership, association state,
or actual direct DSi-to-Android transport.

## What is new in V7.8

The NTR ARM9 cardengine's existing cardRead() function has a tiny passive
counter. At entry (before the ROM implementation's own initialisation and
critical sections), it reads the CPSR mode and REG_IME.

- `ROM read calls`: count of cardRead() callbacks (saturates at UINT32_MAX).
- `Non-IRQ+IME`: count in ARM User (0x10), Supervisor (0x13), or
  System (0x1F) mode with REG_IME bit0 set.
- `Last CPSR mode` and `Last read IME`: latest observed context.
- `Pre-menu IE/IME`: still reports the menu entry, which may be in IRQ,
  and should **not** be interpreted as ordinary gameplay task context.

The existing WalkerArm9Snapshot is extended *at the end* with these four
fields and passed through the already-established ARM9 r3 pointer
handoff into the in-game menu. No new ARM7 IPC slots or persistent
game-memory blocks are introduced.

Open the nds-bootstrap menu -> Virtual Pokewalker -> **R** for
`V7.8 ARM9 ROM TASKS`, which reads those counters. The existing
V7.7 fingerprint view on **L** remains in place. The ARM7 heartbeat and
IRQ diagnostics are unchanged.

A positive Non-IRQ+IME count shows that a *ROM read callback* is
sometimes entered with non-IRQ CPU mode and enabled interrupts. It does
**not** establish a periodic idle worker, thread ownership, or a safe
place to call WCM/SOC functions; calls on ROM read path could deadlock
the game's own I/O. This milestone deliberately does not call them.

## Suggested hardware test after successful CI

1. Back up current `sd:/_nds/nds-bootstrap-nightly.nds`, game .sav,
   and .walker file; replace only nightly bootstrap with experimental V7.8.
2. Set TWiLight Menu++ bootstrap mode to Nightly and run HeartGold on DSi.
3. Enter game, visit a new area (a building or route) for normal ROM loads.
4. Open nds-bootstrap in-game menu -> Virtual Pokewalker -> **R**;
   photograph counters and last CPSR/IME. Back out.
5. Resume gameplay and trigger a different area load; revisit the R
   screen and photograph again. Send both photos.

Network stays **disabled**. The next gate is to find a suitable
non-IRQ, non-I/O-blocking ARM9 scheduler or thread and separately
validate ARM7 WM/Wi-Fi state ownership before any PING to Android.
