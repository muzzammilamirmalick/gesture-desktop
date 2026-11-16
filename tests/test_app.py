"""App state and keys, without a camera or window."""

import main
from tests.sample_hands import make_hand
from tracking import Hand


def make_app():
    app = main.App(can_control=True)
    app.show_intro = False
    return app


def test_control_starts_off():
    assert make_app().control_on is False


def test_space_toggles_control():
    app = make_app()
    app.handle_key(ord(" "))
    assert app.control_on is True


def test_no_permission_keeps_control_off():
    app = main.App(can_control=False)
    app.show_intro = False
    app.handle_key(ord(" "))
    assert app.control_on is False
    assert "permission" in app.message.lower()


def test_sign_mode_turns_control_off():
    app = make_app()
    app.handle_key(ord(" "))
    app.handle_key(ord("s"))
    assert app.sign_mode is True
    assert app.control_on is False


def test_space_in_sign_mode_adds_a_space_instead_of_control():
    app = make_app()
    app.handle_key(ord("s"))
    app.speller.word = "HI"
    app.handle_key(ord(" "))
    assert app.speller.word == "HI "
    assert app.control_on is False


def test_backspace_works_on_windows_and_mac():
    app = make_app()
    app.handle_key(ord("s"))
    app.speller.word = "ABC"
    app.handle_key(8)
    app.handle_key(127)
    assert app.speller.word == "A"


def test_clear_word():
    app = make_app()
    app.handle_key(ord("s"))
    app.speller.word = "ABC"
    app.handle_key(ord("c"))
    assert app.speller.word == ""


def test_sign_mode_reads_letters():
    app = make_app()
    app.handle_key(ord("s"))
    app.update([Hand("Right", make_hand(pinky=True, thumb="out"))])
    assert app.letter == "Y"


def test_help_key_toggles_panel():
    app = make_app()
    app.handle_key(ord("h"))
    assert app.show_help is True
    app.handle_key(ord("h"))
    assert app.show_help is False


def test_any_key_closes_the_intro_and_does_nothing_else(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "INTRO_SEEN_FILE", tmp_path / ".intro_seen")
    app = main.App(can_control=True)
    app.show_intro = True
    app.handle_key(ord(" "))
    assert app.show_intro is False
    assert app.control_on is False
    assert (tmp_path / ".intro_seen").exists()


def test_no_key_does_not_close_the_intro():
    app = main.App(can_control=True)
    app.show_intro = True
    app.handle_key(main.NO_KEY)
    assert app.show_intro is True


def test_hud_says_paused_until_control_is_on():
    app = make_app()
    assert app.mode_name() == "Paused"
    assert "space" in app.hint(0.0)
    app.handle_key(ord(" "))
    assert app.mode_name() == "Pointer"


def test_click_shows_a_ripple_but_no_label():
    from controller import Feedback
    app = make_app()
    app.show_feedback(Feedback("click", "Click", (0.5, 0.5)), 1.0)
    assert len(app.ripples) == 1
    assert app.toast is None


def test_screenshot_flashes_and_says_so():
    from controller import Feedback
    app = make_app()
    app.show_feedback(Feedback("flash", "Screenshot", (0.5, 0.5)), 1.0)
    assert app.flash_at == 1.0
    assert app.toast == "Screenshot"


def test_right_hand_controls_when_both_are_in_view():
    left = Hand("Left", make_hand())
    right = Hand("Right", make_hand(index=True))
    assert main.pick_control_hand([left, right], "Right") is right


def test_the_only_hand_in_view_is_in_control():
    left = Hand("Left", make_hand())
    assert main.pick_control_hand([left], "Right") is left
    assert main.pick_control_hand([], "Right") is None


def test_both_hands_are_tracked_on_their_own():
    app = make_app()
    app.update([Hand("Left", make_hand()), Hand("Right", make_hand(index=True))])
    assert app.motions["Left"].predict(0) is not None
    assert app.motions["Right"].predict(0) is not None
    app.update([Hand("Right", make_hand(index=True))])
    assert app.motions["Left"].predict(0) is None
    assert app.control_hand.side == "Right"


def test_finger_counts_show_for_each_hand_once_steady():
    app = make_app()
    hands = [Hand("Left", make_hand(index=True, middle=True)), Hand("Right", make_hand(index=True))]
    app.update(hands)
    assert app.finger_counts == {}  # one detection is not enough yet
    for _ in range(3):
        app.update(hands)
    assert app.finger_counts == {"Left": 2, "Right": 1}


def test_finger_count_goes_when_the_hand_goes():
    app = make_app()
    for _ in range(3):
        app.update([Hand("Left", make_hand(index=True))])
    app.update([])
    assert app.finger_counts == {}


# Training mode and custom gestures

import custom_gestures  # noqa: E402
import training  # noqa: E402

ROCK = make_hand(index=True, pinky=True)


def rock_samples():
    return [custom_gestures.features(ROCK)] * 20


def test_t_opens_training_and_turns_control_off():
    app = make_app()
    app.control_on = True
    app.handle_key(ord("t"))
    assert app.training is not None
    assert app.control_on is False
    app.handle_key(main.ESC_KEY)
    assert app.training is None


def test_q_types_into_a_name_instead_of_quitting():
    app = make_app()
    app.handle_key(ord("t"))
    app.training.step = training.NAME
    assert app.typing() is True
    app.handle_key(ord("q"))
    assert app.training.name == "q"


def test_a_trained_gesture_is_saved_and_loaded_next_time():
    app = make_app()
    app.save_gesture("rock", "play_pause", rock_samples())
    assert app.gestures_file.exists()
    assert make_app().custom["rock"]["action"] == "play_pause"


def test_deleting_the_last_gesture():
    app = make_app()
    app.save_gesture("rock", "play_pause", rock_samples())
    app.save_gesture("wave", "volume_up", rock_samples())
    app.delete_last_gesture()
    assert list(app.custom) == ["rock"]


def test_holding_a_custom_gesture_runs_its_action_once(monkeypatch):
    clock = {"now": 0.0}
    monkeypatch.setattr(main.time, "monotonic", lambda: clock["now"])
    ran = []
    monkeypatch.setattr(main.actions, "run", ran.append)
    app = make_app()
    app.save_gesture("rock", "play_pause", rock_samples())
    app.control_on = True
    for _ in range(40):
        app.update([Hand("Right", ROCK)])
        clock["now"] += 1 / 30
    assert app.custom_name == "rock"
    assert ran == ["play_pause"]


def test_custom_gestures_do_nothing_while_control_is_off(monkeypatch):
    ran = []
    monkeypatch.setattr(main.actions, "run", ran.append)
    app = make_app()
    app.save_gesture("rock", "play_pause", rock_samples())
    for _ in range(40):
        app.update([Hand("Right", ROCK)])
    assert ran == []
