"""What the hand is doing right now: moving the pointer, using the menu, or a tool.

Outside the menu there are only two gestures: point to move, pinch to click.
Holding an open palm opens the radial menu, and everything else lives there.
Some menu items run straight away (screenshot, play or pause). Others start a
tool you control by moving your hand (scroll, volume, switch app). A pinch
finishes a tool and a fist cancels it.
"""

from dataclasses import dataclass

import actions
import config
import gestures
from debounce import GestureStabilizer
from menu import LABELS, PalmHold, RadialMenu, to_view

POINTER = "pointer"
MENU = "menu"
SCROLL = "scroll"
VOLUME = "volume"
SWITCH = "switch_app"
TOOLS = {SCROLL, VOLUME, SWITCH}

# Room to leave for the header and the hint bar, as a fraction of the window height.
HEADER_SPACE = 0.18
HINT_SPACE = 0.13
# Scroll and volume start from the middle of the free space, so there is room
# to move both ways.
TOOL_START_Y = (HEADER_SPACE + 1 - HINT_SPACE) / 2

# Menu items that just press their shortcut and are done.
INSTANT_ITEMS = {"screenshot", "play_pause", "close_window", "show_desktop"}
# Menu items that start a tool.
MODE_ITEMS = {"scroll": SCROLL, "volume": VOLUME, "switch_app": SWITCH}

HINTS = {
    POINTER: "Point to move, pinch to click, hold an open palm for the menu",
    MENU: "Point at an action and pinch to pick it. Make a fist to close",
    SCROLL: "Move your hand up or down to scroll. Pinch when done",
    VOLUME: "Move your hand up or down for volume. Pinch when done",
    "waiting": "Bring your hand to the circle to start",
    SWITCH: "Flick left or right through apps. Pinch to pick, fist to cancel",
}

MODE_NAMES = {
    POINTER: "Pointer",
    MENU: "Menu",
    SCROLL: "Scroll",
    VOLUME: "Volume",
    SWITCH: "Switch app",
}


@dataclass
class Feedback:
    """Something that just happened, for the window to show."""
    kind: str  # "click", "pick", "flash" or "info"
    text: str
    position: tuple = None  # in view units, see menu.py


def scroll_speed(offset):
    """Wheel notches per second for a hand `offset` above (+) or below (-) its start."""
    distance = abs(offset) - config.SCROLL_DEAD_ZONE
    if distance <= 0:
        return 0.0
    speed = distance * config.SCROLL_SPEED
    return speed if offset > 0 else -speed


def volume_steps(offset):
    """Whole volume steps for a hand `offset` above (+) or below (-) its start."""
    return int(offset / config.VOLUME_STEP)


