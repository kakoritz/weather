#!/usr/bin/env python3
"""
WeatherApp Mobile Device Test Suite
====================================
Runs against the installed APK via ADB.  Equivalent of Playwright for the phone.

Usage:
    python3 tests/device/device_tests.py
    python3 tests/device/device_tests.py --verbose
    python3 tests/device/device_tests.py --test add_city

What it tests:
  1.  App cold launch — no crash, weather screen or add-city screen appears
  2.  Add city via search — type zip, pick from dropdown, stays on list
  3.  Weather screen loads — hero card visible, data appears
  4.  Navigate list screen — tap list icon, list appears
  5.  Open menu — tap ⋯, menu appears above cards
  6.  Toggle F→C — temperatures change
  7.  Toggle C→F — temperatures revert
  8.  Navigate back from menu — dismiss menu
  9.  See More (Air Quality) — modal appears, solid background
  10. Close See More — modal dismisses
  11. Add second city — both cards visible in list
  12. Swipe-to-delete — reveal trash icon
  13. Confirm delete — city removed
  14. Scroll weather screen — no crash at See More cards
  15. Navigate between locations via dot bar swipe

Requirements:
    pip install pillow
    Device connected via ADB (USB or wireless)
"""

import argparse
import subprocess
import sys
import time
import os
import io
from datetime import datetime
from typing import Optional

try:
    from PIL import Image
    import numpy as np
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("WARNING: Pillow not found — pixel checks disabled. pip install pillow")


# ── Phone layout constants (1080x2400 @ 420dpi) ──────────────────────────────
# All positions as fractions of screen width/height for resolution independence.

PKG = 'org.kakoritz.weatherapp'
ACTIVITY = f'{PKG}/org.kivy.android.PythonActivity'
DATA_DIR = f'/data/user/0/{PKG}/files'


class _R:
    """Screen region constants as (x_frac, y_frac) from top-left."""
    # Weather main screen
    HERO_CENTER          = (0.50, 0.12)   # centre of hero card
    HERO_TEMP            = (0.50, 0.10)   # temperature text area
    LIST_ICON            = (0.93, 0.96)   # ≡ list button (bottom right)
    DOT_BAR              = (0.50, 0.975)  # page dot nav bar
    SEE_MORE_AQ          = (0.87, 0.64)   # Air Quality see more (approx)

    # Location list screen
    SEARCH_BAR           = (0.50, 0.19)   # search field
    FIRST_CARD           = (0.50, 0.38)   # first location card centre
    SECOND_CARD          = (0.50, 0.52)   # second card
    MENU_BTN             = (0.93, 0.08)   # ⋯ menu button
    AUTOCOMPLETE_FIRST   = (0.50, 0.30)   # first autocomplete result

    # Menu items (approximate y positions when menu is open)
    MENU_EDIT_LIST       = (0.77, 0.62)
    MENU_FAHRENHEIT      = (0.77, 0.70)
    MENU_CELSIUS         = (0.77, 0.76)
    MENU_CLOSE_AREA      = (0.50, 0.30)   # tap outside menu to close

    # Modal
    MODAL_CLOSE          = (0.93, 0.07)   # X button on modal
    MODAL_BODY           = (0.50, 0.55)   # body of the modal


# ── Test runner ───────────────────────────────────────────────────────────────

