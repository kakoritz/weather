"""Open-Meteo weather + air quality API client."""
import threading
from datetime import datetime
from typing import Callable, Optional

import requests

from src.models.weather import (
    AirQualityData, CurrentConditions, DailyForecast,
    HourlyEntry, WeatherData,
)

_FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
_AQ_URL = 'https://air-quality-api.open-meteo.com/v1/air-quality'
_TIMEOUT = 10


def _build_forecast_params(lat: float, lon: float) -> dict:
    return {
        'latitude': lat,
        'longitude': lon,
        'current': (
            'temperature_2m,relative_humidity_2m,apparent_temperature,'
            'precipitation,weather_code,wind_speed_10m,wind_direction_10m,'
            'uv_index,surface_pressure,visibility'
        ),
        'hourly': (
            'temperature_2m,apparent_temperature,relative_humidity_2m,'
            'precipitation_probability,precipitation,weather_code,'
            'wind_speed_10m,wind_direction_10m,surface_pressure,visibility'
        ),
        'daily': (
            'weather_code,temperature_2m_max,temperature_2m_min,'
            'precipitation_sum,precipitation_probability_max,'
            'wind_speed_10m_max,uv_index_max,sunrise,sunset'
        ),
        'temperature_unit': 'fahrenheit',
        'windspeed_unit': 'mph',
        'precipitation_unit': 'inch',
        'timezone': 'auto',
        'forecast_days': 10,
    }


def _parse_forecast(json: dict, zip_code: str) -> WeatherData:
    c = json['current']
    current = CurrentConditions(
        temp=round(c['temperature_2m']),
        feels_like=round(c['apparent_temperature']),
        humidity=int(c['relative_humidity_2m']),
        wind_speed=round(c['wind_speed_10m']),
        wind_dir=int(c['wind_direction_10m']),
        precip=c['precipitation'],
        uv=c['uv_index'],
        pressure=c['surface_pressure'],
        visibility=c.get('visibility', 10.0) * 0.000621371,  # metres → miles
        code=int(c['weather_code']),
    )

    h = json['hourly']
    hourly = [
        HourlyEntry(
            time=h['time'][i],
            temp=round(h['temperature_2m'][i]),
            feels_like=round(h['apparent_temperature'][i]),
            humidity=int(h['relative_humidity_2m'][i]),
            wind_speed=round(h['wind_speed_10m'][i]),
            wind_dir=int(h['wind_direction_10m'][i]),
            precip_prob=int(h['precipitation_probability'][i] or 0),
            precip=h['precipitation'][i] or 0.0,
            pressure=h['surface_pressure'][i] or 0.0,
            visibility=(h.get('visibility', [10000.0] * len(h['time']))[i] or 10000.0) * 0.000621371,
            code=int(h['weather_code'][i]),
        )
        for i in range(len(h['time']))
    ]

    d = json['daily']
    daily = [
        DailyForecast(
            date=d['time'][i],
            max_temp=round(d['temperature_2m_max'][i]),
            min_temp=round(d['temperature_2m_min'][i]),
            precip_sum=d['precipitation_sum'][i] or 0.0,
            precip_prob=int(d.get('precipitation_probability_max', [0]*10)[i] or 0),
            wind_max=round(d['wind_speed_10m_max'][i]),
            uv_max=d['uv_index_max'][i] or 0.0,
            sunrise=d['sunrise'][i],
            sunset=d['sunset'][i],
            code=int(d['weather_code'][i]),
        )
        for i in range(len(d['time']))
    ]

    return WeatherData(
        location_zip=zip_code,
        fetched_at=datetime.now().isoformat(),
        current=current,
        hourly=hourly,
        daily=daily,
    )


def _parse_air_quality(json: dict) -> Optional[AirQualityData]:
    try:
        c = json['current']
        return AirQualityData(
            us_aqi=int(c.get('us_aqi') or 0),
            pm2_5=c.get('pm2_5') or 0.0,
            pm10=c.get('pm10') or 0.0,
            ozone=c.get('ozone') or 0.0,
            nitrogen_dioxide=c.get('nitrogen_dioxide') or 0.0,
        )
    except Exception:
        return None


def fetch_weather(
    lat: float,
    lon: float,
    zip_code: str,
    on_success: Callable[[WeatherData], None],
    on_error: Callable[[str], None],
) -> None:
    """Fetch forecast + air quality in a background thread.
    Calls on_success or on_error from the background thread — callers must
    dispatch to the main thread via Clock.schedule_once if updating UI.
    """
    def _work():
        try:
            resp = requests.get(
                _FORECAST_URL,
                params=_build_forecast_params(lat, lon),
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = _parse_forecast(resp.json(), zip_code)
        except requests.RequestException as e:
            on_error(f'Weather fetch failed: {e}')
            return
        except (KeyError, TypeError, ValueError) as e:
            on_error(f'Weather parse error: {e}')
            return

        try:
            aq_resp = requests.get(
                _AQ_URL,
                params={
                    'latitude': lat,
                    'longitude': lon,
                    'current': 'us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide',
                    'timezone': 'auto',
                },
                timeout=_TIMEOUT,
            )
            if aq_resp.ok:
                data.air_quality = _parse_air_quality(aq_resp.json())
        except Exception:
            pass  # air quality is non-critical; weather data is still returned

        on_success(data)

    threading.Thread(target=_work, daemon=True).start()
