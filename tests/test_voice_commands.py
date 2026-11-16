"""Matching what was heard to an action, and what the app does with it."""

import pytest

import actions
import config
import main
from voice_commands import clean, find_command

COMMANDS = {"scroll up": "scroll_up", "scroll down": "scroll_down", "click": "click", "play": "play"}


def test_exact_phrase():
    assert find_command("scroll up", COMMANDS) == ("scroll up", "scroll_up")


def test_case_and_spaces_do_not_matter():
    assert find_command("  Scroll   UP ", COMMANDS) == ("scroll up", "scroll_up")


def test_phrase_inside_other_words():
    assert find_command("um scroll down please", COMMANDS) == ("scroll down", "scroll_down")


def test_unknown_words_from_vosk_are_ignored():
    assert find_command("[unk] click", COMMANDS) == ("click", "click")
    assert clean("[unk] [unk]") == ""


def test_nothing_useful_gives_none():
    assert find_command("[unk]", COMMANDS) is None
    assert find_command("hello there", COMMANDS) is None
    assert find_command("", COMMANDS) is None


def test_only_whole_words_match():
    assert find_command("display", COMMANDS) is None  # has "play" inside it


def test_longest_phrase_wins():
    commands = {"next": "next_track", "next window": "next_window"}
    assert find_command("next window", commands) == ("next window", "next_window")


@pytest.mark.parametrize("phrase, action", config.VOICE_COMMANDS.items())
def test_every_configured_phrase_maps_to_a_real_action(phrase, action):
    assert find_command(phrase, config.VOICE_COMMANDS) == (phrase, action)
    assert action in actions.known_actions() | {"control_on", "control_off"}


@pytest.mark.parametrize("os_name", ["windows", "mac"])
def test_every_voice_shortcut_exists_on_both_systems(os_name):
    for action in config.VOICE_COMMANDS.values():
        if action not in actions.SPECIAL_ACTIONS | {"control_on", "control_off"}:
            assert action in config.SHORTCUTS[os_name]


# What the app does with a phrase

def make_app(control_on=False):
    app = main.App(can_control=True)
    app.show_intro = False
    app.control_on = control_on
    return app


@pytest.fixture
def ran(monkeypatch):
    done = []
    monkeypatch.setattr(main.actions, "run", done.append)
    return done


def test_voice_starts_off():
    assert make_app().voice_on is False


def test_control_on_by_voice(ran):
    app = make_app()
    app.on_heard("control on", 1.0)
    assert app.control_on is True
    assert app.heard == ("control on", "control on", 1.0)


def test_commands_are_ignored_while_control_is_off(ran):
    app = make_app()
    app.on_heard("click", 1.0)
    assert ran == []
    assert "control is off" in app.heard[1]


def test_commands_run_while_control_is_on(ran):
    app = make_app(control_on=True)
    app.on_heard("scroll down", 1.0)
    assert ran == ["scroll_down"]
    assert app.heard == ("scroll down", "scroll down", 1.0)


def test_control_off_by_voice(ran):
    app = make_app(control_on=True)
    app.on_heard("control off", 1.0)
    assert app.control_on is False


def test_unknown_phrase_is_shown_but_does_nothing(ran):
    app = make_app(control_on=True)
    app.on_heard("[unk]", 1.0)
    assert ran == []
    assert app.heard[1] == "not a command"


def test_missing_model_keeps_voice_off(monkeypatch):
    monkeypatch.setattr(main.config, "VOSK_MODEL_PATH", "models/not_here")
    app = make_app()
    app.handle_key(ord("v"))
    assert app.voice_on is False
    assert "voice model" in app.message.lower()


class FakeListener:
    def __init__(self, model_path, phrases):
        self.status = "listening"
        self.started = False
        self.phrases_heard = []

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def take_heard(self):
        phrases, self.phrases_heard = self.phrases_heard, []
        return phrases


def test_v_toggles_voice_and_heard_phrases_run(monkeypatch, ran):
    monkeypatch.setattr(main, "VoiceListener", FakeListener)
    app = make_app(control_on=True)
    app.handle_key(ord("v"))
    assert app.voice_on is True and app.voice.started
    app.voice.phrases_heard = ["volume up"]
    app.check_voice(2.0)
    assert ran == ["volume_up"]
    app.handle_key(ord("v"))
    assert app.voice_on is False and not app.voice.started


def test_a_broken_microphone_turns_voice_off(monkeypatch):
    monkeypatch.setattr(main, "VoiceListener", FakeListener)
    app = make_app()
    app.handle_key(ord("v"))
    app.voice.status = "failed"
    app.voice.error = "no microphone"
    app.check_voice(1.0)
    assert app.voice_on is False
    assert "no microphone" in app.message