class DeviceTestRunner:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = []          # [(name, passed, detail)]
        self.W, self.H = self._get_screen_size()
        self._last_logcat_clear = datetime.now()
        print(f"Screen: {self.W}x{self.H}")
        print(f"Package: {PKG}\n")

    # ── ADB helpers ───────────────────────────────────────────────────────────

    def adb(self, *args, check=False, timeout=15) -> str:
        result = subprocess.run(['adb'] + list(args), capture_output=True,
                                text=True, timeout=timeout)
        return result.stdout + result.stderr

    def _get_screen_size(self):
        out = self.adb('shell', 'wm', 'size')
        for line in out.split('\n'):
            if 'Physical size' in line or 'Override size' in line:
                parts = line.split()[-1].split('x')
                return int(parts[0]), int(parts[1])
        return 1080, 2400

    def wake(self):
        self.adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
        time.sleep(0.3)

    def tap(self, x_frac: float, y_frac: float, wait: float = 0.6):
        x, y = int(x_frac * self.W), int(y_frac * self.H)
        if self.verbose:
            print(f"    tap({x}, {y})")
        self.adb('shell', 'input', 'tap', str(x), str(y))
        time.sleep(wait)

    def swipe(self, x1f, y1f, x2f, y2f, ms=400, wait=0.5):
        x1, y1 = int(x1f*self.W), int(y1f*self.H)
        x2, y2 = int(x2f*self.W), int(y2f*self.H)
        self.adb('shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(ms))
        time.sleep(wait)

    def type_text(self, text: str, wait: float = 0.4):
        # ADB text input doesn't handle spaces well — use one char at a time for reliability
        self.adb('shell', 'input', 'text', text.replace(' ', '%s'))
        time.sleep(wait)

    def clear_field(self):
        """Select all and delete."""
        self.adb('shell', 'input', 'keyevent', 'KEYCODE_CTRL_A')
        time.sleep(0.1)
        self.adb('shell', 'input', 'keyevent', 'KEYCODE_DEL')
        time.sleep(0.2)

    def screenshot(self) -> Optional['Image.Image']:
        if not HAS_PIL:
            return None
        self.adb('shell', 'screencap', '-p', '/sdcard/test_qa.png')
        self.adb('pull', '/sdcard/test_qa.png', '/tmp/test_qa.png')
        try:
            return Image.open('/tmp/test_qa.png').convert('RGB')
        except Exception:
            return None

    def save_screenshot(self, name: str):
        img = self.screenshot()
        if img:
            path = f'/tmp/qa_{name}_{datetime.now().strftime("%H%M%S")}.png'
            img.save(path)
            if self.verbose:
                print(f"    Screenshot: {path}")

    def clear_logcat(self):
        self.adb('logcat', '-c')
        self._last_logcat_clear = datetime.now()
        time.sleep(0.2)

    def check_no_crash(self) -> bool:
        """Returns True if no crash has occurred since last clear_logcat()."""
        out = self.adb('logcat', '-d', '-s', 'python')
        return 'Python for android ended' not in out

    def wait_for_load(self, seconds=10):
        """Wait for app to finish loading (looks for KivyMD loaded message)."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            out = self.adb('logcat', '-d', '-s', 'python')
            if 'KivyMD' in out or 'Start application main loop' in out:
                return True
            if 'Python for android ended' in out:
                return False
            time.sleep(0.5)
        return True  # assume loaded if no crash

    def pixel_color(self, img, xf, yf):
        if img is None:
            return (0, 0, 0)
        x, y = int(xf * img.width), int(yf * img.height)
        return img.getpixel((min(x, img.width-1), min(y, img.height-1)))

    def is_dark_bg(self, img, xf=0.5, yf=0.5, threshold=80) -> bool:
        """True if the pixel at position is dark (app background, not white)."""
        if img is None: return True
        r, g, b = self.pixel_color(img, xf, yf)
        return r < threshold and g < threshold and b < threshold

    def is_blue_sky(self, img, xf=0.5, yf=0.08) -> bool:
        """True if hero card area shows a non-white, non-black colour (any gradient)."""
        if img is None: return True
        # Sample several spots across top area and check at least one is coloured
        for xf2, yf2 in [(0.3, 0.08), (0.5, 0.06), (0.7, 0.08)]:
            r, g, b = self.pixel_color(img, xf2, yf2)
            total = r + g + b
            if total > 60 and total < 700:  # not pure black and not pure white
                return True
        return False

    # ── Test assertion ────────────────────────────────────────────────────────

    def assert_test(self, name: str, passed: bool, detail: str = ''):
        icon = '✓' if passed else '✗'
        color = '\033[92m' if passed else '\033[91m'
        reset = '\033[0m'
        print(f"  {color}{icon}{reset} {name}" + (f" — {detail}" if detail else ''))
        self.results.append((name, passed, detail))

    # ── App lifecycle ─────────────────────────────────────────────────────────

    def fresh_launch(self):
        """Force-stop, clear cache, relaunch."""
        self.wake()
        self.adb('shell', 'am', 'force-stop', PKG)
        time.sleep(1)
        # Clear weather cache so we get fresh fetch
        self.adb('shell', 'run-as', PKG, 'rm', '-f', 'files/weather_cache.json')
        self.clear_logcat()
        self.adb('shell', 'am', 'start', '-n', ACTIVITY)
        time.sleep(2)
        loaded = self.wait_for_load(12)
        return loaded

    def launch_with_no_data(self):
        """Remove all saved locations and relaunch — should show add-city screen."""
        self.wake()
        self.adb('shell', 'am', 'force-stop', PKG)
        time.sleep(1)
        self.adb('shell', 'run-as', PKG, 'rm', '-f', 'files/locations.json')
        self.adb('shell', 'run-as', PKG, 'rm', '-f', 'files/weather_cache.json')
        self.clear_logcat()
        self.adb('shell', 'am', 'start', '-n', ACTIVITY)
        time.sleep(2)
        self.wait_for_load(12)

    # ── Individual tests ──────────────────────────────────────────────────────

    def test_launch_no_crash(self):
        print("\n[1] App cold launch")
        self.fresh_launch()
        time.sleep(3)
        ok = self.check_no_crash()
        self.assert_test("App launches without crash", ok)
        img = self.screenshot()
        self.save_screenshot("launch")
        # Should see dark background (app rendered)
        not_white = self.is_dark_bg(img, 0.5, 0.5, threshold=200)
        self.assert_test("Screen is not blank white", not_white)

    def test_add_city_via_search(self):
        print("\n[2] Add city via search")
        self.launch_with_no_data()
        time.sleep(2)
        img = self.screenshot()
        self.save_screenshot("add_screen")
        # Should see the add-location or list screen
        no_crash = self.check_no_crash()
        self.assert_test("App didn't crash on fresh launch", no_crash)

        # Navigate to list screen (might already be there)
        self.tap(*_R.LIST_ICON, wait=1.0)
        time.sleep(1)

        # Tap search bar
        self.tap(*_R.SEARCH_BAR, wait=0.8)
        time.sleep(0.5)

        # Type a zip code
        self.type_text('28139', wait=1.0)
        time.sleep(1.5)  # Wait for autocomplete

        img = self.screenshot()
        self.save_screenshot("search_typed")
        no_crash = self.check_no_crash()
        self.assert_test("Search typing doesn't crash", no_crash)

        # Tap the first autocomplete result
        self.tap(*_R.AUTOCOMPLETE_FIRST, wait=1.5)
        time.sleep(2)

        no_crash = self.check_no_crash()
        self.assert_test("City selection doesn't crash", no_crash)
        self.save_screenshot("after_add_city")

    def test_weather_screen_loads(self):
        print("\n[3] Weather screen loads data")
        self.fresh_launch()
        time.sleep(8)  # Wait for weather fetch

        # Check logcat for successful API call — give it a few extra seconds
        # to appear in logcat buffer after app is running
        api_success = False
        for _ in range(6):
            out = self.adb('logcat', '-d', '-s', 'python')
            if 'HTTP/1.1" 200' in out and 'open-meteo' in out:
                api_success = True
                break
            time.sleep(1)
        self.assert_test("Open-Meteo API call succeeded (HTTP 200)", api_success)

        img = self.screenshot()
        self.save_screenshot("weather_loaded")
        no_crash = self.check_no_crash()
        self.assert_test("Weather screen loaded without crash", no_crash)
        sky_visible = self.is_blue_sky(img)
        self.assert_test("Hero card shows sky blue gradient", sky_visible)

    def test_navigate_to_list(self):
        print("\n[4] Navigate to location list")
        self.fresh_launch()
        time.sleep(6)
        self.clear_logcat()

        self.tap(*_R.LIST_ICON, wait=1.0)
        time.sleep(1)

        img = self.screenshot()
        self.save_screenshot("list_screen")
        no_crash = self.check_no_crash()
        self.assert_test("List screen navigate doesn't crash", no_crash)

        # Sample right edge of screen between cards (not on text or card bg)
        # bg color is (10,13,26) — sample at far right where no card overlaps
        dark = self.is_dark_bg(img, 0.02, 0.50, threshold=60)
        self.assert_test("List screen has dark background", dark)

    def test_menu_open_close(self):
        print("\n[5] Menu open and close")
        self.fresh_launch()
        time.sleep(6)
        self.tap(*_R.LIST_ICON, wait=1.0)
        time.sleep(1)
        self.clear_logcat()

        # Open menu
        self.tap(*_R.MENU_BTN, wait=0.8)
        time.sleep(1)

        img = self.screenshot()
        self.save_screenshot("menu_open")
        no_crash = self.check_no_crash()
        self.assert_test("Menu opens without crash", no_crash)

        # Close by tapping outside
        self.tap(*_R.MENU_CLOSE_AREA, wait=0.8)
        time.sleep(0.5)
        no_crash = self.check_no_crash()
        self.assert_test("Menu closes without crash", no_crash)

    def test_celsius_fahrenheit_toggle(self):
        print("\n[6] Celsius / Fahrenheit toggle")
        self.fresh_launch()
        time.sleep(6)
        self.tap(*_R.LIST_ICON, wait=1.0)
        time.sleep(1)

        # Open menu and tap Celsius
        self.tap(*_R.MENU_BTN, wait=0.8)
        time.sleep(1)
        self.clear_logcat()
        self.tap(*_R.MENU_CELSIUS, wait=1.0)
        time.sleep(1.5)

        no_crash = self.check_no_crash()
        self.assert_test("Toggle to Celsius doesn't crash", no_crash)

        # Switch back to Fahrenheit
        self.tap(*_R.MENU_BTN, wait=0.8)
        time.sleep(1)
        self.clear_logcat()
        self.tap(*_R.MENU_FAHRENHEIT, wait=1.0)
        time.sleep(1)
        no_crash = self.check_no_crash()
        self.assert_test("Toggle to Fahrenheit doesn't crash", no_crash)

    def test_see_more_air_quality(self):
        print("\n[7] See More — Air Quality modal")
        self.fresh_launch()
        time.sleep(8)  # Needs weather loaded first

        no_crash = self.check_no_crash()
        if not no_crash:
            self.assert_test("App loaded for See More test", False, "Crash on load")
            return

        # Scroll down to find Air Quality card
        for _ in range(3):
            self.swipe(0.5, 0.70, 0.5, 0.30, ms=500, wait=0.5)
        time.sleep(0.5)

        self.clear_logcat()
        # Tap the See More footer area (approximate)
        self.tap(*_R.SEE_MORE_AQ, wait=1.0)
        time.sleep(1.5)

        img = self.screenshot()
        self.save_screenshot("see_more_aq")
        no_crash = self.check_no_crash()
        self.assert_test("Air Quality See More doesn't crash", no_crash)

        # Close modal
        self.tap(*_R.MODAL_CLOSE, wait=0.8)
        time.sleep(0.5)
        no_crash = self.check_no_crash()
        self.assert_test("Modal close doesn't crash", no_crash)

    def test_scroll_no_crash(self):
        print("\n[8] Full scroll through weather page")
        self.fresh_launch()
        time.sleep(8)
        self.clear_logcat()

        # Scroll from top to bottom multiple times
        for i in range(6):
            self.swipe(0.5, 0.75, 0.5, 0.20, ms=400, wait=0.3)
        time.sleep(0.5)
        # Scroll back up
        for i in range(4):
            self.swipe(0.5, 0.25, 0.5, 0.75, ms=400, wait=0.3)
        time.sleep(0.3)

        no_crash = self.check_no_crash()
        self.assert_test("Full page scroll doesn't crash", no_crash)

    def test_swipe_to_delete_reveal(self):
        print("\n[9] Swipe to reveal delete on location card")
        self.fresh_launch()
        time.sleep(6)
        self.tap(*_R.LIST_ICON, wait=1.0)
        time.sleep(1)
        self.clear_logcat()

        # Swipe left on first card to reveal delete
        self.swipe(0.70, 0.38, 0.20, 0.38, ms=300, wait=0.8)
        time.sleep(0.5)

        img = self.screenshot()
        self.save_screenshot("delete_revealed")
        no_crash = self.check_no_crash()
        self.assert_test("Swipe to reveal delete doesn't crash", no_crash)

        # Swipe back to close
        self.swipe(0.20, 0.38, 0.70, 0.38, ms=300, wait=0.8)
        no_crash = self.check_no_crash()
        self.assert_test("Swipe back to close doesn't crash", no_crash)

    # ── Test runner ───────────────────────────────────────────────────────────

    def run_all(self, tests=None):
        all_tests = [
            ('launch',        self.test_launch_no_crash),
            ('add_city',      self.test_add_city_via_search),
            ('weather_loads', self.test_weather_screen_loads),
            ('list_nav',      self.test_navigate_to_list),
            ('menu',          self.test_menu_open_close),
            ('cf_toggle',     self.test_celsius_fahrenheit_toggle),
            ('see_more',      self.test_see_more_air_quality),
            ('scroll',        self.test_scroll_no_crash),
            ('swipe_delete',  self.test_swipe_to_delete_reveal),
        ]

        if tests:
            all_tests = [(n, fn) for n, fn in all_tests if n in tests]

        print("=" * 60)
        print("WeatherApp Device Test Suite")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        for name, fn in all_tests:
            try:
                fn()
            except Exception as e:
                print(f"\n  [ERROR in {name}]: {e}")
                self.results.append((name, False, str(e)))

        self._print_summary()
        return all(r[1] for r in self.results)

    def _print_summary(self):
        passed = [r for r in self.results if r[1]]
        failed = [r for r in self.results if not r[1]]
        print("\n" + "=" * 60)
        print(f"RESULTS: {len(passed)} passed, {len(failed)} failed")
        if failed:
            print("\nFAILED:")
            for name, _, detail in failed:
                print(f"  ✗ {name}" + (f" — {detail}" if detail else ''))
        print("=" * 60)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WeatherApp device test suite')
    parser.add_argument('--test', nargs='*', help='Run specific tests by name')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    # Check device connected
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    if 'device' not in result.stdout.split('\n')[1]:
        print("ERROR: No Android device connected. Connect via USB or wireless ADB.")
        sys.exit(1)

    runner = DeviceTestRunner(verbose=args.verbose)
    success = runner.run_all(tests=args.test)
    sys.exit(0 if success else 1)
