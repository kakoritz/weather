"""Precipitation radar map card — full-width card between hourly and 10-day.

Shows a live radar overlay (RainViewer) on a CartoDB dark base tile. City pin
with current temperature is drawn at card center. 'See More' opens Windy.com
precipitation layer in a native WebView modal.
"""
import math
import threading

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.widget import Widget

_RV_META = 'https://api.rainviewer.com/public/weather-maps.json'
_CARD_H = dp(300)
_MAP_H = dp(220)
_HDR_H = dp(36)
_FTR_H = dp(38)


def _tile_xy(lat: float, lon: float, zoom: int) -> tuple:
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)
    return x, y


class _CityPin(Widget):
    """Draws a temperature circle + city label at widget center."""

    def __init__(self, temp_text: str, city: str, **kwargs):
        super().__init__(**kwargs)
        self._temp_text = temp_text
        self._city = city
        self._labels_added = False
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        if self.width < 1:
            return
        r = dp(22)
        cx = self.x + self.width / 2
        # Place circle in upper-center of widget (labels go below)
        cy = self.y + self.height * 0.60

        with self.canvas:
            # Circle fill
            Color(0.10, 0.18, 0.50, 0.92)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            # Circle border
            Color(1, 1, 1, 0.88)
            Line(circle=(cx, cy, r), width=1.5)

        if not self._labels_added:
            self._labels_added = True
            Clock.schedule_once(lambda dt: self._add_labels(cx, cy, r), 0)

    def _add_labels(self, cx, cy, r):
        # Temperature inside circle
        temp_lbl = Label(
            text=self._temp_text,
            font_size=sp(15), bold=True, color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(44), dp(44)),
            pos=(cx - dp(22), cy - dp(22)),
            halign='center', valign='middle',
        )
        temp_lbl.text_size = (dp(44), dp(44))
        self.add_widget(temp_lbl)

        # City label below circle
        city_lbl = Label(
            text=self._city,
            font_size=sp(12), bold=False, color=(1, 1, 1, 0.90),
            size_hint=(None, None), size=(dp(120), dp(20)),
            pos=(cx - dp(60), cy - r - dp(20)),
            halign='center', valign='middle',
        )
        city_lbl.text_size = (dp(120), dp(20))
        self.add_widget(city_lbl)


