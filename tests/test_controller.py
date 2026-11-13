"""Drives the controller detection by detection with sample hands and a fake clock.

pyautogui is stubbed, so nothing really moves or clicks and this runs on any OS.
"""

from unittest import mock

import actions
import config
from controller import MENU, POINTER, GestureController
from menu import to_view
from tests.sample_hands import make_hand

STEP = 1 / 30
ASPECT = 4 / 3
KNUCKLE = make_hand()[5]  # where the cursor point sits on every sample hand

FIST = make_hand()
POINT = make_hand(index=True)
PINCH = make_hand(thumb="pinch")
PALM = make_hand(index=True, middle=True, ring=True, pinky=True, thumb="out")


def moved_to(hand, view_point):
    """Shift a sample hand so its index knuckle sits on a point in view units."""
    dx = view_point[0] / ASPECT - KNUCKLE[0]
    dy = view_point[1] - KNUCKLE[1]
    return [(x + dx, y + dy) for x, y in hand]


class Session:
    def __init__(self, os_name="windows"):
        self.now = 0.0
        self.sent = []
        self.moves = 0
        self.controller = GestureController(ASPECT)
        self.patches = [
            mock.patch.object(actions, "OS_NAME", os_name),
            mock.patch("time.monotonic", lambda: self.now),
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
        self.controller.reset()
        return self

    def __exit__(self, *error):
        for patch in self.patches:
            patch.stop()
        actions.cursor.screen = None

    def show(self, hand, seconds=0.3):
        for _ in range(round(seconds / STEP)):
            self.controller.update(hand, self.now)
            actions.follow_cursor(self.now)  # the main loop does this every pass
            self.now += STEP

    def open_menu(self):
        self.show(POINT)
        self.show(PALM, config.MENU_HOLD_SECONDS + 0.2)
        assert self.controller.mode == MENU

    def pick(self, item):
        menu = self.controller.menu
        target = menu.wedge_position(config.MENU_ITEMS.index(item), menu.radius * 0.6)
        self.show(moved_to(POINT, target))
        self.show(moved_to(PINCH, target))


def test_pointing_moves_the_cursor():
    with Session() as s:
        s.show(POINT)
    assert s.moves > 0


def test_pinch_clicks_once():
    with Session() as s:
        s.show(POINT)
        s.show(PINCH, 1.0)
    assert s.sent == ["click"]


def test_let_go_and_pinch_again_clicks_again():
    with Session() as s:
        s.show(POINT)
        s.show(PINCH)
        s.show(POINT)
        s.show(PINCH)
    assert s.sent == ["click", "click"]


def test_already_pinching_when_control_turns_on_does_not_click():
    with Session() as s:
        s.show(PINCH)
    assert s.sent == []


def test_cursor_freezes_while_pinching():
    with Session() as s:
        s.show(POINT)
        before = s.moves
        s.show(PINCH)
    assert s.moves == before


def test_short_palm_does_not_open_the_menu():
    with Session() as s:
        s.show(PALM, config.MENU_HOLD_SECONDS - 0.2)
    assert s.controller.mode == POINTER


def test_holding_a_palm_opens_the_menu_around_the_hand():
    with Session() as s:
        s.open_menu()
        palm_x, palm_y = to_view(PALM[9], ASPECT)
    menu_x, menu_y = s.controller.menu.center
    assert menu_x == palm_x
    assert palm_y - 0.06 < menu_y <= palm_y  # moved up a little to clear the hint bar


def test_cursor_stays_still_in_the_menu():
    with Session() as s:
        s.open_menu()
        before = s.moves
        s.show(moved_to(POINT, (0.3, 0.3)))
    assert s.moves == before


def test_pointing_highlights_and_pinching_picks():
    with Session() as s:
        s.open_menu()
        s.pick("screenshot")
    assert s.sent == ["win+printscreen"]
    assert s.controller.mode == POINTER


def test_menu_actions_use_mac_keys_on_mac():
    with Session("mac") as s:
        s.open_menu()
        s.pick("close_window")
    assert s.sent == ["command+w"]


def test_every_instant_item_fires_its_shortcut():
    expected = {
        "screenshot": "win+printscreen",
        "play_pause": "playpause",
        "close_window": "ctrl+w",
        "show_desktop": "win+d",
    }
    for item, keys in expected.items():
        with Session() as s:
            s.open_menu()
            s.pick(item)
        assert s.sent == [keys], item


def test_pinch_in_the_middle_closes_without_doing_anything():
    with Session() as s:
        s.open_menu()
        center = s.controller.menu.center
        s.show(moved_to(POINT, center))
        s.show(moved_to(PINCH, center))
    assert s.sent == []
    assert s.controller.mode == POINTER


def test_fist_closes_the_menu():
    with Session() as s:
        s.open_menu()
        s.show(FIST)
    assert s.controller.mode == POINTER
    assert s.sent == []


def test_menu_closes_when_the_hand_is_gone():
    with Session() as s:
        s.open_menu()
        s.show(None, config.MENU_CLOSE_SECONDS + 0.2)
    assert s.controller.mode == POINTER


def test_menu_does_not_reopen_while_the_palm_is_still_up():
    with Session() as s:
        s.open_menu()
        s.show(FIST)
        s.show(PALM, 0.1)
    assert s.controller.mode == POINTER


def test_feedback_is_reported_once():
    with Session() as s:
        s.show(POINT)
        s.show(PINCH)
        first = s.controller.take_feedback()
        second = s.controller.take_feedback()
    assert [item.text for item in first] == ["Click"]
    assert second == []


def test_hint_changes_with_the_mode():
    with Session() as s:
        pointer_hint = s.controller.hint(s.now)
        s.open_menu()
        menu_hint = s.controller.hint(s.now)
    assert "pinch to click" in pointer_hint
    assert "pinch to pick" in menu_hint
