# V7.1 — fail-closed network readiness diagnostics

This changes **only the modified nds-bootstrap source**. It is **not** a ROM patch, an Android release, or an SD-card test build.

## What changed

`walkerHgssNetMissingMask(const WalkerHgssNetApi *)` returns a 13-bit mask. A set bit means the named entry is absent. The resolver and ARM9 transport now share the same readiness requirements.

| Bit | Missing entry |
| --- | --- |
| 0 | wcmInit |
| 1 | wcmStartupAsync |
| 2 | wcmBeginSearchAsync |
| 3 | wcmConnectAsync |
| 4 | wcmGetPhase |
| 5 | wcmPointApList |
| 6 | soclStartup |
| 7 | socSocket |
| 8 | socConnect |
| 9 | socRecv |
| 10 | socSend |
| 11 | socClose |
| 12 | soclGatewayPtr |

If the pointer or magic is invalid, all 13 bits are set. The implementation does not change `WalkerHgssNetApi` layout or storage, and performs no Wi-Fi calls. This mask is **only an absence diagnostic**: a non-zero function address must additionally be proven to match the exact game's function and ABI; a zero mask alone is not proof of safe networking.

## Observed source baseline

The V18 resolver does not currently resolve callable WCM/SOCL/SOC function addresses. Even if the US gateway pointer is known, the resolver is expected to yield a non-zero mask. The ARM9 transport still refuses to call the network backend.

## Required before DSi test

1. Resolve exact binary version and actual WCM/SOCL/SOC entry points against verified disassembly and calling convention; avoid guesses.
2. Add a non-blocking, cancellable transport and strictly bounded timeouts.
3. Compile with devkitPro/nds-bootstrap toolchain, inspect warnings and binary integration.
4. Validate in-game PING/ACK to Android TCP 30821 on a disposable save, without enabling PUSH/PULL.
5. Test power interruption, connection loss, and SD durability before transfer.

Nothing here has been compiled or tested on physical DSi hardware as part of this change.

## 2026-11-22 continuation: source integration audit

The shared `WalkerControl` declaration was missing the `direct` and `hgssNet` members already referenced elsewhere. V7.1 appends those members *after* `linkMode` to preserve legacy offsets; it also adds a hard `sizeof(WalkerControl) <= 0x800` compile-time bound shared by the DS-mode and Slot-1 layouts.

The DSi NTR loader (`retail/bootloaderi/source/arm7/walker_boot.c`) now initializes the direct state and invokes the fail-closed network resolver *only after the IR hook is successfully installed*. Neither call opens Wi-Fi or touches a save.

The resolver no longer allocates an ARM stack array to perform unused heuristic BL-frequency analysis. It clears the output before validating arguments, restricts its existing US gateway *candidate* to IPKE/IPGE, and **does not resolve any callable networking function**.

### Host-only checks

Run `python3 tests/v71_host/run.py` from any directory with a host C compiler (`gcc`, `clang`, or `CC`). The test checks the 0x800-byte memory bound, legacy dirty offset, missing mask, invalid-input reset, and IPKE/IPGE title filtering. The added GitHub Actions workflow also requests these checks on changed sources. The actual workflow result is not yet confirmed.

### Still missing (do not distribute an SD test build)

- The correct in-game DSi ARM9 transport integration and validated ABI are unresolved. The source `retail/cardengine/arm9/source/walker_direct_transport.c` is located under a Makefile with `-DB4DS`, so its mere existence is not evidence of a DSi in-game transport.
- `walkerDirectBridgeTick()` and the ARM7 durability coordinator have not yet been demonstrated to be called by the live DSi code path.
- No real WCM/SOCL/SOC callable addresses, association, socket, PING/ACK or Pokémon transfer have been proven on console.
- The US gateway constant is research-only; a game-code check is not a build fingerprint. Never call it without validating the exact ARM9 binary/revision.

## 2026-11-22 continuation: actual DSi NTR ARM7 wiring

The DSi HGSS save path lives in `retail/cardenginei/arm7`. This is distinct
from the B4DS `retail/cardengine/arm9` proof-of-concept transport. Current
changes wire the existing Direct Sync coordinator **without enabling networking**:

1. In `bootloaderi/source/arm7/walker_boot.c`, initialize bridge state and
   resolve network metadata from the unhooked ARM9 image, then publish the
   control pointer only after installing the existing IR hook. The resolver
   scans within bounded decompressed DS main RAM, not a guessed region.
2. In `cardenginei/arm7/source/walker_file.c`, notify the bridge only
   after all dirty sectors are verified on SD and the write sequence remains
   unchanged; if writes race the flush, keep the newer sequence pending.
3. In `cardenginei/arm7/source/cardengine.c`, call
   `walkerDirectBridgeTick()` after `slot2EmuFlush(false)` on ARM7 VBlank.
   The current weak transport remains permanently unavailable and executes
   **zero** socket calls.
4. In `cardenginei/arm7/source/walker_direct_bridge.c`, compute the EEPROM
   CRC incrementally in blocks of up to 512 bytes per VBlank rather than
   scanning all 64 KiB in one interrupt. Abort the scan on changed sequence,
   dirty sector, or active game IR session. Do not replace a phone-owned
   session with a newer pending snapshot.
5. Source-wiring contract checks under `tests/v71_host/test_source_wiring.py`
   cover the order of resolver/hook, verified-flush gating, bounded CRC, and
   VBlank polling. They are static checks, not hardware proof.

### Next technical blocker

The ARM7 durability coordinator is now connected on the DSi path, but a safe
network worker remains **unimplemented**. A future backend must prove ARM9
NitroWiFi interfaces and ARM7 interrupt ownership, use authenticated/session
consistent framed packets, respect timeouts and VBlank latency, and retain
fail-closed operation until it has been compiled and tested on disposable
saves and real hardware.

Do **not** install this branch as an SD build, and do not interpret
`WALKER_DIRECT_PUSH_READY` as a real transfer. `PUSH_READY` only means a
stable on-SD image has been offered to an unavailable backend.

