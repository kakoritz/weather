"""Temperature unit conversion — single source of truth for °F/°C display.

All weather data is fetched and cached in Fahrenheit (see api/weather.py).
Every screen that displays a temperature must go through this module so the
F/C toggle in the menu affects the entire app, not just one screen.
"""


def to_display(fahrenheit: int, units: str) -> int:
    """Convert a stored Fahrenheit value to the display unit, rounded to an int."""
    if units == 'C':
        return round((fahrenheit - 32) * 5 / 9)
    return fahrenheit


def fmt_temp(fahrenheit: int, units: str) -> str:
    """Format a stored Fahrenheit value as a display string, e.g. '72°'."""
    return f'{to_display(fahrenheit, units)}°'
