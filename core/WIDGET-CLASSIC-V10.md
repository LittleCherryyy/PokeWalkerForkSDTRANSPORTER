# Widget Classic V10

Base: V9 skins + persistent animation.

## Trainer Card fidelity

The Classic Trainer Card now follows the retail navigation model more closely:

- overview at position 0;
- RIGHT browses `-1` through `-7 DAYS`;
- LEFT moves toward the overview and leaves to the pictogram menu from position 0;
- CENTER returns home;
- each history page reads the real 7-entry daily ledger stored in the emulated EEPROM at `0xCEF0`;
- `TOTAL DAYS` is read from the original saved `SaveData.days` field (bytes 12-13 of the health/save record), not estimated from elapsed time;
- `TOTAL STEPS` uses the saved lifetime step counter.

This matches the documented retail behavior and the `pw` matching firmware reconstruction's `TrainerHistory()` flow.

The companion core does not currently expose the retail RTC BCD registers to `walkerClassicFrame()`, so the overview keeps a walk-hours status line instead of inventing a wall-clock value.

## Skins

The ten V9 shells were rebuilt from the original glossy Pokewalker shell rather than flat recolors. The V10 assets preserve the original lighting, reflection, LCD opening, black band, lower shell and buttons, then apply ball-specific paint/details only to the upper shell.

Included: Poke, Great, Ultra, Master, Premier, Luxury, Heal, Dive, Dusk and Quick.

## Persistent animation

The foreground `WalkingService` still refreshes at 400 ms. V10 also advances the native Classic controller with `classicInput(..., -1, ...)` before rendering each service-driven frame. This keeps timed Classic state moving when the widget is untouched instead of relying on launcher interaction.
