# Widget Classic V9

Changes on top of V8:

- Persistent 400 ms LCD animation clock moved into `WalkingService`, so the
  Pokémon animation no longer depends on the `AppWidgetProvider` process
  staying alive while the launcher is idle.
- `WalkingService` may remain as a foreground service while a Pokéwalker widget
  exists even if step tracking is paused. This is intentional and is required
  for continuous animation; Android will show an ongoing notification.
- Initial skin system with 10 shells: Poké Ball, Great Ball, Ultra Ball,
  Master Ball, Premier Ball, Luxury Ball, Heal Ball, Dive Ball, Dusk Ball and
  Quick Ball.
- App skin is saved per walker profile. Widget skin is saved per widget instance.
- Widget configuration now asks for profile, console host and shell skin.
- Main app Settings includes a Pokéwalker skin selector.

## Android long-press limitation

A launcher owns long-press on an AppWidget host view for drag/remove/resize.
`RemoteViews` exposes click PendingIntents but not raw ACTION_DOWN/ACTION_UP or
an OnLongClickListener. Therefore a resizable home-screen widget cannot safely
consume a true held-button gesture without the launcher opening its widget
management UI. V9 retains the firmware-equivalent held-centre action on the LCD
surface, while the three physical-looking buttons remain normal clicks.

A true press-and-hold interaction would require a normal Activity/custom View
or a floating overlay instead of a standard AppWidget.
