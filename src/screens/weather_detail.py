"""WeatherCarouselScreen and WeatherDetailWidget — the main app view.

WeatherCarouselScreen:
  - Full-screen Kivy Carousel (one slide per location)
  - Bottom navigation bar (page dots + list icon)
  - Handles weather data loading and refresh

WeatherDetailWidget (one per location):
  - Hero: gradient background (light top, deeper blue bottom) + WeatherOverlay
    particles (sun/rain/snow/etc.) + text
  - Vertical ScrollView with all content
  - Hero: city, temp, condition, H/L, summary text
  - HourlyForecastCard
  - DailyForecastCard
  - DetailCardsGrid
"""
from datetime import datetime

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle, StencilPush, StencilUse, StencilUnUse, StencilPop
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
from src.utils.wmo_codes import get_label, get_condition, get_icon_path, is_night, get_moon_phase, get_gradients
from src.utils.units import fmt_temp, to_display
from src.widgets.weather_overlay import WeatherOverlay, overlay_for_night
from src.widgets.hourly_card import HourlyForecastCard
from src.widgets.daily_forecast import DailyForecastCard
from src.widgets.detail_cards import AlertBanner, DetailCardsGrid

# Day sky blue — the universal daytime background under all conditions
_DAY_SKY = (0.22, 0.60, 0.86, 1)
_NIGHT_SKY = (0.06, 0.10, 0.22, 1)


