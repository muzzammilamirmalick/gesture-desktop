"""The steps of training mode, driven with a fake clock."""

import training
from training import ACTION, COUNTDOWN, NAME, POSE, RECORDING, SAVED, TrainingSession

ACTIONS = ["play_pause", "volume_up", "screenshot"]
SAMPLE = [0.0] * 63
ENTER = 13
BACKSPACE = 8


def session():
    return TrainingSession(ACTIONS, countdown_seconds=1.0, record_seconds=1.0, min_samples=10)


def record(s, with_hand=True, start=0.0):
    """Press r and feed 30 detections a second through the countdown and the recording."""
    s.handle_key(ord("r"), start)
    now = start
    while s.step in (COUNTDOWN, RECORDING):
        now += 1 / 30
        s.update(SAMPLE if with_hand else None, now)
    return now


def type_text(s, text):
    for char in text:
        s.handle_key(ord(char), 0.0)


def test_starts_on_the_pose_step():
    assert session().step == POSE


def test_r_counts_down_then_records():
    s = session()
    s.handle_key(ord("r"), 0.0)
    assert s.step == COUNTDOWN
    s.update(SAMPLE, 1.01)
    assert s.step == RECORDING


def test_recording_collects_samples_then_asks_for_a_name():
    s = session()
    record(s)
    assert s.step == NAME
    assert 15 <= len(s.samples) <= training.KEEP_SAMPLES


def test_losing_the_hand_goes_back_with_a_note():
    s = session()
    record(s, with_hand=False)
    assert s.step == POSE
    assert "hand" in s.note.lower()


def test_typing_a_name():
    s = session()
    record(s)
    type_text(s, "Rock On")
    s.handle_key(BACKSPACE, 0.0)
    assert s.name == "rock o"


def test_enter_with_no_name_does_nothing():
    s = session()
    record(s)
    s.handle_key(ENTER, 0.0)
    assert s.step == NAME


def test_name_then_number_picks_the_action_and_saves():
    s = session()
    record(s)
    type_text(s, "wave")
    s.handle_key(ENTER, 0.0)
    assert s.step == ACTION
    assert s.handle_key(ord("2"), 0.0) == "save"
    assert (s.step, s.name, s.action) == (SAVED, "wave", "volume_up")


def test_numbers_outside_the_list_do_nothing():
    s = session()
    record(s)
    type_text(s, "wave")
    s.handle_key(ENTER, 0.0)
    assert s.handle_key(ord("9"), 0.0) is None
    assert s.step == ACTION


def test_names_are_kept_short():
    s = session()
    record(s)
    type_text(s, "a" * 40)
    assert len(s.name) == training.MAX_NAME_LENGTH


def test_backspace_on_the_pose_step_asks_to_delete():
    assert session().handle_key(BACKSPACE, 0.0) == "delete"


def test_r_after_saving_records_another():
    s = session()
    record(s)
    type_text(s, "wave")
    s.handle_key(ENTER, 0.0)
    s.handle_key(ord("1"), 0.0)
    s.handle_key(ord("r"), 5.0)
    assert s.step == COUNTDOWN and s.name == ""
