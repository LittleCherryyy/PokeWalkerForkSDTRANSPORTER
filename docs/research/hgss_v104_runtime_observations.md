# HGSS V10.4 — first verified melonDS ARM9 trace (partial log)

Date: 2026-11-22. Emulator: melonDS, ARM9 GDB stub port 3333; user connected with arm-none-eabi-gdb and successfully read ARM9 registers at PC 0x02000800, CPSR 0x000000d3. An initial reconnect-based GDB script attempt failed during qSupported negotiation; the attached-session script worked.

## Direct evidence supplied in conversation

The user posted the last 20 lines of `pw_v104_arm9_trace.log`, containing hits 46–64. This excerpt shows repeated three-hit sequences:

- `C_ENTRY` at PC `0x020D2058`;
- `C_CALL` at PC `0x020D2070`;
- `C_BYPASS` at PC `0x020D209C`.

Last observed hit: `C_ENTRY`, hit 64. The log ends with `PW_V104_LIMIT_REACHED - disabling all trace breakpoints`. The excerpt displays **no C_STORE or other store hit**, but earlier lines 1–45 were not supplied. Therefore do **not** conclude that A_STORE, B_STORE or C_STORE never executed. This trace establishes execution of those C probe PCs in the emulator, not proof of a store, OSThreadInfo linkage, real Nintendo DSi behavior, nds-bootstrap resident networking or Android/Pokewalker transfer.

## Next experiment (V10.5)

The first trace spends hits on frequently executed entry/call/bypass probes and reaches a 64-hit global ceiling. `tools/v10_5/hgss_arm9_focused_store_trace.py` therefore:

1. Summarizes the *complete* V10.4 log to detect any A/B/C_STORE hits before another run.
2. If needed, generates a store-only trace on `0x020D18A4`, `0x020D2034`, and `0x020D20D4` with an independent log, so hot-path probes do not consume the limit.
3. Supports the known-good GDB workflow that connects manually once and sources an attached-session script without disconnecting.

No ROM/save modification or Wi-Fi/IR patches are justified on current evidence.
