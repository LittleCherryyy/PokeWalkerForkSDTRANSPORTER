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
- `retail/cardenginei/arm7/source/walker_direct_bridge.c` prepares the
  durable 64 KiB EEPROM and CRC when the resident ARM9 requests checkout.
  Radio I/O is kept out of the ARM7 VBlank handler.
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

### Single user-facing acceptance test: send a Pokémon, not a diagnostic message

**The next DSi build offered to the user must attempt a REAL outbound
Pokémon transfer. A PING, fake packet, or 'menu opened' event is NOT a
successful milestone and is not worth a separate user-facing DSi test.**

With a backup and disposable HGSS save, the user opens the game's original
Pokéwalker menu, chooses to send a Pokémon and completes the existing SD
Transporter virtual IR exchange (no external Pokéwalker device). When the
virtual walker has changed and the EEPROM image has been committed to SD,
the resident bootstrap network backend must use the Android hotspot to
transmit a **real 65536-byte EEPROM image** using
`PWDSI001 / OP_PUSH_TO_PHONE`, including session identity and CRC32.
The Android `DirectSyncService.push` must validate `Native.walkable`,
bind the trainer, persist the walker in `WalkerStore`, and display that
Pokémon in the app. A successful network ACK is necessary but **not
sufficient**: confirm the Android stored the correct Pokémon before
declaring the test passed.

Preserve a local recovery copy and fail closed: if Wi-Fi/TCP or Android
storage validation fails, do not delete the .walker recovery copy,
claim the Pokémon reached Android, or clear the pending transfer. Do not
modify the game's .sav outside the game's existing save flow. The game
may already have saved the Pokémon as being on the local virtual
Pokéwalker before Android checkout succeeds: recovery must preserve
that .walker rather than falsely claiming the Pokémon remains in party.
Avoid a homebrew intermediary, desktop PC, separate file transfer, and
external internet access. Support phone hotspot as the only network.

Only after REAL outbound transfer succeeds, implement and validate
the return path: `OP_PULL_FROM_PHONE`, CRC/session validation, durable
console-side storage, original virtual-IR Pokéwalker return, and
`OP_CONFIRM_RETURN` after recovery-safe completion.

The Android half of the real payload flow is already present in
`core/android/app/src/main/java/io/github/sdtransporter/pokewalker/DirectSyncService.java`.
The DSi Wi-Fi radio/socket backend is **not** implemented/validated; do
not distribute a build presented as capable of this transfer until it is.

### Implementation progress — real checkout path (2026-11-22)

Source changes are committed to this branch, but there is **not yet
a deployable direct-to-phone DSi build**:

- `retail/pokewalker/walker.c` now marks a checkout STARTED only for
  original HGSS `CMD_WALK_START_INIT/CMD_WALK_START` and COMPLETE only
  after `CMD_CONNECT_COMPLETE`. Aborted sessions and returns clear
  incomplete checkout markers.
- `retail/common/include/walker_emu.h` appends the marker to the
  shared control structure without moving previous offsets.
- `retail/cardenginei/arm7/source/walker_direct_bridge.c` only offers
  an outgoing EEPROM after that COMPLETE marker and verified durable
  SD write, including the edge case of SD flush preceding the final
  IR message. The ARM7 VBlank coordinator no longer contains phantom
  socket callbacks. It must remain SD-only.
- `retail/transport/walker_push_stream.{h,c}` is a bounded nonblocking
  **real 65536-byte PUSH_TO_PHONE frame** serializer: sends the 88-byte
  PWDSI001 header, the entire committed EEPROM, and validates Android's
  session-bound OP_OK response. It fails on partial/invalid ACKs and
  detects EEPROM write-sequence changes. It is connected to the
  ARM9 post-card-read transaction coordinator; no verified resident
  DSi Wi-Fi backend or safe high-frequency execution site exists yet.
- Android `DirectSyncService.java` now refuses an uploaded EEPROM
  without a Pokémon. `WalkerStore.java` persists the original inbound
  checkout CRC so a retry after lost TCP ACK can be recognized without
  importing the Pokémon twice, even if Android has already added steps.
- Portable internal regression tests (no ROM/save) are in
  `core/tools/test_walker_push_stream.c` and
  `core/tools/DirectSyncWireContractTest.java`, with CI workflow
  `.github/workflows/directsync-wire.yml`. These validate framing
  logic, **not** console networking or game-save behavior.

### Resident ARM9 checkout integration (same work session)

