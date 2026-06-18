"""Detail information cards — 2-column grid below the forecast.

Cards: Air Quality, UV Index, Sunset/Sunrise, Wind, Rainfall,
       Feels Like, Humidity, Visibility, Pressure, Temperature Map (placeholder).
"""
import math

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
from src.utils.units import fmt_temp

KV = """
<_BaseCard>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(165)
    padding: [0, 0]
    spacing: 0
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.16
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16)]
        Color:
            rgba: 0.07, 0.14, 0.26, 0.12
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, dp(16)]
            width: 1
"""
Builder.load_string(KV)


def _card_title(text: str) -> Label:
    lbl = Label(
        text=text.upper(),
        font_size=sp(11),
        color=(0.07, 0.14, 0.26, 0.55),
        size_hint_y=None,
        height=dp(16),
        halign='left',
        valign='middle',
        bold=False,
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _card_value(text: str, size=sp(30)) -> Label:
    """Large value label — centered in the body section."""
    lbl = Label(text=text, font_size=size, bold=True,
                color=(0.07, 0.14, 0.26, 1), halign='center', valign='middle',
                size_hint=(1, 1))
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _card_sub(text: str) -> Label:
    """Footer text — small, bottom-left."""
    lbl = Label(text=text, font_size=sp(12), bold=False,
                color=(0.07, 0.14, 0.26, 0.65), halign='left', valign='middle',
                size_hint=(1, None), height=dp(20))
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


class _BaseCard(BoxLayout):
    """3-section card: fixed header | centered body | fixed footer."""

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

    def build_sections(self, title_icon: str, title_text: str,
                       body_widgets: list, footer_text: str = '',
                       see_more_fn=None):
        """
        title_icon  — Material icon name
        title_text  — always shown on ONE line in the header
        body_widgets— list of widgets centered in the body (X and Y)
        footer_text — static bottom-left label (optional)
        see_more_fn — if set, shows 'See More ›' at bottom right
        """
        from kivy.uix.boxlayout import BoxLayout as _BL
        from kivy.uix.floatlayout import FloatLayout as _FL

        # ── Header (fixed height, never wraps) ──────────────────────
        # Header: icon starts at same left as footer text (dp12), text sp21
        hdr = _BL(orientation='horizontal', size_hint=(1, None), height=dp(36),
                  padding=[dp(12), 0, dp(8), 0], spacing=dp(6))
        with hdr.canvas.before:
            Color(0.07, 0.14, 0.26, 0.07)
            _hr = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w, v, r=_hr: setattr(r, 'pos', v),
                 size=lambda w, v, r=_hr: setattr(r, 'size', v))

        from kivymd.uix.button import MDIconButton
        hdr.add_widget(MDIconButton(icon=title_icon, theme_icon_color='Custom',
                                    icon_color=(0.07, 0.14, 0.26, 0.70), icon_size=dp(20),
                                    size_hint=(None, 1), width=dp(32)))
        # Header text — 50% larger than before (was sp14 → now sp21)
        hdr_lbl = Label(text=title_text, font_size=sp(21), bold=False,
                        color=(0.07, 0.14, 0.26, 0.85), size_hint=(1, 1),
                        halign='left', valign='middle')
        hdr_lbl.bind(size=hdr_lbl.setter('text_size'))
        hdr.add_widget(hdr_lbl)
        self.add_widget(hdr)

        # ── Body (centered X and Y) ──────────────────────────────────
        body = _FL(size_hint=(1, 1))
        inner = _BL(orientation='vertical', size_hint=(None, None),
                    pos_hint={'center_x': 0.5, 'center_y': 0.5},
                    spacing=dp(4))
        inner.bind(minimum_height=inner.setter('height'),
                   minimum_width=inner.setter('width'))
        for w in body_widgets:
            inner.add_widget(w)
        body.add_widget(inner)
        self.add_widget(body)

        # ── Footer (fixed bottom) ────────────────────────────────────
        if footer_text or see_more_fn:
            ftr = _BL(orientation='horizontal', size_hint=(1, None),
                      height=dp(22), padding=[dp(12), 0])
            if footer_text:
                fl = Label(text=footer_text, font_size=sp(11), bold=False,
                           color=(0.07, 0.14, 0.26, 0.55), size_hint=(1, 1),
                           halign='left', valign='middle')
                fl.bind(size=fl.setter('text_size'))
                ftr.add_widget(fl)
            if see_more_fn:
                ftr.add_widget(Widget(size_hint_x=1))
                sm = Label(text='See More  ›', font_size=sp(11),
                           color=(0.07, 0.14, 0.26, 0.55), size_hint=(None, 1),
                           width=dp(80), halign='right', valign='middle')
                sm.bind(size=sm.setter('text_size'))
                ftr.add_widget(sm)
                _sm_start = [None]
                def _sm_down(w, t, s=_sm_start):
                    if w.collide_point(*t.pos): s[0] = (t.x, t.y)
                def _sm_up(w, t, s=_sm_start, fn=see_more_fn):
                    if s[0] is None: return
                    dx = abs(t.x - s[0][0]); dy = abs(t.y - s[0][1]); s[0] = None
                    if dx < 8 and dy < 8 and w.collide_point(*t.pos):
                        try: fn()
                        except Exception: pass
                ftr.bind(on_touch_down=_sm_down, on_touch_up=_sm_up)
            self.add_widget(ftr)


