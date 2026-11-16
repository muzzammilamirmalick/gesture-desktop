"""Picking an app profile and what each profile changes."""

import pytest

import active_window
import actions
import config
import main
from profiles import DEFAULT, all_phrases, gestures_for, pick_profile, voice_for
from tests.sample_hands import make_hand
from tracking import Hand

PROFILES = {
    "browser": {"apps": ["chrome", "edge"], "gestures": {"thumbs_up": "forward"}, "voice": {"go back": "back"}},
    "media": {"apps": ["spotify"], "gestures": {"two_fingers": "play_pause"}, "voice": {"next": "next_track"}},
    "default": {"apps": [], "gestures": {"thumbs_up": "volume_up", "thumbs_down": "volume_down"}, "voice": {}},
}
BASE_VOICE = {"click": "click"}


@pytest.mark.parametrize("app, profile", [
    ("chrome", "browser"),
    ("google chrome", "browser"),  # the Mac name
    ("msedge", "browser"),  # the Windows name
    ("Spotify", "media"),
    ("notepad", DEFAULT),
    ("", DEFAULT),
])
def test_picks_the_profile_for_the_app(app, profile):
    assert pick_profile(app, PROFILES) == profile


def test_profile_gestures_add_to_and_replace_the_defaults():
    assert gestures_for("browser", PROFILES) == {"thumbs_up": "forward", "thumbs_down": "volume_down"}
    assert gestures_for(DEFAULT, PROFILES) == PROFILES["default"]["gestures"]


def test_profile_voice_adds_to_the_main_commands():
    assert voice_for("browser", PROFILES, BASE_VOICE) == {"click": "click", "go back": "back"}
    assert voice_for(DEFAULT, PROFILES, BASE_VOICE) == {"click": "click"}


def test_the_speech_model_listens_for_every_profile_phrase():
    assert all_phrases(PROFILES, BASE_VOICE) == ["click", "go back", "next"]


def test_the_real_config_has_a_default_and_every_action_exists():
    assert DEFAULT in config.PROFILES
    known = actions.known_actions() | {"control_on", "control_off"}
    for profile in config.PROFILES.values():
        for action in list(profile.get("gestures", {}).values()) + list(profile.get("voice", {}).values()):
            assert action in known
            if action not in actions.SPECIAL_ACTIONS:
                assert action in config.SHORTCUTS["windows"] and action in config.SHORTCUTS["mac"]


def test_reading_the_active_app_never_crashes():
    name, title = active_window.active_app()
    assert isinstance(name, str) and isinstance(title, str)


# In the app

def make_app():
    app = main.App(can_control=True)
    app.show_intro = False
    return app


def test_switches_profile_with_the_app_in_front():
    app = make_app()
    app.check_active_app(10.0, read_app=lambda: ("chrome", "news - google chrome"))
    assert app.profile == "browser"
    app.check_active_app(20.0, read_app=lambda: ("spotify", "spotify"))
    assert app.profile == "media"


def test_keeps_the_profile_when_our_own_window_is_in_front():
    app = make_app()
    app.check_active_app(10.0, read_app=lambda: ("chrome", ""))
    app.check_active_app(20.0, read_app=lambda: ("python", config.WINDOW_NAME.lower()))
    assert app.profile == "browser"


def test_only_checks_every_so_often():
    app = make_app()
    calls = []
    app.check_active_app(10.0, read_app=lambda: calls.append(1) or ("chrome", ""))
    app.check_active_app(10.1, read_app=lambda: calls.append(1) or ("chrome", ""))
    assert len(calls) == 1


def test_the_same_pose_does_different_things_in_different_apps(monkeypatch):
    clock = {"now": 0.0}
    monkeypatch.setattr(main.time, "monotonic", lambda: clock["now"])
    ran = []
    monkeypatch.setattr(main.actions, "run", ran.append)
    thumbs_up = [Hand("Right", make_hand(thumb="up"))]
    app = make_app()
    app.control_on = True
    for profile in ["browser", DEFAULT]:
        app.set_profile(profile)
        for _ in range(40):
            app.update(thumbs_up)
            clock["now"] += 1 / 30
        app.update([])
    assert ran == ["forward", "volume_up"]


def test_voice_commands_follow_the_profile(monkeypatch):
    ran = []
    monkeypatch.setattr(main.actions, "run", ran.append)
    app = make_app()
    app.control_on = True
    app.on_heard("next tab", 1.0)
    assert ran == []
    assert app.heard[1] == "not for this app"
    app.set_profile("browser")
    app.on_heard("next tab", 2.0)
    assert ran == ["next_tab"]
