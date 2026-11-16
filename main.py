"""Webcam window that turns hand gestures into mouse and keyboard actions."""

import ctypes
import platform
import time
from pathlib import Path

import cv2
import pyautogui

import actions
import asl_letters
import config
import gestures
import instructions
import overlay
import permissions
from camera import Camera
from controller import MENU, SCROLL, SWITCH, VOLUME, GestureController, scroll_speed, volume_steps
from fps import FpsCounter
from motion import HandMotion
from speller import Speller
from tracking import HandTracker

# Created when you close the intro screen, so it only shows on the first run.
INTRO_SEEN_FILE = Path(__file__).parent / ".intro_seen"
TOAST_SECONDS = 1.2
RIPPLE_COLORS = {"click": overlay.GREEN, "pick": overlay.ACCENT, "flash": overlay.ACCENT}
NO_KEY = 255

KEY_LINES = [
    "space: control on or off",
    "h: help   s: sign language",
    "q: quit",
]
SIGN_KEY_LINES = [
    "s: back to hand control",
    "space: add a space   c: clear",
    "backspace: delete   q: quit",
]
FOOTER_KEYS = "space: control   h: help   s: sign   q: quit"
SIGN_FOOTER_KEYS = "s: leave   space: space   backspace: delete   c: clear"

BACKSPACE_KEYS = {8, 127}  # Windows sends 8, Mac sends 127


def resize_for_window(frame):
    height, width = frame.shape[:2]
    if width == config.WINDOW_WIDTH:
        return frame
    new_height = int(height * config.WINDOW_WIDTH / width)
    return cv2.resize(frame, (config.WINDOW_WIDTH, new_height))


def precise_timer(on):
    """Windows sleeps in 15 ms steps by default, so waitKey(1) really waits 15 ms
    and the window cannot hold 60 fps. Ask for 1 ms steps while the app runs."""
    if platform.system() == "Windows":
        winmm = ctypes.windll.winmm
        (winmm.timeBeginPeriod if on else winmm.timeEndPeriod)(1)


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
        self.ripples = []
        self.flash_at = None
        self.panels = {}
        self.fps = FpsCounter()
        self.landmarks = None
        self.motion = HandMotion(config.HAND_ALPHA, config.HAND_BETA, config.HAND_MAX_AHEAD)
        self.gesture = gestures.NO_HAND

    def set_aspect(self, width, height):
        self.controller.aspect = width / height

    # Updates

    def update(self, landmarks):
        """Process one new hand detection."""
        self.landmarks = landmarks
        now = time.monotonic()
        if landmarks is None:
            self.motion.reset()
        else:
            self.motion.observe(landmarks, now)
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
            self.show_feedback(item, now)

    def show_feedback(self, item, now):
        """A label for everything, a ripple where it happened, a flash for screenshots."""
        if item.kind != "click":
            self.show_toast(item.text)
        if item.position and item.kind in RIPPLE_COLORS:
            self.ripples.append((item.position, now, RIPPLE_COLORS[item.kind]))
        if item.kind == "flash":
            self.flash_at = now

    def tick(self, now):
        """Runs on every pass of the main loop, between detections too."""
        if not self.control_on or self.sign_mode:
            return
        try:
            actions.follow_cursor(now)
            self.controller.tick(now)
        except pyautogui.FailSafeException:
            self.failsafe()

    def failsafe(self):
        self.control_on = False
        self.controller.reset()
        self.message = "Failsafe hit, control turned off"

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
        return self.controller.mode_name()

    def hint(self, now):
        if not self.can_control:
            return "Allow input control first, see the terminal"
        if not self.control_on:
            return "Press space to turn control on"
        return self.controller.hint(now)

    # Drawing

    def draw(self, frame, detection=""):
        """Draw the window. `detection` is a short line like "camera 30  detect 28 (CPU)"."""
        frame = resize_for_window(frame)
        now = time.monotonic()
        fps = self.fps.tick(now)
        if self.sign_mode:
            self.draw_sign_mode(frame, fps, detection, now)
        else:
            self.draw_control_mode(frame, fps, detection, now)
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
        points = self.motion.predict(now)
        if points is not None:
            pointer = actions.cursor_point(points)
            if menu_open:
                overlay.draw_pointer_line(frame, controller.menu, pointer)
            overlay.draw_hand(frame, points, pointer)
        hold = controller.palm.progress(now)
        if self.control_on and hold > 0 and controller.palm_center:
            overlay.draw_hold_ring(frame, controller.palm_center, hold)
        if self.control_on:
            self.draw_tool(frame, now)
        self.draw_effects(frame, now)
        overlay.draw_header(frame, self.mode_name(), instructions.hand_name(self.gesture), self.control_on, fps, detection)
        toast = self.current_toast()
        if toast:
            overlay.draw_toast(frame, toast)
        overlay.draw_hint(frame, self.hint(now), FOOTER_KEYS)

    def draw_tool(self, frame, now):
        controller = self.controller
        offset = controller.hand_offset()
        if controller.mode in (SCROLL, VOLUME) and not controller.tool_ready:
            overlay.draw_start_target(frame, controller.anchor)
        elif controller.mode == SCROLL:
            overlay.draw_scroll_tool(frame, controller.anchor, controller.palm_center, scroll_speed(offset), config.SCROLL_DEAD_ZONE)
        elif controller.mode == VOLUME:
            overlay.draw_volume_tool(frame, controller.anchor, controller.palm_center, volume_steps(offset), config.VOLUME_STEP)
        elif controller.mode == SWITCH:
            overlay.draw_switch_tool(frame, controller.last_flick, now)

    def draw_effects(self, frame, now):
        self.ripples = [r for r in self.ripples if now - r[1] < overlay.RIPPLE_SECONDS]
        overlay.draw_ripples(frame, self.ripples, now)
        if self.flash_at is not None:
            overlay.draw_flash(frame, self.flash_at, now)

    def draw_sign_mode(self, frame, fps, detection, now):
        points = self.motion.predict(now)
        if points is not None:
            overlay.draw_hand(frame, points)
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


