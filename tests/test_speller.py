from speller import Speller


def feed(speller, letter, seconds, start, hand=True, step=0.1):
    now = start
    while now < start + seconds - 1e-9:
        speller.update(letter, hand, now)
        now += step
    return now


def test_letter_is_added_after_holding():
    speller = Speller(hold_seconds=1.0, space_seconds=1.5)
    feed(speller, "A", 0.5, 0.0)
    assert speller.word == ""
    feed(speller, "A", 1.0, 0.5)
    assert speller.word == "A"


def test_holding_longer_does_not_repeat():
    speller = Speller(hold_seconds=1.0, space_seconds=1.5)
    feed(speller, "A", 5.0, 0.0)
    assert speller.word == "A"


def test_same_letter_twice_needs_a_break():
    speller = Speller(hold_seconds=1.0, space_seconds=1.5)
    now = feed(speller, "L", 1.2, 0.0)
    now = feed(speller, None, 0.3, now)
    feed(speller, "L", 1.2, now)
    assert speller.word == "LL"


def test_flicker_does_not_add_letters():
    speller = Speller(hold_seconds=1.0, space_seconds=1.5)
    now = 0.0
    for letter in "UVUVUVUVUV":
        now = feed(speller, letter, 0.2, now)
    assert speller.word == ""


def test_hand_away_adds_one_space():
    speller = Speller(hold_seconds=1.0, space_seconds=1.5)
    now = feed(speller, "H", 1.2, 0.0)
    feed(speller, None, 5.0, now, hand=False)
    assert speller.word == "H "


def test_no_space_at_the_start():
    speller = Speller(hold_seconds=1.0, space_seconds=1.5)
    feed(speller, None, 3.0, 0.0, hand=False)
    assert speller.word == ""


def test_backspace_and_clear():
    speller = Speller(hold_seconds=1.0, space_seconds=1.5)
    speller.word = "HEY"
    speller.backspace()
    assert speller.word == "HE"
    speller.clear()
    assert speller.word == ""


def test_word_is_capped():
    speller = Speller(hold_seconds=0.1, space_seconds=1.5, max_length=5)
    speller.word = "ABCDE"
    speller.add("F")
    assert speller.word == "BCDEF"


def test_progress():
    speller = Speller(hold_seconds=1.0, space_seconds=1.5)
    speller.update("A", True, 0.0)
    assert speller.progress(0.5) == 0.5
