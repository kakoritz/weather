"""10-day forecast card widget."""
import math
from datetime import datetime

from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.clock import Clock

from src.models.weather import DailyForecast
from src.utils.wmo_codes import get_condition

KV = """
<DailyForecastCard>:
    orientation: 'vertical'
    size_hint_y: None
    padding: [dp(14), dp(12), dp(14), dp(8)]
    spacing: 0
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.22
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16)]
        Color:
            rgba: 1, 1, 1, 0.12
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(16)]
            width: 1
"""
Builder.load_string(KV)

DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']


class _DayRow(BoxLayout):
    def __init__(self, forecast: DailyForecast, day_label: str,
                 global_min: int, global_max: int, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None,
                         height=dp(46), **kwargs)
        self._forecast = forecast
        self._day_label = day_label
        self._global_min = global_min
        self._global_max = global_max
        Clock.schedule_once(self._build, 0)

    def _build(self, *_):
        f = self._forecast

        # Day name
        day_lbl = Label(
            text=self._day_label,
            font_size=sp(17),
            color=(1, 1, 1, 0.95),
            size_hint=(None, 1),
            width=dp(96),
            halign='left',
            valign='middle',
        )
        day_lbl.bind(size=day_lbl.setter('text_size'))
        self.add_widget(day_lbl)

        # Condition icon
        icon = _DayIcon(wmo_code=f.code, size_hint=(None, 1), width=dp(36))
        self.add_widget(icon)

        # Precip probability (0 shown as blank)
        if f.precip_prob > 0:
            pp = Label(
                text=f'{f.precip_prob}%',
                font_size=sp(12),
                color=(0.58, 0.78, 0.99, 1.0),
                size_hint=(None, 1),
                width=dp(38),
                halign='right',
                valign='middle',
            )
            pp.bind(size=pp.setter('text_size'))
            self.add_widget(pp)
        else:
            self.add_widget(Widget(size_hint=(None, 1), width=dp(38)))

        # Min temp
        min_lbl = Label(
            text=f'{f.min_temp}°',
            font_size=sp(17),
            color=(1, 1, 1, 0.55),
            size_hint=(None, 1),
            width=dp(40),
            halign='right',
            valign='middle',
        )
        min_lbl.bind(size=min_lbl.setter('text_size'))
        self.add_widget(min_lbl)

        # Temperature range bar
        bar = _TempRangeBar(
            min_temp=f.min_temp,
            max_temp=f.max_temp,
            global_min=self._global_min,
            global_max=self._global_max,
            size_hint=(1, None),
            height=dp(6),
        )
        bar_wrap = BoxLayout(size_hint=(1, 1), padding=[dp(6), 0])
        bar_wrap.add_widget(bar)
        self.add_widget(bar_wrap)

        # Max temp
        max_lbl = Label(
            text=f'{f.max_temp}°',
            font_size=sp(17),
            bold=True,
            color=(1, 1, 1, 0.95),
            size_hint=(None, 1),
            width=dp(40),
            halign='left',
            valign='middle',
        )
        max_lbl.bind(size=max_lbl.setter('text_size'))
        self.add_widget(max_lbl)


class _TempRangeBar(Widget):
    def __init__(self, min_temp, max_temp, global_min, global_max, **kwargs):
        super().__init__(**kwargs)
        self._min = min_temp
        self._max = max_temp
        self._gmin = global_min
        self._gmax = global_max
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 1:
            return
        span = max(1, self._gmax - self._gmin)
        x_start = (self._min - self._gmin) / span * w
        x_end = (self._max - self._gmin) / span * w
        bar_h = max(h, dp(5))

        # Background track
        with self.canvas:
            Color(1, 1, 1, 0.18)
            RoundedRectangle(
                pos=(self.x, self.center_y - bar_h / 2),
                size=(w, bar_h),
                radius=[bar_h / 2],
            )
            # Colored portion
            r1 = 0.22 + 0.78 * (self._min - self._gmin) / span  # cool → warm
            r2 = 0.22 + 0.78 * (self._max - self._gmin) / span
            Color(r1 * 0.5 + 0.3, 0.55, 1 - r1 * 0.6, 1.0)
            bar_w = max(dp(4), x_end - x_start)
            RoundedRectangle(
                pos=(self.x + x_start, self.center_y - bar_h / 2),
                size=(bar_w, bar_h),
                radius=[bar_h / 2],
            )


