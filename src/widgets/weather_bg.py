"""Animated weather background widget.

Renders a condition-specific gradient with particle animations:
  - clear day:        spinning sun rays + pulsing core
  - clear night:      40 twinkling stars + crescent moon
  - partly cloudy:    sun/moon (partial) + 2 drifting clouds
  - overcast:         3 layered dark clouds
  - fog:              5 horizontal streaks drifting left/right
  - drizzle/rain:     dark cloud + falling rain streaks
  - snow:             cloud + drifting snowflakes
  - thunderstorm:     rain + periodic lightning flash
"""
import math
import random
from typing import Optional

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics.texture import Texture
from kivy.uix.widget import Widget

from src.utils.wmo_codes import get_condition, get_gradients, is_night


class WeatherBackground(Widget):
    def __init__(self, wmo_code: int = 0, **kwargs):
        super().__init__(**kwargs)
        self._code = wmo_code
        self._condition = get_condition(wmo_code)
        self._night = is_night()
        self._t = 0.0          # animation time accumulator
        self._lightning_t = 0.0
        self._lightning_on = False

        self._gradient_texture: Optional[Texture] = None
        self._particles: list = []

        self.bind(pos=self._rebuild, size=self._rebuild)
        Clock.schedule_interval(self._tick, 1 / 30)

    def update_condition(self, wmo_code: int) -> None:
        self._code = wmo_code
        self._condition = get_condition(wmo_code)
        self._night = is_night()
        self._particles = []
        self._gradient_texture = None
        if self.width > 1:
            self._rebuild()

    def _rebuild(self, *_):
        self._night = is_night()
        self._gradient_texture = self._make_gradient()
        self._particles = self._make_particles()
        self._redraw()

    def _make_gradient(self) -> Texture:
        top, bottom = get_gradients(self._code)
        size = 256
        buf = bytes([
            int((top[ch] * (1 - y / size) + bottom[ch] * (y / size)) * 255)
            for y in range(size)
            for ch in range(3)
        ])
        tex = Texture.create(size=(1, size), colorfmt='rgb')
        tex.blit_buffer(buf, bufferfmt='ubyte', colorfmt='rgb')
        tex.wrap = 'clamp_to_edge'
        return tex

    # ------------------------------------------------------------------
    # Particle initialisation
    # ------------------------------------------------------------------

    def _make_particles(self) -> list:
        c = self._condition
        w, h = self.width or Window.width, self.height or Window.height

        if c == 'clear' and not self._night:
            return self._sun_particles(w, h)
        if c == 'clear' and self._night:
            return self._star_particles(w, h, 40)
        if c == 'partly_cloudy' and not self._night:
            return self._sun_particles(w, h, small=True) + self._cloud_particles(w, h, 2)
        if c == 'partly_cloudy' and self._night:
            return self._star_particles(w, h, 15) + self._cloud_particles(w, h, 1)
        if c == 'overcast':
            return self._cloud_particles(w, h, 3, dark=True)
        if c == 'fog':
            return self._fog_particles(w, h)
        if c in ('drizzle', 'rain'):
            return self._cloud_particles(w, h, 1, dark=True) + self._rain_particles(w, h, 22)
        if c == 'heavy_rain':
            return self._cloud_particles(w, h, 1, dark=True) + self._rain_particles(w, h, 38)
        if c == 'snow':
            return self._cloud_particles(w, h, 1) + self._snow_particles(w, h, 18)
        if c == 'thunderstorm':
            return self._cloud_particles(w, h, 1, dark=True) + self._rain_particles(w, h, 28)
        return []

    def _sun_particles(self, w, h, small=False) -> list:
        cx, cy = w * 0.5, h * 0.72
        r = (28 if small else 42)
        rays = []
        for i in range(8):
            rays.append({'type': 'sun_ray', 'cx': cx, 'cy': cy, 'idx': i, 'r': r})
        return [{'type': 'sun_core', 'cx': cx, 'cy': cy, 'r': r}] + rays

    def _star_particles(self, w, h, count) -> list:
        return [
            {
                'type': 'star',
                'x': random.uniform(0.05, 0.95) * w,
                'y': random.uniform(0.1, 0.9) * h,
                'size': random.choice([2, 2, 3, 3, 4]),
                'phase': random.uniform(0, math.pi * 2),
                'speed': random.uniform(0.8, 2.5),
            }
            for _ in range(count)
        ]

    def _cloud_particles(self, w, h, count, dark=False) -> list:
        clouds = []
        positions = [(0.15, 0.80), (0.35, 0.70), (0.55, 0.75)]
        for i in range(min(count, 3)):
            rx, ry = positions[i]
            clouds.append({
                'type': 'cloud',
                'x': rx * w,
                'y': ry * h,
                'scale': 0.9 + i * 0.15,
                'dark': dark,
                'phase': random.uniform(0, math.pi * 2),
                'speed': random.uniform(1.5, 2.5),
            })
        return clouds

    def _fog_particles(self, w, h) -> list:
        return [
            {
                'type': 'fog',
                'y_frac': 0.3 + i * 0.12,
                'phase': i * 0.7,
                'speed': 1.5 + i * 0.4,
                'alpha': 0.20 + i * 0.05,
            }
            for i in range(5)
        ]

    def _rain_particles(self, w, h, count) -> list:
        return [
            {
                'type': 'rain',
                'x': (i * w / count) % w,
                'y': random.uniform(h * 0.25, h),
                'speed': random.uniform(220, 340),
                'length': random.randint(12, 20),
            }
            for i in range(count)
        ]

    def _snow_particles(self, w, h, count) -> list:
        return [
            {
                'type': 'snow',
                'x': random.uniform(0, w),
                'y': random.uniform(h * 0.25, h),
                'size': random.randint(4, 9),
                'speed_y': random.uniform(30, 70),
                'speed_x': random.uniform(-15, 15),
                'phase': random.uniform(0, math.pi * 2),
            }
            for _ in range(count)
        ]

    # ------------------------------------------------------------------
    # Animation tick
    # ------------------------------------------------------------------

    def _tick(self, dt: float):
        self._t += dt
        w, h = self.width, self.height
        if w < 1:
            return

        # Update particle positions
        for p in self._particles:
            if p['type'] == 'rain':
                p['y'] -= p['speed'] * dt
                if p['y'] < h * 0.2:
                    p['y'] = h + random.randint(0, 40)
                    p['x'] = random.uniform(0, w)
            elif p['type'] == 'snow':
                p['y'] -= p['speed_y'] * dt
                p['x'] += p['speed_x'] * dt * math.sin(self._t + p['phase'])
                if p['y'] < 0:
                    p['y'] = h
                    p['x'] = random.uniform(0, w)
                if p['x'] < 0 or p['x'] > w:
                    p['x'] = random.uniform(0, w)

        # Lightning logic
        if self._condition == 'thunderstorm':
            self._lightning_t += dt
            if not self._lightning_on and self._lightning_t > random.uniform(2.5, 5.0):
                self._lightning_on = True
                self._lightning_t = 0.0
            elif self._lightning_on and self._lightning_t > 0.15:
                self._lightning_on = False
                self._lightning_t = 0.0

        self._redraw()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _redraw(self, *_):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 1:
            return

        with self.canvas:
            # Gradient background
            Color(1, 1, 1, 1)
            if self._gradient_texture:
                Rectangle(texture=self._gradient_texture, pos=self.pos, size=(w, h))
            else:
                top, _ = get_gradients(self._code)
                Color(*top)
                Rectangle(pos=self.pos, size=(w, h))

            # Lightning flash overlay
            if self._lightning_on:
                Color(1, 1, 0.9, 0.18)
                Rectangle(pos=self.pos, size=(w, h))

            # Particles
            for p in self._particles:
                self._draw_particle(p, w, h)

    def _draw_particle(self, p: dict, w: float, h: float):
        t = self._t
        ptype = p['type']

        if ptype == 'sun_core':
            pulse = 0.85 + 0.15 * math.sin(t * 1.2)
            r = p['r'] * pulse
            Color(0.98, 0.75, 0.14, 1.0)
            Ellipse(pos=(p['cx'] - r + self.x, p['cy'] - r + self.y), size=(r*2, r*2))

        elif ptype == 'sun_ray':
            angle = t * 0.3 + p['idx'] * (math.pi / 4)
            inner = p['r'] + 6
            outer = p['r'] + 22
            x1 = p['cx'] + math.cos(angle) * inner + self.x
            y1 = p['cy'] + math.sin(angle) * inner + self.y
            x2 = p['cx'] + math.cos(angle) * outer + self.x
            y2 = p['cy'] + math.sin(angle) * outer + self.y
            Color(0.99, 0.89, 0.53, 0.80)
            Line(points=[x1, y1, x2, y2], width=2.5)

        elif ptype == 'star':
            alpha = 0.2 + 0.8 * (0.5 + 0.5 * math.sin(t * p['speed'] + p['phase']))
            Color(1, 1, 1, alpha)
            s = p['size']
            Ellipse(pos=(p['x'] - s/2 + self.x, p['y'] - s/2 + self.y), size=(s, s))

        elif ptype == 'cloud':
            drift = 6 * math.sin(t * 0.25 + p['phase'])
            cx = p['x'] + drift + self.x
            cy = p['y'] + self.y
            sc = p['scale']
            if p['dark']:
                Color(0.38, 0.45, 0.49, 0.92)
            else:
                Color(0.97, 0.98, 0.99, 0.88)
            self._draw_cloud(cx, cy, sc)

        elif ptype == 'fog':
            drift = 18 * math.sin(t * 0.2 + p['phase'])
            cy = p['y_frac'] * h + self.y
            alpha = p['alpha'] * (0.8 + 0.2 * math.sin(t * 0.3 + p['phase']))
            Color(0.80, 0.85, 0.88, alpha)
            Rectangle(pos=(self.x + drift, cy - 5), size=(w, 10))

        elif ptype == 'rain':
            Color(0.58, 0.76, 0.98, 0.75)
            x1 = p['x'] + self.x
            y1 = p['y'] + self.y
            Line(points=[x1, y1, x1 + 3, y1 + p['length']], width=1.2)

        elif ptype == 'snow':
            alpha = 0.7 + 0.3 * math.sin(t + p['phase'])
            Color(0.95, 0.97, 1.0, alpha)
            s = p['size']
            Ellipse(pos=(p['x'] - s/2 + self.x, p['y'] - s/2 + self.y), size=(s, s))

    def _draw_cloud(self, cx: float, cy: float, sc: float):
        """Draw a simple three-circle cloud shape."""
        # Bottom base
        bw, bh = 70 * sc, 20 * sc
        Rectangle(pos=(cx - bw/2, cy - bh/2), size=(bw, bh))
        # Left puff
        r1 = 18 * sc
        Ellipse(pos=(cx - bw/2 + 2*sc - r1, cy + bh/2 - r1*0.5), size=(r1*2, r1*2))
        # Right puff (larger)
        r2 = 22 * sc
        Ellipse(pos=(cx - r2 + 10*sc, cy + bh/2 - r2*0.4), size=(r2*2, r2*2))
