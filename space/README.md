---
title: Repo2Mini
emoji: 🧩
colorFrom: indigo
colorTo: blue
sdk: static
pinned: false
license: apache-2.0
short_description: Does more repo context help Beam rebuild a library?
---

# Repo2Mini

Repo2Mini asks a model to rebuild a small standalone version of a real library subsystem, following the original's conventions, and scores the result with hidden tests. The main thing that changes between runs is how much of the original repository the model sees and how it gets it.

Built for Build with Beam. The subject model is Beam 1.0 (`Beam-1.0-501B-A23B`) through the Reflection API. A fifth model, Nemotron 3 Ultra 550B (free tier on OpenRouter), ran on a small subset (see Limits). Three OpenAI models ran on the same grid for comparison: `gpt-4.1` (no reasoning), `gpt-5.2` and `gpt-6-astra` (both at low reasoning effort).

## Tasks

| Task | Library | What the model builds | Oracle |
| --- | --- | --- | --- |
| gpt2_forward | Transformers | GPT-2 forward pass | Logits and loss compared with the installed Hugging Face model |
| gpt2_generate | Transformers | KV cache and greedy generation | Generated tokens compared with the installed Hugging Face model |
| sortedlist_core | python-sortedcontainers | SortedList | Random operation sequences compared with the installed package, plus its internal layout |
| sortedlist_key | python-sortedcontainers | SortedList with key functions | Same, including SortedKeyList |
| numpy_quantile | NumPy | quantile and percentile with all 13 interpolation methods | Values, shapes and dtypes compared with the installed `np.quantile` |
| pandas_cut | pandas | The binning logic of `pd.cut` | Codes and label strings compared with the installed `pd.cut` |
| sort_tracker | Roboflow trackers | The SORT multi object tracker | Tracker ids compared with the installed `SORTTracker` on random scenes |

Settings, all scored by the same hidden tests (parity, behavior, API compatibility) after up to two revision rounds against public tests:

* **Write from scratch.** L0 (no repository text), L2 (the relevant files), L5 (a broader slice, capped at 150K tokens).
* **Agentic.** No repository text. The model gets read only tools (`list_dir`, `grep`, `read_file`, `git_log`, jailed to the repo) and a budget of 20 tool turns, then writes its answer.
* **Bug fix.** 14 variants (two per task). The reference solution with one injected bug, plus a bug report that lists the failing checks. L0 and L2.
* **Long context.** The relevant files placed in the middle of a haystack of other code: about 240K tokens for all models, about 600K tokens for Beam only (see limits).

A solution that imports, calls or executes the original library is disqualified and scores 0. The check reads the code's syntax tree, so mentioning a library in a comment or docstring is fine.

## Results

Mean hidden pass rate, and the share of runs that pass every hidden test (low or default reasoning effort, 2 to 3 samples per cell, 1 for long context):

| Setting | gpt-6-astra | gpt-5.2 | Beam | gpt-4.1 |
| --- | --- | --- | --- | --- |
| Write from scratch (L0, L2, L5) | 0.967 (88%) | 0.802 (31%) | 0.735 (20%) | 0.670 (15%) |
| Agentic, tools only | 1.000 (100%) | 0.891 (27%) | 0.388 (0%) | 0.589 (0%) |
| Bug fix | 1.000 (100%) | 0.942 (79%) | **0.960 (79%)** | 0.941 (66%) |
| Long context (about 240K tokens, Beam also 600K) | 1.000 (100%) | 0.867 (57%) | 0.862 (7%) | 0.597 (0%) |

**Where Beam does well**

* **Bug fixing.** Beam matches `gpt-5.2` (0.960 vs 0.942, and the same 79% of runs fully correct) and is ahead of `gpt-4.1`.
* **Using context it is given.** When the relevant files are in the prompt (L2) Beam reaches 0.832, level with `gpt-5.2` (0.852). Its gain from no context to L2 is the largest of any model (+0.22 vs +0.11 for `gpt-5.2`).
* **Very long context.** Beam shows no drop from L2 (0.832) to a 240K token haystack (0.817), and scored 0.907 at 600K tokens (7 runs). `gpt-4.1` falls from 0.724 to 0.597 at 240K.
* **Cost.** See below. Beam is by far the cheapest per unit of quality.

**Where Beam does not**

* **It does not lead.** `gpt-6-astra` passes nearly everything. On writing from scratch Beam is behind `gpt-5.2`, with fewer runs passing every hidden test (20% vs 31%).
* **Agentic use is its weakest setting.** Beam makes few tool calls (7.7 per run on average vs 16.5 for `gpt-5.2`), and in 4 of 15 runs it disqualified itself by loading the original library's source with `exec` or importing from it instead of writing code. Early in the project it also tried to deliver its answer through a tool called `final`, which does not exist. I added an error message and a no-files reminder that help every model equally.
* **Format compliance.** In 13 of 78 early runs Beam left out the opening code fence after the `FILE:` header, and no other model did. The parser is now tolerant and those runs were rescored, but their revision rounds ran before the fix.
* **With the source in context, it can copy it.** On `sortedlist_key` it reproduced the original almost verbatim (about 950 to 1,050 non-empty lines) and failed a compactness check I set at 700 lines.
* **Distraction.** Adding a broad slice of the repo (L5) instead of just the relevant files (L2) cost Beam about 0.07, while `gpt-6-astra` lost nothing.
* **Reasoning effort.** `reasoning_effort=medium` used about 36% more completion tokens than low for Beam with no measurable gain on the first four tasks (0.771 vs 0.759).

## Nemotron 3 Ultra (free tier, small subset)