class _DayIcon(Widget):
    def __init__(self, wmo_code: int, **kwargs):
        super().__init__(**kwargs)
        self._code = wmo_code
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 1:
            return
        cond = get_condition(self._code)
        cx, cy = self.x + w/2, self.y + h/2

        with self.canvas:
            if cond == 'clear':
                Color(0.98, 0.85, 0.20, 1.0)
                r = min(w, h) * 0.32
                Ellipse(pos=(cx-r, cy-r), size=(r*2, r*2))
            elif cond == 'partly_cloudy':
                Color(0.98, 0.85, 0.20, 0.9)
                r = min(w, h) * 0.22
                Ellipse(pos=(cx-r+3, cy+2), size=(r*2, r*2))
                Color(0.90, 0.93, 0.96, 0.92)
                self._cloud(cx - 2, cy - 4, 0.55)
            elif cond in ('overcast', 'fog'):
                Color(0.55, 0.62, 0.67, 0.92)
                self._cloud(cx, cy, 0.75)
            elif cond in ('drizzle', 'rain', 'heavy_rain'):
                Color(0.38, 0.47, 0.55, 0.92)
                self._cloud(cx, cy + 4, 0.72)
                Color(0.55, 0.75, 0.98, 0.85)
                for i in range(3):
                    x = cx - 8 + i * 8
                    Line(points=[x, cy - 2, x + 2, cy - 9], width=1.3)
            elif cond == 'snow':
                Color(0.80, 0.87, 0.95, 0.90)
                self._cloud(cx, cy + 4, 0.72)
                Color(0.95, 0.97, 1.0, 0.9)
                for i in range(3):
                    Ellipse(pos=(cx - 9 + i*8 - 2, cy - 7), size=(4, 4))
            elif cond == 'thunderstorm':
                Color(0.28, 0.33, 0.38, 0.95)
                self._cloud(cx, cy + 4, 0.78)
                Color(0.98, 0.95, 0.20, 0.95)
                Line(points=[cx, cy+2, cx-3, cy-3, cx+1, cy-3, cx-4, cy-10], width=2)

    def _cloud(self, cx, cy, sc):
        Rectangle(pos=(cx - 14*sc, cy - 6*sc), size=(28*sc, 12*sc))
        Ellipse(pos=(cx - 14*sc, cy - 1*sc), size=(18*sc, 18*sc))
        Ellipse(pos=(cx - 4*sc, cy + 1*sc), size=(22*sc, 22*sc))


class DailyForecastCard(BoxLayout):
    def __init__(self, forecasts: list, **kwargs):
        super().__init__(**kwargs)
        self._build(forecasts)

    def _build(self, forecasts: list):
        if not forecasts:
            return

        global_min = min(f.min_temp for f in forecasts)
        global_max = max(f.max_temp for f in forecasts)

        # Section header
        from kivy.uix.label import Label
        header = Label(
            text='10-DAY FORECAST',
            font_size=sp(11),
            color=(1, 1, 1, 0.60),
            size_hint_y=None,
            height=dp(20),
            halign='left',
            valign='middle',
        )
        header.bind(size=header.setter('text_size'))
        self.add_widget(header)

        # Separator
        sep = Widget(size_hint_y=None, height=dp(1))
        with sep.canvas:
            Color(1, 1, 1, 0.18)
            Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda w, v: setattr(sep.canvas.children[-1], 'pos', v))
        sep.bind(size=lambda w, v: setattr(sep.canvas.children[-1], 'size', (v[0], 1)))
        self.add_widget(sep)

        for i, f in enumerate(forecasts):
            try:
                dt = datetime.fromisoformat(f.date + 'T12:00:00')
                label = 'Today' if i == 0 else DAYS[dt.weekday()]
            except Exception:
                label = f'Day {i+1}'

            row = _DayRow(
                forecast=f,
                day_label=label,
                global_min=global_min,
                global_max=global_max,
            )
            self.add_widget(row)

            if i < len(forecasts) - 1:
                divider = Widget(size_hint_y=None, height=dp(1))
                with divider.canvas:
                    Color(1, 1, 1, 0.10)
                    Rectangle(size=(1, 1))
                divider.bind(pos=lambda w, v: w.canvas.clear() or
                             w.canvas.add(Color(1,1,1,0.10)) or
                             w.canvas.add(Rectangle(pos=v, size=(w.width, 1))))
                self.add_widget(divider)

        total_rows = len(forecasts)
        self.height = dp(12+8+20+1) + total_rows * dp(46) + (total_rows - 1) * dp(1) + dp(8)
