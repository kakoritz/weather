"""WMO weather interpretation code mappings."""

_TABLE = {
    0:  ('Clear Sky',         'clear'),
    1:  ('Mainly Clear',      'clear'),
    2:  ('Partly Cloudy',     'partly_cloudy'),
    3:  ('Overcast',          'overcast'),
    45: ('Fog',               'fog'),
    48: ('Icy Fog',           'fog'),
    51: ('Light Drizzle',     'drizzle'),
    53: ('Drizzle',           'drizzle'),
    55: ('Heavy Drizzle',     'drizzle'),
    61: ('Light Rain',        'rain'),
    63: ('Rain',              'rain'),
    65: ('Heavy Rain',        'heavy_rain'),
    71: ('Light Snow',        'snow'),
    73: ('Snow',              'snow'),
    75: ('Heavy Snow',        'snow'),
    80: ('Rain Showers',      'rain'),
    81: ('Rain Showers',      'rain'),
    82: ('Violent Showers',   'heavy_rain'),
    85: ('Snow Showers',      'snow'),
    86: ('Snow Showers',      'snow'),
    95: ('Thunderstorm',      'thunderstorm'),
    96: ('Thunderstorm',      'thunderstorm'),
    99: ('Severe Thunderstorm','thunderstorm'),
}

_FALLBACK = ('Unknown', 'clear')


def get_label(code: int) -> str:
    return _TABLE.get(code, _FALLBACK)[0]


def get_condition(code: int) -> str:
    """Return the condition key used by WeatherBackground and icon drawers."""
    return _TABLE.get(code, _FALLBACK)[1]


def get_both(code: int) -> tuple[str, str]:
    return _TABLE.get(code, _FALLBACK)


# Background gradient colours per condition key (top_rgba, bottom_rgba) — day variants.
# Night variants are handled separately in WeatherBackground by checking local time.
DAY_GRADIENTS: dict[str, tuple[tuple, tuple]] = {
    'clear':         ((0.31, 0.76, 0.97, 1), (0.01, 0.47, 0.74, 1)),
    'partly_cloudy': ((0.39, 0.71, 0.96, 1), (0.08, 0.40, 0.75, 1)),
    'overcast':      ((0.33, 0.43, 0.48, 1), (0.21, 0.28, 0.31, 1)),
    'fog':           ((0.69, 0.75, 0.78, 1), (0.47, 0.57, 0.63, 1)),
    'drizzle':       ((0.18, 0.35, 0.55, 1), (0.07, 0.18, 0.35, 1)),
    'rain':          ((0.12, 0.23, 0.37, 1), (0.05, 0.11, 0.22, 1)),
    'heavy_rain':    ((0.05, 0.11, 0.22, 1), (0.00, 0.05, 0.12, 1)),
    'snow':          ((0.70, 0.80, 0.91, 1), (0.47, 0.57, 0.70, 1)),
    'thunderstorm':  ((0.10, 0.04, 0.16, 1), (0.05, 0.05, 0.10, 1)),
}

NIGHT_GRADIENTS: dict[str, tuple[tuple, tuple]] = {
    'clear':         ((0.05, 0.11, 0.17, 1), (0.10, 0.14, 0.47, 1)),
    'partly_cloudy': ((0.10, 0.14, 0.47, 1), (0.15, 0.19, 0.22, 1)),
    'overcast':      ((0.12, 0.17, 0.19, 1), (0.07, 0.10, 0.12, 1)),
    'fog':           ((0.26, 0.31, 0.33, 1), (0.15, 0.19, 0.22, 1)),
    'drizzle':       ((0.08, 0.14, 0.22, 1), (0.04, 0.08, 0.14, 1)),
    'rain':          ((0.05, 0.10, 0.17, 1), (0.02, 0.05, 0.10, 1)),
    'heavy_rain':    ((0.02, 0.05, 0.10, 1), (0.00, 0.02, 0.06, 1)),
    'snow':          ((0.12, 0.18, 0.27, 1), (0.08, 0.12, 0.18, 1)),
    'thunderstorm':  ((0.06, 0.04, 0.10, 1), (0.03, 0.03, 0.06, 1)),
}


def is_night() -> bool:
    from datetime import datetime
    h = datetime.now().hour
    return h < 6 or h >= 20


def get_gradients(code: int) -> tuple[tuple, tuple]:
    key = get_condition(code)
    table = NIGHT_GRADIENTS if is_night() else DAY_GRADIENTS
    return table.get(key, DAY_GRADIENTS['clear'])


# WMO code → OpenWeatherMap icon base code + whether it has day/night variants
_OWM_MAP = {
    0: ('01', True),   # clear sky
    1: ('01', True),   # mainly clear
    2: ('02', True),   # partly cloudy
    3: ('04', False),  # overcast
    45: ('50', False), # fog
    48: ('50', False), # icy fog
    51: ('09', False), # light drizzle
    53: ('09', False), # drizzle
    55: ('09', False), # heavy drizzle
    61: ('10', True),  # light rain
    63: ('10', True),  # rain
    65: ('10', True),  # heavy rain
    71: ('13', False), # light snow
    73: ('13', False), # snow
    75: ('13', False), # heavy snow
    80: ('09', False), # rain showers
    81: ('10', True),  # rain showers moderate
    82: ('10', True),  # violent showers
    85: ('13', False), # snow showers
    86: ('13', False), # heavy snow showers
    95: ('11', False), # thunderstorm
    96: ('11', False), # thunderstorm with hail
    99: ('11', False), # severe thunderstorm
}


def get_owm_icon(code: int, night: bool = False) -> str:
    """Return the OpenWeatherMap icon filename (without .png) for a WMO code."""
    base, has_variant = _OWM_MAP.get(code, ('01', True))
    suffix = 'n' if (night and has_variant) else 'd'
    return f'{base}{suffix}'


def get_icon_path(code: int, night: bool | None = None) -> str:
    """Return relative path to the weather icon PNG for this WMO code."""
    if night is None:
        night = is_night()
    return f'assets/icons/{get_owm_icon(code, night)}.png'


# WMO condition → background photo name
_BG_MAP = {
    'clear':         ('clear_day', 'clear_night'),
    'partly_cloudy': ('partly_cloudy_day', 'partly_cloudy_night'),
    'overcast':      ('overcast', 'overcast'),
    'fog':           ('fog', 'fog'),
    'drizzle':       ('drizzle', 'rain'),
    'rain':          ('rain', 'rain'),
    'heavy_rain':    ('heavy_rain', 'heavy_rain'),
    'snow':          ('snow', 'snow'),
    'thunderstorm':  ('thunderstorm', 'thunderstorm'),
}


def get_bg_path(code: int, night: bool | None = None) -> str:
    """Return relative path to the hi-res background photo for the hero card."""
    if night is None:
        night = is_night()
    cond = get_condition(code)
    day_bg, night_bg = _BG_MAP.get(cond, ('clear_day', 'clear_night'))
    name = night_bg if night else day_bg
    return f'assets/backgrounds/{name}.jpg'
