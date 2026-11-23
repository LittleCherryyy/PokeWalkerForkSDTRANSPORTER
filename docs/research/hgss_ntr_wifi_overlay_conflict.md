# Why the HGSS in-game Wi-Fi backend cannot directly call Overlay 0

Source: the user-supplied V9.5 complete-ROM overlay-table index
(`wifi_v95_full_rom_index.json`, HG/SS USA Rev0), corroborated by
`pret/pokeheartgold` main linker specification:
https://github.com/pret/pokeheartgold/blob/master/main.lsf

Both HG and SS in that index have:

| ARM9 overlay | Function | Start | RAM bytes | BSS bytes | End exclusive |
|---|---|---:|---:|---:|---:|
| 0 | NITRO-DWC networking / Wi-Fi wrapper | `0x021E5900` | 216448 | 4992 | `0x0221BA00` |
| 112 | HGSS Pokéwalker exchange | `0x021E5900` | 106720 | 704 | `0x021FFCA0` |

**Conflict:** their memory regions overlap from `0x021E5900` through
`0x021FFCA0`. The game loads them as mutually replaceable overlay
contents. When Pokéwalker Overlay 112 is loaded, executing networking
code belonging to Overlay 0 at its original addresses would call the
wrong instructions. Merely finding WCM/SOC signatures in the **ROM** or
in a previously loaded overlay does not establish that their **code is
resident and executable** while Pokéwalker is active.

Main executable data such as `gSoclGateway` is not proof of initialized
WCM/SOCL/SOC or ARM7 radio IRQ ownership. The earlier
`walker_hgss_net.c` resolver is intentionally fail-closed.

## Implementation consequence

A genuinely *in-game* Pokéwalker checkout must use either:

1. a standalone, validated **resident Wi-Fi service** (DS-mode
   ARM7 radio core, compatible ARM9 TCP/IP stack, heap/timers/FIFO/IRQ
   isolation, preserved game networking state); or
2. a controlled game-managed overlay transition **after** the
   Pokéwalker operation, returning to a game context where Overlay 0
   can be loaded and initialized without overwriting an active
   Pokéwalker overlay, with safe re-entry and save recovery.

Neither can be accomplished by pointing the currently written
`WalkerDirectRadioOps` table at unresolved function addresses.

A standalone `Wifi_InitDefault(WFC_CONNECT)` homebrew program is **not**
the solution: it controls both CPUs and the Wi-Fi IRQs, unlike a
resident program sharing HGSS's game runtime. The previous console
diagnostic proved Android communication from the standalone program,
not the in-game environment.

**Acceptance gate:** send the 65536-byte actual Pokéwalker checkout
during the HGSS game without any companion program, with save and
EEPROM recovery on error. A symbol scan, PING, bootstrap-side
mock or disconnected memory read is not success.

## Limitations

These values are grounded for the ROM revisions represented in the
uploaded index. Other language/region/revisions require overlay-table
verification. The table alone does not prove that Overlay 112 is
physically loaded at the precise time a particular callback executes,
only that simultaneous unrelocated use of Overlays 0 and 112 at their
linked addresses is impossible. No game save was modified.
