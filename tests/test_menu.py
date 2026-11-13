import pytest

from menu import PalmHold, RadialMenu, angle_from_top

ITEMS = ["a", "b", "c", "d"]


def open_menu(center=(0.6, 0.5)):
    menu = RadialMenu(ITEMS, radius=0.3, dead_zone=0.08)
    menu.open(center, aspect=4 / 3, now=0.0)
    return menu


@pytest.mark.parametrize("offset, angle", [
    ((0, -1), 0),
    ((1, 0), 90),
    ((0, 1), 180),
    ((-1, 0), 270),
])
def test_angle_is_clockwise_from_the_top(offset, angle):
    assert angle_from_top((0, 0), offset) == pytest.approx(angle)


@pytest.mark.parametrize("offset, item", [
    ((0, -0.2), "a"),   # up
    ((0.2, 0), "b"),    # right
    ((0, 0.2), "c"),    # down
    ((-0.2, 0), "d"),   # left
    ((0.1, -0.15), "a"),  # a bit right of up is still the top wedge
])
def test_pointing_picks_the_wedge_in_that_direction(offset, item):
    menu = open_menu()
    x, y = menu.center
    menu.point_at((x + offset[0], y + offset[1]))
    assert menu.chosen_item() == item


def test_middle_of_the_menu_picks_nothing():
    menu = open_menu()
    x, y = menu.center
    menu.point_at((x + 0.03, y))
    assert menu.chosen_item() is None


def test_menu_is_moved_in_from_the_edges_to_fit():
    menu = open_menu(center=(0.05, 0.95))
    assert menu.center == pytest.approx((0.3, 0.7))
    menu = open_menu(center=(1.3, 0.1))
    assert menu.center == pytest.approx((4 / 3 - 0.3, 0.3))


def test_menu_keeps_clear_of_the_header_and_hint_bar():
    menu = RadialMenu(ITEMS, radius=0.3, dead_zone=0.08, top_margin=0.2, bottom_margin=0.1)
    menu.open((0.6, 0.0), aspect=4 / 3, now=0.0)
    assert menu.center[1] == pytest.approx(0.5)
    menu.open((0.6, 1.0), aspect=4 / 3, now=0.0)
    assert menu.center[1] == pytest.approx(0.6)


def test_wedge_position_points_the_right_way():
    menu = open_menu()
    x, y = menu.center
    top = menu.wedge_position(0, 0.2)
    right = menu.wedge_position(1, 0.2)
    assert top == pytest.approx((x, y - 0.2))
    assert right == pytest.approx((x + 0.2, y))


def test_close():
    menu = open_menu()
    menu.close()
    assert not menu.is_open


def hold(palm, steps, holding=True, start=0.0, step=0.1):
    return [palm.update(holding, start + i * step) for i in range(steps)]


def test_palm_hold_fires_after_the_hold_time():
    palm = PalmHold(0.5)
    results = hold(palm, 8)
    assert results.index(True) == 5
    assert results.count(True) == 1


def test_short_palm_does_not_fire():
    palm = PalmHold(0.5)
    hold(palm, 3)
    palm.update(False, 0.3)
    assert True not in hold(palm, 3, start=0.4)


def test_palm_must_drop_before_firing_again():
    palm = PalmHold(0.5)
    hold(palm, 20)
    palm.update(False, 2.1)
    assert True in hold(palm, 8, start=2.2)


def test_palm_progress():
    palm = PalmHold(0.5)
    palm.update(True, 0.0)
    assert palm.progress(0.25) == pytest.approx(0.5)
