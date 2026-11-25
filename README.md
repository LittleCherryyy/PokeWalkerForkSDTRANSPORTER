# Virtual Slot-2 — Pokéwalker Virtual Plus

**v0.1.0-beta | NBP016 + TWLM03 | Nintendo DSi (internal SD)**

An independent module within the Pokéwalker Virtual ecosystem, dedicated to native Pokémon migration from Generation III to Generation IV through Pal Park. No Wi-Fi, Android application, or physical GBA cartridge is required. This branch preserves the version confirmed working by the user on real hardware on November 25, 2026.

- [Installation, usage and limitations](virtual-slot2/README.md)
- [Version history](virtual-slot2/CHANGELOG.md)
- [Release manifest and reproducible build information](virtual-slot2/release.json)
- [NBP016 bootstrap — download](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/actions/runs/45546143437/artifacts/14991950123)
- [TWLM03 TWiLight Menu++ — DSi/NES — download](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/actions/runs/45546166642/artifacts/14990769748)

The Wi-Fi Pokéwalker code remains separate on [main](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/tree/main) and the original development branches. The two bootstrap implementations have not yet been unified. No commercial ROMs or save files are distributed.

Derived from [SD Transporter](https://github.com/Shinygati/SD-Transporter), with credit to nds-bootstrap, TWiLight Menu++ and their contributors. See [ATTRIBUTION.md](ATTRIBUTION.md), [CREDITS-UPSTREAM.md](CREDITS-UPSTREAM.md) and [LICENSE](LICENSE).

## Main project context

# Pokéwalker Virtual — SD Transporter fork

> **Unofficial derivative of [Shinygati/SD-Transporter](https://github.com/Shinygati/SD-Transporter).**
> **Original project: SD Transporter, by Shinygati and its contributors.** This repository is a personal modification of existing software, not a claim of original authorship. Credit for all pre-existing code, designs, research, assets and infrastructure belongs to their respective original creators and contributors. See [full attribution](ATTRIBUTION.md).

This repository documents and develops experimental **Nintendo DSi ↔ Android local Wi-Fi synchronization** for the virtual Pokéwalker in Pokémon HeartGold and SoulSilver. The goal is to reuse SD Transporter's existing emulation and companion application, while exploring a connection during the original in-game transfer sequence without manual transfer of `.walker` files.

**Status: experimental; in-game wireless Pokémon transfers are NOT yet validated.** The standalone DSi ping tests do not prove that Wi-Fi transport remains functional while the game is running. Do not use irreplaceable saves without backups.

## Attribution and licenses

- **Original project:** [SD Transporter — Shinygati](https://github.com/Shinygati/SD-Transporter)
- **Original license:** [GNU GPL v3](LICENSE); this fork retains it for SD Transporter-derived code.
- **Original credits:** [CREDITS-UPSTREAM.md](CREDITS-UPSTREAM.md) (preserved from the upstream repository).
- **Attribution statement:** [ATTRIBUTION.md](ATTRIBUTION.md) names upstream creators and research sources and explains the scope of this fork.
- Additional upstream projects (including nds-bootstrap and TWiLight Menu++) and third-party components retain their **own** notices/licenses. Do not delete or replace original source headers.
- This is a derivative project **not affiliated with or endorsed by Shinygati, Nintendo or The Pokémon Company**.
- When code is imported, preserve original notices and clearly label this fork's modifications.

## Planned scope

1. Nintendo DSi running HeartGold/SoulSilver through a modified nds-bootstrap.
2. Local Wi-Fi link between the DSi and the Android companion, including hotspot operation without internet access.
3. Reliable handshake, PING, error handling and, once proven, bidirectional Pokémon transfer with data-integrity checks.
4. Preservation of Android Pokéwalker UI, widget, skins and upstream functionality.

## Import and development status

The original local ZIPs contain large snapshots of SD Transporter, TWiLight Menu++, nds-bootstrap, diagnostic workspaces, generated files and binaries. **The entire ZIP contents have not been published here.** Review source provenance, individual licenses and file safety before importing any subtree. See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

## Legal and safety notice

No commercial game ROMs, save files, retail firmware, private credentials or proprietary console files should be committed. Keep backups of game saves. This repository does not distribute Nintendo games.
