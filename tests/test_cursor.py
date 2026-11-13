from cursor import Smoother, map_to_screen


def test_center_of_frame_is_center_of_screen():
    x, y = map_to_screen((0.5, 0.5), 1920, 1080, margin=0.15)
    assert abs(x - 960) < 2
    assert abs(y - 540) < 2


def test_margin_reaches_screen_edges():
    x, y = map_to_screen((0.15, 0.85), 1920, 1080, margin=0.15)
    assert x == 1
    assert abs(y - 1078) < 0.01


def test_never_lands_on_the_failsafe_corner():
    x, y = map_to_screen((0.0, 0.0), 1920, 1080, margin=0.15)
    assert (x, y) == (1, 1)
    x, y = map_to_screen((1.0, 1.0), 1920, 1080, margin=0.15)
    assert x < 1919 and y < 1079


def test_smoother_starts_at_first_point():
    assert Smoother(0.3).update((100, 100)) == (100, 100)


def test_smoother_moves_part_of_the_way():
    smoother = Smoother(0.5)
    smoother.update((0, 0))
    assert smoother.update((100, 200)) == (50, 100)


def test_smoother_reset():
    smoother = Smoother(0.5)
    smoother.update((0, 0))
    smoother.reset()
    assert smoother.update((100, 100)) == (100, 100)


def test_big_moves_get_less_smoothing():
    smoother = Smoother(0.25, fast_pixels=100)
    smoother.update((0, 0))
    assert smoother.update((200, 0)) == (200, 0)


def test_small_shakes_are_smoothed():
    smoother = Smoother(0.25, fast_pixels=100)
    smoother.update((0, 0))
    x, _ = smoother.update((4, 0))
    assert x < 2
