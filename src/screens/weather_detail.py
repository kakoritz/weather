"""WeatherCarouselScreen and WeatherDetailWidget — the main app view.

WeatherCarouselScreen:
  - Full-screen Kivy Carousel (one slide per location)
  - Bottom navigation bar (page dots + list icon)
  - Handles weather data loading and refresh

WeatherDetailWidget (one per location):
  - Animated WeatherBackground (fills screen behind scroll)
  - Vertical ScrollView with all content
  - Hero: city, temp, condition, H/L, summary text
  - HourlyForecastCard
  - DailyForecastCard
  - DetailCardsGrid
"""
from datetime import datetime

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle
from kivy.lang import Builder
from kivy.uix.carousel import Carousel as _KivyCarousel


class _WeatherCarousel(_KivyCarousel):
    """Carousel that only intercepts predominantly horizontal swipes.
    Prevents vertical finger motion from making the screen wobbly/bouncy.
    """
    def on_touch_move(self, touch):
        dx = abs(touch.x - touch.ox)
        dy = abs(touch.y - touch.oy)
        # Only grab touch if horizontal movement clearly dominates
        if dy > dx * 0.75:
            return False  # Let inner ScrollView handle vertical scrolling
        return super().on_touch_move(touch)
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.carousel import Carousel
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivymd.uix.button import MDIconButton
from kivymd.uix.screen import MDScreen

from src.api.weather import fetch_weather
from src.models.location import Location
from src.models.weather import WeatherData, wind_direction_label
from src.utils.wmo_codes import get_label, get_condition
from src.widgets.weather_bg import WeatherBackground
from src.widgets.hourly_card import HourlyForecastCard
from src.widgets.daily_forecast import DailyForecastCard
from src.widgets.detail_cards import DetailCardsGrid

KV = """
<WeatherCarouselScreen>:
    name: 'weather_carousel'
"""
Builder.load_string(KV)


