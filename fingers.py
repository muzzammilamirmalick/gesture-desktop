"""Counts how many fingers a hand is holding up, from 0 to 5.

The rules only use angles and distance ratios, never raw positions or "is the
tip above the knuckle". That way the count stays the same when the hand is
tilted, upside down, close to the camera or far away.

It works on 2D image points or 3D world points. The app passes MediaPipe's
world points (in meters, centred on the hand) when it has them, because in 3D
a finger pointing at the camera still looks straight.

Rules for the four fingers (index, middle, ring, pinky):
  1. The finger is straight: the bend between knuckle->middle joint and
     middle joint->tip is under FINGER_STRAIGHT_DEGREES.
  2. It points away from the palm: the tip is farther from the wrist than the
     middle joint. A finger folded flat can look straight, this catches it.

Rules for the thumb, which bends sideways and needs its own checks:
  1. The thumb is straight: the bend at its middle joint is under
     THUMB_STRAIGHT_DEGREES.
  2. It points away from the hand: the tip is farther from the pinky knuckle
     than the thumb's middle joint is. A thumb tucked across the palm fails this.
  3. It sticks out: the tip is at least THUMB_OUT_RATIO hand sizes away from
     the index knuckle. A thumb pressed against the side of the hand fails this.
"""

import math

WRIST = 0
THUMB_MCP, THUMB_IP, THUMB_TIP = 2, 3, 4
INDEX_MCP = 5
MIDDLE_MCP = 9
PINKY_MCP = 17

# (knuckle, middle joint, tip) for each finger
FINGERS = {
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}

FINGER_STRAIGHT_DEGREES = 50
THUMB_STRAIGHT_DEGREES = 45
THUMB_OUT_RATIO = 0.5


def direction(a, b):
    """The vector from a to b. Works for 2D and 3D points."""
    return [bv - av for av, bv in zip(a, b)]


def bend_degrees(a, b, c):
    """How much the line a->b->c bends at b. 0 means perfectly straight."""
    first, second = direction(a, b), direction(b, c)
    lengths = math.hypot(*first) * math.hypot(*second)
    if lengths == 0:
        return 0.0
    cosine = sum(x * y for x, y in zip(first, second)) / lengths
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def hand_size(points):
    return math.dist(points[WRIST], points[MIDDLE_MCP])


def is_finger_up(points, finger):
    knuckle, joint, tip = FINGERS[finger]
    straight = bend_degrees(points[knuckle], points[joint], points[tip]) < FINGER_STRAIGHT_DEGREES
    wrist = points[WRIST]
    away = math.dist(wrist, points[tip]) > math.dist(wrist, points[joint])
    return straight and away


def is_thumb_up(points):
    straight = bend_degrees(points[THUMB_MCP], points[THUMB_IP], points[THUMB_TIP]) < THUMB_STRAIGHT_DEGREES
    pinky = points[PINKY_MCP]
    away = math.dist(points[THUMB_TIP], pinky) > math.dist(points[THUMB_IP], pinky)
    out = math.dist(points[THUMB_TIP], points[INDEX_MCP]) > THUMB_OUT_RATIO * hand_size(points)
    return straight and away and out


def fingers_up(points):
    """Which fingers are up, as {"thumb": True, "index": False, ...}."""
    up = {"thumb": is_thumb_up(points)}
    for finger in FINGERS:
        up[finger] = is_finger_up(points, finger)
    return up


def count_fingers(points):
    """How many fingers are up, from 0 to 5."""
    return sum(fingers_up(points).values())
