Running the reference checks against this implementation fails.

Failing checks: test_ids_start_at_zero_and_first_frame_is_unconfirmed_even_with_one_frame_minimum, test_ids_match_original_on_random_scenes[0], test_ids_match_original_on_random_scenes[1], test_ids_match_original_on_random_scenes[2] (7 failing in total).

First assertion messages:
    assert [-1, -1, -1, 0, 0] == [-1, -1, 0, 0, 0]
    
    At index 2 diff: -1 != 0
    Use -v to get more diff
    AssertionError: ({'lost_track_buffer': 5, 'frame_rate': 30.0, 'track_activation_threshold': 0.0, 'minimum_consecutive_frames': 2, ...}, 1)
    assert [-1] == [0]
