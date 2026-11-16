"""Plain words for the help panel, the intro screen and the hand label."""

import asl_letters
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

HANDS_HELP = [
    ("Both hands", "tracked, Left and Right"),
    ("Number by a hand", "fingers held up"),
    ("Green ring", "the hand in control"),
]

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

VOICE_HELP_COUNT = 11  # how many voice commands fit in the help panel


def hand_name(gesture):
    return HAND_NAMES.get(gesture, "hand")


def action_words(action):
    return ACTION_WORDS.get(action, action.replace("_", " "))


SIGN_HELP = [
    ("Hold a letter still", "adds it to the word"),
    ("Drop it, sign again", "types it twice"),
    ("Hand out of view", "adds a space"),
    ("Hand control", "is off in this mode"),
]


def help_columns(key_rows):
    """The help screen: gestures and the menu on the left, voice and keys on the right."""
    sections = help_sections()
    return [sections[:3], sections[3:] + [("Keys", key_rows)]]


def sign_help_columns(key_rows):
    letters = " ".join(asl_letters.SUPPORTED_LETTERS)
    return [[("Sign language", [(letters, "")] + SIGN_HELP)], [("Keys", key_rows)]]


def help_sections():
    """The help as (heading, [(name, what it does)]) pairs."""
    menu_rows = [(LABELS[item], MENU_HELP.get(item, "")) for item in config.MENU_ITEMS]
    voice_rows = [(f'"{phrase}"', action_words(action)) for phrase, action in config.VOICE_COMMANDS.items()]
    return [
        ("Always on", ALWAYS_ON),
        ("In the menu", menu_rows),
        ("Hands", HANDS_HELP),
        ("Voice (v)", voice_rows[:VOICE_HELP_COUNT]),
    ]
