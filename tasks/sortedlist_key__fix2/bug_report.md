Running the reference checks against this implementation fails.

Failing checks: test_fuzz_matches_original[1], test_fuzz_matches_original[2] (2 failing in total).

First assertion messages:
    assert 32 == -38
    +  where 32 = pop(-8)
    +    where pop = SortedKeyList([-14, -28, 35, 0, 22, 15, -6, -27, 29, -12, 9, 37, -40, 23, 16, -11, 17, -11, -39, 4, 18, -3, -38, -38, -17, -37, -37, -37, 13, -8, 27], key=<function <lambda> at 0x106d
    +  and   -38 = pop(-8)
    +    where pop = SortedKeyList([-14, -28, 35, 0, 22, 15, -6, -27, 29, 23, 9, 37, -40, 16, -12, 17, -11, -39, -11, 32, -38, 4, 18, -3, -17, -37, -37, -37, -8, 27, 13], key=<function <lambda> at 0x106d0
    assert -21 == 27
