"""Filters out the flicker you get while moving between poses."""


class GestureStabilizer:
    """Only reports a gesture after it has been seen several frames in a row.

    This filters out the one-frame flickers you get while moving between poses.
    """

    def __init__(self, frames_needed):
        self.frames_needed = frames_needed
        self.candidate = None
        self.count = 0
        self.stable = None

    def update(self, gesture):
        if gesture == self.candidate:
            self.count += 1
        else:
            self.candidate = gesture
            self.count = 1
        if self.count >= self.frames_needed:
            self.stable = gesture
        return self.stable
