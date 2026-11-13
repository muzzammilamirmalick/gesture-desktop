"""App state and keys, without a camera or window."""

import main
from tests.sample_hands import make_hand


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
    app.update(make_hand(pinky=True, thumb="out"))
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


def eye_scores(closed):
    names = [
        "eyeLookOutLeft", "eyeLookInLeft", "eyeLookUpLeft",
        "eyeLookOutRight", "eyeLookInRight", "eyeLookUpRight",
    ]
    scores = dict.fromkeys(names, 0.05)
    scores["eyeBlinkLeft"] = scores["eyeBlinkRight"] = 0.9 if closed else 0.05
    return scores


def double_blink(app, monkeypatch):
    clock = {"now": 0.0}
    monkeypatch.setattr(main.time, "monotonic", lambda: clock["now"])
    for closed, frames in [(False, 5), (True, 4), (False, 6), (True, 4), (False, 5)]:
        for _ in range(frames):
            app.update_eyes(eye_scores(closed))
            clock["now"] += 1 / 30


def test_eyes_start_off():
    assert make_app().eyes_on is False


def test_e_toggles_eyes():
    app = make_app()
    app.handle_key(ord("e"))
    assert app.eyes_on is True


def test_double_blink_plays_or_pauses_when_control_is_on(monkeypatch):
    sent = []
    monkeypatch.setattr(main.actions, "press_shortcut", sent.append)
    app = make_app()
    app.control_on = True
    double_blink(app, monkeypatch)
    assert sent == ["play_pause"]


def test_double_blink_does_nothing_when_control_is_off(monkeypatch):
    sent = []
    monkeypatch.setattr(main.actions, "press_shortcut", sent.append)
    app = make_app()
    double_blink(app, monkeypatch)
    assert sent == []
    assert "control is off" in app.toast


def test_missing_face_model_turns_eyes_off(monkeypatch):
    monkeypatch.setattr(main.config, "FACE_MODEL_PATH", "models/not_here.task")
    app = make_app()
    app.eyes_on = True
    assert main.open_face_tracker(app) is None
    assert app.eyes_on is False
    assert "face model" in app.message.lower()
