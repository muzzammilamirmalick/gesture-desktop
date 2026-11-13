"""Real mouse and keyboard actions sent to the operating system."""

import math
import time

import pyautogui

import config
import gestures
import mac_keys
import shortcuts
from cursor import CursorPredictor, map_to_screen

pyautogui.FAILSAFE = True  # push the mouse into a screen corner to stop everything
pyautogui.PAUSE = 0

OS_NAME = shortcuts.detect_os()


def click():
    pyautogui.click()


def press_keys(keys):
    if keys[0] in mac_keys.MEDIA_KEYS:
        mac_keys.press_media_key(keys[0])
    elif len(keys) == 1:
        pyautogui.press(keys[0])
    else:
        pyautogui.hotkey(*keys)


def press_shortcut(action, os_name=None):
    press_keys(shortcuts.shortcut_for(action, os_name or OS_NAME))


def cursor_point(landmarks):
    if config.CURSOR_FOLLOWS_TIP:
        return landmarks[gestures.INDEX_TIP]
    return landmarks[gestures.INDEX_MCP]


class Cursor:
    """Each detection sets where the cursor should go. The main loop then moves
    it on every pass, using the predicted position, so it glides smoothly even
    when detection runs slower than the screen."""

    def __init__(self):
        self.predictor = CursorPredictor(config.CURSOR_ALPHA, config.CURSOR_BETA, config.CURSOR_MAX_AHEAD)
        self.active = False
        self.last_moved = None
        self.screen = None

    def aim(self, landmarks, now):
        if self.screen is None:
            self.screen = pyautogui.size()  # slow on some systems, so ask once
        width, height = self.screen
        target = map_to_screen(cursor_point(landmarks), width, height, config.CURSOR_MARGIN)
        self.predictor.observe(target, now)
        self.active = True

    def follow(self, now):
        if not self.active:
            return
        x, y = self.predictor.predict(now)
        # Skip tiny moves, they are just noise and cost a system call each.
        if self.last_moved and math.dist(self.last_moved, (x, y)) < 1:
            return
        pyautogui.moveTo(round(x), round(y))
        self.last_moved = (x, y)

    def stop(self):
        # Forget the old position so the cursor does not jump when pointing again.
        self.active = False
        self.predictor.reset()
        self.last_moved = None


cursor = Cursor()


def move_cursor(landmarks):
    cursor.aim(landmarks, time.monotonic())


def follow_cursor(now):
    cursor.follow(now)


def stop_cursor():
    cursor.stop()


# What one wheel notch is worth: Windows counts 120 per notch (smaller amounts
# scroll smoothly), the Mac counts lines.
SCROLL_UNITS_PER_NOTCH = {"windows": 120, "mac": 3}


class Scroller:
    """Turns a scroll speed into many small wheel events, so scrolling is smooth."""

    def __init__(self):
        self.leftover = 0.0

    def scroll(self, notches):
        units = notches * SCROLL_UNITS_PER_NOTCH[OS_NAME] + self.leftover
        whole = int(units)
        self.leftover = units - whole
        if whole:
            pyautogui.scroll(whole)

    def reset(self):
        self.leftover = 0.0


scroller = Scroller()
held_keys = []


def press_key(key):
    pyautogui.press(key)


def hold_key(key):
    """Keep a key pressed (like Alt for the app switcher) until release_held_keys()."""
    pyautogui.keyDown(key)
    held_keys.append(key)


def hold_shortcut(action, os_name=None):
    for key in shortcuts.shortcut_for(action, os_name or OS_NAME):
        hold_key(key)


def release_held_keys():
    while held_keys:
        pyautogui.keyUp(held_keys.pop())
