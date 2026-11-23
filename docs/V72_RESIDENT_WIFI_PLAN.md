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

## Real V7.2.1 DMA3 / ARM9 audit photo — 22 November 2026

The user confirmed the DMA3/ARM9 read-only panel works on a real DSi
running HeartGold. Photographed values (literal hardware readings):

| Register / view | Observed |
| --- | --- |
| ARM7 DMA3_CR | `0x00000000` |
| ARM7 DMA3_SRC | `0x00000000` |
| ARM7 DMA3_DST | `0x00000000` |
| ARM9 TIMER3 (menu) | `0x00C1` |
| ARM9 REG_IE (menu) | `0x00050049` |
| ARM9 REG_IME (menu) | `0x00` |

**ARM7 DMA3** was inactive at the pre-menu snapshot, but this does not
establish exclusive or future DMA3 ownership. No DMA reconfiguration is
authorized by this result.

**ARM9 TIMER3** was still configured with timer enable + IRQ + divider
64, even though the in-game menu had disabled the ARM9 interrupt master.
The ARM9 NTR cardengine source explicitly starts its menu wrapper with
`int oldIME = enterCriticalSection();`, *before* invoking the separate
IGM display function. This directly explains the observed
`ARM9 REG_IME=0`. The actual gameplay IME value was not captured.
`REG_IE=0x00050049` has enabled mask bits: VBlank (0), timer 0 (3),
timer 3 (6), IPC sync (16), and IPC receive FIFO (18).

**Critical default DSWifi gate:** the libnds documentation for DSWifi
identifies ARM9 timer 3 as a Wi-Fi resource; the currently observed
TIMER3_CR=0x00C1 prevents us from treating a default DSWifi startup as
safe. We cannot determine from this snapshot which code owns TIMER3,
or whether it is used for a game timer or some other service. Do not
overwrite this timer, call `Wifi_InitDefault()` in the menu, or add an
`IRQ_WIFI` hook without a verified IRQ dispatch/ownership plan.

Relevant source:
- `core/bootstrap/retail/cardenginei/arm9/source/cardengine.c`:
  `inGameMenu(s32* exRegisters)` begins with `enterCriticalSection()`
- `core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c`:
  reads ARM9 timer/IE/IME after entering IGM
- `core/bootstrap/retail/cardenginei/arm7/source/inGameMenu.c`:
  reads DMA3 state before the ARM7 menu pauses the game
- https://blocksds.skylyrac.net/libnds/timers_8h.html
- https://blocksds.skylyrac.net/dswifi/index.html

### Offline hardware readiness audit

```bash
python3 tools/v7_2/analyze_arm9_dma_snapshot.py \
    --dma-cr 0 --dma-src 0 --dma-dst 0 \
    --arm9-timer3 0x00C1 --arm9-ie 0x00050049 --arm9-ime 0
```

This command only prints a JSON interpretation of the six provided
register values. Test fixture `tests/v72_host/test_arm9_dma_audit.py`
asserts TIMER3 is configured active, that the visible IRQ mask decodes
correctly, and that **wifi_resident_ready is false** even if DMA3 is idle.

### Recommended next engineering gate

Capture the **ARM9 TIMER3 + REG_IE/REG_IME before** its cardengine
`inGameMenu()` wrapper calls `enterCriticalSection()`, using a proven
safe handoff to the IGM (do not repurpose existing shared mailbox slots
that the loader/Gen5 features use). The baseline screenshot was taken
after menu pause, so gameplay ownership remains unverified.

Only after tracing which code owns timer 3 and whether the chosen
DSWifi version can use an alternate explicitly negotiated timer should
we contemplate radio initialization. This V7.2.1 diagnostic does not
require a new APK or another hardware test at present.

## V7.2.2 — snapshot ARM9 anterior ao wrapper do menu

A foto real do DSi na V7.2.1 mostrou DMA3 do ARM7 em
`0x00000000` (desabilitado no instante da amostra) e no ARM9
`TIMER3=0x00C1`, `REG_IE=0x00050049`, `REG_IME=0`, todos estes
últimos **após** a entrada no menu. A análise do código mostrou
que o wrapper `cardenginei/arm9/source/cardengine.c::inGameMenu()`
chama `enterCriticalSection()` antes de executar o binário IGM.

