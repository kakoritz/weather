"""LocationListScreen — redesigned per v2 spec.

Layout:
  "Weather" heading (large, left-aligned)
  Search bar (search icon, replaces + button, shows autocomplete top-5)
  Location cards (background photo, city/time/temp/condition/H-L, rounded)
  Menu button (⋯ circle) top-right opens settings popup

Settings menu (groups):
  Group 1: Edit List | Notifications
  Group 2: ● Fahrenheit / ○ Celsius
  Group 3: Report an Issue

Edit mode: red minus left, same swipe-left trash-icon confirmation.
"""
import json
import os
from datetime import datetime

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
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivymd.uix.button import MDIconButton, MDRaisedButton, MDFlatButton
from kivymd.uix.screen import MDScreen

from src.models.location import Location
from src.models.weather import WeatherData
from src.utils.wmo_codes import get_label, get_bg_path, is_night

_DEL_W = dp(80)
_CARD_H = dp(110)

KV = """
<LocationListScreen>:
    name: 'location_list'
    canvas.before:
        Color:
            rgba: 0.04, 0.05, 0.10, 1
        Rectangle:
            pos: self.pos
            size: self.size
"""
Builder.load_string(KV)

# ── City search database ──────────────────────────────────────────────────────

_CITIES: list = []

def _load_cities():
    global _CITIES
    if _CITIES:
        return
    try:
        path = os.path.join(os.getcwd(), 'assets', 'cities_us.json')
        with open(path) as f:
            _CITIES = json.load(f)  # [[zip,city,state,lat,lon], ...]
    except Exception:
        _CITIES = []

def search_cities(query: str, limit: int = 5) -> list:
    """Return top matches for a zip, city, or city+state query."""
    _load_cities()
    q = query.strip().lower()
    if not q or len(q) < 2:
        return []
    results = []
    for row in _CITIES:
        z, c, s, la, lo = row
        if (z.startswith(q) or
                c.lower().startswith(q) or
                f'{c.lower()}, {s.lower()}'.startswith(q)):
            results.append({'zip': z, 'city': c, 'state': s, 'lat': la, 'lon': lo})
            if len(results) >= limit:
                break
    return results


# ── Single location card ──────────────────────────────────────────────────────

