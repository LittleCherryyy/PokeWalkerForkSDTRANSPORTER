# V7.1 — Resident HGSS transport: integration blockers

## What has been proven

The user successfully ran the standalone `PokeWalker_V71_HOTSPOT_PING.nds` on a Nintendo DSi with only the Android hotspot:
- DSi IPv4: `192.168.6.140`
- Android hotspot DHCP gateway: `192.168.6.192`
- PING success: 6; synthetic echo: 8192 bytes; attempts: 10; failures: 0
- Android service: TCP port `30821`; protocol `PWDSI001`

**This is not an in-game result.** That homebrew can initialize DSWiFi because it owns the running program. HeartGold/SoulSilver and nds-bootstrap have a different lifetime/interrupt/ARM7 arrangement.

## Source findings (checked against the current fork)

1. **Partially addressed in V7.1 branch:** `common/include/walker_emu.h` originally lacked `direct` / `hgssNet`, while the experimental transport code referenced both. Both structures are now appended after legacy fields, with compile-time assertions for old offsets and the 4 KiB control-page bound. Full multi-component link/runtime compatibility remains unproven.
2. **Partially addressed in V7.1 branch:** `bootloaderi/source/arm7/walker_boot.c` now initializes the dormant bridge and calls `walkerResolveNetworkApi` after installing the control block. `walker_hgss_net.c` still leaves WCM/SOCL entry points unset. The gateway BSS address alone cannot make the network API usable.
3. The DSi `cardenginei/arm9/Makefile` uses `source source_ext ../../common/source_general`, whereas the experimental `walker_direct_transport.c` is under the **other** `cardengine/arm9/source/` tree. Compiling an unrelated ARM9 variant does not install the DSi resident network transport.
4. The ARM7 bridge has weak placeholders returning unavailable; no functional native DSi transport backend is linked in its place.
5. `cardenginei/arm9_igm/source/inGameMenu.c` explicitly reports `Wi-Fi in game: NOT READY`. This UI state is accurate until resident transport is actually verified.

These are **static code findings**, not runtime claims; `tools/v7_1/resident_audit.py` reports key conditions for every GitHub Actions build.

## Next implementation order

- [x] Append and cross-compile the shared fields with old offsets and 4 KiB assertions (devkitARM); other build targets and console ABI behavior remain to be verified.
- [x] Invoke the dormant resolver during DSi bootstrap initialization (no radio calls).
- [ ] Link and call a **real** DSi ARM9/ARM7 transport backend through the actual game runtime; remove weak placeholders only after correct implementation.
- [ ] Verify the WCM/SOCL/SOC API on the exact HGSS executable revision without guessing call targets; account for overlays/ARM/Thumb and ARM7 Wi-Fi ownership, callbacks and memory lifetime.
- [ ] Implement cancellable nonblocking socket PING/OP_OK only, reading Android hotspot IP automatically from DHCP/gateway, with timeout and cleanup that do not block VBlank or disrupt game networking.
- [ ] Build the complete nds-bootstrap + IR virtual walker tree and confirm no memory/ABI issues on a disposable HGSS save.
- [ ] Ask for DSi testing only once the in-game build truly contains the PING path, *not* merely a standalone homebrew test.
- [ ] Do not enable PUSH/PULL/CONFIRM until repeated PING and error recovery succeed and durable-save semantics are independently audited.

## Attribution

Derived from [Shinygati/SD-Transporter](https://github.com/Shinygati/SD-Transporter). Credit all original contributors and dependency authors. Preserve source headers, upstream licensing and existing widget functionality; see `ATTRIBUTION.md` and `CREDITS-UPSTREAM.md`.

## Compilation and scope of this milestone

- `tools/v7_1/check_shared_layout.c` is compiled in CI with devkitARM; its tests ensure legacy offsets remain unchanged, the appended blocks are contiguous, and the control structure fits within 4 KiB.
- `.github/workflows/v71-bootstrap-build.yml` attempts compilation of the actual DSi bootloader source, to expose linker/build errors before any hardware test.
- No new `nds-bootstrap` production binary is promoted in this milestone. A successfully built **standalone** hotspot PING remains a separate executable.

### Full DSi bootloader build compatibility

The first devkitARM CI build of the full `bootloaderi` target stopped in legacy `source/arm7/main.arm7.c`, before it could validate the entire integration, with:
- `PM_READ_REGISTER` undeclared (line 564)
- `readFirmware` implicitly declared (line 996)

These are currently **unresolved toolchain/upstream compatibility errors** in the broader build. They do not establish that the appended V7.1 control layout is faulty, but the complete bootloader cannot yet be called build-verified. See the `V7.1 DSi bootstrap integration compile` workflow for exact logs. Do not mask these errors or publish the resulting binary as a testable in-game release.
