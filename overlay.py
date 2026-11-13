"""Drawing on top of the webcam frame."""

import cv2
from mediapipe.tasks.python.vision import HandLandmarksConnections

GREEN = (80, 200, 80)
RED = (60, 60, 230)
WHITE = (255, 255, 255)
GREY = (170, 170, 170)
DARK = (30, 30, 30)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def to_pixels(landmarks, frame):
    height, width = frame.shape[:2]
    return [(int(x * width), int(y * height)) for x, y in landmarks]


def draw_hand(frame, landmarks):
    points = to_pixels(landmarks, frame)
    for connection in HandLandmarksConnections.HAND_CONNECTIONS:
        cv2.line(frame, points[connection.start], points[connection.end], WHITE, 2)
    for point in points:
        cv2.circle(frame, point, 4, GREEN, -1)


def draw_text(frame, text, position, color=WHITE, size=0.6, thickness=1):
    cv2.putText(frame, text, position, FONT, size, DARK, thickness + 3, cv2.LINE_AA)
    cv2.putText(frame, text, position, FONT, size, color, thickness, cv2.LINE_AA)


def draw_status(frame, gesture, lines=()):
    """Gesture label at the top, extra status lines underneath."""
    draw_text(frame, gesture.replace("_", " ").upper(), (12, 32), WHITE, 0.9, 2)
    y = 60
    for text, color in lines:
        draw_text(frame, text, (12, y), color)
        y += 24


def draw_help(frame, text):
    height = frame.shape[0]
    draw_text(frame, text, (12, height - 12), GREY, 0.5)
