"""Drives the controller detection by detection with sample hands and a fake clock.

pyautogui is stubbed, so nothing really moves or clicks and this runs on any OS.
"""

from unittest import mock

import actions
import config
from controller import MENU, POINTER, SCROLL, SWITCH, VOLUME, GestureController
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
        self.scrolled = []
        self.moves = 0
        self.controller = GestureController(ASPECT)
        self.patches = [
            mock.patch.object(actions, "OS_NAME", os_name),
            mock.patch("time.monotonic", lambda: self.now),
            mock.patch("pyautogui.click", lambda: self.sent.append("click")),
            mock.patch("pyautogui.hotkey", lambda *keys: self.sent.append("+".join(keys))),
            mock.patch("pyautogui.press", lambda key: self.sent.append(key)),
            mock.patch("pyautogui.moveTo", self.record_move),
            mock.patch("pyautogui.scroll", self.scrolled.append),
            mock.patch("pyautogui.keyDown", lambda key: self.sent.append(f"down:{key}")),
            mock.patch("pyautogui.keyUp", lambda key: self.sent.append(f"up:{key}")),
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
        actions.release_held_keys()  # a failed test must not leave keys held for the next one
        for patch in self.patches:
            patch.stop()
        actions.cursor.screen = None

    def show(self, hand, seconds=0.3):
        for _ in range(round(seconds / STEP)):
            self.controller.update(hand, self.now)
            # The main loop does these on every pass.
            actions.follow_cursor(self.now)
            self.controller.tick(self.now)
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


# Tools


def hand_above_start(session, distance, hand=POINT):
    """A hand whose palm is `distance` above where the tool started (negative is below)."""
    anchor_x, anchor_y = session.controller.anchor
    palm_x, palm_y = to_view(hand[9], ASPECT)
    dx = (anchor_x - palm_x) / ASPECT
    dy = anchor_y - distance - palm_y
    return [(x + dx, y + dy) for x, y in hand]


def start_tool(session, item):
    session.open_menu()
    session.pick(item)
    session.show(hand_above_start(session, 0.0))  # let go of the pinch, at the start point


def test_scroll_waits_until_the_hand_reaches_the_start_point():
    with Session() as s:
        s.open_menu()
        s.pick("scroll")  # the hand is still up at the Scroll wedge
        s.show(hand_above_start(s, 0.25, POINT), 1.0)
        assert s.scrolled == []
        assert "circle" in s.controller.hint(s.now)
        s.show(hand_above_start(s, 0.0))
        s.show(hand_above_start(s, 0.2), 0.5)
    assert sum(s.scrolled) > 0


def test_scroll_tool_scrolls_up_when_the_hand_goes_up():
    with Session() as s:
        start_tool(s, "scroll")
        assert s.controller.mode == SCROLL
        s.show(hand_above_start(s, 0.2), 1.0)
    assert sum(s.scrolled) > 0
    assert all(amount > 0 for amount in s.scrolled)


def test_scroll_tool_scrolls_down_when_the_hand_goes_down():
    with Session() as s:
        start_tool(s, "scroll")
        s.show(hand_above_start(s, -0.2), 1.0)
    assert sum(s.scrolled) < 0


def test_scroll_tool_is_smooth_on_windows():
    # Many small wheel steps rather than a few big jumps.
    with Session() as s:
        start_tool(s, "scroll")
        s.show(hand_above_start(s, 0.2), 1.0)
    assert len(s.scrolled) > 20
    assert max(s.scrolled) < 120


def test_scroll_tool_holds_still_near_the_start():
    with Session() as s:
        start_tool(s, "scroll")
        s.show(hand_above_start(s, 0.02), 1.0)
    assert s.scrolled == []


def test_pinch_finishes_a_tool():
    with Session() as s:
        start_tool(s, "scroll")
        s.show(hand_above_start(s, 0.0, PINCH))
    assert s.controller.mode == POINTER


def test_volume_tool_presses_once_per_step():
    with Session() as s:
        start_tool(s, "volume")
        assert s.controller.mode == VOLUME
        s.sent.clear()
        s.show(hand_above_start(s, 0.17))
        assert s.sent == ["volumeup"] * 3
        s.show(hand_above_start(s, 0.06))
    assert s.sent == ["volumeup"] * 3 + ["volumedown"] * 2


def test_switch_tool_holds_alt_and_flicks_through_apps():
    with Session() as s:
        start_tool(s, "switch_app")
        assert s.controller.mode == SWITCH
        assert s.sent[-2:] == ["down:alt", "tab"]
        s.sent.clear()
        start = hand_above_start(s, 0.0)
        for step in range(6):
            s.show([(x + step * 0.04, y) for x, y in start], STEP)
        s.show([(x + 0.2, y) for x, y in start], 0.5)
        s.show([(x + 0.2, y) for x, y in hand_above_start(s, 0.0, PINCH)], 0.3)
    assert s.sent == ["tab", "up:alt"]


def test_switch_tool_flicks_back_with_shift_tab():
    with Session() as s:
        start_tool(s, "switch_app")
        s.sent.clear()
        start = hand_above_start(s, 0.0)
        for step in range(6):
            s.show([(x - step * 0.04, y) for x, y in start], STEP)
        assert s.sent == ["shift+tab"]


def test_switch_tool_uses_cmd_on_mac():
    with Session("mac") as s:
        start_tool(s, "switch_app")
        s.show(FIST)
    assert "down:command" in s.sent
    assert s.sent[-2:] == ["esc", "up:command"]


def test_fist_cancels_the_switcher_and_lets_go_of_alt():
    with Session() as s:
        start_tool(s, "switch_app")
        s.show(FIST)
    assert s.sent[-2:] == ["esc", "up:alt"]
    assert s.controller.mode == POINTER


def test_turning_control_off_lets_go_of_alt():
    with Session() as s:
        start_tool(s, "switch_app")
        s.controller.reset()
    assert s.sent[-2:] == ["esc", "up:alt"]
    assert actions.held_keys == []


def test_tool_closes_when_the_hand_is_gone():
    with Session() as s:
        start_tool(s, "volume")
        s.show(None, config.MENU_CLOSE_SECONDS + 0.2)
    assert s.controller.mode == POINTER


def test_screenshot_asks_for_a_flash():
    with Session() as s:
        s.open_menu()
        s.pick("screenshot")
        kinds = [item.kind for item in s.controller.take_feedback()]
    assert "flash" in kinds
