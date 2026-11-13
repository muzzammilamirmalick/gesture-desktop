"""All the settings you might want to tweak live here."""

# Which gesture triggers which action. Action names are defined in actions.py.
# Set a value to None to switch a gesture off.
GESTURE_ACTIONS = {
    "point": "move_cursor",
    "pinch": "click",  # quick pinch, fires when you let go
    "pinch_hold": "close_window",  # keep pinching for PINCH_HOLD_SECONDS
    "swipe_right": "next_window",
    "swipe_left": "previous_window",
    "open_palm": "play_pause",
    "thumbs_up": "volume_up",
    "thumbs_down": "volume_down",
    "fist": None,  # neutral resting pose
}

# The keys each action presses on each operating system. The app checks which
# OS it is running on at startup and uses that section. Key names are
# pyautogui key names. "minimize" is available for any gesture you want to map.
SHORTCUTS = {
    "windows": {
        "close_window": ["ctrl", "w"],
        "next_window": ["alt", "tab"],
        "previous_window": ["shift", "alt", "tab"],
        "minimize": ["win", "down"],
        "play_pause": ["playpause"],
        "volume_up": ["volumeup"],
        "volume_down": ["volumedown"],
    },
    "mac": {
        "close_window": ["command", "w"],
        "next_window": ["command", "tab"],
        "previous_window": ["shift", "command", "tab"],
        "minimize": ["command", "m"],
        # pyautogui's media keys do nothing on Mac, so these send the real
        # media key events instead (see mac_keys.py).
        "play_pause": ["mac_play_pause"],
        "volume_up": ["mac_volume_up"],
        "volume_down": ["mac_volume_down"],
    },
}

# Gestures that re-arm the trigger after an action has fired.
RESET_GESTURES = {"fist"}

# Extra poses that re-arm one action. Going back to pointing after a click
# lets you click again without making a fist in between.
REARM_GESTURES = {"pinch": {"point"}}

# How long a pinch must be held to count as pinch and hold.
PINCH_HOLD_SECONDS = 1.0

# Webcam. 640x480 is plenty for hand tracking and keeps everything fast.
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
WINDOW_NAME = "Gesture Control"
WINDOW_WIDTH = 640
MODEL_PATH = "models/hand_landmarker.task"

# Gesture rules. Distances are measured as a fraction of hand size
# (wrist to middle finger knuckle), so they work near or far from the camera.
PINCH_RATIO = 0.25
THUMB_EXTENDED_RATIO = 0.55

# Swipe: how far (fraction of frame width) and how fast (seconds) the hand must move.
SWIPE_DISTANCE = 0.25
SWIPE_MAX_SECONDS = 0.5

# Debounce: a gesture must be seen this many frames in a row to count.
STABLE_FRAMES = 4

# Cursor: ignore this much of each frame edge so you can reach screen corners.
CURSOR_MARGIN = 0.2
# Smoothing for small moves (0 = frozen, 1 = none). Big moves get less smoothing
# so the cursor keeps up: a jump of CURSOR_FAST_PIXELS in one frame is not smoothed.
CURSOR_SMOOTHING = 0.25
CURSOR_FAST_PIXELS = 120
# The cursor follows the index knuckle, which stays still while you pinch.
# Set to True to follow the fingertip instead.
CURSOR_FOLLOWS_TIP = False
