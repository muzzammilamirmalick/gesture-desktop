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
    """Lets one trigger fire, then waits for a reset gesture.

    Starts disarmed, so you have to show the reset pose (a fist) before
    anything can fire. `rearm` lets a pose re-arm a single trigger, for example
    going back to pointing re-arms the click.
    """

    def __init__(self, triggers, reset_gestures, rearm=None):
        self.triggers = set(triggers)
        self.reset_gestures = set(reset_gestures)
        self.rearm = rearm or {}
        self.ready = set()
        self.seen_reset = False  # rearm poses only count after the first fist

    @property
    def armed(self):
        return bool(self.ready)

    def disarm(self):
        self.ready.clear()
        self.seen_reset = False

    def update(self, gesture):
        """Return True if the action for this gesture should fire now."""
        if gesture in self.reset_gestures:
            self.ready = set(self.triggers)
            self.seen_reset = True
            return False
        if self.seen_reset:
            self.rearm_from(gesture)
        if gesture in self.ready:
            self.ready.clear()  # after any action, wait for a reset
            return True
        return False

    def rearm_from(self, gesture):
        for trigger, poses in self.rearm.items():
            if gesture in poses and trigger in self.triggers:
                self.ready.add(trigger)
