"""Per-OS shortcuts. pyautogui is stubbed, so these run the same on any OS."""

from unittest import mock

import pyautogui
import pytest

import actions
import config
import mac_keys
import permissions
import shortcuts


def test_detects_mac():
    assert shortcuts.detect_os("Darwin") == "mac"


def test_detects_windows():
    assert shortcuts.detect_os("Windows") == "windows"


def test_both_os_sections_have_the_same_actions():
    assert set(config.SHORTCUTS["windows"]) == set(config.SHORTCUTS["mac"])


def test_every_shortcut_key_is_a_real_key():
    known = set(pyautogui.KEY_NAMES) | set(mac_keys.MEDIA_KEYS)
    for keys in list(config.SHORTCUTS["windows"].values()) + list(config.SHORTCUTS["mac"].values()):
        for key in keys:
            assert key in known, key


@pytest.mark.parametrize("action, os_name, expected", [
    ("next_window", "windows", ("alt", "tab")),
    ("previous_window", "windows", ("shift", "alt", "tab")),
    ("minimize", "windows", ("win", "down")),
    ("next_window", "mac", ("command", "tab")),
    ("previous_window", "mac", ("shift", "command", "tab")),
    ("minimize", "mac", ("command", "m")),
])
def test_hotkeys_per_os(action, os_name, expected):
    with mock.patch("pyautogui.hotkey") as hotkey:
        actions.press_shortcut(action, os_name)
    hotkey.assert_called_once_with(*expected)


@pytest.mark.parametrize("action, key", [
    ("play_pause", "playpause"),
    ("volume_up", "volumeup"),
    ("volume_down", "volumedown"),
])
def test_windows_media_keys_use_pyautogui(action, key):
    with mock.patch("pyautogui.press") as press:
        actions.press_shortcut(action, "windows")
    press.assert_called_once_with(key)


@pytest.mark.parametrize("action, key", [
    ("play_pause", "mac_play_pause"),
    ("volume_up", "mac_volume_up"),
    ("volume_down", "mac_volume_down"),
])
def test_mac_media_keys_use_mac_events(action, key):
    with mock.patch("mac_keys.press_media_key") as press_media, mock.patch("pyautogui.press") as press:
        actions.press_shortcut(action, "mac")
    press_media.assert_called_once_with(key)
    press.assert_not_called()


def test_run_uses_the_current_os():
    with mock.patch.object(actions, "OS_NAME", "mac"), mock.patch("pyautogui.hotkey") as hotkey:
        actions.run("next_window")
    hotkey.assert_called_once_with("command", "tab")


def test_windows_needs_no_input_permission():
    assert permissions.can_control_input("Windows") is True


def test_camera_help_mentions_the_right_settings():
    assert "Privacy & Security" in permissions.camera_help("Darwin")
    assert "desktop apps" in permissions.camera_help("Windows")
