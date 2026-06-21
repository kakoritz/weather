# CLAUDE.md — WeatherApp

Standard protocol for every code change, no exceptions.
Read this file before touching anything.

---

## Branch & Push Protocol

- All work goes to `development` — **never commit directly to `main`**
- `main` is protected; the only path in is a PR from `development`
- CI (pytest) runs on every push to `development` and every PR targeting `main`
- APK build runs on every push to `main`
- Open PR `development → main` only when CI is green and QA is done

### Workflow

```
work on development branch
  → update all five docs (still on development)
  → git push origin development
  → CI runs (pytest)
  → open PR development → main
  → CI runs again on PR
  → merge PR (squash)
  → APK builds automatically
```

### Five docs to update before every PR

| File | Purpose |
|---|---|
| `RELEASE_NOTES.md` | New version entry (Added / Changed / Fixed) |
| `README.md` | Reflect actual current state |
| `DESIGN.md` | Update if architecture or decisions changed |
| `CLAUDE_REVIEW.md` | New review entry for the version |
| `CLAUDE.md` | Update if file map, constants, or protocol changed |

**Version format:** `vMAJOR.MINOR.PATCH`

| Bump | When |
|---|---|
| PATCH | Bug fix, invisible change, docs only |
| MINOR | Any user-visible addition or change |
| MAJOR | New major system, breaking change |

Version lives in one place: `buildozer.spec` (`version = X.Y.Z`) and the top of
`main.py` (`__version__ = 'X.Y.Z'`). These must always match.

---

## Project Facts

- **Language:** Python 3.11.13 (pinned — p4a master defaults to 3.14 which breaks Kivy)
- **UI Framework:** Kivy 2.3.0 + KivyMD 1.2.0
- **Build system:** buildozer 1.6.0 (venv at `~/.buildozer-env/`)
- **Build dir:** `/home/kakoritz/.weatherapp-build` (NOT on NAS — local disk only)
- **Entry point:** `main.py`
- **Test runner:** pytest (run with `pytest tests/ -v`)
- **Android target:** API 34 / min API 24 / NDK **25b** / arm64-v8a
- **Package name:** `org.kakoritz.weatherapp`
- **GitHub repo:** `git@github.com:kakoritz/weather.git`
- **p4a:** commit `3762c88c` at `~/.p4a-py311/` (NEVER update this checkout)
- **Version:** `1.3.0` (in `buildozer.spec` AND `main.py` — must match)

---

## Architecture

The app is a `MDApp` with a `ScreenManager` (NoTransition) containing two screens:
`WeatherCarouselScreen` (main view with Kivy `Carousel` widget holding one
`WeatherDetailWidget` per location) and `LocationListScreen` (list view with search bar,
accessed via bottom-bar icon). There is no separate AddLocationScreen — the search bar
is built into the list screen.

`WeatherDetailWidget` is one continuous screen (v1.3.0+): the condition gradient +
particle overlay (`weather_overlay.py`) span the *entire* widget via `canvas.before`,
not just a hero strip. The hero `FloatLayout` and the details `BoxLayout` below it are
both fully transparent — no background, no border — they're pure layout containers
floating text/cards on the shared full-screen sky. Individual stat cards (hourly,
daily, AQ, etc.) each carry their own translucent frosted-glass background so the sky
is visible through them. See DESIGN.md's "Layout architecture" section for the full
widget tree.

Weather data is fetched in background threads and delivered to the UI via
`Clock.schedule_once(callback, 0)`. All data is cached as JSON in `user_data_dir`.

**Key UI lesson:** `MDScreen` extends `RelativeLayout`. Widget `pos` inside it is
RELATIVE, not absolute window coordinates. Never use `widget.to_window()` for menu/
popup positioning — anchor to `Window.width/height` directly.

---

## File Map

