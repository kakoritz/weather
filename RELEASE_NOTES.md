# Release Notes — WeatherApp

---

## v1.2.0 — On-device visual QA pass, menu freeze fix, °F/°C propagation
*2026-06-17*

First release with real on-device round-trip testing during development (build → install
→ screenshot/logcat → fix → rebuild), not just post-hoc verification.

### Fixed
- **Location list menu froze the app, requiring force-close.** Root cause: `_open_menu`'s
  `self._menu_open` guard wasn't set until the *deferred* `_do_open_menu` callback ran a
  frame later, leaving a window where a fast double-tap created two `_DropdownMenu`
  instances. Each adds its own always-touch-consuming `_MenuDim` directly to `Window`;
  only the most recent one was ever tracked for removal, so the first one stayed forever,
  silently swallowing every touch on screen. Fixed by setting the guard synchronously, and
  added a defensive sweep in `_close_menu` that removes any stray `_MenuDim` regardless.
- **°F/°C toggle only affected the location list screen.** Every temperature on the
  weather carousel/detail pages (hero, hourly strip, 10-day, detail cards) was rendering
  the raw Fahrenheit value with no unit lookup at all. Added `src/utils/units.py` as the
  single source of truth and threaded `units` through `WeatherCarouselScreen` →
  `WeatherDetailWidget` → `HourlyForecastCard` / `DailyForecastCard` / `DetailCardsGrid`,
  with a `set_units()` hook so toggling on the list screen now re-renders the carousel too.
- **"Clear Sky" condition text was invisible, icon position was wildly wrong.** The label
  had `size_hint=(1,1)` but no `pos_hint` inside its `FloatLayout` — Kivy only positions
  FloatLayout children that have a `pos_hint`, so the label sat at the literal (0,0) origin
  and got clipped by the hero's stencil mask. The icon's position was computed from a
  guessed fallback width (40% of the *entire row width*) whenever `texture_size` wasn't
  ready yet, sending it far off to the left. Rewritten so the label auto-sizes to its own
  rendered text and centers on that, and the icon reads back the label's real left edge
  once Kivy has actually laid it out — no guessing.
- **Hero temperature's "°" symbol biased the apparent center of the digits.** Split into
  two labels — the number centers on its own; the degree symbol reads back the number's
  real right edge after layout settles, so it never shifts where the digits visually sit.

### Changed
- **Details panel background relightened twice** based on on-device feedback: first to a
  medium blue that kept white text legible, then — per explicit user request for a
  lighter look — to a true light sky blue (`#B3D4F2`) with all text/icons/accents in that
  panel switched from white to dark navy. White text fundamentally can't sit on a
  background this light at readable contrast; see DESIGN.md's color palette section for
  the two-theme rationale (hero stays white-on-dark, details panel is dark-on-light).
- **Hero card background is a gradient again, not a photo.** The v1.1.0 photo + dark scrim
  approach read as too dark regardless of condition. Reverted to the gradient-texture
  technique (light blue top fading to deeper blue at the bottom for `clear` day,
  per-condition elsewhere), generated inline in `WeatherDetailWidget` rather than via the
  old standalone `WeatherBackground` widget.
- **10-day forecast icons** sized up slightly and given a soft glow plate behind them —
  the drizzle/rain icon assets are nearly visually identical at small sizes and the
  raindrop color was close in hue to the (now-replaced) dark background.
- Reduced the gap above the first card in the details panel scroll (was an unconditional
  `dp(12)` spacer before every card, including the first).

### Removed
- **Nowcast card** ("Next 2 Hours" 15-minute precipitation bar chart) — user feedback was
  that it didn't add useful information. Removed the UI card, the `NowcastEntry` model,
  the `WeatherData.nowcast` field, and the `minutely_15` API params entirely.
- **Dead code:** `src/widgets/weather_bg.py` (`WeatherBackground` — superseded by the
  photo system in v1.1.0 and never deleted), `_DayIcon` in `daily_forecast.py` (unused,
  and would have raised `NameError` on `get_condition` if anything had ever called it).

