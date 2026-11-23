# V7.4 — HGSS ARM9 runtime reconstruction

**Offline Windows test.** Keep V7.2.8 installed on the DSi. Do not update Android.

## Confirmed V7.3 reference report metadata

- HeartGold US (IPKE): full SHA1 4fcded0e2713dc03929845de631d0932ea2b5a37, compressed ARM9 762644 bytes, candidate static end 0x020BA314.
- SoulSilver US (IPGE): full SHA1 f8dc38ea20c17541a43b58c5e6d18c1732c7e582, compressed ARM9 762648 bytes, candidate static end 0x020BA318.
- ARM7 code hash and ARM9 overlay 72 hash match between titles.
- Network/WCM/SOC function addresses and ABI remain unverified.

## Windows test procedure

1. Download the V7.4 GitHub Actions artifact containing both v7_3 and v7_4 directories. Extract them alongside each other.
2. Drag your own HeartGold .nds backup onto v7_4/TESTAR_ARM9_WIFI.bat.
3. Save/rename the generated wifi_arm9_runtime_report.json as heartgold_arm9.json.
4. Repeat with SoulSilver, save the JSON as soulsilver_arm9.json.
5. Send only those two JSON files. Never share commercial ROM bytes, saves or walker files.

Command-line alternative from the root of the repository:

    python tools/v7_4/arm9_runtime_reconstruction.py "HeartGold.nds" --output heartgold_arm9.json
    python tools/v7_4/arm9_runtime_reconstruction.py "SoulSilver.nds" --output soulsilver_arm9.json

The program verifies the exact published ROM SHA1; reconstructs the BLZ-compressed
static ARM9 image using strict memory bounds; validates the Nintendo module
marker; and only emits metadata and SHA256 hashes. It does NOT write a ROM,
dump raw disassembly, patch HGSS or touch a save.

## Next development gate

Successful decompression is NOT proof that a WCM/SOC function can be called
during normal HGSS gameplay. It provides a reliable raw-to-runtime ARM9 image
fingerprint for comparison to the pret/pokeheartgold disassembly. Call-site
matching, ABI signatures, runtime overlay ownership, and interrupt/thread safety
remain prerequisite to any experimental DSi-to-Android PING.
