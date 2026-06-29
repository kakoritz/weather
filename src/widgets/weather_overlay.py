"""Weather particle overlays — transparent, animated.

Sits between the gradient background and the text layer.
All effects use semi-transparent geometry only — no cartoon icons.

  clear_day / sun        — glowing disc + 8 short tapered rays, slowly rotating
  sun_light (partly day) — same sun at lower opacity + soft cloud wisps drifting
  stars (night)          — twinkling white dots
  rain / drizzle / heavy — diagonal white streaks at 15 degrees
  thunderstorm           — heavy rain + rare white screen flash
  snow                   — small white dots drifting with sinusoidal sway
  fog                    — large radial mist halos, very low opacity
  none (overcast)        — gradient does the job, no overlay
"""
import math
import random

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget

_FPS = 30


def overlay_for_condition(condition_name: str) -> str:
    return {
        'clear':         'sun',
        'partly_cloudy': 'sun_light',
        'overcast':      'none',
        'fog':           'fog',
        'drizzle':       'drizzle',
        'rain':          'rain',
        'heavy_rain':    'heavy_rain',
        'snow':          'snow',
        'thunderstorm':  'thunderstorm',
    }.get(condition_name, 'none')


def overlay_for_night(condition_name: str, night: bool) -> str:
    ov = overlay_for_condition(condition_name)
    if night and ov in ('sun', 'sun_light', 'none'):
        return 'stars'
    return ov


# ─────────────────────────────────────────────────────────────────────────────

