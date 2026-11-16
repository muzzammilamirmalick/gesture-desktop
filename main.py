"""Webcam window that turns hand gestures into mouse and keyboard actions."""

import ctypes
import platform
import time
from pathlib import Path

import cv2
import pyautogui

import actions
import active_window
import asl_letters
import config
import custom_gestures
import fingers
import gestures
import instructions
import overlay
import paths
import permissions
import profiles
import voice_commands
from camera import Camera
from controller import MENU, POINTER, SCROLL, SWITCH, VOLUME, GestureController, scroll_speed, volume_steps
from debounce import GestureStabilizer
from fps import FpsCounter
from motion import HandMotion
from pose_trigger import PoseTrigger
from speller import Speller
from tracking import LEFT, RIGHT, HandTracker
import training
from training import TrainingSession
from voice import FAILED, VoiceListener

# Created when you close the intro screen, so it only shows on the first run.
INTRO_SEEN_FILE = paths.user_file(".intro_seen")
TOAST_SECONDS = 1.2
HEARD_SECONDS = 4.0  # how long "Heard ..." stays on screen
RIPPLE_COLORS = {"click": overlay.GREEN, "pick": overlay.ACCENT, "flash": overlay.ACCENT}
NO_KEY = 255
ESC_KEY = 27
# Poses that already do something, so custom gestures never get in their way.
BUSY_POSES = {gestures.POINT, gestures.PINCH, gestures.OPEN_PALM}

KEY_ROWS = [
    ("space", "control on or off"),
    ("v", "voice on or off"),
    ("s", "sign language"),
    ("t", "train a gesture"),
    ("h", "help"),
    ("q", "quit"),
]
SIGN_KEY_ROWS = [
    ("s", "back to hand control"),
    ("space", "add a space"),
    ("backspace", "delete a letter"),
    ("c", "clear the word"),
    ("q", "quit"),
]
FOOTER_KEYS = "space: control   h: help   v: voice   t: train   s: sign   q: quit"
SIGN_FOOTER_KEYS = "s: leave   space: space   backspace: delete   c: clear"

BACKSPACE_KEYS = {8, 127}  # Windows sends 8, Mac sends 127
SIDE_COLORS = {LEFT: overlay.AMBER, RIGHT: overlay.ACCENT}


def pick_control_hand(hands, preferred):
    """The hand that moves the mouse: the preferred side if it is in view, otherwise any hand."""
    for hand in hands:
        if hand.side == preferred:
            return hand
    return hands[0] if hands else None


