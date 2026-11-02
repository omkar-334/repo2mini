Running the reference checks against this implementation fails.

Failing checks: test_basic_right_closed, test_int_bins_adjust_lowest_edge_like_original, test_left_closed_adjusts_the_upper_edge, test_include_lowest_first_label (8 failing in total).

First assertion messages:
    AssertionError: assert (['(-0.001, 5....'(5.0, 10.0]'] == ['(-0.001, 5....'(5.0, 10.0]']
    
    Use -v to get more diff and [np.int8(0), ...), np.int8(1)] == [np.int64(0),... np.int64(-1)]
    
    At index 2 diff: np.int8(0) != np.int64(1)
    Use -v to get more diff)
