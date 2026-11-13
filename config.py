"""All the settings you might want to tweak live here."""

# Which gesture triggers which action. Action names are defined in actions.py.
# Set a value to None to switch a gesture off.
GESTURE_ACTIONS = {
    "pinch": "click",
    "point": None,
    "swipe_right": None,
    "swipe_left": None,
    "open_palm": None,
    "thumbs_up": None,
    "thumbs_down": None,
    "fist": None,
}

# Gestures that re-arm the trigger after an action has fired.
RESET_GESTURES = {"fist"}

# Webcam
CAMERA_INDEX = 0
WINDOW_NAME = "Gesture Control"
WINDOW_WIDTH = 480
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

# Cursor: ignore this much of each frame edge so you can reach screen corners,
# and smooth movement (0 = frozen, 1 = no smoothing).
CURSOR_MARGIN = 0.15
CURSOR_SMOOTHING = 0.3