class WeatherDetailWidget(FloatLayout):
    """Single location's full weather detail view (one Carousel slide)."""

    def __init__(self, location: Location, weather: WeatherData | None = None, **kwargs):
        super().__init__(**kwargs)
        self._location = location
        self._weather = weather
        self._bg: WeatherBackground | None = None
        self._scroll: ScrollView | None = None
        self._content: BoxLayout | None = None
        self._bind_done = False

        # Build immediately with whatever data we have (may be loading state)
        Clock.schedule_once(self._build, 0)

    def show_error(self, msg: str, retry_fn=None):
        """Replace loading state with a tap-to-retry error screen."""
        self._weather = None
        self.clear_widgets()
        self._bg = WeatherBackground(wmo_code=0, size_hint=(1, 1))
        self.add_widget(self._bg)
        content = BoxLayout(orientation='vertical', size_hint=(1, 1), padding=[dp(32), dp(80)])
        content.add_widget(Label(
            text=self._location.city,
            font_size=sp(28), bold=True, color=(1, 1, 1, 0.90),
            size_hint_y=None, height=dp(40), halign='center', valign='middle',
        ))
        content.add_widget(Label(
            text='Unable to load weather.\nCheck your connection.',
            font_size=sp(16), color=(1, 1, 1, 0.65),
            size_hint_y=None, height=dp(56), halign='center', valign='middle',
        ))
        if retry_fn:
            from kivymd.uix.button import MDRaisedButton
            btn = MDRaisedButton(
                text='Retry',
                size_hint=(None, None), size=(dp(120), dp(44)),
                pos_hint={'center_x': 0.5},
                on_release=lambda *_: (self._add_loading_state_fresh(), retry_fn()),
            )
            content.add_widget(btn)
        self.add_widget(content)

    def _add_loading_state_fresh(self):
        self.clear_widgets()
        self._bg = WeatherBackground(wmo_code=0, size_hint=(1, 1))
        self.add_widget(self._bg)
        self._scroll = None
        self._content = None
        Clock.schedule_once(self._build, 0)

    def update_weather(self, weather: WeatherData):
        self._weather = weather
        self.clear_widgets()
        self._bg = None
        self._scroll = None
        self._content = None
        Clock.schedule_once(self._build, 0)

    def _build(self, *_):
        w = self._weather

        # Animated background (fills full widget)
        code = w.current.code if w else 0
        self._bg = WeatherBackground(wmo_code=code, size_hint=(1, 1))
        self.add_widget(self._bg)

        # Scroll overlay (transparent bg, full size)
        self._scroll = ScrollView(
            do_scroll_y=True,
            do_scroll_x=False,
            bar_width=0,
            size_hint=(1, 1),
        )
        self._content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(0), dp(60), dp(0), dp(80)],
            spacing=dp(14),
        )
        self._content.bind(minimum_height=self._content.setter('height'))

        if w is None:
            self._add_loading_state()
        else:
            self._add_weather_content(w)

        self._scroll.add_widget(self._content)
        self.add_widget(self._scroll)

    def _add_loading_state(self):
        self._content.add_widget(Widget(size_hint_y=None, height=dp(120)))
        self._content.add_widget(Label(
            text=self._location.city,
            font_size=sp(36),
            bold=True,
            color=(1, 1, 1, 0.90),
            size_hint_y=None,
            height=dp(48),
            halign='center',
            valign='middle',
        ))
        self._content.add_widget(Label(
            text='Loading…',
            font_size=sp(18),
            color=(1, 1, 1, 0.55),
            size_hint_y=None,
            height=dp(28),
            halign='center',
            valign='middle',
        ))

    def _add_weather_content(self, w: WeatherData):
        today = w.daily[0] if w.daily else None
        code = w.current.code

        # ── Hero section ────────────────────────────
        hero = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(230),
            padding=[dp(16), dp(20), dp(16), 0],
        )

        city_lbl = Label(
            text=self._location.display_name,
            font_size=sp(34),
            bold=True,
            color=(1, 1, 1, 0.97),
            size_hint_y=None,
            height=dp(44),
            halign='center',
            valign='middle',
        )
        city_lbl.bind(size=city_lbl.setter('text_size'))
        hero.add_widget(city_lbl)

        temp_lbl = Label(
            text=f'{w.current.temp}°',
            font_size=sp(88),
            bold=False,
            color=(1, 1, 1, 0.97),
            size_hint_y=None,
            height=dp(100),
            halign='center',
            valign='middle',
        )
        temp_lbl.bind(size=temp_lbl.setter('text_size'))
        hero.add_widget(temp_lbl)

        cond_lbl = Label(
            text=get_label(code),
            font_size=sp(20),
            color=(1, 1, 1, 0.85),
            size_hint_y=None,
            height=dp(28),
            halign='center',
            valign='middle',
        )
        cond_lbl.bind(size=cond_lbl.setter('text_size'))
        hero.add_widget(cond_lbl)

        if today:
            hl_lbl = Label(
                text=f'H:{today.max_temp}°   L:{today.min_temp}°',
                font_size=sp(18),
                color=(1, 1, 1, 0.78),
                size_hint_y=None,
                height=dp(26),
                halign='center',
                valign='middle',
            )
            hl_lbl.bind(size=hl_lbl.setter('text_size'))
            hero.add_widget(hl_lbl)

        self._content.add_widget(hero)

        # ── Summary text card ────────────────────────
        summary = self._build_summary_card(w)
        self._content.add_widget(summary)

        # ── Hourly strip ─────────────────────────────
        today_hours = w.today_hourly()
        if today_hours:
            hourly_card = HourlyForecastCard(entries=today_hours)
            padded = BoxLayout(size_hint_y=None, height=dp(170), padding=[dp(14), 0])
            padded.add_widget(hourly_card)
            self._content.add_widget(padded)

        # ── 10-day forecast ───────────────────────────
        if w.daily:
            daily_card = DailyForecastCard(forecasts=w.daily)
            padded = BoxLayout(size_hint_y=None, padding=[dp(14), 0])
            padded.bind(minimum_height=padded.setter('height'))
            padded.add_widget(daily_card)
            self._content.add_widget(padded)

        # ── Detail cards grid ─────────────────────────
        grid = DetailCardsGrid(data=w)
        padded = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(14), 0, dp(14), 0],
        )
        padded.bind(minimum_height=padded.setter('height'))
        padded.add_widget(grid)
        self._content.add_widget(padded)

        # Attribution
        attrib = Label(
            text='Weather data: Open-Meteo · Maps: OpenStreetMap',
            font_size=sp(11),
            color=(1, 1, 1, 0.40),
            size_hint_y=None,
            height=dp(20),
            halign='center',
            valign='middle',
        )
        attrib.bind(size=attrib.setter('text_size'))
        self._content.add_widget(attrib)

    def _build_summary_card(self, w: WeatherData) -> Widget:
        """Build the text summary card that describes the next several hours."""
        today = w.daily[0] if w.daily else None
        now_h = datetime.now().hour

        # Build a simple summary sentence from hourly data
        hours = w.today_hourly()
        try:
            current_cond = get_label(w.current.code)
            if hours:
                later_hours = [h for h in hours if datetime.fromisoformat(h.time).hour > now_h + 2]
                if later_hours:
                    later_code = later_hours[0].code
                    later_label = get_label(later_code)
                    later_time_str = datetime.fromisoformat(later_hours[0].time).strftime('%-I%p')
                    if later_code != w.current.code:
                        summary_text = f'{current_cond} conditions changing to {later_label} around {later_time_str}.'
                    else:
                        summary_text = f'{current_cond} throughout the day.'
                else:
                    summary_text = f'{current_cond} conditions expected.'
            else:
                summary_text = f'{current_cond} conditions.'
            if today and today.precip_prob > 30:
                summary_text += f' {today.precip_prob}% chance of precipitation.'
        except Exception:
            summary_text = get_label(w.current.code)

        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(20), dp(14)],
        )
        card.bind(minimum_height=card.setter('height'))

        with card.canvas.before:
            Color(0, 0, 0, 0.22)
            rr = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(16)])
        card.bind(
            pos=lambda w, v: setattr(rr, 'pos', v),
            size=lambda w, v: setattr(rr, 'size', v),
        )

        lbl = Label(
            text=summary_text,
            font_size=sp(14),
            color=(1, 1, 1, 0.85),
            size_hint_y=None,
            halign='left',
            valign='middle',
        )
        lbl.bind(
            size=lambda w, v: setattr(lbl, 'text_size', (v[0], None)),
            texture_size=lambda w, v: setattr(lbl, 'height', v[1] + dp(4)),
        )
        card.add_widget(lbl)
        return card


