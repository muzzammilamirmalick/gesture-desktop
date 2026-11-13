from eyes import DOUBLE_BLINK, BlinkDetector, eyes_closed_score, gaze_direction

FRAME = 1 / 30
OPEN = 0.05
CLOSED = 0.9


def detector():
    return BlinkDetector(closed=0.5, opened=0.3, max_blink=0.5, double_window=0.7)


def play(blinks, scores, start=0.0):
    """Feed a list of (score, seconds) steps. Returns events and the end time."""
    events = []
    now = start
    for score, seconds in scores:
        for _ in range(round(seconds / FRAME)):
            event = blinks.update(score, now)
            if event:
                events.append(event)
            now += FRAME
    return events, now


def test_one_blink_does_nothing():
    events, _ = play(detector(), [(OPEN, 0.5), (CLOSED, 0.15), (OPEN, 1.0)])
    assert events == []


def test_two_quick_blinks_fire_once():
    steps = [(OPEN, 0.5), (CLOSED, 0.15), (OPEN, 0.25), (CLOSED, 0.15), (OPEN, 1.0)]
    events, _ = play(detector(), steps)
    assert events == [DOUBLE_BLINK]


def test_blinks_far_apart_do_not_count():
    steps = [(OPEN, 0.5), (CLOSED, 0.15), (OPEN, 2.0), (CLOSED, 0.15), (OPEN, 1.0)]
    events, _ = play(detector(), steps)
    assert events == []


def test_three_blinks_fire_only_once():
    steps = [(OPEN, 0.3)] + [(CLOSED, 0.15), (OPEN, 0.2)] * 3
    events, _ = play(detector(), steps)
    assert events == [DOUBLE_BLINK]


def test_long_eye_close_is_not_a_blink():
    steps = [(OPEN, 0.3), (CLOSED, 1.5), (OPEN, 0.2), (CLOSED, 0.15), (OPEN, 1.0)]
    events, _ = play(detector(), steps)
    assert events == []


def test_half_closed_flicker_is_ignored():
    steps = [(OPEN, 0.3)] + [(0.45, FRAME), (0.35, FRAME)] * 20
    events, _ = play(detector(), steps)
    assert events == []


def test_wink_is_not_a_blink():
    assert eyes_closed_score({"eyeBlinkLeft": 0.9, "eyeBlinkRight": 0.1}) == 0.1


def gaze_scores(**looks):
    names = [
        "eyeLookOutLeft", "eyeLookInLeft", "eyeLookUpLeft",
        "eyeLookOutRight", "eyeLookInRight", "eyeLookUpRight",
    ]
    scores = dict.fromkeys(names, 0.05)
    scores.update(looks)
    return scores


def test_gaze_center():
    assert gaze_direction(gaze_scores(), threshold=0.4) == "center"


def test_gaze_left():
    scores = gaze_scores(eyeLookOutLeft=0.7, eyeLookInRight=0.6)
    assert gaze_direction(scores, threshold=0.4) == "left"


def test_gaze_right():
    scores = gaze_scores(eyeLookInLeft=0.6, eyeLookOutRight=0.7)
    assert gaze_direction(scores, threshold=0.4) == "right"


def test_gaze_up():
    scores = gaze_scores(eyeLookUpLeft=0.6, eyeLookUpRight=0.6)
    assert gaze_direction(scores, threshold=0.4) == "up"
