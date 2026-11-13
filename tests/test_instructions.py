import config
import gestures
import instructions
from main import GestureController
from tests.sample_hands import make_hand


def test_unknown_pose_is_labelled_unknown():
    three_fingers = make_hand(index=True, middle=True, ring=True)
    assert gestures.classify(three_fingers) == gestures.UNKNOWN
    assert instructions.gesture_name(gestures.UNKNOWN) == "Unknown"


def test_label_follows_the_hand_right_away():
    # The stable gesture lags behind on purpose, but the label must not freeze.
    controller = GestureController()
    for _ in range(10):
        controller.read_gesture(make_hand(index=True))
    raw, stable, _ = controller.read_gesture(make_hand(index=True, middle=True, ring=True))
    assert raw == gestures.UNKNOWN
    assert stable == gestures.POINT


def test_every_gesture_has_a_name():
    for gesture in list(config.GESTURE_ACTIONS) + [gestures.UNKNOWN, gestures.NO_HAND]:
        assert gesture in instructions.GESTURE_NAMES


def test_every_action_has_plain_words():
    for action in config.GESTURE_ACTIONS.values():
        if action:
            assert action in instructions.ACTION_WORDS


def test_guide_lists_every_mapped_gesture():
    guide_names = [name for name, _ in instructions.gesture_guide()]
    for gesture, action in config.GESTURE_ACTIONS.items():
        if action:
            assert instructions.gesture_name(gesture) in guide_names


def test_guide_starts_with_the_rest_pose():
    assert instructions.gesture_guide()[0][0] == "Fist"
