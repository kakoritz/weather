from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CurrentConditions:
    temp: int
    feels_like: int
    humidity: int
    wind_speed: int
    wind_dir: int
    precip: float
    uv: float
    pressure: float
    visibility: float
    code: int


@dataclass
class HourlyEntry:
    time: str          # ISO datetime string "2025-06-01T14:00"
    temp: int
    feels_like: int
    humidity: int
    wind_speed: int
    wind_dir: int
    precip_prob: int
    precip: float
    pressure: float
    visibility: float
    code: int


@dataclass
class DailyForecast:
    date: str          # "2025-06-01"
    max_temp: int
    min_temp: int
    precip_sum: float
    precip_prob: int
    wind_max: int
    uv_max: float
    sunrise: str       # "2025-06-01T06:15"
    sunset: str        # "2025-06-01T20:40"
    code: int
    moonrise: str = '' # "2025-06-01T20:24" or empty
    moonset: str = ''  # "2025-06-01T06:12" or empty


@dataclass
class MinutelyEntry:
    time: str          # ISO datetime string "2025-06-01T14:15"
    precip: float      # precipitation mm
    precip_prob: int   # precipitation probability 0-100


@dataclass
class WeatherAlert:
    event: str          # "Special Weather Statement", "Tornado Warning", etc.
    headline: str       # full NWS-generated headline (kept for the detail modal)
    description: str    # alert body text, truncated to a sane length
    severity: str        # NWS CAP enum: Extreme | Severe | Moderate | Minor | Unknown
    sent: str = ''        # ISO datetime — used to pick the newest of a reissued alert
    expires: str = ''     # ISO datetime, for display


@dataclass
class AirQualityData:
    us_aqi: int
    pm2_5: float
    pm10: float
    ozone: float
    nitrogen_dioxide: float

    @property
    def category(self) -> str:
        if self.us_aqi <= 50:   return 'Good'
        if self.us_aqi <= 100:  return 'Moderate'
        if self.us_aqi <= 150:  return 'Unhealthy for Sensitive Groups'
        if self.us_aqi <= 200:  return 'Unhealthy'
        if self.us_aqi <= 300:  return 'Very Unhealthy'
        return 'Hazardous'

    @property
    def category_color_rgba(self) -> tuple:
        if self.us_aqi <= 50:   return (0.00, 0.89, 0.00, 1)
        if self.us_aqi <= 100:  return (1.00, 1.00, 0.00, 1)
        if self.us_aqi <= 150:  return (1.00, 0.49, 0.00, 1)
        if self.us_aqi <= 200:  return (1.00, 0.00, 0.00, 1)
        if self.us_aqi <= 300:  return (0.56, 0.25, 0.59, 1)
        return (0.49, 0.00, 0.14, 1)

    @property
    def description(self) -> str:
        if self.us_aqi <= 50:
            return 'Air quality is satisfactory.'
        if self.us_aqi <= 100:
            return f'Air quality is acceptable. AQI is {self.us_aqi}, similar to yesterday.'
        if self.us_aqi <= 150:
            return 'Sensitive groups may experience health effects.'
        if self.us_aqi <= 200:
            return 'Everyone may experience health effects.'
        return 'Health warnings — everyone should limit outdoor activity.'


