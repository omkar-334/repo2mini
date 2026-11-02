Running the reference checks against this implementation fails.

Failing checks: test_midpoint_exact_index_takes_that_element, test_matches_numpy_values_shapes_and_dtypes[midpoint] (2 failing in total).

First assertion messages:
    AssertionError: assert np.float64(3.5) == np.float64(3.0)
    +  where np.float64(3.5) = quantile(array([1., 2., 3., 4., 5.]), 0.5, method='midpoint')
    +  and   np.float64(3.0) = <function quantile at 0x10baa8fb0>(array([1., 2., 3., 4., 5.]), 0.5, method='midpoint')
    +    where <function quantile at 0x10baa8fb0> = np.quantile
    AssertionError: ('midpoint', (6, 3), 0, [[0.2, 0.8]])
    assert False