def _see_more_footer(on_tap):
    """Footer 'See More ›' — only fires on actual taps, not during scroll."""
    from kivy.uix.boxlayout import BoxLayout as _BL
    row = _BL(orientation='horizontal', size_hint_y=None, height=dp(24))
    lbl = Label(text='See More  ›', font_size=sp(12), color=(0.07, 0.14, 0.26, 0.55),
                size_hint=(1, 1), halign='right', valign='middle')
    lbl.bind(size=lbl.setter('text_size'))
    row.add_widget(lbl)

    _start = [None]

    def _down(w, t):
        if w.collide_point(*t.pos):
            _start[0] = (t.x, t.y)
    def _up(w, t):
        if _start[0] is None: return
        dx = abs(t.x - _start[0][0])
        dy = abs(t.y - _start[0][1])
        _start[0] = None
        # Only fire if it was a real tap (minimal movement)
        if dx < 8 and dy < 8 and w.collide_point(*t.pos):
            try: on_tap()
            except Exception: pass

    row.bind(on_touch_down=_down, on_touch_up=_up)
    return row


class _SlideUpModal(FloatLayout):
    """Solid dark panel from bottom — 95% screen height, rounded top corners."""

    def __init__(self, title: str, content_builder, **kwargs):
        super().__init__(size_hint=(1, 1), **kwargs)

        # Solid dim (not translucent — opaque enough to block content)
        dim = Widget(size_hint=(1, 1))
        with dim.canvas:
            Color(0, 0, 0, 0.72)
            _dim = Rectangle(pos=dim.pos, size=dim.size)
        dim.bind(pos=lambda w, v, r=_dim: setattr(r, 'pos', v),
                 size=lambda w, v, r=_dim: setattr(r, 'size', v))
        self.add_widget(dim)

        # Panel — solid background, PROPERLY bound so canvas redraws with layout
        panel = BoxLayout(orientation='vertical',
                          size_hint=(1, 0.95), pos_hint={'x': 0, 'y': 0})
        with panel.canvas.before:
            Color(0.10, 0.12, 0.17, 1)   # solid, not alpha
            _pbg = RoundedRectangle(pos=panel.pos, size=panel.size,
                                    radius=[dp(22), dp(22), 0, 0])
        # THIS is the critical bind that was missing — canvas must update when layout fires
        panel.bind(
            pos=lambda w, v, r=_pbg: setattr(r, 'pos', v),
            size=lambda w, v, r=_pbg: setattr(r, 'size', v),
        )
        self._panel = panel
        self.add_widget(panel)

        # Tap dim to close (only if outside panel)
        def _dim_tap(w, t):
            if not panel.collide_point(*t.pos):
                self._close()
        dim.bind(on_touch_up=_dim_tap)

        # Header row
        hdr = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(56),
                        padding=[dp(20), dp(4)])
        hdr.add_widget(Label(text=title, font_size=sp(20), bold=True,
                             color=(1, 1, 1, 1), size_hint=(1, 1),
                             halign='left', valign='middle'))
        from kivymd.uix.button import MDIconButton
        close_btn = MDIconButton(icon='close', theme_icon_color='Custom',
                                 icon_color=(1, 1, 1, 0.80), icon_size=dp(24),
                                 size_hint=(None, None), size=(dp(44), dp(44)),
                                 on_release=lambda *_: self._close())
        hdr.add_widget(close_btn)
        panel.add_widget(hdr)

        # Thin separator
        sep = Widget(size_hint_y=None, height=dp(1))
        with sep.canvas:
            Color(1, 1, 1, 0.12)
            _sr = Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda w, v, r=_sr: setattr(r, 'pos', v),
                 size=lambda w, v, r=_sr: setattr(r, 'size', (v[0], 1)))
        panel.add_widget(sep)

        # Scrollable content
        from kivy.uix.scrollview import ScrollView
        sv = ScrollView(do_scroll_y=True, do_scroll_x=False, bar_width=0,
                        size_hint=(1, 1))
        inner = BoxLayout(orientation='vertical', size_hint_y=None,
                          padding=[dp(20), dp(12), dp(20), dp(40)], spacing=dp(8))
        inner.bind(minimum_height=inner.setter('height'))
        content_builder(inner)
        sv.add_widget(inner)
        panel.add_widget(sv)

    def _close(self):
        from kivy.core.window import Window
        try:
            Window.remove_widget(self)
        except Exception:
            if self.parent:
                self.parent.remove_widget(self)

    @staticmethod
    def show(title: str, content_builder, target_widget):
        """Add modal directly to Window — always works regardless of widget tree."""
        from kivy.core.window import Window
        # Don't pass size_hint — _SlideUpModal.__init__ already sets size_hint=(1,1)
        # Don't pass index — older Kivy Window.add_widget doesn't accept it
        modal = _SlideUpModal(title=title, content_builder=content_builder)
        Window.add_widget(modal)


