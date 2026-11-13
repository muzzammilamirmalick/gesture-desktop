"""Keeps one gesture from firing many times."""


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


class TriggerGate:
    """Lets a trigger gesture fire once, then waits for a reset gesture.

    Starts disarmed, so you have to show the reset pose (a fist) before
    anything can fire.
    """

    def __init__(self, triggers, reset_gestures):
        self.triggers = set(triggers)
        self.reset_gestures = set(reset_gestures)
        self.armed = False

    def disarm(self):
        self.armed = False

    def update(self, gesture):
        """Return True if the action for this gesture should fire now."""
        if gesture in self.reset_gestures:
            self.armed = True
            return False
        if self.armed and gesture in self.triggers:
            self.armed = False
            return True
        return False