- `retail/bootloaderi/source/arm7/walker_boot.c` now **clears** an old
  `ce9->walkerControl` pointer on boot and sets it, together with the ARM7
  pointer, only when the virtual IR hook is installed successfully. Previously
  the transport-side ARM9 cardengine field was not populated by the virtual
  walker install path.
- `retail/cardenginei/arm9/source/walker_direct_worker.c` now owns a
  guarded, bounded outbound transaction. It consumes the ARM7's verified
  `PUSH_READY` snapshot, opens a nonblocking connection to the phone via
  `WalkerDirectRadioOps`, sends the 88+65536 byte frame, waits for a
  correctly session-bound `OP_OK`, and marks `PHONE_OWNS` **only after**
  that ACK. It preserves the SD image on failures, rejects changed EEPROMs,
  avoids calls from the virtual-IR critical section and avoids stale pointers
  on reset. A radio backend **is required**; none is falsely enabled.
- `retail/cardenginei/arm9/source/cardengine.c` invokes one step of that
  worker only after the game finishes a card-read callback and its mode/IME
  checks pass. The NTR ARM9 Makefile includes the portable stream source.
  This site has not been validated as a sufficiently frequent scheduler
  during the HGSS Pokéwalker menu. Non-IRQ+IME checks are a minimum gate,
  **not** full runtime safety validation.
- `retail/common/include/walker_direct_radio.h` defines a strict backend
  contract: connect to the phone hotspot gateway's TCP port 30821, then
  bounded nonblocking reads/writes and close. The weak default deliberately
  returns NULL. No current Wii/DS/NitroWFC library pointer is assumed safe.

**Blocking issue remains:** Under the current resolver,
`walkerResolveHgssNet` does not resolve executable WCM/SOCL/SOC function
entrypoints or validate their ABI, and there is no independently verified
resident ARM7 Wi-Fi service behind the worker. Thus this is an integrated
*transfer coordinator*, NOT a runnable radio transfer. A later exact build
must regenerate `common/include/walker_payload.h` by executing
`python bootstrap/build_walker.py` with legacy devkitARM after changing
`pokewalker/walker.c`. Neither blob regeneration nor full bootstrap
linker/real-device validation was performed in this source-only session.
Do not copy the existing generated bootstrap onto the DSi expecting
network operation.

**Additional mandatory memory-safety gate:** The virtual Pokéwalker
ARM9 blob deliberately disables the game's MPU to access its reserved
EEPROM/control memory. Normal ARM9 card-read callbacks may not have access
to that same region with MPU enabled. The integrated worker now returns
without even dereferencing WalkerControl when the radio backend is absent.
Before enabling a real radio backend, validate normal-MPU accessibility,
cross-CPU cache coherency and, if necessary, create a safe bounded staging
path. Do NOT turn on the backend by guessing Wi-Fi API addresses.

### Persistent direct checkout fence implemented (2026-11-22)

A conservative, no-homebrew, non-duplicating **pre-send journal**
has been integrated into the modified DSi bootstrap, though it still
requires the real resident radio backend and full loader compilation:

1. `retail/arm9/include/walker_prepare.h` preallocates
   `<save>.walker.directlock`, **exactly one 512-byte sector**, for
   original DSi NTR HGSS on SD. The record begins in PREPARED state,
   and on subsequent launches its full length, CRC and state are checked.
   PENDING or corrupt records **refuse to launch virtual HGSS**.
   The original `.walker.lease` check is preserved. For DS Lite/B4DS
   the direct journal path is not used.
2. The launcher passes the preallocated FAT cluster to
   `bootloaderi/walker_boot.c` in `walkerPayloadOffset`, a loader field
   unused when `walkerPayloadSize==0` on NTR (B4DS payload semantics
   remain unchanged). The cardengine ARM7 C structure and its assembly
   storage both gain one **append-only** `walkerDirectLockCluster` field,
   with startup clearing stale state on unsuccessful IR hook installs.
3. The normal ARM7 VBlank flush now invokes
   `walker_direct_lock_writer.c` under the existing SD save mutex.
   It first checks the 512-byte PREPARED sector, writes a CRC-protected
   PENDING record with session ID, EEPROM CRC32 and write sequence,
   and reads back physically using the existing checked SD backend.
   Only then does it set `direct.lockReady`.
4. ARM9 can request this transition **only after a radio backend is
   available**, and the C TCP worker refuses to send a **single byte**
   until `lockReady` is true. ARM7's 64 KiB CRC scan is now likewise
   deferred until ARM9 requests real checkout, preventing needless
   EEPROM RAM accesses while offline.
