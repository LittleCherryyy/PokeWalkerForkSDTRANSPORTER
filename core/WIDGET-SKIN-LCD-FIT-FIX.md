# Widget skin LCD fit fix

The widget LCD geometry is now derived from the actual 1005x1003 skin opening instead of the older oversized approximation.

Reference opening used:
- X: centered, approximately 55.0% of shell width
- Y: approximately 26.0% from shell top
- Height: approximately 38.4% of shell height

All 160/200/240/280/320/360/400/440dp layouts use the same proportions. The touch target now matches the visible LCD rather than extending over the bezel. `PokewalkerWidgetProvider.screenSize()` was updated to exactly match the XML dimensions so generated framebuffers no longer get scaled to a different size than their ImageView.
