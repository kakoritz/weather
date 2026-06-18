# DESIGN.md — WeatherApp

> The *why* behind every decision. Not what the app does — `README.md` covers that.
> This document explains tradeoffs, constraints, and architecture intent.

---

## Project Identity

WeatherApp is a faithful Android port of the iOS Weather app aesthetic and UX. The goal is a
first-class mobile experience: animated conditions, gesture navigation between locations, and a
complete information architecture that exposes everything Apple exposes — without requiring any
paid API plan or developer account.

The reference design is iOS Weather 16/17. Where iOS uses proprietary weather data, we use
open APIs. Where iOS uses native SwiftUI animations, we use Kivy Canvas instructions. The spirit
is 1:1; the stack is different.

---

## Core Design Principles

1. **No API keys.** Every data source must work with zero credentials. No secrets in repo,
   no keys to rotate, no rate limits from forgotten env vars. Builds and runs on a fresh clone.

2. **Tap-arrow navigation (revised from original swipe-first plan).** Swipe between
   locations was the original v1.0 intent but was fully disabled (`_WeatherCarousel.
   on_touch_move` returns `False` unconditionally) in favor of explicit left/right arrow
   buttons at the top of the hero. Bottom bar dots show position and are also tappable.

3. **Always-current data.** Weather is cached for 10 minutes then silently refreshed in a
   background thread. The user never sees a spinner if cached data exists.

4. **Full information parity with iOS.** Every card the iOS app shows, we show:
   AQI, UV index, sunset/sunrise arc, wind compass, rainfall, feels-like, humidity,
   visibility, pressure gauge, temperature map (v2). No missing panels.

5. **Animation is not a feature — it is the experience.** A clear-sky view with a static
   blue rectangle is not acceptable. The animated background (sun rays, drifting clouds,
   rain particles, stars) is a core requirement of v1.0, not a nice-to-have.

---

## Tech Stack Decision

### Language: Python 3.10+
**Why:** Existing toolchain (buildozer, ADB, GitHub Actions) is already proven for Python on
this machine. The ANDROID_APP_PLAYBOOK.md covers every step. Starting from a new stack would
mean re-learning build tooling, not building the app.

### UI Framework: Kivy 2.3.0 + KivyMD 1.2.0
**Why Kivy over pygame:**
Pygame is a game engine. This app has UI layouts, scroll views, carousels, text input, and
touch gestures. Building all of that from scratch with pygame is prohibitive. Kivy is a purpose-
built mobile UI framework with native touch gestures, a layout system, and Android bindings.

**Why KivyMD over pure Kivy:**
KivyMD provides Material Design components (MDTextField, MDCard, MDLabel) that match the
polished look required. Pure Kivy widgets require more KV styling work for the same result.

**Why not Flutter or React Native:**
Different build toolchain entirely. The Android App Playbook does not cover them. Flutter
requires Dart; RN requires JS/npm. Introducing a new build system for this project adds
risk and removes the existing playbook as a reference.

**Why not native Android (Kotlin):**
High capability cost. Android Studio, Gradle, Kotlin — a full new ecosystem. The goal is
shipping a polished app, not learning Android Studio.

### Build System: buildozer 1.6.0
Unchanged from ANDROID_APP_PLAYBOOK.md. Kivy is the primary use case for buildozer — the
SIMD fix required for pygame is NOT needed here.

### Weather Data: Open-Meteo
**URL:** `https://api.open-meteo.com/v1/forecast`
**Why:** Free, no API key, HTTPS, returns all fields needed (temperature, humidity, wind,
UV, pressure, visibility, sunrise/sunset, hourly + daily). Actively maintained. Used in
production by the kakoritz dashboard project already.
**Gotcha:** `moonrise`/`moonset` are NOT valid Open-Meteo daily params (confirmed 400
error) despite existing as fields on the `DailyForecast` model — moon phase is computed
locally instead (see `get_moon_phase()` in `wmo_codes.py`).

### NWS Weather Alerts: api.weather.gov
**URL:** `https://api.weather.gov/alerts/active?point={lat},{lon}`
**Why:** Free, no API key, US only. Returns active watches/warnings/advisories. Non-US
locations return a 404 or empty features array — handled gracefully. Max 3 alerts shown.

### Temperature Map: Windy.com Embed
**URL:** `https://embed.windy.com/embed2.html?lat=...&overlay=temp`
**Why:** Free interactive temperature map, no API key for the embed. Opens in a native
Android WebView Dialog (95% width, 85% height, cancelable with back button).