### Implementação de diagnóstico (somente leitura)

- A V7.2.2 captura `TIMER_CR(3)`, `REG_IE` e `REG_IME` no
  ARM9 *antes* do `enterCriticalSection()` do wrapper.
- Passa uma pequena estrutura `WalkerArm9Snapshot` para o IGM pelo
  **quarto argumento do ABI ARM (r3)**. O ponteiro referencia uma estrutura
  local viva durante toda a chamada; o IGM copia imediatamente o conteúdo.
  O tipo compartilhado e a assinatura magic estão em
  `common/include/walker_arm9_snapshot.h`.
- O mecanismo é restrito ao código NTR do DSi: compila o contrato anterior
  de três parâmetros para B4DS/TWLSDK, sem alterar o layout binário do
  cardengine ARM9, a tabela de IRQ ou os índices `sharedAddr[]`.
- O menu **Virtual Pokéwalker V7.2.2 → X → Y → A** mostra esses valores
  como *ARM9 PRE-WRAPPER*, além da página DMA3/ARM9 anterior.
- **Limitação essencial:** a chamada ao wrapper ocorre no handler de
  interrupção IPC (`myIrqHandlerIPC()`). A captura é anterior à pausa do
  *wrapper*, mas ainda está em **contexto de interrupção**, portanto não
  mede o valor geral de `REG_IME` durante o gameplay normal e **não
  prova a posse do TIMER3**.
- O código não escreve em timers, IRQ, DMA, memória do Walker, ROM ou save;
  não liga Wi-Fi e não envia PING pelo HeartGold.

### Teste físico V7.2.2 (somente após CI verde)

1. Backup do `/_nds/nds-bootstrap-nightly.nds` comprovadamente funcional,
   bem como dos arquivos do Walker e save descartável.
2. Instalar apenas `nds-bootstrap.nds` do artefato **V7.2.2 read-only**
   no caminho Nightly; não mudar o jogo nem o APK Android.
3. Abrir HeartGold; no menu nds-bootstrap abrir `Virtual Pokéwalker`,
   confirmar o rótulo `V7.2.2`, pressionar **X → Y → A**.
4. Fotografar `TIMER3`, `REG_IE`, `REG_IME` e eventuais avisos na
   tela `ARM9 PRE-WRAPPER`. Confirmar que B retorna ao jogo.
5. Restaurar a V7.1.5 se houver travamentos, regressão de IR ou
   comportamento inesperado.

Os resultados ajudam a distinguir alterações introduzidas pelo
próprio menu, mas o bloqueio para o Wi-Fi residente continua: IRQ_WIFI,
DMA3, TIMER3 e worker cooperativo precisam de um plano de posse e
encadeamento seguro. **Não** chamar `Wifi_InitDefault()` no IGM.

## Physical V7.2.2 pre-wrapper result and V7.2.3 safety gate

The user photographed the **V7.2.2 ARM9 PRE-WRAPPER** screen on a
real DSi running HeartGold:

| ARM9 register | Before wrapper critical section | Previous in-menu capture |
| --- | --- | --- |
| `TIMER3_CR` | `0x00C1` | `0x00C1` |
| `REG_IE` | `0x00050049` | `0x00050049` |
| `REG_IME` | `0x01` | `0x00` |

Thus the wrapper's pause did **not** start timer 3, and the IME transition
matches `enterCriticalSection()`. The **pre-wrapper sample still occurs in
IPC interrupt context**, so it is not a measurement from arbitrary normal
gameplay nor evidence of the handler/function that owns timer 3.

### Decision: ordinary DSWifi startup is NOT authorized

Official DSWifi documentation says it uses a configurable default
timer on ARM9 and ARM7 (`LIBNDS_DEFAULT_TIMER_WIFI`), plus ARM7 DMA3
in DS compatibility mode. In libnds documentation, the ARM9 default is
Timer 3. A different timer configuration would require matching the
actual DSWifi/libnds build, and **auditing that alternative timer's use on
both CPUs**. No idle timer should be treated as available without
proving its owner and service lifecycle.

