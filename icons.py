"""Small line icons for the menu, drawn with OpenCV shapes.

Each function draws one icon centred on (x, y), about `size` pixels across.
"""

import cv2
import numpy as np

LINE = cv2.LINE_AA


def scroll(image, x, y, size, color):
    half = size // 2
    cv2.line(image, (x, y - half + 4), (x, y + half - 4), color, 2, LINE)
    for direction in (-1, 1):
        tip = y + direction * half
        points = np.array([(x, tip), (x - 7, tip - direction * 8), (x + 7, tip - direction * 8)])
        cv2.fillPoly(image, [points], color, LINE)


def volume(image, x, y, size, color):
    s = size // 2
    cv2.rectangle(image, (x - s, y - 5), (x - s + 7, y + 5), color, -1, LINE)
    cone = np.array([(x - s + 7, y - 5), (x - 2, y - s + 2), (x - 2, y + s - 2), (x - s + 7, y + 5)])
    cv2.fillPoly(image, [cone], color, LINE)
    for radius in (6, 12):
        cv2.ellipse(image, (x, y), (radius, radius), 0, -45, 45, color, 2, LINE)


def switch_app(image, x, y, size, color):
    s = size // 2
    cv2.rectangle(image, (x - s, y - s + 6), (x + s - 8, y + s - 10), color, 2, LINE)
    cv2.rectangle(image, (x - s + 8, y - s + 12), (x + s, y + s - 4), color, -1, LINE)


def screenshot(image, x, y, size, color):
    s = size // 2
    cv2.rectangle(image, (x - s, y - s + 8), (x + s, y + s - 4), color, 2, LINE)
    cv2.rectangle(image, (x - 5, y - s + 4), (x + 5, y - s + 8), color, -1, LINE)
    cv2.circle(image, (x, y + 2), 6, color, 2, LINE)


def play_pause(image, x, y, size, color):
    s = size // 2
    triangle = np.array([(x - s, y - s + 2), (x - s, y + s - 2), (x - 1, y)])
    cv2.fillPoly(image, [triangle], color, LINE)
    cv2.rectangle(image, (x + 3, y - s + 2), (x + 7, y + s - 2), color, -1, LINE)
    cv2.rectangle(image, (x + 11, y - s + 2), (x + 15, y + s - 2), color, -1, LINE)


def close_window(image, x, y, size, color):
    s = size // 2
    cv2.rectangle(image, (x - s, y - s), (x + s, y + s), color, 2, LINE)
    cv2.line(image, (x - s + 6, y - s + 6), (x + s - 6, y + s - 6), color, 2, LINE)
    cv2.line(image, (x + s - 6, y - s + 6), (x - s + 6, y + s - 6), color, 2, LINE)


def show_desktop(image, x, y, size, color):
    s = size // 2
    cv2.rectangle(image, (x - s, y - s + 2), (x + s, y + s - 8), color, 2, LINE)
    cv2.line(image, (x, y + s - 8), (x, y + s - 2), color, 2, LINE)
    cv2.line(image, (x - 8, y + s - 2), (x + 8, y + s - 2), color, 2, LINE)


ICONS = {
    "scroll": scroll,
    "volume": volume,
    "switch_app": switch_app,
    "screenshot": screenshot,
    "play_pause": play_pause,
    "close_window": close_window,
    "show_desktop": show_desktop,
}


def draw(image, name, center, size, color):
    ICONS[name](image, int(center[0]), int(center[1]), size, color)
