# Resident Wi-Fi integration — release safety gate (2026-11-22)

## What is actually verified

At commit `3f01098`, the pinned legacy NTR source build, Android debug
receiver build and C-to-Java-to-C Direct Sync protocol tests completed
successfully in GitHub Actions. This is **build and synthetic-protocol
verification only**, not evidence of a real in-game Wi-Fi transfer.

The V105 emulator observations are documented in
[`research/hgss_v105_runtime_observations.md`](research/hgss_v105_runtime_observations.md).
The actual HGSS overlay collision and proposed game-managed post-exit
network path are documented in
[`research/hgss_ntr_wifi_overlay_conflict.md`](research/hgss_ntr_wifi_overlay_conflict.md)
and [`research/hgss_native_soc_after_walker.md`](research/hgss_native_soc_after_walker.md).
Do not restart the earlier GDB investigation merely because this gate
file originated on another branch.

The resident HGSS resolver deliberately keeps network function pointers
unresolved and `ready=0` until the exact binary revision, ABI and live
lifetime are proven. The real 65,536-byte outbound sender, Android
receiver, durable direct-lock and guarded post-exit overlay loader exist
in source; none proves that the game can establish a live connection.

## Blocking release conditions

1. Verify exact HGSS revision, original ARM9 main-thread post-Pokéwalker
   callback, overlay manager function address, and its 24-slot active
   table. Overlay 112 must be unloaded before loading network overlay 0;
   WFC setup overlay 13 overlaps menu overlay 74 and must not be called
   from that menu.
2. Verify game-native ARM7 Wi-Fi service ownership, WCM/SOC startup,
   live DHCP gateway, MPU mapping, cross-CPU cache visibility, and a
   bounded non-IRQ scheduler. Never enable verification macros simply
   to force a linker success.
3. Preserve the existing 64 KiB virtual EEPROM and original HGSS save
   path. Do not send a single byte before the durable direct lock is
   verified; retain the recovery image and pending state on error or
   lost ACK. A TCP ACK does not prove the game save and EEPROM were
   committed atomically.
4. Exercise deterministic fault injection, real in-game checkout to
   Android, recovery on interrupted transfers, and safe return using
   disposable Pokémon and backed-up saves before advertising a release.

## CI policy

- `pokewalker-ntr-build.yml`: native ARM7/ARM9/IR build and complete
  `nds-bootstrap.nds` link using the pinned legacy toolchain.
- `directsync-wire.yml`: native C stream, Java receiver framing,
  session-bound ACK, ownership lock, and mocked Nitro SOC/post-exit tests.
- `resident-wifi-host-tests.yml`: resolver, fail-closed gate, protocol
  and shared ABI tests.
- `experimental-bootstrap-build.yml`: manual smoke-check wrapper around
  the same NTR workflow; **no separately published unverified image**.

All relevant CI checks must be green before requesting a user DSi test.
Even green CI is insufficient to call the in-game wireless transfer
stable: the verified resident network backend and hardware acceptance
are still missing. Never use an irreplaceable Pokémon or save for an
experimental transfer.

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for implementation history.