class _LocationCard(BoxLayout):
    """Card with background photo, swipe-left to delete (horizontal ScrollView)."""

    def __init__(self, location: Location, weather: WeatherData | None,
                 on_tap, on_delete, edit_mode: bool = False, **kwargs):
        super().__init__(size_hint_y=None, height=_CARD_H, **kwargs)
        self._location = location
        self._on_tap = on_tap
        self._on_delete = on_delete
        self._edit_mode = edit_mode
        self._touch_start = None

        scroll = ScrollView(
            do_scroll_x=True, do_scroll_y=False,
            bar_width=0, scroll_x=0, effect_cls='ScrollEffect',
            size_hint=(1, 1),
        )
        self._container = BoxLayout(orientation='horizontal', size_hint=(None, 1))
        self.bind(width=self._on_width)

        # ── Content card ─────────────────────────────────────────────
        self._content_card = FloatLayout(size_hint=(None, 1))

        # Background photo
        night = is_night()
        code = weather.current.code if weather else 0
        abs_bg = os.path.join(os.getcwd(), get_bg_path(code, night))
        if os.path.exists(abs_bg):
            bg = KivyImage(source=abs_bg, size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
            try: bg.fit_mode = 'cover'
            except: pass
            self._content_card.add_widget(bg)

        ov = Widget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        with ov.canvas:
            Color(0, 0, 0, 0.40)
            _ov = Rectangle(pos=ov.pos, size=ov.size)
        ov.bind(pos=lambda w, v, r=_ov: setattr(r, 'pos', v),
                size=lambda w, v, r=_ov: setattr(r, 'size', v))
        self._content_card.add_widget(ov)

        # Text layout: 2x2 grid (city/time top-left, temp top-right,
        #              condition bottom-left, H/L bottom-right)
        inner = FloatLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        # Top-left: city name + time
        city_lbl = Label(
            text=location.city,
            font_size=sp(21), bold=True, color=(1, 1, 1, 1),
            size_hint=(None, None), size=(dp(220), dp(28)),
            pos_hint={'x': 0.04, 'top': 0.96}, halign='left', valign='middle',
        )
        city_lbl.bind(size=city_lbl.setter('text_size'))
        inner.add_widget(city_lbl)

        time_lbl = Label(
            text=datetime.now().strftime('%I:%M %p').lstrip('0'),
            font_size=sp(13), bold=False, color=(1, 1, 1, 0.70),
            size_hint=(None, None), size=(dp(160), dp(20)),
            pos_hint={'x': 0.04, 'top': 0.68}, halign='left', valign='middle',
        )
        inner.add_widget(time_lbl)

        # Top-right: temperature
        if weather:
            temp_lbl = Label(
                text=f'{weather.current.temp}°',
                font_size=sp(44), bold=False, color=(1, 1, 1, 1),
                size_hint=(None, None), size=(dp(90), dp(60)),
                pos_hint={'right': 0.97, 'top': 1.0}, halign='right', valign='middle',
            )
            temp_lbl.bind(size=temp_lbl.setter('text_size'))
            inner.add_widget(temp_lbl)

        # Bottom-left: condition
        if weather:
            cond_lbl = Label(
                text=get_label(weather.current.code),
                font_size=sp(14), bold=False, color=(1, 1, 1, 0.85),
                size_hint=(None, None), size=(dp(200), dp(22)),
                pos_hint={'x': 0.04, 'y': 0.04}, halign='left', valign='middle',
            )
            cond_lbl.bind(size=cond_lbl.setter('text_size'))
            inner.add_widget(cond_lbl)

        # Bottom-right: H/L
        if weather:
            hl_lbl = Label(
                text=f'H:{weather.today_high()}°  L:{weather.today_low()}°',
                font_size=sp(13), bold=False, color=(1, 1, 1, 0.75),
                size_hint=(None, None), size=(dp(130), dp(20)),
                pos_hint={'right': 0.97, 'y': 0.04}, halign='right', valign='middle',
            )
            hl_lbl.bind(size=hl_lbl.setter('text_size'))
            inner.add_widget(hl_lbl)

        self._content_card.add_widget(inner)

        # Edit mode: minus button on the left
        if edit_mode:
            minus = Widget(size_hint=(None, 1), width=dp(36), pos_hint={'x': 0, 'y': 0})
            with minus.canvas:
                Color(0.92, 0.18, 0.18, 1)
                Rectangle(pos=minus.pos, size=minus.size)
            minus.bind(pos=lambda w, v: None)  # will redraw with bind
            minus_lbl = Label(text='−', font_size=sp(24), bold=True,
                              color=(1, 1, 1, 1), size_hint=(1, 1))
            minus.add_widget(minus_lbl)
            minus.bind(on_touch_up=lambda w, t: self._on_delete(location.zip)
                       if w.collide_point(*t.pos) else None)
            # overlay on top of content
            minus_wrap = FloatLayout(size_hint=(None, 1), width=dp(36),
                                     pos_hint={'x': 0, 'y': 0})
            with minus_wrap.canvas.before:
                Color(0.92, 0.18, 0.18, 1)
                _mr = Rectangle(pos=minus_wrap.pos, size=minus_wrap.size)
            minus_wrap.bind(pos=lambda w, v, r=_mr: setattr(r, 'pos', v),
                            size=lambda w, v, r=_mr: setattr(r, 'size', v))
            minus_wrap.add_widget(Label(text='−', font_size=sp(28), bold=True,
                                        color=(1, 1, 1, 1), size_hint=(1, 1)))
            minus_wrap.bind(on_touch_up=self._minus_touch)
            self._content_card.add_widget(minus_wrap)

        inner.bind(on_touch_down=self._content_touch_down)
        inner.bind(on_touch_up=self._content_touch_up)
        self._container.add_widget(self._content_card)

        # ── Delete button ─────────────────────────────────────────────
        del_btn = BoxLayout(size_hint=(None, 1), width=_DEL_W)
        with del_btn.canvas.before:
            Color(0.92, 0.18, 0.18, 1)
            _db = Rectangle(pos=del_btn.pos, size=del_btn.size)
        del_btn.bind(pos=lambda w, v, r=_db: setattr(r, 'pos', v),
                     size=lambda w, v, r=_db: setattr(r, 'size', v))
        del_icon = MDIconButton(
            icon='trash-can', theme_icon_color='Custom',
            icon_color=(1, 1, 1, 1), icon_size=dp(26),
            size_hint=(1, 1),
        )
        del_btn.add_widget(del_icon)
        del_btn.bind(on_touch_up=self._delete_touch)
        self._container.add_widget(del_btn)

        scroll.add_widget(self._container)
        self.add_widget(scroll)
        self._scroll = scroll

    def _on_width(self, *_):
        self._content_card.width = self.width
        self._container.width = self.width + _DEL_W

    def _content_touch_down(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self._touch_start = touch.pos

    def _content_touch_up(self, widget, touch):
        if not self._touch_start:
            return
        dx = abs(touch.x - self._touch_start[0])
        self._touch_start = None
        if dx < dp(12):
            if self._scroll.scroll_x < 0.05:
                self._on_tap(self._location)
            else:
                Animation(scroll_x=0, duration=0.2, t='out_quad').start(self._scroll)

    def _delete_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self._on_delete(self._location.zip)
            return True

    def _minus_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
            self._on_delete(self._location.zip)
            return True


# ── Search bar with autocomplete ──────────────────────────────────────────────

class _SearchBar(BoxLayout):
    def __init__(self, on_select, **kwargs):
        super().__init__(orientation='vertical',
                         size_hint_y=None, **kwargs)
        self._on_select = on_select
        self._debounce = None
        self._dropdown = None
        self.bind(minimum_height=self.setter('height'))
        self._build()

    def _build(self):
        # Search input row
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(48),
                        spacing=dp(8), padding=[dp(12), dp(6)])
        with row.canvas.before:
            Color(0.14, 0.16, 0.22, 1)
            self._row_bg = RoundedRectangle(pos=row.pos, size=row.size, radius=[dp(12)])
        row.bind(pos=lambda w, v, r=self._row_bg: setattr(r, 'pos', v),
                 size=lambda w, v, r=self._row_bg: setattr(r, 'size', v))

        row.add_widget(MDIconButton(
            icon='magnify', theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.50), icon_size=dp(20),
            size_hint=(None, 1), width=dp(36),
        ))
        self._field = TextInput(
            hint_text='Search city, state or ZIP code',
            hint_text_color=(0.7, 0.7, 0.7, 0.7),
            foreground_color=(1, 1, 1, 1),
            background_color=(0, 0, 0, 0),
            cursor_color=(1, 1, 1, 1),
            font_size=sp(16),
            multiline=False,
            size_hint=(1, 1),
        )
        self._field.bind(text=self._on_text)
        row.add_widget(self._field)
        self.add_widget(row)

        # Autocomplete dropdown (built on demand)
        self._dropdown_box = BoxLayout(orientation='vertical', size_hint_y=None, height=0)
        self.add_widget(self._dropdown_box)

    def _on_text(self, field, text):
        if self._debounce:
            Clock.unschedule(self._debounce)
        if len(text) < 2:
            self._clear_dropdown()
            return
        self._debounce = Clock.schedule_once(lambda dt: self._do_search(text), 0.25)

    def _do_search(self, query):
        results = search_cities(query)
        self._clear_dropdown()
        if not results:
            return
        for r in results:
            btn = BoxLayout(size_hint_y=None, height=dp(44), padding=[dp(16), 0])
            with btn.canvas.before:
                Color(0.12, 0.14, 0.20, 1)
                RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(6)])
            lbl = Label(
                text=f'{r["city"]}, {r["state"]}  {r["zip"]}',
                font_size=sp(15), color=(1, 1, 1, 0.90),
                halign='left', valign='middle', size_hint=(1, 1),
            )
            lbl.bind(size=lbl.setter('text_size'))
            btn.add_widget(lbl)
            btn.bind(on_touch_up=lambda w, t, row=r: (
                self._select(row) if w.collide_point(*t.pos) else None
            ))
            self._dropdown_box.add_widget(btn)
        self._dropdown_box.height = dp(44) * len(results)

    def _clear_dropdown(self):
        self._dropdown_box.clear_widgets()
        self._dropdown_box.height = 0

    def _select(self, row):
        self._field.text = ''
        self._clear_dropdown()
        self._on_select(row)


