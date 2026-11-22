# Widget Classic V6 — continuous firmware animation

The home-screen widget now refreshes only its LCD bitmap every 400 ms while a bound active Pokéwalker is available.

This interval is taken directly from `shared/walkerclassic.c`:

`unsigned frame=(ms/400)&1;`

Therefore the walking Pokémon on the HOME screen alternates the exact two firmware frames used by Classic mode. The widget does not animate a separate Android sprite.

Implementation notes:
- `Native.classicFrame()` remains the source of the complete 96x64 LCD.
- `AppWidgetManager.partiallyUpdateAppWidget()` updates only `widget_lcd` every 400 ms.
- Full widget updates are still used for resizing, controls, configuration and sync states.
- The animation loop runs while at least one active widget exists. With phone-pedometer tracking enabled, the existing foreground `WalkingService` keeps the process alive, so the animation can remain continuous without adding another persistent notification.
