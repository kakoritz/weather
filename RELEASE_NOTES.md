# Release Notes — WeatherApp

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