def _make_gradient_texture(top_rgba, bottom_rgba, size=256):
    """1xN texture interpolating top_rgba (at y=0) down to bottom_rgba (at y=size)."""
    from kivy.graphics.texture import Texture
    buf = bytes([
        int((top_rgba[ch] * (1 - y / size) + bottom_rgba[ch] * (y / size)) * 255)
        for y in range(size)
        for ch in range(3)
    ])
    tex = Texture.create(size=(1, size), colorfmt='rgb')
    tex.blit_buffer(buf, bufferfmt='ubyte', colorfmt='rgb')
    tex.wrap = 'clamp_to_edge'
    return tex

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

    def __init__(self, location: Location, weather: WeatherData | None = None,
                 units: str = 'F', **kwargs):
        super().__init__(**kwargs)
        self._location = location
        self._weather = weather
        self._units = units
        self._scroll: ScrollView | None = None
        self._content: BoxLayout | None = None
        self._bg_rect = None

        Clock.schedule_once(self._build, 0)

    def set_units(self, units: str) -> None:
        """Called when the user toggles °F/°C — re-renders with cached weather data."""
        self._units = units
        if self._weather is not None:
            self.update_weather(self._weather)

    def _draw_bg(self):
        """Pure black master background — floating cards sit on top of this."""
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *_):
        if self._bg_rect:
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size

    def show_error(self, msg: str, retry_fn=None):
        """Replace loading state with an error screen — city name centered + Retry."""
        self._weather = None
        self.clear_widgets()
        self._draw_bg()
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
        self._bg_rect = None
        self._scroll = None
        self._content = None
        Clock.schedule_once(self._build, 0)

    def update_weather(self, weather: WeatherData):
        self._weather = weather
        self.clear_widgets()
        self._bg_rect = None
        self._scroll = None
        self._content = None
        Clock.schedule_once(self._build, 0)

    def _build(self, *_):
        w = self._weather

        # Pure black master background — cards float on top
        self._draw_bg()

        # Outer stack: padding creates the "floating card" margins around both cards
        # [left, top, right, bottom] — bottom=dp(80) clears the nav bar
        _M = dp(12)
        stack = BoxLayout(orientation='vertical', size_hint=(1, 1),
                          padding=[_M, _M, _M, dp(80)], spacing=dp(8))

        if w is None:
            self._add_loading_state(stack)
        else:
            self._add_weather_content(stack, w)

        self.add_widget(stack)

    def _add_loading_state(self, stack):
        """Floating hero placeholder + floating blue details placeholder."""
        HERO_H = dp(240)
        RADIUS = dp(18)

        # ── Hero placeholder (rounded, dark) ──────────────────────────
        hero = FloatLayout(size_hint=(1, None), height=HERO_H)
        with hero.canvas.before:
            StencilPush()
            Color(1, 1, 1, 1)
            _hm = RoundedRectangle(pos=hero.pos, size=hero.size, radius=[RADIUS])
            StencilUse()
            Color(0.10, 0.14, 0.22, 1)
            _hbg = Rectangle(pos=hero.pos, size=hero.size)
        hero.bind(
            pos=lambda w, v, a=_hm, b=_hbg: (setattr(a, 'pos', v), setattr(b, 'pos', v)),
            size=lambda w, v, a=_hm, b=_hbg: (setattr(a, 'size', v), setattr(b, 'size', v)),
        )
        with hero.canvas.after:
            StencilUnUse()
            StencilPop()

        tl = BoxLayout(orientation='vertical', size_hint=(1, 1),
                       pos_hint={'x': 0, 'y': 0}, padding=[dp(16), dp(16)], spacing=dp(4))
        for txt, sz, alpha in [
            (self._location.display_name, sp(26), 0.90),
            ('--°', sp(80), 0.45),
            ('Retrieving weather…', sp(16), 0.40),
        ]:
            lbl = Label(text=txt, font_size=sz, bold=False, color=(1, 1, 1, alpha),
                        size_hint_y=None, height=dp(92) if txt == '--°' else dp(28),
                        halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            tl.add_widget(lbl)
        hero.add_widget(tl)
        stack.add_widget(hero)

        # ── Details placeholder (rounded, blue) ───────────────────────
        details = BoxLayout(orientation='vertical', size_hint=(1, 1))
        with details.canvas.before:
            StencilPush()
            Color(1, 1, 1, 1)
            _dm = RoundedRectangle(pos=details.pos, size=details.size, radius=[RADIUS])
            StencilUse()
            Color(0.70, 0.83, 0.95, 1)
            _dbg = Rectangle(pos=details.pos, size=details.size)
        details.bind(
            pos=lambda w, v, a=_dm, b=_dbg: (setattr(a, 'pos', v), setattr(b, 'pos', v)),
            size=lambda w, v, a=_dm, b=_dbg: (setattr(a, 'size', v), setattr(b, 'size', v)),
        )
        with details.canvas.after:
            StencilUnUse()
            StencilPop()
        stack.add_widget(details)

    def _add_weather_content(self, stack, w: WeatherData):
        from kivy.uix.image import Image as KivyImage
        today = w.daily[0] if w.daily else None
        code = w.current.code
        night = is_night()
        HERO_H = dp(260) if night else dp(240)   # -20% from original dp(320/300)

        # ── Hero card — rounded all 4 corners, floating on black background ──
        hero = FloatLayout(size_hint=(1, None), height=HERO_H)
        with hero.canvas.before:
            StencilPush()
            Color(1, 1, 1, 1)
            _hero_mask = RoundedRectangle(pos=hero.pos, size=hero.size,
                                          radius=[dp(18)])
            StencilUse()
        hero.bind(
            pos=lambda w, v, r=_hero_mask: setattr(r, 'pos', v),
            size=lambda w, v, r=_hero_mask: setattr(r, 'size', v),
        )
        with hero.canvas.after:
            StencilUnUse()
            StencilPop()

        # Gradient background — light blue at top fading to a deeper blue at the
        # bottom, matching the lightened details card below it. Replaces the old
        # photo background, which read as too dark regardless of condition.
        top_rgba, bottom_rgba = get_gradients(code)
        _grad_tex = _make_gradient_texture(top_rgba, bottom_rgba)
        _grad_widget = Widget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        with _grad_widget.canvas:
            Color(1, 1, 1, 1)
            _grad_rect = Rectangle(texture=_grad_tex, pos=_grad_widget.pos, size=_grad_widget.size)
        _grad_widget.bind(
            pos=lambda w, v, r=_grad_rect: setattr(r, 'pos', v),
            size=lambda w, v, r=_grad_rect: setattr(r, 'size', v),
        )
        hero.add_widget(_grad_widget)

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
                text=fmt_temp(w.current.temp, self._units),
                font_size=sp(90), bold=False, color=(1, 1, 1, 1),
                size_hint=(None, 1), width=dp(160),
                halign='left', valign='middle',
            )
            temp_lbl.bind(size=temp_lbl.setter('text_size'))
            temp_row.add_widget(temp_lbl)
            temp_row.add_widget(Widget(size_hint_x=1))
            text_layer.add_widget(temp_row)
        else:
            # The degree symbol is excluded from centering — including it in
            # one string biases the apparent center of the digits to the
            # left, since "°" adds width only on the right. The number
            # auto-sizes to its own texture and centers on that alone; the
            # degree symbol reads back the number's real right edge (after
            # layout settles) rather than being guessed from texture width,
            # so it can never end up positioned off in the wrong spot.
            temp_wrap = FloatLayout(size_hint_y=None, height=dp(108))
            num_lbl = Label(
                text=str(to_display(w.current.temp, self._units)),
                font_size=sp(90), bold=False, color=(1, 1, 1, 1),
                size_hint=(None, None),
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
            )
            num_lbl.bind(texture_size=lambda inst, v: setattr(inst, 'size', v))
            temp_wrap.add_widget(num_lbl)

            deg_lbl = Label(
                text='°', font_size=sp(90), bold=False, color=(1, 1, 1, 1),
                size_hint=(None, None),
            )
            deg_lbl.bind(texture_size=lambda inst, v: setattr(inst, 'size', v))
            temp_wrap.add_widget(deg_lbl)

            def _position_deg(*_):
                deg_lbl.pos = (num_lbl.right + dp(2), num_lbl.y)
            num_lbl.bind(pos=_position_deg, size=_position_deg)
            deg_lbl.bind(size=_position_deg)
            Clock.schedule_once(_position_deg, 0)

            text_layer.add_widget(temp_wrap)

        # Condition label — auto-sized to its own rendered text and centered
        # on that (matches the H/L line below it). The icon reads back the
        # label's real left edge (cond_lbl.x) once Kivy has actually laid it
        # out, rather than guessing the text width ourselves — guessing was
        # the bug: the fallback estimate was way too wide, so the icon flew
        # off to the left. This way the icon can only ever sit exactly where
        # the first character starts, because that IS cond_lbl.x.
        cond_row = FloatLayout(size_hint_y=None, height=dp(36))
        cond_lbl = Label(
            text=get_label(code),
            font_size=sp(20),
            bold=False,
            color=(1, 1, 1, 0.95),
            size_hint=(None, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
        )
        cond_lbl.bind(texture_size=lambda inst, v: setattr(inst, 'size', v))
        cond_row.add_widget(cond_lbl)
        icon_img = KivyImage(
            source=get_icon_path(code, night),
            size_hint=(None, None), size=(dp(24), dp(24)),
        )
        cond_row.add_widget(icon_img)

        def _position_cond_icon(*_):
            icon_img.pos = (
                cond_lbl.x - icon_img.width - dp(6),
                cond_lbl.center_y - icon_img.height / 2,
            )
        cond_lbl.bind(pos=_position_cond_icon, size=_position_cond_icon)
        Clock.schedule_once(_position_cond_icon, 0)
        text_layer.add_widget(cond_row)

        if today:
            hl_lbl = Label(
                text=f'H:{fmt_temp(today.max_temp, self._units)}   L:{fmt_temp(today.min_temp, self._units)}',
                font_size=sp(17),
                color=(1, 1, 1, 0.85),
                size_hint_y=None,
                height=dp(24),
                halign='center',
                valign='middle',
            )
            hl_lbl.bind(size=hl_lbl.setter('text_size'))
            text_layer.add_widget(hl_lbl)

        # Moon phase name + illumination — night only
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
        stack.add_widget(hero)

        # ── Details card: deep blue, rounded all 4 corners, fills remaining space ──
        RADIUS = dp(18)
        details = BoxLayout(orientation='vertical', size_hint=(1, 1))
        with details.canvas.before:
            StencilPush()
            Color(1, 1, 1, 1)
            _det_mask = RoundedRectangle(pos=details.pos, size=details.size, radius=[RADIUS])
            StencilUse()
            Color(0.70, 0.83, 0.95, 1)   # lighter iOS-style blue
            _det_bg = Rectangle(pos=details.pos, size=details.size)
        details.bind(
            pos=lambda w, v, a=_det_mask, b=_det_bg: (setattr(a, 'pos', v), setattr(b, 'pos', v)),
            size=lambda w, v, a=_det_mask, b=_det_bg: (setattr(a, 'size', v), setattr(b, 'size', v)),
        )
        with details.canvas.after:
            StencilUnUse()
            StencilPop()
        stack.add_widget(details)

        # ── Scrollable content inside the blue details card ────────────
        self._scroll = ScrollView(do_scroll_y=True, do_scroll_x=False,
                                  bar_width=0, size_hint=(1, 1), effect_cls='ScrollEffect')
        self._content = BoxLayout(orientation='vertical', size_hint_y=None,
                                  padding=[0, 0, 0, dp(20)], spacing=0)
        self._content.bind(minimum_height=self._content.setter('height'))

        def add_card(widget, h=None):
            if self._content.children:   # skip the leading gap before the first card
                self._content.add_widget(Widget(size_hint_y=None, height=dp(12)))
            if h:
                padded = BoxLayout(size_hint_y=None, height=h, padding=[dp(14), 0])
            else:
                padded = BoxLayout(orientation='vertical', size_hint_y=None,
                                   padding=[dp(14), 0])
                padded.bind(minimum_height=padded.setter('height'))
            padded.add_widget(widget)
            self._content.add_widget(padded)

        # ── Active weather alerts ──────────────────────────────────────
        if w.alerts:
            add_card(AlertBanner(alerts=w.alerts))

        # ── Hourly strip (with summary text as its header) ────────────
        next_hours = w.next_24_hours()
        if next_hours:
            add_card(HourlyForecastCard(
                entries=next_hours, first_is_now=True,
                summary=self._build_summary_text(w),
                units=self._units,
            ), h=dp(210))

        # ── 10-day forecast ───────────────────────────
        if w.daily:
            add_card(DailyForecastCard(forecasts=w.daily, units=self._units))

        # ── Detail cards grid ─────────────────────────
        add_card(DetailCardsGrid(data=w, units=self._units))

        attrib = Label(text='Data provided by Open-Meteo API · openstreetmap.org',
                       font_size=sp(10), color=(0.07, 0.14, 0.26, 0.45),
                       size_hint_y=None, height=dp(18),
                       halign='center', valign='middle')
        attrib.bind(size=attrib.setter('text_size'))
        self._content.add_widget(attrib)

        self._scroll.add_widget(self._content)
        details.add_widget(self._scroll)

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
        self._units = storage.get_units() if storage else 'F'
        self._weather_map: dict = {}
        self._detail_widgets: list = []
        self._carousel: Carousel | None = None
        self._nav_bar: _BottomNavBar | None = None
        self._build_ui()
        self._load_all_weather()

    def on_pre_enter(self, *_):
        """Pick up a °F/°C change made on the list screen's menu."""
        new_units = self._storage.get_units() if self._storage else 'F'
        if new_units != self._units:
            self._units = new_units
            for w in self._detail_widgets:
                w.set_units(new_units)

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
            widget = WeatherDetailWidget(location=loc, weather=cached, units=self._units)
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
                # Push updated weather to list screen if it is currently visible
                try:
                    if self.manager.current == 'location_list':
                        ls = self.manager.get_screen('location_list')
                        ls.refresh(self._locations, self._weather_map)
                except Exception:
                    pass
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
        widget = WeatherDetailWidget(location=location, weather=cached, units=self._units)
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
        # Refresh list screen with latest weather data before showing it.
        # The list is built at startup when weather_map is empty; this ensures
        # the temperature/H:L cards are populated with data that loaded since then.
        try:
            ls = self.manager.get_screen('location_list')
            ls.refresh(self._locations, self._weather_map)
        except Exception:
            pass
        self.manager.current = 'location_list'

    @property
    def weather_map(self) -> dict:
        return self._weather_map

    @property
    def locations(self) -> list:
        return list(self._locations)
