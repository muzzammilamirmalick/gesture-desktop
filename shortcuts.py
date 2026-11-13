"""Picks the right keyboard shortcut for the operating system."""

import platform

import config


def detect_os(system=None):
    """Return "mac" or "windows" for the shortcut sections in config.py."""
    system = system or platform.system()
    if system == "Darwin":
        return "mac"
    # Not tested on Linux, but most Linux desktops use Alt+Tab too.
    return "windows"


def shortcut_for(action, os_name):
    return config.SHORTCUTS[os_name][action]


def shortcut_actions():
    return set(config.SHORTCUTS["windows"]) | set(config.SHORTCUTS["mac"])
