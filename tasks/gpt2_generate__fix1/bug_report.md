Running the reference checks against this implementation fails.

Failing checks: test_cache_equals_no_cache, test_greedy_matches_original, test_logits_match_with_cache_from_original (3 failing in total).

First assertion messages:
    assert False
    +  where False = <built-in method equal of type object at 0x10a8c5f28>(tensor([[48, 31, 43,  6, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65],\n        [80, 14, 81, 56, 21, 21, 21, 21, 21, 21, 21, 21, 21, 2
    +    where <built-in method equal of type object at 0x10a8c5f28> = torch.equal
    +    and   tensor([[48, 31, 43,  6, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65],\n        [80, 14, 81, 56, 21, 21, 21, 21, 21, 21, 21, 21, 21, 21]]) = generate(tensor([[48, 31, 43,  6, 65],\n        [80, 
    +      where generate = MiniGPT2LMHeadModel(\n  (transformer): MiniGPT2Model(\n    (wte): Embedding(100, 32)\n    (wpe): Embedding(32, 32)\n    (d... eps=1e-05, elementwise_affine=True, bias=True)\n  
    +    and   tensor([[48, 31, 43,  6, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65],\n        [80, 14, 81, 56, 21, 21, 82, 82, 82, 82, 82, 82, 82, 82]]) = generate(tensor([[48, 31, 43,  6, 65],\n        [80, 
