"""WeatherApp — iOS-faithful Android weather app.
Built with Python / Kivy 2.3.0 / KivyMD 1.2.0.
"""
__version__ = '1.0.0'

import os
import sys
import traceback

# Write crash at import-time errors to /sdcard/ which is world-readable
def _write_crash(exc, path=None):
    try:
        if path is None:
            path = '/sdcard/weatherapp_crash.log'
        with open(path, 'w') as f:
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
            f.write('\nPython: ' + sys.version + '\n')
    except Exception:
        pass

try:
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    # Keep console logging ON so errors appear in logcat
    # os.environ.setdefault('KIVY_NO_CONSOLELOG', '1')

    from kivy.config import Config
    Config.set('kivy', 'exit_on_escape', '0')
    Config.set('graphics', 'resizable', '0')
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.utils import platform
    from kivymd.app import MDApp
    from kivy.uix.screenmanager import ScreenManager, FadeTransition

    from src.models.location import Location
    from src.storage.manager import StorageManager
    from src.screens.add_location import AddLocationScreen
    from src.screens.location_list import LocationListScreen
    from src.screens.weather_detail import WeatherCarouselScreen

except Exception as _import_exc:
    _write_crash(_import_exc)
    raise


class WeatherApp(MDApp):
    title = 'Weather'

    def build(self):
        # Theme
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'LightBlue'

        # Desktop: set a phone-like window size for development
        if platform not in ('android', 'ios'):
            Window.size = (400, 820)

        # Request Android permissions (no-op on other platforms)
        if platform == 'android':
            self._request_android_permissions()

        self.storage = StorageManager()
        self.sm = ScreenManager(transition=FadeTransition(duration=0.18))

        locations = self.storage.load_locations()

        if not locations:
            # No saved locations — go straight to add screen
            add_screen = AddLocationScreen(
                name='add_location',
                on_location_added=self._on_first_location_added,
            )
            self.sm.add_widget(add_screen)
            self.sm.current = 'add_location'
        else:
            self._build_main_screens(locations)

        return self.sm

    def _build_main_screens(self, locations: list):
        """Build the carousel + list screens with the given locations."""
        carousel_screen = WeatherCarouselScreen(
            name='weather_carousel',
            locations=locations,
            storage=self.storage,
        )
        self.sm.add_widget(carousel_screen)

        list_screen = LocationListScreen(
            name='location_list',
            locations=locations,
            weather_map=carousel_screen.weather_map,
            on_tap=self._on_list_tap,
            on_add=self._on_add_requested,
            on_delete=self._on_delete_location,
        )
        self.sm.add_widget(list_screen)

        # Add location screen (accessible from list)
        add_screen = AddLocationScreen(
            name='add_location',
            on_location_added=self._on_location_added,
        )
        self.sm.add_widget(add_screen)

        self.sm.current = 'weather_carousel'

    def _on_first_location_added(self, location: Location):
        """Called from AddLocationScreen when the very first location is saved."""
        self.storage.add_location(location)
        locations = self.storage.load_locations()

        # Remove the bootstrap add_location screen and build proper screens
        self.sm.remove_widget(self.sm.get_screen('add_location'))
        self._build_main_screens(locations)

    def _on_location_added(self, location: Location):
        """Called from AddLocationScreen when a new location is added (non-first)."""
        self.storage.add_location(location)
        carousel = self.sm.get_screen('weather_carousel')
        carousel.add_location(location)

        # Rebuild list screen with updated data
        self._rebuild_list_screen()

        self.sm.current = 'weather_carousel'

    def _on_list_tap(self, location: Location):
        """User tapped a location in the list — jump carousel to that location."""
        carousel = self.sm.get_screen('weather_carousel')
        carousel.navigate_to(location.zip)
        self.sm.current = 'weather_carousel'

    def _on_add_requested(self):
        self.sm.current = 'add_location'

    def _on_delete_location(self, zip_code: str):
        self.storage.remove_location(zip_code)
        carousel = self.sm.get_screen('weather_carousel')
        carousel.remove_location(zip_code)
        self._rebuild_list_screen()

        # If no locations remain, go back to add screen
        if not self.storage.load_locations():
            self.sm.remove_widget(self.sm.get_screen('weather_carousel'))
            if self.sm.has_screen('location_list'):
                self.sm.remove_widget(self.sm.get_screen('location_list'))
            if self.sm.has_screen('add_location'):
                self.sm.remove_widget(self.sm.get_screen('add_location'))

            add_screen = AddLocationScreen(
                name='add_location',
                on_location_added=self._on_first_location_added,
            )
            self.sm.add_widget(add_screen)
            self.sm.current = 'add_location'

    def _rebuild_list_screen(self):
        carousel = self.sm.get_screen('weather_carousel')
        if self.sm.has_screen('location_list'):
            self.sm.remove_widget(self.sm.get_screen('location_list'))
        list_screen = LocationListScreen(
            name='location_list',
            locations=carousel.locations,
            weather_map=carousel.weather_map,
            on_tap=self._on_list_tap,
            on_add=self._on_add_requested,
            on_delete=self._on_delete_location,
        )
        self.sm.add_widget(list_screen)

    @staticmethod
    def _request_android_permissions():
        try:
            from android.permissions import request_permissions, Permission  # type: ignore
            request_permissions([Permission.INTERNET, Permission.ACCESS_NETWORK_STATE])
        except ImportError:
            pass


if __name__ == '__main__':
    try:
        WeatherApp().run()
    except Exception as e:
        _write_crash(e)
        raise