class PrecipitationMapCard(BoxLayout):
    """Full-width precipitation radar card with CartoDB dark tile + RainViewer overlay."""

    def __init__(self, lat: float, lon: float, city: str, temp_text: str, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None,
                         height=_CARD_H, **kwargs)
        self._lat = lat
        self._lon = lon
        self._city = city
        self._temp_text = temp_text
        self._rv_img: AsyncImage | None = None
        self._build()
        threading.Thread(target=self._fetch_rv, daemon=True).start()

    def _build(self):
        # Card background + border via canvas.before
        with self.canvas.before:
            Color(0.06, 0.22, 0.55, 0.52)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
            Color(1, 1, 1, 0.18)
            self._border = Line(width=1)
        self.bind(pos=self._update_card_bg, size=self._update_card_bg)

        # ── Header ─────────────────────────────────────────────────────
        hdr = BoxLayout(orientation='horizontal', size_hint=(1, None), height=_HDR_H,
                        padding=[dp(12), 0, dp(8), 0], spacing=dp(6))
        with hdr.canvas.before:
            Color(1, 1, 1, 0.07)
            _hr = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w, v, r=_hr: setattr(r, 'pos', v),
                 size=lambda w, v, r=_hr: setattr(r, 'size', v))

        from kivymd.uix.button import MDIconButton
        hdr.add_widget(MDIconButton(
            icon='umbrella', theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.70), icon_size=dp(16),
            size_hint=(None, 1), width=dp(28),
        ))
        hdr_lbl = Label(
            text='PRECIPITATION', font_size=sp(11), bold=False,
            color=(1, 1, 1, 0.55), size_hint=(1, 1),
            halign='left', valign='middle',
        )
        hdr_lbl.bind(size=hdr_lbl.setter('text_size'))
        hdr.add_widget(hdr_lbl)
        self.add_widget(hdr)

        # ── Map area ────────────────────────────────────────────────────
        zoom = 7
        tx, ty = _tile_xy(self._lat, self._lon, zoom)

        map_fl = FloatLayout(size_hint=(1, None), height=_MAP_H)

        # CartoDB dark base tile (no key required)
        base_url = f'https://a.basemaps.cartocdn.com/dark_all/{zoom}/{tx}/{ty}.png'
        base_img = AsyncImage(
            source=base_url, size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}, allow_stretch=True, keep_ratio=False,
        )
        map_fl.add_widget(base_img)

        # RainViewer radar overlay — source set async once we have the timestamp
        self._rv_img = AsyncImage(
            source='', size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}, allow_stretch=True, keep_ratio=False,
            opacity=0.72,
        )
        map_fl.add_widget(self._rv_img)

        # City pin
        pin = _CityPin(
            temp_text=self._temp_text, city=self._city,
            size_hint=(1, 1), pos_hint={'x': 0, 'y': 0},
        )
        map_fl.add_widget(pin)

        self.add_widget(map_fl)

        # ── See More footer ─────────────────────────────────────────────
        ftr = BoxLayout(orientation='horizontal', size_hint=(1, None), height=_FTR_H,
                        padding=[dp(12), 0])
        sm = Label(
            text='See More  ›', font_size=sp(12), color=(1, 1, 1, 0.55),
            size_hint=(1, 1), halign='right', valign='middle',
        )
        sm.bind(size=sm.setter('text_size'))
        ftr.add_widget(sm)
        _start = [None]

        def _dn(w, t):
            if w.collide_point(*t.pos):
                _start[0] = (t.x, t.y)

        def _up(w, t):
            if _start[0] is None:
                return
            dx = abs(t.x - _start[0][0])
            dy = abs(t.y - _start[0][1])
            _start[0] = None
            if dx < dp(8) and dy < dp(8) and w.collide_point(*t.pos):
                self._open_map()

        ftr.bind(on_touch_down=_dn, on_touch_up=_up)
        self.add_widget(ftr)

    def _update_card_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = [self.x, self.y, self.width, self.height, dp(16)]

    def _fetch_rv(self):
        try:
            import requests
            resp = requests.get(_RV_META, timeout=8)
            if not resp.ok:
                return
            data = resp.json()
            host = data.get('host', 'https://tilecache.rainviewer.com')
            past = data.get('radar', {}).get('past', [])
            if not past:
                return
            path = past[-1].get('path', '')
            if not path:
                return
            zoom = 7
            tx, ty = _tile_xy(self._lat, self._lon, zoom)
            rv_url = f'{host}{path}/512/{zoom}/{tx}/{ty}/4/1_1.png'

            def _set(dt):
                if self._rv_img:
                    self._rv_img.source = rv_url

            Clock.schedule_once(_set, 0)
        except Exception:
            pass

    def _open_map(self):
        url = (
            f'https://embed.windy.com/embed2.html?'
            f'lat={self._lat}&lon={self._lon}'
            f'&detailLat={self._lat}&detailLon={self._lon}'
            f'&width=650&height=450&zoom=8&level=surface'
            f'&overlay=rain&product=ecmwf&menu=&message=&marker='
            f'&pressure=&type=map&location=coordinates&detail='
            f'&metricWind=mph&metricTemp=%C2%B0F&radarRange=-1'
        )
        try:
            from jnius import autoclass  # type: ignore
            from android.runnable import run_on_ui_thread  # type: ignore

            PythonActivity = autoclass('org.kivy.android.PythonActivity')

            @run_on_ui_thread
            def _open():
                activity = PythonActivity.mActivity
                dlg = autoclass('android.app.Dialog')(activity)
                wv = autoclass('android.webkit.WebView')(activity)
                s = wv.getSettings()
                s.setJavaScriptEnabled(True)
                s.setLoadWithOverviewMode(True)
                s.setUseWideViewPort(True)
                s.setDomStorageEnabled(True)
                wv.loadUrl(url)
                dlg.setContentView(wv)
                from kivy.core.window import Window as _kw
                dlg.getWindow().setLayout(int(_kw.width * 0.95), int(_kw.height * 0.85))
                dlg.setCancelable(True)
                dlg.setCanceledOnTouchOutside(True)
                dlg.show()

            _open()
            return
        except Exception:
            pass
        import webbrowser
        webbrowser.open(url)
