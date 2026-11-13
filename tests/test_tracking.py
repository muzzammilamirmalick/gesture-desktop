"""Background detection. A fake model checks the plumbing, then one quick run of the real hand model."""

import time

import numpy as np

import config
import tracking


class FakeModel:
    def close(self):
        pass


class FakeDetector(tracking.BackgroundDetector):
    """Records what it was sent instead of running a model."""

    def build(self, model_path, delegate):
        if delegate == tracking.BaseOptions.Delegate.GPU:
            raise NotImplementedError("no GPU in this build")
        self.sent = []
        return FakeModel()

    def read(self, result):
        return result

    def send(self, image, timestamp_ms):
        self.sent.append(timestamp_ms)


def make_detector():
    return FakeDetector("unused", detection_width=320, use_gpu=True)


def frame():
    return np.zeros((480, 640, 3), np.uint8)


def test_falls_back_to_cpu_when_gpu_fails():
    assert make_detector().delegate_name == "CPU"


def test_skips_frames_while_busy():
    detector = make_detector()
    assert detector.submit(frame(), 1.0) is True
    assert detector.submit(frame(), 1.01) is False
    assert len(detector.sent) == 1


def test_sends_again_once_a_result_is_back():
    detector = make_detector()
    detector.submit(frame(), 1.0)
    detector.on_result("hand", None, 1000)
    assert detector.submit(frame(), 1.03) is True


def test_stops_waiting_if_a_result_never_comes():
    detector = make_detector()
    detector.submit(frame(), 1.0)
    assert detector.submit(frame(), 1.0 + tracking.BUSY_TIMEOUT_SECONDS + 0.01) is True


def test_latest_gives_the_newest_result_and_a_rising_number():
    detector = make_detector()
    assert detector.latest() == (0, None)
    detector.on_result("first", None, 1)
    detector.on_result("second", None, 2)
    assert detector.latest() == (2, "second")


def test_timestamps_always_go_up():
    detector = make_detector()
    for _ in range(3):
        detector.submit(frame(), 5.0)  # same clock reading every time
        detector.on_result(None, None, 0)
    assert detector.sent == sorted(set(detector.sent))


def test_shrinks_big_frames_only():
    assert tracking.shrink(frame(), 320).shape[:2] == (240, 320)
    small = np.zeros((120, 160, 3), np.uint8)
    assert tracking.shrink(small, 320) is small


def test_real_hand_model_runs_in_the_background():
    hands = tracking.HandTracker(config.MODEL_PATH, 320, use_gpu=True)
    try:
        started = time.monotonic()
        hands.submit(frame(), started)
        assert time.monotonic() - started < 0.05  # submit hands off, it does not wait
        deadline = started + 3
        while hands.latest()[0] == 0 and time.monotonic() < deadline:
            time.sleep(0.01)
        number, landmarks = hands.latest()
        assert number == 1
        assert landmarks is None  # a black frame has no hand in it
    finally:
        hands.close()
