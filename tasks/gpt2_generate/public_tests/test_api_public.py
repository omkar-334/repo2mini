import torch
from mini_gpt2 import MiniGPT2Config, MiniGPT2LMHeadModel

KW = dict(vocab_size=100, n_positions=32, n_embd=32, n_layer=2, n_head=4, bos_token_id=1, eos_token_id=2)


def test_forward_shape():
    m = MiniGPT2LMHeadModel(MiniGPT2Config(**KW)).eval()
    out = m(torch.randint(0, 100, (2, 7)))
    assert out.logits.shape == (2, 7, 100)


def test_config_fields():
    c = MiniGPT2Config(**KW)
    assert c.n_embd == 32 and c.n_head == 4 and c.n_layer == 2 and c.n_positions == 32


def test_state_dict_has_wte():
    m = MiniGPT2LMHeadModel(MiniGPT2Config(**KW))
    assert "transformer.wte.weight" in m.state_dict()
