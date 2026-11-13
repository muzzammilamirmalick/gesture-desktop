"""What the hand is doing right now: moving the pointer or using the menu.

Outside the menu there are only two gestures: point to move, pinch to click.
Holding an open palm opens the radial menu, and everything else lives there.
"""

from dataclasses import dataclass

import actions
import config
import gestures
from debounce import GestureStabilizer
from menu import LABELS, PalmHold, RadialMenu, to_view

POINTER = "pointer"
MENU = "menu"

# Room to leave for the header and the hint bar, as a fraction of the window height.
HEADER_SPACE = 0.18
HINT_SPACE = 0.13

# Menu items that just press their shortcut and are done.
INSTANT_ITEMS = {"screenshot", "play_pause", "close_window", "show_desktop"}

HINTS = {
    POINTER: "Point to move, pinch to click, hold an open palm for the menu",
    MENU: "Point at an action and pinch to pick it. Make a fist to close",
}


@dataclass
class Feedback:
    """Something that just happened, for the window to show."""
    kind: str  # "click", "pick" or "info"
    text: str
    position: tuple = None  # in view units, see menu.py


class GestureController:
    def __init__(self, aspect=4 / 3):
        self.aspect = aspect
        self.stabilizer = GestureStabilizer(config.STABLE_FRAMES)
        self.menu = RadialMenu(
            config.MENU_ITEMS, config.MENU_RADIUS, config.MENU_DEAD_ZONE, HEADER_SPACE, HINT_SPACE
        )
        self.palm = PalmHold(config.MENU_HOLD_SECONDS)
        self.mode = POINTER
        self.pinch_ready = False
        self.hand_lost_at = None
        self.feedback = []
        self.palm_center = None

    def reset(self):
        """Back to the pointer, with nothing ready to fire. Used when control turns on or off."""
        self.mode = POINTER
        self.menu.close()
        self.palm.reset()
        self.pinch_ready = False
        self.hand_lost_at = None
        self.stabilizer = GestureStabilizer(config.STABLE_FRAMES)  # forget old poses
        actions.stop_cursor()

    def update(self, landmarks, now):
        """Handle one new hand detection. Returns (raw gesture, stable gesture)."""
        raw = gestures.classify(landmarks)
        stable = self.stabilizer.update(raw) or gestures.NO_HAND
        pinched = self.new_pinch(stable)
        self.palm_center = self.view_point(landmarks, gestures.MIDDLE_MCP)

        if self.mode == MENU:
            self.update_menu(landmarks, raw, stable, pinched, now)
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

    def open_menu(self, now):
        actions.stop_cursor()
        self.menu.open(self.palm_center, self.aspect, now)
        self.mode = MENU

    def close_menu(self):
        self.menu.close()
        self.mode = POINTER

    def update_menu(self, landmarks, raw, stable, pinched, now):
        if landmarks is None:
            self.close_if_hand_gone(now)
            return
        self.hand_lost_at = None

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
            position = self.menu.wedge_position(self.menu.highlighted, self.menu.radius * 0.66) if item else None
            self.close_menu()
            if item:
                self.pick(item, position)
            else:
                self.say("info", "Menu closed")

    def close_if_hand_gone(self, now):
        if self.hand_lost_at is None:
            self.hand_lost_at = now
        elif now - self.hand_lost_at >= config.MENU_CLOSE_SECONDS:
            self.hand_lost_at = None
            self.close_menu()

    def pick(self, item, position):
        if item in INSTANT_ITEMS:
            actions.press_shortcut(item)
            self.say("pick", LABELS[item], position)
        else:
            self.say("info", f"{LABELS[item]} is not ready yet", position)

    def say(self, kind, text, position=None):
        self.feedback.append(Feedback(kind, text, position))

    def take_feedback(self):
        """Hand over everything that happened since the last call."""
        items, self.feedback = self.feedback, []
        return items

    def hint(self, now):
        if self.mode == POINTER and self.palm.progress(now) > 0:
            return "Keep holding for the menu"
        return HINTS[self.mode]
