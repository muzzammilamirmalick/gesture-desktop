from debounce import GestureStabilizer, TriggerGate


def feed(stabilizer, gestures):
    return [stabilizer.update(g) for g in gestures]


def test_stabilizer_waits_for_enough_frames():
    stabilizer = GestureStabilizer(frames_needed=3)
    assert feed(stabilizer, ["pinch", "pinch", "pinch"]) == [None, None, "pinch"]


def test_stabilizer_ignores_a_one_frame_flicker():
    stabilizer = GestureStabilizer(frames_needed=3)
    feed(stabilizer, ["fist"] * 3)
    assert feed(stabilizer, ["pinch", "fist", "fist"]) == ["fist", "fist", "fist"]


def test_gate_starts_disarmed():
    gate = TriggerGate(triggers={"pinch"}, reset_gestures={"fist"})
    assert gate.update("pinch") is False


def test_gate_fires_once_after_reset():
    gate = TriggerGate(triggers={"pinch"}, reset_gestures={"fist"})
    gate.update("fist")
    results = [gate.update("pinch") for _ in range(5)]
    assert results == [True, False, False, False, False]


def test_gate_needs_reset_before_firing_again():
    gate = TriggerGate(triggers={"pinch"}, reset_gestures={"fist"})
    gate.update("fist")
    assert gate.update("pinch") is True
    gate.update("point")
    assert gate.update("pinch") is False
    gate.update("fist")
    assert gate.update("pinch") is True


def test_non_trigger_gestures_keep_gate_armed():
    gate = TriggerGate(triggers={"pinch"}, reset_gestures={"fist"})
    gate.update("fist")
    gate.update("point")
    gate.update("no_hand")
    assert gate.update("pinch") is True


def test_disarm():
    gate = TriggerGate(triggers={"pinch"}, reset_gestures={"fist"})
    gate.update("fist")
    gate.disarm()
    assert gate.update("pinch") is False


def test_rearm_pose_only_rearms_its_own_trigger():
    gate = TriggerGate(triggers={"pinch", "thumbs_up"}, reset_gestures={"fist"}, rearm={"pinch": {"point"}})
    gate.update("fist")
    assert gate.update("pinch") is True
    gate.update("point")
    assert gate.update("thumbs_up") is False
    assert gate.update("pinch") is True
