# Release Notes — WeatherApp

---
## v1.4.04 — Visual redesign: iOS-faithful card styles, location cards, alert badges
*2026-06-30*

### Changed
- **Location cards redesigned.** Height increased to 152dp (was 110dp), temperature font
  enlarged to sp(55) (was sp(42)), right column wider to accommodate larger number. H/L now
  displayed on one line (`H:XX°  L:XX°`) instead of two lines.
- **Alert badge on location cards.** When the location has an active weather alert, the
  condition label is replaced by a ⚠ icon + alert event name in amber text, matching
  Apple Weather's location list design.
- **Card backgrounds match iOS frosted glass.** All stat cards (hourly, 10-day, detail
  grid) now use `rgba(0.06, 0.22, 0.55, 0.52)` — a visible blue-tinted frosted glass
  instead of near-black (0.05, 0.09, 0.16). Cards now read as blue translucent panels
  floating on the sky gradient background.

---
## v1.4.03 — UI bug fixes: swipe, scroll gap, tap, temp card, bar colors
*2026-06-29*

### Fixed
- **Swipe re-enabled on full weather page.** Previously swipe was disabled on the entire
  Carousel and only worked in the bottom nav-bar dot area. Removed the custom
  `_WeatherCarousel` class that overrode `on_touch_move` to return `False`; native Kivy
  `Carousel` swipe now works anywhere on the weather screen.
- **Footer dots centered on first load.** `set_num_pages()` deferred the canvas draw
  one frame (via `Clock.schedule_once`) so dots are drawn after the nav bar has been laid
  out and `center_x` is correct. Previously dots appeared off-center on first load.
- **Large gap under search bar eliminated.** `LocationListScreen` root changed from
  `FloatLayout` with a hardcoded `pos_hint={'top': 0.72}` scroll to a `BoxLayout`
  (header + scroll), so the scroll fills exactly the space below the header regardless of
  screen height.
- **Location card tap fires on vertical scroll.** `_content_up` now tracks both `dx`
  and `dy`; tap only fires if `dx < dp(10) AND dy < dp(10)`. Previously only `dx` was
  checked, so scrolling vertically through cards triggered unintended navigation.
- **Temperature card opens only on "See More" tap.** Removed `on_touch_up` binding from
  the preview widget; only the `build_sections()` See-More footer triggers `_open_map()`.
  Card header now uses `build_sections('map-outline', 'Temperature', ...)` matching the
  Air Quality card style.
- **10-day forecast bar colors.** Changed from a flat blue-ish formula to a proper
  temperature colormap: blue (cold) → yellow → orange → red (hot), matching Apple Weather
  reference screenshots.

### Changed
- **Bottom nav bar** now shows map icon (left) · page dots (center) · list icon (right),
  matching the reference layout. The nav bar is now a `FloatLayout` containing the two
  icon buttons; the separate floating list button on the main screen is removed.

---
## v1.3.1 — Signed release APK for app store distribution
*2026-06-28*

### Changed
- CI now builds a signed release APK (was debug). Keystore stored as GitHub Secret; `apksigner` signs before publishing to GitHub Releases. APK is now accepted by Google Play and third-party stores.

---


## v1.3.0 — One continuous screen: full-page animated sky, frosted-glass cards
*2026-06-18*

Replaces the v1.2.0 "two-zone" layout (separate hero card + separate solid details
card) with a single flowing screen that more closely mimics actual iOS Weather: the
animated condition sky is now the background for the *entire* page, both card
"frames" are gone, and every stat card (hourly, 10-day, AQ, UV, wind, etc.) is now
frosted glass — translucent enough to see the sky and particles through it, opaque
enough to read white text clearly on top.

### Changed
- **Full-screen animated background.** The gradient texture + particle overlay
  (sun rays, rain, snow, stars, fog) that used to be confined to the ~240-260dp hero
  card now span the whole screen. Particle counts in `weather_overlay.py` gained a
  `density` multiplier (2.2x for full-screen use) so rain/snow/stars don't look
  sparse stretched across ~9x more area than before.
- **Hero and details containers are now fully transparent.** No more rounded-rect
  mask, no more solid background color, no more stencil clipping on either — they're
  pure layout containers now. The hero's city/temp/condition text and the details
  ScrollView both float directly on the shared full-screen sky.
- **All text is white again.** Reverts the v1.2.0 dark-text-on-light-card theme.
  Card backgrounds flipped from a near-solid dark tint to a translucent
  blue-black glass (`rgba(0.05,0.08,0.16,0.40)`) with a light frosted-edge border
  (`rgba(1,1,1,0.22)`) in `detail_cards.py`, `hourly_card.py`, and
  `daily_forecast.py`. Precip-probability accent color brightened from a dark blue
  (tuned for light cards) to a bright sky blue (`rgba(0.55,0.80,1.0,1.0)`) so it still
  pops against the new dark glass.
- **Subtle full-screen scrim** (0.25 alpha black) added for text legibility over
  bright daytime gradients — the 'clear' day sky's top color is quite light, and
  without a scrim the contrast against white text would be poor.
- Loading and error states now also render on the same animated full-screen sky
  instead of a flat black/dark placeholder.

### Fixed
- **NWS alert severity was discarded — every alert rendered as the same bold red
  banner regardless of actual urgency.** Found via a direct side-by-side comparison
  against iOS Weather for a real location (Matthews, NC): two "Special Weather
  Statement" (Moderate severity, fire-danger) alerts looked exactly as urgent as a
  Tornado Warning would, which read as contradicting the "Mainly Clear" current
  conditions shown right next to them — they weren't contradicting it, fire risk and
  sky condition are unrelated hazards, but identical styling hid that distinction.
  Alert color now maps to NWS's CAP `severity` field (Extreme/Severe → red,
  Moderate → amber, Minor → muted yellow), and the alert's `event` type is shown
  prominently instead of the auto-generated headline. New `WeatherAlert` dataclass
  replaces the old `list[str]`; `to_dict`/`from_dict` handle old cached data
  gracefully. New `_SlideUpModal`-based tap-to-expand for the full description.
- **Duplicate-looking alert banners — NWS reissues the same advisory every few
  hours while the prior issuance is still technically active.** Verified directly
  against the live NWS API for the same Matthews, NC alerts: two entries, same
  event, issued 1:44 AM and 9:56 AM, neither expired yet. `_fetch_nws_alerts()` now
  dedupes by `event`, keeping only the most recently `sent` one.
- **Confirmed NOT a bug, documented instead:** Open-Meteo's current condition and
  H/L numbers disagreeing with iOS Weather for the same place/time is genuine
  provider/model variance (verified by querying Open-Meteo's API directly), not a
  parsing bug in this app. See DESIGN.md's NWS Weather Alerts section for the
  full writeup — switching providers would mean giving up the zero-API-key principle.

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