```
main.py                       ← App entry point, WeatherApp(MDApp), ScreenManager setup
buildozer.spec                ← Android build configuration
create_assets.py              ← Generates icon.png and presplash.jpg using Pillow
requirements-test.txt         ← pytest + mocking deps (NOT for Android)

src/
  api/
    weather.py                ← Open-Meteo forecast + air quality API client
    geocoding.py              ← Nominatim zip-to-location lookup
  models/
    location.py               ← Location dataclass (zip, city, state, lat, lon)
    weather.py                ← WeatherData, HourlyEntry, DailyForecast, WeatherAlert dataclasses
  storage/
    manager.py                ← JSON-based location list + weather cache persistence
  screens/
    location_list.py          ← LocationListScreen: MDList of all saved locations
    add_location.py           ← AddLocationScreen — DEAD CODE as of v1.2.0: defined but
                                 never instantiated. main.py's _on_first_location_added /
                                 _on_add_requested are also unreachable. Search bar in
                                 location_list.py is the real add-location path. Not yet
                                 removed — flagged in FEATURES.md cleanup backlog instead.
    weather_detail.py         ← WeatherCarouselScreen + WeatherDetailWidget (main view)
  widgets/
    hourly_card.py            ← HourlyForecastCard: horizontal ScrollView strip
    daily_forecast.py         ← DailyForecastCard: 10-day vertical list
    detail_cards.py           ← DetailCardsGrid: AlertBanner, AQ, Temp Map, 2-col grid
  utils/
    wmo_codes.py              ← WMO weather code → (label, condition_key) mapping; also
                                 DAY_GRADIENTS/NIGHT_GRADIENTS + get_gradients() for the
                                 hero card's background (see weather_detail.py)
    units.py                  ← °F/°C conversion — single source of truth, every screen
                                 that displays a temperature must go through this

assets/
  icon.png                    ← 512×512 app icon (generated by create_assets.py)
  presplash.jpg               ← 1080×1920 launch screen (generated by create_assets.py)

tests/
  test_api.py                 ← Tests for weather.py and geocoding.py (mocked HTTP)
  test_models.py              ← Tests for Location and WeatherData construction
  test_storage.py             ← Tests for StorageManager load/save/cache

.github/workflows/
  ci.yml                      ← pytest on push to development + PR to main
  android.yml                 ← APK build + release on push to main
```

---

## Key Constants

### WMO condition keys (used in widgets)

| Key | WMO codes |
|---|---|
| `clear` | 0, 1 |
| `partly_cloudy` | 2 |
| `overcast` | 3 |
| `fog` | 45, 48 |
| `drizzle` | 51, 53, 55 |
| `rain` | 61, 63, 80, 81 |
| `heavy_rain` | 65, 82 |
| `snow` | 71, 73, 75, 85, 86 |
| `thunderstorm` | 95, 96, 99 |

### US AQI categories

| AQI range | Category | Color |
|---|---|---|
| 0–50 | Good | `#00E400` |
| 51–100 | Moderate | `#FFFF00` |
| 101–150 | Unhealthy for Sensitive | `#FF7E00` |
| 151–200 | Unhealthy | `#FF0000` |
| 201–300 | Very Unhealthy | `#8F3F97` |
| 301+ | Hazardous | `#7E0023` |

### NWS alert severity → banner color (`detail_cards.py`)

| Severity (NWS CAP enum) | Color |
|---|---|
| `Extreme` | `rgba(0.75, 0.10, 0.08, 0.95)` — deep red |
| `Severe` | `rgba(0.80, 0.25, 0.08, 0.95)` — red-orange |
| `Moderate` | `rgba(0.80, 0.55, 0.10, 0.95)` — amber |
| `Minor` | `rgba(0.62, 0.58, 0.20, 0.90)` — muted yellow |
| `Unknown` / unmapped | `rgba(0.35, 0.38, 0.45, 0.90)` — neutral slate |

NWS alert dedup: when the same `event` name appears twice (NWS reissues updated
versions of an ongoing advisory every few hours), only the one with the latest
`sent` timestamp is kept. See `_fetch_nws_alerts()` in `src/api/weather.py`.

### Weather cache TTL

`CACHE_TTL_SECONDS = 600` (10 minutes)

### Nominatim User-Agent

`kakoritz-WeatherApp/1.0 (adam@adamscottspiker.org)` — required by OSM usage policy.
Do not remove this header or the API will return 403.

---

## Code Style Rules

- KV layout strings are defined as module-level `KV = """..."""` at the top of each screen/widget
  file and loaded with `Builder.load_string(KV)` at module import time.
- Background API calls always use `threading.Thread(target=..., daemon=True)`. Results
  delivered to UI with `Clock.schedule_once(lambda dt: callback(result), 0)`.
- All sizes in KV use `sp()` for text and `dp()` for layout. Never raw pixels.
- No comments in code unless the WHY is genuinely non-obvious.
- Dataclasses use `@dataclass(frozen=True)` for immutability where the object isn't mutated
  after creation (Location). WeatherData uses regular `@dataclass` since it's rebuilt on refresh.

---

## Project-Specific Gotchas

**NO pygame SIMD fix.** This project uses Kivy, not pygame. The `custom_recipes/pygame/`
directory from the playbook is NOT present and NOT needed. Do not add it.

**NDK is 25b, NOT 28c.** NDK 28c removed `getgrent`/`setgrent`/`endgrent` from Android Bionic.
Python 3.11's `grpmodule.c` calls these unconditionally. Build fails at the C compiler step.
Use NDK 25b. The custom `custom_recipes/python3/` also patches `grpmodule.c` directly.

