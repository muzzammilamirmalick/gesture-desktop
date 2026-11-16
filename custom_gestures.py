"""Your own gestures: turning a hand into numbers, recognizing it, and saving it.

How recognition works (k-nearest-neighbour):

1. Features. A hand is 21 points. We move them so the wrist is at (0, 0, 0),
   divide by the hand size (wrist to middle knuckle) so near and far hands
   match, and flip left hands so a gesture trained with one hand also works
   with the other. Now two hands making the same pose give nearly the same
   numbers, wherever they are in the picture.

2. Distance. To compare two hands we look at each pair of matching points
   (wrist with wrist, index tip with index tip, ...) and take the biggest gap.
   0 means identical, 0.3 means some point is almost a third of a hand size
   off. We use the biggest gap and not the average, because two poses can
   differ in just one finger, and an average over 21 points hides that.
   Orientation counts: a pose turned upside down is a different pose.

3. Vote. When you record a gesture we keep about 30 samples of it. To
   recognize a live hand we measure its distance to every saved sample, take
   the k closest ones, and the name that appears most among them wins.

4. Too far is nothing. If even the closest sample is further away than
   max_distance, the hand is not any of your gestures, so we return None.
   Without this, every hand would be "closest" to something.
"""

import json
import math
from collections import Counter
from pathlib import Path

WRIST = 0
MIDDLE_MCP = 9


def features(points, side="Right"):
    """A hand as a flat list of numbers that ignores position, size and which hand it is."""
    wrist = points[WRIST]
    size = math.dist(wrist, points[MIDDLE_MCP]) or 1.0
    flip = -1.0 if side == "Left" else 1.0
    result = []
    for point in points:
        x, y = point[0], point[1]
        z = point[2] if len(point) > 2 else 0.0
        wx, wy = wrist[0], wrist[1]
        wz = wrist[2] if len(wrist) > 2 else 0.0
        result += [flip * (x - wx) / size, (y - wy) / size, (z - wz) / size]
    return result


def hand_distance(a, b):
    """The biggest gap between matching points of two feature lists."""
    return max(math.dist(a[i:i + 3], b[i:i + 3]) for i in range(0, len(a), 3))


class GestureClassifier:
    def __init__(self, k=5, max_distance=0.35):
        self.k = k
        self.max_distance = max_distance
        self.samples = []  # (name, features) pairs

    def set_samples(self, gestures):
        """Load every sample from {name: {"samples": [...]}}."""
        self.samples = [(name, sample) for name, gesture in gestures.items() for sample in gesture["samples"]]

    def classify(self, hand_features):
        """The name of the closest gesture, or None if nothing is close enough."""
        if not self.samples:
            return None
        scored = sorted((hand_distance(hand_features, sample), name) for name, sample in self.samples)
        if scored[0][0] > self.max_distance:
            return None
        nearest = [name for distance, name in scored[:self.k] if distance <= self.max_distance]
        return Counter(nearest).most_common(1)[0][0]


# Saving and loading. The file looks like:
# {"wave": {"action": "volume_up", "samples": [[0.0, 0.0, 0.0, ...], ...]}}

def load(path):
    """Saved gestures from the file, or nothing if there is no file yet (or it is broken)."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError):
        print(f"Could not read {path}, starting with no custom gestures.")
        return {}


def save(path, gestures):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Round the numbers so the file stays small and readable.
    rounded = {
        name: {"action": g["action"], "samples": [[round(v, 4) for v in s] for s in g["samples"]]}
        for name, g in gestures.items()
    }
    path.write_text(json.dumps(rounded, indent=1))
