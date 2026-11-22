# V7.1 — Resident HGSS transport: integration blockers

## What has been proven

The user successfully ran the standalone `PokeWalker_V71_HOTSPOT_PING.nds` on a Nintendo DSi with only the Android hotspot:
- DSi IPv4: `192.168.6.140`
- Android hotspot DHCP gateway: `192.168.6.192`
- PING success: 6; synthetic echo: 8192 bytes; attempts: 10; failures: 0
- Android service: TCP port `30821`; protocol `PWDSI001`

**This is not an in-game result.** That homebrew can initialize DSWiFi because it owns the running program. HeartGold/SoulSilver and nds-bootstrap have a different lifetime/interrupt/ARM7 arrangement.

## Source findings (checked against the current fork)

1. `common/include/walker_emu.h` currently defines `WalkerControl` without `direct` or `hgssNet` fields. The source-stage files `cardenginei/arm7/source/walker_direct_bridge.c` and `cardengine/arm9/source/walker_direct_transport.c` refer to these missing fields. No binary ABI can be assumed until the shared layout is reconciled across bootloader, ARM7 cardengine, ARM9 cardengine, and in-game menu.
2. `bootloaderi/source/arm7/walker_net_resolve.c` defines `walkerResolveNetworkApi`, but the reviewed `walker_boot.c` does not call it. Furthermore, `walker_hgss_net.c` leaves WCM/SOCL function pointers unset. The gateway BSS address alone cannot make the network API usable.
3. The DSi `cardenginei/arm9/Makefile` uses `source source_ext ../../common/source_general`, whereas the experimental `walker_direct_transport.c` is under the **other** `cardengine/arm9/source/` tree. Compiling an unrelated ARM9 variant does not install the DSi resident network transport.
4. The ARM7 bridge has weak placeholders returning unavailable; no functional native DSi transport backend is linked in its place.
5. `cardenginei/arm9_igm/source/inGameMenu.c` explicitly reports `Wi-Fi in game: NOT READY`. This UI state is accurate until resident transport is actually verified.

These are **static code findings**, not runtime claims; `tools/v7_1/resident_audit.py` reports key conditions for every GitHub Actions build.

## Next implementation order

- [ ] Reconcile the exact `WalkerControl` layout and guard all consumers at build time; preserve the 4 KiB reserved control page, alignment, ABI, and extant save semantics. Test offsets and layouts on the actual devkitARM toolchain.
- [ ] Establish a single DSi executable path linking real transport functions and invoking initialization from the actual bootstrap boot path (rather than a source file that is never called).
- [ ] Verify the WCM/SOCL/SOC API on the exact HGSS executable revision without guessing call targets; account for overlays/ARM/Thumb and ARM7 Wi-Fi ownership, callbacks and memory lifetime.
- [ ] Implement cancellable nonblocking socket PING/OP_OK only, reading Android hotspot IP automatically from DHCP/gateway, with timeout and cleanup that do not block VBlank or disrupt game networking.
- [ ] Build the complete nds-bootstrap + IR virtual walker tree and confirm no memory/ABI issues on a disposable HGSS save.
- [ ] Ask for DSi testing only once the in-game build truly contains the PING path, *not* merely a standalone homebrew test.
- [ ] Do not enable PUSH/PULL/CONFIRM until repeated PING and error recovery succeed and durable-save semantics are independently audited.

## Attribution

Derived from [Shinygati/SD-Transporter](https://github.com/Shinygati/SD-Transporter). Credit all original contributors and dependency authors. Preserve source headers, upstream licensing and existing widget functionality; see `ATTRIBUTION.md` and `CREDITS-UPSTREAM.md`.
