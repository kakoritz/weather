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
