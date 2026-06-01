"""AddLocationScreen — zip code entry with live Nominatim lookup."""
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivymd.uix.button import MDIconButton
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField

from src.api.geocoding import lookup_zip
from src.models.location import Location

KV = """
<AddLocationScreen>:
    name: 'add_location'
    canvas.before:
        Color:
            rgba: 0.04, 0.09, 0.18, 1
        Rectangle:
            pos: self.pos
            size: self.size

<_ZipField>:
    hint_text: 'ZIP code'
    mode: 'rectangle'
    max_text_length: 5
    input_filter: 'int'
    input_type: 'number'
    keyboard_suggestions: False
    font_size: sp(22)
    text_color_normal: 1, 1, 1, 1
    text_color_focus: 1, 1, 1, 1
    hint_text_color_normal: 1, 1, 1, 0.45
    hint_text_color_focus: 1, 1, 1, 0.65
    line_color_normal: 1, 1, 1, 0.30
    line_color_focus: 0.60, 0.80, 1, 0.90
    fill_color_normal: 0, 0, 0, 0.25
    fill_color_focus: 0, 0, 0, 0.30
"""
Builder.load_string(KV)


class _ZipField(MDTextField):
    pass


class AddLocationScreen(MDScreen):
    def __init__(self, on_location_added=None, **kwargs):
        super().__init__(**kwargs)
        self._on_location_added = on_location_added
        self._debounce_event = None
        self._pending_location: Location | None = None
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=[dp(32), dp(60), dp(32), dp(32)])

        # Header
        header = Label(
            text='Weather',
            font_size=sp(34),
            bold=True,
            color=(1, 1, 1, 0.95),
            size_hint_y=None,
            height=dp(50),
            halign='center',
            valign='middle',
        )
        header.bind(size=header.setter('text_size'))
        root.add_widget(header)

        sub = Label(
            text='Add a location to get started',
            font_size=sp(16),
            color=(1, 1, 1, 0.55),
            size_hint_y=None,
            height=dp(30),
            halign='center',
            valign='middle',
        )
        sub.bind(size=sub.setter('text_size'))
        root.add_widget(sub)

        root.add_widget(Widget(size_hint_y=None, height=dp(40)))

        # Zip input
        self._zip_field = _ZipField()
        self._zip_field.bind(text=self._on_text_change)
        root.add_widget(self._zip_field)

        root.add_widget(Widget(size_hint_y=None, height=dp(12)))

        # Status label (shows city name or error)
        self._status = Label(
            text='',
            font_size=sp(18),
            color=(1, 1, 1, 0.80),
            size_hint_y=None,
            height=dp(28),
            halign='center',
            valign='middle',
        )
        self._status.bind(size=self._status.setter('text_size'))
        root.add_widget(self._status)

        root.add_widget(Widget(size_hint_y=None, height=dp(20)))

        # Confirm button row
        btn_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        btn_row.add_widget(Widget(size_hint_x=1))

        self._confirm_btn = MDIconButton(
            icon='check-circle-outline',
            icon_size=dp(38),
            theme_icon_color='Custom',
            icon_color=(0.40, 0.80, 0.50, 1.0),
            disabled=True,
            on_release=self._confirm,
        )
        btn_row.add_widget(self._confirm_btn)
        btn_row.add_widget(Widget(size_hint_x=1))
        root.add_widget(btn_row)

        root.add_widget(Widget(size_hint_y=1))

        self.add_widget(root)

    def _on_text_change(self, field, text: str):
        # Cancel pending debounce
        if self._debounce_event:
            Clock.unschedule(self._debounce_event)
            self._debounce_event = None

        self._pending_location = None
        self._confirm_btn.disabled = True

        if len(text) < 5:
            self._status.text = ''
            self._status.color = (1, 1, 1, 0.80)
            return

        self._status.text = 'Looking up…'
        self._status.color = (1, 1, 1, 0.55)

        # Debounce 800ms (Nominatim rate limit compliance)
        self._debounce_event = Clock.schedule_once(
            lambda dt: self._do_lookup(text), 0.8
        )

    def _do_lookup(self, zip_code: str):
        def on_success(location: Location):
            def _update(dt):
                self._pending_location = location
                self._status.text = location.display_name
                self._status.color = (0.55, 0.90, 0.60, 1.0)
                self._confirm_btn.disabled = False
            Clock.schedule_once(_update, 0)

        def on_error(msg: str):
            def _update(dt):
                self._status.text = 'ZIP code not found'
                self._status.color = (1.0, 0.45, 0.45, 1.0)
                self._confirm_btn.disabled = True
            Clock.schedule_once(_update, 0)

        lookup_zip(zip_code, on_success, on_error)

    def _confirm(self, *_):
        if self._pending_location and self._on_location_added:
            self._on_location_added(self._pending_location)
        self._zip_field.text = ''
        self._status.text = ''
        self._pending_location = None
        self._confirm_btn.disabled = True