NVIDIA's `nemotron-3-ultra-550b-a55b:free` has a 1M token context like Beam and a similar size. The free tier allows 50 requests per day, so it ran only on the write from scratch setting at L0 and L2, 7 tasks, 1 sample, low effort (14 runs, no errors). Mean hidden pass rate was 0.60 (L0 0.50, L2 0.71), with 2 of 14 runs passing every hidden test. Beam on the same L0 and L2 cells scored 0.62 and 0.83, so Nemotron is behind Beam here, but one sample per cell is far too little to call a gap. It was not run on agentic, bug fix or long context. Two other candidates were not usable: `inkling:free` is restricted to agentic harnesses (HTTP 403), and Groq's free tier (8,000 tokens per minute) is smaller than most prompts.

## Cost

Cost uses list prices on the logged tokens, with cached input at the cached rate. OpenAI rates are from its pricing page (per 1M tokens, input / cached / output): `gpt-6-astra` $10 / $1 / $50 (above 272K input tokens $20 / $2 / $75), `gpt-5.2` $1.75 / $0.175 / $14, `gpt-4.1` $2 / $0.50 / $8. Beam is $0.25 in and $1 out per 1M tokens from its OpenRouter listing, which is an estimate: the direct Reflection API was a free beta and nothing was billed.

| Setting | Metric | Beam | gpt-4.1 | gpt-5.2 | gpt-6-astra |
| --- | --- | --- | --- | --- | --- |
| Write from scratch | Cost per run | $0.022 | $0.098 | $0.116 | $0.344 |
| Write from scratch | Cost per fully passing run | $0.107 | $0.661 | $0.375 | $0.390 |
| Bug fix | Cost per run | $0.007 | $0.043 | $0.055 | $0.183 |
| Bug fix | Cost per fully passing run | $0.009 | $0.066 | $0.070 | $0.183 |
| Long context | Cost per run | $0.145 | $0.647 | $0.490 | $2.440 |

### Quality per dollar

Pass rate points per dollar is the sum of hidden pass rates over all runs divided by total list price spend (higher is better). Cost per fully passing run is total spend divided by runs that passed every hidden test (lower is better). Read both: points per dollar rewards cheap and mediocre models (Beam agentic scores 33 with zero fully passing runs), while cost per fully passing run ignores partial credit.

| Setting | Metric | Beam | gpt-4.1 | gpt-5.2 | gpt-6-astra | Best |
| --- | --- | --- | --- | --- | --- | --- |
| Write from scratch | Points per dollar | **33.7** | 6.8 | 6.9 | 2.8 | Beam |
| Write from scratch | $ per fully passing run | **$0.107** | $0.661 | $0.375 | $0.390 | Beam |
| Bug fix | Points per dollar | **135.0** | 21.7 | 17.0 | 5.5 | Beam |
| Bug fix | $ per fully passing run | **$0.009** | $0.066 | $0.070 | $0.183 | Beam |
| Agentic | Points per dollar | **33.5** | 4.4 | 5.7 | 4.3 | Beam (but 0 fully passing runs) |
| Agentic | $ per fully passing run | none | none | $0.587 | **$0.230** | gpt-6-astra |
| Long context (240K) | Points per dollar | **6.0** | 0.9 | 1.8 | 0.4 | Beam |
| Long context (240K) | $ per fully passing run | $2.03 | none | **$0.86** | $2.44 | gpt-5.2 |

Beam is the best on quality per dollar in three of four settings on both metrics, by 5x to 8x over the nearest model. It is not the best where full correctness matters and it rarely achieves it: agentic (no fully passing run) and long context (1 of 14 runs). Caveats: Beam's price is an OpenRouter list price estimate and nothing was billed, Beam cached input is billed at the full input rate (so its cost is if anything overstated), and quality per dollar says nothing about whether a cheap answer is good enough for your use. Nemotron 3 Ultra was free, so its cost is zero and the metric is undefined.

## Corrections made during the project

* A hidden test required `forward` to return no cache unless asked. The spec never said that and the real model returns one by default, so I removed it and rescored the saved solutions without rerunning any model (7 of 36 `gpt2_generate` runs went from failing to passing).
* My "must not mention the original library" tests were plain substring checks. They failed 49 honest solutions (across all models) that wrote "mini re-implementation of `np.quantile`" in a docstring. I replaced them with the syntax tree check described above and rescored all 500 saved runs. That check disqualified 4 Beam runs.
* Revision rounds first failed with HTTP 400 for Beam, because it needs earlier `reasoning_content` sent back. I fixed the pipeline and reran the affected cells.
* The first `sort_tracker` L2 and L5 runs used a wrong source path and gave the models an empty context. I set those 16 runs aside (under `results/invalid_runs`) and reran them.
* Six runs failed with transient connection errors and were rerun.
* `gpt-6-astra` cannot use function tools together with reasoning on the chat completions endpoint, so its agentic and tool conversations use the Responses API.

## Limits

One run per configuration and 2 to 3 samples per cell (1 for long context), so many differences between models are within noise. `gpt-6-astra` and `gpt-5.2` have 2 samples per cell, Beam and `gpt-4.1` 3 on the first four tasks. Only low reasoning effort for the OpenAI reasoning models. The 600K token test ran for Beam only: `gpt-4.1` was rejected by a 500K tokens per minute limit on my organization, and the other two models were not run there to limit cost. My own scoring thresholds (the 700 line compactness check, the 20 turn tool budget). The repository slices come from main branches while the installed packages (for example NumPy 2.5.4, pandas 3.1.0, trackers 2.6.1) were the oracles, so small version drift is possible. Hidden tests are not published, to limit leakage. Familiarity is confounded: `gpt-6-astra` solves `sortedcontainers` from memory with no context, so `sort_tracker` is the cleaner test of context use.