def hand_features(hand):
    """The numbers custom gestures are trained and matched on, or None without a hand."""
    if hand is None:
        return None
    return custom_gestures.features(hand.world or hand.points, hand.side)


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
        self.hands = []  # every hand in view, from the newest detection
        self.control_hand = None  # the one that moves the mouse
        self.motions = {side: HandMotion(config.HAND_ALPHA, config.HAND_BETA, config.HAND_MAX_AHEAD) for side in SIDE_COLORS}
        self.counters = {side: GestureStabilizer(config.STABLE_FRAMES) for side in SIDE_COLORS}
        self.finger_counts = {}  # side -> fingers held up, for the hands in view
        self.gesture = gestures.NO_HAND
        self.voice = None  # created the first time voice is turned on
        self.voice_on = False  # off by default, so it never costs anything unless you want it
        self.heard = None  # (what was heard, what it did, when), for the screen
        self.training = None  # a TrainingSession while training mode is open
        self.gestures_file = paths.user_file(config.CUSTOM_GESTURES_FILE)
        self.custom = custom_gestures.load(self.gestures_file)  # name -> action and samples
        self.classifier = custom_gestures.GestureClassifier(config.CUSTOM_NEIGHBOURS, config.CUSTOM_MATCH_DISTANCE)
        self.classifier.set_samples(self.custom)
        self.custom_name = None  # the custom gesture the control hand is making, if any
        self.trigger = PoseTrigger(config.CUSTOM_HOLD_SECONDS)
        self.profile = None  # which app profile is active, see config.PROFILES
        self.profile_checked_at = 0.0
        self.set_profile(profiles.DEFAULT)

    def set_aspect(self, width, height):
        self.controller.aspect = width / height

    # Updates

    def update(self, hands):
        """Process one new detection: a list with a Hand for each hand in view."""
        now = time.monotonic()
        self.hands = hands or []
        self.track_motion(now)
        self.count_fingers()
        self.control_hand = pick_control_hand(self.hands, config.CONTROL_HAND)
        landmarks = self.control_hand.points if self.control_hand else None
        features = hand_features(self.control_hand)
        self.custom_name = self.classifier.classify(features) if features else None
        if self.training:
            self.training.update(features, now)
            self.gesture = gestures.classify(landmarks)
        elif self.sign_mode:
            self.letter = asl_letters.classify_letter(landmarks)
            self.speller.update(self.letter, landmarks is not None, now)
            self.gesture = gestures.classify(landmarks)
        elif self.control_on:
            self.run_controller(landmarks, now)
            self.check_poses(now)
        else:
            self.gesture = gestures.classify(landmarks)

    def track_motion(self, now):
        """Each side keeps its own smoothing, so the two hands never mix."""
        seen = {hand.side: hand for hand in self.hands}
        for side, motion in self.motions.items():
            if side in seen:
                motion.observe(seen[side].points, now)
            else:
                motion.reset()

    def count_fingers(self):
        """Count each hand's fingers. A new count shows once it holds for a few detections."""
        self.finger_counts = {}
        for side, counter in self.counters.items():
            hand = next((hand for hand in self.hands if hand.side == side), None)
            if hand is None:
                self.counters[side] = GestureStabilizer(config.STABLE_FRAMES)
                continue
            count = counter.update(fingers.count_fingers(hand.world or hand.points))
            if count is not None:
                self.finger_counts[side] = count

    def run_controller(self, landmarks, now):
        try:
            self.gesture, _ = self.controller.update(landmarks, now)
        except pyautogui.FailSafeException:
            self.failsafe()
        for item in self.controller.take_feedback():
            self.show_feedback(item, now)

    def check_poses(self, now):
        """Run a custom gesture's action once it has been held for a moment."""
        if self.controller.mode != POINTER or self.gesture in BUSY_POSES:
            self.trigger.reset()
            return
        pose, action = self.pose_action()
        if self.trigger.update(pose, action is not None, now):
            self.run_action(action)

    def pose_action(self):
        """(pose name, action) for what the control hand is doing, or (None, None).

        Your own gestures come first, then the hand shapes in the app profile."""
        if self.custom_name:
            return self.custom_name, self.custom[self.custom_name]["action"]
        if self.gesture in self.pose_actions:
            return self.gesture, self.pose_actions[self.gesture]
        return None, None

    # App profiles

    def set_profile(self, name):
        if name == self.profile:
            return
        self.profile = name
        self.pose_actions = profiles.gestures_for(name, config.PROFILES)
        self.voice_actions = profiles.voice_for(name, config.PROFILES, config.VOICE_COMMANDS)
        self.trigger.reset()
        self.panels = {}  # the help screen shows this profile's gestures

    def check_active_app(self, now, read_app=active_window.active_app):
        """Twice a second, switch to the profile for the app in front."""
        if now - self.profile_checked_at < config.PROFILE_CHECK_SECONDS:
            return
        self.profile_checked_at = now
        app_name, title = read_app()
        # Our own window gets focus when you press a key. Keep the last profile then.
        if not app_name or title == config.WINDOW_NAME.lower():
            return
        self.set_profile(profiles.pick_profile(app_name, config.PROFILES))

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

    # Named actions, from voice now and from gestures later

    def run_action(self, action):
        """Run an action by name. Returns a few words on what happened, for the screen."""
        if action == "control_on":
            if self.sign_mode or self.training:
                return "ignored in this mode"
            if not self.control_on:
                self.toggle_control()
            return "control on" if self.control_on else "no input permission"
        if action == "control_off":
            if self.control_on:
                self.toggle_control()
            return "control off"
        if self.sign_mode or self.training:
            return "ignored in this mode"
        if not self.control_on:
            return "ignored, control is off"
        try:
            actions.run(action)
        except pyautogui.FailSafeException:
            self.failsafe()
            return "failsafe hit"
        words = instructions.action_words(action)
        self.show_toast(words.capitalize())
        return words

    # Voice

    def toggle_voice(self):
        if self.voice_on:
            self.voice.stop()
            self.voice_on = False
            return
        if not Path(config.VOSK_MODEL_PATH).exists():
            self.message = "Voice model missing, see README"
            return
        if self.voice is None:
            phrases = profiles.all_phrases(config.PROFILES, config.VOICE_COMMANDS)
            self.voice = VoiceListener(config.VOSK_MODEL_PATH, phrases)
        self.voice.start()
        self.voice_on = True
        self.message = ""

    def check_voice(self, now):
        """Runs on every pass of the main loop. Picks up anything the microphone heard."""
        if not self.voice_on:
            return
        if self.voice.status == FAILED:
            self.voice_on = False
            self.message = f"Voice stopped: {self.voice.error}"[:70]
            return
        for text in self.voice.take_heard():
            self.on_heard(text, now)

    def on_heard(self, text, now):
        found = voice_commands.find_command(text, self.voice_actions)
        if found is None:
            words = voice_commands.clean(text)
            known = words in profiles.all_phrases(config.PROFILES, config.VOICE_COMMANDS)
            self.heard = (words or "?", "not for this app" if known else "not a command", now)
            return
        phrase, action = found
        self.heard = (phrase, self.run_action(action), now)

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
        if self.training:
            self.draw_training(frame, fps, detection, now)
        elif self.sign_mode:
            self.draw_sign_mode(frame, fps, detection, now)
        else:
            self.draw_control_mode(frame, fps, detection, now)
        if self.message:
            overlay.draw_message(frame, self.message)
        if self.show_intro:
            overlay.draw_intro(frame)
        elif self.show_help:
            overlay.show_panel(frame, self.help_panel(frame.shape[:2]))
        return frame

    def draw_control_mode(self, frame, fps, detection, now):
        controller = self.controller
        menu_open = self.control_on and controller.mode == MENU
        if menu_open:
            overlay.draw_menu(frame, controller.menu)
        self.draw_hands(frame, now)
        pointer = self.control_pointer(now)
        if menu_open and pointer is not None:
            overlay.draw_pointer_line(frame, controller.menu, pointer)
        hold = max(controller.palm.progress(now), self.trigger.progress(now))
        if self.control_on and hold > 0 and controller.palm_center:
            overlay.draw_hold_ring(frame, controller.palm_center, hold)
        if self.control_on:
            self.draw_tool(frame, now)
        self.draw_effects(frame, now)
        self.draw_voice(frame, now)
        hand = self.custom_name or instructions.hand_name(self.gesture)
        overlay.draw_header(frame, self.mode_name(), hand, self.profile, self.control_on, fps, detection)
        toast = self.current_toast()
        if toast:
            overlay.draw_toast(frame, toast)
        overlay.draw_hint(frame, self.hint(now), FOOTER_KEYS)

    def draw_voice(self, frame, now):
        if not self.voice_on:
            return
        heard, did = None, None
        if self.heard and now - self.heard[2] < HEARD_SECONDS:
            heard, did = self.heard[0], self.heard[1]
        overlay.draw_voice(frame, self.voice.status, heard, did)

    def draw_hands(self, frame, now, with_cursor=True):
        """Both hands, each in its own color with its side written under it."""
        control_side = self.control_hand.side if self.control_hand else None
        for side, motion in self.motions.items():
            points = motion.predict(now)
            if points is None:
                continue
            color = SIDE_COLORS[side]
            cursor = actions.cursor_point(points) if with_cursor and side == control_side else None
            overlay.draw_hand(frame, points, cursor, color)
            overlay.draw_hand_tag(frame, points, side, self.finger_counts.get(side), color)

    def control_pointer(self, now):
        if self.control_hand is None:
            return None
        points = self.motions[self.control_hand.side].predict(now)
        return None if points is None else actions.cursor_point(points)

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
        self.draw_hands(frame, now, with_cursor=False)
        progress = self.speller.progress(now)
        overlay.draw_sign_header(frame, self.letter, self.control_hand is not None, progress, fps, detection)
        overlay.draw_word(frame, self.speller.word)
        overlay.draw_hint(frame, "Hold a letter still to add it to the word", SIGN_FOOTER_KEYS)

    def draw_training(self, frame, fps, detection, now):
        self.draw_hands(frame, now, with_cursor=False)
        overlay.draw_training(frame, self.training, list(self.custom), now)
        overlay.draw_speed(frame, fps, detection)
        toast = self.current_toast()
        if toast:
            overlay.draw_toast(frame, toast)

    def help_panel(self, size):
        # Each panel never changes while running, so draw it once.
        key = (self.sign_mode, self.profile, size)
        if key not in self.panels:
            if self.sign_mode:
                columns = instructions.sign_help_columns(SIGN_KEY_ROWS)
            else:
                columns = instructions.help_columns(KEY_ROWS, self.custom, self.profile, self.pose_actions)
            self.panels[key] = overlay.help_panel(size, columns)
        return self.panels[key]

    # Keys

    def handle_key(self, key):
        if key == NO_KEY:
            return
        if self.show_intro:
            self.close_intro()  # any key closes the intro, and does nothing else
        elif self.training:
            self.handle_training_key(key)
        elif key == ord("t"):
            self.open_training()
        elif key == ord("h"):
            self.show_help = not self.show_help
        elif key == ord("s"):
            self.toggle_sign_mode()
        elif key == ord("v"):
            self.toggle_voice()
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

    def typing(self):
        """True while typing a gesture name, so letters like q type instead of quitting."""
        return self.training is not None and self.training.step == training.NAME

    # Training mode

    def open_training(self):
        # Like sign mode, control is off so recording a pose never clicks anything.
        self.control_on = False
        self.controller.reset()
        self.sign_mode = False
        self.show_help = False
        self.message = ""
        self.training = TrainingSession(config.TRAINING_ACTIONS)

    def handle_training_key(self, key):
        if key == ESC_KEY:
            self.training = None
            return
        event = self.training.handle_key(key, time.monotonic())
        if event == "save":
            self.save_gesture(self.training.name, self.training.action, self.training.samples)
        elif event == "delete":
            self.delete_last_gesture()

    def save_gesture(self, name, action, samples):
        self.custom[name] = {"action": action, "samples": samples}
        self.gestures_changed()
        self.show_toast(f'Saved "{name}"')

    def delete_last_gesture(self):
        if not self.custom:
            return
        name = list(self.custom)[-1]
        del self.custom[name]
        self.gestures_changed()
        self.show_toast(f'Deleted "{name}"')

    def gestures_changed(self):
        custom_gestures.save(self.gestures_file, self.custom)
        self.classifier.set_samples(self.custom)
        self.panels = {}  # the help screen lists your gestures, so draw it again

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
        result_number, seen_hands = hands.latest()
        if result_number != seen_result:
            seen_result = result_number
            app.update(seen_hands)

        # The cursor moves on every pass, using the predicted position.
        app.tick(now)
        app.check_voice(now)
        app.check_active_app(now)

        if view is not None and now >= next_draw:
            next_draw = max(next_draw + draw_every, now)
            cv2.imshow(config.WINDOW_NAME, app.draw(view.copy(), speed_line(camera, hands)))

        key = cv2.waitKey(1) & 0xFF
        if (key == ord("q") and not app.typing()) or window_closed():
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
        if app.voice:
            app.voice.stop()
        actions.release_held_keys()  # never leave Alt or Cmd stuck down
        camera.release()
        hands.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
