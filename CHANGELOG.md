# Changelog

## 2026-10-28

* Downloaded 9 related papers into `paper_review/`.
* Wrote `PLAN.md` for a 5 day entry to the Build with Beam contest.
* Switched the plan from a SWE-Atlas eval to **Repo2Mini**: rebuild a repo subsystem as a mini implementation under a context ablation (L0, L2, L5), scored by hidden tests.
* Dropped the repo mindmap idea and the LLM judge.

## 2026-10-31

* Added `src/repo2mini/` (providers, tasks, sandbox, tools, pipeline), `scripts/run_task.py`, `scripts/ping.py`, `space/app.py` (Gradio) and `tests/test_pipeline.py` (7 harness checks, all pass).
* Logging: per run `messages.jsonl` and `result.json`, global `rows.jsonl` and `summary.json` under `results/run_task/`, plus Trackio project `repo2mini`.
* Decision: own minimal jailed repo tools (`grep`, `read_file`, `list_dir`, `git_log`) over MCP or external agents. The main loop is harness driven (public test feedback), not function calling.
* Smoke task `mini_autograd`: Beam direct API passes 9/9 hidden tests at L0 with 0 revisions, 12.2K completion tokens, 72s. Task is too memorized to be a benchmark task, it only validates plumbing.
* Vercel AI Gateway not set up yet: CLI is logged out.
* Verified Vercel AI Gateway without credentials: `https://ai-gateway.vercel.sh/v1/models` lists `reflection/beam-free` (1,048,576 context, 131072 max output, tags implicit-caching, reasoning, tool-use, free). Chat endpoint returns 401 without a key, as expected. `ai-gateway setup` only wires local coding agents, so for our API calls only `AI_GATEWAY_API_KEY` is needed (create via `vercel ai-gateway api-keys` after `vercel login`, or the dashboard).
* Vercel set up per https://vercel.com/get-started.md: CLI 65.9.0 installed globally, logged in as omkar-334, Vercel plugin already installed (provides the shared MCP at mcp.vercel.com, so no extra MCP entry added). Created gateway key `repo2mini` ($1 cap, 7d expiry) and stored it in `.env`.
* `scripts/ping.py beam-vercel` reaches the gateway and authenticates, but `reflection/beam-free` returns 403 "Free tier users do not have access to this model" until paid credits are added to the Vercel team. Not purchased.

## 2026-11-01

