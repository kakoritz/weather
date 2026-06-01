"""Weather particle overlays — transparent, animated, sits between background and text.

Every effect is drawn with semi-transparent white geometry (not icons, not cartoons):
  rain       — thin diagonal streaks at 15°, 12-18dp long, ~18% opacity
  drizzle    — sparser, shorter, slower rain
  heavy_rain — denser, longer, faster rain
  thunderstorm — heavy rain + rare full-screen white flash
  snow       — small circles drifting down with sinusoidal sway
  sun rays   — slow-rotating radial beams from upper area, ~5-8% opacity
  stars      — twinkling fixed dots (night conditions)
  fog        — wide slow-moving horizontal bands, ~8% opacity
  overcast   — no overlay (gradient does all the work)
"""
import math
import random

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget

_FPS = 30


# ─── Condition → overlay type ──────────────────────────────────────────────

def overlay_for_condition(condition_name: str) -> str:
    """Map wmo_codes.get_condition() result to overlay type."""
    mapping = {
        'clear':         'sun',
        'partly_cloudy': 'sun_light',
        'overcast':      'none',
        'fog':           'fog',
        'drizzle':       'drizzle',
        'rain':          'rain',
        'heavy_rain':    'heavy_rain',
        'snow':          'snow',
        'thunderstorm':  'thunderstorm',
    }
    return mapping.get(condition_name, 'none')


def overlay_for_night(condition_name: str, night: bool) -> str:
    ov = overlay_for_condition(condition_name)
    if night and ov in ('sun', 'sun_light', 'none'):
        return 'stars'
    return ov


# ─── Overlay widget ─────────────────────────────────────────────────────────

class WeatherOverlay(Widget):
    """Transparent widget that draws animated weather particles."""

    def __init__(self, overlay_type: str = 'none', **kwargs):
        super().__init__(**kwargs)
        self._type = overlay_type
        self._t = 0.0
        self._particles: list = []
        self._clock_ev = None
        self.bind(size=self._on_resize, pos=self._redraw)

    def _on_resize(self, *_):
        if self.width < 10:
            return
        self._particles = _make_particles(self._type, self.width, self.height)
        if self._clock_ev is None and self._type != 'none':
            self._clock_ev = Clock.schedule_interval(self._tick, 1 / _FPS)

    def on_parent(self, widget, parent):
        if parent is None and self._clock_ev:
            self._clock_ev.cancel()
            self._clock_ev = None

    def _tick(self, dt):
        self._t += dt
        _update_particles(self._type, self._particles, dt, self._t,
                          self.width, self.height)
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        if self._type == 'none' or not self._particles:
            return
        with self.canvas:
            _draw_particles(self._type, self._particles, self._t,
                            self.x, self.y, self.width, self.height)


# ─── Particle factories ─────────────────────────────────────────────────────

def _make_particles(ptype: str, w: float, h: float) -> list:
    if ptype in ('rain', 'drizzle', 'heavy_rain', 'thunderstorm'):
        counts = {'drizzle': 30, 'rain': 60, 'heavy_rain': 90, 'thunderstorm': 80}
        speeds = {'drizzle': (280, 360), 'rain': (420, 540),
                  'heavy_rain': (520, 650), 'thunderstorm': (500, 630)}
        lens   = {'drizzle': (dp(8), dp(12)), 'rain': (dp(12), dp(18)),
                  'heavy_rain': (dp(16), dp(22)), 'thunderstorm': (dp(15), dp(21))}
        n = counts[ptype]
        lo_s, hi_s = speeds[ptype]
        lo_l, hi_l = lens[ptype]
        return [{'x': random.uniform(0, w), 'y': random.uniform(0, h),
                 'speed': random.uniform(lo_s, hi_s),
                 'length': random.uniform(lo_l, hi_l),
                 'alpha': random.uniform(0.10, 0.22)}
                for _ in range(n)]

    if ptype == 'snow':
        return [{'x': random.uniform(0, w), 'y': random.uniform(0, h),
                 'speed': random.uniform(30, 65),
                 'r': random.uniform(dp(1.5), dp(3.0)),
                 'alpha': random.uniform(0.25, 0.65),
                 'phase': random.uniform(0, math.pi * 2),
                 'sway': random.uniform(dp(18), dp(38))}
                for _ in range(55)]

    if ptype in ('sun', 'sun_light'):
        n = 10 if ptype == 'sun' else 8
        return [{'angle_offset': i * (math.pi * 2 / n),
                 'alpha_base': random.uniform(0.04, 0.10 if ptype == 'sun' else 0.06)}
                for i in range(n)]

    if ptype == 'stars':
        return [{'x': random.uniform(0.04, 0.96) * w,
                 'y': random.uniform(0.06, 0.94) * h,
                 'r': random.uniform(dp(0.8), dp(1.8)),
                 'phase': random.uniform(0, math.pi * 2),
                 'period': random.uniform(1.8, 4.0)}
                for _ in range(45)]

    if ptype == 'fog':
        return [{'x': random.uniform(-w * 0.8, 0),
                 'y': random.uniform(h * 0.05, h * 0.90),
                 'speed': random.uniform(8, 18),
                 'alpha': random.uniform(0.06, 0.13),
                 'bw': random.uniform(w * 0.7, w * 1.3),
                 'bh': random.uniform(dp(35), dp(75))}
                for _ in range(5)]

    return []