### Air Quality: Open-Meteo Air Quality API
**URL:** `https://air-quality-api.open-meteo.com/v1/air-quality`
**Why:** Same vendor as weather data, free, no key, returns US AQI directly.

### Geocoding (zip → lat/lon + city name): Nominatim (OpenStreetMap)
**URL:** `https://nominatim.openstreetmap.org/search`
**Why:** Free, HTTPS, no API key required (User-Agent header required by policy). Returns
city name, state, lat, lon from a US postal code in one call. OpenStreetMap data is
comprehensive for US zip codes.

**Alternative considered:** OpenWeatherMap geocoding — requires a free API key (another
secret to manage). Rejected for violating principle #1.

---

## Architecture

```
WeatherApp (MDApp)
  └── ScreenManager
        ├── AddLocationScreen    ← shown if no locations saved
        ├── WeatherCarouselScreen ← main view; wraps Carousel
        │    ├── WeatherDetailWidget[0]  ← per-location view
        │    ├── WeatherDetailWidget[1]
        │    └── ...
        └── LocationListScreen   ← bottom-bar list icon
```

### Screen transitions

- App start → load `StorageManager.load_locations()`
  - 0 locations → `AddLocationScreen`
  - ≥1 locations → `WeatherCarouselScreen` at index 0
- `WeatherCarouselScreen` bottom bar list icon → `LocationListScreen`
- `LocationListScreen` tap location → `WeatherCarouselScreen` at that location's index
- `LocationListScreen` tap + → `AddLocationScreen`
- `AddLocationScreen` confirm → return to caller screen with new location added

### Data flow

```
User enters zip
  → GeocodingAPI.lookup(zip) → Location(zip, city, state, lat, lon)
  → StorageManager.add_location(loc)
  → WeatherAPI.fetch(lat, lon) → WeatherData
  → AirQualityAPI.fetch(lat, lon) → AirQualityData
  → StorageManager.save_weather_cache(zip, data, timestamp)
  → WeatherDetailWidget.update(data)
```

On subsequent loads:
```
StorageManager.load_weather_cache(zip)
  → if age < 10 min → use cached data
  → else → fetch fresh, update cache, update widget
```

### Threading model

Kivy runs on a single thread. All API calls go through Python `threading.Thread`. The
callback to update UI must use `Clock.schedule_once(callback, 0)` to run on the main thread.
This is the standard Kivy pattern for background work.

---

## UI Specification

### Background system

**v1.2.0 change:** the hero card's background went through three iterations — animated
gradient widget (v1.0, `WeatherBackground` in `weather_bg.py`) → real photo + dark scrim
(v1.1, read as too dark on-device) → gradient again (v1.2, this time built directly in
`WeatherDetailWidget` via `_make_gradient_texture()`, not a separate widget class).
`weather_bg.py` was deleted as dead code once the photo system fully superseded it; the
gradient-texture technique itself (1×256 RGB Kivy texture, generated once per build) is
unchanged from the original approach, just inlined where it's used.

Each weather condition maps to a gradient + particle set. `WeatherOverlay`
(`weather_overlay.py`) still renders the per-condition particles (sun rays, rain, snow,
lightning, stars) on top of the gradient, between it and the text layer:

| Condition | Top color | Bottom color | Particles |
|---|---|---|---|
| Clear day | `#B3D4F2` | `#0582BA` | Animated sun rays + rays rotation |
| Clear night | `#0D1B2A` | `#1A237E` | 40 twinkling stars |
| Partly cloudy day | `#64B5F6` | `#1565C0` | Sun (partial) + 2 drifting clouds |
| Partly cloudy night | `#1A237E` | `#263238` | Moon + 10 stars + 1 cloud |
| Overcast | `#546E7A` | `#37474F` | 3 layered clouds |
| Fog | `#B0BEC5` | `#78909C` | 5 horizontal fog streaks |
| Rain | `#1E3A5F` | `#0D1B2A` | Dark cloud + 20 rain streaks |
| Heavy rain | `#0D1B2A` | `#001428` | Dark cloud + 35 rain streaks |
| Snow | `#B3CCE8` | `#78909C` | White cloud + 16 drifting snowflakes |
| Thunderstorm | `#1A0A2A` | `#0D0D1A` | Dark cloud + rain + lightning flash |

Only `clear` day was relightened in v1.2.0 (explicit user request); other conditions
keep their original, moodier gradients since they weren't reported as a problem.

