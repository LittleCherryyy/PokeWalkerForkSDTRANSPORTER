# Pokéwalker Virtual — V7.6: ARM9 WCM/SOC entry and veneer audit

The user supplied three successful V7.5 reports: original USA HG (IPKE) and
SS (IPGE), and a combined comparison showing **five of five identical
immediate ARM9 targets**. Both ROMs were previously reconstructed to
1,122,040 ARM9 bytes by the V7.4 BLZ decoder.

The V7.6 tool verifies those same targets *again from the original ROMs*
without making any ROM changes. It then inspects a 32-byte window at each
entry in the reconstructed ARM9 image, saves SHA256 fingerprints, and follows
only recognized unconditional ARM B and PC-literal jump veneers. It never
executes code, invokes a network function or touches a game save.

## Windows procedure

1. Download the V7.6 Windows ZIP from GitHub Actions and extract it, keeping
   directories v7_3 / v7_4 / v7_5 / v7_6 alongside each other.
2. Select **both** original .nds files in Windows Explorer.
3. Drag both onto v7_6/COMPARAR_ENTRADAS_WIFI.bat.
4. Share the resulting wifi_v76_arm9_entry_comparison.json, **not** ROMs.
5. If any error appears, send the error message; do not force the program
   past a failed signature check.

CLI alternative:

    python tools/v7_6/hgss_wifi_entry_audit.py "HeartGold.nds" "SoulSilver.nds" --output wifi_v76_arm9_entry_comparison.json

## Scope and limitations

- Every reported WCM/SOC label came from a known V7.5 callsite. A matching
  32-byte fingerprint or a plausible prologue is evidence about the static
  binary, **not** proof of execution-time ABI or correct radio ownership.
- The tool does not follow conditional branches, BL calls, arbitrary BX,
  out-of-image pointers, unusual linker veneers or any unknown instruction.
- The ARM9 network functions might require Nintendo OS threads, interrupts,
  WM/ARM7 firmware coordination and buffers. Nothing in this report proves
  that these resources exist or remain safe while HGSS is in the overworld.
- Every network availability flag remains false. **No ROM patches, no
  save writes, no Android app changes and no nds-bootstrap replacement.**
- The next engineering milestone is a verified non-IRQ execution strategy
  and a bounded network PING with explicit proof of driver availability.

Official public source references (not execution authorization):
- github.com/pret/pokeheartgold, overlays 13 / 39 / 72
- github.com/ntrtwl/NitroWiFi, WCM and SOC API headers
