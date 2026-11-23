# Pokéwalker Virtual V8.1 — Thread ABI and overlay lifetime gate

## Real user V8.0 results (2026-11-22)

The user supplied the verified offline original HGSS USA Rev0 JSON.
The five callsites from overlays 13 and 39 all match between HeartGold
(IPKE) and SoulSilver (IPGE), converging on three ARM9 static targets.

| Called function | ARM9 entry address | Original first 32-byte SHA-256 |
| --- | --- | --- |
| OS_IsThreadAvailable | 0x020D1AC4 | 019981ecfa25184acbaa9368622aa220d87983189bbc59b6199e3488ffbbc7a1 |
| OS_CreateThread | 0x020D1AD4 | 1582b0e22e6375c92adf24dc3d8314e56567f6d6e6742028c3a8a970a1e61da8 |
| OS_WakeupThreadDirect | 0x020D1F34 | 7f7f0e5ae216042332b365e82a2bb13d6d7bf8dadb4fd989b5eb3a06a253967d |

- Overlay 13: three Thumb-1 BLX calls to ARM targets
  (0x02226DD4, 0x02226E00, 0x02226E36).
- Overlay 39: two ARM BL calls to the same OS_CreateThread and
  OS_WakeupThreadDirect targets (0x022299AC and 0x022299B4).
- All 5 neighboring opcode anchors matched the expected assembly,
  all 5 immediate target comparisons matched, and all three 32-byte
  hashes were identical in HG and SS.
- No user report has proven that an extra OS thread can be created in
  gameplay; ARM7 radio ownership is still not established.

## Independent public source cross-check

The public original US assembly at
https://github.com/pret/pokeheartgold/blob/master/lib/NitroDWC/asm/overlay_39_arm.s
shows the game's own OS_CreateThread call in overlay 39:

- `r0`: address of OSThread storage in overlay 39 (`0x0222ADF8`)
- `r1`: callback entry trampoline within overlay 39 (`0x02229974`)
- `r2`: NULL argument to callback
- `r3`: stack top (`0x0222B6D0`)
- caller stack argument 5: size 0x800 (2048 bytes)
- caller stack argument 6: value read from a shared field,
  originally initialized to priority 0x10 (16)
- entry trampoline branches to `0x02229474` in the overlay.

These are **properties of the original game's overlay39 worker**.
They do not mean the bootstrap may borrow this worker, its stack,
the thread object or its callback: the overlay can unload, and
runtime priority/memory ownership can change.

The standard ABI has six arguments:
`OS_CreateThread(thread, callback, arg, stackTop, stackSize, priority)`.
An already-created OSThread begins suspended and is made runnable with
`OS_WakeupThreadDirect`. Activation can cause rescheduling, so it is
not appropriate inside the cardRead callback or the in-game-menu IRQ.

## V8.1 implementation

The new offline analyzer `tools/v8_1/hgss_thread_abi_context.py`:

1. Re-validates each ROM SHA1, its decompressed ARM9 image, and V8.0's
   five exact OS scheduler callsite instruction targets.
2. Re-verifies the user's three 32-byte SHA256 function-entry fingerprints,
   adds a separate 128-byte hash per entry, and traces bounded,
   recognizable immediate entry veneers without executing code.
3. Checks the original overlay39 instruction words at the argument
   preparation, its priority initialization and all six literal
   references in a bounded range, including the callback trampoline.
4. Reports the assembly-level six-argument layout and stack interval.
5. Compares HG and SS in a single metadata-only JSON. No ROM bytes are
   exported, game code executed, radio initialized or save accessed.

Synthetic tests cover ARM literal decoding, bad neighboring opcodes,
modified literal target protection, bounded ARM9 windows, cross-title
differences and refusal to overwrite source ROMs.

## User's next test

- Extract the V8.1 Windows ZIP preserving the directories
  `v7_3/v7_4/v7_5/v7_6/v8_0/v8_1`.
- Drag both original USA .nds backups to
  `v8_1/COMPARAR_ABI_THREADS.bat`.
- Send **only** `wifi_v81_hgss_thread_abi.json`, or the error message
  if the ROM does not match the expected assembly revision.

No new DSi bootstrap build needs installing; keep working V7.9
on the Nintendo DSi and the currently working Android application.

## Further engineering gates

- [ ] Analyze the OS thread implementation's structure fields and
      scheduler initialization/liveness conditions on actual gameplay RAM.
- [ ] Identify a safe, persistent ARM9 region for any new worker's stack
      and OSThread object, independent of overlay39.
- [ ] Avoid calling OS_CreateThread from cardRead, VBlank or IRQ IPC.
- [ ] Validate ARM7 WM/Wi-Fi interrupt ownership in NTR mode; current
      passive V7.2.8 data is not proof of radio ownership.
- [ ] Only after both gates, attempt a bounded, opt-in, no-save
      DSi-to-Android hotspot PING; keep the resident transport fail-closed
      until proven functional.

**Direct DSi-to-Android Wi-Fi remains NOT ENABLED in this release.**
