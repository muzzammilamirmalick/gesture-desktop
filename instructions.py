"""Plain words for the help panel, the intro screen and the hand label."""

import config
from menu import LABELS

ALWAYS_ON = [
    ("Point", "move the mouse"),
    ("Pinch", "click"),
    ("Open palm, hold", "open the menu"),
]

MENU_HELP = {
    "scroll": "move hand up or down",
    "volume": "move hand up or down",
    "switch_app": "flick left or right",
    "screenshot": "save the screen",
    "play_pause": "music and video",
    "close_window": "window or tab",
    "show_desktop": "hide all windows",
}

INTRO_LINES = [
    "Point to move",
    "Pinch to click",
    "Hold an open palm for the menu",
]

# The hand shapes that mean something. Anything else just shows as "hand".
HAND_NAMES = {
    "point": "point",
    "pinch": "pinch",
    "open_palm": "open palm",
    "fist": "fist",
    "no_hand": "no hand",
}

ACTION_WORDS = {
    "play_pause": "play or pause",
}


def hand_name(gesture):
    return HAND_NAMES.get(gesture, "hand")


def action_words(action):
    return ACTION_WORDS.get(action, action.replace("_", " "))


def help_sections():
    """The help panel as (heading, [(name, what it does)]) pairs."""
    menu_rows = [(LABELS[item], MENU_HELP.get(item, "")) for item in config.MENU_ITEMS]
    if config.EYE_ACTIONS.get("double_blink"):
        menu_rows.append(("Blink twice (e)", "play or pause"))
    return [
        ("Always on", ALWAYS_ON),
        ("In the menu", menu_rows),
    ]
