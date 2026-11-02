# Task: mini GPT-2 with KV cache and greedy generation

Implement `solution/mini_gpt2.py`, a small standalone re-implementation of the GPT-2 model from the Hugging Face Transformers library. Use PyTorch only. Do **not** import `transformers` (or any other library that contains GPT-2).

Follow the conventions of the original library so that weights from the original model can be loaded into yours:

* `MiniGPT2Config(vocab_size, n_positions, n_embd, n_layer, n_head, n_inner=None, activation_function="gelu_new", resid_pdrop, embd_pdrop, attn_pdrop, layer_norm_epsilon, initializer_range, bos_token_id, eos_token_id, **kwargs)`. Use the same field names and the same defaults as the original `GPT2Config`, including its aliases `hidden_size`, `max_position_embeddings`, `num_attention_heads` and `num_hidden_layers`. `n_inner=None` means `4 * n_embd`. `activation_function` accepts at least the original's names `gelu_new`, `gelu`, `relu` and `tanh`.
* `MiniGPT2LMHeadModel(config)` with a `transformer` submodule and an `lm_head`. The parameter names (the keys of `state_dict()`) must be identical to those of the original `GPT2LMHeadModel`, and the weight layouts must be identical too, so that `mini.load_state_dict(hf.state_dict(), strict=False)` loads every parameter. The `lm_head` weight is tied to the token embedding.
* `forward(input_ids, attention_mask=None, past_key_values=None, labels=None, use_cache=None)` returns an object with `.logits` of shape `(batch, seq, vocab_size)`, and `.loss` when `labels` is given (next token cross entropy with the usual one position shift).
* The causal mask and attention scaling must match the original. Dropout must be disabled in `eval()` mode.

Keep the implementation compact and readable.

## Additional requirements for this task

* `forward` accepts `past_key_values` and `use_cache`. With `use_cache=True` the output has `.past_key_values`, a tuple with one `(key, value)` pair per layer, each of shape `(batch, n_head, seq_len, head_dim)`. When `past_key_values` is given, `input_ids` holds only the new tokens and the position ids continue after the cached length.
* `generate(input_ids, max_new_tokens=20, eos_token_id=None, use_cache=True)` performs greedy decoding and returns a tensor of shape `(batch, prompt_len + generated)` that starts with the prompt. It must produce the same tokens as the original library's greedy `generate`. If `eos_token_id` is given, generation for a sequence stops after it emits that token, and the whole call stops early when every sequence is finished.
* Decoding with the cache must give the same tokens as decoding without it (`use_cache=False`, which recomputes the full sequence each step).
