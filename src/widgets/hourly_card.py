"""Horizontal scrollable hourly forecast card."""
import math
from datetime import datetime

from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.clock import Clock

from kivy.uix.image import Image

from src.models.weather import HourlyEntry
from src.utils.wmo_codes import get_icon_path, is_night
from src.utils.units import fmt_temp

KV = """
<HourlyForecastCard>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(170)
    padding: [dp(14), dp(10), dp(14), dp(10)]
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: 0.05, 0.09, 0.16, 0.40
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16)]
        Color:
            rgba: 1, 1, 1, 0.22
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(16)]
            width: 1

<HourlySlot>:
    orientation: 'vertical'
    size_hint: None, 1
    width: dp(62)
    spacing: dp(3)
    padding: [dp(6), dp(6), dp(6), dp(6)]
"""

Builder.load_string(KV)


class HourlySlot(BoxLayout):
    def __init__(self, entry: HourlyEntry, is_now: bool = False, units: str = 'F', **kwargs):
        super().__init__(**kwargs)
        self._entry = entry
        self._is_now = is_now
        self._units = units
        Clock.schedule_once(self._draw, 0)

    def _draw(self, *_):
        from kivy.uix.label import Label
        entry = self._entry

        try:
            dt = datetime.fromisoformat(entry.time)
            h = dt.hour
            if self._is_now:
                time_str = 'NOW'
            else:
                ampm = 'AM' if h < 12 else 'PM'
                h12 = h % 12 or 12
                time_str = f'{h12}{ampm}'
        except Exception:
            time_str = 'NOW' if self._is_now else '?'

        # Highlight for NOW
        if self._is_now:
            with self.canvas.before:
                Color(1, 1, 1, 0.15)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])

        # Time label — larger, bold, white
        time_lbl = Label(
            text=time_str,
            font_size=sp(15),
            color=(1, 1, 1, 1),
            bold=True,
            size_hint_y=None,
            height=dp(20),
        )
        self.add_widget(time_lbl)

        try:
            dt_h = datetime.fromisoformat(entry.time).hour
            night = dt_h < 6 or dt_h >= 20
        except Exception:
            night = False
        icon_path = get_icon_path(entry.code, night)
        icon = Image(source=icon_path, size_hint=(1, None), height=dp(38))
        self.add_widget(icon)

        if entry.precip_prob > 0:
            pp_lbl = Label(
                text=f'{entry.precip_prob}%',
                font_size=sp(12),
                color=(0.55, 0.80, 1.0, 1.0),
                size_hint_y=None,
                height=dp(16),
            )
            self.add_widget(pp_lbl)
        else:
            self.add_widget(Widget(size_hint_y=None, height=dp(16)))

        # Temperature — large bold white, easy to read
        temp_lbl = Label(
            text=fmt_temp(entry.temp, self._units),
            font_size=sp(18),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(24),
        )
        self.add_widget(temp_lbl)


