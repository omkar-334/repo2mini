Running the reference checks against this implementation fails.

Failing checks: test_fuzz_matches_original[0], test_fuzz_matches_original[1], test_fuzz_matches_original[2] (3 failing in total).

First assertion messages:
    assert [-34, -34, -3...-35, -35, ...] == [-34, -34, -3...-35, -35, ...]
    
    Right contains 2 more items, first extra item: -38
    Use -v to get more diff
    assert [] == [32]
    
