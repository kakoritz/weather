"""LocationListScreen v2 — fixes from user review.

Fixed:
- ZIP cards fully rounded corners
- Menu pops OUT+DOWN from the button, not slide-from-bottom
- Autocomplete floats directly under search bar, overlays everything
- C/F toggle instantly re-renders all temps across every card
- After adding a zip, stays on the list page
- Full-row clickable menu items
- Search hint text properly centered/aligned
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
from kivymd.uix.button import MDIconButton
from kivymd.uix.screen import MDScreen

from src.models.location import Location
from src.models.weather import WeatherData
from src.utils.wmo_codes import get_label, get_bg_path, is_night

_DEL_W = dp(80)
_CARD_H = dp(110)
_CARD_RADIUS = dp(18)

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


def _c_or_f(fahrenheit: int, units: str) -> str:
    if units == 'C':
        return f'{round((fahrenheit - 32) * 5 / 9)}°'
    return f'{fahrenheit}°'


# ── City search ───────────────────────────────────────────────────────────────

_CITIES: list = []

def _load_cities():
    global _CITIES
    if _CITIES:
        return
    try:
        path = os.path.join(os.getcwd(), 'assets', 'cities_us.json')
        with open(path) as f:
            _CITIES = json.load(f)
    except Exception:
        _CITIES = []

def search_cities(query: str, limit: int = 5) -> list:
    _load_cities()
    q = query.strip().lower()
    if not q or len(q) < 2:
        return []
    results = []
    for row in _CITIES:
        z, c, s, la, lo = row
        if (z.startswith(q) or c.lower().startswith(q) or
                f'{c.lower()}, {s.lower()}'.startswith(q)):
            results.append({'zip': z, 'city': c, 'state': s, 'lat': la, 'lon': lo})
            if len(results) >= limit:
                break
    return results


# ── Location card ─────────────────────────────────────────────────────────────

class _LocationCard(BoxLayout):
    def __init__(self, location: Location, weather: WeatherData | None,
                 on_tap, on_delete, units: str = 'F', **kwargs):
        super().__init__(size_hint_y=None, height=_CARD_H, **kwargs)
        self._location = location
        self._on_tap = on_tap
        self._on_delete = on_delete
        self._touch_start = None

        scroll = ScrollView(do_scroll_x=True, do_scroll_y=False,
                            bar_width=0, scroll_x=0, effect_cls='ScrollEffect',
                            size_hint=(1, 1))
        self._container = BoxLayout(orientation='horizontal', size_hint=(None, 1))
        self.bind(width=self._on_width)

        # ── Content card with TRUE rounded corners using stencil clipping ──
        self._cc = FloatLayout(size_hint=(None, 1))

        # Stencil: clips ALL children to the rounded rect shape
        from kivy.graphics import StencilPush, StencilUse, StencilPop, StencilUnUse
        with self._cc.canvas.before:
            StencilPush()
            Color(1, 1, 1, 1)
            self._cc_stencil = RoundedRectangle(pos=self._cc.pos,
                                                 size=self._cc.size, radius=[_CARD_RADIUS])
            StencilUse()
        self._cc.bind(
            pos=lambda w, v, r=self._cc_stencil: setattr(r, 'pos', v),
            size=lambda w, v, r=self._cc_stencil: setattr(r, 'size', v),
        )
        with self._cc.canvas.after:
            StencilUnUse()
            StencilPop()

        # Background photo (clipped by stencil)
        night = is_night()
        code = weather.current.code if weather else 0
        abs_bg = os.path.join(os.getcwd(), get_bg_path(code, night))
        if os.path.exists(abs_bg):
            bg = KivyImage(source=abs_bg, size_hint=(1, 1),
                           pos_hint={'x': 0, 'y': 0})
            try: bg.fit_mode = 'cover'
            except: pass
            self._cc.add_widget(bg)

        # Dark overlay
        ov = Widget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        with ov.canvas:
            Color(0, 0, 0, 0.40)
            _ov = Rectangle(pos=ov.pos, size=ov.size)
        ov.bind(pos=lambda w, v, r=_ov: setattr(r, 'pos', v),
                size=lambda w, v, r=_ov: setattr(r, 'size', v))
        self._cc.add_widget(ov)

        # Text
        inner = FloatLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})

        def _lbl(text, fs, bold, alpha, sx, sy, w_dp, h_dp, align):
            l = Label(text=text, font_size=fs, bold=bold, color=(1, 1, 1, alpha),
                      size_hint=(None, None), size=(dp(w_dp), dp(h_dp)),
                      pos_hint=dict(zip(
                          (['x', 'top'] if 'top' in str(sy) else ['x', 'y']),
                          [sx, sy]
                      )),
                      halign=align, valign='middle')
            l.bind(size=l.setter('text_size'))
            return l

        L = 0.04   # left margin fraction
        R = 0.97   # right margin fraction

        inner.add_widget(Label(text=location.city, font_size=sp(23), bold=True,
                               color=(1, 1, 1, 1), size_hint=(None, None),
                               size=(dp(220), dp(30)),
                               pos_hint={'x': L, 'top': 0.97},
                               halign='left', valign='middle'))
        inner.add_widget(Label(text=datetime.now().strftime('%I:%M %p').lstrip('0'),
                               font_size=sp(13), bold=False, color=(1, 1, 1, 1),
                               size_hint=(None, None), size=(dp(140), dp(20)),
                               pos_hint={'x': L, 'top': 0.65},
                               halign='left', valign='middle'))
        if weather:
            inner.add_widget(Label(
                text=_c_or_f(weather.current.temp, units),
                font_size=sp(46), bold=False, color=(1, 1, 1, 1),
                size_hint=(None, None), size=(dp(110), dp(62)),
                pos_hint={'right': R, 'top': 1.02},
                halign='right', valign='middle'))
            inner.add_widget(Label(
                text=get_label(weather.current.code),
                font_size=sp(14), bold=False, color=(1, 1, 1, 1),
                size_hint=(None, None), size=(dp(200), dp(22)),
                pos_hint={'x': L, 'y': 0.04},
                halign='left', valign='middle'))
            inner.add_widget(Label(
                text=f'H:{_c_or_f(weather.today_high() or 0, units)}  '
                     f'L:{_c_or_f(weather.today_low() or 0, units)}',
                font_size=sp(13), bold=False, color=(1, 1, 1, 1),
                size_hint=(None, None), size=(dp(130), dp(20)),
                pos_hint={'right': R, 'y': 0.04},
                halign='right', valign='middle'))

        self._cc.add_widget(inner)
        inner.bind(on_touch_down=self._content_down)
        inner.bind(on_touch_up=self._content_up)
        self._container.add_widget(self._cc)

        # ── Delete zone ─────────────────────────────────────────────
        del_box = BoxLayout(size_hint=(None, 1), width=_DEL_W)
        with del_box.canvas.before:
            Color(0.92, 0.18, 0.18, 1)
            _db = Rectangle(pos=del_box.pos, size=del_box.size)
        del_box.bind(pos=lambda w, v, r=_db: setattr(r, 'pos', v),
                     size=lambda w, v, r=_db: setattr(r, 'size', v))
        del_box.add_widget(MDIconButton(icon='trash-can', theme_icon_color='Custom',
                                         icon_color=(1, 1, 1, 1), icon_size=dp(26),
                                         size_hint=(1, 1)))
        del_box.bind(on_touch_up=self._delete_up)
        self._container.add_widget(del_box)

        scroll.add_widget(self._container)
        self.add_widget(scroll)
        self._scroll = scroll

    def _on_width(self, *_):
        self._cc.width = self.width
        self._container.width = self.width + _DEL_W

    def _content_down(self, w, touch):
        if w.collide_point(*touch.pos):
            self._touch_start = touch.pos

    def _content_up(self, w, touch):
        if not self._touch_start: return
        dx = abs(touch.x - self._touch_start[0])
        self._touch_start = None
        if dx < dp(10):
            if self._scroll.scroll_x < 0.05:
                self._on_tap(self._location)
            else:
                Animation(scroll_x=0, duration=0.2).start(self._scroll)

    def _delete_up(self, w, touch):
        if w.collide_point(*touch.pos):
            self._on_delete(self._location.zip)
            return True


# ── Dropdown menu (pops out from button) ─────────────────────────────────────

class _DropdownMenu(FloatLayout):
    """Compact dropdown that appears below the ⋯ button."""

    def __init__(self, btn_pos, btn_size, storage, on_close,
                 on_edit_list, current_units='F', **kwargs):
        super().__init__(size_hint=(1, 1), **kwargs)

        # Transparent full-screen dim — tap to close
        dim = Widget(size_hint=(1, 1))
        with dim.canvas:
            Color(0, 0, 0, 0.25)
            _d = Rectangle(pos=dim.pos, size=dim.size)
        dim.bind(pos=lambda w, v, r=_d: setattr(r, 'pos', v),
                 size=lambda w, v, r=_d: setattr(r, 'size', v))
        dim.bind(on_touch_down=lambda w, t: on_close()
                 if not self._menu_rect.collide_point(*t.pos) else None)
        self.add_widget(dim)

        # Menu card — positioned below+left of the button
        MENU_W = dp(200)
        ITEM_H = dp(46)
        ITEMS = [
            ('playlist-edit', 'Edit List',       on_edit_list),
            None,
            ('thermometer', 'Fahrenheit °F', lambda: self._set_unit('F', storage, on_close)),
            ('thermometer', 'Celsius °C',    lambda: self._set_unit('C', storage, on_close)),
            None,
            ('bell-outline',        'Notifications',   lambda: None),   # stub — stays open
            ('flag-outline',        'Report an Issue', lambda: None),   # stub — stays open
        ]
        # Count actual items (not separators)
        n_items = sum(1 for x in ITEMS if x is not None)
        n_seps   = sum(1 for x in ITEMS if x is None)
        MENU_H = n_items * ITEM_H + n_seps * dp(1) + dp(10)

        # Position: right-align with button, below it
        mx = max(dp(8), btn_pos[0] + btn_size[0] - MENU_W)
        my = btn_pos[1] - MENU_H - dp(4)

        menu = BoxLayout(orientation='vertical',
                         size_hint=(None, None),
                         size=(MENU_W, MENU_H),
                         pos=(mx, my),
                         padding=[0, dp(6)])
        self._menu_rect = menu

        with menu.canvas.before:
            Color(0.12, 0.14, 0.20, 0.97)
            RoundedRectangle(pos=menu.pos, size=menu.size, radius=[dp(12)])
        menu.bind(pos=lambda w, v: None)

        for item in ITEMS:
            if item is None:
                sep = Widget(size_hint_y=None, height=dp(1))
                with sep.canvas:
                    Color(1, 1, 1, 0.10)
                    _sr = Rectangle(pos=sep.pos, size=sep.size)
                sep.bind(pos=lambda w, v, r=_sr: setattr(r, 'pos', v),
                         size=lambda w, v, r=_sr: setattr(r, 'size', (v[0], 1)))
                menu.add_widget(sep)
                continue

            icon, label, cb = item
            is_checked = (label == 'Fahrenheit °F' and current_units == 'F') or \
                         (label == 'Celsius °C'    and current_units == 'C')

            row = BoxLayout(orientation='horizontal', size_hint_y=None,
                            height=ITEM_H, padding=[dp(14), 0], spacing=dp(10))
            # Subtle hover bg on the row itself
            with row.canvas.before:
                Color(0, 0, 0, 0)   # transparent normally
                Rectangle(pos=row.pos, size=row.size)

            row.add_widget(MDIconButton(
                icon=icon, theme_icon_color='Custom',
                icon_color=(0.30, 0.70, 1, 1) if is_checked else (1, 1, 1, 0.55),
                icon_size=dp(18),
                size_hint=(None, 1), width=dp(30),
            ))
            lbl = Label(text=label, font_size=sp(15), bold=False,
                        color=(0.30, 0.70, 1, 1) if is_checked else (1, 1, 1, 0.90),
                        size_hint=(1, 1), halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            row.add_widget(lbl)

            if is_checked:
                row.add_widget(MDIconButton(
                    icon='check', theme_icon_color='Custom',
                    icon_color=(0.30, 0.70, 1, 1), icon_size=dp(16),
                    size_hint=(None, 1), width=dp(30),
                ))

            _cb = cb
            # Bind to the WHOLE row — on_touch_up fires when finger lifts anywhere on row
            row.bind(on_touch_up=lambda w, t, fn=_cb: (fn(), True)
                     if w.collide_point(*t.pos) else None)
            menu.add_widget(row)

        self.add_widget(menu)

    def _set_unit(self, unit: str, storage, on_close):
        if storage:
            storage.set_units(unit)
        on_close()


# ── Main screen ───────────────────────────────────────────────────────────────

class LocationListScreen(MDScreen):
    def __init__(self, locations: list, weather_map: dict,
                 on_tap, on_add, on_delete, storage=None, **kwargs):
        super().__init__(**kwargs)
        self._locations = list(locations)
        self._weather_map = weather_map
        self._on_tap = on_tap
        self._on_add = on_add
        self._on_delete = on_delete
        self._storage = storage
        self._units = storage.get_units() if storage else 'F'
        self._menu_open = False
        self._build_ui()

    def refresh(self, locations: list, weather_map: dict):
        self._locations = list(locations)
        self._weather_map = weather_map
        self._units = self._storage.get_units() if self._storage else 'F'
        self.clear_widgets()
        self._build_ui()

    def _build_ui(self):
        self._root = FloatLayout()

        # ── Fixed header bar ─────────────────────────────────────────
        self._header = BoxLayout(orientation='vertical', size_hint=(1, None),
                                  height=dp(130), padding=[dp(18), dp(10)],
                                  spacing=dp(8), pos_hint={'top': 1})
        with self._header.canvas.before:
            Color(0.04, 0.05, 0.10, 1)
            _hbg = Rectangle(pos=self._header.pos, size=self._header.size)
        self._header.bind(pos=lambda w, v, r=_hbg: setattr(r, 'pos', v),
                          size=lambda w, v, r=_hbg: setattr(r, 'size', v))

        title_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(44))
        title_lbl = Label(text='Weather', font_size=sp(36), bold=True,
                          color=(1, 1, 1, 0.97), size_hint=(1, 1),
                          halign='left', valign='middle')
        title_lbl.bind(size=title_lbl.setter('text_size'))
        title_row.add_widget(title_lbl)

        self._menu_btn = MDIconButton(
            icon='dots-horizontal-circle-outline',
            theme_icon_color='Custom', icon_color=(1, 1, 1, 0.80),
            icon_size=dp(28), size_hint=(None, None), size=(dp(44), dp(44)),
            on_release=self._open_menu,
        )
        title_row.add_widget(self._menu_btn)
        self._header.add_widget(title_row)

        # Search bar
        search_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                               height=dp(44), spacing=dp(8))
        with search_row.canvas.before:
            Color(0.14, 0.16, 0.22, 1)
            _sbg = RoundedRectangle(pos=search_row.pos, size=search_row.size, radius=[dp(11)])
        search_row.bind(pos=lambda w, v, r=_sbg: setattr(r, 'pos', v),
                        size=lambda w, v, r=_sbg: setattr(r, 'size', v))

        search_row.add_widget(MDIconButton(
            icon='magnify', theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.45), icon_size=dp(18),
            size_hint=(None, 1), width=dp(36),
        ))
        self._field = TextInput(
            hint_text='City, state or ZIP code',
            hint_text_color=(0.65, 0.65, 0.65, 1),
            foreground_color=(1, 1, 1, 1),
            background_color=(0, 0, 0, 0),
            cursor_color=(1, 1, 1, 1),
            font_size=sp(16),
            padding=[0, dp(10), 0, dp(10)],
            multiline=False, size_hint=(1, 1),
        )
        self._field.bind(text=self._on_search_text)
        search_row.add_widget(self._field)
        search_row.add_widget(Widget(size_hint=(None, 1), width=dp(8)))
        self._header.add_widget(search_row)
        self._root.add_widget(self._header)

        # ── Location cards scroll ─────────────────────────────────────
        scroll = ScrollView(do_scroll_y=True, do_scroll_x=False,
                            bar_width=0, size_hint=(1, 1),
                            pos_hint={'top': 0.72})
        cards_box = BoxLayout(orientation='vertical', size_hint_y=None,
                              spacing=dp(10),
                              padding=[dp(14), dp(8), dp(14), dp(80)])
        cards_box.bind(minimum_height=cards_box.setter('height'))

        for loc in self._locations:
            weather = self._weather_map.get(loc.zip)
            card = _LocationCard(location=loc, weather=weather,
                                  on_tap=self._on_tap,
                                  on_delete=self._on_delete,
                                  units=self._units)
            cards_box.add_widget(card)

        scroll.add_widget(cards_box)
        self._root.add_widget(scroll)

        # Autocomplete overlay (floats over everything, starts hidden)
        self._ac_box = BoxLayout(orientation='vertical', size_hint=(None, None),
                                  size=(0, 0), pos=(0, 0))
        with self._ac_box.canvas.before:
            Color(0.10, 0.13, 0.18, 0.98)
            self._ac_bg = RoundedRectangle(pos=self._ac_box.pos,
                                            size=self._ac_box.size, radius=[dp(10)])
        self._ac_box.bind(pos=lambda w, v, r=self._ac_bg: setattr(r, 'pos', v),
                          size=lambda w, v, r=self._ac_bg: setattr(r, 'size', v))
        self._root.add_widget(self._ac_box)

        self.add_widget(self._root)
        self._debounce = None

    # ── Search ────────────────────────────────────────────────────────────────

    def _on_search_text(self, field, text):
        if self._debounce:
            Clock.unschedule(self._debounce)
        if len(text) < 2:
            self._clear_ac()
            return
        self._debounce = Clock.schedule_once(lambda dt: self._do_search(text), 0.22)

    def _do_search(self, query):
        results = search_cities(query)
        self._clear_ac()
        if not results:
            return
        # Position directly under the search bar
        Clock.schedule_once(lambda dt: self._place_ac(results), 0)

    def _place_ac(self, results):
        h = self._header
        ITEM_H = dp(46)
        ac_w = h.width - dp(28)
        ac_h = ITEM_H * len(results)
        ac_x = h.x + dp(14)
        # In Kivy y=0 is BOTTOM. Header bottom edge = h.y.
        # Autocomplete should start at h.y (just below header) and grow DOWNWARD
        # (smaller y values = visually lower on screen).
        ac_y = h.y - ac_h   # top of dropdown = bottom of header; grows down
        # Ensure it doesn't go off screen
        from kivy.core.window import Window
        if ac_y < 0:
            ac_y = 0

        self._ac_box.size = (ac_w, ac_h)
        self._ac_box.pos = (ac_x, ac_y)
        self._ac_box.clear_widgets()

        for r in results:
            row = BoxLayout(orientation='horizontal', size_hint_y=None,
                            height=ITEM_H, padding=[dp(14), 0])
            lbl = Label(
                text=f'{r["city"]}, {r["state"]}  {r["zip"]}',
                font_size=sp(15), color=(1, 1, 1, 0.90),
                size_hint=(1, 1), halign='left', valign='middle',
            )
            lbl.bind(size=lbl.setter('text_size'))
            row.add_widget(lbl)
            _r = r
            row.bind(on_touch_up=lambda w, t, row=_r:
                     self._select_result(row) if w.collide_point(*t.pos) else None)
            self._ac_box.add_widget(row)

    def _clear_ac(self):
        self._ac_box.clear_widgets()
        self._ac_box.size = (0, 0)

    def _select_result(self, row):
        self._field.text = ''
        self._clear_ac()
        loc = Location(zip=row['zip'], city=row['city'], state=row['state'],
                       lat=row['lat'], lon=row['lon'])
        # Add the location then STAY on this screen
        self._on_add(loc)

    # ── Menu ─────────────────────────────────────────────────────────────────

    def _open_menu(self, *_):
        if self._menu_open:
            return
        self._menu_open = True
        units = self._storage.get_units() if self._storage else 'F'
        btn = self._menu_btn
        menu = _DropdownMenu(
            btn_pos=(btn.x, btn.y),
            btn_size=(btn.width, btn.height),
            storage=self._storage,
            on_close=self._close_menu,
            on_edit_list=self._close_menu,   # stub — edit mode coming
            current_units=units,
        )
        self._menu_widget = menu
        self._root.add_widget(menu)

    def _close_menu(self):
        self._menu_open = False
        if hasattr(self, '_menu_widget'):
            self._root.remove_widget(self._menu_widget)
        # Refresh units and rebuild if changed
        new_units = self._storage.get_units() if self._storage else 'F'
        if new_units != self._units:
            self._units = new_units
            self.clear_widgets()
            self._build_ui()
