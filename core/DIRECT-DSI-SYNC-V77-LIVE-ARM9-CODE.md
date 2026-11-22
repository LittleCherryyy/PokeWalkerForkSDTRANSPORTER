# V7.7 — live ARM9 WCM/SOC code signatures (experimental DSi test)

This experiment continues the DSi-only Virtual Pokewalker direct-sync
project, **without making any call to Wi-Fi, WCM, SOC or SOCL**.

## User-observed V7.6 result

Both original USA Rev0 HeartGold (IPKE) and SoulSilver (IPGE) gave five
matching target addresses and matching SHA256 digests for the first 32
code bytes at each target:

| API label | ARM9 address | SHA256 over exactly 32 decoded ARM9 bytes |
| --- | --- | --- |
| WCM_Init | 0x020AD850 | 6369f74947b51749f41b1dc42db9f0d10e989d24518127300ea55879176a89fa |
| WCM_StartupAsync | 0x020AD9C0 | 20af5f8f43b8fa2f1b7747e115b41bda5a876f3406341dc5ccb78c7f7ac8dac8 |
| WCM_GetPhase | 0x020AE420 | 50a48e8d3c3605adc7f1e46386654ec05e1a4fa6af163bd40d665126c22f0aff |
| SOC_Socket | 0x020A2EAC | 856fb418640b96d191c34c16da2011da5f10da499fa42eb1785241364b0e3dc0 |
| SOC_Connect | 0x020A2F04 | c0c3988ea2f7f0f199d8a5c393682f1749d129812599aa66611e7aa28f3642ff |

The V7.6 analyzer observed ARM stack-saving prologues at all five
addresses, with no recognized veneer hops. This **does not prove
callable ABI**, runtime code lifetime, correctness of ARM7 Wi-Fi driver
ownership, safety of calling NitroWiFi from any IRQ, or a network link.

## V7.7 implementation

In the DSi NTR nds-bootstrap ARM9 in-game menu, opening
"Virtual Pokewalker" and pressing **L** opens "V7.7 ARM9 WIFI CODE".
A dedicated SHA-256 routine reads five fixed 32-byte ARM9 RAM windows
**only after the user requests the diagnostic menu**. It compares the
hashes to the authenticated V7.6 values and shows MATCH / DIFF for each
symbol, plus count of matches out of five.

The runtime SHA routine is deliberately restricted to one 32-byte input.
It uses a fixed-size single 64-byte block with no heap allocation,
IPC commands, network calls or writes to code, save, ROM or .walker files.
The UI reports "Wi-Fi: NOT ENABLED" even if all five windows match.

The B4DS build returns zero code matches. No new interrupts are installed
and the ARM7 resident VBlank/bridge hook from V7.2.8 is unchanged.

## Hardware test when the CI build succeeds

1. Download the experimental V7.7 nds-bootstrap.nds from GitHub Actions.
2. Back up the current sd:/_nds/nds-bootstrap-nightly.nds and the game's
   .sav and .walker files before changing anything.
3. Rename the new nds-bootstrap.nds to nds-bootstrap-nightly.nds and
   replace only that one file.
4. In TWiLight Menu++, ensure the game's bootstrap setting uses Nightly.
5. Start HGSS, open the in-game menu, open Virtual Pokewalker, press **L**.
6. Photograph the "V7.7 ARM9 WIFI CODE" screen.
7. Press B to return, resume gameplay for 10 seconds, and repeat once.
   Optional: repeat on the second US version.

Expected for the exact US ROM and unmodified code: 5/5 matches in both
visits. A mismatch is a legitimate result, not permission to bypass checks.

## The next actual networking gate

Even an identical 5/5 code hash proves only that the *bytes* are resident
in RAM while the game is paused. The implementation must still prove
(a) that a safe ARM9 non-IRQ execution context exists, (b) correct
ARM7 WCM/WM/radio interrupt ownership, and (c) Wi-Fi/DHCP association
state, before issuing a bounded no-save DSi-to-Android PING.

**Do not set walkerDirectTransportAvailable() true based on this test.**
