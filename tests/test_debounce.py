from debounce import GestureStabilizer


def feed(stabilizer, gestures):
    return [stabilizer.update(g) for g in gestures]


def test_stabilizer_waits_for_enough_frames():
    stabilizer = GestureStabilizer(frames_needed=3)
    assert feed(stabilizer, ["pinch", "pinch", "pinch"]) == [None, None, "pinch"]


def test_stabilizer_ignores_a_one_frame_flicker():
    stabilizer = GestureStabilizer(frames_needed=3)
    feed(stabilizer, ["fist"] * 3)
    assert feed(stabilizer, ["pinch", "fist", "fist"]) == ["fist", "fist", "fist"]