References:
- https://blocksds.skylyrac.net/dswifi/index.html
- https://blocksds.skylyrac.net/dswifi/md_documentation_2internet__mode.html
- https://blocksds.skylyrac.net/libnds/timers_8h.html

### V7.2.3 guard code, no Wi-Fi driver

Added `core/bootstrap/retail/nettransport/walker_wifi_preflight.h`
and `.c`, which take a caller-supplied description of the selected
ARM9 and ARM7 timer control values, ARM7 DMA3 control and independently
verified ownership assertions for each resource. The function reports
explicit block reasons if:
- a hardware capture is missing;
- either selected timer or DMA3 is **currently enabled**;
- ownership of either timer, ARM7 DMA3 or IRQ_WIFI chaining is unverified;
- the resident ARM7 Wi-Fi service or ARM9 cooperative worker is not proven.

The module **never reads or writes hardware registers**, starts a timer,
calls DSWifi, sends a packet, or touches ROM/save/Walker files. A zero
result only means that the supplied declarations satisfy the gate; it
does not establish that the declarations are true. An eventual hardware
adapter must supply independent evidence rather than fill the ownership
flags with hardcoded true values.

Offline fixtures in `tests/v72_host/test_wifi_preflight.c` expressly
**reject the user's measured ARM9 timer 3 (`0x00C1`)**, also reject the
all-idle-but-unverified state, and check each blocker on synthetic data.
Run `python3 tests/v72_host/run_preflight.py`; CI also cross-compiles the
object for ARM7 and ARM9, but does not link it to a runtime.

**No new DSi test binary or Android APK is required for this stage.**
The V7.2.2 snapshot answered the timer-state question. Next engineering
work is to identify the Timer3 interrupt handler/ownership and a safe
ARM7 Wi-Fi IRQ dispatcher, not to repeatedly generate screenshots of
the same active timer.

## V7.2.4 — IRQ_WIFI slot-24 safe footprint inspection

Follow-up to the physical V7.2.2 confirmation: ARM9 TIMER3 is already
running at `0x00C1` **before** the cardengine menu's critical section;
`REG_IE=0x00050049`, `REG_IME=1`. These readings still do not identify
the owner of the timer.

An additional concrete blocker was found in
`cardenginei/arm7/source/patcher/hook_arm7.c`:

- The legacy Nitro IRQ-table hook validates a footprint of only **17
  entries** (slots 0..16), enough to chain VBlank (0) and IPC sync (16).
  Wi-Fi uses **IRQ_WIFI slot 24**, which requires at least **25 entries
  (100 bytes)**. The current 17-entry guarantee cannot authorize writing
  to slot 24. An attempted blind extension could corrupt the game's RAM.
- For `returnIndex==3`, the existing code selects a **runtime table**,
  whose capacity is **not known** from the address of its first element.
  The fact that the address lies in the ARM7 RAM range is not proof that
  entry 24 exists.
- The existing hook's two write points MUST remain unchanged until
  layout and original dispatch/chaining ownership are established.

New `nettransport/walker_wifi_irq_audit.{h,c}` provides an **offline,
pure, no-dereference** footprint checker for this distinction.
`walkerWifiIrqInspect()` returns a conservative classification:
`INLINE_TABLE_OUTSIDE_IMAGE`, `INLINE_25_SLOTS_WITHIN_IMAGE`,
`RUNTIME_TABLE_UNBOUNDED`, or `BAD_ARGUMENT`. Even an inline
25-slot result is **not permission to hook**: the actual layout,
handler-chain semantics, writable memory and IRQ ownership must still
be independently verified.

`tests/v72_host/test_wifi_irq_audit.c` exercises the 17-versus-25
boundary, a valid in-image 25-slot footprint, an unbounded runtime
table, unaligned and missing image values, and near-upper-address ranges.
CI runs these host tests and cross-compiles the checker for ARM7.
The object is **not linked into the functioning HGSS/nds-bootstrap**;
it does not initialize Wi-Fi, manipulate IRQs or access user data.