**widget.bind(on_touch_down=...) return value is ignored.** Kivy's `bind()` adds an observer;
observer return values do NOT affect event propagation. To block touch pass-through, subclass
Widget and override `on_touch_down`/`on_touch_move`/`on_touch_up` methods returning True.
See `_MenuDim` in `src/screens/location_list.py`.

**A guard flag must be set synchronously, not inside a `Clock.schedule_once`-deferred
callback it's meant to guard.** `LocationListScreen._open_menu` checked `self._menu_open`
before scheduling `_do_open_menu` one frame later, but only set `_menu_open = True` *inside*
that deferred callback. A fast double-tap could pass the guard twice in the one-frame gap,
creating two `_DropdownMenu` instances — each adds its own always-touch-consuming `_MenuDim`
directly to `Window`, and only the most recently created one is ever cleaned up. The other
stays forever, silently swallowing every touch on screen (looked like a full app freeze,
not a crash — confirmed via on-device logcat showing `_do_open_menu`'s `MENU:` log line
firing twice ~250ms apart from one tap). Fix: set the guard flag immediately in the
non-deferred function, before scheduling anything.

**MDScreen pos is RELATIVE.** `MDScreen → Screen → RelativeLayout`. `widget.pos` inside
MDScreen is relative to the layout origin, not absolute window coordinates. Never use
`widget.to_window()` for absolute positioning. Anchor menus/popups to `Window.width/height`.

**Window.add_widget() does not auto-size.** Explicitly set `widget.size = (Window.width,
Window.height)` before `Window.add_widget()` when the widget should fill the screen.

**FloatLayout only positions children that have a `pos_hint` — `size_hint` alone is not
enough.** A child with `size_hint=(1,1)` and no `pos_hint` gets correctly *sized* by its
FloatLayout parent but its `pos` is left untouched at whatever it was (the Kivy default,
effectively (0,0) in window-absolute terms for a freshly created widget). Inside a
stencil-masked card, this renders the widget clipped away entirely — it looks "invisible,"
not just misplaced. Always pair `size_hint` with an explicit `pos_hint` (even
`{'x': 0, 'y': 0}`) for any FloatLayout child that needs centering or anchoring.

**Label.texture_size lags layout by an unpredictable number of frames — don't build
positioning math around a fallback for when it's not ready yet.** An early version of the
"Clear Sky" icon-overlay positioning guessed a fallback text width (40% of the full row
width) for use when `texture_size` was still `(0, 0)`. That fallback was wildly wrong — it
estimated against the row's full width, not the actual text, sending the icon far off to
the left whenever the real `texture_size` hadn't arrived yet by the time the position was
computed. The robust pattern: give the Label `size_hint=(None, None)` and bind
`texture_size` directly to its own `size` (`label.bind(texture_size=lambda i, v: setattr(i,
'size', v))`), then position dependent elements (icons, degree symbols) by reading back the
label's *real* `.x`/`.right`/`.center_y` once Kivy has actually laid it out — never by
estimating the text width yourself.

**build_dir must be local.** `/home/kakoritz/.weatherapp-build` — NOT on the NAS share.
buildozer writes thousands of small files; network shares cause extreme slowness and
occasional SIGBUS errors.

**Kivy + Android networking.** On Android 9+, cleartext HTTP is blocked. All API calls
use HTTPS. Nominatim requires HTTPS (not HTTP). The `requests` library handles SSL via
`certifi` which is included in `requirements` in buildozer.spec.

**KV loading order.** `Builder.load_string(KV)` must be called at import time, before any
widget of that class is instantiated. If a class is used before its KV is loaded, Kivy
renders it without the KV styles silently (no error). Keep the `KV = """..."""` and
`Builder.load_string(KV)` at the top of each file.

**Presplash caching.** If `presplash.jpg` is changed, buildozer may not pick it up.
Fix: `find ~/.weatherapp-build -name "presplash*" -exec rm -f {} \;` before rebuilding.
This is a known buildozer/p4a bug.

**Clock callbacks and GC.** Clock.schedule_interval callbacks hold a weak reference.
If the widget is garbage-collected (e.g., screen removed from manager), the callback
stops silently. This is correct behavior — no cleanup needed if screens are properly
removed from the ScreenManager.

**Nominatim debounce.** The add-location screen debounces the lookup to 800ms after
last keypress. This is implemented via `Clock.unschedule` + `Clock.schedule_once`.
Do NOT change this to 200ms — it will hammer the public API with every keystroke.