class _BottomNavBar(Widget):
    """Bottom navigation: page dots + list button."""
    def __init__(self, carousel: Carousel, on_list: callable, **kwargs):
        super().__init__(**kwargs)
        self._carousel = carousel
        self._on_list = on_list
        self._num_pages = 0

        from kivy.graphics import InstructionGroup
        with self.canvas.before:
            Color(0, 0, 0, 0.38)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        # Dedicated group for dots so we can clear it atomically (no list.remove crash)
        self._dots_group = InstructionGroup()
        self.canvas.add(self._dots_group)

        self.bind(pos=self._redraw_bg, size=self._redraw_bg)
        carousel.bind(current_slide=self._redraw_dots)

    def _redraw_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._redraw_dots()

    def set_num_pages(self, n: int):
        self._num_pages = n
        self._redraw_dots()

    def _redraw_dots(self, *_):
        # Clear the dots group atomically — no per-instruction remove calls
        self._dots_group.clear()

        if self._num_pages < 2:
            return

        try:
            idx = self._carousel.slides.index(self._carousel.current_slide)
        except (ValueError, AttributeError):
            idx = 0

        cx = self.center_x
        cy = self.center_y
        dot_r = dp(4)
        spacing = dp(14)
        total_w = (self._num_pages - 1) * spacing
        start_x = cx - total_w / 2

        for i in range(self._num_pages):
            if i == idx:
                self._dots_group.add(Color(1, 1, 1, 0.92))
                r = dot_r
            else:
                self._dots_group.add(Color(1, 1, 1, 0.40))
                r = dot_r * 0.75
                x = start_x + i * spacing
                self._dots_group.add(Ellipse(pos=(x - r, cy - r), size=(r*2, r*2)))