Related official documentation:
- https://blocksds.skylyrac.net/libnds/interrupts_8h.html
- https://blocksds.skylyrac.net/dswifi/index.html

### Next engineering task
Identify the real HeartGold ARM7 IRQ-table variant during boot, and
determine the **actual** writable table extent and whether chaining a
new handler at 24 is supported. For the runtime-table variant, the
loader must locate a trustworthy table-length source rather than
guess 25 entries. In parallel, trace ownership of ARM9 TIMER3 and
validate an alternative Wi-Fi timer if the actual DSWifi toolchain
permits one. This needs source-level plus on-hardware evidence.
**No new binary or Android APK should be installed for this offline audit.**

### V7.2.4 integration — IRQ table gate now enforced by the Wi-Fi preflight

The pure `walkerWifiIrqInspect()` function is now actually called by the
existing `walkerWifiPreflight()` policy. Added
`WalkerWifiPreflight.irqLayout` and the blocking flag
`WALKER_WIFI_BLOCK_IRQ_TABLE_UNVERIFIED` (bit 10).

A future Wi-Fi adapter **cannot get a zero gate result** by asserting that
the timers/DMA/IRQ services are available while supplying either:
- a 17-slot legacy table footprint that excludes IRQ_WIFI slot 24;
- an external runtime IRQ table with no independently proven capacity;
- an invalid or out-of-bounds IRQ table candidate.

The only non-blocking table classification is an inline 25-slot range
proven inside the loaded ARM7 image. This is still *not permission to
install*: original handler ownership, chain semantics, memory
writability, timer alternatives and the resident radio service remain
separate requirements. The existing working HGSS hook is unchanged.
All new code remains **offline**, not linked into the DSi binary.

`run_preflight.py` now links both the preflight and the IRQ-footprint
module; regression tests verify that the synthetic "all resources
verified" case stops passing if its IRQ table is changed to a truncated
or unbounded runtime variant.

## V7.2.5 — medir a tabela IRQ do carregador NTR real (HeartGold)

Uma revisão mais detalhada distinguiu **dois** mecanismos neste fork:
`cardenginei/arm7/source/patcher/hook_arm7.c` é chamado em caminhos
especiais (notadamente tratamento de jogos Gen5), enquanto a inicialização
normal do HeartGold passa por
`bootloaderi/source/arm7/hook_arm7.c::hookNdsRetailArm7()`.

Esta rotina principal encontra a tabela IRQ do jogo através de endereço
salvo no cache, layout SDK conhecido, varredura de assinatura/marcador ou
cálculo relativo aos literais do handler; em seguida instala seus
hooks existentes de **VBlank (slot 0)** e **IPC (slot 16)**.
O resultado anterior baseado na garantia de 17 entradas do patcher
específico, portanto, não basta para determinar a extensão da tabela
real de HeartGold.

### Instrumentação somente leitura

A V7.2.5 adiciona quatro palavras **no final** do cabeçalho ARM7 do
cardengine (C/assembly alinhados):

- `walkerIrqTableAddress`: endereço da tabela já encontrado pelo
  carregador principal;
- `walkerIrqImageStart`: início da imagem ARM7 carregada;
- `walkerIrqImageSize`: tamanho da imagem ARM7 carregada;
- `walkerIrqTableMethod`: 1=cache, 2=layout SDK, 3=busca por marcador,
  4=cálculo relativo; zero=desconhecido.

O próprio hook de inicialização guarda esses dados ao aceitar a tabela,
**sem ler novos índices nem alterar a instalação existente**. O menu
do ARM7 responde ao novo pedido de diagnóstico `WPTQ/WPTK` com as
quatro palavras. No menu **Virtual Pokéwalker V7.2.5**, pressione
**Y** para visualizar a página **ARM7 BOOT IRQ MAP**.

A página calcula apenas se **100 bytes a partir do endereço da tabela
caberiam numericamente na imagem ARM7**. Uma mensagem de encaixe
significa apenas isso: não comprova layout real de 25 entradas,
memória gravável, controle de IRQ_WIFI ou funcionamento de rádio.
Quando a tabela está fora da imagem (ou vem de um cache/SDK), é
esperado que a capacidade permaneça **não comprovada**. O código
não faz `table[24]`, não registra IRQ_WIFI, não escreve em DMA/timers,
não inicializa DSWifi e não altera save/EEPROM.

