"""Webcam window that turns hand gestures into mouse and keyboard actions."""

import time
from pathlib import Path

import cv2
import pyautogui

import actions
import asl_letters
import config
import eyes
from camera import Camera
from fps import FpsCounter
import gestures
import instructions
import overlay
import permissions
from debounce import GestureStabilizer, TriggerGate
from speller import Speller
from tracking import FaceTracker, HandTracker

# Created the first time you hide the help panel, so it only opens by itself once.
HELP_SEEN_FILE = Path(__file__).parent / ".help_seen"
FIRED_SHOW_SECONDS = 1.5

KEYS = [
    ("space", "control on or off"),
    ("s", "sign language mode"),
    ("e", "eye tracking on or off"),
    ("h", "show or hide this help"),
    ("q", "quit"),
]

SIGN_KEYS = [
    ("s", "back to hand control"),
    ("space", "add a space"),
    ("backspace", "delete a letter"),
    ("c", "clear the word"),
    ("e", "eye tracking on or off"),
    ("h", "show or hide this help"),
    ("q", "quit"),
]

BACKSPACE_KEYS = {8, 127}  # Windows sends 8, Mac sends 127


def one_shot_gestures():
    """Gestures whose action should fire once per reset."""
    return {
        gesture
        for gesture, action in config.GESTURE_ACTIONS.items()
        if action and action not in actions.CONTINUOUS_ACTIONS
    }


def resize_for_window(frame):
    height, width = frame.shape[:2]
    if width == config.WINDOW_WIDTH:
        return frame
    new_height = int(height * config.WINDOW_WIDTH / width)
    return cv2.resize(frame, (config.WINDOW_WIDTH, new_height))


def window_closed():
    return cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1


class GestureController:
    """Decides what to do each frame based on the current gesture."""

    def __init__(self):
        self.stabilizer = GestureStabilizer(config.STABLE_FRAMES)
        self.gate = TriggerGate(one_shot_gestures(), config.RESET_GESTURES, config.REARM_GESTURES)
        self.swipes = gestures.SwipeDetector()
        self.pinches = gestures.PinchTracker()

    def read_gesture(self, landmarks):
        """Return (raw gesture, stable gesture, event).

        The event is what the trigger gate sees: a swipe, a finished pinch, a
        held pinch, or just the stable gesture.
        """
        raw = gestures.classify(landmarks)
        stable = self.stabilizer.update(raw) or gestures.NO_HAND
        now = time.monotonic()

        swipe = self.read_swipe(raw, landmarks, now)
        pinch = self.pinches.update(stable, now)
        if swipe:
            return raw, stable, swipe
        if pinch:
            return raw, stable, pinch
        if stable == gestures.PINCH:
            return raw, stable, None  # still deciding between click and hold
        return raw, stable, stable

    def read_swipe(self, raw, landmarks, now):
        # Swipes use the raw pose so a fast move is not lost to smoothing.
        if raw != gestures.TWO_FINGERS:
            self.swipes.reset()
            return None
        return self.swipes.update(gestures.two_finger_x(landmarks), now)

    def act(self, raw, stable, event, landmarks):
        """Run actions for this frame. Returns the one-shot action that fired, if any."""
        fired = None
        if self.gate.update(event):
            fired = config.GESTURE_ACTIONS[event]
            actions.run(fired)

        # Only move while both the raw and stable pose agree, so the cursor
        # freezes as soon as the fingers start closing for a pinch.
        action = config.GESTURE_ACTIONS.get(stable)
        if action in actions.CONTINUOUS_ACTIONS and raw == stable and landmarks:
            actions.run(action, landmarks)
        else:
            actions.stop_cursor()
        return fired


