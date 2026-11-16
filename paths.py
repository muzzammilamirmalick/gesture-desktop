"""Where the app keeps its files."""

from pathlib import Path

APP_FOLDER = Path(__file__).parent


def user_file(name):
    """A file the app writes for you, like your saved gestures."""
    return APP_FOLDER / name