# ──────────────────────────────────────────────
# Air Quality
# ──────────────────────────────────────────────

class AirQualityCard(_BaseCard):
    def __init__(self, aq: AirQualityData, **kwargs):
        super().__init__(**kwargs)
        self._aq = aq
        val = Label(text=f'{aq.us_aqi}', font_size=sp(42), bold=True,
                    color=aq.category_color_rgba, halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(80), dp(52)))
        cat = Label(text=aq.category, font_size=sp(16), bold=False,
                    color=(0.07, 0.14, 0.26, 0.90), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(150), dp(22)))
        bar = _AQIBar(aqi=aq.us_aqi, size_hint=(None, None), size=(dp(130), dp(6)))
        self.build_sections('air-filter', 'Air Quality',
                            [val, cat, bar],
                            footer_text=aq.description[:40],
                            see_more_fn=self._open_detail)

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
            Color(0.07, 0.14, 0.26, 1)
            r = h * 0.9
            Ellipse(pos=(self.x + marker_x - r, self.y + h/2 - r), size=(r*2, r*2))


# ──────────────────────────────────────────────
# UV Index
# ──────────────────────────────────────────────

class UVIndexCard(_BaseCard):
    def __init__(self, uv: float, **kwargs):
        super().__init__(**kwargs)
        val = Label(text=f'{int(uv)}', font_size=sp(42), bold=True,
                    color=(0.07, 0.14, 0.26, 1), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(60), dp(52)))
        cat = Label(text=_uv_label(uv), font_size=sp(16), bold=True,
                    color=(0.07, 0.14, 0.26, 0.90), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(100), dp(22)))
        bar = _UVBar(uv=uv, size_hint=(None, None), size=(dp(120), dp(6)))
        self.build_sections('white-balance-sunny', 'UV Index',
                            [val, cat, bar], footer_text=_uv_advice(uv))


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
            Color(0.07, 0.14, 0.26, 1)
            r = h * 0.9
            Ellipse(pos=(self.x + mx - r, self.y + h/2 - r), size=(r*2, r*2))


# ──────────────────────────────────────────────
# Sunset / Sunrise
# ──────────────────────────────────────────────

class SunsetCard(_BaseCard):
    def __init__(self, sunset: str, sunrise: str, progress: float, **kwargs):
        super().__init__(**kwargs)
        val = Label(text=sunset or '—', font_size=sp(32), bold=True,
                    color=(0.07, 0.14, 0.26, 1), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(140), dp(40)))
        arc = _SunArc(progress=progress, size_hint=(None, None), size=(dp(130), dp(52)))
        self.build_sections('weather-sunset', 'Sunset',
                            [val, arc], footer_text=f'Sunrise: {sunrise or "—"}')


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
            Color(0.07, 0.14, 0.26, 0.25)
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
        lbl = wind_direction_label(direction_deg)
        compass = _WindCompass(deg=direction_deg,
                               size_hint=(None, None), size=(dp(90), dp(90)))
        spd = Label(text=f'{speed} mph', font_size=sp(22), bold=True,
                    color=(0.07, 0.14, 0.26, 1), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(100), dp(28)))
        self.build_sections('weather-windy', 'Wind',
                            [compass, spd], footer_text=f'Direction: {lbl}')


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
            Color(0.07, 0.14, 0.26, 0.18)
            Line(circle=(cx, cy, r), width=1.5)
            # Inner ring
            Color(0.07, 0.14, 0.26, 0.08)
            Line(circle=(cx, cy, r * 0.6), width=1)

            # Cardinal tick marks
            for i in range(12):
                angle = math.radians(i * 30)
                is_cardinal = (i % 3 == 0)
                inner = r * (0.78 if is_cardinal else 0.85)
                outer = r * 0.98
                Color(0.07, 0.14, 0.26, 0.60 if is_cardinal else 0.25)
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
            Color(0.07, 0.14, 0.26, 0.45)
            Line(points=[cx, cy, tail_x, tail_y], width=1.5)

            # Centre dot
            Color(0.07, 0.14, 0.26, 0.95)
            Ellipse(pos=(cx - dp(3.5), cy - dp(3.5)), size=(dp(7), dp(7)))


