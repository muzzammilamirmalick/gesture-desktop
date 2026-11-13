"""Rules that turn 21 MediaPipe hand landmarks into a gesture name.

Landmarks are (x, y) pairs in normalized image coordinates, so y grows downward.
"""

import math
from collections import deque

import config

WRIST = 0
THUMB_MCP, THUMB_IP, THUMB_TIP = 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_PIP, RING_TIP = 14, 16
PINKY_PIP, PINKY_TIP = 18, 20

FINGER_JOINTS = {
    "index": (INDEX_PIP, INDEX_TIP),
    "middle": (MIDDLE_PIP, MIDDLE_TIP),
    "ring": (RING_PIP, RING_TIP),
    "pinky": (PINKY_PIP, PINKY_TIP),
}

PINCH = "pinch"
POINT = "point"
TWO_FINGERS = "two_fingers"
OPEN_PALM = "open_palm"
THUMBS_UP = "thumbs_up"
THUMBS_DOWN = "thumbs_down"
FIST = "fist"
UNKNOWN = "unknown"
NO_HAND = "no_hand"
SWIPE_RIGHT = "swipe_right"
SWIPE_LEFT = "swipe_left"


def distance(a, b):
    return math.dist(a, b)


def hand_size(landmarks):
    return distance(landmarks[WRIST], landmarks[MIDDLE_MCP])


def is_finger_up(landmarks, finger):
    # A straight finger's tip is farther from the wrist than its middle joint.
    # Comparing distances (not y values) keeps this working when the hand is tilted.
    pip, tip = FINGER_JOINTS[finger]
    wrist = landmarks[WRIST]
    return distance(wrist, landmarks[tip]) > distance(wrist, landmarks[pip])


def fingers_up(landmarks):
    return {finger: is_finger_up(landmarks, finger) for finger in FINGER_JOINTS}


def is_thumb_extended(landmarks):
    gap = distance(landmarks[THUMB_TIP], landmarks[INDEX_MCP])
    return gap > config.THUMB_EXTENDED_RATIO * hand_size(landmarks)


def thumb_direction(landmarks):
    """Return 'up', 'down' or 'side' based on where the thumb tip points."""
    dx = landmarks[THUMB_TIP][0] - landmarks[THUMB_MCP][0]
    dy = landmarks[THUMB_TIP][1] - landmarks[THUMB_MCP][1]
    if abs(dy) <= abs(dx):
        return "side"
    return "up" if dy < 0 else "down"


def is_pinching(landmarks):
    close = distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) < config.PINCH_RATIO * hand_size(landmarks)
    # In a fist the thumb rests near the curled index, so also require the
    # index tip to reach out past its knuckle.
    wrist = landmarks[WRIST]
    index_reaching = distance(wrist, landmarks[INDEX_TIP]) > distance(wrist, landmarks[INDEX_MCP])
    return close and index_reaching


def classify(landmarks):
    """Return the gesture name for one hand."""
    if landmarks is None:
        return NO_HAND
    if is_pinching(landmarks):
        return PINCH

    up = fingers_up(landmarks)
    pattern = (up["index"], up["middle"], up["ring"], up["pinky"])

    if pattern == (True, False, False, False):
        return POINT
    if pattern == (True, True, False, False):
        return TWO_FINGERS
    if pattern == (True, True, True, True):
        return OPEN_PALM
    if pattern == (False, False, False, False):
        if is_thumb_extended(landmarks):
            direction = thumb_direction(landmarks)
            if direction == "up":
                return THUMBS_UP
            if direction == "down":
                return THUMBS_DOWN
        return FIST
    return UNKNOWN


def two_finger_x(landmarks):
    """Horizontal position between the index and middle fingertips."""
    return (landmarks[INDEX_TIP][0] + landmarks[MIDDLE_TIP][0]) / 2


class SwipeDetector:
    """Spots a fast sideways move of the hand while two fingers are up."""

    def __init__(self, min_distance=None, max_seconds=None):
        self.min_distance = min_distance or config.SWIPE_DISTANCE
        self.max_seconds = max_seconds or config.SWIPE_MAX_SECONDS
        self.history = deque()

    def reset(self):
        self.history.clear()

    def update(self, x, timestamp):
        """Feed the hand's x position. Returns a swipe name or None."""
        self.history.append((timestamp, x))
        while timestamp - self.history[0][0] > self.max_seconds:
            self.history.popleft()

        moved = x - self.history[0][1]
        if moved > self.min_distance:
            self.reset()
            return SWIPE_RIGHT
        if moved < -self.min_distance:
            self.reset()
            return SWIPE_LEFT
        return None
