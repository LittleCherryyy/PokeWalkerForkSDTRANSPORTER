# HGSS V10.3 — NZCV-consistent paths and change of verification method

Date: 2026-11-22. Source: user-generated `wifi_v103_hgss_cpsr_paths.json` from original USA Rev0 IPKE/IPGE ROMs. Both games have identical region reports (`comparison.all_match=true`).

## Result

| Candidate region/entry | V10.2 possible | V10.3 still possible | Bounded-path call-return assumptions |
|---|---|---|---|
| A older entry `0x020D1808` | No | No | none |
| A alternative entry `0x020D1868` | Yes | Yes | none |
| B entry `0x020D1FA0` | Yes | Yes | `0x020D1FB8` |
| C entry `0x020D2058` | Yes | Yes | `0x020D2070` |

**No possible path was removed by V10.3's flags-consistency model.**
For the V10.3 store witnesses:
- A alternative: 13 A32 path edges, including conditional branch skip at `0x020D1888` and conditional `BXNE LR` skip at `0x020D1898`; flag states remain assumptions.
- B: 23 edges, requiring a return from the BL at `0x020D1FB8` and a conditional bypass past `0x020D2018`.
- C: 25 edges, requiring a return from the BL at `0x020D2070` and a conditional bypass past `0x020D20AC`.

The V10.3 abstract semantics reset NZCV to all 16 combinations following possible flag-writing instructions. This preserves potential paths but **does not prove feasible arithmetic operands, call behavior, RAM values or execution**. The paths are NOT verified NitroSDK scheduler routines, and nothing establishes in-game Wi-Fi.

## Practical next gate: actual ARM9 execution observation

Further static scans of the same candidate branches may yield diminishing information. V10.4 therefore prepares optional **emulator-only** ARM9 GDB breakpoints via `tools/v10_4/hgss_arm9_runtime_trace_bundle.py`. It accepts this V10.3 JSON and generates a GDB script that logs at most 64 hits (11 candidate PCs covering entries, branch barriers, call sites, and the three writes). It neither reads ROM bytes nor modifies them.

A hit at `A_STORE`, `B_STORE`, or `C_STORE` would establish execution of that instruction in the configured emulator run. It would **not** prove the pointer is an OSThreadInfo, the DSi/nds-bootstrap executes the same path, or an Android Wi-Fi handshake works. No-hit is inconclusive.

The generator can be run independently from the repository with:
```powershell
python tools/v10_4/hgss_arm9_runtime_trace_bundle.py --self-test
python tools/v10_4/hgss_arm9_runtime_trace_bundle.py --report "path/to/wifi_v103_hgss_cpsr_paths.json" --output-dir "path/to/trace_output"
```

Review `README_v104_runtime_trace.txt` before using the GDB script. Debugger must support ARM9 over GDB; a melonDS build with GDB stub is one option; see <https://blocksds.skylyrac.net/docs/guides/debugging/>. Use a **copy of ROM and save** for emulator tests. A GDB breakpoint can alter emulated memory/timing, even though the ROM file remains unchanged.

## Safety

Do not modify the original ROM/save, deploy a DSi thread patch or infer Wi-Fi compatibility from static results. The Wi-Fi bridge, ARM7 IRQ/radio ownership, nds-bootstrap resident mode and actual Pokéwalker transfer all remain unverified.
