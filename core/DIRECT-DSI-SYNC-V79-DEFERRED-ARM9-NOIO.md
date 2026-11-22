# V7.9 — one-shot deferred ARM9 dry-run (no radio or save access)

## Real DSi evidence from V7.8 (2026-11-22)

HeartGold on an actual Nintendo DSi reported:

- `ROM reads: 0x00000A01` (2561 observed cardRead entries)
- `NonIRQ+IME: 0x00000A01` (2561 entries satisfying the passive filter)
- `Last CPSR: 0x1F` (ARM System mode)
- `Read IME: 0x01` (interrupts enabled at entry)

This is a one-time screenshot; it shows those counts at that moment,
not that two observations differed or that background work executes in an
independent thread. A read callback may hold I/O locks or interrupt-sensitive
resources. These measurements **do not justify invoking WCM/SOC**.

## V7.9 implementation

1. **Menu-exit request.** On normal return from the in-game-menu wrapper,
   after leaving its critical section, queue one dry-run request by
   setting a private ARM9 word. This is a trivial store; the menu/IRQ
   path does not perform any deferred work.
2. **Post-I/O completion.** At the end of a normal cardRead callback,
   after the game's ROM-read path and its existing post-read hook have
   returned, sample ARM9 CPSR and REG_IME. In User/System/Supervisor
   mode with IME bit 0 set, increment a saturating post-read counter.
3. **Constant-time dry run.** If a request is queued, clear the flag and
   increment the completion counter. There are no loops, IPC requests,
   allocations, game calls, network calls, or SD accesses in this step.
4. **Read-only view.** Under Virtual Pokewalker -> **R**, the compact
   `V7.9 ARM9 DEFERRED` view shows ROM reads, eligible post-read
   entries, queued dry-runs, and completed dry-runs.
5. **Platform boundaries.** This code is compiled only for NTR DSi
   cardenginei ARM9 (not TWLSDK, DLDI, GSDD or B4DS). Other versions
   receive an unavailable snapshot, retaining their fixed linker sizes.
   No changes to ARM7's IRQ handling, SD writer, .walker, saves, or APK.

A queued request is serviced **only if the game later performs another
eligible normal cardRead**. No polling loop or periodic worker is created.
If the game never requests ROM data, completion remains pending.

## Hardware test

1. Back up your working nightly bootstrap and .sav/.walker files.
2. Install V7.9 nds-bootstrap.nds as
   `sd:/_nds/nds-bootstrap-nightly.nds`; enable Nightly for HGSS.
3. Open HeartGold and visit Virtual Pokewalker -> **R**.
   Photograph queued/completed counters and leave the in-game menu.
4. Walk into a different room/route to ensure ROM data is loaded.
5. Reopen Virtual Pokewalker -> **R** and photograph again.
6. Send both photos. The second one should have at least one additional
   queued/completed dry-run if a normal eligible read occurred.

This proves the feasibility of *a bounded non-I/O unit of deferred work*
on a game-triggered ARM9 callback, not a general-purpose network task
scheduler. In particular, **do not call potentially blocking WCM/SOC or
driver operations from cardRead**.

## Next milestone

Find or establish an independently schedulable non-IRQ ARM9 task with
correct Nintendo OS/WM thread context. Separately verify ARM7 Wi-Fi
driver/radio ownership, association and interruption coexistence,
then build an opt-in bounded no-save PING. Do not claim Direct Sync is
ready until actual in-game DSi-to-Android PING succeeds.
