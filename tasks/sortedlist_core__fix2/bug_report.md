Running the reference checks against this implementation fails.

Failing checks: test_contents_and_queries_match[0], test_contents_and_queries_match[1], test_contents_and_queries_match[2] (3 failing in total).

First assertion messages:
    assert (28 == 28 and 28 == 31)
    +  where 28 = bisect_left(-53)
    +    where bisect_left = SortedList([-60, -60, -60, -60, -60, -59, -59, -59, -59, -59, -59, -58, -58, -58, -57, -57, -56, -56, -56, -56, -56, -...2, 52, 52, 53, 53, 53, 54, 54, 54, 54, 55, 55, 55, 55,
    +  and   28 = bisect_left(-53)
    +    where bisect_left = SortedList([-60, -60, -60, -60, -60, -59, -59, -59, -59, -59, -59, -58, -58, -58, -57, -57, -56, -56, -56, -56, -56, -...2, 52, 52, 53, 53, 53, 54, 54, 54, 54, 55, 55, 55, 55,
    +  and   28 = bisect_right(-53)
