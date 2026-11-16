"""Where the app keeps its files, both when run with Python and as a packaged app.

Packaged with PyInstaller, the app unpacks its bundled files (the models) into
a temporary folder named in sys._MEIPASS, and that folder is wiped on exit.
So bundled files are read from there, but anything the app writes for you,
like your saved gestures, goes into a normal folder in your user account.
"""

import os
import platform
import sys
from pathlib import Path

APP_FOLDER = Path(__file__).parent
APP_NAME = "Gesture Control"


def is_packaged():
    return getattr(sys, "frozen", False)


def resource(relative_path):
    """A file that ships with the app, like models/hand_landmarker.task."""
    base = Path(sys._MEIPASS) if is_packaged() else APP_FOLDER
    return base / relative_path


def user_folder():
    """Where the app saves your files. The project folder when run with Python."""
    if not is_packaged():
        return APP_FOLDER
    if platform.system() == "Windows":
        return Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".gesture-control"


def user_file(name):
    """A file the app writes for you, like your saved gestures."""
    folder = user_folder()
    folder.mkdir(parents=True, exist_ok=True)
    return folder / name
