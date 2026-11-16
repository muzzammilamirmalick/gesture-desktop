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
    ("close_window", "windows", ("ctrl", "w")),
    ("show_desktop", "windows", ("win", "d")),
    ("screenshot", "windows", ("win", "printscreen")),
    ("close_window", "mac", ("command", "w")),
    ("screenshot", "mac", ("command", "shift", "3")),
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


def test_mac_show_desktop_is_f11():
    with mock.patch("pyautogui.press") as press:
        actions.press_shortcut("show_desktop", "mac")
    press.assert_called_once_with("f11")


def test_uses_the_current_os_by_default():
    with mock.patch.object(actions, "OS_NAME", "mac"), mock.patch("pyautogui.hotkey") as hotkey:
        actions.press_shortcut("close_window")
    hotkey.assert_called_once_with("command", "w")


def test_windows_needs_no_input_permission():
    assert permissions.can_control_input("Windows") is True


def test_camera_help_mentions_the_right_settings():
    assert "Privacy & Security" in permissions.camera_help("Darwin")
    assert "desktop apps" in permissions.camera_help("Windows")


def test_named_actions_send_the_right_input():
    sent = []
    with mock.patch.object(actions, "OS_NAME", "windows"), \
         mock.patch("pyautogui.click", lambda: sent.append("click")), \
         mock.patch("pyautogui.scroll", lambda amount: sent.append(f"scroll {amount}")), \
         mock.patch("pyautogui.press", sent.append), \
         mock.patch("pyautogui.hotkey", lambda *keys: sent.append("+".join(keys))):
        actions.scroller.reset()
        for action in ["click", "scroll_up", "scroll_down", "volume_up", "next_window", "play"]:
            actions.run(action)
    notches = config.SCROLL_NOTCHES * 120
    assert sent == [
        "click", f"scroll {notches}", f"scroll {-notches}",
        "volumeup", "volumeup", "alt+tab", "playpause",
    ]
