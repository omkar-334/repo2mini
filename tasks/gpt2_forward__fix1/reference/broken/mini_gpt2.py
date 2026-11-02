import math
from types import SimpleNamespace

import torch
from torch import nn
from torch.nn import functional as F


class MiniGPT2Config:
    model_type = "gpt2"
    attribute_map = {"hidden_size": "n_embd", "max_position_embeddings": "n_positions",
                     "num_attention_heads": "n_head", "num_hidden_layers": "n_layer"}

    def __init__(self, vocab_size=50257, n_positions=1024, n_embd=768, n_layer=12, n_head=12, n_inner=None,
                 activation_function="gelu_new", resid_pdrop=0.1, embd_pdrop=0.1, attn_pdrop=0.1,
                 layer_norm_epsilon=1e-5, initializer_range=0.02, bos_token_id=50256, eos_token_id=50256, **kwargs):
        self.vocab_size, self.n_positions, self.n_embd, self.n_layer, self.n_head = vocab_size, n_positions, n_embd, n_layer, n_head
        self.n_inner = n_inner
        self.activation_function = activation_function
        self.resid_pdrop, self.embd_pdrop, self.attn_pdrop = resid_pdrop, embd_pdrop, attn_pdrop
        self.layer_norm_epsilon, self.initializer_range = layer_norm_epsilon, initializer_range
        self.bos_token_id, self.eos_token_id = bos_token_id, eos_token_id
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        m = type(self).attribute_map
        if name in m:
            return getattr(self, m[name])
        raise AttributeError(name)


class Conv1D(nn.Module):
    """GPT-2 style linear layer: weight is (nx, nf), the transpose of nn.Linear."""

    def __init__(self, nf, nx):
        super().__init__()
        self.nf = nf
        self.weight = nn.Parameter(torch.empty(nx, nf))
        self.bias = nn.Parameter(torch.zeros(nf))
        nn.init.normal_(self.weight, std=0.02)

    def forward(self, x):
        return torch.addmm(self.bias, x.view(-1, x.size(-1)), self.weight).view(*x.size()[:-1], self.nf)


def gelu_new(x):
    return 0.5 * x * (1.0 + torch.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * torch.pow(x, 3.0))))


ACT = {"gelu_new": gelu_new, "gelu": F.gelu, "relu": F.relu, "tanh": torch.tanh}


class Attention(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.n_head, self.embed_dim = c.n_head, c.n_embd
        self.head_dim = c.n_embd // c.n_head
        self.c_attn = Conv1D(3 * c.n_embd, c.n_embd)
        self.c_proj = Conv1D(c.n_embd, c.n_embd)
        self.attn_dropout, self.resid_dropout = nn.Dropout(c.attn_pdrop), nn.Dropout(c.resid_pdrop)

    def _split(self, x):
        b, s, _ = x.shape
        return x.view(b, s, self.n_head, self.head_dim).transpose(1, 2)

    def forward(self, x, past=None, attention_mask=None):
        q, k, v = self.c_attn(x).split(self.embed_dim, dim=2)
        q, k, v = self._split(q), self._split(k), self._split(v)
        if past is not None:
            k, v = torch.cat([past[0], k], dim=-2), torch.cat([past[1], v], dim=-2)
        present = (k, v)
        sq, sk = q.size(-2), k.size(-2)
        scores = q @ k.transpose(-1, -2) / math.sqrt(self.embed_dim)
        causal = torch.ones(sq, sk, dtype=torch.bool, device=x.device).tril(diagonal=sk - sq)
        scores = scores.masked_fill(~causal, torch.finfo(scores.dtype).min)
        if attention_mask is not None:
            scores = scores.masked_fill(attention_mask[:, None, None, :sk] == 0, torch.finfo(scores.dtype).min)
        w = self.attn_dropout(torch.softmax(scores, dim=-1))
        out = (w @ v).transpose(1, 2).reshape(x.size(0), sq, self.embed_dim)
        return self.resid_dropout(self.c_proj(out)), present


class MLP(nn.Module):
    def __init__(self, inner, c):
        super().__init__()
        self.c_fc, self.c_proj = Conv1D(inner, c.n_embd), Conv1D(c.n_embd, inner)
        self.act, self.dropout = ACT[c.activation_function], nn.Dropout(c.resid_pdrop)

    def forward(self, x):
        return self.dropout(self.c_proj(self.act(self.c_fc(x))))


class Block(nn.Module):
    def __init__(self, c):
        super().__init__()
        inner = c.n_inner if c.n_inner is not None else 4 * c.n_embd
        self.ln_1 = nn.LayerNorm(c.n_embd, eps=c.layer_norm_epsilon)
        self.attn = Attention(c)
        self.ln_2 = nn.LayerNorm(c.n_embd, eps=c.layer_norm_epsilon)
        self.mlp = MLP(inner, c)

    def forward(self, x, past=None, attention_mask=None):
        a, present = self.attn(self.ln_1(x), past, attention_mask)
        x = x + a
        return x + self.mlp(self.ln_2(x)), present


class MiniGPT2Model(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.wte, self.wpe = nn.Embedding(c.vocab_size, c.n_embd), nn.Embedding(c.n_positions, c.n_embd)
        self.drop = nn.Dropout(c.embd_pdrop)
        self.h = nn.ModuleList([Block(c) for _ in range(c.n_layer)])
        self.ln_f = nn.LayerNorm(c.n_embd, eps=c.layer_norm_epsilon)

    def forward(self, input_ids, past_key_values=None, attention_mask=None):
        past_len = 0 if past_key_values is None else past_key_values[0][0].size(-2)
        pos = torch.arange(past_len, past_len + input_ids.size(1), device=input_ids.device)
        x = self.drop(self.wte(input_ids) + self.wpe(pos)[None])
        presents = []
        for i, blk in enumerate(self.h):
            x, p = blk(x, None if past_key_values is None else past_key_values[i], attention_mask)
            presents.append(p)
        return self.ln_f(x), tuple(presents)


class MiniGPT2LMHeadModel(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.transformer = MiniGPT2Model(config)
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)
        self.lm_head.weight = self.transformer.wte.weight

    def forward(self, input_ids, attention_mask=None, past_key_values=None, labels=None, use_cache=None):
        h, presents = self.transformer(input_ids, past_key_values, attention_mask)
        logits = self.lm_head(h)
        loss = None
        if labels is not None:
            loss = F.cross_entropy(logits[..., :-1, :].reshape(-1, logits.size(-1)), labels[..., 1:].reshape(-1))
        return SimpleNamespace(logits=logits, loss=loss, past_key_values=presents if use_cache else None)

    @torch.no_grad()
    def generate(self, input_ids, max_new_tokens=20, eos_token_id=None, use_cache=True):
        past, cur, out = None, input_ids, input_ids
        done = torch.zeros(input_ids.size(0), dtype=torch.bool, device=input_ids.device)
        for _ in range(max_new_tokens):
            if use_cache:
                r = self(cur, past_key_values=past, use_cache=True)
                past = r.past_key_values
            else:
                r = self(out)
            nxt = r.logits[:, -1].argmax(-1)
            if eos_token_id is not None:
                nxt = torch.where(done, torch.full_like(nxt, eos_token_id), nxt)
                done = done | (nxt == eos_token_id)
            out = torch.cat([out, nxt[:, None]], dim=1)
            cur = nxt[:, None]
            if eos_token_id is not None and bool(done.all()):
                break
        return out
