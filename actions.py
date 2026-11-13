"""Real mouse and keyboard actions sent to the operating system."""

import pyautogui

pyautogui.FAILSAFE = True  # push the mouse into a screen corner to stop everything
pyautogui.PAUSE = 0


def click():
    pyautogui.click()


ACTIONS = {
    "click": click,
}

# Actions that run every frame while the gesture is held, instead of once.
CONTINUOUS_ACTIONS = set()


def run(name):
    ACTIONS[name]()
