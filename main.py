"""Webcam window that turns hand gestures into mouse and keyboard actions."""

import time
from pathlib import Path

import cv2
import pyautogui

import actions
import asl_letters
import config
import eyes
import gestures
import instructions
import overlay
import permissions
from camera import Camera
from controller import MENU, GestureController
from debounce import GestureStabilizer
from fps import FpsCounter
from speller import Speller
from tracking import FaceTracker, HandTracker

# Created when you close the intro screen, so it only shows on the first run.
INTRO_SEEN_FILE = Path(__file__).parent / ".intro_seen"
TOAST_SECONDS = 1.2
NO_KEY = 255

KEY_LINES = [
    "space: control on or off",
    "h: help   s: sign language",
    "e: eye tracking   q: quit",
]
SIGN_KEY_LINES = [
    "s: back to hand control",
    "space: add a space   c: clear",
    "backspace: delete   q: quit",
]
FOOTER_KEYS = "space: control   h: help   s: sign   e: eyes   q: quit"
SIGN_FOOTER_KEYS = "s: leave   space: space   backspace: delete   c: clear"

BACKSPACE_KEYS = {8, 127}  # Windows sends 8, Mac sends 127


def resize_for_window(frame):
    height, width = frame.shape[:2]
    if width == config.WINDOW_WIDTH:
        return frame
    new_height = int(height * config.WINDOW_WIDTH / width)
    return cv2.resize(frame, (config.WINDOW_WIDTH, new_height))


def window_closed():
    return cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1


