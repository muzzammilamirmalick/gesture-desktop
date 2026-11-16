"""Features, the k-nearest-neighbour classifier, and saving to a file."""

import random

import pytest

from custom_gestures import GestureClassifier, features, hand_distance, load, save
from tests.sample_hands import make_hand, rotate, scale

ROCK = make_hand(index=True, pinky=True)
PEACE = make_hand(index=True, middle=True, spread=True)
FIST = make_hand()


def shifted(points, dx, dy):
    return [(x + dx, y + dy) for x, y in points]


def jitter(points, amount, seed):
    rng = random.Random(seed)
    return [(x + rng.uniform(-amount, amount), y + rng.uniform(-amount, amount)) for x, y in points]


def mirrored(points):
    return [(1 - x, y) for x, y in points]


def samples_of(points, count=20):
    return [features(jitter(points, 0.004, seed)) for seed in range(count)]


def trained():
    classifier = GestureClassifier(k=5, max_distance=0.35)
    classifier.set_samples({
        "rock": {"action": "play_pause", "samples": samples_of(ROCK)},
        "peace": {"action": "screenshot", "samples": samples_of(PEACE)},
    })
    return classifier


def test_features_ignore_where_the_hand_is():
    assert hand_distance(features(ROCK), features(shifted(ROCK, 0.2, -0.1))) == pytest.approx(0, abs=1e-9)


def test_features_ignore_how_big_the_hand_is():
    assert hand_distance(features(ROCK), features(scale(ROCK, 0.5))) == pytest.approx(0, abs=1e-9)


def test_a_left_hand_matches_the_same_pose_trained_with_the_right():
    left = features(mirrored(ROCK), side="Left")
    assert hand_distance(features(ROCK), left) == pytest.approx(0, abs=1e-9)


def test_3d_points_work_too():
    flat = features(ROCK)
    with_depth = features([(x, y, 0.0) for x, y in ROCK])
    assert hand_distance(flat, with_depth) == pytest.approx(0, abs=1e-9)


def test_recognizes_each_trained_gesture():
    classifier = trained()
    assert classifier.classify(features(jitter(ROCK, 0.004, 99))) == "rock"
    assert classifier.classify(features(jitter(PEACE, 0.004, 99))) == "peace"


def test_recognizes_it_somewhere_else_in_the_picture_and_further_away():
    assert trained().classify(features(scale(shifted(ROCK, -0.2, 0.1), 0.6))) == "rock"


def test_a_slight_tilt_still_matches():
    assert trained().classify(features(rotate(ROCK, 8))) == "rock"


def test_a_pose_that_was_never_trained_is_nothing():
    assert trained().classify(features(FIST)) is None


def test_a_pose_that_differs_in_one_finger_is_not_a_match():
    assert trained().classify(features(make_hand(index=True))) is None


def test_upside_down_is_a_different_pose():
    assert trained().classify(features(rotate(ROCK, 180))) is None


def test_no_samples_means_nothing():
    assert GestureClassifier().classify(features(ROCK)) is None


def test_majority_of_the_nearest_wins():
    classifier = GestureClassifier(k=3, max_distance=1.0)
    near = features(ROCK)
    classifier.samples = [("a", near), ("b", near), ("b", near), ("a", features(PEACE))]
    assert classifier.classify(near) == "b"


def test_save_and_load_keep_everything(tmp_path):
    path = tmp_path / "gestures.json"
    gestures = {"rock": {"action": "play_pause", "samples": samples_of(ROCK, 3)}}
    save(path, gestures)
    loaded = load(path)
    assert list(loaded) == ["rock"]
    assert loaded["rock"]["action"] == "play_pause"
    assert hand_distance(loaded["rock"]["samples"][0], gestures["rock"]["samples"][0]) < 1e-3


def test_load_with_no_file_is_empty(tmp_path):
    assert load(tmp_path / "missing.json") == {}


def test_a_broken_file_is_ignored(tmp_path):
    path = tmp_path / "gestures.json"
    path.write_text("{not json")
    assert load(path) == {}
