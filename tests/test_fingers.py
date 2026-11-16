"""Finger counting at different poses, angles and distances."""

import math

import pytest

from fingers import count_fingers, fingers_up
from tests.sample_hands import make_hand, rotate, scale

POSES = {
    0: make_hand(),
    1: make_hand(index=True),
    2: make_hand(index=True, middle=True),
    3: make_hand(index=True, middle=True, ring=True),
    4: make_hand(index=True, middle=True, ring=True, pinky=True),
    5: make_hand(index=True, middle=True, ring=True, pinky=True, thumb="out"),
}


def tilt_3d(points, degrees):
    """Turn a flat hand around the vertical axis, as if it faced partly sideways."""
    angle = math.radians(degrees)
    turned = []
    for x, y in points:
        dx = x - 0.5
        turned.append((0.5 + dx * math.cos(angle), y, dx * math.sin(angle)))
    return turned


@pytest.mark.parametrize("count", POSES)
def test_counts_each_pose(count):
    assert count_fingers(POSES[count]) == count


@pytest.mark.parametrize("degrees", [-60, -30, 30, 60, 90, 180])
@pytest.mark.parametrize("count", POSES)
def test_count_holds_when_the_hand_is_rotated(count, degrees):
    assert count_fingers(rotate(POSES[count], degrees)) == count


@pytest.mark.parametrize("factor", [0.4, 0.7, 1.5])
@pytest.mark.parametrize("count", POSES)
def test_count_holds_near_and_far(count, factor):
    assert count_fingers(scale(POSES[count], factor)) == count


@pytest.mark.parametrize("degrees", [30, 60])
@pytest.mark.parametrize("count", POSES)
def test_count_holds_in_3d_when_the_hand_turns_sideways(count, degrees):
    assert count_fingers(tilt_3d(POSES[count], degrees)) == count


def test_thumbs_up_is_one():
    assert count_fingers(make_hand(thumb="up")) == 1


def test_peace_sign_with_spread_fingers_is_two():
    assert count_fingers(make_hand(index=True, middle=True, spread=True)) == 2


def test_thumb_tucked_across_the_palm_is_not_counted():
    assert fingers_up(make_hand(thumb="tucked"))["thumb"] is False


def test_thumb_against_the_side_of_a_fist_is_not_counted():
    assert fingers_up(make_hand(thumb="side"))["thumb"] is False


def test_says_which_fingers_are_up():
    up = fingers_up(make_hand(index=True, pinky=True))
    assert up == {"thumb": False, "index": True, "middle": False, "ring": False, "pinky": True}