def speed_line(camera, hands):
    return f"camera {camera.fps:.0f}   detect {hands.detect_fps:.0f} ({hands.delegate_name})"


def run(camera, hands, app):
    """The main loop. It never waits for the model, so video and cursor stay smooth.

    Three things run at their own speed: the webcam, the hand model, and the
    window. The window redraws at DISPLAY_FPS using predicted hand points, so it
    stays smooth even when the webcam or the model is slower than that.
    """
    shown_frame = 0
    seen_result = 0
    view = None  # the newest camera frame, mirrored and sized for the window
    draw_every = 1 / config.DISPLAY_FPS
    next_draw = 0.0

    while True:
        now = time.monotonic()
        frame_number, camera_frame = camera.latest()
        if camera.stopped():
            print("The webcam stopped sending frames.")
            break

        if frame_number != shown_frame:
            shown_frame = frame_number
            mirrored = cv2.flip(camera_frame, 1)  # mirror view so moving right looks like right
            app.set_aspect(mirrored.shape[1], mirrored.shape[0])
            hands.submit(mirrored, now)
            view = resize_for_window(mirrored)

        # Gesture logic runs once per new detection, not once per loop.
        result_number, landmarks = hands.latest()
        if result_number != seen_result:
            seen_result = result_number
            app.update(landmarks)

        # The cursor moves on every pass, using the predicted position.
        app.tick(now)

        if view is not None and now >= next_draw:
            next_draw = max(next_draw + draw_every, now)
            cv2.imshow(config.WINDOW_NAME, app.draw(view.copy(), speed_line(camera, hands)))

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or window_closed():
            break
        app.handle_key(key)


def main():
    camera = Camera(config.CAMERA_INDEX, config.CAMERA_WIDTH, config.CAMERA_HEIGHT, config.CAMERA_FPS)
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
    precise_timer(True)
    try:
        run(camera, hands, app)
    finally:
        precise_timer(False)
        actions.release_held_keys()  # never leave Alt or Cmd stuck down
        camera.release()
        hands.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
