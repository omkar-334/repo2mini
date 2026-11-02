Running the reference checks against this implementation fails.

Failing checks: test_attributes_match_original_defaults_and_derived_budget, test_ids_match_original_on_random_scenes[0], test_ids_match_original_on_random_scenes[1], test_ids_match_original_on_random_scenes[5] (4 failing in total).

First assertion messages:
    AssertionError: (1, 5.0)
    assert 0 == 1
    +  where 0 = <mini_sort.SORTTracker object at 0x116d68530>.maximum_frames_without_update
    +  and   1 = <trackers.core.sort.tracker.SORTTracker object at 0x116d68650>.maximum_frames_without_update
    AssertionError: ({'lost_track_buffer': 1, 'frame_rate': 15.0, 'track_activation_threshold': 0.0, 'minimum_consecutive_frames': 1, ...}, 27)
    assert [-1] == [0]
