# Virtual Slot-2 v0.1.0-beta

## Purpose

Emulate a GBA Slot-2 cartridge on the Nintendo DSi using an external nds-bootstrap provider. The DS game continues to use the original Pal Park workflow; the GBA save is read and changes are persisted to the SD card. This is neither a Pokémon editor nor a Wi-Fi implementation.

## Installation and usage

1. Download the [published DSi beta ZIP](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/releases/download/virtual-slot2-v0.1.0-beta/Virtual-Slot2-v0.1.0-beta-DSi.zip).
2. Copy the files from its `_nds` directory to the root of the SD card: `nds-bootstrap-nightly.nds`, `nds-bootstrap/plugins/virtual_slot2.nbp` and `TWiLightMenu/dsimenu.srldr`. Use the Nightly channel.
3. Keep your existing configuration, or initially insert a compatible GBA ROM through the Y menu while highlighting the GBA game. Insertion requires an associated save. ROM and save paths can also be configured in `sd:/_nds/nds-bootstrap/slot2.ini`. See the example included in the package. Do not overwrite a working configuration indiscriminately.
4. Launch a compatible DS game. For supported titles and revisions, the daily migration limit bypass is opt-in through the Y menu or `migration.ini`.
5. Save your DS game progress. Open the in-game menu with L + Down + Select and choose Virtual Slot-2. Up/Down changes the edition, Left/Right changes the save, A confirms and restarts, and B cancels.
6. Verify MIGRATE FROM in the game's menu and complete Pal Park. Save your DS game and allow writes to finish before powering off.

## Compatibility and evidence

- Nintendo DSi, internal SD, Pearl (USA, ROM modified for Ranch): complete Emerald migration and removal from the GBA save were confirmed; FireRed was recognized; Ruby, Sapphire and LeafGreen were reported working by the user. The NBP016 + TWLM03 combination was confirmed working by the user; this does not constitute a complete migration test matrix for that version.
- Diamond, Platinum, HeartGold and SoulSilver: implementation intended, but full migrations have not yet been validated in this project.
- R4/Acekard: TWLM03 themes compiled, but have not been tested on hardware. Flashcards/B4DS are not supported by this beta's provider.
- GBA saves: 128 KiB, or 128 KiB plus 16 bytes of RTC data. ROM hacks with modified game IDs may be excluded. The catalog uses ROM headers and save filenames; it does not fully verify save contents or hack compatibility.
- Up to 96 catalog entries; scans the GBA folder and configured directories. Each save is associated with a ROM variant. To force a different variant, initially insert it through the GBA menu or configure the paths manually.
- The current reset restarts the bootstrap; it is not a reset-free hot swap. Swapping requires an initially valid virtual cartridge. Writes are verified sector by sector; there is no atomic transaction across the GBA and DS saves. Backups are recommended.
- Diagnostics: `NBP016.BIN`, `NBP016-BOOT.TXT` and `NDSBTSRP.LOG`. Personal logs and saves must not be committed to Git.

## Source and build reproduction

This beta's implementation is applied to upstream commit `75610fa9905ac252609081287121e8d4c44febed` by the [NBP016 workflow](../.github/workflows/nbp016-swap.yml). The package contains integration.patch, credits and license. The [TWLM03 workflow](../.github/workflows/twlm03-clean-menu.yml) recompiles the upstream menu without TWLM02's two additional rows. Both use devkitpro/devkitarm:20241104. GitHub Actions artifacts have limited retention; see the [manifest](release.json) for their exact IDs. Historical workflows remain in the original experimental branch; no merge with the Pokéwalker implementation has been performed.

## Credits

SD Transporter (Shinygati and contributors), nds-bootstrap and TWiLight Menu++ (DS-Homebrew and contributors). Preserve GPLv3, copyright notices and component licenses. Not affiliated with Nintendo.
