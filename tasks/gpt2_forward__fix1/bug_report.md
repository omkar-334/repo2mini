Running the reference checks against this implementation fails.

Failing checks: test_logits_match, test_logits_match_other_shapes, test_relu_activation_variant (3 failing in total).

First assertion messages:
    +    where <built-in method allclose of type object at 0x10c60df28> = torch.allclose
    +    and   tensor([[[ 1.3040e-01, -9.2767e-03, -2.1592e-01, -6.1918e-02, -5.8645e-02,\n           8.3503e-02,  5.2578e-02, -3.6592...2,  7.2462e-02,  1.4546e-02, -6.6141e-02,\n          -6.5526e-02, -
    +      where CausalLMOutputWithCrossAttentions(loss=None, logits=tensor([[[ 1.3040e-01, -9.2767e-03, -2.1592e-01, -6.1918e-02, -5.8...icCache(layers=[DynamicLayer, DynamicLayer, DynamicLayer]), hidden
    +    and   tensor([[[ 1.3040e-01, -9.2767e-03, -2.1592e-01, -6.1918e-02, -5.8645e-02,\n           8.3503e-02,  5.2578e-02, -3.6592...2,  7.2382e-02,  1.4789e-02, -6.6217e-02,\n          -6.5051e-02, -
    +      where namespace(logits=tensor([[[ 1.3040e-01, -9.2767e-03, -2.1592e-01, -6.1918e-02, -5.8645e-02,\n           8.3503e-02,  5....17e-02,\n          -6.5051e-02, -8.2093e-02,  4.6437e-02,  7.8443
    assert False
