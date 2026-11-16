"""All the settings you might want to tweak live here."""

# Outside the menu there are only two gestures:
#   point with your index finger to move the mouse
#   pinch (thumb and index together) to click
# Everything else lives in the radial menu. Hold an open palm to open it.

# The menu, clockwise from the top. Reorder or remove items here.
MENU_ITEMS = [
    "scroll",
    "volume",
    "switch_app",
    "screenshot",
    "play_pause",
    "close_window",
    "show_desktop",
]
MENU_HOLD_SECONDS = 0.5  # how long to hold an open palm to open the menu
MENU_RADIUS = 0.33  # size of the menu, as a fraction of the window height
MENU_DEAD_ZONE = 0.08  # the middle of the menu, where nothing is picked
MENU_CLOSE_SECONDS = 1.5  # the menu and tools close if your hand is gone this long

# Tools from the menu. Distances are fractions of the window height.
# Scroll: move your hand above or below where it started. Further means faster.
SCROLL_DEAD_ZONE = 0.04  # this close to the start does nothing
SCROLL_SPEED = 50  # wheel notches per second, per unit of distance
# Volume: one volume key press for every VOLUME_STEP your hand moves.
VOLUME_STEP = 0.05
# Switch app: a flick is the hand moving FLICK_DISTANCE sideways within FLICK_SECONDS.
FLICK_DISTANCE = 0.12
FLICK_SECONDS = 0.3
FLICK_COOLDOWN = 0.3  # ignore the hand coming back after a flick

# The keys each action presses on each operating system. The app checks which
# OS it is running on at startup and uses that section. Key names are
# pyautogui key names.
SHORTCUTS = {
    "windows": {
        "close_window": ["ctrl", "w"],
        "show_desktop": ["win", "d"],
        "app_switcher": ["alt"],  # held down while you flick, then Tab moves along
        "screenshot": ["win", "printscreen"],  # saved to Pictures > Screenshots
        "play_pause": ["playpause"],
        "volume_up": ["volumeup"],
        "volume_down": ["volumedown"],
    },
    "mac": {
        "close_window": ["command", "w"],
        "app_switcher": ["command"],
        # F11 is the Mac's default Show Desktop key (System Settings >
        # Desktop & Dock > Shortcuts).
        "show_desktop": ["f11"],
        "screenshot": ["command", "shift", "3"],  # saved to the Desktop
        # pyautogui's media keys do nothing on Mac, so these send the real
        # media key events instead (see mac_keys.py).
        "play_pause": ["mac_play_pause"],
        "volume_up": ["mac_volume_up"],
        "volume_down": ["mac_volume_down"],
    },
}

# Webcam. The app asks for 1280x720 at 60 fps. Many webcams only give 30 fps,
# the window shows the real number.
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 60
# The model gets a smaller copy of each frame. The window still shows full detail.
DETECTION_WIDTH = 480
# Try the GPU for detection. Falls back to the CPU if this build has no GPU support.
USE_GPU = True
WINDOW_NAME = "Gesture Control"
WINDOW_WIDTH = 960  # the camera view is scaled to this width. 1280 also works.
# The window redraws this often, even when the webcam or the model is slower.
DISPLAY_FPS = 60
MODEL_PATH = "models/hand_landmarker.task"

# Both hands are tracked. This one moves the mouse when both are in view.
# With only one hand in view, that hand is in control. "Left" or "Right".
CONTROL_HAND = "Right"

# Gesture rules. Distances are measured as a fraction of hand size
# (wrist to middle finger knuckle), so they work near or far from the camera.
PINCH_RATIO = 0.25
THUMB_EXTENDED_RATIO = 0.55

# Debounce: a gesture must be seen this many detections in a row to count.
STABLE_FRAMES = 3

# Cursor: ignore this much of each frame edge so you can reach screen corners.
CURSOR_MARGIN = 0.2
# Cursor smoothing and prediction. ALPHA is how far each detection pulls the
# cursor (lower is smoother, higher is snappier). BETA is how quickly it picks
# up speed. Between detections the cursor keeps moving for up to MAX_AHEAD seconds.
CURSOR_ALPHA = 0.6
CURSOR_BETA = 0.2
CURSOR_MAX_AHEAD = 0.08
# The same smoothing for the hand points drawn on screen.
HAND_ALPHA = 0.7
HAND_BETA = 0.2
HAND_MAX_AHEAD = 0.06
# The cursor follows the index knuckle, which stays still while you pinch.
# Set to True to follow the fingertip instead.
CURSOR_FOLLOWS_TIP = False

# Sign language mode. A finger is straight when its tip reaches at least
# ASL_STRAIGHT_RATIO times as far from the wrist as its knuckle, and curled
# below ASL_CURLED_RATIO. In between counts as bent (used for C and O).
ASL_STRAIGHT_RATIO = 1.5
ASL_CURLED_RATIO = 1.1
ASL_TOUCH_RATIO = 0.25  # fingertips this close (times hand size) are touching
ASL_SPREAD_DEGREES = 12  # index and middle this far apart is V, closer is U
SIGN_HOLD_SECONDS = 1.0  # hold a letter this long to add it to the word
SIGN_SPACE_SECONDS = 1.5  # take your hand away this long to add a space

