"""LocationListScreen — list of all saved locations with current conditions."""
import os
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivymd.uix.button import MDIconButton
from kivymd.uix.screen import MDScreen

from src.models.location import Location
from src.models.weather import WeatherData
from src.utils.wmo_codes import get_label, get_bg_path, is_night

_DEL_W = dp(80)   # width of the revealed delete zone

KV = """
<LocationListScreen>:
    name: 'location_list'
    canvas.before:
        Color:
            rgba: 0.04, 0.05, 0.08, 1
        Rectangle:
            pos: self.pos
            size: self.size
"""
Builder.load_string(KV)


class _LocationCard(FloatLayout):
    """Location card with hi-res weather background + swipe-left to delete.

    Swipe left ≥ 60dp → red Delete button revealed.
    Tap (no swipe) → navigates to that location.
    """

    def __init__(self, location: Location, weather: WeatherData | None,
                 on_tap, on_delete, **kwargs):
        super().__init__(size_hint_y=None, height=dp(110), **kwargs)
        self._location = location
        self._on_tap = on_tap
        self._on_delete = on_delete
        self._swiped = False
        self._tx = None   # touch start x
        self._ty = None   # touch start y

        # ── Background photo ────────────────────────────────────────
        night = is_night()
        code = weather.current.code if weather else 0
        abs_bg = os.path.join(os.getcwd(), get_bg_path(code, night))
        if os.path.exists(abs_bg):
            bg = KivyImage(source=abs_bg, size_hint=(1, 1),
                           pos_hint={'x': 0, 'y': 0})
            try: bg.fit_mode = 'cover'
            except: pass
            self.add_widget(bg)

        # Dark overlay
        ov = Widget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        with ov.canvas:
            Color(0, 0, 0, 0.38)
            _ov = Rectangle(pos=ov.pos, size=ov.size)
        ov.bind(pos=lambda w, v, r=_ov: setattr(r, 'pos', v),
                size=lambda w, v, r=_ov: setattr(r, 'size', v))
        self.add_widget(ov)

        # ── Delete zone (always present, revealed by sliding _main) ─
        del_zone = Widget(size_hint=(None, 1), width=_DEL_W,
                          pos_hint={'right': 1, 'y': 0})
        with del_zone.canvas:
            Color(0.90, 0.15, 0.15, 1)
            _dz = Rectangle(pos=del_zone.pos, size=del_zone.size)
        del_zone.bind(pos=lambda w, v, r=_dz: setattr(r, 'pos', v),
                      size=lambda w, v, r=_dz: setattr(r, 'size', v))
        del_lbl = Label(text='Delete', font_size=sp(13), bold=True,
                        color=(1, 1, 1, 1), size_hint=(1, 1))
        del_zone.add_widget(del_lbl)
        del_zone.bind(on_touch_down=self._on_delete_tap)
        self.add_widget(del_zone)

        # ── Main content (slides to reveal delete zone) ──────────────
        self._main = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            padding=[dp(16), dp(12)],
            spacing=dp(12),
        )

        left = BoxLayout(orientation='vertical', size_hint=(1, 1))
        from datetime import datetime
        time_lbl = Label(
            text=datetime.now().strftime('%I:%M %p').lstrip('0'),
            font_size=sp(12), color=(1, 1, 1, 0.65),
            size_hint_y=None, height=dp(16), halign='left', valign='middle',
        )
        time_lbl.bind(size=time_lbl.setter('text_size'))
        left.add_widget(time_lbl)

        city_lbl = Label(
            text=location.city, font_size=sp(22), bold=True,
            color=(1, 1, 1, 1), size_hint_y=None, height=dp(28),
            halign='left', valign='middle',
        )
        city_lbl.bind(size=city_lbl.setter('text_size'))
        left.add_widget(city_lbl)

        if weather:
            for txt, sz, alpha, h in [
                (get_label(weather.current.code), sp(14), 0.80, dp(20)),
                (f'H:{weather.today_high()}°   L:{weather.today_low()}°', sp(13), 0.70, dp(18)),
            ]:
                lbl = Label(text=txt, font_size=sz, color=(1, 1, 1, alpha),
                            size_hint_y=None, height=h, halign='left', valign='middle')
                lbl.bind(size=lbl.setter('text_size'))
                left.add_widget(lbl)

        self._main.add_widget(left)

        if weather:
            temp_lbl = Label(
                text=f'{weather.current.temp}°', font_size=sp(44),
                color=(1, 1, 1, 1), size_hint=(None, 1), width=dp(80),
                halign='right', valign='middle',
            )
            temp_lbl.bind(size=temp_lbl.setter('text_size'))
            self._main.add_widget(temp_lbl)

        self.add_widget(self._main)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._tx, self._ty = touch.x, touch.y
            touch.grab(self)
            return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return
        dx = touch.x - self._tx
        # Only slide if predominantly horizontal
        if abs(dx) > abs(touch.y - self._ty):
            base = -_DEL_W if self._swiped else 0
            offset = max(-_DEL_W, min(0, base + dx))
            self._main.x = self.x + offset

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return
        touch.ungrab(self)
        dx = touch.x - self._tx
        dy = touch.y - self._ty

        if abs(dx) < dp(8) and abs(dy) < dp(8):
            # Pure tap
            if self._swiped:
                self._snap_close()
            else:
                self._on_tap(self._location)
        elif dx < -dp(50):
            self._snap_open()
        else:
            self._snap_close()

    def _snap_open(self):
        Animation(x=self.x - _DEL_W, duration=0.18, t='out_quad').start(self._main)
        self._swiped = True

    def _snap_close(self):
        Animation(x=self.x, duration=0.18, t='out_quad').start(self._main)
        self._swiped = False

    def _on_delete_tap(self, widget, touch):
        if widget.collide_point(*touch.pos) and self._swiped:
            self._on_delete(self._location.zip)
            return True


