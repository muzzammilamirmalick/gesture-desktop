"""Frames per second, smoothed so the number on screen is readable."""


class FpsCounter:
    def __init__(self, smoothing=0.1):
        self.smoothing = smoothing
        self.last_time = None
        self.fps = 0.0

    def tick(self, now):
        if self.last_time is not None and now > self.last_time:
            current = 1.0 / (now - self.last_time)
            if self.fps == 0:
                self.fps = current
            else:
                self.fps += self.smoothing * (current - self.fps)
        self.last_time = now
        return self.fps
