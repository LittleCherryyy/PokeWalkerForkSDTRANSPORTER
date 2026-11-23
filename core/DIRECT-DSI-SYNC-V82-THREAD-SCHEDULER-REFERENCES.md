# Virtual Pokéwalker V8.2 — scheduler-state reference audit

## Confirmed V8.1 original USA HGSS results (user report, Nov 22 2026)

The user's V8.1 offline report validated the original ROMs:
- HG: IPKE, SHA1 `4fcded0e2713dc03929845de631d0932ea2b5a37`
- SS: IPGE, SHA1 `f8dc38ea20c17541a43b58c5e6d18c1732c7e582`

All three NitroSDK OS scheduler entry addresses match both titles,
including identical 32 and 128-byte static code-window SHA256 digests.

| Source symbol | ARM9 entry address | 128-byte SHA256 in both titles |
| --- | --- | --- |
| OS_IsThreadAvailable | 0x020D1AC4 | 6f79f8546657e0f58cd1a14655aa428f899a2934cf8b0ebce8a8420283519dd5 |
| OS_CreateThread | 0x020D1AD4 | 7b287dd68088c34260a8e2394f1b51d078294901cff6cb0cc44943dd651eba5a |
| OS_WakeupThreadDirect | 0x020D1F34 | 3db8cf1e6e896b7ce88daad513295ea83af37e71930f7c895d848ac691327edd |

The original overlay 39, from `0x02227060`, has static code ending at
`0x0222AB80` and BSS ending at `0x0222B6E0`. The game's OWN worker
thread object begins at `0x0222ADF8`. Its 2048-byte stack is between
`0x0222AED0` and `0x0222B6D0`. The gap from object start to stack
bottom is 216 bytes but **this does not prove sizeof(OSThread)**.
The creation call gives callback `0x02229974` (a trampoline toward
`0x02229474`), NULL arg and an initially configured priority of 16.

All these references can become invalid when overlay 39 is unloaded.
None is an available bootstrap-owned memory region.

Important distinction:
- `OS_CreateThread`'s caller ABI is confirmed in overlay 39.
- `OS_CreateThread`'s internal `OSThread` structure layout is NOT verified.
- Runtime OS scheduler state is NOT verified.
- No additional persistent ARM9 stack or thread-object allocation
  has been established.
- ARM7/WCM/radio ownership is NOT verified.
- No network stack has been enabled in-game.

The publicly available NitroSDK OS_CreateThread specification states
the six-argument API, 4-byte aligned stack top, stack size multiple of
four, valid priorities 0–31, and that newly created threads begin
sleeping until OS_WakeupThreadDirect is called. These conditions are
necessary but do not prove safe integration with HGSS.

Source: https://twlsdk.randommeaninglesscharacters.com/docs/nitro/NitroSDK/os/thread/OS_CreateThread.html

## V8.2: bounded offline metadata reader

`tools/v8_2/hgss_thread_scheduler_refs.py`:

1. Re-verifies V8.1 full original-ROM identity, code entry SHA256
   fingerprints, assembly callsites, ABI sequence and BSS bounds.
2. Inspects a fixed maximum 128-byte ARM9 entry window per OS_* function.
3. Reports syntactically recognized **unconditional ARM** PC-relative
   LDR immediate references, reading only literal values that lie
   inside the verified static ARM9 image.
4. Reports r0-based immediate offsets as **unconfirmed offsets**:
   these are NOT named fields of OSThread.
5. Halts conservative linear scanning at an unconditional ARM B,
   BX LR, or stack pop into PC. Unknown branches and aliases are
   not followed.
6. Cross-compares HeartGold and SoulSilver, producing JSON **only**
   with metadata, not code bytes. The tool never reads live RAM,
   invokes an OS_* API, alters ROM/save or enables wireless.

The static scan may stop early, miss alternate control-flow paths or
find PC literals unrelated to the scheduler; every candidate remains
untrusted as a live state until independently validated.

## Next test

1. Download the V8.2 Windows artifact from a successful GitHub Actions
   run, unpack while keeping v7_3/v7_4/v7_5/v7_6/v8_0/v8_1/v8_2.
2. Drag both unmodified USA Rev0 ROM backups onto
   `v8_2/COMPARAR_ESTADO_THREADS.bat`.
3. Share only `wifi_v82_hgss_scheduler_refs.json`.
4. Do not install new files to the DSi/Android; continue using the
   proven V7.9 offline callback diagnostic if needed.

The following milestone may be a **read-only, bounded DSi scheduler
liveness check**, but only once a candidate address has been validated
by exact original source/callsite evidence and proved safe to read.
The actual worker and Wi-Fi Direct Sync remain fail-closed.
