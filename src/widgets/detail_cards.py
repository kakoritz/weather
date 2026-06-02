"""Detail information cards — 2-column grid below the forecast.

Cards: Air Quality, UV Index, Sunset/Sunrise, Wind, Rainfall,
       Feels Like, Humidity, Visibility, Pressure, Temperature Map (placeholder).
"""
import math
from datetime import datetime

from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle, Mesh
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.clock import Clock

from src.models.weather import (
    AirQualityData, WeatherData,
    wind_direction_label, pressure_trend, feels_like_reason, visibility_description,
)

KV = """
<_BaseCard>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(165)
    padding: [dp(14), dp(12)]
    spacing: dp(6)
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


def _card_title(text: str) -> Label:
    lbl = Label(
        text=text.upper(),
        font_size=sp(11),
        color=(1, 1, 1, 0.55),
        size_hint_y=None,
        height=dp(16),
        halign='left',
        valign='middle',
        bold=False,
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _card_value(text: str, size=sp(30)) -> Label:
    lbl = Label(
        text=text,
        font_size=size,
        bold=True,
        color=(1, 1, 1, 0.97),
        size_hint_y=None,
        height=dp(40),
        halign='left',
        valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _card_sub(text: str) -> Label:
    lbl = Label(
        text=text,
        font_size=sp(13),
        color=(1, 1, 1, 0.70),
        size_hint_y=None,
        height=dp(36),
        halign='left',
        valign='top',
        text_size=(None, None),
    )
    lbl.bind(size=lambda w, v: setattr(w, 'text_size', (v[0], None)))
    return lbl


class _BaseCard(BoxLayout):
    pass


def _see_more_footer(on_tap):
    """Footer button — 'See More  ›' tappable line at the bottom of a card."""
    from kivy.uix.boxlayout import BoxLayout as _BL
    row = _BL(orientation='horizontal', size_hint_y=None, height=dp(24))
    lbl = Label(text='See More  ›', font_size=sp(12), color=(1, 1, 1, 0.55),
                size_hint=(1, 1), halign='right', valign='middle')
    lbl.bind(size=lbl.setter('text_size'))
    row.add_widget(lbl)
    row.bind(on_touch_up=lambda w, t: on_tap() if w.collide_point(*t.pos) else None)
    return row


class _SlideUpModal(FloatLayout):
    """Dark gray panel that slides up from bottom (95% of screen height)."""

    def __init__(self, title: str, content_builder, **kwargs):
        super().__init__(size_hint=(1, 1), **kwargs)
        # Dim overlay
        dim = Widget(size_hint=(1, 1))
        with dim.canvas:
            Color(0, 0, 0, 0.55)
            _dim = Rectangle(pos=dim.pos, size=dim.size)
        dim.bind(pos=lambda w, v, r=_dim: setattr(r, 'pos', v),
                 size=lambda w, v, r=_dim: setattr(r, 'size', v))
        dim.bind(on_touch_down=lambda w, t: self._close() if w.collide_point(*t.pos) else None)
        self.add_widget(dim)

        # Panel
        panel = BoxLayout(orientation='vertical',
                          size_hint=(1, 0.95), pos_hint={'bottom': 1})
        with panel.canvas.before:
            Color(0.11, 0.13, 0.17, 1)
            RoundedRectangle(pos=panel.pos, size=panel.size, radius=[dp(20), dp(20), 0, 0])
        panel.bind(pos=lambda w, v: None)
        self.add_widget(panel)
        self._panel = panel

        # Header
        hdr = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52),
                        padding=[dp(20), 0])
        hdr.add_widget(Label(text=title, font_size=sp(18), bold=True,
                             color=(1, 1, 1, 0.95), size_hint=(1, 1),
                             halign='left', valign='middle'))
        from kivymd.uix.button import MDIconButton
        close_btn = MDIconButton(icon='close', theme_icon_color='Custom',
                                 icon_color=(1, 1, 1, 0.70), icon_size=dp(22),
                                 size_hint=(None, None), size=(dp(44), dp(44)),
                                 on_release=lambda *_: self._close())
        hdr.add_widget(close_btn)
        panel.add_widget(hdr)

        # Content
        from kivy.uix.scrollview import ScrollView
        sv = ScrollView(do_scroll_y=True, do_scroll_x=False, bar_width=0,
                        size_hint=(1, 1))
        inner = BoxLayout(orientation='vertical', size_hint_y=None,
                          padding=[dp(20), dp(8), dp(20), dp(40)])
        inner.bind(minimum_height=inner.setter('height'))
        content_builder(inner)
        sv.add_widget(inner)
        panel.add_widget(sv)

    def _close(self):
        parent = self.parent
        if parent:
            parent.remove_widget(self)

    @staticmethod
    def show(title: str, content_builder, target_widget):
        """Find the root FloatLayout parent and attach the modal there."""
        root = target_widget
        for _ in range(20):
            if root.parent is None:
                break
            root = root.parent
        modal = _SlideUpModal(title=title, content_builder=content_builder,
                              size_hint=(1, 1))
        root.add_widget(modal)


# ──────────────────────────────────────────────
# Air Quality
# ──────────────────────────────────────────────

class AirQualityCard(_BaseCard):
    def __init__(self, aq: AirQualityData, **kwargs):
        super().__init__(**kwargs)
        self._aq = aq
        self.add_widget(_card_title('Air Quality'))
        self.add_widget(_card_value(f'{aq.us_aqi} — {aq.category}', size=sp(22)))
        self.add_widget(_card_sub(aq.description))
        bar = _AQIBar(aqi=aq.us_aqi, size_hint=(1, None), height=dp(6))
        self.add_widget(bar)
        self.add_widget(_see_more_footer(self._open_detail))

    def _open_detail(self):
        aq = self._aq
        def build(box):
            stats = [
                ('US AQI',            f'{aq.us_aqi}',              aq.category),
                ('PM2.5',             f'{aq.pm2_5:.1f} µg/m³',     ''),
                ('PM10',              f'{aq.pm10:.1f} µg/m³',      ''),
                ('Ozone (O₃)',        f'{aq.ozone:.1f} µg/m³',     ''),
                ('Nitrogen Dioxide',  f'{aq.nitrogen_dioxide:.1f} µg/m³', ''),
            ]
            for name, val, note in stats:
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(46))
                row.add_widget(Label(text=name, font_size=sp(15), bold=False,
                                     color=(1, 1, 1, 0.75), size_hint=(1, 1),
                                     halign='left', valign='middle'))
                row.add_widget(Label(text=val + (f'  {note}' if note else ''),
                                     font_size=sp(15), bold=True, color=(1, 1, 1, 1),
                                     size_hint=(None, 1), width=dp(180),
                                     halign='right', valign='middle'))
                box.add_widget(row)
                box.add_widget(Widget(size_hint_y=None, height=dp(1)))
            box.add_widget(Label(
                text='Data: Open-Meteo Air Quality API',
                font_size=sp(11), color=(1, 1, 1, 0.30),
                size_hint_y=None, height=dp(30),
                halign='center', valign='middle',
            ))
        _SlideUpModal.show('Air Quality', build, self)


class _AQIBar(Widget):
    def __init__(self, aqi: int, **kwargs):
        super().__init__(**kwargs)
        self._aqi = aqi
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 1:
            return
        # Gradient bar: green → yellow → orange → red → purple → maroon
        # Draw as 6 colored segments
        colors = [
            (0.00, 0.89, 0.00),
            (1.00, 1.00, 0.00),
            (1.00, 0.49, 0.00),
            (1.00, 0.00, 0.00),
            (0.56, 0.25, 0.59),
            (0.49, 0.00, 0.14),
        ]
        seg_w = w / len(colors)
        with self.canvas:
            for i, c in enumerate(colors):
                Color(*c, 0.85)
                x = self.x + i * seg_w
                if i == 0:
                    RoundedRectangle(pos=(x, self.y), size=(seg_w, h), radius=[h/2, 0, 0, h/2])
                elif i == len(colors) - 1:
                    RoundedRectangle(pos=(x, self.y), size=(seg_w, h), radius=[0, h/2, h/2, 0])
                else:
                    Rectangle(pos=(x, self.y), size=(seg_w, h))

            # Marker dot
            marker_x = min(self._aqi / 300.0, 1.0) * w
            Color(1, 1, 1, 1)
            r = h * 0.9
            Ellipse(pos=(self.x + marker_x - r, self.y + h/2 - r), size=(r*2, r*2))


# ──────────────────────────────────────────────
# UV Index
# ──────────────────────────────────────────────

class UVIndexCard(_BaseCard):
    def __init__(self, uv: float, **kwargs):
        super().__init__(**kwargs)
        label = _uv_label(uv)
        self.add_widget(_card_title('UV Index'))
        self.add_widget(_card_value(f'{int(uv)}'))
        self.add_widget(Label(
            text=label,
            font_size=sp(18),
            bold=True,
            color=(1, 1, 1, 0.90),
            size_hint_y=None,
            height=dp(24),
            halign='left',
            valign='middle',
        ))
        bar = _UVBar(uv=uv, size_hint=(1, None), height=dp(6))
        self.add_widget(bar)
        advice = _uv_advice(uv)
        self.add_widget(_card_sub(advice))


def _uv_label(uv: float) -> str:
    if uv <= 2:   return 'Low'
    if uv <= 5:   return 'Moderate'
    if uv <= 7:   return 'High'
    if uv <= 10:  return 'Very High'
    return 'Extreme'


def _uv_advice(uv: float) -> str:
    if uv <= 2:   return 'No protection needed.'
    if uv <= 5:   return 'Use sun protection 10AM–4PM.'
    if uv <= 7:   return 'SPF 30+ and hat recommended.'
    if uv <= 10:  return 'Reduce time in sun 10AM–4PM.'
    return 'Avoid sun during midday hours.'


class _UVBar(Widget):
    def __init__(self, uv: float, **kwargs):
        super().__init__(**kwargs)
        self._uv = uv
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 1:
            return
        colors = [(0.00, 0.89, 0.00), (1.00, 1.00, 0.00), (1.00, 0.49, 0.00),
                  (1.00, 0.00, 0.00), (0.56, 0.00, 0.56)]
        seg_w = w / len(colors)
        with self.canvas:
            for i, c in enumerate(colors):
                Color(*c, 0.85)
                RoundedRectangle(
                    pos=(self.x + i*seg_w, self.y),
                    size=(seg_w, h),
                    radius=[h/2 if i==0 else 0, h/2 if i==len(colors)-1 else 0,
                            h/2 if i==len(colors)-1 else 0, h/2 if i==0 else 0],
                )
            # Marker
            mx = min(self._uv / 11.0, 1.0) * w
            Color(1, 1, 1, 1)
            r = h * 0.9
            Ellipse(pos=(self.x + mx - r, self.y + h/2 - r), size=(r*2, r*2))


# ──────────────────────────────────────────────
# Sunset / Sunrise
# ──────────────────────────────────────────────

class SunsetCard(_BaseCard):
    def __init__(self, sunset: str, sunrise: str, progress: float, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(165)
        self.add_widget(_card_title('Sunset'))
        self.add_widget(_card_value(sunset or '—', size=sp(34)))
        arc = _SunArc(progress=progress, size_hint=(1, None), height=dp(70))
        self.add_widget(arc)
        self.add_widget(Label(
            text=f'Sunrise: {sunrise or "—"}',
            font_size=sp(13),
            color=(1, 1, 1, 0.65),
            size_hint_y=None,
            height=dp(18),
            halign='left',
            valign='middle',
        ))


class _SunArc(Widget):
    def __init__(self, progress: float, **kwargs):
        super().__init__(**kwargs)
        self._progress = progress
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 1:
            return
        cx, cy = self.x + w / 2, self.y + 8
        rx, ry = w * 0.42, h * 0.85

        with self.canvas:
            # Arc path (semicircle)
            Color(1, 1, 1, 0.25)
            points = []
            for deg in range(0, 181, 4):
                rad = math.radians(deg)
                px = cx + math.cos(math.pi - rad) * rx
                py = cy + math.sin(rad) * ry
                points.extend([px, py])
            Line(points=points, width=1.5)

            # Sun dot on arc
            p = max(0.0, min(1.0, self._progress))
            rad = math.radians(p * 180)
            sx = cx + math.cos(math.pi - rad) * rx
            sy = cy + math.sin(rad) * ry
            Color(0.98, 0.88, 0.22, 1.0)
            Ellipse(pos=(sx - 6, sy - 6), size=(12, 12))
            Color(0.99, 0.93, 0.60, 0.45)
            Ellipse(pos=(sx - 10, sy - 10), size=(20, 20))


# ──────────────────────────────────────────────
# Wind
# ──────────────────────────────────────────────

class WindCard(_BaseCard):
    def __init__(self, speed: int, direction_deg: int, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(165)
        label = wind_direction_label(direction_deg)
        self.add_widget(_card_title('Wind'))

        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(80))
        compass = _WindCompass(deg=direction_deg, size_hint=(None, 1), width=dp(80))
        row.add_widget(compass)

        info = BoxLayout(orientation='vertical', size_hint=(1, 1))
        info.add_widget(_card_value(f'{speed}', size=sp(32)))
        info.add_widget(Label(
            text='mph',
            font_size=sp(14),
            color=(1, 1, 1, 0.65),
            size_hint_y=None,
            height=dp(20),
            halign='left',
            valign='middle',
        ))
        info.add_widget(Label(
            text=label,
            font_size=sp(16),
            color=(1, 1, 1, 0.80),
            size_hint_y=None,
            height=dp(22),
            halign='left',
            valign='middle',
        ))
        row.add_widget(info)
        self.add_widget(row)


class _WindCompass(Widget):
    """Proper compass rose with tick marks, N/S/E/W labels, and arrow needle."""
    def __init__(self, deg: int, **kwargs):
        super().__init__(**kwargs)
        self._deg = deg
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 1:
            return
        cx, cy = self.x + w/2, self.y + h/2
        r = min(w, h) / 2 - dp(6)

        with self.canvas:
            # Outer ring
            Color(1, 1, 1, 0.18)
            Line(circle=(cx, cy, r), width=1.5)
            # Inner ring
            Color(1, 1, 1, 0.08)
            Line(circle=(cx, cy, r * 0.6), width=1)

            # Cardinal tick marks
            for i in range(12):
                angle = math.radians(i * 30)
                is_cardinal = (i % 3 == 0)
                inner = r * (0.78 if is_cardinal else 0.85)
                outer = r * 0.98
                Color(1, 1, 1, 0.60 if is_cardinal else 0.25)
                x1 = cx + math.cos(angle) * inner
                y1 = cy + math.sin(angle) * inner
                x2 = cx + math.cos(angle) * outer
                y2 = cy + math.sin(angle) * outer
                Line(points=[x1, y1, x2, y2], width=1.5 if is_cardinal else 0.8)

            # N marker (top = 90° in screen coords = 270° math)
            north_r = r * 0.62
            Color(0.95, 0.30, 0.30, 1.0)
            Ellipse(pos=(cx - dp(5), cy + north_r - dp(5)), size=(dp(10), dp(10)))

            # Direction needle — pointer triangle
            needle_angle = math.radians(self._deg - 90)  # screen coords
            tip_r = r * 0.72
            base_r = dp(5)
            tx = cx + math.cos(needle_angle) * tip_r
            ty = cy + math.sin(needle_angle) * tip_r
            # Two base points perpendicular to needle
            perp = needle_angle + math.pi / 2
            bx1 = cx + math.cos(perp) * base_r
            by1 = cy + math.sin(perp) * base_r
            bx2 = cx - math.cos(perp) * base_r
            by2 = cy - math.sin(perp) * base_r
            Color(0.98, 0.92, 0.25, 1.0)
            Line(points=[bx1, by1, tx, ty, bx2, by2, bx1, by1], width=1.8)

            # Tail (opposite direction, shorter)
            tail_r = r * 0.30
            tail_x = cx - math.cos(needle_angle) * tail_r
            tail_y = cy - math.sin(needle_angle) * tail_r
            Color(1, 1, 1, 0.45)
            Line(points=[cx, cy, tail_x, tail_y], width=1.5)

            # Centre dot
            Color(1, 1, 1, 0.95)
            Ellipse(pos=(cx - dp(3.5), cy - dp(3.5)), size=(dp(7), dp(7)))


# ──────────────────────────────────────────────
# Rainfall
# ──────────────────────────────────────────────

class RainfallCard(_BaseCard):
    def __init__(self, last_24h: float, next_24h: float, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(_card_title('Rainfall'))
        self.add_widget(_card_value(f'{last_24h:.2f}"'))
        self.add_widget(_card_sub('in last 24 hours'))
        self.add_widget(_card_sub(f'{next_24h:.2f}" expected in next 24h.'))


# ──────────────────────────────────────────────
# Feels Like
# ──────────────────────────────────────────────

class FeelsLikeCard(_BaseCard):
    def __init__(self, feels: int, actual: int, humidity: int, wind: int, **kwargs):
        super().__init__(**kwargs)
        reason = feels_like_reason(feels, actual, humidity, wind)
        self.add_widget(_card_title('Feels Like'))
        self.add_widget(_card_value(f'{feels}°'))
        self.add_widget(_card_sub(reason))


# ──────────────────────────────────────────────
# Humidity
# ──────────────────────────────────────────────

class HumidityCard(_BaseCard):
    def __init__(self, humidity: int, dew_point: int, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(_card_title('Humidity'))
        self.add_widget(_card_value(f'{humidity}%'))
        self.add_widget(_card_sub(f'The dew point is {dew_point}° right now.'))


# ──────────────────────────────────────────────
# Visibility
# ──────────────────────────────────────────────

class VisibilityCard(_BaseCard):
    def __init__(self, miles: float, **kwargs):
        super().__init__(**kwargs)
        desc = visibility_description(miles)
        self.add_widget(_card_title('Visibility'))
        self.add_widget(_card_value(f'{min(miles, 10):.0f} mi'))
        self.add_widget(_card_sub(desc))


# ──────────────────────────────────────────────
# Pressure
# ──────────────────────────────────────────────

class PressureCard(_BaseCard):
    def __init__(self, pressure_hpa: float, trend: str, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(165)
        inhg = pressure_hpa * 0.02953
        self.add_widget(_card_title('Pressure'))
        gauge = _PressureGauge(inhg=inhg, size_hint=(1, None), height=dp(80))
        self.add_widget(gauge)
        self.add_widget(_card_sub(trend))


class _PressureGauge(Widget):
    def __init__(self, inhg: float, **kwargs):
        super().__init__(**kwargs)
        self._inhg = inhg
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        w, h = self.width, self.height
        if w < 1:
            return
        cx, cy = self.x + w/2, self.y + h * 0.25
        r = min(w, h) * 0.7

        # Pressure range: 28.0–31.0 inHg maps to 0–1
        p = max(0.0, min(1.0, (self._inhg - 28.0) / 3.0))
        # Arc from -200° to 20° (240° sweep), mapped to pressure
        start_deg = 200
        sweep = 140 * p - 70  # -70 (low) to +70 (high)
        needle_deg = 90 + sweep

        with self.canvas:
            # Arc background
            Color(1, 1, 1, 0.18)
            for deg in range(200, -21, -4):
                rad = math.radians(deg)
                px = cx + math.cos(rad) * r
                py = cy + math.sin(rad) * r
                if deg == 200:
                    prev = (px, py)
                    continue
                Line(points=[prev[0], prev[1], px, py], width=2)
                prev = (px, py)

            # Needle
            rad = math.radians(needle_deg)
            nx = cx + math.cos(rad) * r * 0.8
            ny = cy + math.sin(rad) * r * 0.8
            Color(1, 1, 1, 0.90)
            Line(points=[cx, cy, nx, ny], width=2)

            # Value text (drawn as label — we'll add outside)
            Color(1, 1, 1, 0.95)
            Ellipse(pos=(cx - 4, cy - 4), size=(8, 8))

        # Add value label
        from kivy.uix.label import Label
        if not self.children:
            lbl = Label(
                text=f'{self._inhg:.2f}\ninHg',
                font_size=sp(16),
                bold=True,
                color=(1, 1, 1, 0.95),
                halign='center',
                valign='middle',
                pos=(cx - dp(30) - self.x, cy - dp(14) - self.y),
                size=(dp(60), dp(28)),
            )
            self.add_widget(lbl)


# ──────────────────────────────────────────────
# Temperature Map (placeholder v1)
# ──────────────────────────────────────────────

class TemperatureMapCard(_BaseCard):
    def __init__(self, lat: float = 35.37, lon: float = -81.96,
                 city: str = '', temp: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.height = dp(165)
        self._lat = lat
        self._lon = lon
        self._city = city
        self._temp = temp

        self.add_widget(_card_title('Temperature'))

        # Map preview (gradient placeholder — tappable)
        preview = Widget(size_hint=(1, 1))
        with preview.canvas:
            # Temperature gradient: blue (cold) → yellow → red (hot)
            for i, col in enumerate([(0.25,0.55,0.90), (0.35,0.75,0.50),
                                      (0.90,0.80,0.20), (0.95,0.40,0.15)]):
                Color(*col, 0.6)
                RoundedRectangle(pos=(0, 0), size=(1, 1), radius=[dp(6)])
        preview.bind(pos=lambda w, v: None, size=lambda w, v: None)
        preview.add_widget(Label(
            text=f'{city}\n{temp}°',
            font_size=sp(13), color=(1, 1, 1, 0.70),
            halign='center', valign='middle', size_hint=(1, 1),
        ))
        preview.bind(on_touch_up=lambda w, t: self._open_map()
                     if w.collide_point(*t.pos) else None)
        self.add_widget(preview)
        self.add_widget(_see_more_footer(self._open_map))

    def _open_map(self):
        def build(box):
            box.add_widget(Label(
                text=(
                    'Temperature Map\n\n'
                    'Full interactive heat map coming in v1.2\n\n'
                    f'Current location:\n{self._city}\n'
                    f'Lat {self._lat:.2f}, Lon {self._lon:.2f}'
                ),
                font_size=sp(15), color=(1, 1, 1, 0.80),
                halign='center', valign='top',
                size_hint_y=None, height=dp(220),
            ))
        _SlideUpModal.show('Temperature', build, self)


# ──────────────────────────────────────────────
# Main grid assembler
# ──────────────────────────────────────────────

class DetailCardsSection(BoxLayout):
    """Full-width cards (AQ, Temp Map) followed by 2-col grid of smaller cards."""

    def __init__(self, data: WeatherData, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None,
                         spacing=dp(10), **kwargs)
        self.bind(minimum_height=self.setter('height'))
        self._build(data)

    def _build(self, data: WeatherData):
        c = data.current
        today = data.daily[0] if data.daily else None

        # ── FULL-WIDTH cards ──────────────────────────────────────────
        if data.air_quality:
            self.add_widget(AirQualityCard(aq=data.air_quality,
                                           size_hint=(1, None), height=dp(165)))

        self.add_widget(TemperatureMapCard(
            lat=getattr(data, '_lat', 35.37),
            lon=getattr(data, '_lon', -81.96),
            city=data.location_zip,
            temp=c.temp,
            size_hint=(1, None), height=dp(165),
        ))

        # ── 2-column grid for smaller info cards ──────────────────────
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        grid.add_widget(UVIndexCard(uv=c.uv))

        sunset_str = data.today_sunset() or '—'
        sunrise_str = data.today_sunrise() or '—'
        sun_prog = data.sun_progress()
        grid.add_widget(SunsetCard(sunset=sunset_str, sunrise=sunrise_str, progress=sun_prog))

        grid.add_widget(WindCard(speed=c.wind_speed, direction_deg=c.wind_dir))

        precip_24h = today.precip_sum if today else 0.0
        grid.add_widget(RainfallCard(last_24h=c.precip, next_24h=precip_24h))

        dew_approx = round(c.temp - (100 - c.humidity) / 5)
        grid.add_widget(FeelsLikeCard(
            feels=c.feels_like, actual=c.temp,
            humidity=c.humidity, wind=c.wind_speed,
        ))

        grid.add_widget(HumidityCard(humidity=c.humidity, dew_point=dew_approx))
        grid.add_widget(VisibilityCard(miles=c.visibility))

        pressure_trend_label = pressure_trend(data.hourly, c.pressure) if data.hourly else 'Steady'
        grid.add_widget(PressureCard(pressure_hpa=c.pressure, trend=pressure_trend_label))

        self.add_widget(grid)


# Keep old name as alias so weather_detail.py import still works
DetailCardsGrid = DetailCardsSection
