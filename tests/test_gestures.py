import gestures
from tests.sample_hands import make_hand, rotate, scale


def test_hand_has_21_points():
    assert len(make_hand()) == 21


def test_finger_up_and_down():
    hand = make_hand(index=True)
    assert gestures.is_finger_up(hand, "index")
    assert not gestures.is_finger_up(hand, "middle")


def test_point():
    assert gestures.classify(make_hand(index=True)) == gestures.POINT


def test_two_fingers():
    assert gestures.classify(make_hand(index=True, middle=True)) == gestures.TWO_FINGERS


def test_open_palm():
    hand = make_hand(index=True, middle=True, ring=True, pinky=True, thumb="out")
    assert gestures.classify(hand) == gestures.OPEN_PALM


def test_fist():
    assert gestures.classify(make_hand()) == gestures.FIST


def test_thumbs_up():
    assert gestures.classify(make_hand(thumb="up")) == gestures.THUMBS_UP


def test_thumbs_down():
    assert gestures.classify(make_hand(thumb="down")) == gestures.THUMBS_DOWN


def test_thumb_out_sideways_is_still_a_fist():
    assert gestures.classify(make_hand(thumb="out")) == gestures.FIST


def test_pinch():
    assert gestures.classify(make_hand(thumb="pinch")) == gestures.PINCH


def test_fist_with_tucked_thumb_is_not_a_pinch():
    assert not gestures.is_pinching(make_hand())


def test_no_hand():
    assert gestures.classify(None) == gestures.NO_HAND


def test_three_fingers_is_unknown():
    assert gestures.classify(make_hand(index=True, middle=True, ring=True)) == gestures.UNKNOWN


def test_point_works_when_hand_is_tilted():
    tilted = rotate(make_hand(index=True), 40)
    assert gestures.classify(tilted) == gestures.POINT


def test_rules_ignore_distance_from_camera():
    far_away = scale(make_hand(thumb="pinch"), 0.5)
    assert gestures.classify(far_away) == gestures.PINCH


def test_thumb_direction():
    assert gestures.thumb_direction(make_hand(thumb="up")) == "up"
    assert gestures.thumb_direction(make_hand(thumb="down")) == "down"
    assert gestures.thumb_direction(make_hand(thumb="out")) == "side"


def test_swipe_right():
    detector = gestures.SwipeDetector(min_distance=0.25, max_seconds=0.5)
    assert detector.update(0.2, 0.0) is None
    assert detector.update(0.35, 0.1) is None
    assert detector.update(0.5, 0.2) == gestures.SWIPE_RIGHT


def test_swipe_left():
    detector = gestures.SwipeDetector(min_distance=0.25, max_seconds=0.5)
    detector.update(0.8, 0.0)
    assert detector.update(0.5, 0.2) == gestures.SWIPE_LEFT


def test_slow_move_is_not_a_swipe():
    detector = gestures.SwipeDetector(min_distance=0.25, max_seconds=0.5)
    results = [detector.update(0.2 + i * 0.05, i * 0.3) for i in range(8)]
    assert results == [None] * 8


def test_swipe_fires_once_then_needs_new_movement():
    detector = gestures.SwipeDetector(min_distance=0.25, max_seconds=0.5)
    detector.update(0.2, 0.0)
    assert detector.update(0.5, 0.1) == gestures.SWIPE_RIGHT
    assert detector.update(0.52, 0.15) is None