# ──────────────────────────────────────────────
# Rainfall
# ──────────────────────────────────────────────

class RainfallCard(_BaseCard):
    def __init__(self, last_24h: float, next_24h: float, **kwargs):
        super().__init__(**kwargs)
        val = Label(text=f'{last_24h:.2f}"', font_size=sp(38), bold=True,
                    color=(0.07, 0.14, 0.26, 1), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(120), dp(50)))
        self.build_sections('weather-rainy', 'Rainfall',
                            [val], footer_text=f'{next_24h:.2f}" expected next 24h')


class FeelsLikeCard(_BaseCard):
    def __init__(self, feels: int, actual: int, humidity: int, wind: int,
                 units: str = 'F', **kwargs):
        super().__init__(**kwargs)
        # feels_like_reason's thresholds are calibrated in Fahrenheit degrees,
        # so the comparison stays in F — only the displayed value converts.
        reason = feels_like_reason(feels, actual, humidity, wind)
        val = Label(text=fmt_temp(feels, units), font_size=sp(42), bold=True,
                    color=(0.07, 0.14, 0.26, 1), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(90), dp(52)))
        self.build_sections('thermometer', 'Feels Like', [val], footer_text=reason[:42])


class HumidityCard(_BaseCard):
    def __init__(self, humidity: int, dew_point: int, units: str = 'F', **kwargs):
        super().__init__(**kwargs)
        val = Label(text=f'{humidity}%', font_size=sp(42), bold=True,
                    color=(0.07, 0.14, 0.26, 1), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(90), dp(52)))
        self.build_sections('water-percent', 'Humidity',
                            [val], footer_text=f'Dew point {fmt_temp(dew_point, units)}')


class VisibilityCard(_BaseCard):
    def __init__(self, miles: float, **kwargs):
        super().__init__(**kwargs)
        val = Label(text=f'{min(miles, 10):.0f} mi', font_size=sp(38), bold=True,
                    color=(0.07, 0.14, 0.26, 1), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(110), dp(50)))
        self.build_sections('eye', 'Visibility',
                            [val], footer_text=visibility_description(miles)[:40])


class PressureCard(_BaseCard):
    def __init__(self, pressure_hpa: float, trend: str, **kwargs):
        super().__init__(**kwargs)
        inhg = pressure_hpa * 0.02953
        gauge = _PressureGauge(inhg=inhg, size_hint=(None, None), size=(dp(100), dp(80)))
        val = Label(text=f'{inhg:.2f} inHg', font_size=sp(16), bold=True,
                    color=(0.07, 0.14, 0.26, 0.90), halign='center', valign='middle',
                    size_hint=(None, None), size=(dp(120), dp(24)))
        self.build_sections('gauge', 'Pressure', [gauge, val], footer_text=trend)


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
            Color(0.07, 0.14, 0.26, 0.18)
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
            Color(0.07, 0.14, 0.26, 0.90)
            Line(points=[cx, cy, nx, ny], width=2)

            # Value text (drawn as label — we'll add outside)
            Color(0.07, 0.14, 0.26, 0.95)
            Ellipse(pos=(cx - 4, cy - 4), size=(8, 8))

        # Add value label
        from kivy.uix.label import Label
        if not self.children:
            lbl = Label(
                text=f'{self._inhg:.2f}\ninHg',
                font_size=sp(16),
                bold=True,
                color=(0.07, 0.14, 0.26, 0.95),
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
                 city: str = '', temp: int = 0, units: str = 'F', **kwargs):
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
            text=f'{city}\n{fmt_temp(temp, units)}',
            font_size=sp(13), color=(0.07, 0.14, 0.26, 0.70),
            halign='center', valign='middle', size_hint=(1, 1),
        ))
        preview.bind(on_touch_up=lambda w, t: self._open_map()
                     if w.collide_point(*t.pos) else None)
        self.add_widget(preview)
        self.add_widget(_see_more_footer(self._open_map))

    def _open_map(self):
        url = (
            f'https://embed.windy.com/embed2.html?'
            f'lat={self._lat}&lon={self._lon}'
            f'&detailLat={self._lat}&detailLon={self._lon}'
            f'&width=650&height=450&zoom=8&level=surface'
            f'&overlay=temp&product=ecmwf&menu=&message=&marker='
            f'&pressure=&type=map&location=coordinates&detail='
            f'&metricWind=mph&metricTemp=%C2%B0F&radarRange=-1'
        )

        # Android: full-screen native WebView dialog
        try:
            from jnius import autoclass  # type: ignore
            from android.runnable import run_on_ui_thread  # type: ignore

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            WebView = autoclass('android.webkit.WebView')
            Dialog = autoclass('android.app.Dialog')

            @run_on_ui_thread
            def _open_webview():
                activity = PythonActivity.mActivity
                dlg = Dialog(activity)
                wv = WebView(activity)
                s = wv.getSettings()
                s.setJavaScriptEnabled(True)
                s.setLoadWithOverviewMode(True)
                s.setUseWideViewPort(True)
                s.setDomStorageEnabled(True)
                wv.loadUrl(url)
                dlg.setContentView(wv)
                # 95% width, 85% height — leaves edge visible so tap-outside closes it
                from kivy.core.window import Window as _kw
                dlg.getWindow().setLayout(
                    int(_kw.width * 0.95),
                    int(_kw.height * 0.85),
                )
                dlg.setCancelable(True)          # back button closes
                dlg.setCanceledOnTouchOutside(True)  # tap outside closes
                dlg.show()

            _open_webview()
            return
        except Exception:
            pass

        # Desktop / CI fallback: open in system browser
        import webbrowser
        webbrowser.open(url)


