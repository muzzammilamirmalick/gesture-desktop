"""Webcam window that turns hand gestures into mouse and keyboard actions."""

import time

import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

import actions
import config
import gestures
import overlay
import permissions
from debounce import GestureStabilizer, TriggerGate


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


def status_lines(control_on, armed, last_action, message):
    if not control_on:
        lines = [("CONTROL OFF", overlay.RED)]
    else:
        lines = [("CONTROL ON", overlay.GREEN)]
        lines.append(("ready", overlay.GREEN) if armed else ("make a fist to arm", overlay.GREY))
        if last_action:
            lines.append((f"last: {last_action}", overlay.WHITE))
    if message:
        lines.append((message, overlay.RED))
    return lines


def window_closed():
    return cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1


class GestureController:
    """Decides what to do each frame based on the current gesture."""

    def __init__(self):
        self.stabilizer = GestureStabilizer(config.STABLE_FRAMES)
        self.gate = TriggerGate(one_shot_gestures(), config.RESET_GESTURES)
        self.swipes = gestures.SwipeDetector()
        self.last_action = None

    def read_gesture(self, landmarks):
        """Return (stable gesture, event). The event can be a swipe."""
        raw = gestures.classify(landmarks)
        gesture = self.stabilizer.update(raw) or gestures.NO_HAND

        # Swipes are tracked on the raw pose so a fast move is not lost to smoothing.
        if raw == gestures.TWO_FINGERS:
            swipe = self.swipes.update(gestures.two_finger_x(landmarks), time.monotonic())
            if swipe:
                return gesture, swipe
        else:
            self.swipes.reset()
        return gesture, gesture

    def act(self, gesture, event, landmarks):
        action = config.GESTURE_ACTIONS.get(gesture)
        if action in actions.CONTINUOUS_ACTIONS and landmarks:
            actions.run(action, landmarks)
        else:
            actions.stop_cursor()

        if self.gate.update(event):
            action = config.GESTURE_ACTIONS[event]
            actions.run(action)
            self.last_action = action


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
    controller = GestureController()

    cv2.namedWindow(config.WINDOW_NAME)
    cv2.setWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
    start = time.monotonic()
    control_on = False  # always start safe
    message = ""

    while True:
        ok, frame = camera.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)  # mirror view so moving right looks like right

        timestamp_ms = int((time.monotonic() - start) * 1000)
        landmarks = find_hand(landmarker, frame, timestamp_ms)
        gesture, event = controller.read_gesture(landmarks)

        if control_on:
            try:
                controller.act(gesture, event, landmarks)
            except pyautogui.FailSafeException:
                control_on = False
                message = "failsafe hit, control turned off"

        frame = resize_for_window(frame)
        if landmarks:
            overlay.draw_hand(frame, landmarks)
        lines = status_lines(control_on, controller.gate.armed, controller.last_action, message)
        overlay.draw_status(frame, event, lines)
        overlay.draw_help(frame, "space: control on/off   q: quit")
        cv2.imshow(config.WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or window_closed():
            break
        if key == ord(" ") and not can_control:
            message = "no input permission, see terminal"
        elif key == ord(" "):
            control_on = not control_on
            controller.gate.disarm()  # never fire straight away after switching on
            actions.stop_cursor()
            message = ""

    camera.release()
    landmarker.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