5. Tests `core/tools/test_walker_direct_lock.c` and
   `test_walker_direct_lock_cpp.cpp` cover sector serialization,
   CRC validation, corruption rejection, disk round trip and C++
   launcher compatibility. These tests compiled and passed locally
   against a reconstructed copy of the same record-format functions
   with GCC/G++, **not** the devkitARM target build.

**Important:** This marker intentionally remains PENDING if the radio
fails or the console powers off, because Android may have received the
Pokémon before the TCP ACK was lost. There is **no safe automatic
rollback** until a verified phone-return / recovery path is built.
Do not test with an irreplaceable Pokémon. This new sidecar is separate
from the legacy `PWLEASE1` `.walker.lease` format; the NDS companion
does not automatically clear it. Future end-to-end return must remove
this blocker transactionally and only after the restored .walker is
verified.

**Still blocked:** safe resident ARM7 Wi-Fi driver, valid shared MPU
memory mapping, frequently called non-IRQ ARM9 worker, successful full
devkitARM build/link and actual hardware send/return. The desktop
format test proves neither console compatibility nor safe power-loss
behavior on FAT media.

### Host execution results (source-equivalent regression, no DSi)

A locally reconstructed, functionally identical copy of the transport C
implementation was compiled with `gcc -std=c99 -O2 -Wall -Wextra -Werror
-Wno-unused-function` and passed: 65,624 total frame bytes (88 header +
65,536 EEPROM), partial writes, CRC, session and trainer, invalid ACK
rejection, EEPROM mutation guard.

The Android `DirectSyncProtocol.read` code was compiled with host
`javac` and decoded the **exact 65,624 bytes produced by the C test**,
then its `write` implementation generated a real 88-byte OP_OK that the
C-side state machine accepted; a deliberately altered ACK was rejected.
This establishes a checked host wire-format match but does NOT validate
running an actual DSi build, the app's native EEPROM parsing, Android
storage behavior or any Wi-Fi activity inside HGSS.

The GitHub Actions workflow now runs this full C→Java→C exchange on the
actual checked-out repository sources. A successful CI run has **not**
been retrieved/confirmed in this session.

### Ownership and end-to-end wire safety (2026-11-22)

- `retail/pokewalker/walker.c` now rejects virtual-IR read/write
  operations after Android's session-bound `OP_OK` moved the runtime state
  to `PHONE_OWNS`. This prevents immediately returning the same Pokémon
  from the SD recovery EEPROM **in the same game session**.
- `core/tools/test_walker_push_stream.c` can emit the exact
  88+65536-byte frame generated by the native C sender, using partial
  TCP writes and a simulated Android ACK; Java
  `DirectSyncWireContractTest.java` reads and validates those **same
  bytes** with the shipping `DirectSyncProtocol.read` implementation.
  `.github/workflows/directsync-wire.yml` links both tests together.
  This is a synthetic byte-for-byte interoperability check; CI must
  report success before describing it as passed.
- **Existing reuse opportunity:** `retail/arm9/include/walker_prepare.h`
already refuses to launch HGSS when `<save>.walker.lease` exists.
The existing NDS companion `core/nds/source/lease.c` already writes a
`PWLEASE1` 64-byte lease and a `.walker.phone` recovery image. The
resident direct path must persist that compatible lease on SD before
making Android the owner, without launching the companion. The bootstrap
cardengine currently receives only `walkerCluster` and has no
lease-file cluster or verified creation path, so the persistent lock is
not yet available inside HGSS. Do not treat the in-memory guard above
as durable against reboot.

**Not yet crash-safe ownership:** `PHONE_OWNS` is only in RAM, and
  `walkerDirectBridgeReset` clears state at boot. After a DSi restart,
  the SD recovery image can again appear locally available despite the
  Android holding the Pokémon. A persistent, verified ownership lease
  (integrated into existing SD Transporter phone-lock policy) is REQUIRED
  before any non-disposable Pokémon test.
- **Not yet transactionally durable with the HGSS .sav:** A verified
  `.walker` flush is not proof that HGSS committed its *game save*.
  The bootstrap ARM7 save writer's apparent success does not by itself
  establish power-loss-safe ordering across the two files. The Android
  ACK must not be presented as proof of dual-file atomicity. Do not use
  an irreplaceable Pokémon/save while these problems remain.

### Radio backend research and implementation (2026-11-22)

- Checked the user-provided `wifi_v95_full_rom_index.json` overlay table:
  `OVY_0` (networking) = `0x021E5900..0x0221BA00`;
  `OVY_112` (Pokéwalker) = `0x021E5900..0x021FFCA0`.
  The shared address range means the game cannot use both overlays
  *unrelocated* at the same time. See
  `docs/research/hgss_ntr_wifi_overlay_conflict.md`.
