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


class _LocationCard(BoxLayout):
    """Location card using a horizontal ScrollView for swipe-to-delete.

    The card content is full-width. Swiping left reveals a red Delete button
    that's the same height. Snaps to open (50/50) or closed. Tap on content
    navigates; tap on Delete button removes the location.
    """

    def __init__(self, location: Location, weather: WeatherData | None,
                 on_tap, on_delete, **kwargs):
        super().__init__(size_hint_y=None, height=dp(110), **kwargs)
        self._location = location
        self._on_tap = on_tap
        self._on_delete = on_delete
        self._touch_start = None

        # Horizontal scroll reveals Delete button to the right
        scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=0,
            scroll_x=0,
            effect_cls='ScrollEffect',
            size_hint=(1, 1),
        )
        # Container: [full-width content] [delete button _DEL_W]
        self._container = BoxLayout(
            orientation='horizontal',
            size_hint=(None, 1),
        )

        # ── Content card ──────────────────────────────────────────
        self._content_card = FloatLayout(size_hint=(None, 1))
        self.bind(width=self._on_width)  # set widths once we know our own

        # Background photo
        night = is_night()
        code = weather.current.code if weather else 0
        abs_bg = os.path.join(os.getcwd(), get_bg_path(code, night))
        if os.path.exists(abs_bg):
            bg = KivyImage(source=abs_bg, size_hint=(1, 1),
                           pos_hint={'x': 0, 'y': 0})
            try: bg.fit_mode = 'cover'
            except: pass
            self._content_card.add_widget(bg)

        ov = Widget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        with ov.canvas:
            Color(0, 0, 0, 0.38)
            _ov = Rectangle(pos=ov.pos, size=ov.size)
        ov.bind(pos=lambda w, v, r=_ov: setattr(r, 'pos', v),
                size=lambda w, v, r=_ov: setattr(r, 'size', v))
        self._content_card.add_widget(ov)

        inner = BoxLayout(orientation='horizontal', size_hint=(1, 1),
                          pos_hint={'x': 0, 'y': 0},
                          padding=[dp(16), dp(12)], spacing=dp(12))
        left = BoxLayout(orientation='vertical', size_hint=(1, 1))
        from datetime import datetime
        for txt, sz, bold, alpha, h in [
            (datetime.now().strftime('%I:%M %p').lstrip('0'), sp(12), False, 0.65, dp(16)),
            (location.city, sp(22), True, 1.0, dp(28)),
        ]:
            lbl = Label(text=txt, font_size=sz, bold=bold, color=(1, 1, 1, alpha),
                        size_hint_y=None, height=h, halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            left.add_widget(lbl)
        if weather:
            for txt, sz, alpha, h in [
                (get_label(weather.current.code), sp(14), 0.80, dp(20)),
                (f'H:{weather.today_high()}°   L:{weather.today_low()}°', sp(13), 0.70, dp(18)),
            ]:
                lbl = Label(text=txt, font_size=sz, color=(1, 1, 1, alpha),
                            size_hint_y=None, height=h, halign='left', valign='middle')
                lbl.bind(size=lbl.setter('text_size'))
                left.add_widget(lbl)
        inner.add_widget(left)
        if weather:
            t = Label(text=f'{weather.current.temp}°', font_size=sp(44),
                      color=(1, 1, 1, 1), size_hint=(None, 1), width=dp(80),
                      halign='right', valign='middle')
            t.bind(size=t.setter('text_size'))
            inner.add_widget(t)
        self._content_card.add_widget(inner)

        # Touch on content → tap or start swipe
        inner.bind(on_touch_down=self._content_touch_down)
        inner.bind(on_touch_up=self._content_touch_up)
        self._container.add_widget(self._content_card)

        # ── Delete button — BoxLayout clips text within bounds ───────
        del_btn = BoxLayout(size_hint=(None, 1), width=_DEL_W)
        with del_btn.canvas.before:
            Color(0.92, 0.18, 0.18, 1)
            _db = Rectangle(pos=del_btn.pos, size=del_btn.size)
        del_btn.bind(pos=lambda w, v, r=_db: setattr(r, 'pos', v),
                     size=lambda w, v, r=_db: setattr(r, 'size', v))
        lbl_del = Label(text='Delete', font_size=sp(14), bold=True,
                        color=(1, 1, 1, 1), size_hint=(1, 1),
                        halign='center', valign='middle')
        lbl_del.bind(size=lbl_del.setter('text_size'))
        del_btn.add_widget(lbl_del)
        del_btn.bind(on_touch_up=self._delete_touch)
        self._container.add_widget(del_btn)

        scroll.add_widget(self._container)
        self.add_widget(scroll)
        self._scroll = scroll

    def _on_width(self, *_):
        w = self.width
        self._content_card.width = w
        self._container.width = w + _DEL_W

    def _content_touch_down(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self._touch_start = touch.pos

    def _content_touch_up(self, widget, touch):
        if not self._touch_start:
            return
        dx = touch.x - self._touch_start[0]
        dy = touch.y - self._touch_start[1]
        self._touch_start = None
        if abs(dx) < dp(12) and abs(dy) < dp(12):
            if self._scroll.scroll_x < 0.05:
                self._on_tap(self._location)
            else:
                # Tap while open → close
                Animation(scroll_x=0, duration=0.2, t='out_quad').start(self._scroll)

    def _delete_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
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
