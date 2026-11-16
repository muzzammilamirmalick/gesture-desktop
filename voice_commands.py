"""Turns what the microphone heard into an action name from config.VOICE_COMMANDS."""

UNKNOWN_WORD = "[unk]"


def clean(text):
    """Lower case, single spaces, and without Vosk's "[unk]" for words it did not know."""
    words = [word for word in text.lower().split() if word != UNKNOWN_WORD]
    return " ".join(words)


def find_command(text, commands):
    """Return (phrase, action) for the command in `text`, or None.

    An exact match wins. Otherwise the longest phrase that appears as whole
    words, so "um scroll down" still works, and "scroll down" is never
    mistaken for a shorter phrase hiding inside it.
    """
    heard = clean(text)
    if not heard:
        return None
    if heard in commands:
        return heard, commands[heard]
    padded = f" {heard} "
    for phrase in sorted(commands, key=len, reverse=True):
        if f" {phrase} " in padded:
            return phrase, commands[phrase]
    return None