class App:
    def __init__(self, can_control):
        self.can_control = can_control
        self.controller = GestureController()
        self.speller = Speller(config.SIGN_HOLD_SECONDS, config.SIGN_SPACE_SECONDS)
        self.sign_mode = False
        self.letter = None
        self.control_on = False  # always start safe
        self.show_help = not HELP_SEEN_FILE.exists()
        self.message = ""
        self.fired = None
        self.fired_at = 0.0
        self.panels = {}
        self.fps = FpsCounter()
        self.eyes_on = False  # the face model adds load, so it starts off
        self.blinks = eyes.BlinkDetector()
        self.gaze = GestureStabilizer(config.GAZE_STABLE_FRAMES)
        self.eye_status = "no face"
        self.gaze_label = None
        self.landmarks = None
        self.gesture = gestures.NO_HAND

    def update(self, landmarks):
        """Process one new hand detection. Returns the gesture name to show."""
        self.landmarks = landmarks
        if self.sign_mode:
            self.letter = asl_letters.classify_letter(landmarks)
            self.speller.update(self.letter, landmarks is not None, time.monotonic())
            self.gesture = gestures.classify(landmarks)
            return self.gesture

        raw, stable, event = self.controller.read_gesture(landmarks)
        if self.control_on:
            self.run_actions(raw, stable, event, landmarks)
        self.gesture = raw
        return raw

    def tick(self, now):
        """Runs on every pass of the main loop, between detections too."""
        if not self.control_on or self.sign_mode:
            return
        try:
            actions.follow_cursor(now)
        except pyautogui.FailSafeException:
            self.control_on = False
            self.message = "failsafe hit, control turned off"

    def run_actions(self, raw, stable, event, landmarks):
        try:
            fired = self.controller.act(raw, stable, event, landmarks)
        except pyautogui.FailSafeException:
            self.control_on = False
            self.message = "failsafe hit, control turned off"
            return
        if fired:
            self.show_fired(instructions.action_words(fired))

    def update_eyes(self, scores):
        """Process one frame of face scores, or None when no face is found."""
        if scores is None:
            self.blinks.reset()
            self.eye_status = "no face"
            self.gaze_label = None
            return
        event = self.blinks.update(eyes.eyes_closed_score(scores), time.monotonic())
        self.eye_status = "closed" if self.blinks.eyes_closed() else "open"
        self.gaze_label = self.gaze.update(eyes.gaze_direction(scores))
        if event == eyes.DOUBLE_BLINK:
            self.on_double_blink()

    def on_double_blink(self):
        action = config.EYE_ACTIONS.get(eyes.DOUBLE_BLINK)
        if not action:
            return
        if not self.control_on:
            self.show_fired("double blink seen, control is off")
            return
        try:
            actions.run(action)
        except pyautogui.FailSafeException:
            self.control_on = False
            self.message = "failsafe hit, control turned off"
            return
        self.show_fired(f"{instructions.action_words(action)} (double blink)")

    def show_fired(self, text):
        self.fired = text
        self.fired_at = time.monotonic()

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
        if self.sign_mode:
            lines.append(("s: leave   space: space   backspace: delete   c: clear", overlay.GREY))
        else:
            lines.append(("h: help   space: control   s: sign mode   e: eyes   q: quit", overlay.GREY))
        return lines

    def draw(self, frame, detection=""):
        """Draw the window. `detection` is a short line like "detect 30 fps, CPU"."""
        frame = resize_for_window(frame)
        landmarks = self.landmarks
        if landmarks:
            overlay.draw_hand(frame, landmarks, actions.cursor_point(landmarks))
        fps = self.fps.tick(time.monotonic())
        if self.sign_mode:
            progress = self.speller.progress(time.monotonic())
            overlay.draw_sign_header(frame, self.letter, landmarks is not None, progress, fps, detection)
            overlay.draw_word(frame, self.speller.word)
        else:
            overlay.draw_header(frame, self.gesture, self.control_on, self.recent_action(), fps, detection)
        if self.eyes_on:
            overlay.draw_eye_status(frame, self.eye_status, self.gaze_label)
        overlay.draw_footer(frame, self.footer_lines())
        if self.show_help:
            frame = overlay.attach_panel(frame, self.help_panel(frame.shape[0]))
        return frame

    def help_panel(self, height):
        # Each panel never changes while running, so draw it once.
        key = (self.sign_mode, height)
        if key not in self.panels:
            if self.sign_mode:
                self.panels[key] = overlay.sign_help_panel(height, SIGN_KEYS)
            else:
                self.panels[key] = overlay.help_panel(height, KEYS)
        return self.panels[key]

    def handle_key(self, key):
        if key == ord("h"):
            self.toggle_help()
        elif key == ord("s"):
            self.toggle_sign_mode()
        elif key == ord("e"):
            self.toggle_eyes()
        elif self.sign_mode:
            self.handle_sign_key(key)
        elif key == ord(" "):
            self.toggle_control()

    def handle_sign_key(self, key):
        if key in BACKSPACE_KEYS:
            self.speller.backspace()
        elif key == ord("c"):
            self.speller.clear()
        elif key == ord(" "):
            self.speller.add(" ")

    def toggle_help(self):
        self.show_help = not self.show_help
        if not self.show_help:
            HELP_SEEN_FILE.touch()

    def toggle_eyes(self):
        self.eyes_on = not self.eyes_on
        self.blinks.reset()
        self.eye_status = "no face"
        self.gaze_label = None

    def toggle_sign_mode(self):
        self.sign_mode = not self.sign_mode
        # Hand control is always off while signing, so letters never click anything.
        self.control_on = False
        self.controller.gate.disarm()
        actions.stop_cursor()
        self.message = ""

    def toggle_control(self):
        if not self.can_control:
            self.message = "no input permission, see terminal"
            return
        self.control_on = not self.control_on
        self.controller.gate.disarm()  # never fire straight away after switching on
        actions.stop_cursor()
        self.message = ""


