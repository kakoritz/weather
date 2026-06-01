"""Tests for src/api/weather.py and src/api/geocoding.py.

All HTTP calls are mocked — no real network access required.
"""
import json
import pytest
import responses as resp_mock

from src.api.weather import _parse_forecast, _parse_air_quality
from src.api.geocoding import _extract_city, _state_abbr
from src.models.weather import WeatherData, AirQualityData


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def sample_forecast_json():
    return {
        'current': {
            'temperature_2m': 62.4,
            'apparent_temperature': 61.8,
            'relative_humidity_2m': 99,
            'precipitation': 0.0,
            'weather_code': 2,
            'wind_speed_10m': 5.1,
            'wind_direction_10m': 190,
            'uv_index': 1.0,
            'surface_pressure': 1015.2,
            'visibility': 16093.0,
        },
        'hourly': {
            'time': ['2025-06-01T08:00', '2025-06-01T09:00'],
            'temperature_2m': [62.0, 67.0],
            'apparent_temperature': [61.0, 66.0],
            'relative_humidity_2m': [99, 95],
            'precipitation_probability': [10, 20],
            'precipitation': [0.0, 0.0],
            'weather_code': [2, 2],
            'wind_speed_10m': [5.0, 6.0],
            'wind_direction_10m': [190, 195],
            'surface_pressure': [1015.2, 1015.0],
            'visibility': [16093.0, 16093.0],
        },
        'daily': {
            'time': ['2025-06-01', '2025-06-02'],
            'weather_code': [2, 3],
            'temperature_2m_max': [83.0, 68.0],
            'temperature_2m_min': [59.0, 55.0],
            'precipitation_sum': [0.15, 0.05],
            'precipitation_probability_max': [40, 25],
            'wind_speed_10m_max': [12.0, 8.0],
            'uv_index_max': [5.0, 3.0],
            'sunrise': ['2025-06-01T06:15', '2025-06-02T06:16'],
            'sunset': ['2025-06-01T20:40', '2025-06-02T20:39'],
        },
    }


@pytest.fixture
def sample_aq_json():
    return {
        'current': {
            'us_aqi': 51,
            'pm2_5': 12.3,
            'pm10': 18.5,
            'ozone': 55.2,
            'nitrogen_dioxide': 8.1,
        }
    }


# ──────────────────────────────────────────────
# Forecast parsing
# ──────────────────────────────────────────────

def test_parse_forecast_current_temp(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert data.current.temp == 62


def test_parse_forecast_current_humidity(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert data.current.humidity == 99


def test_parse_forecast_current_code(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert data.current.code == 2


def test_parse_forecast_visibility_converted_to_miles(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    # 16093 metres → ~10 miles
    assert 9.5 < data.current.visibility < 10.5


def test_parse_forecast_hourly_count(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert len(data.hourly) == 2


def test_parse_forecast_hourly_temp(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert data.hourly[0].temp == 62
    assert data.hourly[1].temp == 67


def test_parse_forecast_daily_count(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert len(data.daily) == 2


def test_parse_forecast_daily_max_min(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert data.daily[0].max_temp == 83
    assert data.daily[0].min_temp == 59


def test_parse_forecast_daily_sunrise(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert data.daily[0].sunrise == '2025-06-01T06:15'


def test_parse_forecast_zip_stored(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert data.location_zip == '28139'


def test_parse_forecast_fetched_at_is_set(sample_forecast_json):
    data = _parse_forecast(sample_forecast_json, '28139')
    assert data.fetched_at  # non-empty


# ──────────────────────────────────────────────
# Air quality parsing
# ──────────────────────────────────────────────

def test_parse_air_quality_aqi(sample_aq_json):
    aq = _parse_air_quality(sample_aq_json)
    assert aq is not None
    assert aq.us_aqi == 51


def test_parse_air_quality_category_moderate(sample_aq_json):
    aq = _parse_air_quality(sample_aq_json)
    assert aq.category == 'Moderate'


def test_parse_air_quality_none_on_bad_json():
    aq = _parse_air_quality({'current': None})
    assert aq is None


def test_parse_air_quality_pm_values(sample_aq_json):
    aq = _parse_air_quality(sample_aq_json)
    assert aq.pm2_5 == pytest.approx(12.3)
    assert aq.pm10 == pytest.approx(18.5)


# ──────────────────────────────────────────────
# AQI categories
# ──────────────────────────────────────────────

@pytest.mark.parametrize('aqi,expected', [
    (25, 'Good'),
    (75, 'Moderate'),
    (125, 'Unhealthy for Sensitive Groups'),
    (175, 'Unhealthy'),
    (250, 'Very Unhealthy'),
    (350, 'Hazardous'),
])
def test_aqi_category_thresholds(aqi, expected):
    from src.models.weather import AirQualityData
    aq = AirQualityData(us_aqi=aqi, pm2_5=0, pm10=0, ozone=0, nitrogen_dioxide=0)
    assert aq.category == expected


# ──────────────────────────────────────────────
# Geocoding helpers
# ──────────────────────────────────────────────

def test_extract_city_from_city_key():
    addr = {'city': 'Rutherfordton', 'state': 'North Carolina'}
    assert _extract_city(addr) == 'Rutherfordton'


def test_extract_city_falls_back_to_town():
    addr = {'town': 'Smallville', 'state': 'Kansas'}
    assert _extract_city(addr) == 'Smallville'


def test_extract_city_falls_back_to_village():
    addr = {'village': 'Tiny Place'}
    assert _extract_city(addr) == 'Tiny Place'


def test_extract_city_falls_back_to_county():
    addr = {'county': 'Rutherford County'}
    assert _extract_city(addr) == 'Rutherford County'


def test_extract_city_empty_on_no_match():
    assert _extract_city({}) == ''


def test_state_abbr_known():
    assert _state_abbr('North Carolina') == 'NC'
    assert _state_abbr('California') == 'CA'
    assert _state_abbr('District of Columbia') == 'DC'


def test_state_abbr_unknown_truncates():
    assert _state_abbr('Fakeland') == 'FA'


def test_state_abbr_empty():
    assert _state_abbr('') == ''