# ──────────────────────────────────────────────
# Alert Banner
# ──────────────────────────────────────────────

class AlertBanner(BoxLayout):
    """Amber alert rows shown at the top of the details card when NWS alerts are active."""

    def __init__(self, alerts: list, **kwargs):
        super().__init__(orientation='vertical', size_hint=(1, None),
                         spacing=dp(4), padding=[0, 0, 0, dp(4)], **kwargs)
        self.bind(minimum_height=self.setter('height'))
        from kivymd.uix.button import MDIconButton

        for alert in alerts[:2]:
            row = BoxLayout(orientation='horizontal', size_hint=(1, None),
                            height=dp(42), padding=[dp(10), dp(4)])
            with row.canvas.before:
                Color(0.75, 0.22, 0.08, 0.95)
                _rb = RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(8)])
            row.bind(
                pos=lambda w, v, r=_rb: setattr(r, 'pos', v),
                size=lambda w, v, r=_rb: setattr(r, 'size', v),
            )
            row.add_widget(MDIconButton(
                icon='alert', theme_icon_color='Custom',
                icon_color=(1.0, 0.90, 0.30, 1), icon_size=dp(18),
                size_hint=(None, 1), width=dp(28),
            ))
            lbl = Label(
                text=alert, font_size=sp(12), bold=False,
                color=(1, 1, 1, 0.95), size_hint=(1, 1),
                halign='left', valign='middle',
            )
            lbl.bind(size=lambda w, v: setattr(w, 'text_size', (v[0], None)))
            row.add_widget(lbl)
            self.add_widget(row)


# ──────────────────────────────────────────────
# Main grid assembler
# ──────────────────────────────────────────────

class DetailCardsSection(BoxLayout):
    """Full-width cards (AQ, Temp Map) followed by 2-col grid of smaller cards."""

    def __init__(self, data: WeatherData, units: str = 'F', **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None,
                         spacing=dp(10), **kwargs)
        self.bind(minimum_height=self.setter('height'))
        self._build(data, units)

    def _build(self, data: WeatherData, units: str = 'F'):
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
            units=units,
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

        # Approximation is calibrated in Fahrenheit — convert only for display.
        dew_approx = round(c.temp - (100 - c.humidity) / 5)
        grid.add_widget(FeelsLikeCard(
            feels=c.feels_like, actual=c.temp,
            humidity=c.humidity, wind=c.wind_speed,
            units=units,
        ))

        grid.add_widget(HumidityCard(humidity=c.humidity, dew_point=dew_approx, units=units))
        grid.add_widget(VisibilityCard(miles=c.visibility))

        pressure_trend_label = pressure_trend(data.hourly, c.pressure) if data.hourly else 'Steady'
        grid.add_widget(PressureCard(pressure_hpa=c.pressure, trend=pressure_trend_label))

        self.add_widget(grid)


# Keep old name as alias so weather_detail.py import still works
DetailCardsGrid = DetailCardsSection
