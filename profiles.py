"""App profiles: different gestures and voice commands for different apps.

Each profile in config.PROFILES lists the apps it is for and its own gestures
and voice commands. The "default" profile is used for every other app, and its
gestures and the main VOICE_COMMANDS work everywhere. A profile only adds to
them or changes some of them.
"""

DEFAULT = "default"


def pick_profile(app_name, profiles):
    """The first profile with a name in its app list that is part of the
    program's name ("chrome" matches "Google Chrome"), or "default".

    Only the program name is checked, not the window title, so a document
    called "knowledge base" never counts as the Edge browser.
    """
    app_name = app_name.lower()
    for name, profile in profiles.items():
        if any(app in app_name for app in profile.get("apps", [])):
            return name
    return DEFAULT


def gestures_for(name, profiles):
    """Pose name -> action for a profile, on top of the default ones."""
    gestures = dict(profiles[DEFAULT].get("gestures", {}))
    gestures.update(profiles[name].get("gestures", {}))
    return gestures


def voice_for(name, profiles, base_commands):
    """Phrase -> action for a profile, on top of the main voice commands."""
    commands = dict(base_commands)
    commands.update(profiles[DEFAULT].get("voice", {}))
    commands.update(profiles[name].get("voice", {}))
    return commands


def all_phrases(profiles, base_commands):
    """Every phrase any profile uses. The speech model listens for all of them."""
    phrases = set(base_commands)
    for profile in profiles.values():
        phrases.update(profile.get("voice", {}))
    return sorted(phrases)
