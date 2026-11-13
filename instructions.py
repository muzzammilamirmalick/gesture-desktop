"""Plain-word names for gestures and actions, used by the on-screen panel."""

import config

GESTURE_NAMES = {
    "fist": "Fist",
    "point": "Point",
    "pinch": "Pinch",
    "pinch_hold": "Pinch and hold",
    "two_fingers": "Peace sign",
    "swipe_right": "Peace swipe right",
    "swipe_left": "Peace swipe left",
    "open_palm": "Open palm",
    "thumbs_up": "Thumbs up",
    "thumbs_down": "Thumbs down",
    "unknown": "Unknown",
    "no_hand": "No hand",
    "double_blink": "Blink twice",
}

ACTION_WORDS = {
    "click": "click",
    "move_cursor": "move the mouse",
    "close_window": "close the window",
    "next_window": "next window",
    "previous_window": "previous window",
    "minimize": "minimize the window",
    "play_pause": "play or pause",
    "volume_up": "volume up",
    "volume_down": "volume down",
}

# Order the gestures appear in the panel.
GUIDE_ORDER = [
    "point", "pinch", "pinch_hold", "swipe_right", "swipe_left",
    "open_palm", "thumbs_up", "thumbs_down",
]


def gesture_name(gesture):
    return GESTURE_NAMES.get(gesture, gesture.replace("_", " ").capitalize())


def action_words(action):
    return ACTION_WORDS.get(action, action.replace("_", " "))


def gesture_guide():
    """List of (gesture name, what it does) for every mapped gesture."""
    guide = [("Fist", "rest, and get ready")]
    for gesture in GUIDE_ORDER:
        action = config.GESTURE_ACTIONS.get(gesture)
        if action:
            guide.append((gesture_name(gesture), action_words(action)))
    blink_action = config.EYE_ACTIONS.get("double_blink")
    if blink_action:
        guide.append((gesture_name("double_blink"), f"{action_words(blink_action)} (e)"))
    return guide
