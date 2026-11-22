# V7.3 — HGSS Wi-Fi ABI audit

Status: **ready for an offline test on the user's own ROM.**
This is not a resident Wi-Fi build.

## Why this test matters

Physical DSi V7.2.8 screenshots proved that the resident VBlank callback
and bridge tick advance during HeartGold gameplay (both +1368). They do not
prove that a Wi-Fi stack is connected or that HGSS network functions are
callable.

The current bridge's weak default transport returns **unavailable**.
The WCM/SOCL resolver leaves callable addresses empty by design. Enabling
guessed addresses or writing into an unverified IRQ table could corrupt RAM,
interrupt the game, or affect save durability.

The next hard dependency is to identify the exact ROM revision and whether
NitroWiFi might be resident in the ARM9 binary or in an overlay that is not
available during the overworld.

## Windows test

1. Get the tools/v7_3 directory from dev/v72-resident-ping-core.
2. Drag your own HeartGold/SoulSilver .nds backup onto TESTAR_ROM_WIFI.bat.
3. The BAT calls Python 3, reads the ROM **read-only**, and creates
   wifi_abi_report.json in this folder.
4. Share only the resulting JSON. Never share the ROM, save, or walker file.

Command-line alternative:

    python tools\v7_3\hgss_wifi_abi_audit.py "G:\roms\nds\Pokemon HeartGold.nds" --output wifi_abi_report.json

The path is illustrative, not a presumed location on the user's PC.

## What the report does NOT establish

- Hashes and a title ID are identity clues, not executable address validation.
- File ARM9 SHA256 may differ from its decompressed in-RAM image.
- A raw module-parameter marker is only a candidate, not a runtime ABI proof.
- HGSS's Nintendo WFC application uses overlay ID 72 in the public
  decompilation, but its presence in the ROM does not mean it is loaded
  during normal play.
- All Wi-Fi call permission flags remain false.
- No ROM bytes, local path, game save, or Pokewalker data are copied to JSON.

## Follow-up engineering gate

After the JSON is available, validate the ARM9 decompression and exact
NitroWiFi WCM/SOCL ABI against the matching revision. If callable resident
functions cannot be proven, use an independently integrated DSWiFi stack
with explicit ARM7/ARM9 interrupt, timer, and memory ownership instead.

Only after a real Wi-Fi backend passes checks may the console attempt a
bounded DSi-to-Android PING on TCP port 30821 with **no save access**.

Until then, keep the existing V7.2.8 bootstrap installed on the DSi.
