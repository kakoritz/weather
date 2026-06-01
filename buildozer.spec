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
# NDK 25b — correct for Kivy (NOT 28c which is pygame-specific per ANDROID_APP_PLAYBOOK.md)
android.ndk         = 25b
android.archs       = arm64-v8a
android.accept_sdk_license = True
android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.icon.filename     = %(source.dir)s/assets/icon.png
android.presplash.filename = %(source.dir)s/assets/presplash.jpg

# Local build dir — NOT on NAS, must be a local path with no spaces
# Thousands of small file writes; network share causes SIGBUS and extreme slowness
[buildozer]
build_dir = /home/kakoritz/.weatherapp-build
log_level = 2
