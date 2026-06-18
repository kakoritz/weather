# 🌤 WeatherApp

An Android weather app that looks and feels like iOS Weather — floating glass cards,
animated skies, a 28-phase moon at night, live NWS alerts — built entirely in Python
with **zero API keys, zero paid plans, zero secrets to manage.**

**Current version: v1.2.0**

---

## Why this isn't just another weather app demo

Every data source is free and keyless (Open-Meteo, NWS, Nominatim/OSM) — clone the repo,
run it, no `.env` file, no signup form, no rate-limited trial key expiring in 30 days.

The hero card isn't a static icon over a flat color. Each condition gets its own
gradient sky plus a live Canvas particle layer: rain falls at a real diagonal, lightning
actually flashes with timing, clouds drift, sun rays glow. At night, the moon icon
isn't a generic crescent — it's the *correct* one of 28 real phases for tonight, with
illumination percentage.

Air quality, UV, wind, pressure, humidity, visibility, feels-like — every card the iPhone
Weather app shows is here, and most of them don't just show a number. The feels-like card
tells you *why* it feels different (humidity vs. wind chill). The pressure card tells you
the trend, not just the value. Active NWS watches and warnings surface as a banner at the
top — most free weather apps charge for that.

This was built and iterated against a real Pixel device, not just a desktop simulator —
every layout bug, contrast issue, and touch-handling edge case in `CLAUDE_REVIEW.md` and
`FEATURES.md` was found by installing the actual APK and looking at the actual screen.

---

## What It Does

- **Multi-location carousel** — tap the left/right arrows to switch between any number of
  saved zip codes
- **Animated condition skies** — sun rays, drifting clouds, falling rain, twinkling stars,
  lightning flashes, all layered Canvas particles over a per-condition gradient; time-of-day
  aware
- **28-phase moon** — not 8, not a placeholder crescent — the actual lunar phase tonight
  with illumination %
- **Live NWS weather alerts** — active watches/warnings/advisories surface as a banner,
  free, no key, US locations
- **Hourly strip** — `NOW` + next 23 hours with condition icon and temperature
- **10-day forecast** — day name, condition icon, precipitation probability, temperature
  range bar
- **Detail cards that explain, not just display** — Air Quality (US AQI + category),
  UV Index, Sunset/Sunrise arc, Wind compass, Rainfall, Feels Like (with plain-English
  reason), Humidity + dew point, Visibility, Pressure (with trend)
- **Interactive temperature map** — full Windy.com embed, tap to open
- **°F / °C toggle** — one tap in the menu, propagates everywhere instantly
- **Location management** — add zip codes with real-time city name lookup; swipe to delete
- **Silent background refresh** — 10-minute cache, never a loading spinner if cached data
  exists

---

## Getting Started

### Prerequisites

- Python 3.11+ (`python3 --version`)
- Kivy dev dependencies (for desktop testing): `pip install kivy[base] kivymd requests`
- buildozer (for APK): see [DEPLOYMENT.md](DEPLOYMENT.md)

### Run on desktop (development)

```bash
cd /home/kakoritz/NAS/Data/Documents/vscode/WeatherApp
pip install kivy[base] kivymd requests pillow
python main.py
```

### Build APK

```bash
# Generate icon and presplash first
python create_assets.py

# Build (must activate the venv — see DEPLOYMENT.md)
source ~/.buildozer-env/bin/activate
buildozer android debug

# Install to connected device
adb install -r bin/*.apk
```

### Run tests

```bash
pip install pytest pytest-mock responses
pytest tests/ -v
```

---

## App Screens

### Location list (list icon, bottom-right)
All saved locations with current temperature and conditions at a glance. Search bar
(city, state, or ZIP) is built into this screen — type and tap a result to add it. Swipe
a location card to reveal delete. Menu (`⋯`) has Edit List, °F/°C toggle, Notifications,
Report an Issue.

### Weather detail (main view)
Floating hero card — city, temperature, condition, H/L — over an animated, condition-aware
sky, with the moon at night. Below it, a separate floating details panel holds the hourly
strip, 10-day forecast, NWS alert banner (when active), and every detail card. Tap the
left/right arrows at the top of the hero to switch between saved locations. Bottom bar
shows page dots.

---

## Navigation

| Gesture / tap | Result |
|---|---|
| Left / right arrows on main view | Switch between saved locations |
| List icon (bottom right) | Open location list |
| Tap location in list | Jump to that location's weather detail |
| Type in list screen's search bar | Look up a city/ZIP, tap a result to add it |
| Swipe a location card | Reveal delete |
| Back gesture on Android | Return to weather detail from list |

---

## Data Sources — all free, all keyless

| Data | Source | API Key |
|---|---|---|
| Weather forecast | [Open-Meteo](https://open-meteo.com) | None |
| Air quality | [Open-Meteo AQ](https://open-meteo.com/en/docs/air-quality-api) | None |
| Severe weather alerts | [NWS / api.weather.gov](https://www.weather.gov/documentation/services-web-api) | None |
| Temperature map | [Windy.com embed](https://www.windy.com) | None |
| Zip code / city lookup | [Nominatim / OSM](https://nominatim.openstreetmap.org) | None |

---

## Project Documents

| File | Purpose |
|---|---|
| [DESIGN.md](DESIGN.md) | Architecture decisions and design rationale |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Build, deploy, QA, and troubleshooting reference |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history and changelog |
| [CLAUDE_REVIEW.md](CLAUDE_REVIEW.md) | Honest technical assessment, updated every release |
| [FEATURES.md](FEATURES.md) | Living product backlog — what's polished, what's not, what's next |
| [CLAUDE.md](CLAUDE.md) | AI context: rules, file map, constants, gotchas |
| [../ANDROID_APP_PLAYBOOK.md](../ANDROID_APP_PLAYBOOK.md) | Base Android build toolchain |
| [../ANDROID_KIVY_DEPLOY.md](../ANDROID_KIVY_DEPLOY.md) | Kivy-specific Android lessons |

---

## Build Status

CI runs on every push to `development` and every PR to `main`.
APK is built automatically on merge to `main` and published to GitHub Releases
(`apk-latest` tag — always the most recent build).