### Color palette (UI chrome) — two themes, by design

The app intentionally runs **two different text/background pairings** depending on
section, not one global theme:

| Section | Background | Text |
|---|---|---|
| Hero card (city, temp, condition, H/L) | Per-condition gradient (table above) + `rgba(0,0,0,0.42)` scrim + particles | White — `#FFFFFF` at full opacity down to ~35% for tertiary text |
| Details panel (hourly/daily/grid cards) | `#B3D4F2` flat (the held "light sky blue"), cards layered with `rgba(0,0,0,0.16)` | Dark navy — `rgb(0.07, 0.14, 0.26)` at full opacity down to ~35% for tertiary text |

**Why two themes, not one:** white text needs a background luminance below ~0.18–0.20 for
WCAG-AA contrast; the light sky blue the user wanted for the details panel sits at ~0.55+
luminance, which only works with dark text. The hero kept white text because changing it
wasn't requested and the gradient there still gets darker toward the bottom (where most
hero text sits), giving it more contrast headroom than a flat light panel would.

| Role | Color |
|---|---|
| Card border | `rgba(255, 255, 255, 0.15)` (hero) / `rgba(0,0,0, 0.10)` (details panel) |
| Accent (rain, on dark hero) | `#93C5FD` |
| Accent (rain, on light details panel) | `rgb(0.05, 0.30, 0.70)` — darkened so it doesn't wash out |
| Accent (sun) | `#FCD34D` |
| Bottom nav bar | `rgba(0, 0, 0, 0.35)` |

### Typography scale

| Element | Size | Weight |
|---|---|---|
| City name | `sp(36)` | Bold |
| Temperature (hero) | `sp(80)` | Thin (200) |
| Condition text | `sp(20)` | Regular |
| H/L line | `sp(18)` | Regular |
| Card title | `sp(11)` | Light, uppercase, 2px letter-spacing |
| Card value | `sp(28)–sp(36)` | Bold |
| Card label | `sp(14)` | Regular |
| Hourly time | `sp(14)` | Regular |
| Hourly temp | `sp(16)` | Semibold |
| Daily day | `sp(18)` | Regular |
| Daily temp | `sp(18)` | Bold |

### Card inventory (WeatherDetailWidget, scrolling inside the details panel)

Full-width cards (top of scroll):
1. **Alert Banner** — amber/red NWS alert rows (shown only when active alerts present)
2. **Hourly** — horizontal ScrollView; `NOW` + 24h; condition icon + temp per slot; summary header
3. **10-Day Forecast** — vertical list; day name, icon, precip%, temperature range bar
4. **Air Quality** — US AQI value, category, color scale bar, "See More" → detail modal
5. **Temperature Map** — Windy.com embed via Android WebView dialog; "See More" opens it

2-column grid (below full-width cards):
6. **UV Index** — numeric value, label, color scale bar, advisory text
7. **Sunset** — sunset time, arc graphic showing sun position, sunrise time
8. **Wind** — compass rose with needle, speed, direction label
9. **Rainfall** — last 24h accumulation, expected next 24h
10. **Feels Like** — apparent temperature, plain-English reason
11. **Humidity** — percentage, dew point
12. **Visibility** — miles, plain-English descriptor
13. **Pressure** — gauge arc graphic, inHg value, trend (rising/falling/steady)

**Removed in v1.2.0:** Nowcast ("Next 2 Hours" 15-min precipitation bar chart). User
feedback was that it didn't add useful information over the hourly strip + daily
precip%; removed UI, model (`NowcastEntry`), and the `minutely_15` API params entirely
rather than leaving an unused fetch in place.

### Layout architecture (v1.1.0)

```
WeatherDetailWidget (FloatLayout, black background)
  └── BoxLayout (vertical, padding=[dp(12), dp(12), dp(12), dp(80)])
       ├── Hero card (FloatLayout, stencil-clip dp(18) radius, animated bg)
       ├── Widget (spacer dp(8))
       └── Details card (BoxLayout, blue #1A2947, stencil-clip dp(18) radius)
            └── ScrollView
                 └── All data cards listed above
```

The dp(80) bottom padding gives clearance for the dp(52) nav bar + breathing room.

---

## Storage

### Location storage

File: `{user_data_dir}/locations.json`

```json
[
  {
    "zip": "28139",
    "city": "Rutherfordton",
    "state": "NC",
    "lat": 35.3648,
    "lon": -81.9627
  }
]
```

