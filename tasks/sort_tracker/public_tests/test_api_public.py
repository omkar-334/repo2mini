import numpy as np
from mini_sort import SORTTracker


def test_defaults_are_stored():
    t = SORTTracker()
    assert t.track_activation_threshold == 0.25 and t.minimum_consecutive_frames == 3 and t.minimum_iou_threshold == 0.3


def test_returns_one_id_per_detection():
    t = SORTTracker()
    ids = t.update(np.array([[0, 0, 10, 10], [50, 50, 60, 60]], float))
    assert ids.shape == (2,) and (ids == -1).all()


def test_object_gets_an_id_after_three_frames():
    t = SORTTracker()
    box = np.array([[0.0, 0, 20, 20]])
    out = [int(t.update(box)[0]) for _ in range(4)]
    assert out[0] == -1 and out[-1] >= 0
