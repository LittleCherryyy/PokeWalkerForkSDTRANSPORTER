# V7.2 — resident Wi-Fi bridge after HGSS virtual IR hardware validation

## Established baseline (22 November 2026)

The DSi tests showed the HGSS Pokéwalker hook being installed, and the original
game reported that Rocky (Onix Lv. 5) was sent successfully **after a retry**.
The user subsequently reported the local virtual Pokéwalker workflow is
working. Preserve the **working V7.1.5** installation and do not modify its
ROM, save, or Android APK for this milestone.

The Android app's existing **DirectSyncService** listens on TCP **30821**
and handles OP_PING (4) with a 88-byte OP_OK (0x80) response; the DSi V6.7
standalone homebrew already exercises this protocol. Neither observation
proves that a radio service can be safely started from inside a commercial
HGSS session under nds-bootstrap.

## V7.2 code that exists today

`core/bootstrap/retail/nettransport/walker_ping_engine.{h,c}` is a standalone
C11 PING-only packet/state-machine component. The engine:
- Generates a zero-payload 88-byte `PWDSI001` / version 1 / OP_PING frame.
- Accepts only the zero-payload OP_OK response with matching magic/version,
  zero flags, zero CRC, and zeroed session/trainer.
- Handles partial writes, partial reads, would-block, socket errors, a
  monotonic frame deadline, explicit cancel on menu exit, and 32-bit counter wrap.
- Performs **at most one I/O callback per step** (zero sleeps/spins), so an
  eventual adapter can call it from a cooperative ARM9 worker *outside IRQ*.
- Does **not** access SD, 64 KiB Walker EEPROM, game saves, sockets, or radio.
- Is **not wired to the V7.1.5 ARM7 bridge** yet. Both ARM CPUs receive
  cross-compile-only object checks; neither object is linked into the ROM or
  nds-bootstrap. The engine therefore cannot PING the phone until the next
  hardware-aware stage.

`tests/v72_host/test_ping.c` uses synthetic callbacks to check fragmented
I/O, would-block, reply validation, timeout, unsigned counter wrap, and
a one-I/O-call-per-step budget. Run using:

```sh
python3 tests/v72_host/run.py
```

CI: `.github/workflows/v72-ping-core.yml` executes the host and ARM7/ARM9
object cross-compilation. The checks do not require user files.

## Hardware integration acceptance gates

1. **Prove radio ownership and interrupt compatibility first.** DSWifi's
   `Wifi_InitDefault` requires matching ARM7 support and uses ARM7 Wi-Fi
   timers/interrupt services. The standalone DSi homebrew has these services;
   retail HGSS+nds-bootstrap does **not** automatically gain them.
   Calling `Wifi_InitDefault` inside the IGM or VBlank is unsafe without
   a resident ARM7 service designed around the game's existing timer, IPC,
   audio and file servicing.
2. **Prove a cooperative ARM9 execution context.** A worker must run outside
   VBlank/IRQ, with bounded memory/stack, cancellable startup and error
   handling, leaving HGSS's game state intact.
3. **Prove DS-mode hotspot association.** HGSS is a DS-mode program on DSi;
   a 2.4 GHz OPEN (or WEP) phone hotspot is needed for the classic DS
   Wi-Fi interface. WPA2 is not automatically available merely because
   the DSi console has WPA2 support in its system menu.
4. **Test only PING/OP_OK first**, no session/lease changes, EEPROM transfer,
   `PUSH` or `PULL`. Preserve the V7.1.5 binary and disposable saves.
5. Only after a reproducible in-HGSS PING and graceful radio shutdown
   consider wire transport of the durable Walker image and session/lease
   protocol. No hypothetical test should be presented as hardware proof.

## Compatibility note

The user's existing `DirectSyncService` may answer repeated PINGs on one TCP
session. V7.2 intentionally models **one PING exchange per engine instance**.
Persistent socket connection/close policy remains an adapter decision.
The earlier standalone DSi V6.7 diagnostic noted a blocking `close()`
behavior on its DSWifi build; do not import its blocking network calls into
an interrupt handler.

The adapter must translate a POSIX `recv()==0` (peer EOF) into an engine
error (negative callback return); a callback return of zero is **would-block**,
not a successful empty socket read. The adapter owns all socket cleanup.

## Cross-language compatibility check

`tests/v72_host/run_interop.py` compiles the standalone C engine and the
**actual** `core/android/app/src/main/java/io/github/sdtransporter/pokewalker/DirectSyncProtocol.java`
on a desktop JDK. The C engine emits its 88-byte OP_PING to a temporary
file; the real Android Java parser decodes that request and generates OP_OK;
the same C engine then receives/validates those exact Java response bytes.

Run `python3 tests/v72_host/run_interop.py` on a PC with a C compiler
and JDK 17+. All intermediate bytes are synthetic and temporary. This
proves agreement on wire format across C and Android Java, **not** real
network connection, Wi-Fi initialization, or an HGSS resident socket.

## V7.2.0 — first safe on-device radio-compatibility diagnostic

A separate read-only **ARM7 IRQ/timer snapshot** has been wired to the
in-game menu. It is intentionally *not* a DSWifi driver or network socket.

- The resident ARM7 `inGameMenu()` samples `REG_IE`, `REG_IME`,
  and four `TIMER_CR(i)` values **before its critical section disables
  interrupts**. No radio register, timer, IRQ mask or game memory is written.
- A second IPC command `WPRD`/`WPRK` returns these four packed values
  in the existing diagnostic reply region. The prior Walker `WPDG`/`WPDK`
  request is preserved, and the shared reply is held until ARM9 ACK.
- In Virtual Pokéwalker **V7.2.0**, press **X** to open the
  `V7.2 ARM7 IRQ/TIMER SNAPSHOT` page. Press **B** to return to the
  parent menu. The snapshot displays raw hex registers, no fabricated
  Wi-Fi ready/available assertion, and explicitly says Wi-Fi is disabled.
- This is only a *sample before the menu pauses the game*. A nonzero
  `REG_IE` bit does not identify the interrupt's owning function,
  and the timer values are not a full IRQ compatibility proof.
- Static host checks under `tests/v72_host/test_radio_snapshot.py`
  cover read-only wiring, timing of the capture and matching IPC IDs.

**Hardware test instructions (once GitHub CI publishes a tested binary):**
1. Preserve working `/_nds/nds-bootstrap-nightly.nds` and make copies
   of expendable `.sav`, `.walker` and auxiliary files.
2. Install only the V7.2.0 *test-only* Nightly diagnostic build,
   leaving Android APK and game ROM untouched.
3. Boot HGSS with a disposable save and confirm the existing IR virtual
   Pokéwalker behavior was not regressed. **Do not start a phone transfer.**
4. Open nds-bootstrap's Virtual Pokéwalker panel, confirm title V7.2.0,
   press X and photograph REG_IE, REG_IME and TIMER0..3 values.
5. Press B to return to menu and verify the game remains responsive.
6. If any crash, white screen or unusual save behavior occurs, restore
   the original V7.1.5 Nightly and test save backups.

This proves a safe diagnostics round-trip (if the hardware test succeeds),
**not** Wi-Fi enabled, a socket in HGSS or the eventual PING/ACK.
