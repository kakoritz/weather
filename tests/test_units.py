"""Tests for src/utils/units.py — the single source of truth for °F/°C display."""
from src.utils.units import to_display, fmt_temp


def test_to_display_fahrenheit_passthrough():
    assert to_display(72, 'F') == 72


def test_to_display_celsius_conversion():
    assert to_display(32, 'C') == 0
    assert to_display(212, 'C') == 100
    assert to_display(98, 'C') == 37


def test_fmt_temp_appends_degree_symbol():
    assert fmt_temp(72, 'F') == '72°'
    assert fmt_temp(32, 'C') == '0°'
