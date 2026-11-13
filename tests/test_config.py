import actions
import config

KNOWN_GESTURES = {
    "pinch", "pinch_hold", "point", "swipe_right", "swipe_left",
    "open_palm", "thumbs_up", "thumbs_down", "fist",
}


def test_every_mapped_action_exists():
    known = actions.all_action_names()
    for action in config.GESTURE_ACTIONS.values():
        assert action is None or action in known


def test_only_known_gestures_are_mapped():
    assert set(config.GESTURE_ACTIONS) <= KNOWN_GESTURES


def test_reset_gesture_has_no_action():
    for gesture in config.RESET_GESTURES:
        assert config.GESTURE_ACTIONS.get(gesture) is None