# ── Settings menu popup ───────────────────────────────────────────────────────

class _SettingsMenu(FloatLayout):
    """Full-screen overlay with a bottom sheet menu."""

    def __init__(self, storage, on_close, on_edit_list, on_celsius, on_fahrenheit,
                 current_units='F', **kwargs):
        super().__init__(size_hint=(1, 1), **kwargs)
        self._storage = storage
        self._on_close = on_close

        # Dim background — tap to close
        bg = Widget(size_hint=(1, 1))
        with bg.canvas:
            Color(0, 0, 0, 0.55)
            _bg = Rectangle(pos=bg.pos, size=bg.size)
        bg.bind(pos=lambda w, v, r=_bg: setattr(r, 'pos', v),
                size=lambda w, v, r=_bg: setattr(r, 'size', v))
        bg.bind(on_touch_down=lambda w, t: on_close() if w.collide_point(*t.pos) else None)
        self.add_widget(bg)

        # Sheet panel
        sheet = BoxLayout(orientation='vertical',
                          size_hint=(1, None), height=dp(320),
                          pos_hint={'bottom': 1}, padding=[0, dp(8)])
        with sheet.canvas.before:
            Color(0.10, 0.12, 0.16, 1)
            RoundedRectangle(pos=sheet.pos, size=sheet.size, radius=[dp(20), dp(20), 0, 0])
        sheet.bind(pos=lambda w, v: None)  # static
        self.add_widget(sheet)

        # Pull indicator
        indicator = Widget(size_hint_y=None, height=dp(20))
        with indicator.canvas:
            Color(1, 1, 1, 0.25)
            RoundedRectangle(pos=(0, 0), size=(dp(40), dp(4)), radius=[dp(2)])
        indicator.bind(pos=lambda w, v: setattr(
            indicator.canvas.children[-1], 'pos',
            (v[0] + w.width/2 - dp(20), v[1] + dp(8))
        ))
        sheet.add_widget(indicator)

        def _row(icon, label, on_tap, right_widget=None):
            r = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(52),
                          padding=[dp(20), 0], spacing=dp(14))
            r.add_widget(MDIconButton(icon=icon, theme_icon_color='Custom',
                                      icon_color=(1, 1, 1, 0.70), icon_size=dp(20),
                                      size_hint=(None, 1), width=dp(36)))
            r.add_widget(Label(text=label, font_size=sp(16), bold=False,
                               color=(1, 1, 1, 0.90), size_hint=(1, 1),
                               halign='left', valign='middle'))
            if right_widget:
                r.add_widget(right_widget)
            r.bind(on_touch_up=lambda w, t: on_tap() if w.collide_point(*t.pos) else None)
            return r

        # Group 1 separator label
        g1 = Label(text='PREFERENCES', font_size=sp(11), bold=False,
                   color=(1, 1, 1, 0.35), size_hint_y=None, height=dp(28),
                   halign='left', valign='middle', padding=[dp(20), 0])
        g1.bind(size=g1.setter('text_size'))
        sheet.add_widget(g1)

        sheet.add_widget(_row('pencil', 'Edit List', on_edit_list))

        # Fahrenheit / Celsius with check
        def _unit_row(label, unit):
            chk = MDIconButton(
                icon='check-circle' if current_units == unit else 'circle-outline',
                theme_icon_color='Custom',
                icon_color=(0.30, 0.70, 1, 1) if current_units == unit else (1, 1, 1, 0.40),
                icon_size=dp(20), size_hint=(None, 1), width=dp(36),
            )
            def _tap():
                if unit == 'C': on_celsius()
                else: on_fahrenheit()
                on_close()
            return _row('thermometer', label, _tap, right_widget=chk)

        sheet.add_widget(_unit_row('Fahrenheit °F', 'F'))
        sheet.add_widget(_unit_row('Celsius °C', 'C'))

        # Group 2
        div = Widget(size_hint_y=None, height=dp(1))
        with div.canvas:
            Color(1, 1, 1, 0.10)
            Rectangle(pos=div.pos, size=div.size)
        div.bind(pos=lambda w, v: [setattr(div.canvas.children[-1], 'pos', v),
                                    setattr(div.canvas.children[-1], 'size', (w.width, 1))])
        sheet.add_widget(div)

        def _notif():
            on_close()  # placeholder — Notifications coming next session
        def _report():
            on_close()  # placeholder — Report an Issue coming next session

        sheet.add_widget(_row('bell', 'Notifications', _notif))
        sheet.add_widget(_row('alert-circle-outline', 'Report an Issue', _report))
        sheet.add_widget(Widget(size_hint_y=None, height=dp(16)))


