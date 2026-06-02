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
from src.utils.wmo_codes import get_label, get_condition, get_bg_path, get_icon_path, is_night, get_moon_phase
from src.widgets.weather_overlay import WeatherOverlay, overlay_for_night
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

        # Sky background (canvas)
        self._draw_sky()

        # ── Outer vertical stack: [Hero (fixed)] [ScrollView (rest)] ──────────
        # Hero is LOCKED at the top — it never scrolls away.
        stack = BoxLayout(orientation='vertical', size_hint=(1, 1))

        if w is None:
            self._add_loading_state(stack)
        else:
            self._add_weather_content(stack, w)

        self.add_widget(stack)

    def _add_loading_state(self, stack):
        """Skeleton: hero pinned at top, ghost cards in scroll below."""
        HERO_H = dp(240)

        # Hero placeholder (pinned to top of stack)
        hero = FloatLayout(size_hint=(1, None), height=HERO_H)
        with hero.canvas.before:
            Color(0, 0, 0, 0.25)
            _h_rect = Rectangle(pos=hero.pos, size=hero.size)
        hero.bind(pos=lambda w, v, r=_h_rect: setattr(r, 'pos', v),
                  size=lambda w, v, r=_h_rect: setattr(r, 'size', v))
        tl = BoxLayout(orientation='vertical', size_hint=(1, 1),
                       pos_hint={'x': 0, 'y': 0}, padding=[dp(16), dp(16)], spacing=dp(4))
        for txt, sz, alpha in [
            (self._location.display_name, sp(26), 0.90),
            ('--°', sp(80), 0.55),
            ('Retrieving weather…', sp(16), 0.50),
        ]:
            lbl = Label(text=txt, font_size=sz, bold=False, color=(1, 1, 1, alpha),
                        size_hint_y=None, height=dp(92) if txt == '--°' else dp(28),
                        halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            tl.add_widget(lbl)
        hero.add_widget(tl)
        stack.add_widget(hero)

        # Scrollable skeleton cards
        self._scroll = ScrollView(do_scroll_y=True, do_scroll_x=False,
                                  bar_width=0, size_hint=(1, 1), effect_cls='ScrollEffect')
        content = BoxLayout(orientation='vertical', size_hint_y=None,
                            padding=[0, 0, 0, dp(80)], spacing=0)
        content.bind(minimum_height=content.setter('height'))
        for h in [dp(50), dp(170), dp(400)]:
            content.add_widget(Widget(size_hint_y=None, height=dp(10)))
            ph = Widget(size_hint_y=None, height=h)
            with ph.canvas:
                Color(0, 0, 0, 0.12)
                _rr = RoundedRectangle(pos=ph.pos, size=ph.size, radius=[dp(14)])
            ph.bind(pos=lambda w, v, r=_rr: setattr(r, 'pos', v),
                    size=lambda w, v, r=_rr: setattr(r, 'size', v))
            padded = BoxLayout(size_hint_y=None, height=h, padding=[dp(14), 0])
            padded.add_widget(ph)
            content.add_widget(padded)
        self._scroll.add_widget(content)
        stack.add_widget(self._scroll)

    def _add_weather_content(self, stack, w: WeatherData):
        from kivy.uix.image import Image as KivyImage
        today = w.daily[0] if w.daily else None
        code = w.current.code
        night = is_night()
        HERO_H = dp(260) if night else dp(240)   # -20% from original dp(320/300)

        # ── Hero card — FIXED/STICKY at top, never scrolls ──────────
        hero = FloatLayout(size_hint=(1, None), height=HERO_H)

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

        # Weather particle overlay — between dark overlay and text
        ov_type = overlay_for_night(get_condition(code), night)
        if ov_type != 'none':
            wx_overlay = WeatherOverlay(
                overlay_type=ov_type,
                size_hint=(1, 1),
                pos_hint={'x': 0, 'y': 0},
            )
            hero.add_widget(wx_overlay)

        # Text layer — topmost child
        text_layer = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            padding=[dp(16), dp(20)],
            spacing=dp(4),
        )

        # City name — thin weight per design direction
        city_lbl = Label(
            text=self._location.display_name,
            font_size=sp(28),
            bold=False,
            color=(1, 1, 1, 0.95),
            size_hint_y=None,
            height=dp(36),
            halign='center',
            valign='middle',
        )
        city_lbl.bind(size=city_lbl.setter('text_size'))
        text_layer.add_widget(city_lbl)

        # Temperature + moon (at night) side by side, centred in the card
        if night:
            moon_name, moon_path, moon_illum = get_moon_phase()
            import os as _os
            abs_moon = _os.path.join(_os.getcwd(), moon_path)
            temp_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                                 height=dp(108))
            temp_row.add_widget(Widget(size_hint_x=1))
            # Moon icon — same visual weight as the temperature number
            if _os.path.exists(abs_moon):
                moon_big = KivyImage(
                    source=abs_moon,
                    size_hint=(None, None),
                    size=(dp(82), dp(82)),
                    pos_hint={'center_y': 0.45},   # slightly lower: offset feel
                )
                temp_row.add_widget(moon_big)
                temp_row.add_widget(Widget(size_hint=(None, 1), width=dp(10)))
            temp_lbl = Label(
                text=f'{w.current.temp}°',
                font_size=sp(90), bold=False, color=(1, 1, 1, 1),
                size_hint=(None, 1), width=dp(160),
                halign='left', valign='middle',
            )
            temp_lbl.bind(size=temp_lbl.setter('text_size'))
            temp_row.add_widget(temp_lbl)
            temp_row.add_widget(Widget(size_hint_x=1))
            text_layer.add_widget(temp_row)
        else:
            temp_lbl = Label(
                text=f'{w.current.temp}°',
                font_size=sp(90), bold=False, color=(1, 1, 1, 1),
                size_hint_y=None, height=dp(108),
                halign='center', valign='middle',
            )
            temp_lbl.bind(size=temp_lbl.setter('text_size'))
            text_layer.add_widget(temp_lbl)

        # Condition: icon + label on ONE line, full width, centered, no wrapping
        cond_row = BoxLayout(orientation='horizontal', size_hint_y=None,
                             height=dp(36), spacing=dp(6))
        cond_row.add_widget(Widget(size_hint_x=1))
        icon_img = KivyImage(
            source=get_icon_path(code, night),
            size_hint=(None, None), size=(dp(30), dp(30)),
        )
        cond_row.add_widget(icon_img)
        cond_lbl = Label(
            text=get_label(code),
            font_size=sp(20),
            bold=False,
            color=(1, 1, 1, 0.95),
            size_hint=(None, 1),
            width=dp(220),   # fixed wide enough for longest label, never wraps
            halign='left',
            valign='middle',
        )
        # Do NOT bind text_size — use fixed width so it never wraps
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

        # Moon phase name + illumination — small text below condition, night only
        if night:
            moon_name, _mp, moon_illum = get_moon_phase()
            moon_sub = Label(
                text=f'{moon_name}  ·  {moon_illum}% illuminated',
                font_size=sp(12), color=(1, 1, 1, 0.65),
                size_hint_y=None, height=dp(20),
                halign='center', valign='middle',
            )
            moon_sub.bind(size=moon_sub.setter('text_size'))
            text_layer.add_widget(moon_sub)

        hero.add_widget(text_layer)
        stack.add_widget(hero)   # ← STICKY: hero goes directly into the outer stack

        # ── Scrollable content below the fixed hero ────────────────────
        self._scroll = ScrollView(do_scroll_y=True, do_scroll_x=False,
                                  bar_width=0, size_hint=(1, 1), effect_cls='ScrollEffect')
        self._content = BoxLayout(orientation='vertical', size_hint_y=None,
                                  padding=[0, 0, 0, dp(80)], spacing=0)
        self._content.bind(minimum_height=self._content.setter('height'))

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

        # ── Hourly strip (with summary text as its header) ────────────
        next_hours = w.next_24_hours()
        if next_hours:
            add_card(HourlyForecastCard(
                entries=next_hours, first_is_now=True,
                summary=self._build_summary_text(w),
            ), h=dp(210))

        # ── 10-day forecast ───────────────────────────
        if w.daily:
            add_card(DailyForecastCard(forecasts=w.daily))

        # ── Detail cards grid ─────────────────────────
        add_card(DetailCardsGrid(data=w))

        attrib = Label(text='Data provided by Open-Meteo API · openstreetmap.org',
                       font_size=sp(10), color=(1, 1, 1, 0.35),
                       size_hint_y=None, height=dp(18),
                       halign='center', valign='middle')
        attrib.bind(size=attrib.setter('text_size'))
        self._content.add_widget(attrib)

        self._scroll.add_widget(self._content)
        stack.add_widget(self._scroll)

    def _build_summary_text(self, w: WeatherData) -> str:
        """Build a one-line summary for the hourly card header."""
        today = w.daily[0] if w.daily else None
        now_h = datetime.now().hour
        hours = w.next_24_hours()
        try:
            current_cond = get_label(w.current.code)
            later_hours = [h for h in hours[2:] if h.code != w.current.code]
            if later_hours:
                lh = later_hours[0]
                t_str = datetime.fromisoformat(lh.time).strftime('%-I%p').lower()
                summary = f'{current_cond} conditions changing to {get_label(lh.code)} around {t_str}.'
            else:
                summary = f'{current_cond} throughout the day.'
            if today and today.precip_prob > 30:
                summary += f'  {today.precip_prob}% chance of rain.'
        except Exception:
            summary = get_label(w.current.code)
        return summary

    def _build_summary_card(self, w: WeatherData) -> Widget:
        """Kept for compatibility — no longer used (summary merged into hourly)."""
        summary_text = self._build_summary_text(w)

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

        self.add_widget(root)

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
