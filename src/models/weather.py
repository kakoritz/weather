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

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'WeatherData':
        current = CurrentConditions(**d['current'])
        hourly = [HourlyEntry(**h) for h in d.get('hourly', [])]
        daily = [DailyForecast(**df) for df in d.get('daily', [])]
        aq = AirQualityData(**d['air_quality']) if d.get('air_quality') else None
        return cls(
            location_zip=d['location_zip'],
            fetched_at=d['fetched_at'],
            current=current,
            hourly=hourly,
            daily=daily,
            air_quality=aq,
        )

    def today_hourly(self) -> list:
        """Return hourly entries for today only (matching daily[0].date)."""
        if not self.daily:
            return self.hourly[:24]
        today = self.daily[0].date
        return [h for h in self.hourly if h.time.startswith(today)]

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
