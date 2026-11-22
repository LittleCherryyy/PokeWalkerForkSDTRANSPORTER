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
