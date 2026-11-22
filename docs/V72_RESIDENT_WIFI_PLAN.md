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

## Real DSi V7.2.0 snapshot — 22 November 2026

The user's real DSi photo confirms the **ARM7 register snapshot page works**
and reports the following values while running HeartGold:

| ARM7 register | Observed raw value | Interpretation |
|---|---|---|
| `REG_IE` | `0x00050019` | Enabled IRQs: VBlank (bit 0), Timer 0 (3), Timer 1 (4), IPC sync (16), IPC receive FIFO (18) |
| `REG_IME` | `0x00000001` | Master IRQ enable is on |
| `TIMER0_CR` | `0x00C1` | Timer enabled, IRQ enabled, prescaler 1/64 |
| `TIMER1_CR` | `0x00C1` | Timer enabled, IRQ enabled, prescaler 1/64 |
| `TIMER2_CR` | `0x0000` | Disabled at instant of capture |
| `TIMER3_CR` | `0x0000` | Disabled at instant of capture |

No `IRQ_WIFI` (bit 24) is enabled in the captured `REG_IE`.
**This is only the pre-menu ARM7 snapshot**, not ARM9 state, handler ownership,
or an observation of every moment of gameplay.

`0xC1` is `TIMER_ENABLE (0x80) | TIMER_IRQ_REQ (0x40) | DIV_64 (0x01)`.
Both first ARM7 timers are occupied; do not reinitialize or stop them
to give the Wi-Fi stack a time source.

**Verified external interface requirements (2026):**
- DSWifi documents an ARM7 Wi-Fi timer `LIBNDS_DEFAULT_TIMER_WIFI`,
  DS-mode **DMA channel 3**, and an ARM9 Wi-Fi timer.
- libnds's timer documentation identifies **ARM9 timer 3** as DSWifi
  resource in its documented configuration. This must be independently
  audited for the actual version/toolchain integrated with nds-bootstrap.
- The library expects a matching ARM7 service, interrupt/handler
  registration, DMA and IPC; **calling `Wifi_InitDefault` from the
  current in-game menu is not safe** just because Timer 2/3 read zero.

Official technical references:
- https://blocksds.skylyrac.net/dswifi/index.html
- https://blocksds.skylyrac.net/dswifi/md_documentation_2internet__mode.html
- https://blocksds.skylyrac.net/libnds/interrupts_8h.html
- https://blocksds.skylyrac.net/libnds/timers_8h.html

### Reproducible offline decode

```bash
python3 tools/v7_2/analyze_irq_snapshot.py \
  --ie 0x00050019 --ime 0x01 \
  --timer0 0x00C1 --timer1 0x00C1 \
  --timer2 0x0000 --timer3 0x0000
```

Output lists enabled IRQ sources, each timer's flags, and the **still
unverified** conditions needed for Wi-Fi. The script never accesses
console hardware, user files, game memory, or the network.

### Next integration gate (no new .nds required yet)

Before implementing the first in-HGSS network PING:
1. Determine the specific *resident* ARM7 IRQ dispatch table mechanism
   and safely chain `IRQ_WIFI` without interrupting the game's existing
   VBlank/timer/IPC handlers.
2. Audit **ARM7 DMA3** and the chosen periodic Wi-Fi timer against the
   actual DS-mode cardengine. Do not assume idle means unowned.
3. Inspect **ARM9 timer 3** and choose a cooperative, bounded network
   polling context outside IRQ and VBlank.
4. Define explicit abort/rollback and save-isolation behavior. Only then
   link the already tested C PING state machine to the resident network
   callbacks in an experimental image.

**Hardware status:** Virtual IR transmission/return tested successfully;
diagnostics V7.2.0 read registers successfully; **no Wi-Fi PING within
HGSS has yet been demonstrated.**

### Static IRQ-dispatch audit of current cardengine

A review of `cardenginei/arm7/source/patcher/hook_arm7.c` found
that the existing retails' interrupt-table patch is specifically tailored
to **VBlank (slot 0)** and **IPC sync (slot 16)**:

