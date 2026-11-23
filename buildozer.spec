
[app]

title = Football Pass Analyzer Pro
package.name = footballpassanalyzer
package.domain = org.footballpassanalyzer

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf

version = 1.0.0

requirements = python3,kivy==2.3.2,arabic-reshaper,python-bidi

orientation = portrait
fullscreen = 0

android.permissions =

android.api = 35
android.minapi = 24
android.ndk = 25b

android.archs = arm64-v8a

android.accept_sdk_license = True
android.allow_backup = True

p4a.bootstrap = sdl2
p4a.branch = develop

[buildozer]

warn_on_root = 0
log_level = 2
