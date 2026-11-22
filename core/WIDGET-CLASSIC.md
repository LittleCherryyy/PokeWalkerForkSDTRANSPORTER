# Pokéwalker Classic widget

The Android home-screen widget now uses the same `Native.classicInput()` / `Native.classicFrame()` path as MainActivity Classic mode.

Controls:
- Left, centre, right: the three Pokéwalker buttons.
- Tap LCD while inside a menu: held-centre/back. Android reserves widget long-press for move/resize, so the LCD is the substitute gesture.
- Tap LCD from HOME: widget profile / console-IP configuration.
- CONNECT > CONSOLE: starts Wi-Fi console transfer directly in the widget. If the profile has no Pokémon it receives; if it has a Pokémon it returns it.
- CONNECT > OTHER WALKER: opens the app's local/Bluetooth connect screen because RemoteViews cannot host discovery UI.

The LCD is the firmware/controller 96x64 framebuffer, not a separate Android recreation. Timed Classic-mode screens receive short background ticks after interaction, and firmware sound scores are played from `Native.classicSound()`.
