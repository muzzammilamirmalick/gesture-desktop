"""Media keys on Mac.

pyautogui's playpause and volume keys do nothing on macOS, so this posts the
same system event a real keyboard's media key sends. Only imported on a Mac.
"""

# Key codes from Apple's ev_keymap.h
MEDIA_KEYS = {
    "mac_volume_up": 0,
    "mac_volume_down": 1,
    "mac_play_pause": 16,
}

SYSTEM_DEFINED_EVENT = 14
MEDIA_KEY_SUBTYPE = 8


def media_key_event(code, key_down):
    # These libraries come with pyautogui on Mac (pyobjc).
    import AppKit

    flags = 0xA00 if key_down else 0xB00
    data = (code << 16) | ((0xA if key_down else 0xB) << 8)
    return AppKit.NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
        SYSTEM_DEFINED_EVENT, (0, 0), flags, 0, 0, 0, MEDIA_KEY_SUBTYPE, data, -1
    )


def press_media_key(name):
    import Quartz

    code = MEDIA_KEYS[name]
    for key_down in (True, False):
        Quartz.CGEventPost(0, media_key_event(code, key_down).CGEvent())
