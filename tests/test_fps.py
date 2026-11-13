from fps import FpsCounter


def test_steady_frames():
    counter = FpsCounter()
    for frame in range(60):
        fps = counter.tick(frame / 30)
    assert round(fps) == 30


def test_first_tick_reports_zero():
    assert FpsCounter().tick(0.0) == 0.0


def test_one_slow_frame_does_not_crash_the_number():
    counter = FpsCounter()
    for frame in range(30):
        counter.tick(frame / 30)
    fps = counter.tick(29 / 30 + 0.5)
    assert fps > 20