* Added real tasks: `gpt2_forward`, `gpt2_generate` (Transformers GPT-2, parity against the installed HF model) and `sortedlist_core`, `sortedlist_key` (python-sortedcontainers, parity and internal layout against the installed package). Each has public tests, hidden tests (parity, behavior, API conventions) and a reference solution; the harness gate checks the references pass (11 harness tests pass). Hidden tests also reject solutions that import the original library.
* Repos cloned into `repos/` (Transformers sparse, sortedcontainers). Prompt sizes: L2 about 19K to 49K tokens, L5 capped at 150K tokens.
* Beam pilot on `gpt2_forward` (effort low): 13/16 hidden tests at both L0 and L2, same failures at both levels (n_inner default, config aliases, relu variant). Spec clarified for activation names, pilot discarded.
* Launched Beam grid (effort low, 3 samples, 4 tasks x L0, L2, L5) as two background streams, logs in `results/grid/`.
* Fixed a pipeline bug: revision rounds failed with HTTP 400 because Beam requires earlier assistant `reasoning_content` in the history. `src/repo2mini/pipeline.py` now sends it back. 10 errored cells were rerun (`scripts/rerun_failed.py`), all 36 low effort runs completed.
* Beam low effort grid (3 samples per cell): `sortedlist_core` pass rate 0.85 at L0 and 1.00 at L2 and L5 (full success 0/3 to 3/3). GPT-2 tasks are not monotonic in context. On `sortedlist_key`, with context Beam reproduces the original library almost verbatim (about 950 to 1,050 non-empty lines) and fails the compactness check 3/3 at L2 and L5; without context it fails the parity fuzz tests.
* Started `reasoning_effort=medium` sweep (2 samples), tag `c_medium`.
* Medium effort sweep finished (24 runs, 2 samples per cell, no errors). Pooled over tasks and levels: mean hidden pass rate 0.771 at medium vs 0.759 at low, full success 0.125 vs 0.222, mean completion tokens 7,577 vs 5,572 (+36%). 60 Beam runs in total, analysis in `results/analyze/` (`table.csv`, `by_level.csv`, `pass_vs_level.png`).
* Added peer model GPT-4.1 (alias `gpt41`) on the same grid (36 runs, no errors). Pooled mean hidden pass rate 0.756 vs Beam low 0.759; full success 0.111 vs 0.222. 96 runs in total, analysis refreshed.
* Added `scripts/build_space.py` (bundle for publishing, hidden tests and tracebacks excluded) and made `space/app.py` portable.
* Published under omkar334 (public): dataset https://huggingface.co/datasets/omkar334/repo2mini-results (per run solutions, results, analysis tables, task specs and public tests; no hidden tests, no logs with tracebacks) and static Space https://huggingface.co/spaces/omkar334/repo2mini (live at https://omkar334-repo2mini.static.hf.space/). A Gradio Space was refused (402): Gradio on free hardware needs HF PRO. Not purchased. `space/app.py` remains runnable locally.
* Not yet done: the link has not been posted in discussion #5 of reflection/Beam-1.0-501B-A23B.
* Added peers `gpt-5.2` and `gpt-6-astra` (low effort, 2 samples per cell) and two more repos: `numpy_quantile` (all 13 `np.quantile` methods, parity on 3,900 random cases) and `pandas_cut` (`pd.cut` binning and labels, parity on 2,400 random cases). 192 runs in total.
* Test fix: removed `test_no_cache_by_default` from `gpt2_generate` (the spec never required it and the real model returns a cache by default). Rescored 36 saved solutions with `scripts/rescore.py` (full successes 0 to 7).
* Parser fix: Beam omitted the opening code fence after `FILE:` in 13 of 72 runs. `parse_files` is now tolerant and `scripts/rescore_parse.py` rescored those runs from saved replies (revision rounds were not rerun).
* Republished the dataset (413 files, no hidden tests) and the static Space with the 6 task, 4 model results.
* Not added: vLLM and SGLang (need GPUs and have no runnable oracle on this Mac), OpenCV (not attempted). Roboflow `trackers` installed as a candidate.
* Added task `sort_tracker` (Roboflow trackers SORT, ids compared with the installed `SORTTracker` on random scenes; 18 hidden tests; 3 of 5 deliberate mutations caught). First L2 and L5 runs had an empty context (the package lives under `src/trackers`, my paths did not). Set those 16 runs aside in `results/invalid_runs/` and reran: with no repo text all models score 0.47 to 0.50, with the relevant files 0.81 to 1.00.
* 216 runs in total over 7 tasks and 4 models (plus a Beam medium effort sweep). README rewritten around the context effect. Pooled mean pass rate by model (low/default effort): gpt-6-astra 0.960, gpt-5.2 0.790, Beam 0.745, gpt-4.1 0.676.
* Added `dashboard/app.py`: local Gradio and Plotly dashboard (`uv run python dashboard/app.py`, http://127.0.0.1:7861). Effort dropdown (highest, default, low, medium, high), context level, metric, model and task filters; tabs for overview, by task, cost versus quality, effort comparison, all runs and coverage. `highest` picks the highest effort run per model and task.
* Prices: OpenAI list prices read from developers.openai.com/api/docs/pricing (gpt-6-astra $10/$1/$50 with a long context tier above 272K input tokens, gpt-5.2 $1.75/$0.175/$14, gpt-4.1 $2/$0.50/$8); Beam $0.25/$1 from the OpenRouter listing (free beta, not billed). `src/repo2mini/pricing.py`, `scripts/costs.py`, Cost tab in the dashboard.
* Agentic level (AG): tool calling loop with jailed read only repo tools, 20 turn budget, Responses API for gpt-6-astra. 60 runs.
* Bug fix tasks: 14 variants from `scripts/make_fix_tasks.py` (one injected bug per variant, all verified to fail the hidden tests; one first candidate survived the tests and was replaced). 224 runs.
* Long context: XL (about 240K tokens) for four models and XXL (about 600K) for Beam. GPT-4.1 at 600K was rejected by the organization's 500K tokens per minute limit.
* Scoring fixes: substring "mentions the original library" tests replaced by an AST integrity check (`src/repo2mini/integrity.py`), all runs rescored (`scripts/rescore_all.py`), 4 Beam runs disqualified. Six connection error cells rerun (`scripts/rerun_errors.py`).
* Totals: 535 runs. List price cost about $73 on OpenAI, about $4 on Beam.

## 2026-11-01 (evening)

* Read discussion #5 (84 events) into `results/discussion5/` and wrote `summary.md`: all entries, brief, tiers, a top 15 ranking, and an honest placement of Repo2Mini.
* Added provider aliases `nemotron` (OpenRouter `nvidia/nemotron-3-ultra-550b-a55b:free`, 1M context), `gptoss` and `qwen27` (Groq). Findings: `thinkingmachines/inkling:free` returns 403 (only for agentic harnesses), the second OpenRouter key is expired, Muse Spark and MiniMax are paid (not added). OpenRouter free tier allows 50 requests per day. Groq free tier allows 8,000 tokens per minute, which is smaller than most prompts, so `gptoss` and `qwen27` are not run.
* Started `nemotron` at low effort on 7 tasks, L0 and L2, 1 sample (`results/grid/nemotron1.log`). Rate limit errors are logged as errors, not scored as 0.

## 2026-11-02

* Nemotron 3 Ultra free (OpenRouter) finished: 14 runs, L0 0.502, L2 0.705, 2 of 14 full successes (Beam same cells 0.616 and 0.832). Added to README, `PRICES` (free) and the dashboard label. `inkling:free` still 403, Groq 8K TPM too small, so not run.
* Regenerated analysis (549 runs), rebuilt and republished the dataset and static Space (no hidden tests).
* Posted the entry in discussion #5 (comment id 6ae8bfe04238b36306e97f3f), text in `results/discussion5/my_post.md`.
* Added a quality per dollar table (points per dollar and cost per fully passing run, all four settings, including where Beam is not best) to the README and republished.
* Added scripts/make_report.py: best variant per model chart (context levels plus agentic and bug fix panels) and per task side by side model tables, now used by the static page instead of the old chart and All cells table. Edited the discussion #5 comment to add the quality per dollar table.
* Added a conclusion to the discussion #5 comment. Staged the GitHub repo (committed locally in the scratchpad), public repo creation not yet done.
* Published https://github.com/omkar-334/repo2mini (public, hidden tests and reference solutions withheld) and linked it from the discussion comment and the Space.
