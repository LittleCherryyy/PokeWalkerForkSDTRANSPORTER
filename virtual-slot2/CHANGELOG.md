# Changelog — Virtual Slot-2

## v0.1.0-beta — 2026-11-25

- NBP016 + TWLM03: confirmed working by the user on a Nintendo DSi.
- External provider, native migration, verified writeback and opt-in migration limit bypass.
- In-game edition and save selector using the D-pad, bootstrap restart, catalog reuse and single-record transfer through a shared buffer.
- DS game Y menu without redundant selectors; initial insertion through the GBA menu remains available.

## Experimental history

- NBP003–011: external provider, game family detection, partial-sector read fix, migration limit bypass and save persistence. NBP011 validated a complete Emerald-to-Pearl migration.
- TWLM01–02: pre-launch selector with support for ROM variants and save copies.
- NBP012–013: in-game menu, cartridge swapping after writeback, menu initialization fix.
- NBP014–015: optimized catalog, edition grouping and direct navigation. A catalog read error was observed in NBP015.
- NBP016/TWLM03: single-operation record transfer, counter fix and DS game menu cleanup.

## Next steps

Validate all Generation IV destinations and repeated migrations, improve initialization without a configured cartridge, and investigate integration with the Pokéwalker bootstrap without regressions.
