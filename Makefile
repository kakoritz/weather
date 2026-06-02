## WeatherApp build + QA shortcuts

build:
	~/.buildozer-env/bin/buildozer android debug

install: build
	adb install -r bin/*.apk

deploy: install
	adb shell am start -n org.kakoritz.weatherapp/org.kivy.android.PythonActivity

# Run unit tests (no device needed)
test:
	python3 -m pytest tests/ -q --ignore=tests/device

# Run device QA suite (phone must be connected)
qa: install
	python3 tests/device/device_tests.py

# Run specific device test
qa-test:
	python3 tests/device/device_tests.py --test $(TEST) --verbose

# Quick deploy + full QA
ship: deploy
	@sleep 5
	python3 tests/device/device_tests.py

.PHONY: build install deploy test qa qa-test ship
