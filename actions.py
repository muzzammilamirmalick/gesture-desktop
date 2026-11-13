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


# Fire once per gesture, then wait for the reset pose.
# Keyboard shortcuts (next_window, play_pause and so on) are set per OS in config.py.
ONE_SHOT_ACTIONS = {
    "click": click,
}

# Run every frame while the gesture is held. These get the hand landmarks.
CONTINUOUS_ACTIONS = {
    "move_cursor": move_cursor,
}


def all_action_names():
    return set(ONE_SHOT_ACTIONS) | set(CONTINUOUS_ACTIONS) | shortcuts.shortcut_actions()


def run(name, landmarks=None):
    if name in CONTINUOUS_ACTIONS:
        CONTINUOUS_ACTIONS[name](landmarks)
    elif name in ONE_SHOT_ACTIONS:
        ONE_SHOT_ACTIONS[name]()
    else:
        press_shortcut(name)
