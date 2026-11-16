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