class App:
    def __init__(self, can_control):
        self.can_control = can_control
        self.controller = GestureController()
        self.speller = Speller(config.SIGN_HOLD_SECONDS, config.SIGN_SPACE_SECONDS)
        self.sign_mode = False
        self.letter = None
        self.control_on = False  # always start safe
        self.show_intro = not INTRO_SEEN_FILE.exists()
        self.show_help = False
        self.message = ""
        self.toast = None
        self.toast_at = 0.0
        self.panels = {}
        self.fps = FpsCounter()
        self.eyes_on = False  # the face model adds load, so it starts off
        self.blinks = eyes.BlinkDetector()
        self.gaze = GestureStabilizer(config.GAZE_STABLE_FRAMES)
        self.eye_status = "no face"
        self.gaze_label = None
        self.landmarks = None
        self.gesture = gestures.NO_HAND

    def set_aspect(self, width, height):
        self.controller.aspect = width / height

    # Updates

    def update(self, landmarks):
        """Process one new hand detection."""
        self.landmarks = landmarks
        now = time.monotonic()
        if self.sign_mode:
            self.letter = asl_letters.classify_letter(landmarks)
            self.speller.update(self.letter, landmarks is not None, now)
            self.gesture = gestures.classify(landmarks)
        elif self.control_on:
            self.run_controller(landmarks, now)
        else:
            self.gesture = gestures.classify(landmarks)

    def run_controller(self, landmarks, now):
        try:
            self.gesture, _ = self.controller.update(landmarks, now)
        except pyautogui.FailSafeException:
            self.failsafe()
        for item in self.controller.take_feedback():
            self.show_toast(item.text)

    def tick(self, now):
        """Runs on every pass of the main loop, between detections too."""
        if not self.control_on or self.sign_mode:
            return
        try:
            actions.follow_cursor(now)
        except pyautogui.FailSafeException:
            self.failsafe()

    def failsafe(self):
        self.control_on = False
        self.controller.reset()
        self.message = "Failsafe hit, control turned off"

    def update_eyes(self, scores):
        """Process one result from the face model, or None when no face is found."""
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
            self.show_toast("Double blink seen, control is off")
            return
        try:
            actions.press_shortcut(action)
        except pyautogui.FailSafeException:
            self.failsafe()
            return
        self.show_toast(instructions.action_words(action).capitalize())

    def show_toast(self, text):
        self.toast = text
        self.toast_at = time.monotonic()

    def current_toast(self):
        if self.toast and time.monotonic() - self.toast_at < TOAST_SECONDS:
            return self.toast
        return None

    # What the HUD says

    def mode_name(self):
        if not self.control_on:
            return "Paused"
        return "Menu" if self.controller.mode == MENU else "Pointer"

    def hint(self, now):
        if not self.can_control:
            return "Allow input control first, see the terminal"
        if not self.control_on:
            return "Press space to turn control on"
        return self.controller.hint(now)

    # Drawing

    def draw(self, frame, detection=""):
        """Draw the window. `detection` is a short line like "detect 30 fps, CPU"."""
        frame = resize_for_window(frame)
        now = time.monotonic()
        fps = self.fps.tick(now)
        if self.sign_mode:
            self.draw_sign_mode(frame, fps, detection, now)
        else:
            self.draw_control_mode(frame, fps, detection, now)
        if self.eyes_on:
            overlay.draw_eye_status(frame, self.eye_status, self.gaze_label)
        if self.message:
            overlay.draw_message(frame, self.message)
        if self.show_intro:
            overlay.draw_intro(frame)
        elif self.show_help:
            frame = overlay.attach_panel(frame, self.help_panel(frame.shape[0]))
        return frame

    def draw_control_mode(self, frame, fps, detection, now):
        controller = self.controller
        menu_open = self.control_on and controller.mode == MENU
        if menu_open:
            overlay.draw_menu(frame, controller.menu)
        if self.landmarks:
            pointer = actions.cursor_point(self.landmarks)
            if menu_open:
                overlay.draw_pointer_line(frame, controller.menu, pointer)
            overlay.draw_hand(frame, self.landmarks, pointer)
        hold = controller.palm.progress(now)
        if self.control_on and hold > 0 and controller.palm_center:
            overlay.draw_hold_ring(frame, controller.palm_center, hold)
        overlay.draw_header(frame, self.mode_name(), instructions.hand_name(self.gesture), self.control_on, fps, detection)
        toast = self.current_toast()
        if toast:
            overlay.draw_toast(frame, toast)
        overlay.draw_hint(frame, self.hint(now), FOOTER_KEYS)

    def draw_sign_mode(self, frame, fps, detection, now):
        if self.landmarks:
            overlay.draw_hand(frame, self.landmarks, actions.cursor_point(self.landmarks))
        progress = self.speller.progress(now)
        overlay.draw_sign_header(frame, self.letter, self.landmarks is not None, progress, fps, detection)
        overlay.draw_word(frame, self.speller.word)
        overlay.draw_hint(frame, "Hold a letter still to add it to the word", SIGN_FOOTER_KEYS)

    def help_panel(self, height):
        # Each panel never changes while running, so draw it once.
        key = (self.sign_mode, height)
        if key not in self.panels:
            if self.sign_mode:
                self.panels[key] = overlay.sign_help_panel(height, SIGN_KEY_LINES)
            else:
                self.panels[key] = overlay.help_panel(height, KEY_LINES)
        return self.panels[key]

    # Keys

    def handle_key(self, key):
        if key == NO_KEY:
            return
        if self.show_intro:
            self.close_intro()  # any key closes the intro, and does nothing else
        elif key == ord("h"):
            self.show_help = not self.show_help
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

    def close_intro(self):
        self.show_intro = False
        INTRO_SEEN_FILE.touch()

    def toggle_eyes(self):
        self.eyes_on = not self.eyes_on
        self.blinks.reset()
        self.eye_status = "no face"
        self.gaze_label = None

    def toggle_sign_mode(self):
        self.sign_mode = not self.sign_mode
        # Hand control is always off while signing, so letters never click anything.
        self.control_on = False
        self.controller.reset()
        self.message = ""

    def toggle_control(self):
        if not self.can_control:
            self.message = "No input permission, see the terminal"
            return
        self.control_on = not self.control_on
        self.controller.reset()  # nothing fires straight away after switching on
        self.message = ""


def open_face_tracker(app):
    if not Path(config.FACE_MODEL_PATH).exists():
        app.eyes_on = False
        app.message = "Face model missing, see README"
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
            app.set_aspect(frame.shape[1], frame.shape[0])
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