class LocationListScreen(MDScreen):
    def __init__(self, locations: list, weather_map: dict,
                 on_tap, on_add, on_delete, **kwargs):
        super().__init__(**kwargs)
        self._locations = locations
        self._weather_map = weather_map
        self._on_tap = on_tap
        self._on_add = on_add
        self._on_delete = on_delete
        self._build_ui()

    def refresh(self, locations: list, weather_map: dict):
        self._locations = locations
        self._weather_map = weather_map
        self.clear_widgets()
        self._build_ui()

    def _build_ui(self):
        root = FloatLayout()

        # Top bar
        top_bar = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(52),
            padding=[dp(16), dp(8)],
            pos_hint={'top': 1},
        )
        with top_bar.canvas.before:
            Color(0.04, 0.05, 0.08, 0.95)
            self._topbar_bg = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=lambda w, v: setattr(self._topbar_bg, 'pos', v))
        top_bar.bind(size=lambda w, v: setattr(self._topbar_bg, 'size', v))

        top_bar.add_widget(Label(
            text='Weather',
            font_size=sp(24),
            bold=True,
            color=(1, 1, 1, 0.95),
            size_hint=(1, 1),
            halign='left',
            valign='middle',
        ))

        # Hint label
        hint = Label(
            text='← swipe to delete',
            font_size=sp(11), color=(1, 1, 1, 0.35),
            size_hint=(None, 1), width=dp(120),
            halign='right', valign='middle',
        )
        hint.bind(size=hint.setter('text_size'))
        top_bar.add_widget(hint)

        root.add_widget(top_bar)

        # Search bar area (visual only — zip input is in AddLocationScreen)
        search_area = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(44),
            padding=[dp(14), 0],
            pos_hint={'top': 0.89},
        )
        search_box = BoxLayout(size_hint=(1, 1))
        with search_box.canvas.before:
            Color(0.15, 0.15, 0.18, 0.90)
            _sb_rect = RoundedRectangle(pos=(0, 0), size=(1, 1), radius=[dp(10)])
        search_box.bind(
            pos=lambda w, v, r=_sb_rect: setattr(r, 'pos', v),
            size=lambda w, v, r=_sb_rect: setattr(r, 'size', v),
        )
        search_lbl = Label(
            text='  Search for a city or airport',
            font_size=sp(15),
            color=(1, 1, 1, 0.40),
            halign='left',
            valign='middle',
        )
        search_lbl.bind(size=search_lbl.setter('text_size'))
        search_box.add_widget(search_lbl)
        search_area.add_widget(search_box)
        root.add_widget(search_area)

        # Cards scroll view
        scroll = ScrollView(
            do_scroll_y=True,
            do_scroll_x=False,
            bar_width=0,
            size_hint=(1, 1),
            pos_hint={'top': 0.81},
        )
        cards_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=[dp(14), dp(10), dp(14), dp(80)],
        )
        cards_box.bind(minimum_height=cards_box.setter('height'))

        for loc in self._locations:
            weather = self._weather_map.get(loc.zip)
            card = _LocationCard(
                location=loc,
                weather=weather,
                on_tap=self._on_tap,
                on_delete=self._on_delete,
            )
            cards_box.add_widget(card)

        scroll.add_widget(cards_box)
        root.add_widget(scroll)

        # Bottom: add button
        add_btn = MDIconButton(
            icon='plus-circle-outline',
            theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.85),
            icon_size=dp(32),
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={'center_x': 0.5, 'y': 0.01},
            on_release=lambda *_: self._on_add(),
        )
        root.add_widget(add_btn)

        self.add_widget(root)

    pass