- `hookNdsRetailArm7()` writes only `hookLocation[0]` and
  `hookLocation[16]`, chaining their previous handlers.
- The current bounds check covers **17 entries**, not the
  `IRQ_WIFI` handler slot **24**. Extending a raw write to slot 24
  without proving a larger writable table layout could corrupt RAM.
- A special runtime-table mode also patches only VBlank and IPC.
  It is not a generic `irqSet(IRQ_WIFI, ...)` dispatcher.
- `cardenginei/arm7/source/cardengine.c` resets DMA and timer
  registers during reboot/soft reset. A resident Wi-Fi driver will
  need an explicit shutdown and must not leave stale peripheral state.

**Decision:** The current design remains **NO-GO for radio initialization**
until IRQ_WIFI dispatch ownership is identified and a validated chaining
strategy exists, plus ARM7 DMA3/periodic timer and ARM9 timer/worker audits.
No automated change has been made to IRQ tables or timer controls.

This is a source-code finding, not a claim of Wi-Fi connectivity or a
conclusive runtime ownership map. The observed `REG_IE=0x00050019`
contains no IRQ_WIFI enable flag.

## V7.2.1 — ARM7 DMA3 and ARM9 resource view (read-only)

The real V7.2.0 photo already established that ARM7 timer 0/1 are active,
timer 2/3 were disabled at the capture instant, and IRQ_WIFI is not enabled.
The next conservative diagnostic deliberately **does not enable radio**.

On the **V7.2.1** in-game diagnostics page, press **X** for the existing
ARM7 IRQ/timer snapshot, then **Y** for the new resource page. The page shows:

- **ARM7 DMA3_CR, DMA3_SRC, DMA3_DST**, captured alongside the IRQ and
  timer values *before* the ARM7 menu enters its critical section.
- **ARM9 TIMER3, REG_IE and REG_IME**, sampled *after the menu has
  opened*. These are explicitly labeled **(menu)**; they are NOT
  evidence of what HeartGold ARM9 had configured during active gameplay.
- The DMA3 enable bit from the control register, with a warning that a
  disabled channel does not imply software ownership or future availability.
- `Wi-Fi: NOT ENABLED` and `No IRQ/DMA ownership proof`.

ARM7 serves a new **WPSD / WPSK** read-only IPC request using the same
bounded, retry-on-idle 90-frame pattern as the earlier diagnostic
messages. The ARM7 dispatcher preserves WPSK until ARM9 has read its
data. The code **never writes to DMA registers, IRQ tables, hardware timers
or the Wi-Fi device**.

**Next on-device test (after successful CI build):**

1. Back up your working V7.1.5 `nds-bootstrap-nightly.nds` and all
   expendable `.sav`, `.walker` and lease/phone state files.
2. Temporarily install the new V7.2.1 diagnostic Nightly binary.
3. Open HeartGold and open the nds-bootstrap Virtual Pokéwalker panel.
   Confirm the title shows `V7.2.1`; press **X**, then **Y**.
4. Photograph both the IRQ/timer panel and the new **DMA3/ARM9 AUDIT**
   panel, including all hexadecimal values.
5. Press **B** to return and confirm the game resumes. Do not attempt
   any Android transfer or touch important saves during diagnostics.

If `ARM7 DMA3_CR` has its enable bit set, this is an immediate reason
not to claim the DMA3 resource is safely reusable. If the bit is clear,
DMA3 is only **idle in that snapshot**; this still does not establish
whether DSWifi may take ownership. Similarly, a zero ARM9 TIMER3 while
the game is paused does not show it was idle during gameplay.

**Implementation gate after this:** inspect which runtime ARM7 IRQ table
contains slot 24 (`IRQ_WIFI`) and whether its handler can safely chain,
then evaluate DMA3 ownership and the ARM7/ARM9 timer service strategy
before any PING inside HGSS. No release or Wi-Fi claim is justified by
these snapshots alone.
