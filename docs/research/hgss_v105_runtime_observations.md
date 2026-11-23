# HGSS V10.5 — focused ARM9 store breakpoint log (2026-11-22)

Source: user-uploaded `pw_v105_arm9_stores.log` and both generated GDB script files. The log contains exactly these five lines:

```text
PW_V105_EXISTING_CONNECTION arm9_port=3333
Breakpoint 1 at 0x20d18a4
Breakpoint 2 at 0x20d2034
Breakpoint 3 at 0x20d20d4
PW_V105_BREAKPOINTS_READY
```

**Observed:** GDB attached to an existing melonDS ARM9 session and registered three store-only breakpoints: A_STORE `0x020D18A4`, B_STORE `0x020D2034`, C_STORE `0x020D20D4`. Neither `PW_V105_STORE` nor `PW_V105_LIMIT_REACHED` appears in the uploaded log. The attached script has three `break *ADDRESS` commands, each with a `silent` logging callback and `continue`. The alternate script includes its own `target remote` but was not used according to the log.

**Limits:** The file alone does not establish how long execution continued after breakpoints were enabled, nor which Pokéwalker screens/actions were exercised. There were no logged store PC hits during the recorded interval; this does not prove those instructions are unreachable. An earlier full V10.4 trace reached its 64-hit limit on C_ENTRY/C_CALL/C_BYPASS; it did **not** demonstrate store execution, RAM updates, OSThreadInfo identity, Wi-Fi in-game or behavior on physical DSi/nds-bootstrap.

**Next highest-information diagnostic:** With the existing connected GDB session, interrupt execution (Ctrl+C) and inspect `x/16i 0x020D209C`, `x/16i 0x020D20B0`, `x/8i 0x020D20D4` and `info breakpoints`. This verifies actual mapped ARM9 instructions in the emulator and branch structure around C_BYPASS/C_STORE. Alternately resume tracing through relevant Pokéwalker menus using a test save, and review the same log. Do not infer a store from repeated C_BYPASS hits.

No ROM, save, Android or nds-bootstrap changes were requested or made.


## Follow-up: duplicate installed breakpoints and disassembly

User's `info breakpoints` output shows **six enabled breakpoints**, with pairs 1/4 at `0x020D18A4`, 2/5 at `0x020D2034`, 3/6 at `0x020D20D4`; all pairs run the same V10.5 logging commands. This indicates the attached GDB script was sourced twice in the same GDB session. These duplicates can log events twice and consume the global limit; they do NOT indicate duplicate HGSS instruction execution. Clean the debugger state with `delete breakpoints` before installing a new probe.

The user's live GDB disassembly around C shows:
```asm
0x020D209C: bne   0x020D20B0
0x020D20B0: ldr   r0, [r8, #112]
0x020D20B4: cmp   r0, r6
0x020D20B8: beq   0x020D20E8
0x020D20BC: cmp   r4, #0
0x020D20C0: ldrne r0, [r7, #104]
0x020D20C4: strne r0, [r4, #104]
0x020D20C8: bne   0x020D20D8
0x020D20CC: ldr   r1, [r7, #104]
0x020D20D0: ldr   r0, [pc, #32]
0x020D20D4: str   r1, [r0, #44]
```

Thus a candidate alternative memory write exists at `0x020D20C4` when `r4 != 0`; that path branches over `0x020D20D4`. If `r0 == r6` at the preceding compare the `BEQ` bypasses both. A GDB breakpoint at the address of a *conditional* instruction alone does not prove the condition held: inspect `r4`/CPSR and, for memory effects, compare before/after state.

Next diagnostic, on a currently paused GDB session: `delete breakpoints`, `break *0x020D20C4`, `continue`, then when stopped `info registers r4 r7 r0 cpsr` and `x/i $pc`. No ROM/save changes or proof of Wi-Fi.
