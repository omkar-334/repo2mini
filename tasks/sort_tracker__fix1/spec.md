# Task: mini SORT tracker

Implement `solution/mini_sort.py`, a compact standalone re-implementation of the SORT multi object tracker from the Roboflow `trackers` library. You may use NumPy and SciPy. Do **not** import `trackers` or `supervision`.

Interface:

* `SORTTracker(lost_track_buffer=30, frame_rate=30.0, track_activation_threshold=0.25, minimum_consecutive_frames=3, minimum_iou_threshold=0.3)`, with the same parameter names and defaults as the original, stored as attributes of the same names. It also has `maximum_frames_without_update` (derived, see the original) and `tracks` (the list of live tracklets).
* `update(xyxy, confidence=None)` takes the detections of one frame, boxes as an `(N, 4)` array of `[x_min, y_min, x_max, y_max]` and optional confidences, and returns an integer array of length `N` with the tracker id of every detection, using `-1` for detections that have no confirmed track.
* `reset()` clears all tracks and restarts the id counter.

Behaviour to match the original:

* Constant velocity Kalman prediction for every live track each frame, then IoU association with the Hungarian algorithm (`scipy.optimize.linear_sum_assignment`), accepting a match only if its IoU reaches `minimum_iou_threshold`.
* Unmatched detections start a new track only if their confidence reaches `track_activation_threshold`. A missing `confidence` means every detection is fully confident.
* The original's rules for when a track is confirmed, when it gets an id and which id, when a detection is reported as `-1`, and when a track is removed (including how `lost_track_buffer` and `frame_rate` set the number of missed frames a track survives, and what `lost_track_buffer=0` means).
* `ValueError` for a negative `lost_track_buffer` and for a `frame_rate` that is not finite and positive.
