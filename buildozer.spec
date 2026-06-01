[app]
title           = Weather
package.name    = weatherapp
package.domain  = org.kakoritz
version         = 1.0.0

source.dir      = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf,otf

# Kivy + KivyMD; pillow for asset generation; requests+certifi for HTTPS API calls
requirements    = python3,kivy==2.3.0,kivymd==1.2.0,pillow,requests,certifi

orientation     = portrait
fullscreen      = 0

android.minapi      = 24
android.targetapi   = 34
# NDK 28c — p4a master (2026.05.09) recommends 28c. Already cached from retris.
# Previous assumption that 25b was Kivy-specific was incorrect for current p4a.
android.ndk         = 28c
android.archs       = arm64-v8a
# Pin p4a to last commit before Python 3.14 (3762c88c = Python 3.11.13).
# p4a master (2026.05.09) uses Python 3.14 which breaks Kivy 2.3.0 —
# _PyLong_AsByteArray gained a 6th arg in 3.14 that Cython 0.29 doesn't generate.
# Cloned + checked out at /home/kakoritz/.p4a-py311/ — do NOT update this clone.
p4a.source_dir      = /home/kakoritz/.p4a-py311
android.accept_sdk_license = True
android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.icon.filename     = %(source.dir)s/assets/icon.png
android.presplash.filename = %(source.dir)s/assets/presplash.jpg

# Local build dir — NOT on NAS, must be a local path with no spaces
# Thousands of small file writes; network share causes SIGBUS and extreme slowness
[buildozer]
build_dir = /home/kakoritz/.weatherapp-build
log_level = 2
