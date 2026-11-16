"""Training mode: hold a pose, record it, give it a name, pick an action.

This file is only the steps and the keys. main.py feeds it hand detections and
key presses, and overlay.py draws whichever step it is on.
"""

POSE = "pose"  # waiting for you to get your pose ready and press r
COUNTDOWN = "countdown"  # a short wait so you can get your hand back in place
RECORDING = "recording"  # collecting samples of the pose
NAME = "name"  # typing a name
ACTION = "action"  # picking what the gesture does
SAVED = "saved"

ENTER_KEYS = {10, 13}
BACKSPACE_KEYS = {8, 127}
MAX_NAME_LENGTH = 16
KEEP_SAMPLES = 30  # plenty for matching, and keeps the file and the matching small


class TrainingSession:
    def __init__(self, actions, countdown_seconds=2.0, record_seconds=2.0, min_samples=15):
        self.actions = list(actions)
        self.countdown_seconds = countdown_seconds
        self.record_seconds = record_seconds
        self.min_samples = min_samples
        self.step = POSE
        self.started_at = 0.0
        self.samples = []
        self.name = ""
        self.action = None
        self.note = ""  # a line telling you what went wrong, if anything

    def update(self, hand_features, now):
        """Called on every detection. `hand_features` is None when no hand is in view."""
        if self.step == COUNTDOWN and now - self.started_at >= self.countdown_seconds:
            self.step = RECORDING
            self.started_at = now
            self.samples = []
        if self.step != RECORDING:
            return
        if hand_features is not None:
            self.samples.append(hand_features)
        if now - self.started_at >= self.record_seconds:
            self.finish_recording()

    def finish_recording(self):
        if len(self.samples) < self.min_samples:
            self.note = "Lost your hand. Keep it in view the whole time and try again."
            self.step = POSE
            return
        every = max(1, len(self.samples) // KEEP_SAMPLES)
        self.samples = self.samples[::every][:KEEP_SAMPLES]
        self.note = ""
        self.step = NAME

    def handle_key(self, key, now):
        """React to a key. Returns "save" when the gesture is ready to save,
        "delete" when you asked to delete the last saved gesture, otherwise None."""
        if self.step in (POSE, SAVED):
            if key == ord("r"):
                self.start(now)
            elif self.step == POSE and key in BACKSPACE_KEYS:
                return "delete"
        elif self.step == NAME:
            self.type_name(key)
        elif self.step == ACTION:
            return self.pick_action(key)
        return None

    def start(self, now):
        self.step = COUNTDOWN
        self.started_at = now
        self.name = ""
        self.action = None
        self.note = ""

    def type_name(self, key):
        if key in ENTER_KEYS:
            if self.name.strip():
                self.name = self.name.strip()
                self.step = ACTION
        elif key in BACKSPACE_KEYS:
            self.name = self.name[:-1]
        elif len(self.name) < MAX_NAME_LENGTH and (chr(key).isalnum() or chr(key) in " _-"):
            self.name += chr(key).lower()

    def pick_action(self, key):
        """Number keys 1 to 9 pick from the list."""
        index = key - ord("1")
        if 0 <= index < len(self.actions):
            self.action = self.actions[index]
            self.step = SAVED
            return "save"
        return None

    # For the screen

    def countdown_left(self, now):
        return max(0.0, self.countdown_seconds - (now - self.started_at))

    def recording_progress(self, now):
        return min(1.0, (now - self.started_at) / self.record_seconds)
