"""Nominatim (OpenStreetMap) zip-to-location geocoding.

Usage policy: https://operations.osmfoundation.org/policies/nominatim/
- Must send a meaningful User-Agent header (see CLAUDE.md)
- Max 1 request/second — enforced by the 800ms UI debounce in add_location.py
"""
import threading
from typing import Callable, Optional

import requests

from src.models.location import Location

_URL = 'https://nominatim.openstreetmap.org/search'
_HEADERS = {
    'User-Agent': 'kakoritz-WeatherApp/1.0 (adam@adamscottspiker.org)',
    'Accept-Language': 'en-US,en;q=0.9',
}
_TIMEOUT = 8


def _extract_city(address: dict) -> str:
    """Pull the best city name from a Nominatim address dict.

    Priority: city > town > village > hamlet > municipality > suburb > county.
    For county results (e.g. zip resolves to 'Rutherford County'), strip the
    ' County' suffix so we get 'Rutherford' at worst.
    """
    for key in ('city', 'town', 'village', 'hamlet', 'municipality', 'suburb'):
        if key in address and address[key]:
            return address[key]
    if 'county' in address:
        name = address['county']
        if name.endswith(' County'):
            name = name[:-7]
        return name
    return ''


def lookup_zip(
    zip_code: str,
    on_success: Callable[[Location], None],
    on_error: Callable[[str], None],
) -> None:
    """Look up a US zip code in a background thread.
    Calls on_success(Location) or on_error(message) from the background thread.
    Callers must dispatch to the main thread via Clock.schedule_once.
    """
    def _work():
        try:
            resp = requests.get(
                _URL,
                params={
                    'postalcode': zip_code,
                    'country': 'US',
                    'format': 'json',
                    'addressdetails': '1',
                    'limit': '1',
                },
                headers=_HEADERS,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            results = resp.json()
        except requests.RequestException as e:
            on_error(f'Network error: {e}')
            return

        if not results:
            on_error(f'Zip code {zip_code} not found.')
            return

        try:
            r = results[0]
            addr = r.get('address', {})
            city = _extract_city(addr)
            state_abbr = addr.get('state_abbr') or _state_abbr(addr.get('state', ''))
            loc = Location(
                zip=zip_code,
                city=city or zip_code,
                state=state_abbr,
                lat=float(r['lat']),
                lon=float(r['lon']),
            )
            on_success(loc)
        except (KeyError, ValueError, TypeError) as e:
            on_error(f'Parse error: {e}')

    threading.Thread(target=_work, daemon=True).start()


_STATE_ABBREVS = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC',
}


def _state_abbr(full_name: str) -> str:
    return _STATE_ABBREVS.get(full_name, full_name[:2].upper() if full_name else '')
