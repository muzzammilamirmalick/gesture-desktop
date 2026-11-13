import pytest

import asl_letters
from tests.sample_hands import make_hand, rotate, scale

ALL_BENT = ("index", "middle", "ring", "pinky")

LETTER_HANDS = {
    "A": make_hand(thumb="side"),
    "B": make_hand(index=True, middle=True, ring=True, pinky=True),
    "C": make_hand(bent=ALL_BENT, thumb="c"),
    "D": make_hand(index=True, thumb="touch_middle"),
    "E": make_hand(),
    "F": make_hand(middle=True, ring=True, pinky=True, thumb="pinch"),
    "I": make_hand(pinky=True),
    "L": make_hand(index=True, thumb="out"),
    "O": make_hand(bent=ALL_BENT, thumb="o"),
    "U": make_hand(index=True, middle=True),
    "V": make_hand(index=True, middle=True, spread=True),
    "W": make_hand(index=True, middle=True, ring=True),
    "Y": make_hand(pinky=True, thumb="out"),
}


def test_every_supported_letter_has_a_sample():
    assert "".join(sorted(LETTER_HANDS)) == asl_letters.SUPPORTED_LETTERS


@pytest.mark.parametrize("letter", sorted(LETTER_HANDS))
def test_letter(letter):
    assert asl_letters.classify_letter(LETTER_HANDS[letter]) == letter


@pytest.mark.parametrize("letter", sorted(LETTER_HANDS))
def test_letter_far_from_camera(letter):
    assert asl_letters.classify_letter(scale(LETTER_HANDS[letter], 0.6)) == letter


@pytest.mark.parametrize("letter", ["B", "L", "U", "V", "W", "Y"])
def test_letter_with_tilted_hand(letter):
    assert asl_letters.classify_letter(rotate(LETTER_HANDS[letter], 25)) == letter


def test_open_palm_with_thumb_out_is_not_b():
    hand = make_hand(index=True, middle=True, ring=True, pinky=True, thumb="out")
    assert asl_letters.classify_letter(hand) is None


def test_no_hand():
    assert asl_letters.classify_letter(None) is None


def test_finger_states():
    states = asl_letters.finger_states(make_hand(index=True, bent=("middle",)))
    assert states == {"index": "straight", "middle": "bent", "ring": "curled", "pinky": "curled"}
