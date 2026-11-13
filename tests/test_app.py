"""App state and keys, without a camera or window."""

import main
from tests.sample_hands import make_hand


def make_app():
    app = main.App(can_control=True)
    return app


def test_control_starts_off():
    assert make_app().control_on is False


def test_space_toggles_control():
    app = make_app()
    app.handle_key(ord(" "))
    assert app.control_on is True


def test_no_permission_keeps_control_off():
    app = main.App(can_control=False)
    app.handle_key(ord(" "))
    assert app.control_on is False
    assert "permission" in app.message


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


def test_help_key_toggles_panel(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "HELP_SEEN_FILE", tmp_path / ".help_seen")
    app = make_app()
    app.show_help = True
    app.handle_key(ord("h"))
    assert app.show_help is False
    assert (tmp_path / ".help_seen").exists()


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
    monkeypatch.setattr(main.actions, "run", sent.append)
    app = make_app()
    app.control_on = True
    double_blink(app, monkeypatch)
    assert sent == ["play_pause"]


def test_double_blink_does_nothing_when_control_is_off(monkeypatch):
    sent = []
    monkeypatch.setattr(main.actions, "run", sent.append)
    app = make_app()
    double_blink(app, monkeypatch)
    assert sent == []
    assert "control is off" in app.fired


def test_missing_face_model_turns_eyes_off(monkeypatch):
    monkeypatch.setattr(main.config, "FACE_MODEL_PATH", "models/not_here.task")
    app = make_app()
    app.eyes_on = True
    assert main.open_face_tracker(app) is None
    assert app.eyes_on is False
    assert "face model" in app.message
