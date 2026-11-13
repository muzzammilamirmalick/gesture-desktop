"""The radial menu: opening it with a held palm, and which wedge the hand points at.

Positions are in "view units": y runs from 0 (top) to 1 (bottom) of the window
and x from 0 to the window's width divided by its height. That keeps circles
round whatever the window size.
"""

import math

LABELS = {
    "scroll": "Scroll",
    "volume": "Volume",
    "switch_app": "Switch app",
    "screenshot": "Screenshot",
    "play_pause": "Play / pause",
    "close_window": "Close window",
    "show_desktop": "Desktop",
}

# One line each for the help panel.
DESCRIPTIONS = {
    "scroll": "move your hand up or down to scroll",
    "volume": "move your hand up or down for volume",
    "switch_app": "flick left or right through apps",
    "screenshot": "save a screenshot",
    "play_pause": "play or pause music and video",
    "close_window": "close the window or tab",
    "show_desktop": "hide all windows",
}


def to_view(point, aspect):
    """A normalized (x, y) landmark in view units."""
    return point[0] * aspect, point[1]


def angle_from_top(center, point):
    """Clockwise angle in degrees, 0 straight up. Screen y grows downward."""
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    return math.degrees(math.atan2(dx, -dy)) % 360


class RadialMenu:
    def __init__(self, items, radius, dead_zone, top_margin=0.0, bottom_margin=0.0):
        self.items = list(items)
        self.radius = radius
        self.dead_zone = dead_zone
        self.top_margin = top_margin
        self.bottom_margin = bottom_margin
        self.center = None
        self.highlighted = None
        self.opened_at = 0.0

    @property
    def is_open(self):
        return self.center is not None

    @property
    def sector(self):
        return 360 / len(self.items)

    def open(self, center, aspect, now):
        """Open around `center`, moved in from the edges so the whole menu fits."""
        x = min(max(center[0], self.radius), aspect - self.radius)
        y = min(max(center[1], self.top_margin + self.radius), 1 - self.bottom_margin - self.radius)
        self.center = (x, y)
        self.highlighted = None
        self.opened_at = now

    def close(self):
        self.center = None
        self.highlighted = None

    def wedge_at(self, point):
        """Index of the wedge under `point`, or None in the middle of the menu."""
        if math.dist(self.center, point) < self.dead_zone:
            return None
        angle = (angle_from_top(self.center, point) + self.sector / 2) % 360
        return int(angle // self.sector)

    def point_at(self, point):
        self.highlighted = self.wedge_at(point)

    def chosen_item(self):
        if self.highlighted is None:
            return None
        return self.items[self.highlighted]

    def wedge_position(self, index, distance):
        """Where the middle of a wedge is, at `distance` from the center."""
        angle = math.radians(index * self.sector)
        return (
            self.center[0] + math.sin(angle) * distance,
            self.center[1] - math.cos(angle) * distance,
        )


class PalmHold:
    """Says when an open palm has been held long enough to open the menu.

    It fires once per hold. Drop the palm and show it again to fire again.
    """

    def __init__(self, seconds):
        self.seconds = seconds
        self.started_at = None
        self.fired = False

    def reset(self):
        self.started_at = None
        self.fired = False

    def update(self, holding, now):
        if not holding:
            self.reset()
            return False
        if self.started_at is None:
            self.started_at = now
        if not self.fired and now - self.started_at >= self.seconds:
            self.fired = True
            return True
        return False

    def progress(self, now):
        """From 0 to 1 while holding, for the filling ring on screen."""
        if self.started_at is None or self.fired:
            return 0.0
        return min(1.0, (now - self.started_at) / self.seconds)
