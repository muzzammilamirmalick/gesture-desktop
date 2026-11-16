"""Runs a pose's action once you have held the pose still for a moment.

Used for your custom gestures and for the poses in each app profile. Holding
for a moment means passing through a pose on the way to another one never
fires anything. It fires once per hold: change pose (or drop your hand) and
make it again to fire again.
"""


class PoseTrigger:
    def __init__(self, hold_seconds):
        self.hold_seconds = hold_seconds
        self.reset()

    def reset(self):
        self.pose = None
        self.since = 0.0
        self.fired = False
        self.armed = False  # True while the pose has an action

    def update(self, pose, has_action, now):
        """Feed the current pose. Returns True at the moment its action should run."""
        if pose != self.pose:
            self.pose = pose
            self.since = now
            self.fired = False
        self.armed = pose is not None and has_action
        if pose is None or not has_action or self.fired:
            return False
        if now - self.since >= self.hold_seconds:
            self.fired = True
            return True
        return False

    def progress(self, now):
        """From 0 to 1 while a pose is being held, for the ring on screen."""
        if not self.armed or self.fired:
            return 0.0
        return min(1.0, (now - self.since) / self.hold_seconds)
