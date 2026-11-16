from pose_trigger import PoseTrigger


def test_fires_once_after_the_hold():
    trigger = PoseTrigger(0.5)
    fired = [trigger.update("rock", True, t / 10) for t in range(20)]
    assert fired.count(True) == 1
    assert fired.index(True) == 5


def test_passing_through_a_pose_does_not_fire():
    trigger = PoseTrigger(0.5)
    assert not trigger.update("rock", True, 0.0)
    assert not trigger.update("rock", True, 0.3)
    assert not trigger.update("peace", True, 0.4)
    assert not trigger.update("peace", True, 0.8)


def test_making_it_again_fires_again():
    trigger = PoseTrigger(0.5)
    trigger.update("rock", True, 0.0)
    assert trigger.update("rock", True, 0.6)
    trigger.update(None, False, 0.7)
    trigger.update("rock", True, 0.8)
    assert trigger.update("rock", True, 1.4)


def test_poses_without_an_action_never_fire_or_show_a_ring():
    trigger = PoseTrigger(0.5)
    assert not trigger.update("fist", False, 0.0)
    assert not trigger.update("fist", False, 1.0)
    assert trigger.progress(1.0) == 0.0


def test_progress_fills_while_holding():
    trigger = PoseTrigger(0.5)
    trigger.update("rock", True, 0.0)
    assert trigger.progress(0.25) == 0.5
