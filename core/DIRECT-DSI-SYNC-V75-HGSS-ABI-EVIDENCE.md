# V7.5 — Verified HGSS USA binary identities and Wi-Fi ABI research

## User's on-PC, read-only test results (2026-11-22)

| Property | Pokémon HeartGold USA | Pokémon SoulSilver USA |
| --- | --- | --- |
| Game code | IPKE | IPGE |
| ROM revision | 0 | 0 |
| ROM SHA-1 | 4fcded0e2713dc03929845de631d0932ea2b5a37 | f8dc38ea20c17541a43b58c5e6d18c1732c7e582 |
| Raw ARM9 bytes | 762644 | 762648 |
| Decompressed ARM9 bytes | 1122040 | 1122040 |
| ARM9 runtime SHA-256 (compressed_static_end cleared) | 9f0e2790baa596d52dbf19e6b20a951964b37f8cde1a267c18e44d072052f35c | 4569e1454c6a22d79a96f34fb720d82396159a2bed9c5d78c7610c75650ffe31 |
| ARM7 raw SHA-256 | 746355ed51b324933542a7c4fcf109a5f83755a97c95b834ffd08caf6d4fafea | same |
| ARM9 overlay 72 raw SHA-256 | 12239f448bcd1e45a492a2ebafabbdf4f392a50aa8e455e472f76ae335f7783f | same |
| Runtime ARM9 decompression | successful BLZ decode | successful BLZ decode |

Both module-param signatures are unique in the raw ARM9 file:
- HG compressed_static_end 0x020BA314
- SS compressed_static_end 0x020BA318

Source of the hash reference values: V7.3 and V7.4 user-generated JSONs.
Do not save or distribute either commercial ROM or its decoded executable.

## Architecture and callsite anchors

Upstream source: https://github.com/pret/pokeheartgold
- asm/overlay_72.s: Thumb BL to WCM_GetPhase at 0x02237E0C
- asm/overlay_13_thumb_2.s: Thumb BL to WCM_Init at 0x02223712
- asm/overlay_13_thumb_2.s: Thumb BL to WCM_StartupAsync at 0x02223736
- lib/NitroDWC/asm/overlay_39_arm.s: ARM BL to SOC_Socket at 0x02229AE8
- lib/NitroDWC/asm/overlay_39_arm.s: ARM BL to SOC_Connect at 0x02229C5C

NitroWiFi interfaces: https://github.com/ntrtwl/NitroWiFi
- WCM_Init(void *buf, s32 len), with caller-provided 32-byte aligned work RAM.
- WCM_StartupAsync(WCMConfig*, WCMNotify), callback-based.
- WCM_GetPhase() returns a WCM phase; DCF is 9.
- SOC_Connect(s, sockaddr*) is a network call; not appropriate to invoke
  unguarded or blocking from ARM7 VBlank.

**Not yet proven:** final WCM/SOC targets in the two exact binaries,
whether an immediate BL goes through a veneer, function ABI and loaded-code
lifetime in HGSS overworld, Wi-Fi IRQ ownership, and safe network-driver start.

## V7.5 implementation and stopping point

The V7.5 Python script reconstructs ARM9 in-memory using the verified decoder
and reads/decompresses only overlays 13,39,72 from the user's *local* ROM.
It verifies the published callsites' Thumb/ARM BL encodings and neighboring
instruction signatures, reporting only numeric target addresses and their
memory region. Two-ROM mode compares HeartGold against SoulSilver in one JSON.

Static address similarity does not enable networking. Every output explicitly
states Wi-Fi ABI and runtime readiness are NOT verified. No new IRQ hooks or
game save access are introduced. The resident bridge retains safe no-op network
gates until driver ownership and callability are demonstrated.

Next input is the user's V7.5 dual-ROM JSON, not another DSi IRQ dump.