### Teste no DSi — somente após passar a compilação completa

1. Fazer backup do `/_nds/nds-bootstrap-nightly.nds` que já funciona
   e dos saves/Walker de teste.
2. Instalar somente o artefato de diagnóstico `v72-5-hgss-ntr-irq-table-diagnostic-test-only`.
3. Abrir HeartGold usando a versão Nightly e um save descartável;
   no painel `Virtual Pokéwalker V7.2.5`, pressionar **Y**.
4. Fotografar `IRQ table`, `ARM7 image`, `Image bytes` e
   `Method` junto do aviso sobre os 25 slots.
5. Pressionar B e verificar que o jogo ainda retorna normalmente.
   Restaurar a versão funcional se houver qualquer instabilidade.

**Sem necessidade de modificar APK Android, hotspot ou ROM.**
A validação de propriedade real de IRQ_WIFI continua pendente; a
V7.2.5 não é uma versão de transporte Wi-Fi.

## Captura física V7.2.5 e implementação V7.2.6 — 22/11/2026

Fotografia enviada pelo usuário, capturada dentro de Pokémon HeartGold no
DSi com o nds-bootstrap V7.2.5:

| Campo mostrado | Valor |
|---|---|
| `IRQ table` | `0x0238ECF4` |
| `ARM7 image` | `0x02380000` |
| `Image bytes` | `0x000276D8` |
| `Method` | `Cached IRQ location` |
| indicação do próprio IGM | `25 slots fit image` |

O deslocamento é `0xECF4`; `table[24]` ficaria em `0x0238ED54`.
O final hipotético de 25 entradas cabe na região carregada. **Isso não
comprova que a entrada 24 exista como parte da tabela lógica de IRQ, que
seja gravável ou que o índice corresponda ao handler Wi-Fi usado pelo
jogo**. Em particular, o método de localização foi **cache** e
não uma assinatura nova revalidada neste boot.

### V7.2.6 — leitura somente dos três valores brutos, com limites

Novo `common/include/walker_irq_live_guard.h` faz um check puro,
sem MMIO nem leitura de RAM, antes de qualquer acesso:

- Método da fonte deve ser um dos caminhos 1..4 do bootloaderi.
- Endereço da tabela e início de imagem alinhados em 4 bytes.
- Imagem inteiramente na RAM principal de compatibilidade NTR
  `0x02000000..0x023FFFFF`, tamanho de imagem dentro desta RAM.
- 100 bytes contíguos a partir da tabela devem caber **dentro da
  imagem ARM7 carregada e da RAM**; aritmética é feita sem overflow.

O comando de IPC `WPKQ/WPKK` no ARM7 responde com apenas:
`status` (1=leitura permitida, 0=bloqueada), `word[0]`,
`word[16]` e `word[24]`, todos acessados via ponteiro
`const volatile`, somente se o guard passar. Nenhuma escrita à
tabela; nenhum IRQ registrado/encadeado, timer ou DMA ativado.

No menu `Virtual Pokéwalker V7.2.6 → Y (ARM7 BOOT IRQ MAP)
→ A (ARM7 IRQ WORDS)`, mostrar os três valores brutos.
**Mesmo quando a leitura é permitida, não interpretar word[24] como
um IRQ_WIFI válido sem prova adicional**: pode ser outro dado em RAM.
O campo cached significa que a origem da tabela não foi revalidada
neste boot. O cenário de risco de leitura de dados mapeados é mitigado
pelo guard estrito, mas a instrumentação permanece experimental.

Testes offline: `tests/v72_host/run_irq_live_guard.py`, casos com os
valores reais, acessos além da imagem, regiões fora de RAM, alinhamento,
overflow e borda final. Testes estáticos:
`tests/v72_host/test_irq_live_integration.py`, verificando que o
ARM7 só lê `entries[0]`, `entries[16]`, `entries[24]` após
checagem e que menu não afirma posse de IRQ. Compilação ARM7 incluída
no CI; nenhum serviço Wi-Fi residente foi ligado.

