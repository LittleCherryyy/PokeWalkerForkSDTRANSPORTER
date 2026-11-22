# V7.1 — HGSS DWC overlay residency research

## Why the existing network entrypoints cannot be assumed resident

The public reverse-engineered project [pret/pokeheartgold](https://github.com/pret/pokeheartgold) contains two explicit game-side entrypoints:

- [`asm/unk_020915B0.s`](https://github.com/pret/pokeheartgold/blob/master/asm/unk_020915B0.s) exposes `LoadDwcOverlay` and `UnloadDwcOverlay`. The former calls `HandleLoadOverlay` with `SDK_OVERLAY_OVY_0_ID`; the latter calls `UnloadOverlayByID` with the same ID.
- [`src/unk_02037C94.c`](https://github.com/pret/pokeheartgold/blob/master/src/unk_02037C94.c), in `sub_02039FFC`, calls `LoadDwcOverlay`, loads overlay 38, performs a DWC initialization step, and subsequently calls `UnloadDwcOverlay` and `UnloadOVY38`.
- [`src/overlay_44_0222CDAC.c`](https://github.com/pret/pokeheartgold/blob/master/src/overlay_44_0222CDAC.c) also shows a mode that explicitly loads, then unloads, the DWC overlay.
- [`lib/NitroDWC/asm/include/overlay_00_arm.inc`](https://github.com/pret/pokeheartgold/blob/master/lib/NitroDWC/asm/include/overlay_00_arm.inc) references `SOC_Startup`, `SOC_Socket`, `SOC_Connect`, `SOC_Send`, `SOC_Recv`, `SOC_Close` and WCM routines. The source reference alone does **not** prove that each function's body lives in overlay 0.

**Conclusion supported by the source:** HGSS has an explicit dynamically loaded DWC overlay lifecycle. This prevents the V7.1 bootloader from assuming an arbitrary WCM/SOC function address is safe at all times. It does **not** establish the actual ROM revision address or which overlays are loaded during the Pokéwalker IR menu.

## New metadata-only HGSS overlay inspector

The script `tools/v7_1/nds_overlays.py` works entirely on a locally stored .nds dump and reads **only** the header, the ARM9 overlay metadata table and individual 8-byte FAT entries. It does not read or output the overlay's actual code, keys, save contents, Pokémon data or an executable ROM copy.

Example, when the eventual binary-analysis stage is appropriate:

```powershell
python tools/v7_1/nds_overlays.py "C:\Games\MyOwnHGSSDump.nds" --overlay-id 0
```

`--all` lists metadata for all ARM9 overlays. The reported `ram_address`, initialized size, BSS size, FAT file index and stored-file offsets are **potential load metadata** only. They are not evidence that the overlay is loaded in-game, that a callable WCM/SOC ABI is known, or that the ARM7 radio can be shared with the game. The tool rejects invalid tables, IDs, out-of-file entries and memory overflows. All tests use generated mock ROM headers/table entries and require no commercial data.

## Follow-on verification gates, before any in-game hotspot test

1. Compare **exactly the user's own HGSS build/revision** with the decomp's overlay table. Track overlays loaded when the game enters IR communication, and how their RAM ranges overlap the resident bootstrap. Header metadata cannot reveal runtime overlay lifetime.
2. Establish ARM7/ARM9 Wi-Fi ownership and callback/IRQ behavior while the game's IR session is active. Do not call into an unloaded overlay. Do not start an independent Wi-Fi firmware stack over another owner.
3. Prove a location for the nonblocking PING FSM without changing fixed cardengine VRAM. The separate FSM overflowed that region by 592 bytes; do not hide the overflow by raising the linker memory limit.
4. Avoid relying on blocking socket calls or close. The standalone DSi test in `diagnostics/dsi_ping_v6/source/direct_ping.c` records that `close()` hung during earlier hardware testing; the FSM's close callback requires an independently validated nonblocking implementation.
5. Only after a runtime networking backend is proven should `OP_PING` be connected to the in-game diagnostics screen. PUSH/PULL/CONFIRM must remain disabled until save-integrity, ownership/lease, and durable storage tests are independently passed.

## Local real TCP test already verified

`tools/v7_1/test_ping_tcp_loopback.c` runs the **same experimental ARM9 FSM source** against a local Java `ServerSocket` built from the actual Android `DirectSyncProtocol.java` implementation. The server uses an ephemeral 127.0.0.1 port, not a real hotspot, and returns two intentionally fragmented 88-byte replies: first a valid `OP_OK`, then an invalid transfer opcode. The FSM must accept the former, reject the latter, close the local connections and perform at most one callback per tick. This test exercises real nonblocking TCP behavior but is **not** a substitute for a resident DSi/HGSS hardware proof.

This research preserves the credit/licensing of Shinygati, SD-Transporter, nds-bootstrap, and the upstream source authors. No ROM bytes or copies of upstream commercial binary assets are included.