class GestureController:
    def __init__(self, aspect=4 / 3):
        self.aspect = aspect
        self.stabilizer = GestureStabilizer(config.STABLE_FRAMES)
        self.menu = RadialMenu(
            config.MENU_ITEMS, config.MENU_RADIUS, config.MENU_DEAD_ZONE, HEADER_SPACE, HINT_SPACE
        )
        self.palm = PalmHold(config.MENU_HOLD_SECONDS)
        self.flicks = gestures.SwipeDetector(config.FLICK_DISTANCE, config.FLICK_SECONDS)
        self.mode = POINTER
        self.pinch_ready = False
        self.hand_lost_at = None
        self.feedback = []
        self.palm_center = None
        self.anchor = None  # the point scroll and volume measure from
        self.tool_ready = False  # scroll and volume wait until the hand reaches the anchor
        self.volume_sent = 0
        self.flick_quiet_until = 0.0
        self.last_flick = None  # (direction, time), for the arrows on screen
        self.last_tick = None

    def reset(self):
        """Back to the pointer, with nothing ready to fire. Used when control turns on or off."""
        if self.mode in TOOLS:
            self.finish_tool(cancel=True)
        self.mode = POINTER
        self.menu.close()
        self.palm.reset()
        self.pinch_ready = False
        self.hand_lost_at = None
        self.stabilizer = GestureStabilizer(config.STABLE_FRAMES)  # forget old poses
        actions.stop_cursor()

    # Each detection

    def update(self, landmarks, now):
        """Handle one new hand detection. Returns (raw gesture, stable gesture)."""
        raw = gestures.classify(landmarks)
        stable = self.stabilizer.update(raw) or gestures.NO_HAND
        pinched = self.new_pinch(stable)
        self.palm_center = self.view_point(landmarks, gestures.MIDDLE_MCP)

        if self.mode == MENU:
            self.update_menu(landmarks, raw, stable, pinched, now)
        elif self.mode in TOOLS:
            self.update_tool(landmarks, stable, pinched, now)
        else:
            self.update_pointer(landmarks, raw, stable, pinched, now)
        return raw, stable

    def new_pinch(self, stable):
        """True once per pinch. The hand has to let go before the next one counts.

        Letting go means a real hand pose that is not a pinch. Losing the hand
        does not count, so a pinch that drops out of view and comes back is
        not a second click.
        """
        if stable != gestures.PINCH:
            if stable != gestures.NO_HAND:
                self.pinch_ready = True
            return False
        if self.pinch_ready:
            self.pinch_ready = False
            return True
        return False

    def view_point(self, landmarks, index):
        if landmarks is None:
            return None
        return to_view(landmarks[index], self.aspect)

    def hand_gone_too_long(self, landmarks, now):
        """True once the hand has been out of view for MENU_CLOSE_SECONDS."""
        if landmarks is not None:
            self.hand_lost_at = None
            return False
        if self.hand_lost_at is None:
            self.hand_lost_at = now
        return now - self.hand_lost_at >= config.MENU_CLOSE_SECONDS

    # Pointer

    def update_pointer(self, landmarks, raw, stable, pinched, now):
        # Move only while the raw and stable pose agree, so the cursor freezes
        # as soon as the fingers start closing for a pinch.
        if stable == gestures.POINT and raw == gestures.POINT:
            actions.move_cursor(landmarks)
        else:
            actions.stop_cursor()

        if pinched:
            actions.click()
            self.say("click", "Click", self.view_point(landmarks, gestures.INDEX_TIP))

        if self.palm.update(stable == gestures.OPEN_PALM, now):
            self.open_menu(now)

    # Menu

    def open_menu(self, now):
        actions.stop_cursor()
        self.menu.open(self.palm_center, self.aspect, now)
        self.mode = MENU

    def close_menu(self):
        self.menu.close()
        self.mode = POINTER

    def update_menu(self, landmarks, raw, stable, pinched, now):
        if self.hand_gone_too_long(landmarks, now):
            self.close_menu()
            return
        if landmarks is None:
            return

        if stable == gestures.FIST:
            self.close_menu()
            self.say("info", "Menu closed")
            return

        # Freeze the highlight while pinching, so closing the fingers does not
        # slide it onto the next wedge.
        if raw != gestures.PINCH:
            self.menu.point_at(to_view(actions.cursor_point(landmarks), self.aspect))

        if pinched:
            item = self.menu.chosen_item()
            position = self.menu.wedge_position(self.menu.highlighted, self.menu.radius * 0.64) if item else None
            self.close_menu()
            if item:
                self.pick(item, position)
            else:
                self.say("info", "Menu closed")

    def pick(self, item, position):
        if item in MODE_ITEMS:
            self.start_tool(MODE_ITEMS[item], position)
            return
        actions.press_shortcut(item)
        kind = "flash" if item == "screenshot" else "pick"
        self.say(kind, LABELS[item], position)

    # Tools

    def start_tool(self, tool, position):
        self.mode = tool
        self.anchor = (self.palm_center[0], TOOL_START_Y)
        # The switcher starts straight away. Scroll and volume wait for the
        # hand to reach the start point, so nothing jumps the moment you pick.
        self.tool_ready = tool == SWITCH
        self.volume_sent = 0
        self.flicks.reset()
        self.last_flick = None
        self.last_tick = None
        actions.scroller.reset()
        if tool == SWITCH:
            actions.hold_shortcut("app_switcher")
            actions.press_key("tab")  # opens the switcher on the next app
        self.say("pick", MODE_NAMES[tool], position)

    def update_tool(self, landmarks, stable, pinched, now):
        if self.hand_gone_too_long(landmarks, now):
            self.finish_tool(cancel=True)
            return
        if landmarks is None:
            return
        if pinched:
            self.finish_tool()
            return
        if stable == gestures.FIST:
            self.finish_tool(cancel=True)
            return
        if not self.tool_ready:
            self.tool_ready = abs(self.hand_offset()) < config.SCROLL_DEAD_ZONE
            return
        if self.mode == VOLUME:
            self.update_volume()
        elif self.mode == SWITCH:
            self.update_switch(now)
        # Scrolling happens in tick(), so it stays smooth between detections.

    def hand_offset(self):
        """How far the hand is above (+) or below (-) where the tool started."""
        if self.anchor is None or self.palm_center is None:
            return 0.0
        return self.anchor[1] - self.palm_center[1]

    def update_volume(self):
        steps = volume_steps(self.hand_offset())
        while self.volume_sent < steps:
            actions.press_shortcut("volume_up")
            self.volume_sent += 1
        while self.volume_sent > steps:
            actions.press_shortcut("volume_down")
            self.volume_sent -= 1

    def update_switch(self, now):
        if now < self.flick_quiet_until:
            self.flicks.reset()
            return
        flick = self.flicks.update(self.palm_center[0], now)
        if not flick:
            return
        if flick == gestures.SWIPE_RIGHT:
            actions.press_key("tab")
        else:
            actions.press_keys(["shift", "tab"])
        self.last_flick = (flick, now)
        self.flick_quiet_until = now + config.FLICK_COOLDOWN

    def finish_tool(self, cancel=False):
        tool = self.mode
        if tool == SWITCH:
            if cancel:
                actions.press_key("esc")  # close the switcher without changing apps
            actions.release_held_keys()
        actions.scroller.reset()
        self.mode = POINTER
        self.anchor = None
        self.say("info", "Cancelled" if cancel else "Done")

    # Every pass of the main loop

    def tick(self, now):
        """Scrolls a little on every pass, so it is smooth between detections."""
        elapsed = 0.0 if self.last_tick is None else min(now - self.last_tick, 0.1)
        self.last_tick = now
        if self.mode != SCROLL or self.palm_center is None or not self.tool_ready:
            return
        notches = scroll_speed(self.hand_offset()) * elapsed
        if notches:
            actions.scroller.scroll(notches)

    # For the window

    def say(self, kind, text, position=None):
        self.feedback.append(Feedback(kind, text, position))

    def take_feedback(self):
        """Hand over everything that happened since the last call."""
        items, self.feedback = self.feedback, []
        return items

    def mode_name(self):
        return MODE_NAMES[self.mode]

    def hint(self, now):
        if self.mode == POINTER and self.palm.progress(now) > 0:
            return "Keep holding for the menu"
        if self.mode in TOOLS and not self.tool_ready:
            return HINTS["waiting"]
        return HINTS[self.mode]
