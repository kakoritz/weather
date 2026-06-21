"""Tests for src/models/location.py and src/models/weather.py."""
import pytest
from src.models.location import Location
from src.models.weather import (
    WeatherData, CurrentConditions, HourlyEntry, DailyForecast,
    AirQualityData, WeatherAlert, wind_direction_label, pressure_trend,
    feels_like_reason, visibility_description,
)


# ──────────────────────────────────────────────
# Location
# ──────────────────────────────────────────────

def test_location_display_name():
    loc = Location(zip='28139', city='Rutherfordton', state='NC', lat=35.37, lon=-81.96)
    assert loc.display_name == 'Rutherfordton, NC'


def test_location_round_trip():
    loc = Location(zip='28139', city='Rutherfordton', state='NC', lat=35.37, lon=-81.96)
    restored = Location.from_dict(loc.to_dict())
    assert restored == loc


def test_location_from_dict_coerces_lat_lon():
    d = {'zip': '10001', 'city': 'New York', 'state': 'NY', 'lat': '40.71', 'lon': '-74.00'}
    loc = Location.from_dict(d)
    assert isinstance(loc.lat, float)
    assert isinstance(loc.lon, float)


def test_location_is_frozen():
    loc = Location(zip='28139', city='Rutherfordton', state='NC', lat=35.37, lon=-81.96)
    with pytest.raises((AttributeError, TypeError)):
        loc.city = 'Other'  # type: ignore


# ──────────────────────────────────────────────
# WeatherData helpers
# ──────────────────────────────────────────────

def _make_weather(**overrides) -> WeatherData:
    current = CurrentConditions(
        temp=62, feels_like=61, humidity=99,
        wind_speed=5, wind_dir=190,
        precip=0.0, uv=1.0, pressure=1015.2, visibility=10.0, code=2,
    )
    daily = [
        DailyForecast(
            date='2025-06-01', max_temp=83, min_temp=59,
            precip_sum=0.15, precip_prob=40, wind_max=12,
            uv_max=5.0, sunrise='2025-06-01T06:15', sunset='2025-06-01T20:40', code=2,
        ),
        DailyForecast(
            date='2025-06-02', max_temp=68, min_temp=55,
            precip_sum=0.05, precip_prob=25, wind_max=8,
            uv_max=3.0, sunrise='2025-06-02T06:16', sunset='2025-06-02T20:39', code=3,
        ),
    ]
    hourly = [
        HourlyEntry(
            time='2025-06-01T08:00', temp=62, feels_like=61, humidity=99,
            wind_speed=5, wind_dir=190, precip_prob=10, precip=0.0,
            pressure=1015.2, visibility=10.0, code=2,
        ),
    ]
    data = WeatherData(
        location_zip='28139', fetched_at='2025-06-01T08:09:00',
        current=current, daily=daily, hourly=hourly,
        **overrides,
    )
    return data


def test_today_high_low():
    data = _make_weather()
    assert data.today_high() == 83
    assert data.today_low() == 59


def test_today_sunrise_format():
    data = _make_weather()
    sr = data.today_sunrise()
    assert sr is not None
    assert ':' in sr
    assert 'AM' in sr or 'PM' in sr


def test_today_sunset_format():
    data = _make_weather()
    ss = data.today_sunset()
    assert ss is not None
    assert ':' in ss


def test_today_hourly_filters_by_date():
    data = _make_weather()
    hours = data.today_hourly()
    assert len(hours) == 1
    assert hours[0].time.startswith('2025-06-01')


def test_sun_progress_returns_float():
    data = _make_weather()
    p = data.sun_progress()
    assert 0.0 <= p <= 1.0


def test_weather_data_round_trip():
    data = _make_weather()
    restored = WeatherData.from_dict(data.to_dict())
    assert restored.location_zip == data.location_zip
    assert restored.current.temp == data.current.temp
    assert len(restored.daily) == len(data.daily)
    assert len(restored.hourly) == len(data.hourly)


# ──────────────────────────────────────────────
# WeatherAlert
# ──────────────────────────────────────────────

def test_weather_alert_round_trip():
    data = _make_weather(alerts=[
        WeatherAlert(event='Special Weather Statement', headline='SWS issued...',
                     description='Fire danger.', severity='Moderate', sent='2026-06-18T09:56'),
    ])
    restored = WeatherData.from_dict(data.to_dict())
    assert len(restored.alerts) == 1
    assert restored.alerts[0].event == 'Special Weather Statement'
    assert restored.alerts[0].severity == 'Moderate'


def test_weather_alert_backward_compat_plain_strings():
    """Old cache had alerts as list[str]; from_dict must not crash on it."""
    d = _make_weather().to_dict()
    d['alerts'] = ['Some old headline string']
    restored = WeatherData.from_dict(d)
    assert len(restored.alerts) == 1
    assert isinstance(restored.alerts[0], WeatherAlert)
    assert restored.alerts[0].headline == 'Some old headline string'
    assert restored.alerts[0].severity == 'Unknown'


# ──────────────────────────────────────────────
# Wind direction label
# ──────────────────────────────────────────────

@pytest.mark.parametrize('deg,expected', [
    (0, 'N'),
    (90, 'E'),
    (180, 'S'),
    (270, 'W'),
    (45, 'NE'),
    (225, 'SW'),
])
def test_wind_direction_label(deg, expected):
    assert wind_direction_label(deg) == expected


# ──────────────────────────────────────────────
# Pressure trend
# ──────────────────────────────────────────────

def _make_hourly_with_pressures(pressures: list) -> list:
    return [
        HourlyEntry(
            time=f'2025-06-01T0{i}:00', temp=62, feels_like=61, humidity=99,
            wind_speed=5, wind_dir=190, precip_prob=0, precip=0.0,
            pressure=p, visibility=10.0, code=2,
        )
        for i, p in enumerate(pressures)
    ]


def test_pressure_trend_rising():
    hourly = _make_hourly_with_pressures([1010.0, 1011.0, 1012.0])
    assert pressure_trend(hourly, 1012.0) == 'Rising'


def test_pressure_trend_falling():
    hourly = _make_hourly_with_pressures([1015.0, 1014.0, 1013.0])
    assert pressure_trend(hourly, 1013.0) == 'Falling'


def test_pressure_trend_steady():
    hourly = _make_hourly_with_pressures([1015.0, 1015.1, 1015.2])
    assert pressure_trend(hourly, 1015.2) == 'Steady'


def test_pressure_trend_too_few_hours():
    hourly = _make_hourly_with_pressures([1015.0, 1014.0])
    assert pressure_trend(hourly, 1014.0) == 'Steady'


# ──────────────────────────────────────────────
# Feels like reason
# ──────────────────────────────────────────────

def test_feels_like_similar():
    assert 'Similar' in feels_like_reason(62, 62, 60, 5)


def test_feels_like_wind_chill():
    result = feels_like_reason(50, 58, 40, 20)
    assert 'cool' in result.lower()


def test_feels_like_humidity():
    result = feels_like_reason(70, 65, 85, 3)
    assert 'warm' in result.lower()


# ──────────────────────────────────────────────
# Visibility description
# ──────────────────────────────────────────────

@pytest.mark.parametrize('miles,keyword', [
    (10, 'clear'),
    (7, 'Good'),
    (4, 'Hazy'),
    (2, 'Reduced'),
    (0.5, 'poor'),
])
def test_visibility_descriptions(miles, keyword):
    desc = visibility_description(miles)
    assert keyword.lower() in desc.lower()
