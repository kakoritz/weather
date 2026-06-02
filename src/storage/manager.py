"""JSON-based persistence for locations and weather cache."""
import json
import os
from datetime import datetime
from typing import Optional

from src.models.location import Location
from src.models.weather import WeatherData

CACHE_TTL_SECONDS = 600   # 10 minutes — normal refresh
CACHE_STALE_SECONDS = 1800  # 30 minutes — force-refresh on app open if older


class StorageManager:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = self._resolve_data_dir()
        self._data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._locations_path = os.path.join(data_dir, 'locations.json')
        self._cache_path = os.path.join(data_dir, 'weather_cache.json')

    @staticmethod
    def _resolve_data_dir() -> str:
        # On Android, ANDROID_PRIVATE points to internal storage
        android_private = os.environ.get('ANDROID_PRIVATE')
        if android_private:
            return android_private
        # Desktop: store next to main.py
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')

    # --- Locations ---

    def load_locations(self) -> list:
        """Return list[Location] from disk, empty list if file doesn't exist."""
        try:
            with open(self._locations_path) as f:
                raw = json.load(f)
            return [Location.from_dict(d) for d in raw]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return []

    def save_locations(self, locations: list) -> None:
        """Persist list[Location] to disk."""
        with open(self._locations_path, 'w') as f:
            json.dump([loc.to_dict() for loc in locations], f, indent=2)

    def add_location(self, location: Location) -> list:
        """Append location if not already present (by zip). Returns updated list."""
        locations = self.load_locations()
        if any(loc.zip == location.zip for loc in locations):
            return locations
        locations.append(location)
        self.save_locations(locations)
        return locations

    def remove_location(self, zip_code: str) -> list:
        """Remove location by zip. Returns updated list."""
        locations = [loc for loc in self.load_locations() if loc.zip != zip_code]
        self.save_locations(locations)
        self._evict_cache(zip_code)
        return locations

    # --- Weather cache ---

    def _load_cache(self) -> dict:
        try:
            with open(self._cache_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache(self, cache: dict) -> None:
        with open(self._cache_path, 'w') as f:
            json.dump(cache, f)

    def _evict_cache(self, zip_code: str) -> None:
        cache = self._load_cache()
        cache.pop(zip_code, None)
        self._save_cache(cache)

    def get_cached_weather(self, zip_code: str) -> Optional[WeatherData]:
        """Return cached WeatherData if it exists and is within TTL, else None."""
        cache = self._load_cache()
        entry = cache.get(zip_code)
        if not entry:
            return None
        try:
            fetched = datetime.fromisoformat(entry['timestamp'])
            age = (datetime.now() - fetched).total_seconds()
            if age > CACHE_TTL_SECONDS:
                return None
            return WeatherData.from_dict(entry['data'])
        except Exception:
            return None

    def save_weather_cache(self, zip_code: str, data: WeatherData) -> None:
        cache = self._load_cache()
        cache[zip_code] = {
            'timestamp': datetime.now().isoformat(),
            'data': data.to_dict(),
        }
        self._save_cache(cache)
