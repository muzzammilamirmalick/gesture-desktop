"""Smooth, predicted hand points for drawing, so the overlay moves at the display rate.

Detection might only run at 20 or 30 fps, but the window redraws at 60. If we
drew the raw landmarks, the hand would visibly jump every time a new detection
came in. Instead every point keeps a position and a speed (the same alpha-beta
idea as CursorPredictor in cursor.py, just for all 21 points at once with numpy),
and the window draws where the hand should be right now.
"""

import numpy as np


class HandMotion:
    def __init__(self, alpha, beta, max_ahead):
        self.alpha = alpha
        self.beta = beta
        self.max_ahead = max_ahead
        self.reset()

    def reset(self):
        self.position = None
        self.velocity = None
        self.updated_at = 0.0

    def observe(self, points, now):
        """Feed the newest detected points, a list of (x, y)."""
        measured = np.array(points, dtype=np.float32)
        if self.position is None or self.position.shape != measured.shape:
            self.position = measured
            self.velocity = np.zeros_like(measured)
            self.updated_at = now
            return
        elapsed = max(now - self.updated_at, 1e-3)
        guess = self.ahead(elapsed)
        miss = measured - guess
        self.position = guess + self.alpha * miss
        self.velocity = self.velocity + self.beta * miss / elapsed
        self.updated_at = now

    def ahead(self, seconds):
        return self.position + self.velocity * min(seconds, self.max_ahead)

    def predict(self, now):
        """The points as they should be right now, or None if there is no hand."""
        if self.position is None:
            return None
        return self.ahead(now - self.updated_at)
