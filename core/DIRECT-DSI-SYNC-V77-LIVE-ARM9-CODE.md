# V7.7 — read-only ARM9 code residency check (experimental DSi test)

The user's V7.6 offline report identifies five ARM9 addresses in
original USA Rev0 HeartGold and SoulSilver with matching 32-byte
SHA-256 code-window fingerprints and apparent ARM stack prologues.

## Five candidate network entries

| Label | ARM9 address | First 32 bytes verified by V7.6 offline SHA256 |
| --- | --- | --- |
| WCM_Init | 0x020AD850 | yes, same HG and SS |
| WCM_StartupAsync | 0x020AD9C0 | yes, same HG and SS |
| WCM_GetPhase | 0x020AE420 | yes, same HG and SS |
| SOC_Socket | 0x020A2EAC | yes, same HG and SS |
| SOC_Connect | 0x020A2F04 | yes, same HG and SS |

The V7.7 RAM-resident in-game-menu does **not** run a full SHA-256
routine because the existing ARM9 IGM is close to its fixed 0x9C00-byte
linker budget. Instead, it uses a compact *standard CRC32 (IEEE)*
algorithm over exactly the same 32-byte ARM9 code windows. It reports
the CRC32 numbers and whether each first instruction is compatible with
an ARM stack prologue (PRO).

The companion Windows utility verifies the original US ROMs, applies
the bounded BLZ decoder from V7.4, checks the V7.6 SHA256 fingerprints
against each 32-byte window, and emits an offline CRC32 reference JSON
with no game bytes. That JSON must be compared with the 5 displayed
DSi CRC values. A CRC32 match across independent code window
comparisons is strong practical evidence of matching RAM bytes, but
it is not a cryptographic equivalence proof.

## Test steps (after GitHub CI success)

1. Obtain the V7.7 offline Windows ZIP; keep v7_3/v7_4/v7_7 together.
2. Drag both original US .nds files to
   v7_7/COMPARAR_CRC_ARM9.bat. Send only the generated
   wifi_v77_arm9_crc_reference.json, not the commercial ROMs.
3. Back up sd:/_nds/nds-bootstrap-nightly.nds, .sav and .walker.
4. Replace only the DSi bootstrap file with the V7.7 experimental
   nds-bootstrap.nds renamed to nds-bootstrap-nightly.nds.
5. Start HeartGold with TWiLight Menu++ nightly bootstrap.
6. Open nds-bootstrap's in-game menu -> Virtual Pokewalker -> L.
7. Photograph "V7.7 ARM9 LIVE CRC"; repeat with SoulSilver if desired.
8. Send the photo(s) and the reference JSON.

A 5/5 PRO value indicates plausible code prologues, not Wi-Fi readiness.
An exact set of five CRC values matching the offline JSON will indicate
the expected ARM9 function bytes are still present while the paused
in-game menu is open.

**No new radio driver, ARM7 IRQ handler, Wi-Fi calls, save mutations or
Android app updates.** The resident Direct Sync backend stays fail-closed.

The next engineering gate is to establish a safe non-IRQ ARM9 context and
ARM7 WM/radio ownership before any no-save DSi->Android PING attempt.
