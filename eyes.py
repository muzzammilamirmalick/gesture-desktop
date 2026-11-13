"""Blinks and a rough gaze direction from MediaPipe FaceLandmarker scores.

The face model gives scores from 0 to 1 for things like "left eye closed" or
"right eye looking in". Blinks from these scores are reliable. Gaze is only a
rough guess, so it is shown on screen and never used to click. The face model
itself runs in the background, see FaceTracker in tracking.py.
"""

import config

DOUBLE_BLINK = "double_blink"


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
