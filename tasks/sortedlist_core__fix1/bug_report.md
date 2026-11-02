Running the reference checks against this implementation fails.

Failing checks: test_sequential_add_splits_like_original, test_deletes_merge_like_original, test_update_rebuild_vs_incremental_like_original (3 failing in total).

First assertion messages:
    assert ([1000, 1000, ...00, 1000, ...] == [1000, 1000, ...00, 1000, ...]
    
    At index 7 diff: 1000 != 2000
    Left contains one more item: 1000
    Use -v to get more diff)
    assert ([999, 500, 1] == [1500]
