"""Drawing the window: the HUD, the radial menu, feedback and help."""

import math

import cv2
import numpy as np

import asl_letters
import icons
import instructions

GREEN = (90, 200, 90)
RED = (70, 70, 225)
AMBER = (0, 180, 255)
ACCENT = (235, 190, 60)  # a bright blue in OpenCV's BGR order
WHITE = (255, 255, 255)
GREY = (170, 170, 170)
INK = (30, 30, 30)
WEDGE = (55, 50, 45)
PANEL_COLOR = (40, 34, 30)
FONT = cv2.FONT_HERSHEY_SIMPLEX
LINE = cv2.LINE_AA

HEADER_HEIGHT = 84
PANEL_WIDTH = 340
HELP_COLUMN = 170
FINGERTIPS = [4, 8, 12, 16, 20]
# The hand drawn as five lines from the wrist plus one across the knuckles.
HAND_LINES = [
    [0, 1, 2, 3, 4],
    [0, 5, 6, 7, 8],
    [9, 10, 11, 12],
    [13, 14, 15, 16],
    [0, 17, 18, 19, 20],
    [5, 9, 13, 17],
]


# Basics

def to_pixel(point, frame):
    """A normalized (x, y) landmark in window pixels."""
    height, width = frame.shape[:2]
    return int(point[0] * width), int(point[1] * height)


def view_to_pixel(point, frame):
    """A point in view units (see menu.py) in window pixels."""
    height = frame.shape[0]
    return int(point[0] * height), int(point[1] * height)


def draw_text(frame, text, position, color=WHITE, size=0.6, thickness=1):
    cv2.putText(frame, text, position, FONT, size, color, thickness, LINE)


def text_width(text, size, thickness=1):
    return cv2.getTextSize(text, FONT, size, thickness)[0][0]


def draw_centered(frame, text, center_x, y, color=WHITE, size=0.6, thickness=1):
    draw_text(frame, text, (int(center_x - text_width(text, size, thickness) / 2), y), color, size, thickness)


def darken(frame, top, bottom, left=0, right=None, amount=0.35):
    area = frame[top:bottom, left:right]
    cv2.convertScaleAbs(area, dst=area, alpha=amount)


# HUD

def to_pixels(points, frame):
    """All landmarks in window pixels at once, as a numpy array."""
    height, width = frame.shape[:2]
    return (np.asarray(points, dtype=np.float32) * (width, height)).astype(np.int32)


def draw_hand(frame, points, cursor_point=None, color=WHITE):
    """A thin skeleton in one draw call, dots on the fingertips, and a ring on the cursor point."""
    pixels = to_pixels(points, frame)
    cv2.polylines(frame, [pixels[line] for line in HAND_LINES], False, color, 2, LINE)
    for tip in FINGERTIPS:
        cv2.circle(frame, tuple(pixels[tip]), 5, color, -1, LINE)
    if cursor_point is not None:
        cv2.circle(frame, to_pixel(cursor_point, frame), 10, GREEN, 2, LINE)


