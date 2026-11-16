# PyInstaller build for Gesture Control.
#
#   pyinstaller gesture_control.spec
#
# Windows: dist/GestureControl.exe, one file you can double-click.
# Mac: dist/Gesture Control.app, a normal app you can drag into Applications.
#
# Build on the system you want the app for. PyInstaller cannot build a Mac app
# on Windows or the other way round. Download the models first (see README),
# they are packed into the app.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

HAND_MODEL = "models/hand_landmarker.task"
VOICE_MODEL = "models/vosk-model-small-en-us-0.15"

for needed in (HAND_MODEL, VOICE_MODEL):
    if not Path(needed).exists():
        sys.exit(f"{needed} is missing. Download the models first, see the README.")

# MediaPipe and Vosk load native libraries and data files at runtime, which
# PyInstaller cannot find by reading the imports, so collect them by hand.
mediapipe_datas, mediapipe_binaries, mediapipe_imports = collect_all("mediapipe")

datas = mediapipe_datas + [
    (HAND_MODEL, "models"),
    (VOICE_MODEL, VOICE_MODEL),
]
binaries = mediapipe_binaries + collect_dynamic_libs("vosk")
hidden_imports = mediapipe_imports + ["vosk", "sounddevice"]

a = Analysis(
    ["main.py"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hidden_imports,
    excludes=["pytest", "tkinter"],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    # On a Mac the app is a folder (Gesture Control.app) that looks like one file.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="GestureControl", console=False)
    folder = COLLECT(exe, a.binaries, a.datas, name="GestureControl")
    app = BUNDLE(
        folder,
        name="Gesture Control.app",
        bundle_identifier="com.muzzammilmalick.gesturecontrol",
        info_plist={
            # macOS shows these when it asks for permission.
            "NSCameraUsageDescription": "Gesture Control watches your hands to move the mouse.",
            "NSMicrophoneUsageDescription": "Gesture Control listens for voice commands, on this Mac only.",
            "NSHighResolutionCapable": True,
        },
    )
else:
    # On Windows everything goes into one .exe. No console window.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name="GestureControl",
        console=False,
        upx=False,
    )