- Added `retail/transport/walker_dswifi_radio.c`, containing an actual
  nonblocking POSIX/DSWifi TCP client to the Android hotspot's DHCP
  gateway, supporting connect/partial send/partial receive. It checks
  `Wifi_CheckInit` and `Wifi_AssocStatus`. Because the standalone DSi
  V6.x diagnostic observed a DSWifi `close()` hang, this first-pass
  backend retires after one connection and does not call close.
  **This is not an in-game driver yet.** It is excluded unless explicitly
  compiled with `WALKER_RESIDENT_DSWIFI_ARM7_VERIFIED`, and that macro
  MUST NOT be enabled until an actual resident, game-compatible DSWifi
  ARM7 service + FIFO/IRQ/timer ownership and memory mapping are
  implemented and verified. Calling `Wifi_InitDefault` by itself will
  not create the required ARM7 core in retail HGSS.
- The retail Makefile now automatically invokes
  `bootstrap/build_walker.py` before building the injected walker
  loader. Without regeneration, edits to `walker.c` would be lost
  because the loader uses a pre-generated binary header.

**Current result:** real outbound protocol framing, Android receiver,
ARM9 send coordinator, and an opt-in TCP socket adapter exist in
source. **No end-to-end DSi Wi-Fi transport has been compiled or tested.**
This is not a build for the console. The blocked component is
the wireless service coexisting with the retail game's ARM7 runtime,
not the basic TCP client code. Research sources:
- https://blocksds.skylyrac.net/dswifi/md_documentation_2library__design.html
- https://blocksds.skylyrac.net/dswifi/md_documentation_2internet__mode.html
- https://github.com/pret/pokeheartgold/blob/master/main.lsf

### CI milestone — actual ARM7/ARM9/IR/linker build passed (2026-11-22)

GitHub Actions [run 45085211191](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/actions/runs/45085211191),
commit `6b581b291eaeb12465c3fc2b3dc35d03e1eefff8`, completed **successfully**.
The pinned, legacy devkitARM/libnds toolchain rebuilt the freestanding
virtual-IR walker ARM9 payload, linked `cardenginei_arm7` (including
durable SD owner-lock writer), linked `cardenginei_arm9` (including
real 65,536-byte PUSH stream and guarded worker), compiled
`bootloaderi` and checked the native NTR binary outputs.
The exact C->Java->C byte-protocol test also passed on this branch.

To fit fixed memory boundaries without enlarging game-reserved WRAM:
- ARM7 cardengine compiled with `-Os`.
- ARM9 cardengine compiled with `-Oz`.
- `WalkerControl.directPushStream` lives in the separately reserved
  4 KiB virtual Pokéwalker control page rather than scarce cardengine
  ARM9 static memory; existing size assertions constrain the shared
  C layout to the original 0x800-byte supported subset.
- The **NTR** ARM9 C and assembly cardengine headers now both append
  `walkerControl` at the same offset; the earlier field had
  accidentally been added only to the TWLSDK header.

**This is a source/link build milestone, NOT a DSi ready-to-play
release.** The default `walkerDirectRadioBackend()` still resolves
to unavailable; the opt-in DSWifi TCP adapter is not compiled into
a runnable radio path without a verified ARM7 Wi-Fi service, NTR
game-mode FIFO/IRQ cooperation, safe normal-MPU visibility of the
walker and a reliable non-IRQ worker schedule. It therefore cannot
perform real in-game Pokémon checkout yet. No game save or phone
was used to validate this CI run.

**Before any DSi test:** implement and link a verified resident Wi-Fi
association/TCP backend for physical DSi DS-mode HGSS, identify a safe
regular non-IRQ ARM9 worker, wire its socket write/read to
`walkerPushStep` and to the bridge state machine, compile with the
proper devkitARM toolchain and verify linker memory limits. Also
verify that the console save and local walker file remain recoverable
across real transfers. A source-only or CI-pass result is not a
successful Pokémon transfer.

**Immediate blocker:** Identify a safe ARM7/ARM9 Wi-Fi backend that remains
available while HGSS executes in DS mode. The WCM/SOCL resolver and network
callbacks are not implemented/verified, so the phone cannot yet receive
in-game events. GDB static/CPU scheduling probes do not replace this gate.

Future work should be measured against this acceptance sequence rather than
issuing new emulator trace versions without direct relevance.

## Historical V7.1 research milestones (not user-facing transfer tests)

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
