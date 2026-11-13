"""Builds a word from letters held in front of the camera."""


class Speller:
    """Adds a letter once it has been held steady, and a space when the hand leaves.

    To type the same letter twice, drop the shape (or your hand) and sign it again.
    """

    def __init__(self, hold_seconds, space_seconds, max_length=24):
        self.hold_seconds = hold_seconds
        self.space_seconds = space_seconds
        self.max_length = max_length
        self.word = ""
        self.letter = None
        self.letter_since = 0.0
        self.letter_added = False
        self.hand_gone_since = None

    def update(self, letter, hand_seen, now):
        """Feed the current letter (or None). Returns the letter just added, if any."""
        self.track_hand(hand_seen, now)
        if letter != self.letter:
            self.letter = letter
            self.letter_since = now
            self.letter_added = False
        if letter and not self.letter_added and now - self.letter_since >= self.hold_seconds:
            self.letter_added = True
            self.add(letter)
            return letter
        return None

    def track_hand(self, hand_seen, now):
        if hand_seen:
            self.hand_gone_since = None
            return
        if self.hand_gone_since is None:
            self.hand_gone_since = now
        elif now - self.hand_gone_since >= self.space_seconds:
            if self.word and not self.word.endswith(" "):
                self.add(" ")

    def add(self, text):
        self.word = (self.word + text)[-self.max_length:]

    def progress(self, now):
        """How far through the hold the current letter is, from 0 to 1."""
        if not self.letter or self.letter_added:
            return 0.0
        return min(1.0, (now - self.letter_since) / self.hold_seconds)

    def backspace(self):
        self.word = self.word[:-1]

    def clear(self):
        self.word = ""
