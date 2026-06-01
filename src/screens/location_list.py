"""LocationListScreen — list of all saved locations with current conditions."""
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivymd.uix.button import MDIconButton
from kivymd.uix.screen import MDScreen

from src.models.location import Location
from src.models.weather import WeatherData
from src.utils.wmo_codes import get_label, get_gradients

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
    """Single location row card."""
    def __init__(self, location: Location, weather: WeatherData | None,
                 on_tap, on_delete, edit_mode: bool, **kwargs):
        super().__init__(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(105),
            padding=[dp(16), dp(12)],
            spacing=dp(12),
            **kwargs,
        )
        self._location = location
        self._on_tap = on_tap

        # Background gradient from weather condition
        top, bottom = get_gradients(weather.current.code if weather else 0)
        with self.canvas.before:
            Color(*top)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Left: city name + condition
        left = BoxLayout(orientation='vertical', size_hint=(1, 1))
        time_lbl = Label(
            text=self._local_time(),
            font_size=sp(12),
            color=(1, 1, 1, 0.65),
            size_hint_y=None,
            height=dp(16),
            halign='left',
            valign='middle',
        )
        time_lbl.bind(size=time_lbl.setter('text_size'))
        left.add_widget(time_lbl)

        city_lbl = Label(
            text=location.city,
            font_size=sp(22),
            bold=True,
            color=(1, 1, 1, 0.97),
            size_hint_y=None,
            height=dp(28),
            halign='left',
            valign='middle',
        )
        city_lbl.bind(size=city_lbl.setter('text_size'))
        left.add_widget(city_lbl)

        if weather:
            cond_lbl = Label(
                text=get_label(weather.current.code),
                font_size=sp(14),
                color=(1, 1, 1, 0.75),
                size_hint_y=None,
                height=dp(20),
                halign='left',
                valign='middle',
            )
            cond_lbl.bind(size=cond_lbl.setter('text_size'))
            left.add_widget(cond_lbl)

            hl_lbl = Label(
                text=f'H:{weather.today_high()}°   L:{weather.today_low()}°',
                font_size=sp(13),
                color=(1, 1, 1, 0.70),
                size_hint_y=None,
                height=dp(18),
                halign='left',
                valign='middle',
            )
            hl_lbl.bind(size=hl_lbl.setter('text_size'))
            left.add_widget(hl_lbl)

        self.add_widget(left)

        # Right: temperature or delete button
        if edit_mode:
            del_btn = MDIconButton(
                icon='minus-circle',
                theme_icon_color='Custom',
                icon_color=(1, 0.35, 0.35, 1),
                icon_size=dp(28),
                size_hint=(None, None),
                size=(dp(44), dp(44)),
                on_release=lambda *_: on_delete(location.zip),
            )
            self.add_widget(del_btn)
        else:
            if weather:
                temp_lbl = Label(
                    text=f'{weather.current.temp}°',
                    font_size=sp(44),
                    color=(1, 1, 1, 0.97),
                    size_hint=(None, 1),
                    width=dp(80),
                    halign='right',
                    valign='middle',
                )
                temp_lbl.bind(size=temp_lbl.setter('text_size'))
                self.add_widget(temp_lbl)

        # Touch handling
        self.bind(on_touch_down=self._touch_down)

    def _touch_down(self, widget, touch):
        if self.collide_point(*touch.pos):
            self._on_tap(self._location)
            return True

    def _update_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    @staticmethod
    def _local_time() -> str:
        from datetime import datetime
        return datetime.now().strftime('%I:%M %p').lstrip('0')


class LocationListScreen(MDScreen):
    def __init__(self, locations: list, weather_map: dict,
                 on_tap, on_add, on_delete, **kwargs):
        super().__init__(**kwargs)
        self._locations = locations
        self._weather_map = weather_map  # dict[zip_str → WeatherData | None]
        self._on_tap = on_tap
        self._on_add = on_add
        self._on_delete = on_delete
        self._edit_mode = False
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

        self._edit_btn = MDIconButton(
            icon='pencil',
            theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.75),
            icon_size=dp(22),
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            on_release=self._toggle_edit,
        )
        top_bar.add_widget(self._edit_btn)

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
                on_delete=self._handle_delete,
                edit_mode=self._edit_mode,
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

    def _toggle_edit(self, *_):
        self._edit_mode = not self._edit_mode
        self._edit_btn.icon = 'check' if self._edit_mode else 'pencil'
        self.clear_widgets()
        self._build_ui()

    def _handle_delete(self, zip_code: str):
        self._on_delete(zip_code)
