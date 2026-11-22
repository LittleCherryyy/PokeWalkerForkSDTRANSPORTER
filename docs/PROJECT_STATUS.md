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
