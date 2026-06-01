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

2. **Gesture-first navigation.** Primary interaction is swipe left/right between locations.
   The bottom bar is supplementary. On Android, taps are cheap; swipes are the experience.

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

Each weather condition maps to a gradient + particle set:

| Condition | Top color | Bottom color | Particles |
|---|---|---|---|
| Clear day | `#4FC3F7` | `#0277BD` | Animated sun rays + rays rotation |
| Clear night | `#0D1B2A` | `#1A237E` | 40 twinkling stars |
| Partly cloudy day | `#64B5F6` | `#1565C0` | Sun (partial) + 2 drifting clouds |
| Partly cloudy night | `#1A237E` | `#263238` | Moon + 10 stars + 1 cloud |
| Overcast | `#546E7A` | `#37474F` | 3 layered clouds |
| Fog | `#B0BEC5` | `#78909C` | 5 horizontal fog streaks |
| Rain | `#1E3A5F` | `#0D1B2A` | Dark cloud + 20 rain streaks |
| Heavy rain | `#0D1B2A` | `#001428` | Dark cloud + 35 rain streaks |
| Snow | `#B3CCE8` | `#78909C` | White cloud + 16 drifting snowflakes |
| Thunderstorm | `#1A0A2A` | `#0D0D1A` | Dark cloud + rain + lightning flash |

Gradients are rendered as 1×256 RGB Kivy textures, created once on widget init.
Particles are drawn each frame via `Clock.schedule_interval(1/30)` on the Canvas layer.

### Color palette (UI chrome)

| Role | Color |
|---|---|
| Card background | `rgba(0, 0, 0, 0.20)` (frosted glass over gradient bg) |
| Card border | `rgba(255, 255, 255, 0.15)` |
| Primary text | `#FFFFFF` |
| Secondary text | `rgba(255, 255, 255, 0.70)` |
| Accent (rain) | `#93C5FD` |
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

### Card inventory (WeatherDetailScreen, scrolling)

1. **Hero** — city, temperature, condition, H/L (not a card; full width, no border)
2. **Summary** — text description of next 12 hours ("Partly cloudy from 9AM–12PM…")
3. **Hourly** — horizontal ScrollView; `NOW` + hours; icon + temp per slot
4. **10-Day Forecast** — vertical list; day name, icon, precip%, temperature range bar
5. **Air Quality** — US AQI value, category label, description, color scale bar, "See More"
6. **Temperature Map** — regional map with temp overlay [v2 — placeholder in v1]
7. **UV Index** — numeric value, label (Low/Moderate/High), color scale bar, advisory text
8. **Sunset** — sunset time (large), arc graphic (sun position), sunrise time
9. **Wind** — compass rose, speed, direction (SSW/NNE etc.)
10. **Rainfall** — current 24h accumulation, expected next 24h
11. **Feels Like** — apparent temperature, plain-English reason
12. **Humidity** — percentage, dew point
13. **Visibility** — miles, plain-English descriptor
14. **Pressure** — gauge arc graphic, inHg value, trend (rising/falling)

Cards 5–14 are arranged in a 2-column grid (`GridLayout cols=2`).
Cards 1–4 are full-width above the grid.

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

## Future Work (v1.x / v2.0)

### v1.x

- **Temperature map card** — WebView with OpenWeatherMap raster tile layers + OSM base
- **"See More" for Air Quality** — expand card to show PM2.5, PM10, O3, NO2 breakdown
- **"See More" for UV** — 24h UV curve chart using Kivy Canvas
- **"See More" for Pressure** — 24h pressure trend line chart
- **Precipitation chart** — hourly rain probability bar chart
- **Push notifications** — weather alerts via Android WorkManager (requires Kotlin bridge)
- **Widget** — Android home screen widget showing current temp + condition
- **Unit toggle** — °F / °C, mph / km/h, in / mm
- **Dark/light background** — user override separate from time-of-day logic

### v2.0

- **Weather map screen** — full-screen interactive map with temperature/precipitation/wind
  layers; tap map icon in bottom nav to access
- **Severe weather alerts** — NWS CAP/ATOM alerts for US locations
- **Historical data** — past 7 days charts
- **Multi-language** — internationalization via Kivy's i18n system
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
