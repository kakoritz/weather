[app]
title           = WeatherBird
package.name    = weatherbird
package.domain  = org.kakoritz
version         = 1.4.04

source.dir      = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf,otf

# Kivy + KivyMD; pillow for asset generation; requests+certifi for HTTPS API calls
requirements    = python3,kivy==2.3.0,kivymd==1.2.0,pillow,requests,certifi

orientation     = portrait
fullscreen      = 0

android.minapi      = 24
android.api         = 35
# NDK 25b for Kivy. NDK 28c breaks Python 3.11's grp module (Android Bionic removed
# setgrent/getgrent/endgrent in NDK 28c; NDK 25b still has them).
# pygame projects use NDK 28c (SIMD fix); Kivy projects need NDK 25b + p4a.source_dir.
android.ndk         = 25b
android.archs       = arm64-v8a
# Pin p4a to last commit before Python 3.14 (3762c88c = Python 3.11.13).
# p4a master (2026.05.09) uses Python 3.14 which breaks Kivy 2.3.0 —
# _PyLong_AsByteArray gained a 6th arg in 3.14 that Cython 0.29 doesn't generate.
# Cloned + checked out at /home/kakoritz/.p4a-py311/ — do NOT update this clone.
p4a.source_dir      = /home/kakoritz/.p4a-py311
# Patch Python 3.11 to skip grp module (setgrent/getgrent/endgrent not in Android Bionic)
p4a.local_recipes   = ./custom_recipes
android.accept_sdk_license = True
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# NOTE: buildozer reads 'icon.filename' and 'presplash.filename' (NOT android.* prefix)
icon.filename                          = %(source.dir)s/assets/icon.png
# Adaptive icon layers (Android 8+ — gives proper circle with no white ring)
icon.adaptive_foreground.filename      = %(source.dir)s/assets/icon_fg.png
icon.adaptive_background.filename      = %(source.dir)s/assets/icon_bg.png
presplash.filename                     = %(source.dir)s/assets/presplash.jpg

# Local build dir — NOT on NAS, must be a local path with no spaces
# Thousands of small file writes; network share causes SIGBUS and extreme slowness
[buildozer]
build_dir = /home/kakoritz/.weatherapp-build
log_level = 2