class WeatherCarouselScreen(MDScreen):
    def __init__(self, locations: list, storage, **kwargs):
        super().__init__(**kwargs)
        self._locations = list(locations)
        self._storage = storage
        self._weather_map: dict = {}
        self._detail_widgets: list = []
        self._carousel: Carousel | None = None
        self._nav_bar: _BottomNavBar | None = None
        self._build_ui()
        self._load_all_weather()

    def _build_ui(self):
        root = FloatLayout(size_hint=(1, 1))

        self._carousel = _WeatherCarousel(
            direction='right',
            loop=False,
            size_hint=(1, 1),
            scroll_distance=dp(20),
        )

        for loc in self._locations:
            cached = self._storage.get_cached_weather(loc.zip)
            widget = WeatherDetailWidget(location=loc, weather=cached)
            self._detail_widgets.append(widget)
            self._carousel.add_widget(widget)

        root.add_widget(self._carousel)

        # Bottom nav bar
        self._nav_bar = _BottomNavBar(
            carousel=self._carousel,
            on_list=self._go_to_list,
            pos_hint={'bottom': 1},
            size_hint=(1, None),
            height=dp(52),
        )
        self._nav_bar.set_num_pages(len(self._locations))
        root.add_widget(self._nav_bar)

        # List icon (bottom right)
        list_btn = MDIconButton(
            icon='format-list-bulleted',
            theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.80),
            icon_size=dp(22),
            size_hint=(None, None),
            size=(dp(44), dp(44)),
            pos_hint={'right': 0.97, 'y': 0.005},
            on_release=self._go_to_list,
        )
        root.add_widget(list_btn)

        self.add_widget(root)

    def _load_all_weather(self):
        for i, loc in enumerate(self._locations):
            cached = self._storage.get_cached_weather(loc.zip)
            if cached is None:
                self._fetch_weather(i, loc)
            else:
                self._weather_map[loc.zip] = cached

    def _fetch_weather(self, idx: int, loc: Location):
        def on_success(data: WeatherData):
            self._storage.save_weather_cache(loc.zip, data)
            self._weather_map[loc.zip] = data

            def _update(dt):
                if idx < len(self._detail_widgets):
                    self._detail_widgets[idx].update_weather(data)
            Clock.schedule_once(_update, 0)

        def on_error(msg: str):
            def _show_error(dt):
                if idx < len(self._detail_widgets):
                    self._detail_widgets[idx].show_error(msg, retry_fn=lambda: self._fetch_weather(idx, loc))
            Clock.schedule_once(_show_error, 0)

        fetch_weather(loc.lat, loc.lon, loc.zip, on_success, on_error)

    def navigate_to(self, zip_code: str):
        """Jump carousel to the slide for the given zip code."""
        for i, loc in enumerate(self._locations):
            if loc.zip == zip_code:
                if i < len(self._detail_widgets):
                    self._carousel.load_slide(self._detail_widgets[i])
                break

    def add_location(self, location: Location):
        """Add a new location slide and start loading its weather."""
        self._locations.append(location)
        cached = self._storage.get_cached_weather(location.zip)
        widget = WeatherDetailWidget(location=location, weather=cached)
        self._detail_widgets.append(widget)
        self._carousel.add_widget(widget)
        self._nav_bar.set_num_pages(len(self._locations))
        if cached is None:
            self._fetch_weather(len(self._locations) - 1, location)
        self._carousel.load_slide(widget)

    def remove_location(self, zip_code: str):
        """Remove a location slide."""
        for i, loc in enumerate(self._locations):
            if loc.zip == zip_code:
                widget = self._detail_widgets.pop(i)
                self._locations.pop(i)
                self._carousel.remove_widget(widget)
                self._nav_bar.set_num_pages(len(self._locations))
                break

    def refresh_current(self):
        """Force-refresh weather for the currently visible slide."""
        try:
            idx = self._carousel.slides.index(self._carousel.current_slide)
            loc = self._locations[idx]
            self._fetch_weather(idx, loc)
        except (ValueError, IndexError):
            pass

    def _go_to_list(self, *_):
        self.manager.current = 'location_list'

    @property
    def weather_map(self) -> dict:
        return self._weather_map

    @property
    def locations(self) -> list:
        return list(self._locations)
