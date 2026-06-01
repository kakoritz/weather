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
from src.utils.wmo_codes import get_label, get_condition, get_bg_path, get_icon_path, is_night
from src.widgets.hourly_card import HourlyForecastCard
from src.widgets.daily_forecast import DailyForecastCard
from src.widgets.detail_cards import DetailCardsGrid

# Day sky blue — the universal daytime background under all conditions
_DAY_SKY = (0.22, 0.60, 0.86, 1)
_NIGHT_SKY = (0.06, 0.10, 0.22, 1)

KV = """
<WeatherCarouselScreen>:
    name: 'weather_carousel'
"""
Builder.load_string(KV)


class _WeatherCarousel(_KivyCarousel):
    """Swipe completely disabled — navigation is tap-arrow only."""
    def on_touch_move(self, touch):
        return False   # No swipe at all; arrows handle navigation


class WeatherDetailWidget(FloatLayout):
    """Single location's full weather detail view (one Carousel slide)."""

    def __init__(self, location: Location, weather: WeatherData | None = None, **kwargs):
        super().__init__(**kwargs)
        self._location = location
        self._weather = weather
        self._scroll: ScrollView | None = None
        self._content: BoxLayout | None = None
        self._sky_rect = None  # The solid sky-blue background rectangle

        Clock.schedule_once(self._build, 0)

    def _draw_sky(self):
        """Draw or update the sky-blue solid background rectangle."""
        self.canvas.before.clear()
        night = is_night()
        col = _NIGHT_SKY if night else _DAY_SKY
        with self.canvas.before:
            Color(*col)
            self._sky_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_sky, size=self._update_sky)

    def _update_sky(self, *_):
        if self._sky_rect:
            self._sky_rect.pos = self.pos
            self._sky_rect.size = self.size

    def show_error(self, msg: str, retry_fn=None):
        """Replace loading state with an error screen — city name centered + Retry."""
        self._weather = None
        self.clear_widgets()
        self._draw_sky()
        # Use a FloatLayout so content is truly centred regardless of screen height
        fl = FloatLayout(size_hint=(1, 1))
        box = BoxLayout(
            orientation='vertical',
            size_hint=(0.8, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            spacing=dp(14),
            padding=[0, 0],
        )
        box.bind(minimum_height=box.setter('height'))
        for text, sz, bold, alpha in [
            (self._location.city, sp(30), True, 0.95),
            ('Unable to load weather.\nCheck your connection.', sp(15), False, 0.65),
        ]:
            lbl = Label(text=text, font_size=sz, bold=bold,
                        color=(1, 1, 1, alpha), size_hint_y=None, height=dp(48) if bold else dp(44),
                        halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            box.add_widget(lbl)
        if retry_fn:
            from kivymd.uix.button import MDRaisedButton
            btn = MDRaisedButton(
                text='Retry',
                size_hint=(None, None), size=(dp(120), dp(44)),
                pos_hint={'center_x': 0.5},
                on_release=lambda *_: (self._add_loading_state_fresh(), retry_fn()),
            )
            box.add_widget(btn)
        fl.add_widget(box)
        self.add_widget(fl)

    def _add_loading_state_fresh(self):
        self.clear_widgets()
        self._sky_rect = None
        self._scroll = None
        self._content = None
        Clock.schedule_once(self._build, 0)

    def update_weather(self, weather: WeatherData):
        self._weather = weather
        self.clear_widgets()
        self._sky_rect = None
        self._scroll = None
        self._content = None
        Clock.schedule_once(self._build, 0)

    def _build(self, *_):
        w = self._weather

        # Solid sky-blue background for the entire screen (no canvas animations)
        self._draw_sky()

        # Scroll view — flush to top of screen, no overscroll
        self._scroll = ScrollView(
            do_scroll_y=True,
            do_scroll_x=False,
            bar_width=0,
            size_hint=(1, 1),
            scroll_type=['bars', 'content'],
            # Prevent rubber-band bounce past the top edge
            effect_cls='ScrollEffect',
        )
        self._content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(0), dp(0), dp(0), dp(80)],  # no top padding — hero is flush to top
            spacing=dp(0),  # hero has no gap above it; gaps added per-card via padding
        )
        self._content.bind(minimum_height=self._content.setter('height'))

        if w is None:
            self._add_loading_state()
        else:
            self._add_weather_content(w)

        self._scroll.add_widget(self._content)
        self.add_widget(self._scroll)

    def _add_loading_state(self):
        """Skeleton loading state — pre-populated layout with placeholder values."""
        # Hero placeholder (matches hero card dimensions)
        hero = FloatLayout(size_hint_y=None, height=dp(300))
        # Dim placeholder background
        with hero.canvas.before:
            Color(0, 0, 0, 0.25)
            _h_rect = Rectangle(pos=hero.pos, size=hero.size)
        hero.bind(
            pos=lambda w, v, r=_h_rect: setattr(r, 'pos', v),
            size=lambda w, v, r=_h_rect: setattr(r, 'size', v),
        )
        text_layer = BoxLayout(orientation='vertical', size_hint=(1, 1),
                               pos_hint={'x': 0, 'y': 0}, padding=[dp(16), dp(20)], spacing=dp(4))
        for txt, sz, bold, alpha in [
            (self._location.display_name, sp(30), True, 0.90),
            ('--°', sp(90), False, 0.55),
            ('Retrieving weather…', sp(18), False, 0.50),
            ('H:--°   L:--°', sp(17), False, 0.45),
        ]:
            lbl = Label(text=txt, font_size=sz, bold=bold, color=(1, 1, 1, alpha),
                        size_hint_y=None, height=dp(108) if '°' in txt and len(txt) <= 4 else dp(32),
                        halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            text_layer.add_widget(lbl)
        hero.add_widget(text_layer)
        self._content.add_widget(hero)

        # Skeleton cards below
        self._content.add_widget(Widget(size_hint_y=None, height=dp(12)))
        for h in [dp(60), dp(170), dp(400)]:
            ph = Widget(size_hint_y=None, height=h)
            with ph.canvas:
                Color(0, 0, 0, 0.15)
                _rr = RoundedRectangle(pos=ph.pos, size=ph.size, radius=[dp(14)])
            ph.bind(
                pos=lambda w, v, r=_rr: setattr(r, 'pos', v),
                size=lambda w, v, r=_rr: setattr(r, 'size', v),
            )
            padded = BoxLayout(size_hint_y=None, height=h, padding=[dp(14), 0])
            padded.add_widget(ph)
            self._content.add_widget(padded)
            self._content.add_widget(Widget(size_hint_y=None, height=dp(10)))

    def _add_weather_content(self, w: WeatherData):
        from kivy.uix.image import Image as KivyImage
        today = w.daily[0] if w.daily else None
        code = w.current.code
        night = is_night()

        # ── Hero card with hi-res background photo ──────────────────
        # Layout: Image fills card → dark overlay → text on top
        hero = FloatLayout(size_hint_y=None, height=dp(300))

        # Photo background via canvas.before texture (most reliable on Android)
        import os
        bg_path = get_bg_path(code, night)
        abs_bg = os.path.join(os.getcwd(), bg_path)
        if not os.path.exists(abs_bg):
            abs_bg = None

        if abs_bg:
            from kivy.uix.image import Image as _Img
            bg_img = _Img(source=abs_bg, size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
            try:
                bg_img.fit_mode = 'cover'
            except Exception:
                pass
            hero.add_widget(bg_img)

        # Dark overlay (child widget, renders on top of photo, under text)
        _ov = Widget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        with _ov.canvas:
            Color(0, 0, 0, 0.42)
            _ov_rect = Rectangle(pos=_ov.pos, size=_ov.size)
        _ov.bind(
            pos=lambda w, v, r=_ov_rect: setattr(r, 'pos', v),
            size=lambda w, v, r=_ov_rect: setattr(r, 'size', v),
        )
        hero.add_widget(_ov)

        # Text layer — topmost child
        text_layer = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            padding=[dp(16), dp(20)],
            spacing=dp(4),
        )

        city_lbl = Label(
            text=self._location.display_name,
            font_size=sp(30),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(40),
            halign='center',
            valign='middle',
        )
        city_lbl.bind(size=city_lbl.setter('text_size'))
        text_layer.add_widget(city_lbl)

        temp_lbl = Label(
            text=f'{w.current.temp}°',
            font_size=sp(90),
            bold=False,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(108),
            halign='center',
            valign='middle',
        )
        temp_lbl.bind(size=temp_lbl.setter('text_size'))
        text_layer.add_widget(temp_lbl)

        # Condition icon + label side by side
        cond_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                             height=dp(36), spacing=dp(8))
        cond_row.add_widget(Widget(size_hint_x=1))
        icon_img = KivyImage(
            source=get_icon_path(code, night),
            size_hint=(None, None), size=(dp(36), dp(36)),
        )
        cond_row.add_widget(icon_img)
        cond_lbl = Label(
            text=get_label(code),
            font_size=sp(20),
            color=(1, 1, 1, 0.95),
            size_hint_y=None,
            height=dp(36),
            halign='left',
            valign='middle',
        )
        cond_lbl.bind(size=cond_lbl.setter('text_size'))
        cond_row.add_widget(cond_lbl)
        cond_row.add_widget(Widget(size_hint_x=1))
        text_layer.add_widget(cond_row)

        if today:
            hl_lbl = Label(
                text=f'H:{today.max_temp}°   L:{today.min_temp}°',
                font_size=sp(17),
                color=(1, 1, 1, 0.85),
                size_hint_y=None,
                height=dp(24),
                halign='center',
                valign='middle',
            )
            hl_lbl.bind(size=hl_lbl.setter('text_size'))
            text_layer.add_widget(hl_lbl)

        hero.add_widget(text_layer)
        self._content.add_widget(hero)

        # Helper: add a card with consistent 12dp vertical gap + horizontal padding
        def add_card(widget, h=None):
            self._content.add_widget(Widget(size_hint_y=None, height=dp(12)))
            if h:
                padded = BoxLayout(size_hint_y=None, height=h, padding=[dp(14), 0])
            else:
                padded = BoxLayout(orientation='vertical', size_hint_y=None,
                                   padding=[dp(14), 0])
                padded.bind(minimum_height=padded.setter('height'))
            padded.add_widget(widget)
            self._content.add_widget(padded)

        # ── Summary text card ────────────────────────
        add_card(self._build_summary_card(w))

        # ── Hourly strip ─────────────────────────────
        today_hours = w.today_hourly()
        if today_hours:
            add_card(HourlyForecastCard(entries=today_hours), h=dp(178))

        # ── 10-day forecast ───────────────────────────
        if w.daily:
            add_card(DailyForecastCard(forecasts=w.daily))

        # ── Detail cards grid ─────────────────────────
        add_card(DetailCardsGrid(data=w))

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
    """Bottom nav bar: swipe left/right here to navigate, dots show position."""
    _swipe_tx = None

    def __init__(self, carousel: Carousel, on_list: callable, **kwargs):
        super().__init__(**kwargs)
        self._carousel = carousel
        self._on_list = on_list
        self._num_pages = 0

        from kivy.graphics import InstructionGroup
        with self.canvas.before:
            Color(0, 0, 0, 0.38)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self._dots_group = InstructionGroup()
        self.canvas.add(self._dots_group)

        self.bind(pos=self._redraw_bg, size=self._redraw_bg)
        carousel.bind(current_slide=self._redraw_dots)

    # ── Swipe/tap in the nav bar navigates ────────────────────────
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._swipe_tx = touch.x
            touch.grab(self)
            return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return
        touch.ungrab(self)
        if self._swipe_tx is None:
            return
        dx = touch.x - self._swipe_tx
        self._swipe_tx = None
        if abs(dx) < dp(20):
            # Tap on a dot — navigate to that dot's index
            try:
                idx = self._carousel.slides.index(self._carousel.current_slide)
            except Exception:
                idx = 0
            if self._num_pages < 2:
                return True
            cx = self.center_x
            spacing = dp(14)
            total_w = (self._num_pages - 1) * spacing
            start_x = cx - total_w / 2
            # Find which dot was tapped
            for i in range(self._num_pages):
                dot_x = start_x + i * spacing
                if abs(touch.x - dot_x) < dp(14):
                    if i != idx and i < len(self._carousel.slides):
                        self._carousel.load_slide(self._carousel.slides[i])
                    return True
        elif dx < -dp(20):
            self._carousel.load_next()
        elif dx > dp(20):
            self._carousel.load_previous()
        return True

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
            x = start_x + i * spacing
            if i == idx:
                self._dots_group.add(Color(1, 1, 1, 0.92))
                r = dot_r
            else:
                self._dots_group.add(Color(1, 1, 1, 0.40))
                r = dot_r * 0.75
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

        # ── Tap-arrow navigation (NO SWIPE — explicit buttons only) ──
        # Arrows are at the top left/right of the hero area.
        n = len(self._locations)
        self._left_arrow = MDIconButton(
            icon='chevron-left',
            theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.90),
            icon_size=dp(34),
            size_hint=(None, None),
            size=(dp(52), dp(52)),
            pos_hint={'x': 0, 'top': 0.97},
            opacity=0,
            on_release=self._go_prev,
        )
        self._right_arrow = MDIconButton(
            icon='chevron-right',
            theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.90),
            icon_size=dp(34),
            size_hint=(None, None),
            size=(dp(52), dp(52)),
            pos_hint={'right': 1.0, 'top': 0.97},
            opacity=0,
            on_release=self._go_next,
        )
        root.add_widget(self._left_arrow)
        root.add_widget(self._right_arrow)
        if n > 1:
            self._carousel.bind(current_slide=self._update_arrows)
            self._update_arrows()

        # ── Bottom nav bar ────────────────────────────────────────────
        self._nav_bar = _BottomNavBar(
            carousel=self._carousel,
            on_list=self._go_to_list,
            pos_hint={'bottom': 1},
            size_hint=(1, None),
            height=dp(52),
        )
        self._nav_bar.set_num_pages(n)
        root.add_widget(self._nav_bar)

        # List icon (bottom right, above nav bar)
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

        # ── Debug: background review button (temp, bottom-right) ──────
        debug_btn = MDIconButton(
            icon='image-search',
            theme_icon_color='Custom',
            icon_color=(1, 0.85, 0.2, 0.85),
            icon_size=dp(20),
            size_hint=(None, None),
            size=(dp(38), dp(38)),
            pos_hint={'right': 0.99, 'top': 0.14},
            on_release=self._open_bg_review,
        )
        root.add_widget(debug_btn)

        self.add_widget(root)

    def _open_bg_review(self, *_):
        from src.screens.bg_review import BgReviewScreen
        if not self.manager.has_screen('bg_review'):
            self.manager.add_widget(BgReviewScreen(
                name='bg_review',
                on_close=lambda: setattr(self.manager, 'current', 'weather_carousel'),
            ))
        self.manager.current = 'bg_review'

    def _update_arrows(self, *_):
        try:
            idx = self._carousel.index
        except Exception:
            idx = 0
        total = len(self._locations)
        self._left_arrow.opacity = 1 if idx > 0 else 0
        self._right_arrow.opacity = 1 if idx < total - 1 else 0
        self._left_arrow.disabled = idx == 0
        self._right_arrow.disabled = idx >= total - 1

    def _go_prev(self, *_):
        self._carousel.load_previous()
        self._update_arrows()
        Clock.schedule_once(lambda dt: self._scroll_to_top(), 0.05)

    def _go_next(self, *_):
        self._carousel.load_next()
        self._update_arrows()
        Clock.schedule_once(lambda dt: self._scroll_to_top(), 0.05)

    def _scroll_to_top(self):
        """Always snap the active slide's scroll to top on navigation."""
        try:
            idx = self._carousel.index
            w = self._detail_widgets[idx]
            if w._scroll:
                w._scroll.scroll_y = 1.0
        except Exception:
            pass

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
        """Jump carousel to the slide for the given zip code, always scroll to top."""
        for i, loc in enumerate(self._locations):
            if loc.zip == zip_code:
                if i < len(self._detail_widgets):
                    self._carousel.load_slide(self._detail_widgets[i])
                    Clock.schedule_once(lambda dt: self._scroll_to_top(), 0.05)
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