---

## v1.1.0 — Nowcasting, NWS alerts, breezy-weather learnings
*2026-06-03*

### Added
- **Precipitation nowcast card** — "Next 2 Hours" full-width card with a 15-minute
  interval bar chart showing upcoming precipitation. Bars scale gray→blue by intensity.
  Smart summary: *"Rain possible in ~30 min · 0.12" peak"* or *"No precipitation
  expected."* Data from Open-Meteo `minutely_15=precipitation`.
- **NWS weather alerts banner** — Amber/red banner at top of scroll content when
  NOAA/NWS has an active watch, warning, or advisory for the location. US only, no
  API key required. Up to 2 alerts shown simultaneously.
- **Floating card layout** — Hero card and details card now float on a pure-black
  master background with dp(12) margins and rounded corners on all 4 sides. Deep blue
  details card background (0.10, 0.16, 0.28).

### Fixed
- **Menu click-through** — touches inside the menu card were falling through to the
  location card below. Root cause: `widget.bind(on_touch_down=handler)` observer return
  value is ignored by Kivy event propagation. Fixed with `_MenuDim` Widget subclass
  that overrides `on_touch_down/move/up` methods directly.
- **Menu position** — `btn.to_window()` returns wrong values inside MDScreen
  (RelativeLayout), giving `(0, 0)`. Fixed by anchoring menu to `Window.width/height`
  directly, with dim+card added as separate Window-level widgets (no FloatLayout wrapper).
- **Weather list empty cards** — list screen was built at startup before async fetch
  returned. Fixed with `on_pre_enter` refresh + push to list screen when data arrives.
- **Delete-last-location crash** — navigated to removed AddLocationScreen. Stays on
  list (empty state with search bar).
- **WebView close** — temperature map dialog is now 95%×85%, cancelable with back
  button and tap-outside.

---

## v1.0.0 — Initial release
*2026-06-01*

### Added

- **Multi-location carousel** — swipe left/right between saved zip code locations; bottom
  bar shows page indicator dots.
- **Animated weather backgrounds** — condition-specific gradient backgrounds with live
  particle animations: sun rays (clear day), star twinkle (clear night), cloud drift
  (partly cloudy), rain streaks (rain/heavy rain), snowflake fall (snow), lightning
  flash + rain (thunderstorm), fog streaks (foggy), layered clouds (overcast).
- **Hourly forecast strip** — horizontal scrollable row beginning with `NOW`; shows
  condition icon and temperature for each hour through end of day.
- **10-day forecast** — full 10-day outlook with condition icon, precipitation probability,
  and temperature range bar per day.
- **Air Quality card** — US AQI value, category label (Good → Hazardous), description,
  color scale bar.
- **UV Index card** — numeric index, label, color scale bar, protection advisory text.
- **Sunset/Sunrise card** — sunset time (large), sunrise time, arc graphic showing
  current sun position in the day arc.
- **Wind card** — compass rose with direction needle, wind speed, cardinal direction label.
- **Rainfall card** — last 24h accumulation, next 24h expected.
- **Feels Like card** — apparent temperature, plain-English reason (humidity, wind chill).
- **Humidity card** — relative humidity percentage, current dew point.
- **Visibility card** — miles, plain-English descriptor ("Perfectly clear", "Hazy").
- **Pressure card** — arc gauge graphic, inHg value, trend indicator (rising/steady/falling).
- **Location management** — add locations by US zip code with real-time Nominatim city
  lookup; remove via list screen edit mode.
- **10-minute weather cache** — data served from local JSON cache; background thread
  silently refreshes when cache is stale.
- **buildozer APK build** — debug APK via `buildozer android debug`; CI builds on merge
  to `main` and publishes to GitHub Releases (latest only).
- **GitHub Actions CI** — pytest suite runs on every push to `development` and every
  PR targeting `main`; APK build runs on `main` push.
