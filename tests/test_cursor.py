from cursor import CursorPredictor, map_to_screen


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


def predictor():
    return CursorPredictor(alpha=0.6, beta=0.2, max_ahead=0.08)


def test_nothing_to_predict_before_the_first_detection():
    assert predictor().predict(0.0) is None


def test_starts_at_the_first_point():
    cursor = predictor()
    cursor.observe((100, 100), 0.0)
    assert cursor.predict(0.0) == (100, 100)


def test_still_hand_stays_still():
    cursor = predictor()
    for step in range(30):
        cursor.observe((500, 300), step / 30)
    x, y = cursor.predict(1.05)
    assert abs(x - 500) < 1 and abs(y - 300) < 1


def test_keeps_moving_between_detections():
    # A hand moving right at 600 px per second, detected 30 times a second.
    cursor = predictor()
    for step in range(30):
        cursor.observe((step * 20, 0), step / 30)
    at_detection = cursor.predict(29 / 30)[0]
    halfway_to_next = cursor.predict(29 / 30 + 1 / 60)[0]
    assert halfway_to_next > at_detection + 5


def test_catches_up_with_a_moving_hand():
    cursor = predictor()
    for step in range(30):
        cursor.observe((step * 20, 0), step / 30)
    assert abs(cursor.predict(29 / 30)[0] - 29 * 20) < 25


def test_prediction_stops_if_detections_stop():
    cursor = predictor()
    for step in range(30):
        cursor.observe((step * 20, 0), step / 30)
    soon = cursor.predict(29 / 30 + 0.08)[0]
    much_later = cursor.predict(29 / 30 + 5.0)[0]
    assert much_later == soon


def test_shaky_hand_is_calmer_than_the_raw_points():
    cursor = predictor()
    raw_jumps = []
    smooth_jumps = []
    last_raw = last_smooth = None
    for step in range(60):
        point = (500 + (6 if step % 2 else -6), 300)
        cursor.observe(point, step / 30)
        smooth = cursor.predict(step / 30)
        if last_raw:
            raw_jumps.append(abs(point[0] - last_raw[0]))
            smooth_jumps.append(abs(smooth[0] - last_smooth[0]))
        last_raw, last_smooth = point, smooth
    assert sum(smooth_jumps) < sum(raw_jumps) * 0.7


def test_reset():
    cursor = predictor()
    cursor.observe((100, 100), 0.0)
    cursor.reset()
    assert cursor.predict(1.0) is None
