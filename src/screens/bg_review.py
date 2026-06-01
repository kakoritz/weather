"""Debug: Background image review screen.

Tap the debug button (bottom-right of main weather screen) to open this.
Shows every weather condition + its assigned background photo so you can
review and approve or request changes before they're locked in.

Remove the debug button from weather_detail.py once the set is approved.
"""
import os

from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.screen import MDScreen

from src.utils.wmo_codes import get_bg_path

KV = """
<BgReviewScreen>:
    name: 'bg_review'
    canvas.before:
        Color:
            rgba: 0.05, 0.06, 0.10, 1
        Rectangle:
            pos: self.pos
            size: self.size
"""
Builder.load_string(KV)

# Every condition we handle, with a human label and the WMO code used to look it up
_CONDITIONS = [
    ('Clear Sky — Day',          0,  False),
    ('Clear Sky — Night',        0,  True),
    ('Partly Cloudy — Day',      2,  False),
    ('Partly Cloudy — Night',    2,  True),
    ('Overcast',                 3,  False),
    ('Fog / Mist',               45, False),
    ('Drizzle',                  51, False),
    ('Rain',                     61, False),
    ('Heavy Rain',               65, False),
    ('Snow',                     73, False),
    ('Thunderstorm',             95, False),
]


class BgReviewScreen(MDScreen):
    def __init__(self, on_close, **kwargs):
        super().__init__(**kwargs)
        self._build_ui(on_close)

    def _build_ui(self, on_close):
        root = FloatLayout()

        # Header
        header = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(52),
            pos_hint={'top': 1},
            padding=[dp(16), dp(8)],
        )
        with header.canvas.before:
            Color(0, 0, 0, 0.6)
            _hbg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda w, v, r=_hbg: setattr(r, 'pos', v),
                    size=lambda w, v, r=_hbg: setattr(r, 'size', v))
        header.add_widget(Label(
            text='Background Image Review',
            font_size=sp(18), bold=True, color=(1, 1, 1, 0.95),
            size_hint=(1, 1), halign='left', valign='middle',
        ))
        close_btn = MDIconButton(
            icon='close', theme_icon_color='Custom',
            icon_color=(1, 1, 1, 0.85), icon_size=dp(24),
            size_hint=(None, None), size=(dp(44), dp(44)),
            on_release=lambda *_: on_close(),
        )
        header.add_widget(close_btn)
        root.add_widget(header)

        # Instruction label
        instr = Label(
            text='Review each background below. Tell me which ones to replace.',
            font_size=sp(13), color=(1, 1, 1, 0.55),
            size_hint=(1, None), height=dp(28),
            pos_hint={'top': 0.89},
            halign='center', valign='middle',
        )
        root.add_widget(instr)

        # Scrollable grid of conditions
        scroll = ScrollView(
            do_scroll_y=True, do_scroll_x=False,
            bar_width=0, size_hint=(1, 1),
            pos_hint={'top': 0.83},
        )
        content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(16),
            padding=[dp(12), dp(12), dp(12), dp(80)],
        )
        content.bind(minimum_height=content.setter('height'))

        for label, wmo_code, night in _CONDITIONS:
            bg_path = get_bg_path(wmo_code, night)
            abs_path = os.path.join(os.getcwd(), bg_path)
            card = _ConditionCard(
                label=label,
                img_path=abs_path if os.path.exists(abs_path) else None,
                size_hint_y=None,
                height=dp(200),
            )
            content.add_widget(card)

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)


class _ConditionCard(FloatLayout):
    def __init__(self, label: str, img_path: str | None, **kwargs):
        super().__init__(**kwargs)

        # Background photo (or dark placeholder if missing)
        if img_path:
            bg = KivyImage(source=img_path, size_hint=(1, 1),
                           pos_hint={'x': 0, 'y': 0})
            try: bg.fit_mode = 'cover'
            except: pass
            self.add_widget(bg)
        else:
            with self.canvas.before:
                Color(0.15, 0.20, 0.28, 1)
                Rectangle(pos=self.pos, size=self.size)

        # Dark overlay for legibility
        ov = Widget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        with ov.canvas:
            Color(0, 0, 0, 0.45)
            _ov = Rectangle(pos=ov.pos, size=ov.size)
        ov.bind(pos=lambda w, v, r=_ov: setattr(r, 'pos', v),
                size=lambda w, v, r=_ov: setattr(r, 'size', v))
        self.add_widget(ov)

        # Condition label
        lbl = Label(
            text=label,
            font_size=sp(20), bold=True, color=(1, 1, 1, 1),
            size_hint=(1, None), height=dp(36),
            pos_hint={'x': 0, 'top': 0.92},
            halign='left', valign='middle',
            padding=[dp(16), 0],
        )
        lbl.bind(size=lbl.setter('text_size'))
        self.add_widget(lbl)

        # File name tag (bottom right for reference)
        if img_path:
            fname = os.path.basename(img_path)
            tag = Label(
                text=fname,
                font_size=sp(10), color=(1, 1, 1, 0.45),
                size_hint=(None, None), height=dp(18), width=dp(200),
                pos_hint={'right': 0.99, 'y': 0.02},
                halign='right', valign='bottom',
            )
            tag.bind(size=tag.setter('text_size'))
            self.add_widget(tag)
        else:
            lbl2 = Label(
                text='⚠ image not found',
                font_size=sp(13), color=(1, 0.5, 0.3, 1),
                size_hint=(1, None), height=dp(24),
                pos_hint={'x': 0, 'y': 0.05},
                halign='center', valign='middle',
            )
            self.add_widget(lbl2)