# ── Main screen ───────────────────────────────────────────────────────────────

class LocationListScreen(MDScreen):
    def __init__(self, locations: list, weather_map: dict,
                 on_tap, on_add, on_delete, storage=None, **kwargs):
        super().__init__(**kwargs)
        self._locations = locations
        self._weather_map = weather_map
        self._on_tap = on_tap
        self._on_add = on_add
        self._on_delete = on_delete
        self._storage = storage
        self._edit_mode = False
        self._menu_open = False
        self._build_ui()

    def refresh(self, locations: list, weather_map: dict):
        self._locations = locations
        self._weather_map = weather_map
        self.clear_widgets()
        self._build_ui()

    def _build_ui(self):
        root = FloatLayout()

        # ── Header ──────────────────────────────────────────────────────────
        header = BoxLayout(orientation='vertical', size_hint=(1, None),
                           height=dp(130), padding=[dp(18), dp(14)], spacing=dp(8),
                           pos_hint={'top': 1})
        with header.canvas.before:
            Color(0.04, 0.05, 0.10, 1)
            _hbg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda w, v, r=_hbg: setattr(r, 'pos', v),
                    size=lambda w, v, r=_hbg: setattr(r, 'size', v))

        # "Weather" title row
        title_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(44))
        title_lbl = Label(
            text='Weather',
            font_size=sp(36), bold=True, color=(1, 1, 1, 0.97),
            size_hint=(1, 1), halign='left', valign='middle',
        )
        title_lbl.bind(size=title_lbl.setter('text_size'))
        title_row.add_widget(title_lbl)

        # ⋯ menu button (circle with ellipsis)
        menu_btn = MDIconButton(
            icon='dots-horizontal-circle-outline',
            theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.80),
            icon_size=dp(28),
            size_hint=(None, None), size=(dp(44), dp(44)),
            on_release=self._open_menu,
        )
        title_row.add_widget(menu_btn)
        header.add_widget(title_row)

        # Search bar
        self._search = _SearchBar(
            on_select=self._on_search_select,
            size_hint=(1, None),
        )
        header.add_widget(self._search)
        root.add_widget(header)

        # ── Location cards ───────────────────────────────────────────────────
        scroll = ScrollView(do_scroll_y=True, do_scroll_x=False,
                            bar_width=0, size_hint=(1, 1),
                            pos_hint={'top': 0.72})
        cards_box = BoxLayout(orientation='vertical', size_hint_y=None,
                              spacing=dp(10), padding=[dp(14), dp(6), dp(14), dp(80)])
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
        self.add_widget(root)
        self._root = root

    def _on_search_select(self, row):
        """User picked a city from autocomplete."""
        from src.models.location import Location
        loc = Location(
            zip=row['zip'], city=row['city'], state=row['state'],
            lat=row['lat'], lon=row['lon'],
        )
        self._on_add(loc)

    def _handle_delete(self, zip_code: str):
        self._on_delete(zip_code)

    def _open_menu(self, *_):
        if self._menu_open:
            return
        self._menu_open = True
        units = self._storage.get_units() if self._storage else 'F'
        menu = _SettingsMenu(
            storage=self._storage,
            on_close=self._close_menu,
            on_edit_list=self._toggle_edit,
            on_celsius=lambda: self._set_units('C'),
            on_fahrenheit=lambda: self._set_units('F'),
            current_units=units,
        )
        self._menu_widget = menu
        self._root.add_widget(menu)

    def _close_menu(self):
        self._menu_open = False
        if hasattr(self, '_menu_widget'):
            self._root.remove_widget(self._menu_widget)

    def _toggle_edit(self):
        self._close_menu()
        self._edit_mode = not self._edit_mode
        self.clear_widgets()
        self._build_ui()

    def _set_units(self, units: str):
        if self._storage:
            self._storage.set_units(units)
