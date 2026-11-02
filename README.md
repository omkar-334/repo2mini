# Repo2Mini

Does more repo context help Beam rebuild a real library? Repo2Mini asks a model to write a small standalone version of a real library subsystem, then scores it with hidden tests that compare it against the installed original package. The variable is how much of the original repository the model sees and how it gets it.

Built for the Build with Beam challenge. Subject model: `Beam-1.0-501B-A23B` through the Reflection API. Peers: `gpt-4.1`, `gpt-5.2`, `gpt-6-astra`, and a small subset with Nemotron 3 Ultra.

* Results page: https://huggingface.co/spaces/omkar334/repo2mini
* Run data (solutions, per run logs, task specs, public tests): https://huggingface.co/datasets/omkar334/repo2mini-results
* Contest thread: https://huggingface.co/reflection/Beam-1.0-501B-A23B/discussions/5

## Headline results

Mean hidden pass rate (share of runs passing every hidden test in brackets), low or default reasoning effort.

| Setting | GPT-6 Astra | GPT-5.2 | Beam | GPT-4.1 |
| --- | --- | --- | --- | --- |
| Write from scratch (L0, L2, L5) | 0.967 (88%) | 0.802 (31%) | 0.735 (20%) | 0.670 (15%) |
| Agentic, tools only | 1.000 (100%) | 0.891 (27%) | 0.388 (0%) | 0.589 (0%) |
| Bug fix (14 variants) | 1.000 (100%) | 0.942 (79%) | 0.960 (79%) | 0.941 (66%) |
| Long context (240K tokens) | 1.000 (100%) | 0.867 (57%) | 0.862 (7%) | 0.597 (0%) |

Beam is mid pack on quality and the cheapest by a wide margin. Cost per fully passing bug fix at list price: Beam $0.009, GPT-5.2 $0.070, GPT-6 Astra $0.183. Beam's price is the OpenRouter listing and was not billed (the direct API was a free beta). The full discussion, including where Beam is weak (agentic use, rarely fully correct at long context), is in the Space README.

## What is in this repository

| Path | Content |
| --- | --- |
| `src/repo2mini/providers.py` | One chat interface over OpenAI compatible endpoints (Reflection, OpenAI, OpenRouter, Groq, Vercel), plus a Responses API path for `gpt-6-astra` tool conversations |
| `src/repo2mini/tasks.py` | Task loading, the `FILE:` answer parser, prompt and context builders (levels L0, L2, L5, AG, XL, XXL) |
| `src/repo2mini/pipeline.py` | One run: prompt, optional tool exploration, up to 3 revision rounds on public tests, final hidden scoring, logging |
| `src/repo2mini/sandbox.py` | Runs generated code and tests in a throwaway directory with a scrubbed environment |
| `src/repo2mini/integrity.py` | Syntax tree check that rejects solutions that import, call or execute the original library |
| `src/repo2mini/tools.py` | Read only repo tools for the agentic setting: `list_dir`, `grep`, `read_file`, `git_log` |
| `src/repo2mini/pricing.py` | List prices and cost from logged token usage |
| `tasks/` | 7 tasks and 14 bug fix variants: spec, `task.json`, public tests, buggy code and bug report for fix tasks |
| `scripts/` | Run, rescore, analyze, cost and publishing scripts (see below) |
| `dashboard/app.py` | Local Plotly and Gradio dashboard over `results/run_task/rows.jsonl` |
| `space/` | Source of the static results page and a replay app |
| `results/run_task/rows.jsonl` | One row per run (535+ rows) with scores, tokens, rounds and integrity result |
| `results/analyze`, `results/make_report` | Aggregated tables, cost tables and charts |

## How a run works

1. **Prompt.** The task spec (`tasks/<id>/spec.md`) states the API to build, the file layout and rules (no importing the original library, standard library plus NumPy or PyTorch only where the task allows it). The answer format is `FILE: solution/<name>.py` followed by a fenced code block. The parser tolerates a missing opening fence.
2. **Context level.** L0 adds no repository text. L2 adds the relevant files, listed in `task.json`. L5 adds a broader slice, capped at 150K tokens. AG gives no text but read only tools (20 tool turns, then the model must answer). XL and XXL place the relevant files at 50% depth inside a haystack of about 240K or 600K tokens, filled with other files of the same repo and then with other installed libraries.
3. **Revision rounds.** The solution is run against the public tests. If they fail, the pytest output is returned and the model answers again, at most three times. Beam needs earlier `reasoning_content` sent back in history, and the pipeline does that for every model that returns reasoning.
4. **Hidden scoring.** The final solution runs against public plus hidden tests. The score is the share of passing tests, split by category (api, parity, behavior). A run is a full success if every test passes.
5. **Integrity.** `integrity.py` parses the code and bans listed imports and calls (`exec`, `eval`, `compile`, `__import__`, `importlib`, `runpy` and the original package). A violation scores 0 and the run is marked disqualified. Mentioning the library in a comment or docstring is fine.
6. **Logging.** Every run writes `runs/<id>/result.json`, `messages.jsonl` (reasoning, replies, public test output per round) and the final solution, and appends a row to `rows.jsonl`. Trackio logging is optional (`--no-trackio`).

