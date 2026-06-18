# FEATURES.md — Product Review & Roadmap

Living backlog for product-level decisions: what's polished, what's broken, what's
missing versus a top-tier weather app, and the order we tackle it in. Distinct from
the five required-per-PR docs — this is where direction gets debated before it
becomes a RELEASE_NOTES entry.

---

## Session 2026-06-17 — Visual fixes shipped

| Issue | Root cause | Fix |
|---|---|---|
| Details card background too dark to read against | Deep navy `(0.10, 0.16, 0.28)` | Lightened to `(0.15, 0.32, 0.55)` — closer to iOS Weather's mid blue, still passes contrast for white text. [weather_detail.py](src/screens/weather_detail.py) |
| 10-day forecast icons hard to identify (esp. rain/thunderstorm) | Two compounding causes — see below | Icons sized up `dp(36)→dp(38)` + given a soft `0.07` alpha glow plate so pale icons don't wash into the card. [daily_forecast.py](src/widgets/daily_forecast.py) |
| "Clear Sky" subtitle visibly off-center vs the H/L line below it | The condition row centered the icon+label as a *group* (flex spacers either side), but the label itself was a fixed `width=dp(220)` box with `halign='left'` — so the visible glyphs sat left-of-center inside their own box while the H/L label below used true full-width `halign='center'`. Two different centering strategies stacked on top of each other. | Condition label now centers exactly like the H/L line (`size_hint=(1,1)`, `halign='center'`). Icon is a separate floating overlay positioned from the label's `texture_size` at runtime, so it never participates in text layout. [weather_detail.py](src/screens/weather_detail.py) |

**Also removed:** `_DayIcon` in `daily_forecast.py` — a hand-drawn canvas icon class that was
dead code (unused, and would've thrown `NameError` on `get_condition` if it were ever
called — the name was never imported). `math` and `Line` imports cleaned up alongside it.

---

## Session 2026-06-17 (continued) — first real on-device round-trip

Everything below was found and fixed by actually building, installing, screenshotting,
and pulling logcat against a physical Pixel 5a, not by reading code. That loop (build →
install → screenshot/logcat → fix → rebuild) ran roughly 10 times in one session.

**°F/°C not propagating — fixed.** Confirmed root cause as suspected above. Added
`src/utils/units.py` as the single conversion source of truth and threaded `units`
through `WeatherCarouselScreen` → `WeatherDetailWidget` → `HourlyForecastCard` /
`DailyForecastCard` / `DetailCardsGrid`. `WeatherDetailWidget.set_units()` lets the
carousel re-render in place when the unit changes on the list screen.

**Menu freeze — root cause found and fixed.** This was NOT the same bug the v1.1.0
RELEASE_NOTES claimed was fixed. On-device logcat showed `_do_open_menu`'s `MENU:` log
line firing **twice**, ~250ms apart, from one tap. Root cause: `_open_menu`'s
`self._menu_open` guard wasn't set until the *deferred* `_do_open_menu` ran a frame
later, so a fast double-tap could pass the guard twice. Each pass creates its own
`_DropdownMenu`, which adds its own always-touch-consuming `_MenuDim` straight to
`Window`; only the most recent one is ever tracked for cleanup, so the other lives
forever, silently eating every touch on screen — looks exactly like a freeze. Fixed by
setting the guard synchronously, plus a defensive sweep in `_close_menu` for any stray
`_MenuDim` regardless of how it got there. Full writeup in CLAUDE.md's Gotchas section.
**This is the kind of bug code review alone would not have caught** — it required an
actual repro + a live logcat capture timed against the tap.

