"""Rules for the ASL alphabet letters you can tell apart from a still hand shape.

Supported: A B C D E F I L O U V W Y. Letters like J and Z need movement,
and others (M, N, S, T and so on) are too close to tell apart from a webcam.

Each finger is sorted into straight, bent or curled by how far its tip reaches
from the wrist compared to its knuckle. All distances are compared to the hand
size, so the rules work near or far from the camera.
"""

import math

import config
import gestures

KNUCKLES = {"index": 5, "middle": 9, "ring": 13, "pinky": 17}
TIPS = {"index": 8, "middle": 12, "ring": 16, "pinky": 20}
FINGERS = ["index", "middle", "ring", "pinky"]

STRAIGHT = "straight"
BENT = "bent"
CURLED = "curled"

SUPPORTED_LETTERS = "ABCDEFILOUVWY"


def finger_state(landmarks, finger):
    wrist = landmarks[gestures.WRIST]
    reach = gestures.distance(wrist, landmarks[TIPS[finger]])
    knuckle = gestures.distance(wrist, landmarks[KNUCKLES[finger]])
    ratio = reach / knuckle
    if ratio >= config.ASL_STRAIGHT_RATIO:
        return STRAIGHT
    if ratio <= config.ASL_CURLED_RATIO:
        return CURLED
    return BENT


def finger_states(landmarks):
    return {finger: finger_state(landmarks, finger) for finger in FINGERS}


def touching(landmarks, a, b):
    gap = gestures.distance(landmarks[a], landmarks[b])
    return gap < config.ASL_TOUCH_RATIO * gestures.hand_size(landmarks)


def thumb_across_palm(landmarks):
    # The thumb tip is closer to the pinky knuckle than the index knuckle is.
    pinky_knuckle = landmarks[KNUCKLES["pinky"]]
    thumb_reach = gestures.distance(landmarks[gestures.THUMB_TIP], pinky_knuckle)
    palm_width = gestures.distance(landmarks[KNUCKLES["index"]], pinky_knuckle)
    return thumb_reach < palm_width


def finger_angle(landmarks, finger):
    knuckle = landmarks[KNUCKLES[finger]]
    tip = landmarks[TIPS[finger]]
    return math.degrees(math.atan2(tip[1] - knuckle[1], tip[0] - knuckle[0]))


def fingers_spread(landmarks):
    """True when the index and middle fingers point apart, like a V."""
    gap = abs(finger_angle(landmarks, "index") - finger_angle(landmarks, "middle"))
    gap = min(gap, 360 - gap)
    return gap > config.ASL_SPREAD_DEGREES


def straight_pattern(states):
    return tuple(states[finger] == STRAIGHT for finger in FINGERS)


def classify_letter(landmarks):
    """Return the letter for this hand shape, or None if it is not one we know."""
    if landmarks is None:
        return None
    states = finger_states(landmarks)
    pattern = straight_pattern(states)
    thumb_out = gestures.is_thumb_extended(landmarks)

    if pattern == (False, True, True, True) and touching(landmarks, gestures.THUMB_TIP, TIPS["index"]):
        return "F"
    if pattern == (True, True, True, True):
        return None if thumb_out else "B"
    if pattern == (True, True, True, False):
        return "W"
    if pattern == (True, True, False, False):
        return "V" if fingers_spread(landmarks) else "U"
    if pattern == (False, False, False, True):
        return "Y" if thumb_out else "I"
    if pattern == (True, False, False, False):
        return index_only_letter(landmarks, thumb_out)
    if pattern == (False, False, False, False):
        return no_straight_finger_letter(landmarks, states)
    return None


def index_only_letter(landmarks, thumb_out):
    if thumb_out:
        return "L"
    if touching(landmarks, gestures.THUMB_TIP, TIPS["middle"]):
        return "D"
    return None


def no_straight_finger_letter(landmarks, states):
    """A, C, E and O all have no straight fingers."""
    if all(state == CURLED for state in states.values()):
        return "E" if thumb_across_palm(landmarks) else "A"
    if states["index"] != BENT:
        return None
    if touching(landmarks, gestures.THUMB_TIP, TIPS["index"]):
        return "O"
    if not thumb_across_palm(landmarks):
        return "C"
    return None
