"""Turns a hand position in the camera frame into a smooth, responsive cursor."""


def map_to_screen(point, screen_width, screen_height, margin):
    """Map a normalized (x, y) point to screen pixels.

    The outer `margin` of the frame is cut off so you can reach the screen edges
    without your hand leaving the camera view. The result stays one pixel away
    from the edges so it never trips pyautogui's corner failsafe by itself.
    """
    def stretch(value):
        scaled = (value - margin) / (1 - 2 * margin)
        return min(max(scaled, 0.0), 1.0)

    x = 1 + stretch(point[0]) * (screen_width - 3)
    y = 1 + stretch(point[1]) * (screen_height - 3)
    return x, y


class CursorPredictor:
    """Smooths the detected position and guesses where the hand is between detections.

    It keeps a position and a speed (an alpha-beta filter). Each detection pulls
    the position part of the way to the measured point (`alpha`) and corrects the
    speed (`beta`). Between detections the cursor keeps moving at that speed, so
    it glides instead of jumping each time a new detection lands. The guess is
    capped at `max_ahead` seconds so it never runs off if detections stop.
    """

    def __init__(self, alpha, beta, max_ahead):
        self.alpha = alpha
        self.beta = beta
        self.max_ahead = max_ahead
        self.reset()

    def reset(self):
        self.position = None
        self.velocity = (0.0, 0.0)
        self.updated_at = 0.0

    def observe(self, point, now):
        if self.position is None:
            self.position = point
            self.velocity = (0.0, 0.0)
            self.updated_at = now
            return
        elapsed = max(now - self.updated_at, 1e-3)
        guess = self.ahead(elapsed)
        miss = (point[0] - guess[0], point[1] - guess[1])
        self.position = (guess[0] + self.alpha * miss[0], guess[1] + self.alpha * miss[1])
        self.velocity = (
            self.velocity[0] + self.beta * miss[0] / elapsed,
            self.velocity[1] + self.beta * miss[1] / elapsed,
        )
        self.updated_at = now

    def ahead(self, seconds):
        seconds = min(seconds, self.max_ahead)
        return (
            self.position[0] + self.velocity[0] * seconds,
            self.position[1] + self.velocity[1] * seconds,
        )

    def predict(self, now):
        """Where the cursor should be right now, or None before the first detection."""
        if self.position is None:
            return None
        return self.ahead(now - self.updated_at)
