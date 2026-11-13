"""Camera thread logic with a fake capture, so no webcam is needed."""

import camera


class FakeCapture:
    def __init__(self, frames):
        self.frames = list(frames)

    def read(self):
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
    cam.new_frame = camera.threading.Condition()
    return cam


def test_reads_newest_frame_and_stops_at_the_end():
    cam = make_camera(["a", "b", "c"])
    cam.start()
    number, frame = cam.read(0)
    assert frame in {"a", "b", "c"}
    while frame is not None:
        last = frame
        number, frame = cam.read(number, timeout=0.5)
    assert last == "c"


def test_never_returns_the_same_frame_twice():
    cam = make_camera(["a"])
    cam.start()
    number, frame = cam.read(0)
    assert frame == "a"
    assert cam.read(number, timeout=0.2) == (number, None)
