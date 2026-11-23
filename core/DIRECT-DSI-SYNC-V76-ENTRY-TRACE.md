# Pokewalker Virtual — V7.5 verified WCM/SOC callsites and V7.6 entry validation

## Actual V7.5 data from the user's two original US ROMs

Original US HeartGold IPKE: 4fcded0e2713dc03929845de631d0932ea2b5a37
Original US SoulSilver IPGE: f8dc38ea20c17541a43b58c5e6d18c1732c7e582

Both V7.5 individual reports and the combined report agreed on all five
immediate BL/BLX targets in the decompressed ARM9 image:

| Public symbol | Overlay callsite | Immediate ARM9 target | Call type |
| --- | --- | --- | --- |
| WCM_Init | overlay 13, 0x02223712 | 0x020AD850 | Thumb BLX to ARM |
| WCM_StartupAsync | overlay 13, 0x02223736 | 0x020AD9C0 | Thumb BLX to ARM |
| WCM_GetPhase | overlay 72, 0x02237E0C | 0x020AE420 | Thumb BLX to ARM |
| SOC_Socket | overlay 39, 0x02229AE8 | 0x020A2EAC | ARM BL |
| SOC_Connect | overlay 39, 0x02229C5C | 0x020A2F04 | ARM BL |

- All five V7.5 callsites checked a neighboring instruction fingerprint.
- The destination region reported was static ARM9 main code.
- **Five matching addresses do not prove function entry identity**, or
  interface call safety, radio initialisation, or a working network stack.
- ARM9 reconstructed bytes: 1,122,040 for each; they have distinct SHA256s.
- The ARM7 image and overlay 72 code match across the two US titles.

## V7.6 next gate (offline, no ROM output)

- Cross-validates the V7.5 callsites from the two original ROMs again.
- Reconstructs ARM9 locally with bounded BLZ decompression.
- Only follows recognizable unconditional ARM B or PC-relative literal
  veneers at the known targets; reports bounded 32-byte SHA256 fingerprints.
- Stops at an unclassified instruction, prologue, out-of-range jump,
  register-indirect branch or loop. It never executes target code.
- The report has explicit false flags for network ABI verification,
  resident driver availability, ARM7 Wi-Fi interrupt ownership,
  physical DSi-to-Android PING and permission to call these functions.

## Architecture constraint that remains

V7.2.8 hardware showed the VBlank/bridge callbacks execute while HGSS runs,
but calling WCM_Init, WCM_StartupAsync, SOC_Connect, socket send/recv,
or other thread/IRQ-dependent NitroWiFi functions from that VBlank IRQ
would be unsafe without proof of their execution context and ARM7 radio
ownership. The current walkerDirectTransportAvailable() weak fallback
remains false. **No new IRQ slot writes or game save modifications.**

After the V7.6 trace, investigate exact ABI, whether the NitroWiFi static
code is resident and safe, and how to schedule networking from a proper
thread/task context rather than the existing ARM7 IRQ. The first hardware
test must be a bounded, no-save DSi->Android PING before any walker handoff.
