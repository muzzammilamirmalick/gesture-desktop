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

VOICE_HELP_COUNT = 12  # how many voice phrases fit in the help panel
CUSTOM_HELP_COUNT = 3  # and how many of your gestures


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


def custom_rows(custom):
    """Your trained gestures for the help screen, or a pointer to training mode."""
    if not custom:
        return [("none yet", "press t to train one")]
    return [(name, action_words(gesture["action"])) for name, gesture in list(custom.items())[:CUSTOM_HELP_COUNT]]


def help_columns(key_rows, custom=None):
    """The help screen: gestures and the menu on the left, voice and keys on the right."""
    sections = help_sections()
    left = sections[:3]
    right = sections[3:] + [("Your gestures (t)", custom_rows(custom)), ("Keys", key_rows)]
    return [left, right]


def sign_help_columns(key_rows):
    letters = " ".join(asl_letters.SUPPORTED_LETTERS)
    return [[("Sign language", [(letters, "")] + SIGN_HELP)], [("Keys", key_rows)]]


def help_sections():
    """The help as (heading, [(name, what it does)]) pairs."""
    menu_rows = [(LABELS[item], MENU_HELP.get(item, "")) for item in config.MENU_ITEMS]
    # Two phrases a row, since most of them say what they do.
    phrases = [f'"{phrase}"' for phrase in config.VOICE_COMMANDS][:VOICE_HELP_COUNT]
    voice_rows = [(phrases[i], " ".join(phrases[i + 1:i + 2])) for i in range(0, len(phrases), 2)]
    return [
        ("Always on", ALWAYS_ON),
        ("In the menu", menu_rows),
        ("Hands", HANDS_HELP),
        ("Voice (v)", voice_rows),
    ]
