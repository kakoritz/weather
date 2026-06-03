# Release Notes — WeatherApp

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