**Procedimento:** somente após CI completo aprovado, testar com
save descartável e backup do binário Nightly; no IGM apertar
**Y → A**, fotografar a nova tela, voltar com **B** e confirmar
continuidade do jogo. Não reconstruir APK Android nem repetir testes
de PING/hotspot. Não enviar Pokémon importantes durante este teste.

### Critério de engenharia

O sucesso da leitura não basta para autorizar `IRQ_WIFI`. Precisamos
comprovar layout e capacidade reais da tabela, o proprietário do
despachante IRQ no jogo, o encadeamento sem interrupção de handlers,
e resolver o timer3 ARM9 que estava ativo durante a captura pré-wrapper.

## V7.2.6 physical read-out — 22 November 2026: IRQ table contents NOT validated

The user supplied a real DSi photo from
`Virtual Pokéwalker V7.2.6 → Y → A`. The bounded read succeeded,
but the three raw 32-bit words were:

| Index | Observed raw value | Runtime candidate address |
| --- | --- | --- |
| 0 | `0xCBA77ABC` | from `0x0238ECF4` |
| 16 | `0x24285A5F` | from `0x0238ED34` |
| 24 | `0xBA84DFC5` | from `0x0238ED54` |

These words **do not resemble ordinary NTR executable RAM function
addresses** (typical ARM7 code may be in main RAM, shared WRAM or
ARM7 WRAM). The raw bytes are NOT proof of a handler table, and there
is currently NO basis to patch slot 24. A pointer-appearance heuristic
cannot distinguish an encoded table, an overwritten region, a cached
offset that no longer matches the loaded image, or a read/display fault.

**Do not claim a stale cache is definitively proven.** Source audit
shows the bootloader may use `patchOffsetCache.a7IrqHookOffset` to
skip rediscovery. Current retail cache files are keyed by
`romTid-headerCRC` in `_nds/nds-bootstrap/patchOffsetCache`,
and the cache struct has `patchOffsetCacheFileVersion=121`.
The loader also checks the ARM7 binary size to decide whether to reset
some cached offsets. These checks do not demonstrate that IRQ
table words have the expected semantics by the time the in-game menu
reads the candidate address. The original V7.2.5 "25 slots fit image"
display was **only a numeric bounds check**.

### V7.2.6 follow-up: offline semantic/audit gate (no console release)

- New pure-Python `tools/v7_2/analyze_irq_words.py` analyzes the
  exact measured values, flags that none looks like an ordinary ARM7
  RAM-code pointer and **always** sets `verified_irq_table=false`
  and `irq_wifi_hook_allowed=false`. A plausible-looking pointer
  does NOT authorize a hook either.
- `tests/v72_host/test_irq_words_audit.py` asserts rejection of
  those real values, rejection even when all words look plausible,
  and protection against overflow/invalid metadata.
- `walker_wifi_preflight.{h,c}` now requires two further independent,
  explicit conditions: `arm7IrqTableProvenanceVerified` and
  `arm7IrqTableSemanticsVerified`. Both default to false. An
  unverified cached address or a mere 25-slot memory span can no
  longer satisfy the gate, even if synthetic timer/DMA/IRQ claims
  are marked true. This is **policy code only** and is not linked
  to DSWifi or the running HGSS bootloader.
- The V7.2.6 device build already used for this measurement remains
  unchanged; no reason to rebuild APK/nds or repeat this memory peek.

### Engineering next step (not a current DSi test)

Determine whether the IRQ-table candidate address already contains
unexpected words during the **bootloader's original hook installation**,
or only after the game is running. Record, without replacing handlers,
the bootloader's exact chosen address, discovery path and the original
VBlank/IPC entries before it overwrites them, with a safe read bound,
and compare against the already photographed runtime raw words.
Do NOT delete the user's existing `patchOffsetCache` folder or
patch live IRQ handlers. If fresh discovery is tested later, isolate
that experiment using a copy of the SD data and a disposable save.
Radio and timer3 resource conflicts remain unresolved.