class WeatherOverlay(Widget):
    def __init__(self, overlay_type: str = 'none', density: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self._type = overlay_type
        self._density = density
        self._t = 0.0
        self._particles: list = []
        self._clock_ev = None
        self.bind(size=self._on_resize)

    def _on_resize(self, *_):
        if self.width < 10:
            return
        self._particles = _make_particles(self._type, self.width, self.height, self._density)
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
        self.canvas.clear()
        if self._type != 'none' and self.width > 10:
            with self.canvas:
                _draw(self._type, self._particles, self._t,
                      self.x, self.y, self.width, self.height)


# ─── particle factories ───────────────────────────────────────────────────────

def _make_particles(ptype, w, h, density=1.0):
    if ptype in ('rain', 'drizzle', 'heavy_rain', 'thunderstorm'):
        specs = {
            'drizzle':     (28,  (260, 350), (dp(8),  dp(12))),
            'rain':        (55,  (410, 530), (dp(13), dp(19))),
            'heavy_rain':  (85,  (510, 640), (dp(17), dp(24))),
            'thunderstorm':(80,  (490, 620), (dp(16), dp(23))),
        }
        n, (lo_s, hi_s), (lo_l, hi_l) = specs[ptype]
        n = max(1, round(n * density))
        return [{'x': random.uniform(0, w), 'y': random.uniform(0, h),
                 'speed': random.uniform(lo_s, hi_s),
                 'length': random.uniform(lo_l, hi_l),
                 'alpha': random.uniform(0.10, 0.22)}
                for _ in range(n)]

    if ptype == 'snow':
        n = max(1, round(55 * density))
        return [{'x': random.uniform(0, w), 'y': random.uniform(0, h),
                 'speed': random.uniform(28, 62),
                 'r': random.uniform(dp(1.5), dp(3.0)),
                 'alpha': random.uniform(0.25, 0.65),
                 'phase': random.uniform(0, math.pi * 2),
                 'sway': random.uniform(dp(16), dp(36))}
                for _ in range(n)]

    if ptype in ('sun', 'sun_light'):
        # Sun position: upper-right area so it doesn't cover city/temp text
        sun_x = w * 0.72
        sun_y = h * 0.68
        clouds = []
        if ptype == 'sun_light':
            # 2 soft cloud clusters that drift left→right
            for i in range(2):
                clouds.append({
                    'type': 'cloud',
                    'x': random.uniform(-w * 0.3, w * 0.5),
                    'y': random.uniform(h * 0.30, h * 0.75),
                    'speed': random.uniform(9, 17),
                    'alpha': random.uniform(0.07, 0.13),
                    'scale': random.uniform(0.9, 1.4),
                })
        return [{'type': 'sun', 'cx': sun_x, 'cy': sun_y}] + clouds

    if ptype == 'stars':
        n = max(1, round(48 * density))
        return [{'x': random.uniform(0.03, 0.97) * w,
                 'y': random.uniform(0.04, 0.96) * h,
                 'r': random.uniform(dp(0.7), dp(1.8)),
                 'phase': random.uniform(0, math.pi * 2),
                 'period': random.uniform(1.6, 4.2)}
                for _ in range(n)]

    if ptype == 'fog':
        # Radial mist halos — NOT horizontal bands
        n = max(1, round(7 * density))
        return [{'x': random.uniform(0.1, 0.9) * w,
                 'y': random.uniform(0.1, 0.9) * h,
                 'r': random.uniform(dp(70), dp(130)),
                 'vx': random.uniform(-6, 6),
                 'vy': random.uniform(-4, 4),
                 'alpha': random.uniform(0.04, 0.09)}
                for _ in range(n)]

    return []


# ─── per-frame update ─────────────────────────────────────────────────────────

def _update_particles(ptype, particles, dt, t, w, h):
    if ptype in ('rain', 'drizzle', 'heavy_rain', 'thunderstorm'):
        dx_ratio = math.tan(math.radians(15))
        for p in particles:
            p['y'] -= p['speed'] * dt
            p['x'] -= p['speed'] * dx_ratio * dt
            if p['y'] < -dp(28):
                p['y'] = h + random.uniform(0, dp(30))
                p['x'] = random.uniform(-w * 0.25, w * 1.25)

    elif ptype == 'snow':
        for p in particles:
            p['y'] -= p['speed'] * dt
            p['x'] += math.sin(t * 0.85 + p['phase']) * p['sway'] * dt
            if p['y'] < -dp(10):
                p['y'] = h + dp(10)
                p['x'] = random.uniform(0, w)

    elif ptype in ('sun', 'sun_light'):
        for p in particles:
            if p['type'] == 'cloud':
                p['x'] += p['speed'] * dt
                if p['x'] > w + dp(120):
                    p['x'] = -dp(140)
                    p['y'] = random.uniform(h * 0.30, h * 0.75)

    elif ptype == 'fog':
        for p in particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            # Soft bounce off edges
            if p['x'] < -p['r'] or p['x'] > w + p['r']:
                p['vx'] *= -1
            if p['y'] < -p['r'] or p['y'] > h + p['r']:
                p['vy'] *= -1


# ─── drawing ──────────────────────────────────────────────────────────────────

def _draw(ptype, particles, t, ox, oy, w, h):

    # ── Rain family ────────────────────────────────────────────────────────
    if ptype in ('rain', 'drizzle', 'heavy_rain', 'thunderstorm'):
        # Lightning flash
        if ptype == 'thunderstorm':
            cycle, phase = 5.8, (t % 5.8) / 5.8
            if phase < 0.026:
                fa = min(0.48, phase / 0.013 * 0.48)
                Color(1, 1, 1, fa); Rectangle(pos=(ox, oy), size=(w, h))
            elif phase < 0.048:
                fa = max(0, (0.048 - phase) / 0.022 * 0.48)
                Color(1, 1, 1, fa); Rectangle(pos=(ox, oy), size=(w, h))

        ang = math.radians(-15)
        cos_a, sin_a = math.cos(ang + math.pi/2), math.sin(ang + math.pi/2)
        lw = dp(0.7) if ptype == 'drizzle' else dp(1.1)
        for p in particles:
            dx, dy = cos_a * p['length'], sin_a * p['length']
            Color(1, 1, 1, p['alpha'])
            Line(points=[ox+p['x'], oy+p['y'],
                         ox+p['x']+dx, oy+p['y']+dy], width=lw)

    # ── Snow ──────────────────────────────────────────────────────────────
    elif ptype == 'snow':
        for p in particles:
            Color(1, 1, 1, p['alpha'])
            r = p['r']
            Ellipse(pos=(ox+p['x']-r, oy+p['y']-r), size=(r*2, r*2))

    # ── Sun (clear day / partly cloudy day) ───────────────────────────────
    elif ptype in ('sun', 'sun_light'):
        pulse = 0.93 + 0.07 * math.sin(t * 0.4)
        sun_alpha = 1.0 if ptype == 'sun' else 0.65

        for p in particles:
            if p['type'] == 'sun':
                _draw_sun(p['cx'] + ox, p['cy'] + oy, t, pulse, sun_alpha)
            elif p['type'] == 'cloud':
                _draw_cloud_wisp(ox + p['x'], oy + p['y'], p['scale'], p['alpha'])

    # ── Stars (night) ─────────────────────────────────────────────────────
    elif ptype == 'stars':
        for p in particles:
            alpha = 0.20 + 0.60 * (0.5 + 0.5 * math.sin(
                t / p['period'] * math.pi * 2 + p['phase']))
            Color(1, 1, 1, alpha)
            r = p['r']
            Ellipse(pos=(ox+p['x']-r, oy+p['y']-r), size=(r*2, r*2))

    # ── Fog ───────────────────────────────────────────────────────────────
    elif ptype == 'fog':
        for p in particles:
            # Soft radial halo using concentric rings
            for ring in range(4):
                scale = 1.0 + ring * 0.35
                fade = p['alpha'] * (1.0 - ring * 0.22)
                r = p['r'] * scale
                Color(1, 1, 1, fade)
                Ellipse(pos=(ox+p['x']-r, oy+p['y']-r), size=(r*2, r*2))


def _draw_sun(cx, cy, t, pulse, alpha_scale):
    """Draw a proper sun: layered glow + short tapered rays."""
    rot = t * 0.18   # very slow rotation

    # ── Outer glow rings ─────────────────────────────────────────
    for r_dp, a in [(dp(62), 0.04), (dp(46), 0.09), (dp(34), 0.18), (dp(24), 0.32)]:
        r = r_dp * pulse
        Color(1, 0.95, 0.70, a * alpha_scale)
        Ellipse(pos=(cx-r, cy-r), size=(r*2, r*2))

    # ── 8 short rays ─────────────────────────────────────────────
    inner_r = dp(19) * pulse
    outer_r = dp(34) * pulse
    ray_w   = dp(2.2)
    for i in range(8):
        angle = rot + i * (math.pi / 4)
        x1 = cx + math.cos(angle) * inner_r
        y1 = cy + math.sin(angle) * inner_r
        x2 = cx + math.cos(angle) * outer_r
        y2 = cy + math.sin(angle) * outer_r
        Color(1, 0.96, 0.72, 0.55 * alpha_scale)
        Line(points=[x1, y1, x2, y2], width=ray_w)

    # ── Core disc ────────────────────────────────────────────────
    core_r = dp(16) * pulse
    Color(1, 0.99, 0.90, 0.95 * alpha_scale)
    Ellipse(pos=(cx-core_r, cy-core_r), size=(core_r*2, core_r*2))
    # Inner bright centre
    c2 = dp(9) * pulse
    Color(1, 1, 0.97, 1.0 * alpha_scale)
    Ellipse(pos=(cx-c2, cy-c2), size=(c2*2, c2*2))


def _draw_cloud_wisp(cx, cy, scale, alpha):
    """Draw a soft cloud wisp: overlapping white ellipses, very translucent."""
    bw = dp(90) * scale
    bh = dp(42) * scale
    # Cluster of ellipses that together look like a soft cloud puff
    puffs = [
        (0,    0,    1.00, bw,    bh),
        (-0.38, 0.12, 0.72, bw*0.8, bh*0.8),
        ( 0.38, 0.08, 0.72, bw*0.8, bh*0.8),
        (-0.18,-0.18, 0.55, bw*0.6, bh*0.7),
        ( 0.20,-0.15, 0.55, bw*0.6, bh*0.7),
    ]
    for dx_f, dy_f, s, pw, ph in puffs:
        ex = cx + dx_f * bw - pw/2
        ey = cy + dy_f * bh - ph/2
        Color(1, 1, 1, alpha * s)
        Ellipse(pos=(ex, ey), size=(pw, ph))
