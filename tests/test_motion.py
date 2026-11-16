"""Predicted hand points for drawing between detections."""

import pytest

from motion import HandMotion


def hand_at(x):
    return [(x, 0.5)] * 21


def test_no_hand_means_nothing_to_draw():
    assert HandMotion(0.7, 0.2, 0.06).predict(1.0) is None


def test_first_detection_is_drawn_as_is():
    motion = HandMotion(0.7, 0.2, 0.06)
    motion.observe(hand_at(0.3), 1.0)
    assert motion.predict(1.0)[0][0] == pytest.approx(0.3)


def test_keeps_moving_between_detections():
    motion = HandMotion(0.7, 0.2, 0.06)
    for step in range(10):
        motion.observe(hand_at(0.1 + step * 0.01), step / 30)
    last = motion.predict(9 / 30)[0][0]
    later = motion.predict(9 / 30 + 1 / 60)[0][0]
    assert later > last  # half a detection later it has moved on a bit


def test_stops_guessing_if_detections_stop():
    motion = HandMotion(0.7, 0.2, 0.06)
    for step in range(10):
        motion.observe(hand_at(0.1 + step * 0.01), step / 30)
    assert motion.predict(5.0)[0][0] == pytest.approx(motion.predict(9 / 30 + 0.06)[0][0])


def test_reset_forgets_the_hand():
    motion = HandMotion(0.7, 0.2, 0.06)
    motion.observe(hand_at(0.3), 1.0)
    motion.reset()
    assert motion.predict(1.0) is None
