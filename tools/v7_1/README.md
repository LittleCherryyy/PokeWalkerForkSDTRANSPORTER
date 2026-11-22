# V7.1 — Offline ARM9 call inventory (read-only)

This is **not** an in-game wireless transfer implementation or DSi installable build. It is the first verified tooling step toward identifying potential WCM/SOCL function boundaries without inventing addresses.

## Verified source-stage blocker

- `core/bootstrap/retail/common/source/walker_hgss_net.c` does not resolve WCM/SOCL/SOC function entry points.
- `core/bootstrap/retail/cardengine/arm9/source/walker_direct_transport.c` refuses network calls when API entries are absent. Even if they were present, live networking is currently gated.
- Standalone DSi PING diagnostics do not demonstrate functioning connectivity during Pokémon HeartGold/SoulSilver.

## Usage (Windows PowerShell)

Python 3.10+ is required. Use an **extracted/decompressed ARM9 image** from a game copy you are legally entitled to inspect. Do not publish the ARM9 binary or a retail game ROM.

```powershell
cd "G:\GITHUB\PokeWalker virtual"
python tools/v7_1/arm9_calls.py "C:\private\hgss-arm9.bin" --load-address 0x02000000 --output "C:\private\hgss-calls.json"
python -m unittest discover -s tools/v7_1 -p "test_*.py" -v
```

**Replace** `0x02000000` with the **actual verified ARM9 load address for that exact ROM revision**, from its executable header. This is an example, not a verified address. An incorrect load address makes all reported targets wrong.

The report lists ARM-mode BL target addresses and their callsites, sorted by frequency. It is an **inventory of candidate functions only**; it does not prove WCM/SOCL identity, correct calling convention, Thumb targets, overlays, or whether functions remain resident at runtime. Even an ARM word that resembles a BL instruction may be embedded data rather than a reachable instruction.

## Next steps toward in-game PING

1. Identify the exact supported HGSS revision and independently confirm the image load address.
2. Compare relevant candidate functions against verified reference symbols/disassembly and calling conventions. Distinguish ARM, Thumb and overlays; check lifetime in resident memory.
3. Define exact functions and initialization sequencing for WCM/SOCL, DHCP, socket operations and cleanup; verify ARM7 Wi-Fi ownership and interrupts.
4. Implement reversible, nonblocking PING/ACK only after validation. No save changes or Pokémon transfers in V7.1.
5. Build against toolchain and validate on a DSi using noncritical test saves before enabling any transfer operations.

Credit for SD Transporter belongs to Shinygati and original contributors. See root `ATTRIBUTION.md`, `CREDITS-UPSTREAM.md` and `LICENSE`.
