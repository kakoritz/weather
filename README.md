# WeatherApp

An iOS-faithful Android weather app built with Python + Kivy. Swipe between locations,
see animated weather conditions, and get the full detail set the iPhone Weather app shows —
with zero paid API plans.

**Current version: v1.0.0**

---

## What It Does

- **Multi-location carousel** — swipe left/right between any number of saved zip codes
- **Animated backgrounds** — sun rays, drifting clouds, falling rain, twinkling stars,
  lightning flashes; all condition-specific and time-of-day aware
- **Hourly strip** — `NOW` + next 23 hours with condition icon and temperature; scrolls
  horizontally inside the main view
- **10-day forecast** — day name, condition icon, precipitation probability, temperature
  range bar with min/max
- **Detail cards** — Air Quality (US AQI), UV Index, Sunset/Sunrise arc, Wind compass,
  Rainfall, Feels Like, Humidity, Visibility, Pressure gauge
- **Location management** — add zip codes with real-time city name lookup; remove locations
  via the list screen's edit mode
- **10-minute cache** — weather data refreshes silently in the background; never a spinner
  if cached data is available

---

## Getting Started

### Prerequisites

- Python 3.10+ (`python3 --version`)
- Kivy dev dependencies (for desktop testing): `pip install kivy[base] kivymd requests`
- buildozer (for APK): see [ANDROID_APP_PLAYBOOK.md](../ANDROID_APP_PLAYBOOK.md)

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

# Build
~/.buildozer-env/bin/buildozer android debug

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
All saved locations with current temperature and conditions. Tap a location to jump to
its weather detail. Tap + to add a zip code. Long-press or edit button to remove locations.

### Weather detail (main view)
Full-screen animated background. Pull down to manually refresh. Swipe left/right to
navigate between saved locations. Bottom bar shows page dots.

### Add location
Type a US zip code. City name and state appear as you type (after 5 digits). Tap
the checkmark to save.

---

## Navigation

| Gesture / tap | Result |
|---|---|
| Swipe left / right on main view | Switch between saved locations |
| List icon (bottom right) | Open location list |
| Tap location in list | Jump to that location's weather detail |
| + button in list | Open add-location screen |
| Back gesture on Android | Return to weather detail from list |

---

## Data Sources

| Data | Source | API Key |
|---|---|---|
| Weather forecast | [Open-Meteo](https://open-meteo.com) | None |
| Air quality | [Open-Meteo AQ](https://open-meteo.com/en/docs/air-quality-api) | None |
| Zip code lookup | [Nominatim / OSM](https://nominatim.openstreetmap.org) | None |

---

## Project Documents

| File | Purpose |
|---|---|
| [DESIGN.md](DESIGN.md) | Architecture decisions and design rationale |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Version history and changelog |
| [CLAUDE_REVIEW.md](CLAUDE_REVIEW.md) | Honest technical assessment |
| [CLAUDE.md](CLAUDE.md) | AI context: rules, file map, constants |
| [../ANDROID_APP_PLAYBOOK.md](../ANDROID_APP_PLAYBOOK.md) | Full Android build guide |

---

## Build Status

CI runs on every push to `development` and every PR to `main`.
APK is built automatically on merge to `main` and published to GitHub Releases.