## Tasks and oracles

| Task | Library | What is built | Oracle |
| --- | --- | --- | --- |
| gpt2_forward | Transformers | GPT-2 forward pass | Logits and loss against the installed Hugging Face model |
| gpt2_generate | Transformers | KV cache and greedy generation | Generated tokens against the installed model |
| sortedlist_core | sortedcontainers | SortedList | Random operation sequences and internal layout against the installed package |
| sortedlist_key | sortedcontainers | SortedList with key functions | Same, including SortedKeyList |
| numpy_quantile | NumPy | quantile and percentile, 13 methods | Values, shapes, dtypes on 3,900 random cases |
| pandas_cut | pandas | Binning logic of `pd.cut` | Codes and labels on 2,400 random cases |
| sort_tracker | Roboflow trackers | The SORT tracker | Tracker ids against the installed `SORTTracker` on random scenes |

## Data generation

Everything the benchmark runs on is generated or built by code in this repository, except the hidden tests and reference solutions (see below).

1. **Source repositories.** `bash scripts/fetch_repos.sh` makes sparse clones of Transformers, sortedcontainers, NumPy, pandas and Roboflow trackers into `repos/`, pinned to the exact commits used (listed in the script). Only the directories the tasks need are checked out.
2. **Task authoring.** Each task directory holds `spec.md`, `task.json` (context file lists for L2 and L5, integrity rules, familiarity label), `public_tests/` and, privately, `hidden_tests/` and a reference solution. The oracle is the installed package itself. Hidden tests generate random inputs, run the original and the candidate on the same input, and compare outputs. A task is only accepted when the reference solution passes every test. I also checked that deliberate mutations of the reference fail the tests (for `sort_tracker`, 3 of 5 mutations were caught, so it is the weakest of the oracles).
3. **Bug fix variants.** `scripts/make_fix_tasks.py` copies a task and injects one bug into its reference solution (two per task, 14 in total), writes a bug report that lists failing checks, and keeps a variant only if the parent's hidden tests fail on it. One first candidate survived the tests and was replaced. The script needs the private reference solutions, so it cannot be rerun from this checkout. The resulting buggy code and bug report are in `tasks/*__fix*/reference/broken` and `bug_report.md`.
4. **Long context haystacks.** `build_long_context` in `src/repo2mini/tasks.py` builds XL and XXL prompts: relevant files at 50% depth, filler from the rest of the same repo, then from large installed libraries (sympy, scipy, matplotlib, gradio, plotly, rich) until the token target is reached.
5. **Model outputs.** `scripts/run_task.py` runs a grid and writes the per run logs. The published outputs are in the HF dataset above.

## Reproduce

```bash
uv sync
cp .env.example .env            # add your own keys
bash scripts/fetch_repos.sh
uv run python scripts/ping.py beam low
uv run python scripts/run_task.py --tag=demo --task sortedlist_core --model beam --level L0 L2 --samples=1 --effort=low
uv run python scripts/analyze.py && uv run python scripts/costs.py && uv run python scripts/make_report.py
uv run python dashboard/app.py   # http://127.0.0.1:7861
```

Model aliases are in `src/repo2mini/providers.py` (`beam`, `gpt41`, `gpt52`, `gpt6astra`, `nemotron`, `gptoss`, `qwen27`). `run_one` expects a `hidden_tests/` directory per task, so to score runs you need to write your own (the public tests show the format and categories: api, parity, behavior). `pytest` skips the harness checks that need private files.

| Script | Purpose |
| --- | --- |
| `run_task.py` | Run a grid of task, model, level and sample cells |
| `rescore.py`, `rescore_parse.py`, `rescore_all.py` | Rescore saved solutions after a test or parser fix, without calling any model |
| `rerun_failed.py`, `rerun_errors.py` | Rerun cells that failed with transient or protocol errors |
| `analyze.py`, `costs.py`, `make_report.py` | Tables, cost metrics, best variant chart and per task comparison |
| `build_space.py`, `build_static_page.py` | Build the publishable bundle (no hidden tests, secret scan) and the static page |
| `make_fix_tasks.py` | Generate bug fix variants (needs private references) |
| `fetch_repos.sh` | Pinned sparse clones of the source repositories |

## Corrections made along the way

All are disclosed in the Space README: an unfair hidden test removed and runs rescored, substring "mentions the library" checks replaced by the syntax tree check (49 false positives removed, 4 Beam runs disqualified), a Beam `reasoning_content` protocol fix and reruns, a tolerant parser, 16 empty context runs set aside and rerun, transient errors rerun, and tool protocol fairness fixes.

## Limits

One to three samples per cell (one for long context), so many gaps are within noise. Mostly low reasoning effort. Beam's cost is a list price estimate. Hidden tests are withheld to limit leakage, so the benchmark cannot be rerun as is without writing new hidden tests, and the repository slices come from recent main branches while the oracles are the installed releases, so small version drift is possible. Familiarity is a confound: GPT-6 Astra writes `sortedcontainers` from memory with no context, which is why `sort_tracker` is the cleaner test of context use.

## License

Apache-2.0 for the code. The source repositories keep their own licenses.
