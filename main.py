"""Webcam window that turns hand gestures into mouse and keyboard actions."""

import time
from pathlib import Path

import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

import actions
import config
import gestures
import instructions
import overlay
import permissions
from debounce import GestureStabilizer, TriggerGate

# Created the first time you hide the help panel, so it only opens by itself once.
HELP_SEEN_FILE = Path(__file__).parent / ".help_seen"
FIRED_SHOW_SECONDS = 1.5

KEYS = [
    ("space", "control on or off"),
    ("h", "show or hide this help"),
    ("q", "quit"),
]


def create_landmarker():
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=config.MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=1,
    )
    return HandLandmarker.create_from_options(options)


def find_hand(landmarker, frame, timestamp_ms):
    """Return the first hand's landmarks as (x, y) pairs, or None."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect_for_video(image, timestamp_ms)
    if not result.hand_landmarks:
        return None
    return [(point.x, point.y) for point in result.hand_landmarks[0]]


def one_shot_gestures():
    """Gestures whose action should fire once per reset."""
    return {
        gesture
        for gesture, action in config.GESTURE_ACTIONS.items()
        if action and action not in actions.CONTINUOUS_ACTIONS
    }


def resize_for_window(frame):
    height, width = frame.shape[:2]
    new_height = int(height * config.WINDOW_WIDTH / width)
    return cv2.resize(frame, (config.WINDOW_WIDTH, new_height))


def window_closed():
    return cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1


class GestureController:
    """Decides what to do each frame based on the current gesture."""

    def __init__(self):
        self.stabilizer = GestureStabilizer(config.STABLE_FRAMES)
        self.gate = TriggerGate(one_shot_gestures(), config.RESET_GESTURES)
        self.swipes = gestures.SwipeDetector()

    def read_gesture(self, landmarks):
        """Return (raw gesture, stable gesture, event). The event can be a swipe."""
        raw = gestures.classify(landmarks)
        stable = self.stabilizer.update(raw) or gestures.NO_HAND

        # Swipes are tracked on the raw pose so a fast move is not lost to smoothing.
        if raw == gestures.TWO_FINGERS:
            swipe = self.swipes.update(gestures.two_finger_x(landmarks), time.monotonic())
            if swipe:
                return raw, stable, swipe
        else:
            self.swipes.reset()
        return raw, stable, stable

    def act(self, gesture, event, landmarks):
        """Run actions for this frame. Returns the one-shot action that fired, if any."""
        action = config.GESTURE_ACTIONS.get(gesture)
        if action in actions.CONTINUOUS_ACTIONS and landmarks:
            actions.run(action, landmarks)
        else:
            actions.stop_cursor()

        if self.gate.update(event):
            action = config.GESTURE_ACTIONS[event]
            actions.run(action)
            return action
        return None


class App:
    def __init__(self, can_control):
        self.can_control = can_control
        self.controller = GestureController()
        self.control_on = False  # always start safe
        self.show_help = not HELP_SEEN_FILE.exists()
        self.message = ""
        self.fired = None
        self.fired_at = 0.0
        self.panel = None

    def update(self, landmarks):
        raw, stable, event = self.controller.read_gesture(landmarks)
        if self.control_on:
            try:
                fired = self.controller.act(stable, event, landmarks)
            except pyautogui.FailSafeException:
                self.control_on = False
                self.message = "failsafe hit, control turned off"
                fired = None
            if fired:
                self.fired = instructions.action_words(fired)
                self.fired_at = time.monotonic()
        return raw

    def recent_action(self):
        if time.monotonic() - self.fired_at < FIRED_SHOW_SECONDS:
            return self.fired
        return None

    def footer_lines(self):
        lines = []
        if self.control_on and not self.controller.gate.armed:
            lines.append(("make a fist to get ready", overlay.AMBER))
        if self.message:
            lines.append((self.message, overlay.RED))
        lines.append(("h: help   space: control   q: quit", overlay.GREY))
        return lines

    def draw(self, frame, landmarks, gesture):
        frame = resize_for_window(frame)
        if landmarks:
            overlay.draw_hand(frame, landmarks)
        overlay.draw_header(frame, gesture, self.control_on, self.recent_action())
        overlay.draw_footer(frame, self.footer_lines())
        if self.show_help:
            frame = overlay.attach_panel(frame, self.help_panel(frame.shape[0]))
        return frame

    def help_panel(self, height):
        # The panel never changes while running, so draw it once.
        if self.panel is None or self.panel.shape[0] != height:
            self.panel = overlay.help_panel(height, KEYS)
        return self.panel

    def handle_key(self, key):
        if key == ord("h"):
            self.toggle_help()
        elif key == ord(" "):
            self.toggle_control()

    def toggle_help(self):
        self.show_help = not self.show_help
        if not self.show_help:
            HELP_SEEN_FILE.touch()

    def toggle_control(self):
        if not self.can_control:
            self.message = "no input permission, see terminal"
            return
        self.control_on = not self.control_on
        self.controller.gate.disarm()  # never fire straight away after switching on
        actions.stop_cursor()
        self.message = ""


def main():
    camera = cv2.VideoCapture(config.CAMERA_INDEX)
    if not camera.isOpened():
        print("Could not open the webcam. Check CAMERA_INDEX in config.py.")
        print(permissions.camera_help())
        return

    can_control = permissions.can_control_input()
    if not can_control:
        print(permissions.MAC_PERMISSION_HELP)

    landmarker = create_landmarker()
    app = App(can_control)

    cv2.namedWindow(config.WINDOW_NAME)
    cv2.setWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
    start = time.monotonic()

    while True:
        ok, frame = camera.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)  # mirror view so moving right looks like right

        timestamp_ms = int((time.monotonic() - start) * 1000)
        landmarks = find_hand(landmarker, frame, timestamp_ms)
        gesture = app.update(landmarks)
        cv2.imshow(config.WINDOW_NAME, app.draw(frame, landmarks, gesture))

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or window_closed():
            break
        app.handle_key(key)

    camera.release()
    landmarker.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