# ─── Per-frame update ────────────────────────────────────────────────────────

def _update_particles(ptype, particles, dt, t, w, h):
    if ptype in ('rain', 'drizzle', 'heavy_rain', 'thunderstorm'):
        dx_per_unit = math.tan(math.radians(15))
        for p in particles:
            p['y'] -= p['speed'] * dt
            p['x'] -= p['speed'] * dx_per_unit * dt
            if p['y'] < -dp(25):
                p['y'] = h + random.uniform(0, dp(30))
                p['x'] = random.uniform(-w * 0.25, w * 1.25)

    elif ptype == 'snow':
        for p in particles:
            p['y'] -= p['speed'] * dt
            p['x'] += math.sin(t * 0.9 + p['phase']) * p['sway'] * dt
            if p['y'] < -dp(10):
                p['y'] = h + dp(10)
                p['x'] = random.uniform(0, w)

    elif ptype == 'fog':
        for p in particles:
            p['x'] += p['speed'] * dt
            if p['x'] > w + p['bw']:
                p['x'] = -p['bw'] * random.uniform(0.8, 1.4)
                p['y'] = random.uniform(h * 0.05, h * 0.90)


# ─── Canvas drawing ─────────────────────────────────────────────────────────

def _draw_particles(ptype, particles, t, ox, oy, w, h):
    """Draw all particles into the current canvas context."""

    # ── Rain family ──────────────────────────────────────────────────────────
    if ptype in ('rain', 'drizzle', 'heavy_rain', 'thunderstorm'):

        # Lightning flash (thunderstorm only)
        if ptype == 'thunderstorm':
            cycle = 5.5
            phase = (t % cycle) / cycle
            if phase < 0.025:
                fa = min(0.50, phase / 0.012 * 0.50)
                Color(1, 1, 1, fa)
                Rectangle(pos=(ox, oy), size=(w, h))
            elif phase < 0.045:
                fa = max(0, (0.045 - phase) / 0.020 * 0.50)
                Color(1, 1, 1, fa)
                Rectangle(pos=(ox, oy), size=(w, h))

        # Rain streaks — thin diagonal white lines
        angle = math.radians(-15)
        cos_a = math.cos(angle + math.pi / 2)
        sin_a = math.sin(angle + math.pi / 2)
        lw = dp(0.7) if ptype == 'drizzle' else dp(1.0)
        for p in particles:
            dx = cos_a * p['length']
            dy = sin_a * p['length']
            Color(1, 1, 1, p['alpha'])
            Line(points=[ox + p['x'], oy + p['y'],
                         ox + p['x'] + dx, oy + p['y'] + dy],
                 width=lw)

    # ── Snow ─────────────────────────────────────────────────────────────────
    elif ptype == 'snow':
        for p in particles:
            Color(1, 1, 1, p['alpha'])
            r = p['r']
            Ellipse(pos=(ox + p['x'] - r, oy + p['y'] - r), size=(r * 2, r * 2))

    # ── Sun rays ─────────────────────────────────────────────────────────────
    elif ptype in ('sun', 'sun_light'):
        # Rays originate from upper-centre of the card
        cx = ox + w * 0.50
        cy = oy + h * 0.82
        ray_len = max(w, h) * 1.5
        pulse = 0.5 + 0.5 * math.sin(t * 0.35)
        beam_half = math.radians(5)
        for p in particles:
            base_angle = p['angle_offset'] + t * 0.05
            alpha = p['alpha_base'] * (0.55 + 0.45 * pulse)
            Color(1, 0.97, 0.80, alpha)
            # Draw a thin beam (two lines bracketing the centre angle)
            for spread in (-beam_half, beam_half):
                a = base_angle + spread
                Line(points=[cx, cy,
                              cx + math.cos(a) * ray_len,
                              cy + math.sin(a) * ray_len],
                     width=dp(1.0))

    # ── Stars ─────────────────────────────────────────────────────────────────
    elif ptype == 'stars':
        for p in particles:
            alpha = 0.25 + 0.55 * (0.5 + 0.5 * math.sin(
                t / p['period'] * math.pi * 2 + p['phase']))
            Color(1, 1, 1, alpha)
            r = p['r']
            Ellipse(pos=(ox + p['x'] - r, oy + p['y'] - r), size=(r * 2, r * 2))

    # ── Fog ──────────────────────────────────────────────────────────────────
    elif ptype == 'fog':
        for p in particles:
            Color(1, 1, 1, p['alpha'])
            Rectangle(pos=(ox + p['x'], oy + p['y'] - p['bh'] / 2),
                      size=(p['bw'], p['bh']))
