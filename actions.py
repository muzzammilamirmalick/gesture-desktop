"""Real mouse and keyboard actions sent to the operating system."""

import pyautogui

import config
import gestures
from cursor import Smoother, map_to_screen

pyautogui.FAILSAFE = True  # push the mouse into a screen corner to stop everything
pyautogui.PAUSE = 0

cursor_smoother = Smoother(config.CURSOR_SMOOTHING)


def click():
    pyautogui.click()


def next_window():
    pyautogui.hotkey("alt", "tab")


def previous_window():
    pyautogui.hotkey("alt", "shift", "tab")


def play_pause():
    pyautogui.press("playpause")


def volume_up():
    pyautogui.press("volumeup")


def volume_down():
    pyautogui.press("volumedown")


def move_cursor(landmarks):
    width, height = pyautogui.size()
    target = map_to_screen(landmarks[gestures.INDEX_TIP], width, height, config.CURSOR_MARGIN)
    x, y = cursor_smoother.update(target)
    pyautogui.moveTo(x, y)


def stop_cursor():
    # Forget the old position so the cursor does not jump when pointing again.
    cursor_smoother.reset()


# Fire once per gesture, then wait for the reset pose.
ONE_SHOT_ACTIONS = {
    "click": click,
    "next_window": next_window,
    "previous_window": previous_window,
    "play_pause": play_pause,
    "volume_up": volume_up,
    "volume_down": volume_down,
}

# Run every frame while the gesture is held. These get the hand landmarks.
CONTINUOUS_ACTIONS = {
    "move_cursor": move_cursor,
}


def run(name, landmarks=None):
    if name in CONTINUOUS_ACTIONS:
        CONTINUOUS_ACTIONS[name](landmarks)
    else:
        ONE_SHOT_ACTIONS[name]()
