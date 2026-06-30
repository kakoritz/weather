"""10-day forecast card widget."""
from datetime import datetime

from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.clock import Clock

from kivy.uix.image import Image

from src.models.weather import DailyForecast
from src.utils.wmo_codes import get_icon_path
from src.utils.units import fmt_temp

KV = """
<DailyForecastCard>:
    orientation: 'vertical'
    size_hint_y: None
    padding: [dp(14), dp(12), dp(14), dp(8)]
    spacing: 0
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
"""
Builder.load_string(KV)

# Python weekday() returns 0=Mon..6=Sun — must match that order
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


class _DayRow(BoxLayout):
    def __init__(self, forecast: DailyForecast, day_label: str,
                 global_min: int, global_max: int, units: str = 'F', **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None,
                         height=dp(46), **kwargs)
        self._forecast = forecast
        self._day_label = day_label
        # Bar math stays in Fahrenheit — (x-min)/(max-min) is invariant under
        # the affine F->C conversion, so only the display strings need it.
        self._global_min = global_min
        self._global_max = global_max
        self._units = units
        Clock.schedule_once(self._build, 0)

    def _build(self, *_):
        f = self._forecast

        # Day name
        day_lbl = Label(
            text=self._day_label,
            font_size=sp(19),
            color=(1, 1, 1, 0.95),
            size_hint=(None, 1),
            width=dp(96),
            halign='left',
            valign='middle',
        )
        day_lbl.bind(size=day_lbl.setter('text_size'))
        self.add_widget(day_lbl)

        # Condition icon — official OWM PNG on a soft glow plate so pale
        # icons (drizzle/rain) don't wash out against the blue card behind them
        icon_wrap = FloatLayout(size_hint=(None, 1), width=dp(40))
        with icon_wrap.canvas.before:
            Color(1, 1, 1, 0.07)
            _glow = Ellipse(pos=(0, 0), size=(dp(38), dp(38)))

        def _update_glow(w, v, e=_glow):
            e.pos = (w.center_x - dp(19), w.center_y - dp(19))
        icon_wrap.bind(pos=_update_glow, size=_update_glow)
        icon = Image(
            source=get_icon_path(f.code, night=False),
            size_hint=(None, None), size=(dp(38), dp(38)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
        )
        icon_wrap.add_widget(icon)
        self.add_widget(icon_wrap)

        # Precip probability (0 shown as blank)
        if f.precip_prob > 0:
            pp = Label(
                text=f'{f.precip_prob}%',
                font_size=sp(14),
                color=(0.55, 0.80, 1.0, 1.0),
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
            text=fmt_temp(f.min_temp, self._units),
            font_size=sp(19),
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
            text=fmt_temp(f.max_temp, self._units),
            font_size=sp(19),
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
            # Colored portion — blue (cold) → yellow → orange → red (hot)
            r1 = (self._min - self._gmin) / span
            _stops = [
                (0.0,  (0.27, 0.50, 0.90)),
                (0.40, (0.95, 0.88, 0.20)),
                (0.70, (0.95, 0.50, 0.10)),
                (1.0,  (0.92, 0.15, 0.08)),
            ]
            rc, gc, bc = _stops[0][1]
            for si in range(len(_stops) - 1):
                t0, c0 = _stops[si]
                t1, c1 = _stops[si + 1]
                if r1 <= t1:
                    t = (r1 - t0) / (t1 - t0)
                    rc = c0[0] + t * (c1[0] - c0[0])
                    gc = c0[1] + t * (c1[1] - c0[1])
                    bc = c0[2] + t * (c1[2] - c0[2])
                    break
            Color(rc, gc, bc, 1.0)
            bar_w = max(dp(4), x_end - x_start)
            RoundedRectangle(
                pos=(self.x + x_start, self.center_y - bar_h / 2),
                size=(bar_w, bar_h),
                radius=[bar_h / 2],
            )


class DailyForecastCard(BoxLayout):
    def __init__(self, forecasts: list, units: str = 'F', **kwargs):
        super().__init__(**kwargs)
        self._build(forecasts, units)

    def _build(self, forecasts: list, units: str = 'F'):
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

        # Separator — keep named reference to avoid canvas.children[-1] pitfall
        sep = Widget(size_hint_y=None, height=dp(1))
        with sep.canvas:
            Color(1, 1, 1, 0.18)
            _sep_rect = Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda w, v, r=_sep_rect: setattr(r, 'pos', v))
        sep.bind(size=lambda w, v, r=_sep_rect: setattr(r, 'size', (v[0], 1)))
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
                units=units,
            )
            self.add_widget(row)

            if i < len(forecasts) - 1:
                divider = Widget(size_hint_y=None, height=dp(1))
                with divider.canvas:
                    Color(1, 1, 1, 0.10)
                    _div_rect = Rectangle(size=(1, 1))

                def _update_divider(w, v, r=_div_rect):
                    r.pos = v
                    r.size = (w.width, 1)

                divider.bind(pos=_update_divider, size=_update_divider)
                self.add_widget(divider)

        total_rows = len(forecasts)
        self.height = dp(12+8+20+1) + total_rows * dp(46) + (total_rows - 1) * dp(1) + dp(8)
