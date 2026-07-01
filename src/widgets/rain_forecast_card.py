"""Rain Forecasted bar-chart card — shown when precipitation expected within 60 min."""
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

KV = """
<RainForecastedCard>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(142)
    padding: [dp(16), dp(14), dp(16), dp(10)]
    spacing: dp(4)
    canvas.before:
        Color:
            rgba: 0.06, 0.22, 0.55, 0.52
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16)]
        Color:
            rgba: 1, 1, 1, 0.18
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(16)]
            width: 1
"""
Builder.load_string(KV)


def rain_card_info(minutely: list) -> tuple:
    """Returns (subtitle, rain_start_min) or (None, -1) when no rain expected in 60 min."""
    if not minutely:
        return None, -1

    slots = minutely[:5]   # next 0, 15, 30, 45, 60 minutes

    if slots[0].precip_prob >= 40:
        stop = next((i for i, s in enumerate(slots) if s.precip_prob < 30), len(slots))
        duration = stop * 15
        sub = f'Rain for the next {duration} min' if duration < 60 else 'Rain throughout the hour'
        return sub, 0

    start = next((i for i, s in enumerate(slots) if s.precip_prob >= 40), None)
    if start is None:
        return None, -1
    return f'Rain starting in {start * 15} min', start * 15


def _interp_probs(minutely: list, n: int = 60) -> list:
    """Linear-interpolate 15-min precip_prob values to per-minute resolution."""
    probs = [e.precip_prob for e in minutely]
    result = []
    for i in range(n):
        idx = i // 15
        t = (i % 15) / 15.0
        if idx + 1 < len(probs):
            result.append(probs[idx] * (1 - t) + probs[idx + 1] * t)
        elif idx < len(probs):
            result.append(float(probs[idx]))
        else:
            result.append(0.0)
    return result


class _BarChart(Widget):
    def __init__(self, probs: list, **kwargs):
        super().__init__(**kwargs)
        self._probs = probs
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        if not self._probs or self.width < 1 or self.height < 1:
            return
        n = len(self._probs)
        bar_w = self.width / n
        with self.canvas:
            for i, prob in enumerate(self._probs):
                bar_h = max(dp(2), self.height * max(0, prob) / 100.0)
                Color(1, 1, 1, 0.82)
                Rectangle(
                    pos=(self.x + i * bar_w + 0.3, self.y),
                    size=(max(1, bar_w - 0.6), bar_h),
                )


class RainForecastedCard(BoxLayout):
    def __init__(self, minutely: list, **kwargs):
        super().__init__(**kwargs)
        self._minutely = minutely
        Clock.schedule_once(self._build, 0)

    def _build(self, *_):
        subtitle, _ = rain_card_info(self._minutely)
        if subtitle is None:
            self.height = 0
            self.opacity = 0
            return

        title = Label(
            text='Rain Forecasted',
            font_size=sp(17), bold=True, color=(1, 1, 1, 1),
            size_hint_y=None, height=dp(22),
            halign='left', valign='middle',
        )
        title.bind(size=title.setter('text_size'))
        self.add_widget(title)

        sub = Label(
            text=subtitle,
            font_size=sp(13), bold=False, color=(1, 1, 1, 0.75),
            size_hint_y=None, height=dp(18),
            halign='left', valign='middle',
        )
        sub.bind(size=sub.setter('text_size'))
        self.add_widget(sub)

        # Separator line
        sep = Widget(size_hint_y=None, height=dp(8))
        with sep.canvas:
            Color(1, 1, 1, 0.20)
            _sr = Rectangle(size=(1, 1))

        def _update_sep(w, v, r=_sr):
            r.pos = (w.x, w.y + dp(4))
            r.size = (w.width, dp(1))

        sep.bind(pos=_update_sep, size=_update_sep)
        self.add_widget(sep)

        # Bar chart
        probs = _interp_probs(self._minutely, 60)
        chart = _BarChart(probs=probs, size_hint=(1, None), height=dp(40))
        self.add_widget(chart)

        # X-axis labels: Now | 10m | 20m | 30m | 40m | 50m
        axis = BoxLayout(orientation='horizontal', size_hint=(1, None), height=dp(16))
        for i, txt in enumerate(['Now', '10m', '20m', '30m', '40m', '50m']):
            lbl = Label(
                text=txt, font_size=sp(10), color=(1, 1, 1, 0.50),
                size_hint=(1, 1),
                halign='left' if i == 0 else ('right' if i == 5 else 'center'),
                valign='top',
            )
            lbl.bind(size=lbl.setter('text_size'))
            axis.add_widget(lbl)
        self.add_widget(axis)
