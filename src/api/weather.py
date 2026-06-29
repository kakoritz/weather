"""Open-Meteo weather + air quality API client."""
import threading
from datetime import datetime
from typing import Callable, Optional

import requests

from src.models.weather import (
    AirQualityData, CurrentConditions, DailyForecast,
    HourlyEntry, WeatherData, WeatherAlert,
)

# NWS CAP severity ranking — higher shows first / sorts ahead
_SEVERITY_RANK = {'Extreme': 4, 'Severe': 3, 'Moderate': 2, 'Minor': 1, 'Unknown': 0}

_FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
_AQ_URL = 'https://air-quality-api.open-meteo.com/v1/air-quality'
_NWS_URL = 'https://api.weather.gov/alerts/active'
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
    n_days = len(d['time'])
    daily = [
        DailyForecast(
            date=d['time'][i],
            max_temp=round(d['temperature_2m_max'][i]),
            min_temp=round(d['temperature_2m_min'][i]),
            precip_sum=d['precipitation_sum'][i] or 0.0,
            precip_prob=int(d.get('precipitation_probability_max', [0]*n_days)[i] or 0),
            wind_max=round(d['wind_speed_10m_max'][i]),
            uv_max=d['uv_index_max'][i] or 0.0,
            sunrise=d['sunrise'][i],
            sunset=d['sunset'][i],
            code=int(d['weather_code'][i]),
        )
        for i in range(n_days)
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


def _fetch_nws_alerts(lat: float, lon: float) -> list:
    """Active NWS weather alerts for a US location. Returns [] outside US or on error.

    NWS frequently reissues an updated version of the same advisory (e.g. a
    "Special Weather Statement" reissued every few hours for an ongoing
    situation) while the older one is still technically "active" until its
    own expiry. Without deduping, two near-identical banners look like a
    rendering bug rather than the same real alert being refreshed. Dedup by
    `event` name, keeping only the most recently `sent` one — this trades a
    small risk (a rare second, genuinely distinct alert sharing the same
    generic event category gets hidden) for fixing the much more common case.
    """
    try:
        resp = requests.get(
            _NWS_URL,
            params={'point': f'{lat:.4f},{lon:.4f}'},
            headers={
                'User-Agent': 'kakoritz-WeatherApp/1.3 (adam@adamscottspiker.org)',
                'Accept': 'application/geo+json',
            },
            timeout=5,
        )
        if not resp.ok:
            return []

        by_event: dict = {}
        for f in resp.json().get('features', []):
            props = f.get('properties', {})
            event = props.get('event') or 'Weather Alert'
            sent = props.get('sent', '')
            existing = by_event.get(event)
            if existing is not None and existing.sent >= sent:
                continue
            by_event[event] = WeatherAlert(
                event=event,
                headline=props.get('headline') or event,
                description=(props.get('description') or '')[:280],
                severity=props.get('severity', 'Unknown'),
                sent=sent,
                expires=props.get('expires', ''),
            )

        alerts = sorted(
            by_event.values(),
            key=lambda a: _SEVERITY_RANK.get(a.severity, 0),
            reverse=True,
        )
        return alerts[:3]
    except Exception:
        return []


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
            pass

        # NWS alerts — US only, non-critical
        try:
            data.alerts = _fetch_nws_alerts(lat, lon)
        except Exception:
            pass

        on_success(data)

    threading.Thread(target=_work, daemon=True).start()
