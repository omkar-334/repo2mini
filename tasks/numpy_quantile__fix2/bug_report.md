Running the reference checks against this implementation fails.

Failing checks: test_matches_numpy_values_shapes_and_dtypes[hazen] (1 failing in total).

First assertion messages:
    AssertionError: ('hazen', (6, 3, 5), 0, [[0.2, 0.8]])
    assert False
    +  where False = <function allclose at 0x1072282b0>(array([[[[[-0.71564626,  0.23185727, -0.1473818 , -0.24622773,\n           -0.85346597],\n          [-1.83216399, -0.599... ,\n            1.1602459
    +    where <function allclose at 0x1072282b0> = np.allclose
