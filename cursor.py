"""Turns a hand position in the camera frame into a smooth screen position."""

import math


def map_to_screen(point, screen_width, screen_height, margin):
    """Map a normalized (x, y) point to screen pixels.

    The outer `margin` of the frame is cut off so you can reach the screen edges
    without your finger leaving the camera view. The result stays one pixel away
    from the edges so it never trips pyautogui's corner failsafe by itself.
    """
    def stretch(value):
        scaled = (value - margin) / (1 - 2 * margin)
        return min(max(scaled, 0.0), 1.0)

    x = 1 + stretch(point[0]) * (screen_width - 3)
    y = 1 + stretch(point[1]) * (screen_height - 3)
    return x, y


class Smoother:
    """Moving average so the cursor does not jitter.

    With fast_pixels set, the smoothing eases off as the jump gets bigger, so
    small shakes are calmed but quick moves are not dragged behind.
    """

    def __init__(self, amount, fast_pixels=None):
        self.amount = amount
        self.fast_pixels = fast_pixels
        self.position = None

    def amount_for(self, jump):
        if not self.fast_pixels:
            return self.amount
        return min(1.0, self.amount + jump / self.fast_pixels)

    def reset(self):
        self.position = None

    def update(self, point):
        if self.position is None:
            self.position = point
        else:
            old_x, old_y = self.position
            amount = self.amount_for(math.dist(self.position, point))
            self.position = (
                old_x + amount * (point[0] - old_x),
                old_y + amount * (point[1] - old_y),
            )
        return self.position
