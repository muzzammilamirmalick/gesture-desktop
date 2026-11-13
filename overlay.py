"""Drawing on top of the webcam frame."""

import cv2
import numpy as np
from mediapipe.tasks.python.vision import HandLandmarksConnections

import gestures
import instructions

GREEN = (80, 200, 80)
RED = (60, 60, 230)
AMBER = (0, 180, 255)
WHITE = (255, 255, 255)
GREY = (170, 170, 170)
PANEL_COLOR = (40, 34, 30)
FONT = cv2.FONT_HERSHEY_SIMPLEX

HEADER_HEIGHT = 84
PANEL_WIDTH = 340
ACTION_COLUMN = 180
CONNECTIONS = [(c.start, c.end) for c in HandLandmarksConnections.HAND_CONNECTIONS]


def to_pixels(landmarks, frame):
    height, width = frame.shape[:2]
    return [(int(x * width), int(y * height)) for x, y in landmarks]


def draw_hand(frame, landmarks):
    points = to_pixels(landmarks, frame)
    for start, end in CONNECTIONS:
        cv2.line(frame, points[start], points[end], WHITE, 2)
    for point in points:
        cv2.circle(frame, point, 4, GREEN, -1)


def draw_text(frame, text, position, color=WHITE, size=0.6, thickness=1):
    cv2.putText(frame, text, position, FONT, size, color, thickness, cv2.LINE_AA)


def text_width(text, size, thickness=1):
    return cv2.getTextSize(text, FONT, size, thickness)[0][0]


def darken(frame, top, bottom):
    strip = frame[top:bottom]
    cv2.convertScaleAbs(strip, dst=strip, alpha=0.35)


def gesture_color(gesture):
    if gesture == gestures.UNKNOWN:
        return AMBER
    if gesture == gestures.NO_HAND:
        return GREY
    return WHITE


def fps_color(fps):
    if fps >= 24:
        return GREEN
    if fps >= 15:
        return AMBER
    return RED


def draw_header(frame, gesture, control_on, fired, fps):
    """Big gesture name, CONTROL ON/OFF, frames per second and the action that just fired."""
    width = frame.shape[1]
    darken(frame, 0, HEADER_HEIGHT)

    draw_text(frame, instructions.gesture_name(gesture).upper(), (14, 44), gesture_color(gesture), 1.2, 2)

    state, color = ("CONTROL ON", GREEN) if control_on else ("CONTROL OFF", RED)
    state_x = width - text_width(state, 0.7, 2) - 14
    draw_text(frame, state, (state_x, 36), color, 0.7, 2)

    fps_text = f"{fps:.0f} fps"
    fps_x = width - text_width(fps_text, 0.55) - 14
    draw_text(frame, fps_text, (fps_x, 70), fps_color(fps), 0.55)

    if fired:
        draw_text(frame, f"Action: {fired}", (14, 72), GREEN, 0.65, 2)


def draw_footer(frame, lines):
    """Small status lines and key help along the bottom."""
    height = frame.shape[0]
    darken(frame, height - 16 - 24 * len(lines), height)
    y = height - 12 - 24 * (len(lines) - 1)
    for text, color in lines:
        draw_text(frame, text, (14, y), color, 0.5)
        y += 24


def help_panel(height, keys):
    """A side panel listing every gesture and key in plain words."""
    panel = np.full((height, PANEL_WIDTH, 3), PANEL_COLOR, dtype=np.uint8)
    y = 34
    cv2.putText(panel, "Gestures", (16, y), FONT, 0.75, WHITE, 2, cv2.LINE_AA)
    y += 30
    for name, action in instructions.gesture_guide():
        cv2.putText(panel, name, (16, y), FONT, 0.5, WHITE, 1, cv2.LINE_AA)
        cv2.putText(panel, action, (ACTION_COLUMN, y), FONT, 0.5, GREY, 1, cv2.LINE_AA)
        y += 28

    y += 6
    cv2.putText(panel, "Keys", (16, y), FONT, 0.75, WHITE, 2, cv2.LINE_AA)
    y += 28
    for key, meaning in keys:
        cv2.putText(panel, f"{key}: {meaning}", (16, y), FONT, 0.5, GREY, 1, cv2.LINE_AA)
        y += 24
    return panel


def attach_panel(frame, panel):
    return np.hstack([frame, panel])
