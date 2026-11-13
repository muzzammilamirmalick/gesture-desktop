"""Eye tracking with MediaPipe FaceLandmarker: blinks, and a rough gaze direction.

The face model gives scores from 0 to 1 for things like "left eye closed" or
"right eye looking in". Blinks from these scores are reliable. Gaze is only a
rough guess, so it is shown on screen and never used to click.
"""

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

import config

DOUBLE_BLINK = "double_blink"


class FaceTracker:
    def __init__(self, model_path):
        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
        )
        self.landmarker = FaceLandmarker.create_from_options(options)

    def scores(self, frame, timestamp_ms):
        """Return a dict of face scores like {"eyeBlinkLeft": 0.8}, or None."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(image, timestamp_ms)
        if not result.face_blendshapes:
            return None
        return {shape.category_name: shape.score for shape in result.face_blendshapes[0]}

    def close(self):
        self.landmarker.close()


def eyes_closed_score(scores):
    # Both eyes have to close, so a wink does not count as a blink.
    return min(scores["eyeBlinkLeft"], scores["eyeBlinkRight"])


class BlinkDetector:
    """Spots two quick blinks in a row.

    An eye counts as closed above `closed` and open again below `opened`. The
    gap between the two stops flicker around one value from counting as blinks.
    Closing your eyes for a long time is not a blink.
    """

    def __init__(self, closed=None, opened=None, max_blink=None, double_window=None):
        self.closed = closed or config.BLINK_CLOSED
        self.opened = opened or config.BLINK_OPEN
        self.max_blink = max_blink or config.BLINK_MAX_SECONDS
        self.double_window = double_window or config.DOUBLE_BLINK_SECONDS
        self.closed_since = None
        self.last_blink = None

    def reset(self):
        self.closed_since = None
        self.last_blink = None

    def eyes_closed(self):
        return self.closed_since is not None

    def update(self, closed_score, now):
        """Feed how closed the eyes are. Returns DOUBLE_BLINK or None."""
        if self.closed_since is None:
            if closed_score >= self.closed:
                self.closed_since = now
            return None
        if closed_score > self.opened:
            return None  # still closed
        return self.eyes_opened(now)

    def eyes_opened(self, now):
        duration = now - self.closed_since
        self.closed_since = None
        if duration > self.max_blink:
            self.last_blink = None
            return None
        if self.last_blink is not None and now - self.last_blink <= self.double_window:
            self.last_blink = None
            return DOUBLE_BLINK
        self.last_blink = now
        return None


def gaze_direction(scores, threshold=None):
    """Rough gaze: "left", "right", "up" or "center", from your point of view.

    Needs scores from an unmirrored camera frame, so left means your left.
    """
    threshold = threshold or config.GAZE_THRESHOLD
    looks = {
        "left": (scores["eyeLookOutLeft"] + scores["eyeLookInRight"]) / 2,
        "right": (scores["eyeLookInLeft"] + scores["eyeLookOutRight"]) / 2,
        "up": (scores["eyeLookUpLeft"] + scores["eyeLookUpRight"]) / 2,
    }
    direction = max(looks, key=looks.get)
    if looks[direction] < threshold:
        return "center"
    return direction
