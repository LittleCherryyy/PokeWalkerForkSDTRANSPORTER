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

## Revision identity: local NDS header inspector

Before giving an ARM9 scanner a load address, inspect the NDS header locally:

```powershell
python tools/v7_1/nds_header.py "C:\\private\\my-legal-game-dump.nds" --output "C:\\private\\arm9-identity.json"
```

This tool reads but **never changes or extracts** the ROM. It reports game code (IPK / IPG candidate), ARM9 ROM offset, entry, RAM address, stored segment size and SHA-256. The hash identifies the **stored** ARM9 bytes, which may be compressed; it is not automatically a hash of the decompressed runtime code. The tool does not check a regional/version whitelist and does not prove that any networking symbol is resident.

Only run `arm9_calls.py` against an **actually decompressed** and verified ARM9 image, using the matching RAM load address. Do not use a raw compressed ARM9 segment as if it were an instruction stream. Do not commit ROMs, decompressed proprietary code or user saves.

Run all synthetic-fixture tests:

```powershell
python -m unittest discover -s tools/v7_1 -p "test_*.py" -v
```

The GitHub Actions workflow `.github/workflows/v71-offline-tests.yml` runs these tests in CI; no physical DSi or Android test is performed there.

## First live test — Android V18 PING (no DSi build required)

This checks the **existing Android direct-sync server** from your Windows computer. It is a real TCP connection but **does not prove PING while HeartGold/SoulSilver runs**.

1. Open the installed Android Pokéwalker app (V18) and enable **Direct DSi Sync** so its foreground service is listening on port `30821`.
2. Turn on the Android hotspot and connect your Windows computer to that hotspot. Do not use mobile-data internet; only local Wi-Fi is needed.
3. In Windows CMD, run `ipconfig`. The **Default Gateway** of the hotspot Wi-Fi interface is often the phone's local IP. Confirm the correct interface; do not assume a hardcoded IP.
4. From your Git checkout:
   ```powershell
   cd "G:\\GITHUB\\PokeWalker virtual"
   git fetch origin
   git switch dev/v7.1-arm9-network-analysis
   git pull --ff-only
   python tools/v7_1/android_ping_probe.py 192.168.43.1
   ```
   Replace `192.168.43.1` with the **actual phone hotspot gateway** shown on your machine.
5. Expected result: three `PING N: OK` messages and a final `PASS`. The Android app should indicate a DSi/bridge request; the test does not send any Pokémon or save data.

If the test fails: check that the Android **Direct DSi Sync** foreground service is running, both devices are on the same local network, port 30821 is reachable, and your phone's hotspot allows clients to communicate with the phone. A timeout is a networking failure, not evidence of an incorrect game ROM.

**Safety:** This probe sends only three 88-byte `OP_PING` requests; it does not use `OP_PUSH`, `OP_PULL`, `OP_CONFIRM`, `.walker`, saves or game ROMs. The APK is unchanged. Successful PING proves only the Android listener and protocol over local TCP, **not** the in-game Nintendo DSi transport.
