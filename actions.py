"""Real mouse and keyboard actions sent to the operating system."""

import pyautogui

import config
import gestures
import mac_keys
import shortcuts
from cursor import Smoother, map_to_screen

pyautogui.FAILSAFE = True  # push the mouse into a screen corner to stop everything
pyautogui.PAUSE = 0

OS_NAME = shortcuts.detect_os()
cursor_smoother = Smoother(config.CURSOR_SMOOTHING, config.CURSOR_FAST_PIXELS)


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


def move_cursor(landmarks):
    width, height = pyautogui.size()
    target = map_to_screen(cursor_point(landmarks), width, height, config.CURSOR_MARGIN)
    x, y = cursor_smoother.update(target)
    pyautogui.moveTo(x, y)


def stop_cursor():
    # Forget the old position so the cursor does not jump when pointing again.
    cursor_smoother.reset()


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