**Background contrast tension — resolved, but took ~4 iterations.** User wanted the
details panel genuinely light ("light light blue"), not just "less dark." White text
fundamentally cannot sit on a background that light at readable contrast (verified with
WCAG luminance math, documented in DESIGN.md). Landed on: details panel goes fully light
(`#B3D4F2`), and every label/icon/accent color inside it flips from white to dark navy
(`rgb(0.07, 0.14, 0.26)`) — not just a tint tweak, an actual theme flip across
`hourly_card.py`, `daily_forecast.py`, and `detail_cards.py` (with explicit exclusions for
the AlertBanner's red background and the `_SlideUpModal` detail popups, which both keep
white text since they're not on the light panel). The hero card was NOT touched — it
still uses white text on its own gradient/photo system. See DESIGN.md for the two-theme
rationale; this is a real ongoing maintenance hazard (a new card added without checking
which "zone" it's in could end up invisible) worth a code-level guard eventually.

**Hero background reverted from photo back to gradient.** The v1.1.0 photo + flat dark
scrim read as too dark on-device regardless of condition. Replaced with the same
gradient-texture technique the old (and now-deleted) `WeatherBackground` widget used,
inlined directly in `WeatherDetailWidget` via `_make_gradient_texture()`. Only the
`clear` day gradient was relightened (light blue top matching the details panel, fading
to a deeper blue bottom) per explicit request; other conditions keep their original
gradients since they weren't reported as a problem.

**"Clear Sky" centering bug — actually two bugs, not one.** The first attempted fix
(centering via `size_hint=(1,1)` + `halign='center'`, icon positioned from `texture_size`)
still shipped broken: the label had no `pos_hint`, so it sat at literal `(0,0)` and got
clipped by the hero's stencil mask (invisible), and the icon's fallback width estimate
(used whenever `texture_size` wasn't ready) was 40% of the *entire row width* instead of
the actual text width, sending it far off-screen. Rewritten to auto-size the label to its
own texture and read back its real `.x` for icon placement — no more guessing. Same
technique applied to the new degree-symbol-excluded-from-centering request on the hero
temperature. Full pattern documented in CLAUDE.md's Gotchas section so it doesn't get
reinvented (incorrectly) again.

**Nowcast card removed entirely**, per direct feedback that it didn't add useful
information over the hourly strip + daily precip%. Removed the UI card, the
`NowcastEntry` model, the `WeatherData.nowcast` field, and the `minutely_15` API params
— not just hidden from view.

**New finding: `AddLocationScreen` is dead code.** `main.py` imports it and has
`_on_first_location_added`/`_on_add_requested` methods referencing it, but
`_build_main_screens` (the actual startup path) never instantiates it — the search bar
built into `LocationListScreen` is the real add-location path and has been for at least
since v1.1.0. Not removed this session (out of scope for what was asked), flagged in
CLAUDE.md and here for a future cleanup pass.

**Dead code removed:** `weather_bg.py` (`WeatherBackground` — fully superseded, confirmed
zero references beyond its own file and stale comments) and `_DayIcon` (see above).

---

## Full Product Review

### Architecture — sound, with a few seams

- The hero gradient + `WeatherOverlay` particle system ([weather_overlay.py](src/widgets/weather_overlay.py))
  is genuinely good — diagonal rain at a real angle, lightning flash timing, sun glow
  layers, cloud wisps. This is *already* most of the "nice background animation" the
  long-term ask wants. It's underused: it only renders on the hero card behind the
  temperature, never anywhere else.
- ~~`weather_bg.py` dead code~~ — **deleted 2026-06-17.** Confirmed zero references
  beyond its own file.
- ~~Units (°F/°C) display-layer-only~~ — **fixed 2026-06-17.** `src/utils/units.py` is now
  the single source of truth, threaded through every screen that shows a temperature.
- `DetailCardsGrid` does real, useful synthesis (pressure trend, feels-like reason,
  visibility description) — this is the kind of thing that makes an app feel smart
  instead of just a data dump. Good bones to build on.
- New finding: `AddLocationScreen` (`src/screens/add_location.py`) is dead code —
  `main.py` references it but never instantiates it. The list screen's search bar is
  the real add-location path. Not removed yet — flagged for a future cleanup pass.

### Performance / efficiency

- Each `WeatherDetailWidget._build()` constructs dozens of widgets with per-instance
  `canvas.before` stencil/rounded-rect setups and lambda-bound redraw callbacks. Fine at
  1-3 locations; would get noticeably heavier with many saved locations since every
  carousel slide builds eagerly on add (`WeatherCarouselScreen` builds all slides up
  front, not lazily). Not a problem today — worth a lazy-build-on-`current_slide` pass
  if location count grows.
- `HourlySlot` and the daily `_DayRow` both use `Clock.schedule_once(self._build, 0)`
  per-instance — for 24 hourly entries that's 24 deferred callbacks every time a
  location's weather updates. Works, but a direct synchronous build (no Clock indirection)
  would be simpler and marginally cheaper; the one-frame defer pattern seems to exist out
  of caution rather than necessity here.
- Weather cache TTL is 10 minutes with no background refresh — data goes stale silently
  until the user reopens the screen. A lightweight `Clock.schedule_interval` refresh
  while the carousel is foregrounded (only for the visible slide) would keep nowcast/alerts
  meaningfully fresh without extra battery cost of polling all locations.
- Network calls (forecast, air quality, NWS alerts) run sequentially per location, not
  batched — fine for 1-3 locations, would add up for many. Not urgent.

### UX polish — the gap to "10/10"

This is genuinely a strong scaffold with real iOS-faithful bones (floating cards, hero
photo+overlay, nowcast bars, AQI/UV scales, NWS alerts). The gap to "people actually
want to download this for free" is mostly in *feel*, not features:

1. **No onboarding / empty-state personality.** First launch drops a blank search bar
   with no explanation, no "use my location" option, no sample/placeholder state that
   sells what the app does. iOS Weather (and every well-reviewed weather app) leads with
   "use current location" via GPS — this app is ZIP-search only, US-only by extension
   (Nominatim/NWS are US-biased already). Geolocation permission + reverse-geocode would
   remove the single biggest first-run friction point.
2. **No haptic/motion feedback anywhere.** Card taps, "See More" reveals, the carousel
   arrows, unit toggle — all are silent, instant state changes. Even a 10–20ms Android
   vibration on tap + a subtle scale/opacity animation on press would make the whole app
   feel considered rather than functional. This is cheap to add (Kivy `Animation` is
   already imported in places) and disproportionately raises perceived quality.
3. **Carousel transitions are instant, not fluid.** Swipe is disabled entirely (arrow-tap
   only, by design per the code comment) — that's a defensible choice for a weather app,
   but the page-to-page transition itself has no animation; it's a hard cut. A short
   slide/fade (150–200ms) would feel a generation more polished for near-zero cost.
4. **Pull-to-refresh doesn't exist.** Every modern weather app supports drag-down-to-refresh
   on the main scroll. Right now refresh only happens via backgrounding/reopening (there
   isn't even a refresh item in the menu). This is a high-expectation gesture for the
   category — its absence will read as "incomplete" to anyone who's used any other
   weather app.
5. **Widgets / home screen presence is the single biggest growth lever for a weather app**
   and doesn't exist. Most people who download a weather app do it *specifically* for
   the home screen widget. This is a bigger lift on Kivy/Android (would likely need a
   native Android widget via a small Java/Kotlin shim + RemoteViews, outside the Python
   runtime) but is worth scoping explicitly rather than assuming it's out of reach —
   it's the difference between "an app I open" and "an app I forgot I installed."
6. **No notifications** (severe weather alerts already fetched from NWS but never pushed;
   daily summary notification is a near-zero-cost retention feature once a notification
   channel exists).
7. **Icon/condition legibility (this session's fix is a patch, not a cure).** The OWM-style
   icon set itself has a real limitation: drizzle (`09d`) and rain (`10d`) are nearly
   visually identical at any size — same cloud, near-identical raindrop arrangement — and
   the raindrop color (saturated blue) sits close in hue to the blue card background,
   so the *differentiating* element (not the cloud) has the weakest contrast. The glow
   plate added this session helps the cloud silhouette pop but doesn't fix the underlying
   asset ambiguity. Longer-term: either source a more distinct icon set, or recolor by
   condition (cooler blue for drizzle, deeper/more saturated for rain, keep thunderstorm's
   bolt as the only really-distinct one it already is).
8. **Long-term animated background ask (explicitly raised this session):** the
   `WeatherOverlay` system already does real particle work and is the right foundation —
   it just needs to be: (a) extended to subtly animate behind the *whole* details card,
   not just the hero, and/or (b) given parallax/depth (clouds at two speeds, rain at a
   slight perspective skew already exists) to read as "alive" rather than "decorative."
   iOS's own implementation is mostly the same idea — layered semi-transparent particles
   over a gradient/photo, not real physics — so this is achievable in Kivy without needing
   a different rendering approach, just more layers and longer iteration on timing/easing.
9. **No app icon / branding personality visible in repo beyond the generated placeholder**
   (`create_assets.py`) — worth a real pass once the UI itself is locked, since first
   impression in the Play Store / APK listing matters for "would a stranger download this."

### What's already good and shouldn't be second-guessed

- NWS alerts, moon phase (28-phase, not just 8) — these are details most free weather
  apps skip. Keep leaning into "does more than expected for free." (Nowcast was in this
  category too but got cut 2026-06-17 — see session notes above; doing more than
  expected only counts if the thing is actually useful, not just present.)
- Floating-card visual language is distinctive and on-brand for iOS fidelity without
  being a literal clone — now spans two deliberate themes (white-on-dark hero,
  dark-on-light details panel) rather than one flat dark scheme.
- `DetailCardsGrid`'s synthesized "why" text (feels-like reason, pressure trend, visibility
  description) is exactly the kind of thing that separates "shows numbers" from "explains
  weather." Worth extending to more cards (UV advice already does this).

---

## Game Plan

**Phase 1 — Fix what's broken — ✅ done 2026-06-17**
1. ~~°F/°C unit propagation~~ — fixed, `src/utils/units.py`.
2. ~~Location list dropdown menu freeze~~ — fixed, root cause was a guard-flag race
   (see session notes above and CLAUDE.md Gotchas).
3. ~~Delete dead `weather_bg.py`~~ — deleted.

New Phase 1 leftover, found during this pass: `AddLocationScreen` is also dead code
(see above) — small, low-risk cleanup, good candidate for next session's first item.

**Phase 2 — Cheap, high-perceived-value polish (not started)**
4. Pull-to-refresh on the details ScrollView.
5. Carousel page transition animation (slide/fade, ~150–200ms).
6. Haptic feedback + press-state animation on taps (cards, arrows, toggle, See More).
7. "Use my location" GPS option on first run / add-location flow.

**Phase 3 — Differentiation (not started)**
8. Daily summary + severe alert push notifications (NWS data already fetched — just
   needs a notification channel).
9. Icon legibility — recolor or re-source the rain/drizzle/thunderstorm icon set so
   each condition is identifiable by silhouette+color alone, not just by close reading.
10. Extend `WeatherOverlay`-style animation beyond the hero card.

**Phase 4 — Reach (not started)**
11. Home screen widget (native Android shim — separate scoping conversation, this is
    the biggest lift and biggest payoff item on the list).
12. App icon / store-listing polish pass.

**New since last pass:**
13. Clean up `AddLocationScreen` dead code (`add_location.py` + the unreachable methods
    in `main.py` that reference it).
14. Consider a code-level guard against the two-theme (white-on-dark hero /
    dark-on-light details panel) mixing incorrectly in a future card — e.g. shared
    color constants per zone instead of each widget file hardcoding its own.
