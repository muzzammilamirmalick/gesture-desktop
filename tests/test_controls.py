"""Drives the controller frame by frame with sample hands and a fake clock.

pyautogui is stubbed, so nothing really moves or clicks and this runs on any OS.
"""

from unittest import mock

import pytest

import actions
import main
from tests.sample_hands import make_hand

FRAME_SECONDS = 1 / 30

FIST = make_hand()
POINT = make_hand(index=True)
PINCH = make_hand(thumb="pinch")
PALM = make_hand(index=True, middle=True, ring=True, pinky=True, thumb="out")
THUMBS_UP = make_hand(thumb="up")
THUMBS_DOWN = make_hand(thumb="down")
PEACE = make_hand(index=True, middle=True)


class Session:
    """A controller plus a record of everything it sent to the OS."""

    def __init__(self, os_name="windows"):
        self.now = 0.0
        self.sent = []
        self.moves = 0
        self.controller = main.GestureController()
        self.patches = [
            mock.patch.object(actions, "OS_NAME", os_name),
            mock.patch.object(main.time, "monotonic", lambda: self.now),
            mock.patch("pyautogui.click", lambda: self.sent.append("click")),
            mock.patch("pyautogui.hotkey", lambda *keys: self.sent.append("+".join(keys))),
            mock.patch("pyautogui.press", lambda key: self.sent.append(key)),
            mock.patch("pyautogui.moveTo", self.record_move),
            mock.patch("pyautogui.size", lambda: (1920, 1080)),
            mock.patch("mac_keys.press_media_key", lambda key: self.sent.append(key)),
        ]

    def record_move(self, x, y):
        self.moves += 1

    def __enter__(self):
        for patch in self.patches:
            patch.start()
        actions.stop_cursor()
        return self

    def __exit__(self, *error):
        for patch in self.patches:
            patch.stop()

    def show(self, hand, seconds=0.3):
        for _ in range(round(seconds / FRAME_SECONDS)):
            raw, stable, event = self.controller.read_gesture(hand)
            self.controller.act(raw, stable, event, hand)
            self.now += FRAME_SECONDS


def test_nothing_fires_before_the_first_fist():
    with Session() as s:
        s.show(THUMBS_UP)
        s.show(POINT)
        s.show(PINCH)
        s.show(POINT)
    assert s.sent == []


def test_quick_pinch_clicks_once_when_released():
    with Session() as s:
        s.show(FIST)
        s.show(POINT)
        s.show(PINCH, 0.3)
        assert s.sent == []  # nothing yet, it could still become a hold
        s.show(POINT)
    assert s.sent == ["click"]


def test_cursor_stops_while_pinching():
    with Session() as s:
        s.show(FIST)
        s.show(POINT)
        moves_before = s.moves
        s.show(PINCH, 0.3)
    assert moves_before > 0
    assert s.moves == moves_before


def test_can_click_again_after_pointing_without_a_fist():
    with Session() as s:
        s.show(FIST)
        s.show(POINT)
        s.show(PINCH)
        s.show(POINT)
        s.show(PINCH)
        s.show(POINT)
    assert s.sent == ["click", "click"]


def test_pinch_and_hold_closes_the_window_once():
    with Session() as s:
        s.show(FIST)
        s.show(POINT)
        s.show(PINCH, 2.5)
        s.show(POINT)
    assert s.sent == ["ctrl+w"]


def test_close_needs_a_fist_before_it_can_fire_again():
    with Session() as s:
        s.show(FIST)
        s.show(PINCH, 1.5)
        s.show(POINT)
        s.show(PINCH, 1.5)
        s.show(FIST)
        s.show(PINCH, 1.5)
    assert s.sent == ["ctrl+w", "ctrl+w"]


def test_close_window_uses_cmd_w_on_mac():
    with Session("mac") as s:
        s.show(FIST)
        s.show(PINCH, 1.5)
    assert s.sent == ["command+w"]


def test_losing_the_hand_mid_pinch_does_not_click():
    with Session() as s:
        s.show(FIST)
        s.show(PINCH)
        s.show(None)
    assert s.sent == []


@pytest.mark.parametrize("hand, key", [
    (THUMBS_UP, "volumeup"),
    (THUMBS_DOWN, "volumedown"),
    (PALM, "playpause"),
])
def test_each_pose_fires_once_until_a_fist(hand, key):
    with Session() as s:
        s.show(FIST)
        s.show(hand, 1.0)
        s.show(POINT)
        s.show(hand, 1.0)
        assert s.sent == [key]
        s.show(FIST)
        s.show(hand)
    assert s.sent == [key, key]


def test_swipe_fires_once():
    with Session() as s:
        s.show(FIST)
        for step in range(12):
            moved = [(x + step * 0.04, y) for x, y in PEACE]
            s.show(moved, FRAME_SECONDS)
        s.show(PEACE, 0.5)
    assert s.sent == ["alt+tab"]


def test_one_action_at_a_time():
    # After any action, other gestures wait for a fist too.
    with Session() as s:
        s.show(FIST)
        s.show(THUMBS_UP)
        s.show(PALM)
        s.show(THUMBS_DOWN)
    assert s.sent == ["volumeup"]
