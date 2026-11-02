import math

import numpy as np
from scipy.optimize import linear_sum_assignment


def iou_matrix(a, b):
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    a, b = np.asarray(a, float), np.asarray(b, float)
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.clip(rb - lt, 0, None).prod(axis=2)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    union = area_a[:, None] + area_b[None, :] - inter
    return np.where(union > 0, inter / np.where(union > 0, union, 1), 0.0)


class Tracklet:
    """Constant velocity Kalman filter over [x1, y1, x2, y2, vx1, vy1, vx2, vy2]."""

    def __init__(self, bbox):
        self.x = np.concatenate([np.asarray(bbox, float), np.zeros(4)])
        self.P = np.eye(8)
        self.F = np.eye(8)
        self.F[:4, 4:] = np.eye(4)
        self.H = np.hstack([np.eye(4), np.zeros((4, 4))])
        self.Q, self.R = np.eye(8) * 0.01, np.eye(4) * 0.1
        self.tracker_id = -1
        self.time_since_update = 0
        self.number_of_successful_updates = 1

    def predict(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        self.time_since_update += 1

    def update(self, bbox):
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ (np.asarray(bbox, float) - self.H @ self.x)
        self.P = (np.eye(8) - K @ self.H) @ self.P
        self.time_since_update = 0
        self.number_of_successful_updates += 1

    def bbox(self):
        return self.x[:4].copy()


class SORTTracker:
    def __init__(self, lost_track_buffer=30, frame_rate=30.0, track_activation_threshold=0.25,
                 minimum_consecutive_frames=3, minimum_iou_threshold=0.3):
        if lost_track_buffer < 0:
            raise ValueError("lost_track_buffer must be non negative")
        if not math.isfinite(frame_rate) or frame_rate <= 0:
            raise ValueError("frame_rate must be finite and positive")
        self.maximum_frames_without_update = 0 if lost_track_buffer == 0 else int(frame_rate / 30.0 * lost_track_buffer)
        self.minimum_consecutive_frames = minimum_consecutive_frames
        self.minimum_iou_threshold = minimum_iou_threshold
        self.track_activation_threshold = track_activation_threshold
        self.tracks = []
        self._next_track_id = 0

    def reset(self):
        self.tracks = []
        self._next_track_id = 0

    def update(self, xyxy, confidence=None):
        boxes = np.asarray(xyxy, float).reshape(-1, 4)
        conf = np.ones(len(boxes), np.float32) if confidence is None else np.asarray(confidence, float)
        if not self.tracks and len(boxes) == 0:
            return np.array([], dtype=int)
        for t in self.tracks:
            t.predict()
        predicted = np.array([t.bbox() for t in self.tracks]) if self.tracks else np.empty((0, 4))
        iou = iou_matrix(predicted, boxes)
        matched, free_dets = {}, set(range(len(boxes)))
        if len(self.tracks) and len(boxes):
            rows, cols = linear_sum_assignment(iou, maximize=True)
            for r, c in zip(rows, cols):
                if iou[r, c] >= self.minimum_iou_threshold:
                    self.tracks[r].update(boxes[c])
                    matched[c] = self.tracks[r]
                    free_dets.discard(c)
        for c in sorted(free_dets):
            if conf[c] >= self.track_activation_threshold:
                self.tracks.append(Tracklet(boxes[c]))
        self.tracks = [t for t in self.tracks
                       if t.time_since_update <= self.maximum_frames_without_update
                       and (t.number_of_successful_updates >= self.minimum_consecutive_frames or t.time_since_update == 0)]
        ids = np.full(len(boxes), -1, dtype=int)
        for c, t in matched.items():
            if t.number_of_successful_updates >= self.minimum_consecutive_frames:
                if t.tracker_id == -1:
                    t.tracker_id = self._next_track_id
                    self._next_track_id += 1
                ids[c] = t.tracker_id
        return ids