def draw_hand_tag(frame, points, text, color):
    """A small label under the wrist, like "Right" or "Left  3"."""
    height, width = frame.shape[:2]
    wrist = to_pixel(points[0], frame)
    size = 0.7
    text_size = text_width(text, size, 2)
    left = min(max(wrist[0] - text_size // 2 - 10, 0), width - text_size - 20)
    top = min(wrist[1] + 18, height - 100)
    cv2.rectangle(frame, (left, top), (left + text_size + 20, top + 32), color, -1, LINE)
    draw_text(frame, text, (left + 10, top + 24), INK, size, 2)


def fps_color(fps):
    if fps >= 50:
        return GREEN
    if fps >= 25:
        return AMBER
    return RED


def draw_control_state(frame, control_on):
    """A solid badge, so ON and OFF are obvious from across the room."""
    text, color = ("CONTROL ON", GREEN) if control_on else ("CONTROL OFF", RED)
    width = frame.shape[1]
    text_size = text_width(text, 0.6, 2)
    left = width - text_size - 34
    cv2.rectangle(frame, (left, 16), (width - 14, 46), color, -1, LINE)
    draw_text(frame, text, (left + 10, 39), INK, 0.6, 2)


def draw_speed(frame, fps, detection):
    """Display frame rate, and the camera and detection rates, top right under the badge."""
    width = frame.shape[1]
    fps_text = f"display {fps:.0f} fps"
    draw_text(frame, fps_text, (width - text_width(fps_text, 0.5) - 14, 64), fps_color(fps), 0.5)
    if detection:
        draw_text(frame, detection, (width - text_width(detection, 0.4) - 14, 79), GREY, 0.4)


def draw_header(frame, mode, hand, control_on, fps, detection=""):
    """Big mode name, the hand shape, CONTROL ON/OFF and speed."""
    darken(frame, 0, HEADER_HEIGHT)
    draw_text(frame, mode.upper(), (16, 46), WHITE, 1.2, 2)
    draw_text(frame, f"hand: {hand}", (18, 72), GREY, 0.5)
    draw_control_state(frame, control_on)
    draw_speed(frame, fps, detection)


def draw_hint(frame, hint, keys):
    """What to do next, in plain words, and the keys underneath."""
    height = frame.shape[0]
    darken(frame, height - 62, height)
    draw_text(frame, hint, (16, height - 34), WHITE, 0.55, 1)
    draw_text(frame, keys, (16, height - 12), GREY, 0.42)


def draw_message(frame, message):
    height = frame.shape[0]
    draw_text(frame, message, (16, height - 72), RED, 0.55, 2)


# Feedback

def draw_toast(frame, text):
    """A short label in the middle near the top, like "Screenshot"."""
    width = frame.shape[1]
    size = text_width(text, 0.8, 2)
    left = (width - size) // 2 - 16
    top = HEADER_HEIGHT + 14
    cv2.rectangle(frame, (left, top), (left + size + 32, top + 42), INK, -1, LINE)
    cv2.rectangle(frame, (left, top), (left + size + 32, top + 42), ACCENT, 2, LINE)
    draw_text(frame, text, (left + 16, top + 30), WHITE, 0.8, 2)


def draw_hold_ring(frame, center, progress):
    """A ring that fills while you hold your palm open."""
    x, y = view_to_pixel(center, frame)
    cv2.circle(frame, (x, y), 34, GREY, 2, LINE)
    cv2.ellipse(frame, (x, y), (34, 34), -90, 0, 360 * progress, ACCENT, 5, LINE)


# Radial menu

def draw_wedges(frame, menu, cx, cy, radius):
    """The filled wedges, blended so the video shows through a little."""
    left, top = cx - radius, cy - radius
    area = frame[top:top + 2 * radius, left:left + 2 * radius]
    layer = area.copy()
    local = (radius, radius)
    for index in range(len(menu.items)):
        start = index * menu.sector - menu.sector / 2 - 90  # OpenCV angles start at 3 o'clock
        color = ACCENT if index == menu.highlighted else WEDGE
        cv2.ellipse(layer, local, (radius, radius), 0, start + 1.5, start + menu.sector - 1.5, color, -1, LINE)
    cv2.addWeighted(layer, 0.85, area, 0.15, 0, dst=area)


def draw_menu(frame, menu):
    cx, cy = view_to_pixel(menu.center, frame)
    height = frame.shape[0]
    radius = int(menu.radius * height)
    inner = int(menu.dead_zone * height)

    draw_wedges(frame, menu, cx, cy, radius)
    cv2.circle(frame, (cx, cy), inner + 6, INK, -1, LINE)
    draw_centered(frame, "fist", cx, cy - 2, GREY, 0.4)
    draw_centered(frame, "to close", cx, cy + 12, GREY, 0.4)

    for index, item in enumerate(menu.items):
        x, y = view_to_pixel(menu.wedge_position(index, menu.radius * 0.64), frame)
        color = INK if index == menu.highlighted else WHITE
        icons.draw(frame, item, (x, y - 10), 26, color)
        draw_centered(frame, instructions.LABELS[item], x, y + 24, color, 0.42, 1)


def draw_pointer_line(frame, menu, pointer):
    """A thin line from the middle of the menu to the hand, so you can see what you point at."""
    cx, cy = view_to_pixel(menu.center, frame)
    px, py = to_pixel(pointer, frame)
    length = math.hypot(px - cx, py - cy)
    inner = menu.dead_zone * frame.shape[0] + 6
    if length <= inner:
        return
    # Start at the edge of the middle circle so the line does not cross its text.
    start = (int(cx + (px - cx) * inner / length), int(cy + (py - cy) * inner / length))
    cv2.line(frame, start, (px, py), ACCENT, 2, LINE)


# Help panel and intro

def help_panel(height, keys):
    """A side panel with the two gestures, the menu and the keys, in plain words."""
    panel = np.full((height, PANEL_WIDTH, 3), PANEL_COLOR, dtype=np.uint8)
    y = 32
    for heading, rows in instructions.help_sections():
        draw_text(panel, heading, (16, y), WHITE, 0.7, 2)
        y += 28
        for name, meaning in rows:
            draw_text(panel, name, (16, y), WHITE, 0.48)
            draw_text(panel, meaning, (HELP_COLUMN, y), GREY, 0.45)
            y += 24
        y += 10
    draw_text(panel, "Keys", (16, y), WHITE, 0.7, 2)
    y += 26
    for line in keys:
        draw_text(panel, line, (16, y), GREY, 0.45)
        y += 22
    return panel


def attach_panel(frame, panel):
    return np.hstack([frame, panel])


def draw_intro(frame):
    """The first-run screen: the three things to know, then any key to start."""
    height, width = frame.shape[:2]
    darken(frame, 0, height, amount=0.2)
    center = width // 2
    draw_centered(frame, "Gesture Control", center, 110, WHITE, 1.2, 2)
    y = 180
    for number, line in enumerate(instructions.INTRO_LINES, start=1):
        draw_centered(frame, f"{number}.  {line}", center, y, WHITE, 0.75, 2)
        y += 46
    draw_centered(frame, "Control starts off. Press space to turn it on.", center, y + 20, GREY, 0.55)
    draw_centered(frame, "Press any key to start", center, y + 70, ACCENT, 0.7, 2)


# Sign language mode

def draw_sign_header(frame, letter, hand_seen, progress, fps, detection=""):
    """The detected letter, big, with a bar that fills while you hold it."""
    width = frame.shape[1]
    darken(frame, 0, HEADER_HEIGHT)

    if letter:
        draw_text(frame, letter, (14, 56), WHITE, 1.8, 3)
    elif hand_seen:
        draw_text(frame, "?", (14, 56), AMBER, 1.8, 3)
    else:
        draw_text(frame, "NO HAND", (14, 48), GREY, 1.0, 2)

    if progress > 0:
        bar_end = 70 + int(progress * 120)
        cv2.rectangle(frame, (70, 40), (190, 48), GREY, 1)
        cv2.rectangle(frame, (70, 40), (bar_end, 48), GREEN, -1)

    mode = "SIGN MODE"
    draw_text(frame, mode, (width - text_width(mode, 0.7, 2) - 14, 36), AMBER, 0.7, 2)
    draw_speed(frame, fps, detection)


def draw_word(frame, word):
    """The word so far, in a bar above the footer."""
    height = frame.shape[0]
    top = height - 108
    darken(frame, top, top + 46)
    draw_text(frame, f"Word: {word}_", (14, top + 32), WHITE, 0.9, 2)


def sign_help_panel(height, keys):
    panel = np.full((height, PANEL_WIDTH, 3), PANEL_COLOR, dtype=np.uint8)
    lines = [
        ("Sign language", WHITE, 0.7, 2),
        (" ".join(asl_letters.SUPPORTED_LETTERS), WHITE, 0.6, 2),
        ("Hold a letter still for a second", GREY, 0.48, 1),
        ("to add it to the word.", GREY, 0.48, 1),
        ("To repeat a letter, drop it and", GREY, 0.48, 1),
        ("sign it again.", GREY, 0.48, 1),
        ("Move your hand away to add a space.", GREY, 0.48, 1),
        ("Hand control is off in this mode.", AMBER, 0.48, 1),
        ("", GREY, 0.48, 1),
        ("Keys", WHITE, 0.7, 2),
    ] + [(line, GREY, 0.45, 1) for line in keys]
    y = 32
    for text, color, size, thickness in lines:
        draw_text(panel, text, (16, y), color, size, thickness)
        y += 30 if thickness == 2 else 23
    return panel


# Feedback effects

RIPPLE_SECONDS = 0.5
FLASH_SECONDS = 0.35


def draw_ripples(frame, ripples, now):
    """Rings that grow and fade where something just happened."""
    for position, started, color in ripples:
        age = (now - started) / RIPPLE_SECONDS
        if 0 <= age < 1:
            radius = int(12 + 60 * age)
            thickness = max(1, int(6 * (1 - age)))
            cv2.circle(frame, view_to_pixel(position, frame), radius, color, thickness, LINE)


def draw_flash(frame, started, now):
    """A white flash over the window that fades out, like a camera."""
    age = (now - started) / FLASH_SECONDS
    if 0 <= age < 1:
        white = np.full_like(frame, 255)
        cv2.addWeighted(white, 0.8 * (1 - age), frame, 1 - 0.8 * (1 - age), 0, dst=frame)


# Tools

def draw_start_target(frame, anchor):
    """Where to bring your hand before scroll or volume starts."""
    x, y = view_to_pixel(anchor, frame)
    cv2.circle(frame, (x, y), 30, ACCENT, 3, LINE)
    cv2.circle(frame, (x, y), 5, ACCENT, -1, LINE)
    draw_centered(frame, "bring your hand here", x, y + 54, WHITE, 0.55, 1)


def draw_track(frame, x, top, bottom):
    cv2.line(frame, (x, top), (x, bottom), GREY, 2, LINE)


def draw_scroll_tool(frame, anchor, hand, speed, dead_zone):
    """A track through the start point, with an arrow showing which way and how fast."""
    if anchor is None:
        return
    ax, ay = view_to_pixel(anchor, frame)
    height = frame.shape[0]
    reach = int(0.3 * height)
    draw_track(frame, ax, ay - reach, ay + reach)
    zone = int(dead_zone * height)
    cv2.rectangle(frame, (ax - 14, ay - zone), (ax + 14, ay + zone), GREY, 1, LINE)
    if hand is None:
        return
    hy = view_to_pixel(hand, frame)[1]
    color = ACCENT if speed else GREY
    cv2.arrowedLine(frame, (ax, ay), (ax, hy), color, 5, LINE, tipLength=0.25)
    label = "hold still" if not speed else ("scrolling up" if speed > 0 else "scrolling down")
    draw_text(frame, label, (ax + 24, hy + 6), color, 0.6, 2)


def draw_volume_tool(frame, anchor, hand, steps, step_size):
    """A slider with a tick for each volume step and a knob at the hand."""
    if anchor is None:
        return
    ax, ay = view_to_pixel(anchor, frame)
    height = frame.shape[0]
    x = min(ax + 90, frame.shape[1] - 40)
    reach = int(0.3 * height)
    draw_track(frame, x, ay - reach, ay + reach)
    tick = step_size * height
    for index in range(-int(reach / tick), int(reach / tick) + 1):
        y = int(ay - index * tick)
        cv2.line(frame, (x - 8, y), (x + 8, y), GREY, 1, LINE)
    knob_y = int(ay - steps * tick)
    cv2.line(frame, (x, ay), (x, knob_y), ACCENT, 6, LINE)
    cv2.circle(frame, (x, knob_y), 12, ACCENT, -1, LINE)
    icons.draw(frame, "volume", (x - 44, knob_y), 26, WHITE)
    draw_text(frame, f"{steps:+d}", (x + 22, knob_y + 8), WHITE, 0.8, 2)


def draw_switch_tool(frame, last_flick, now):
    """Big arrows at the sides. The one you just flicked lights up."""
    height, width = frame.shape[:2]
    middle = height // 2
    lit = last_flick[0] if last_flick and now - last_flick[1] < 0.4 else None
    for direction, x, step in (("swipe_left", 40, -1), ("swipe_right", width - 40, 1)):
        color = ACCENT if lit == direction else GREY
        tip = (x + step * 18, middle)
        cv2.arrowedLine(frame, (x - step * 18, middle), tip, color, 8 if color == ACCENT else 4, LINE, tipLength=0.6)
