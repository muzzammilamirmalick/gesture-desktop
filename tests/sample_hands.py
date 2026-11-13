"""Sample landmark data for tests.

Builds a right hand facing the camera, palm open, with each finger either
straight or curled. Coordinates are normalized like MediaPipe's (y grows down).
"""

import math

WRIST = (0.50, 0.80)
KNUCKLES = {
    "index": (0.44, 0.60),
    "middle": (0.50, 0.58),
    "ring": (0.55, 0.60),
    "pinky": (0.60, 0.62),
}
THUMB_BASE = [(0.45, 0.75), (0.41, 0.70)]  # CMC, MCP

THUMB_POSES = {
    "tucked": [(0.42, 0.64), (0.47, 0.62)],  # IP, tip resting on the index
    "out": [(0.35, 0.64), (0.28, 0.58)],
    "up": [(0.40, 0.58), (0.39, 0.45)],
    "down": [(0.41, 0.80), (0.40, 0.92)],
    "pinch": [(0.43, 0.56), (0.47, 0.50)],
}


def straight_finger(knuckle):
    x, y = knuckle
    return [(x, y - 0.07), (x, y - 0.12), (x, y - 0.16)]


def curled_finger(knuckle):
    x, y = knuckle
    return [(x, y - 0.05), (x, y - 0.02), (x, y + 0.03)]


def pinching_index(knuckle):
    x, y = knuckle
    return [(x, y - 0.06), (x + 0.02, y - 0.09), (0.47, 0.50)]


def make_hand(index=False, middle=False, ring=False, pinky=False, thumb="tucked"):
    raised = {"index": index, "middle": middle, "ring": ring, "pinky": pinky}
    points = [WRIST] + THUMB_BASE + THUMB_POSES[thumb]
    for finger, knuckle in KNUCKLES.items():
        points.append(knuckle)
        if finger == "index" and thumb == "pinch":
            points += pinching_index(knuckle)
        elif raised[finger]:
            points += straight_finger(knuckle)
        else:
            points += curled_finger(knuckle)
    return points


def rotate(points, degrees, center=(0.5, 0.6)):
    angle = math.radians(degrees)
    cx, cy = center
    rotated = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        rotated.append((
            cx + dx * math.cos(angle) - dy * math.sin(angle),
            cy + dx * math.sin(angle) + dy * math.cos(angle),
        ))
    return rotated


def scale(points, factor, center=(0.5, 0.6)):
    cx, cy = center
    return [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in points]