class _WeatherIconSmall(Widget):
    """Tiny canvas-based weather icon for the hourly strip."""
    def __init__(self, wmo_code: int = 0, **kwargs):
        super().__init__(**kwargs)
        self._code = wmo_code
        self._t = 0.0
        self.bind(pos=self._redraw, size=self._redraw)
        Clock.schedule_interval(self._tick, 1/20)

    def _tick(self, dt):
        self._t += dt
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 1:
            return
        cx, cy = self.x + w / 2, self.y + h / 2
        cond = get_condition(self._code)

        with self.canvas:
            if cond == 'clear':
                self._draw_sun(cx, cy, min(w, h) * 0.35)
            elif cond == 'partly_cloudy':
                self._draw_sun(cx + w*0.1, cy + h*0.12, min(w, h) * 0.22)
                self._draw_cloud(cx - w*0.05, cy - h*0.1, 0.65)
            elif cond in ('overcast', 'fog'):
                self._draw_cloud(cx, cy, 0.85, dark=True)
            elif cond in ('drizzle', 'rain'):
                self._draw_cloud(cx, cy + h*0.1, 0.80, dark=True)
                self._draw_rain_drops(cx, cy - h*0.1, 3)
            elif cond == 'heavy_rain':
                self._draw_cloud(cx, cy + h*0.1, 0.85, dark=True)
                self._draw_rain_drops(cx, cy - h*0.1, 5)
            elif cond == 'snow':
                self._draw_cloud(cx, cy + h*0.1, 0.80)
                self._draw_snow_dots(cx, cy - h*0.1, 4)
            elif cond == 'thunderstorm':
                self._draw_cloud(cx, cy + h*0.1, 0.85, dark=True)
                self._draw_lightning(cx, cy - h*0.05)

    def _draw_sun(self, cx, cy, r):
        Color(0.98, 0.85, 0.22, 1.0)
        for i in range(8):
            angle = self._t * 0.4 + i * math.pi / 4
            x1 = cx + math.cos(angle) * (r + 2)
            y1 = cy + math.sin(angle) * (r + 2)
            x2 = cx + math.cos(angle) * (r + 8)
            y2 = cy + math.sin(angle) * (r + 8)
            Line(points=[x1, y1, x2, y2], width=1.5)
        Ellipse(pos=(cx - r, cy - r), size=(r*2, r*2))

    def _draw_cloud(self, cx, cy, sc, dark=False):
        if dark:
            Color(0.40, 0.47, 0.52, 0.95)
        else:
            Color(0.92, 0.95, 0.98, 0.92)
        r = 10 * sc
        Rectangle(pos=(cx - 14*sc, cy - 6*sc), size=(28*sc, 12*sc))
        Ellipse(pos=(cx - 14*sc, cy - 1*sc), size=(r*2, r*2))
        Ellipse(pos=(cx - 2*sc, cy + 1*sc), size=(r*2.2, r*2.2))

    def _draw_rain_drops(self, cx, cy, count):
        Color(0.55, 0.75, 0.98, 0.85)
        for i in range(count):
            x = cx - (count * 4) + i * 8
            offset = (self._t * 80 + i * 15) % 12
            Line(points=[x, cy - offset + 4, x + 2, cy - offset + 10], width=1.2)

    def _draw_snow_dots(self, cx, cy, count):
        Color(0.92, 0.96, 1.0, 0.9)
        for i in range(count):
            x = cx - (count * 4) + i * 8
            offset = (self._t * 30 + i * 20) % 10
            Ellipse(pos=(x - 2, cy - offset), size=(4, 4))

    def _draw_lightning(self, cx, cy):
        Color(0.98, 0.95, 0.22, 0.90)
        Line(points=[cx, cy + 8, cx - 4, cy, cx + 2, cy, cx - 4, cy - 8], width=2)


class HourlyForecastCard(BoxLayout):
    def __init__(self, entries: list, first_is_now: bool = False,
                 summary: str = '', units: str = 'F', **kwargs):
        super().__init__(**kwargs)
        self._build(entries, first_is_now, summary, units)

    def _build(self, entries: list, first_is_now: bool, summary: str, units: str):
        from kivy.uix.label import Label as _Lbl

        # Summary text sits INSIDE the hourly card as its header — one unified card
        if summary:
            summary_lbl = _Lbl(
                text=summary,
                font_size=sp(14),
                bold=False,
                color=(1, 1, 1, 0.85),
                size_hint=(1, None),
                height=dp(32),
                halign='left',
                valign='middle',
                padding=[dp(8), 0],
            )
            summary_lbl.bind(size=summary_lbl.setter('text_size'))
            self.add_widget(summary_lbl)

        scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=0,
            size_hint=(1, 1),
        )
        row = BoxLayout(
            orientation='horizontal',
            size_hint_x=None,
            spacing=dp(4),
            padding=[dp(4), 0],
        )

        for i, entry in enumerate(entries):
            is_now = (i == 0 and first_is_now)
            slot = HourlySlot(entry=entry, is_now=is_now, units=units)
            row.add_widget(slot)

        row.width = (dp(58) + dp(4)) * len(entries) + dp(8)
        scroll.add_widget(row)
        self.add_widget(scroll)