### Weather cache

File: `{user_data_dir}/weather_cache.json`

```json
{
  "28139": {
    "timestamp": "2025-06-01T08:00:00",
    "data": { ... WeatherData dict ... }
  }
}
```

Cache TTL: 600 seconds (10 minutes). If cache entry is older than TTL, fetch fresh data.

---

## Build Pipeline

See `ANDROID_APP_PLAYBOOK.md` for full detail. Key differences from the pygame setup:

- **No SIMD fix.** The `custom_recipes/pygame/` directory is NOT needed. Do not include it.
- **NDK 25b** (not 28c). Kivy's p4a recipe targets NDK 25b.
- **`build_dir`**: `/home/kakoritz/.weatherapp-build` (no spaces, local disk, not NAS)
- **Requirements**: `python3,kivy==2.3.0,kivymd==1.2.0,pillow,requests,certifi`

### APK management (CI)

The `android.yml` workflow:
1. Builds a debug APK on every push to `main`
2. Publishes to GitHub Release tagged `apk-latest` (replaces previous)
3. Deletes all release assets older than the new one (keep only 1 APK)

---

## Breezy-Weather Learnings (v1.1.0+)

[breezy-weather](https://github.com/breezy-weather/breezy-weather) is a production
Kotlin/Android weather app studied as a UX and feature reference in 2026-06.

### Implemented from Breezy (v1.1.0)
- **Precipitation nowcasting** — 15-min bar chart ("Next 2 Hours"). Breezy shows this
  as their highest-signal card; we implemented using Open-Meteo `minutely_15`.
- **NWS weather alerts** — Breezy supports 5+ alert sources. We implemented US NWS only
  (free, no key) as an amber banner at top of scroll.
- **Floating card layout** — Inspired by breezy's Material 3 block-style cards.

### On the Backlog from Breezy
- **Moon rise/set times** — Breezy computes these locally using astronomical algorithms.
  Open-Meteo does NOT provide them. Implementation: use `ephem` or pure-Python calculation
  from lat/lon. Fields (`moonrise`, `moonset`) already exist in `DailyForecast` model.
- **Pollen/allergen data** — Copernicus free API. High value for allergy sufferers.
- **Climate normals** — "5° above normal" context. Open-Meteo has historical data endpoint.
- **Reorderable cards** — Drag to reorder the detail card grid. Nice polish, medium effort.
- **Precipitation radar** — Breezy defers to Windy/RainViewer; we already do Windy for temp.

### Breezy Animation Approach (future reference)
Breezy implements 7 canvas-based weather animation `implementors` (Rain, Snow, Hail,
Cloud, Wind, Sun, Meteor Shower) with frame interpolation and accelerometer input.
See: `breezy-weather/app/src/main/java/org/breezyweather/ui/weather/view/materialWeatherView/`
Our particle system in `src/widgets/weather_overlay.py` uses a similar approach but
without gravity/sensor input. Sensor-driven animations are a v2+ consideration.

---

## Future Work (v1.x / v2.0)

### v1.x
- **Moon rise/set** — astronomical calculation from lat/lon (no API needed)
- **Pollen card** — Copernicus free pollen API (PM, grass, tree, weed counts)
- **"See More" for UV** — 24h UV curve chart using Kivy Canvas
- **"See More" for Pressure** — 24h pressure trend line chart
- **Push notifications** — weather alerts via Android WorkManager (requires Kotlin bridge)
- **Unit toggle** — °F / °C stored per-location, toggleable from menu (C/F already in menu)

### v2.0
- **Weather map screen** — full-screen Windy embed in bottom nav
- **Climate normals** — "5° above normal for this date" context in hero card
- **Reorderable detail cards** — drag to rearrange the grid
- **Historical data** — past 7 days charts
- **Sensor-driven animations** — accelerometer input for gravity-aware particle effects
- **iPad / tablet layout** — side-by-side location list + detail

---

## Known Limitations

- **Nominatim rate limit:** 1 req/sec. If the user rapidly types multiple zip codes,
  requests are debounced to 800ms after last keypress.
- **Open-Meteo outage:** If the API is unreachable, the app shows cached data with an
  age indicator. If no cache exists, an error state with retry button is shown.
- **Temperature map (v1):** Not implemented. The card slot renders a placeholder
  with "Map coming in v1.1".
- **iOS-exclusive features not ported:** Next-hour precipitation timeline (Apple only),
  Apple Weather attribution (we attribute Open-Meteo and OSM).