def open_face_tracker(app):
    if not Path(config.FACE_MODEL_PATH).exists():
        app.eyes_on = False
        app.message = "face model missing, see README"
        return None
    return FaceTracker(config.FACE_MODEL_PATH, config.DETECTION_WIDTH, config.USE_GPU)


def detection_line(hands):
    return f"detect {hands.detect_fps:.0f} fps, {hands.delegate_name}"


def run(camera, hands, app):
    """The main loop. It never waits for the models, so video and cursor stay smooth."""
    face = None  # loaded the first time eye tracking is turned on
    shown_frame = 0
    seen_hand = 0
    seen_face = 0

    while True:
        now = time.monotonic()
        frame_number, camera_frame = camera.latest()
        if camera.stopped():
            print("The webcam stopped sending frames.")
            break

        new_frame = frame_number != shown_frame
        if new_frame:
            shown_frame = frame_number
            frame = cv2.flip(camera_frame, 1)  # mirror view so moving right looks like right
            hands.submit(frame, now)
            if app.eyes_on:
                face = face or open_face_tracker(app)
                if face:
                    # The face model gets the unmirrored frame so "left" means your left.
                    face.submit(camera_frame, now)

        # Gesture logic runs once per new detection, not once per loop.
        result_number, landmarks = hands.latest()
        if result_number != seen_hand:
            seen_hand = result_number
            app.update(landmarks)

        if face and app.eyes_on:
            result_number, scores = face.latest()
            if result_number != seen_face:
                seen_face = result_number
                app.update_eyes(scores)

        # The cursor moves on every pass, using the predicted position.
        app.tick(now)

        if new_frame:
            cv2.imshow(config.WINDOW_NAME, app.draw(frame, detection_line(hands)))

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or window_closed():
            break
        app.handle_key(key)

    if face:
        face.close()


def main():
    camera = Camera(config.CAMERA_INDEX, config.CAMERA_WIDTH, config.CAMERA_HEIGHT)
    if not camera.is_open():
        print("Could not open the webcam. Check CAMERA_INDEX in config.py.")
        print(permissions.camera_help())
        return

    can_control = permissions.can_control_input()
    if not can_control:
        print(permissions.MAC_PERMISSION_HELP)

    hands = HandTracker(config.MODEL_PATH, config.DETECTION_WIDTH, config.USE_GPU)
    print(f"Hand detection is running on the {hands.delegate_name}.")
    app = App(can_control)

    cv2.namedWindow(config.WINDOW_NAME)
    cv2.setWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
    camera.start()
    try:
        run(camera, hands, app)
    finally:
        camera.release()
        hands.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