@dataclass
class WeatherData:
    location_zip: str
    fetched_at: str    # ISO datetime string
    current: CurrentConditions
    hourly: list = field(default_factory=list)     # list[HourlyEntry]
    daily: list = field(default_factory=list)      # list[DailyForecast]
    air_quality: Optional[AirQualityData] = None
    alerts: list = field(default_factory=list)     # list[WeatherAlert]
    minutely: list = field(default_factory=list)   # list[MinutelyEntry] — 15-min intervals

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'WeatherData':
        current = CurrentConditions(**d['current'])
        hourly = [HourlyEntry(**h) for h in d.get('hourly', [])]
        # Explicit construction handles old cache that lacks moonrise/moonset
        daily = [
            DailyForecast(
                date=df['date'], max_temp=df['max_temp'], min_temp=df['min_temp'],
                precip_sum=df['precip_sum'], precip_prob=df['precip_prob'],
                wind_max=df['wind_max'], uv_max=df['uv_max'],
                sunrise=df['sunrise'], sunset=df['sunset'], code=df['code'],
                moonrise=df.get('moonrise', ''), moonset=df.get('moonset', ''),
            )
            for df in d.get('daily', [])
        ]
        aq = AirQualityData(**d['air_quality']) if d.get('air_quality') else None
        # Handles old cache where alerts was list[str] (pre-WeatherAlert) by
        # wrapping each string as a minimal alert rather than crashing.
        alerts = []
        for a in d.get('alerts', []):
            if isinstance(a, dict):
                alerts.append(WeatherAlert(**a))
            else:
                alerts.append(WeatherAlert(event='Weather Alert', headline=str(a),
                                            description='', severity='Unknown'))
        minutely = [MinutelyEntry(**m) for m in d.get('minutely', [])]
        return cls(
            location_zip=d['location_zip'],
            fetched_at=d['fetched_at'],
            current=current,
            hourly=hourly,
            daily=daily,
            air_quality=aq,
            alerts=alerts,
            minutely=minutely,
        )

    def today_hourly(self) -> list:
        """Return hourly entries for today only (matching daily[0].date)."""
        if not self.daily:
            return self.hourly[:24]
        today = self.daily[0].date
        return [h for h in self.hourly if h.time.startswith(today)]

    def next_24_hours(self) -> list:
        """Return 24 hourly entries starting from the current hour.

        NOW threshold: if >= 55 min past the hour (xx:55+), advance to
        the next hour so NOW flips cleanly 5 minutes before the hour turns.
        """
        from datetime import datetime
        now = datetime.now()
        # Advance to next hour if within 5 min of the turn
        hour = now.hour if now.minute < 55 else min(now.hour + 1, 23)
        current_slot = now.strftime(f'%Y-%m-%dT{hour:02d}:00')
        start_idx = None
        for i, h in enumerate(self.hourly):
            if h.time >= current_slot:
                start_idx = i
                break
        if start_idx is None:
            return self.hourly[:24]
        return self.hourly[start_idx:start_idx + 24]

    def today_high(self) -> Optional[int]:
        return self.daily[0].max_temp if self.daily else None

    def today_low(self) -> Optional[int]:
        return self.daily[0].min_temp if self.daily else None

    def today_sunrise(self) -> Optional[str]:
        if not self.daily:
            return None
        raw = self.daily[0].sunrise
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(raw)
            return dt.strftime('%I:%M %p').lstrip('0')
        except Exception:
            return raw

    def today_sunset(self) -> Optional[str]:
        if not self.daily:
            return None
        raw = self.daily[0].sunset
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(raw)
            return dt.strftime('%I:%M %p').lstrip('0')
        except Exception:
            return raw

    def sun_progress(self) -> float:
        """0.0–1.0 position of current time between sunrise and sunset."""
        if not self.daily:
            return 0.5
        try:
            from datetime import datetime
            now = datetime.now()
            sunrise = datetime.fromisoformat(self.daily[0].sunrise)
            sunset = datetime.fromisoformat(self.daily[0].sunset)
            total = (sunset - sunrise).total_seconds()
            elapsed = (now - sunrise).total_seconds()
            return max(0.0, min(1.0, elapsed / total)) if total > 0 else 0.5
        except Exception:
            return 0.5


def wind_direction_label(degrees: int) -> str:
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    return dirs[round(degrees / 22.5) % 16]


def pressure_trend(hourly: list, current_pressure: float) -> str:
    """Compare current pressure to 3h ago."""
    if len(hourly) < 3:
        return 'Steady'
    past = hourly[-3].pressure
    diff = current_pressure - past
    if diff > 0.5:   return 'Rising'
    if diff < -0.5:  return 'Falling'
    return 'Steady'


def feels_like_reason(feels: int, actual: int, humidity: int, wind: int) -> str:
    diff = feels - actual
    if abs(diff) <= 1:
        return 'Similar to the actual temperature.'
    if diff < 0 and wind > 10:
        return f'Wind is making it feel cooler.'
    if diff > 2 and humidity > 70:
        return f'Humidity is making it feel warmer.'
    if diff < 0:
        return 'Feels cooler than the actual temperature.'
    return 'Feels warmer than the actual temperature.'


def visibility_description(miles: float) -> str:
    if miles >= 10: return "It's perfectly clear right now."
    if miles >= 6:  return 'Good visibility.'
    if miles >= 3:  return 'Hazy conditions.'
    if miles >= 1:  return 'Reduced visibility.'
    return 'Very poor visibility.'
