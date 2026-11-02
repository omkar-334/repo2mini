Running the reference checks against this implementation fails.

Failing checks: test_int_bins_adjust_lowest_edge_like_original, test_left_closed_adjusts_the_upper_edge, test_codes_labels_and_errors_match_pandas[0], test_codes_labels_and_errors_match_pandas[1] (6 failing in total).

First assertion messages:
    AssertionError: assert (['(0.995, 2.6...(4.333, 6.0]'] == ['(1.0, 2.667....333, 6.005]']
    
    At index 0 diff: '(0.995, 2.667]' != '(1.0, 2.667]'
    Use -v to get more diff)
    AssertionError: assert (['[1.0, 2.667....333, 6.005)'] == ['[0.995, 2.6...[4.333, 6.0)']
    
