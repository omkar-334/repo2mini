Running the reference checks against this implementation fails.

Failing checks: test_logits_match, test_logits_match_other_shapes (2 failing in total).

First assertion messages:
    +    and   tensor([[[ 3.8393e-02, -3.9751e-02, -1.2124e-01,  ..., -1.3520e-01,\n          -3.2419e-02, -6.3614e-02],\n         [ 8....1.6047e-01],\n         [-7.0608e-02,  1.2307e-02,  1.1604e-01,  ..
    +      where CausalLMOutputWithCrossAttentions(loss=None, logits=tensor([[[ 3.8393e-02, -3.9751e-02, -1.2124e-01,  ..., -1.3520e-01...y_values=DynamicCache(layers=[DynamicLayer, DynamicLayer]), hidden
    +    and   tensor([[[ 3.8316e-02, -3.9755e-02, -1.2131e-01,  ..., -1.3520e-01,\n          -3.2386e-02, -6.3506e-02],\n         [ 8....1.6047e-01],\n         [-7.0554e-02,  1.2347e-02,  1.1605e-01,  ..
    +      where namespace(logits=tensor([[[ 3.8316e-02, -3.9755e-02, -1.2131e-01,  ..., -1.3520e-01,\n          -3.2386e-02, -6.3506e-0...,  1.2347e-02,  1.1605e-01,  ...,  6.9960e-02,\n           4.6435
    assert False
    +  where False = <built-in method allclose of type object at 0x10bd25f28>(tensor([[[ 1.3040e-01, -9.2767e-03, -2.1592e-01, -6.1918e-02, -5.8645e-02,\n           8.3503e-02,  5.2578e-02, -3.6592...2,  
