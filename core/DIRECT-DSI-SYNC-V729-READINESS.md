# Direct DSi Sync V7.2.9 — hardware evidence and next engineering gate

Status: **read-only diagnostics proven; resident Wi-Fi transport NOT implemented**.
Platform: physical Nintendo DSi running retail-mode HeartGold through modified nds-bootstrap with a virtual Pokéwalker.

## V7.2.8 physical console evidence (2026-11-22)

The user returned two screenshots of **V7.2.8 ARM7 HEARTBEAT**, taken
before and after resuming gameplay.

| Counter | First (hex) | Second (hex) | Delta (decimal) |
| --- | --- | --- | ---: |
| Resident ARM7 VBlank callback | `000005BD` | `00000B15` | **1368** |
| Resident bridge tick | `000005BC` | `00000B14` | **1368** |
| ARM7 IPC callback | `00006BC8` | `0000E0B2` | **29930** |

Both snapshots reported **Walker ptr: present**.

### What this does and does not establish

- The callback and bridge tick counters advanced at the same rate during gameplay.
- VBlank minus bridge ticks remained **1** in both snapshots.
- The existing ARM7 VBlank callback provides a proven *call site*, not proof that
  it is safe to initialize a Wi-Fi stack, block, allocate large buffers or do
  network I/O inside an IRQ.
- A nonzero IPC counter does **not** establish network connectivity.
- V7.2.7 found the boot-time VBlank and IPC hook addresses differed from the
  words later read at the bootloader's initial IRQ-table location. Do not
  assume that location is the live Wi-Fi IRQ table or write its slot 24.
- Prior PC->Android PING success was a host/network receiver check, not
  proof that a physical HGSS runtime could use the radio.

## Source-level findings

- `cardenginei/arm7/source/cardengine.c`: `walkerDirectBridgeTick()`
  is invoked after the checked sector-flush path in the existing VBlank callback.
- `cardenginei/arm7/source/walker_direct_bridge.c`: the linked
  `walkerDirectTransportAvailable()` currently has a **weak default returning false**.
  Push/Pull/Confirm default to no-ops. There is **no validated resident
  hardware transport** linked yet.
- `common/source/walker_hgss_net.c`: `walkerResolveHgssNet()` resets its
  API pointers, records at most a candidate US HGSS gateway address, and
  deliberately leaves all WCM/SOCL call targets unresolved. `ready`
  must remain false until full validation.
- The NTR-mode wireless network must be compatible with DS software;
  in practice use an **open 2.4-GHz hotspot with 802.11b support** for
  controlled testing. This is a radio compatibility condition, not a
  substitute for a working resident driver.

## V7.2.9 engineering acceptance criteria

1. **Do not add another periodic IRQ hook.** Use the existing bridge tick only
   for constant-time state coordination; any Wi-Fi driver that may block or
   invoke callbacks requires separately validated execution context.
2. Select a concrete NTR-mode network strategy based on source and hardware
   evidence: (a) integrate a compatible ARM7/ARM9 DSWiFi stack with explicit
   resource ownership, or (b) independently validate exact HGSS wireless
   functions, runtime overlays, calling conventions and IRQ behavior. Neither
   candidate is currently proven.
3. Preserve the game's VBlank, IPC, timer, audio, DMA, IR emulation and SD write
   ownership; **never overwrite candidate IRQ slot 24**.
4. Gate `Available()` on actual driver readiness, association to the
   intended open Android hotspot, transport session initialization and a
   verified network endpoint. A valid function address alone is insufficient.
5. Start with a small, bounded, **non-save** PING request from the real resident
   DSi to Android. Demand ACK and timeout/no-response behavior on hardware.
6. Only after a hardware PING is confirmed, add durable 64-KiB `.walker`
   handoff with CRC/session/trainer validation and recovery from interruptions.
   Never offer an unflushed or dirty walker image to Android.
7. Keep all validation builds labeled *experimental*, maintain original
   `.sav` and `.walker` backups, and do not claim Wi-Fi is enabled until
   the physical console actually sends and receives traffic.

No next binary test is justified solely by the V7.2.8 counters: the resident
call site is already proven. The meaningful next milestone is a **real Wi-Fi
driver/ABI integration proof**, not another read-only IRQ table dump.
