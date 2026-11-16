"""Camera thread logic with a fake capture, so no webcam is needed."""

import threading
import time

import camera


class FakeCapture:
    def __init__(self, frames):
        self.frames = list(frames)

    def read(self):
        time.sleep(0.01)
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self):
        pass


def make_camera(frames):
    cam = camera.Camera.__new__(camera.Camera)
    cam.capture = FakeCapture(frames)
    cam.frame = None
    cam.frame_number = 0
    cam.running = False
    cam.new_frame = threading.Condition()
    cam.rate = camera.FpsCounter()
    cam.fps = 0.0
    return cam


def wait_until_stopped(cam):
    deadline = time.monotonic() + 2
    while not cam.stopped() and time.monotonic() < deadline:
        time.sleep(0.01)


def test_latest_never_waits():
    cam = make_camera(["a"])
    started = time.monotonic()
    assert cam.latest() == (0, None)
    assert time.monotonic() - started < 0.05


def test_keeps_only_the_newest_frame():
    cam = make_camera(["a", "b", "c"])
    cam.start()
    wait_until_stopped(cam)
    assert cam.latest() == (3, "c")


def test_reports_when_the_camera_stops():
    cam = make_camera(["a"])
    cam.start()
    assert not cam.stopped()
    wait_until_stopped(cam)
    assert cam.stopped()
