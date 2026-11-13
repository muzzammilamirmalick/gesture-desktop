"""Startup checks for the permissions the app needs."""

import ctypes
import platform

MAC_PERMISSION_HELP = """
This app cannot control the mouse and keyboard yet.

On Mac, open System Settings > Privacy & Security and turn on the app you
run this from (Terminal, iTerm or VS Code) under:
  - Accessibility (needed to move the mouse and press keys)
  - Input Monitoring
  - Camera

Then quit that app completely and open it again so the change takes effect.
The camera view still works, but CONTROL ON stays disabled until this is done.
"""

CAMERA_HELP = {
    "Darwin": "On Mac, allow your terminal under System Settings > Privacy & Security > Camera, then restart it.",
    "Windows": "On Windows, turn on Settings > Privacy & security > Camera > Let desktop apps access your camera.",
}


def mac_is_trusted():
    """Ask macOS whether this process has Accessibility permission."""
    services = ctypes.cdll.LoadLibrary(
        "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
    )
    services.AXIsProcessTrusted.restype = ctypes.c_bool
    return services.AXIsProcessTrusted()


def can_control_input(system=None):
    system = system or platform.system()
    if system != "Darwin":
        return True  # Windows does not need a special permission
    return mac_is_trusted()


def camera_help(system=None):
    return CAMERA_HELP.get(system or platform.system(), "")
