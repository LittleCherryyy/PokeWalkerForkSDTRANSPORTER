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

### Subsequent bootstrap compile finding (toolchain ABI)

After adding the missing `readFirmware` prototype, restoring the historical `PM_READ_REGISTER = 0x80` opcode, and correcting the explicit cast for `arm9destination`, the actual `walker_boot.c` and `walker_net_resolve.c` translation units were reached by the devkitARM build. The next failure was in `bootloaderi/source/arm7/libnds/codec.c`:

- Legacy `cdcReadReg(u8,u8)` conflicts with Calico's `cdcReadReg(CdcPage,unsigned)` declaration.
- Legacy `cdcWriteReg(u8,u8,u8)` returning `void` conflicts with Calico's `bool cdcWriteReg(CdcPage,unsigned,u8)`.

This **must not** be addressed by arbitrary casts or silencing warnings: the newer codec API has different semantics and ABI. Audit the legacy codec implementation and complete bootloader toolchain compatibility before shipping a modified nds-bootstrap binary to a console.

### Bootloader compatibility work following codec ABI mismatch

The experimental branch now preserves the old ARM7 peripheral access logic while avoiding incompatible declarations from modern Calico:
- Renamed only the local `bootloaderi` SPI codec implementation and its callers to `walkerLegacyCdcReadReg` / `walkerLegacyCdcWriteReg`.
- Renamed the local I²C implementation and callers to `walkerLegacyI2cReadRegister` / `walkerLegacyI2cWriteRegister`.
- Renamed the historical power-management SPI function/callers to `walkerLegacyWritePowerManagement`.
- Restored the documented ARM9 DSi `SCFG_RST` 16-bit register alias at `0x04004006` when the toolchain does not declare it.

All changes are confined to the non-main experimental branch and retain upstream authors' headers. They aim to preserve old behavior instead of silently adapting parameters to a different Calico ABI. **Compile success, console boot stability, and runtime correctness require separate verification; never infer HGSS Wi-Fi functionality from these fixes.**

### FAT API compatibility remains unresolved

The expanded devkitARM build now gets beyond the former legacy codec, I²C, SPI and `REG_SCFG_RST` errors. It next fails in `common/include_fat/my_disc_io.h` because modern installed SDK headers no longer provide the legacy `sec_t` type and therefore its `FN_MEDIUM_*SECTOR*` callback typedefs cannot be formed. This causes secondary "called object is not a function" errors from `common/include_fat/card.h`.

This is a storage-interface compatibility issue, **not** evidence of a broken Pokéwalker save. The correct solution requires examining the historical libnds/libfat API and selecting a matching, reproducible toolchain or carefully defining a compatible adapter with correct sector widths and callback ABIs. Do not invent disk function signatures, substitute new callbacks silently, or deploy an unverified bootstrap to real saves.

### Toolchain correction — historical SDK instead of modern Calico

The original `core/bootstrap/BUILD.md` **explicitly pins devkitARM r65 (GCC 14.2.0), libnds 1.8.3 and compatible libfat 1.1.5**. Modern Calico/devkitARM images caused misleading conflicts in unrelated legacy source. The V7.1 bootstrap CI has been switched to the published historical `devkitpro/devkitarm:20240918` image (r65-era); verify its actual installed package versions in build logs. All V7.1 experiment-only renames to ARM7 codec, I²C, power SPI, firmware and ARM9 reset were subsequently reverted to the upstream `main` source, preserving the intended old API and attribution. Preserve the rest of the V7.1 bridge layout changes.

Reproducing an actual full bootstrap/ndstool build must use the original portable rules and legacy libraries described in `core/bootstrap/BUILD.md`; a successful **isolated bootloaderi** build remains a necessary but not sufficient precondition for gameplay tests. The separate standalone hotspot diagnostic uses a different, modern SDK and remains independently tested.

## Verified historical bootloader build

With the historical `devkitpro/devkitarm:20240918` image and a statically linked host `lzss` tool built on Ubuntu, CI successfully compiled and linked `bootloaderi/loadi0.elf`, generated `loadi0.bin` and compressed `retail/nitrofiles/loadi0.lz77`. This proves the **isolated DSi loader** builds against the intended older SDK, not that Wi-Fi works during HGSS. The experiment-specific Calico-compatibility edits to unrelated peripheral sources were reverted.

The first attempt at the full `retail/bin/nds-bootstrap.nds` build failed when linking `cardengine/arm9` and `cardengine/arm9_32`: their output `.bss` sections exceed the fixed `vram` memory regions (linker reports addresses near `0x023DE0FC` / `0x023D80FC`). **Do not enlarge these hardware-reserved regions blindly.** A separate CI failure step collects object sizes/linker maps to identify the exact contributors and determine whether the overflow already exists in `main`. No full bootstrap artifact is currently verified or suitable for installation.
