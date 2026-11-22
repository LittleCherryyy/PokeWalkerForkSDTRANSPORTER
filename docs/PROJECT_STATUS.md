# Project status — Nintendo DSi / Android

## Baseline

Project derived from [Shinygati/SD-Transporter](https://github.com/Shinygati/SD-Transporter). Retain the original GPL-3.0 license, contributor credits, and license notices for each separately licensed dependency.

## Experimental target

Use the game's original Pokéwalker interface in Pokémon HeartGold/SoulSilver on Nintendo DSi while an Android application implements a virtual Pokéwalker over a local Wi-Fi connection.

## Findings from locally provided source archives

- Android and DSi standalone networking diagnostics exist.
- Tests using a standalone DS/DSi homebrew program cannot prove that the same connection survives in-game.
- The local modified bootstrap has unresolved HGSS WCM/SOC/SOCL network function bindings and safety checks that avoid claiming they are usable.
- Actual bidirectional Pokémon transfer during game execution has not been validated on hardware.

## Primary goal: direct in-game DSi -> Android Pokéwalker sync (2026-11-22)

**No companion homebrew during transfers.** Keep the original SD Transporter
HGSS IR interception, virtual 64 KiB EEPROM and local SD recovery file. Replace
the *handoff* to a separate console companion program with an asynchronous
network backend inside the modified nds-bootstrap runtime. Android runs the
existing DirectSync receiver on TCP 30821, with the phone hotspot as the
only access point; no computer or outside internet required.

Source facts (not claims of runtime success):
- `retail/pokewalker/walker_stub.s` intercepts the game's IR read, write,
  and init calls; `walker.c` processes the virtual Pokéwalker protocol.
- `retail/cardenginei/arm7/source/walker_direct_bridge.c` models a durable
  64 KiB EEPROM push/pull and CRC flow, but its weak transport callbacks
  currently default to unavailable/no-op.
- `retail/common/source/walker_hgss_net.c` leaves Wi-Fi API function pointers
  unresolved, so `ready` is false; the existing
  `retail/cardengine/arm9/source/walker_direct_transport.c` is gated off
  in the B4DS build and has no runnable network calls.
- `android/DirectSyncProtocol.java` implements the PWDSI001 wire framing:
  an 88-byte header, optional 65536-byte walker payload and CRC32.
  Standalone DSi-to-Android ping is **not** in-game transport proof.

**Engineering decision:** Do NOT put blocking Wi-Fi/TCP calls directly in
`walker_stub.s` or `walker.c`. The stub temporarily disables IRQ/FIQ and
the MPU, so network operations there would risk breaking HGSS. Treat the
original .walker save as a rollback/journal rather than an intermediary
homebrew step. A resident, nonblocking transport must act only outside
the critical IR handler and preserve the original transfer protocol.

### One acceptance sequence (test only with disposable ROM/save)

1. With HGSS running on physical DSi, prove that entering its original
   Pokéwalker connection sequence advances a bootstrapped in-memory event.
   Event detection alone is not networking.
2. Prove an actual *in-game* PING/ACK from the persistent bootstrap runtime
   to Android TCP 30821 while HGSS remains active, with phone 2.4 GHz hotspot
   and no external application on the DSi.
3. After the original virtual-Pokéwalker send operation and verified SD
   commit, PUSH the 65536-byte image to Android and verify ACK + CRC32.
   If the network fails, keep the recoverable local image unchanged.
4. For return, PULL the Android image into a safe staging buffer; validate
   CRC and matching session/trainer, commit it durably, then let the existing
   HGSS virtual-IR protocol perform return. Only send CONFIRM_RETURN once
   the console-side state is durable; guard against duplicate transfers.
5. Confirm bidirectional transfers on disposable saves with airplane-mode
   interruption/retry and power-cycle recovery. No file moving, no
   `Pokewalker-NDS.nds`, no PC and no emulated Pokéwalker needed.

**Immediate blocker:** Identify a safe ARM7/ARM9 Wi-Fi backend that remains
available while HGSS executes in DS mode. The WCM/SOCL resolver and network
callbacks are not implemented/verified, so the phone cannot yet receive
in-game events. GDB static/CPU scheduling probes do not replace this gate.

Future work should be measured against this acceptance sequence rather than
issuing new emulator trace versions without direct relevance.

## Next milestone: V7.1

1. Identify safe networking function entry points and ABI for the target HGSS revision.
2. Implement nonblocking, cancellable communication or an equivalent safe transport.
3. Confirm PING/ACK to Android TCP port 30821 while gameplay is active.
4. Preserve upstream transfer behavior and existing Android widget functionality.
5. Prove recovery and data integrity using disposable saves before enabling transfers.

## Import safeguards

Keep original third-party headers and licenses. Exclude ROMs, game saves, firmware, downloaded binaries, personal paths, signing secrets, generated build folders and snapshot duplicates. Distinguish project-owned modifications from unmodified upstream source. Import remains incomplete until a reviewed source tree is committed.


## Parallel development track: Android Pokéwalker widget

The Android home-screen Pokéwalker widget is a core feature of this fork and predates the current DSi networking work. Its source code, layouts and skin assets have already been imported to `core/android/app/src/main/`; **their presence does not mean all visual defects have been fixed**.

Track ongoing work and acceptance criteria in [Widget issue #2](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/issues/2), including LCD/shell alignment across layouts, Premier Ball white appearance, transparent assets, touch targets, visual scaling and preserving original emulator behavior.

Keep widget enhancements and DSi/network changes separately reviewable where practical. Do not report a widget fix as complete without a built APK and a repeatable phone test. Credit Shinygati and every relevant original contributor, and preserve licenses and source notices.
