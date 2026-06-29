# DEPLOYMENT.md — WeatherApp

Project-specific deployment reference. For machine setup, ADB, and the full
Android toolchain, see the parent: `../ANDROID_APP_PLAYBOOK.md` and
`../ANDROID_KIVY_DEPLOY.md`.

---

## Quick Deploy (day-to-day)

```bash
cd /home/kakoritz/NAS/Data/Documents/vscode/WeatherApp

# 1. Build — MUST activate the venv first, not just invoke its buildozer by path.
#    buildozer only skips its `pip install --user ...` platform-bootstrap step when
#    $VIRTUAL_ENV is set; invoking ~/.buildozer-env/bin/buildozer directly from a shell
#    that never activated it leaves $VIRTUAL_ENV unset, and that pip call fails outright
#    with "Can not perform a '--user' install" (pip refuses --user inside any venv).
source ~/.buildozer-env/bin/activate
buildozer android debug

# 2. Install
adb install -r bin/weatherbird-*.apk

# 3. Launch
adb shell am start -n org.kakoritz.weatherbird/org.kivy.android.PythonActivity
```

One-liner (Makefile target):
```bash
make deploy   # build + install + launch
make qa       # build + install + run full device QA suite
```

---

## Build Configuration

| Item | Value |
|------|-------|
| Entry point | `main.py` |
| Package | `org.kakoritz.weatherbird` |
| Activity | `org.kivy.android.PythonActivity` |
| Version | `main.py:__version__` + `buildozer.spec:version` (must match) |
| Build dir | `/home/kakoritz/.weatherapp-build` (local disk — NOT NAS) |
| APK output | `bin/weatherbird-{version}-arm64-v8a-debug.apk` |
| Python | 3.11.13 (pinned via `p4a.source_dir`) |
| NDK | 25b (`android.ndk = 25b`) |
| p4a commit | `3762c88c` at `~/.p4a-py311` |

### Why NDK 25b (not 28c)

NDK 28c removed `getgrent`/`setgrent`/`endgrent` from Android Bionic.
Python 3.11 unconditionally builds `grpmodule.c` which calls these — the
build fails at the C compiler step. NDK 25b still has these symbols.
The custom python3 recipe in `custom_recipes/python3/` also patches
`grpmodule.c` directly with `#ifndef __ANDROID__` guards as a belt-and-
suspenders fix.

### Why Python 3.11 (not newer)

p4a master (2026+) defaults to Python 3.14. `_PyLong_AsByteArray` gained
a 6th argument in 3.12, which breaks Kivy 2.3.0's Cython 0.29-generated
C code with "too few arguments" at compile time. Pinning to p4a commit
`3762c88c` locks to Python 3.11.13.

---

## Requirements

```
python3,kivy==2.3.0,kivymd==1.2.0,pillow,requests,certifi
```

Custom recipes in `custom_recipes/`:
| Recipe | Why |
|--------|-----|
| `python3/` | Patches grpmodule.c for Android Bionic |
| `kivy/` | `--no-isolation` flag + config.pxi pre-generation |
| `pyjnius/` | Pins to 1.6.1 + `long = int` patch for Cython 3 |

---

## Custom p4a Setup (one-time, already done)

```bash
# p4a pinned to Python 3.11 era
git clone https://github.com/kivy/python-for-android.git ~/.p4a-py311
cd ~/.p4a-py311 && git checkout 3762c88c

# Patch recipe.py for --no-isolation and dist-info cleanup
python3 ci_patch_p4a.py
```

`ci_patch_p4a.py` in the project root applies two patches to
`~/.p4a-py311/pythonforandroid/recipe.py`:
1. Adds `--no-isolation` to `PyProjectRecipe.build_arch` build args
2. Deletes stale `*.dist-info` dirs before pip installs

---

## Version Bump Checklist

Before every PR to `main`:

```bash
# 1. Update version in TWO places (must match):
#    buildozer.spec  → version = X.Y.Z
#    main.py         → __version__ = 'X.Y.Z'

# 2. Update five docs:
#    RELEASE_NOTES.md  — new entry
#    README.md         — reflect current state
#    DESIGN.md         — if architecture changed
#    CLAUDE_REVIEW.md  — new review entry
#    CLAUDE.md         — if file map or constants changed

# 3. Verify CI is green on development before opening PR
```

Version convention:
| Bump | When |
|------|------|
| PATCH | Bug fix, invisible change, docs only |
| MINOR | Any user-visible addition |
| MAJOR | New major system or breaking change |

---

## CI/CD Pipeline

```
push → development    →  pytest (ci.yml)
PR   → main           →  pytest (ci.yml)
push → main           →  APK build + GitHub Release (android.yml)
```

APK is published to the `apk-latest` pre-release on every `main` push.
Download from GitHub CLI:
```bash
gh release download apk-latest --pattern "*.apk" --dir /tmp/ --repo kakoritz/weather
adb install /tmp/*.apk
```

---

## Device QA

Phone: Samsung Galaxy (USB debug enabled)

```bash
# Full suite (all 9 test groups)
python3 tests/device/device_tests.py

# Specific group
python3 tests/device/device_tests.py --test menu --verbose
python3 tests/device/device_tests.py --test weather --verbose

# Menu QA confirms position + click-through fix
# Screenshots saved to /tmp/qa_*.png
```

**Important:** QA tests check for crashes ("no crash" = pass), NOT visual
correctness. Always view screenshots from `/tmp/qa_*.png` to confirm UI
is actually correct before reporting a test as passed.

---

## Logcat Debugging

```bash
# App PID
PID=$(adb shell pidof org.kakoritz.weatherbird | tr -d '\r')

# Python output only (most useful)
adb logcat -d --pid=$PID | grep "I python" | tail -50

# Look for our Logger.info calls
adb logcat -d --pid=$PID | grep "MENU\|WEATHER\|ERROR" | tail -20

# Crash log on device
adb pull /sdcard/weatherbird_crash.log /tmp/
```

---

## Clearing Build Cache

When switching Python versions or after recipe changes:
```bash
rm -rf /home/kakoritz/.weatherapp-build/android/platform/build-arm64-v8a/dists/
rm -rf /home/kakoritz/.weatherapp-build/android/platform/build-arm64-v8a/build/bootstrap_builds/
rm -rf /home/kakoritz/.weatherapp-build/android/platform/build-arm64-v8a/build/python-installs/
```

Force presplash update:
```bash
find /home/kakoritz/.weatherapp-build -name "presplash*" -exec rm -f {} \;
```

---

## GitHub Repo

`git@github.com:kakoritz/weather.git`

```bash
# Check CI status
gh run list --repo kakoritz/weather --limit 5

# Download latest CI APK
gh release download apk-latest --pattern "*.apk" --dir /tmp/ --repo kakoritz/weather
```
