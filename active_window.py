"""Which app is in front right now, so the app can switch profiles.

Returns the program name (like "chrome" or "spotify") and the window title,
both lower case. Uses the operating system directly, nothing extra to install.
"""

import ctypes
import platform
from ctypes import wintypes
from pathlib import Path

# Lets us ask Windows for another program's file name without extra rights.
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def windows_active_app():
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    window = user32.GetForegroundWindow()
    if not window:
        return "", ""

    title = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(window, title, 256)

    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(window, ctypes.byref(process_id))
    process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id.value)
    name = ""
    if process:
        path = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)):
            name = Path(path.value).stem  # "C:\\...\\chrome.exe" -> "chrome"
        kernel32.CloseHandle(process)
    return name.lower(), title.value.lower()


def mac_active_app():
    from AppKit import NSWorkspace  # comes with pyautogui on Mac (pyobjc)

    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return (str(app.localizedName()).lower() if app else ""), ""


def active_app():
    """(program name, window title) of the app in front, or ("", "") if unknown."""
    try:
        if platform.system() == "Windows":
            return windows_active_app()
        if platform.system() == "Darwin":
            return mac_active_app()
    except Exception:
        pass  # never let this break the app, we just keep the current profile
    return "", ""
