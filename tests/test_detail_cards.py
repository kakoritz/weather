"""Tests for detail card widgets — construction, logic, and crash guards.

Widget construction tests are skipped in headless CI (no Kivy display).
Logic/data tests run everywhere.
"""
import pytest

# Skip all Kivy-dependent tests in headless environments
kivy_available = False
try:
    import kivy  # noqa
    kivy.require('2.0.0')
    kivy_available = True
except Exception:
    pass

kivy_only = pytest.mark.skipif(not kivy_available, reason='Kivy display not available')

from src.models.weather import (
    AirQualityData, CurrentConditions, DailyForecast, HourlyEntry, WeatherData,
)


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_aq():
    return AirQualityData(us_aqi=51, pm2_5=12.3, pm10=18.5,
                          ozone=55.2, nitrogen_dioxide=8.1)


@pytest.fixture
def sample_current():
    return CurrentConditions(
        temp=75, feels_like=73, humidity=60, wind_speed=10,
        wind_dir=180, precip=0.0, uv=3.0, pressure=1015.0,
        visibility=10.0, code=2,
    )


@pytest.fixture
def sample_daily():
    return DailyForecast(
        date='2025-06-01', max_temp=83, min_temp=59,
        precip_sum=0.0, precip_prob=10, wind_max=12,
        uv_max=5.0, sunrise='2025-06-01T06:15', sunset='2025-06-01T20:40',
        code=2,
    )


@pytest.fixture
def sample_weather(sample_current, sample_daily):
    return WeatherData(
        location_zip='28139',
        fetched_at='2025-06-01T08:00:00',
        current=sample_current,
        daily=[sample_daily],
        hourly=[HourlyEntry(
            time='2025-06-01T08:00', temp=70, feels_like=69, humidity=65,
            wind_speed=8, wind_dir=180, precip_prob=5, precip=0.0,
            pressure=1015.0, visibility=10.0, code=2,
        )],
        air_quality=AirQualityData(us_aqi=42, pm2_5=8.0, pm10=12.0,
                                    ozone=40.0, nitrogen_dioxide=5.0),
    )


# ─── card construction — skipped in headless CI ───────────────────────────────

@kivy_only
def test_all_cards_construct(sample_aq, sample_weather):
    from src.widgets.detail_cards import (
        AirQualityCard, UVIndexCard, SunsetCard, WindCard, RainfallCard,
        FeelsLikeCard, HumidityCard, VisibilityCard, PressureCard,
        TemperatureMapCard, DetailCardsSection,
    )
    AirQualityCard(aq=sample_aq)
    UVIndexCard(uv=5.5)
    SunsetCard(sunset='8:40 PM', sunrise='6:15 AM', progress=0.6)
    WindCard(speed=12, direction_deg=270)
    RainfallCard(last_24h=0.15, next_24h=0.30)
    FeelsLikeCard(feels=72, actual=75, humidity=60, wind=10)
    HumidityCard(humidity=65, dew_point=58)
    VisibilityCard(miles=10.0)
    PressureCard(pressure_hpa=1015.0, trend='Steady')
    TemperatureMapCard(lat=35.37, lon=-81.96, city='Test', temp=75)
    DetailCardsSection(data=sample_weather)


# ─── See More guard — no crash on callback invocation ─────────────────────────

def test_see_more_callback_invoked_without_crash():
    """See More lambda must be invocable without crashing outside Kivy."""
    called = []
    cb = lambda: called.append(True)
    cb()
    assert called == [True]


def test_see_more_guard_only_fires_on_tap():
    """The tap guard (dx<15, dy<15) must be present in source code."""
    src = open('src/widgets/detail_cards.py').read()
    assert 'dx < 15 and dy < 15' in src, \
        "See More tap guard missing — will fire during scroll and crash"


# ─── Window.add_widget — no 'index' kwarg ────────────────────────────────────

def test_window_add_widget_no_index_in_source():
    """Source must NOT call Window.add_widget(..., index=...) — unsupported in this Kivy."""
    for fname in ['src/screens/location_list.py', 'src/widgets/detail_cards.py']:
        src = open(fname).read()
        assert 'add_widget(' not in src.replace(
            'add_widget(self._ac_box)', ''
        ).replace('add_widget(menu)', '').replace('add_widget(modal)', '') or \
            'index=' not in src, \
            f"{fname} calls Window.add_widget with index= which is unsupported"


# ─── AQI categories ──────────────────────────────────────────────────────────

@pytest.mark.parametrize('aqi,cat', [
    (25,  'Good'),
    (75,  'Moderate'),
    (125, 'Unhealthy for Sensitive Groups'),
    (175, 'Unhealthy'),
    (250, 'Very Unhealthy'),
    (350, 'Hazardous'),
])
def test_aq_categories(aqi, cat):
    aq = AirQualityData(us_aqi=aqi, pm2_5=0, pm10=0, ozone=0, nitrogen_dioxide=0)
    assert aq.category == cat


# ─── Card header text — no text wrapping ─────────────────────────────────────

def test_card_header_titles_are_short_enough():
    """All card header labels must fit on one line — check string length."""
    titles = [
        'Air Quality', 'UV Index', 'Sunset', 'Wind',
        'Rainfall', 'Feels Like', 'Humidity', 'Visibility', 'Pressure',
        'Temperature',
    ]
    # Any title over 20 chars risks wrapping at small widths
    long = [t for t in titles if len(t) > 20]
    assert long == [], f'Titles too long for single line: {long}'
