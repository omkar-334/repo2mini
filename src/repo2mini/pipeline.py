"""One run = one (task, model, level, sample). Prompt, up to N revision rounds on public tests, final hidden scoring."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from .integrity import check as integrity_check
from .providers import Client
from .sandbox import run_tests
from .tasks import REPOS_DIR, build_prompt, load_task, parse_files
from .tools import SCHEMAS, RepoTools

RESULTS = Path(__file__).resolve().parents[2] / "results" / "run_task"


def _feedback(rep, files=None) -> str:
    if files is not None and not files:
        return ("No files were found in your reply. Reply with the complete files as plain text, each one preceded by a line "
                "`FILE: solution/<name>.py` and followed by a fenced code block. Do not put the files in a tool call.")
    return ("Your implementation failed the public tests. Fix it and return ALL files again in the same format.\n\n"
            f"pytest output:\n{rep.output}")


def integrity_config(task) -> dict:
    meta = task.meta if not task.meta.get("fix_of") else load_task(task.meta["fix_of"]).meta
    return meta.get("integrity", {})


def _explore(client, messages, tools, max_tokens, effort, max_turns):
    """Let the model call repo tools until it answers or the budget runs out. Returns (final reply, intermediate tool turns)."""
    inter = []
    for turn in range(max_turns + 1):
        last = turn == max_turns
        if last:
            messages.append({"role": "user", "content": "The tool budget is used up. Reply now with the final files in the required format."})
        res = client.chat(messages, max_tokens=max_tokens, effort=effort, tools=None if last else SCHEMAS)
        if not res.tool_calls:
            return res, inter
        inter.append(res)
        messages.append(res.message)
        for tc in res.tool_calls:
            try:
                out = tools.call(tc["name"], json.loads(tc["arguments"] or "{}"))
            except (json.JSONDecodeError, TypeError):
                out = "error: arguments must be a JSON object"
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
    return res, inter


def run_one(task_id: str, model: str, level: str = "L0", sample: int = 0, rounds: int = 3, effort: str | None = None,
            max_tokens: int = 16000, ctx_cap: int = 400_000, log_trackio: bool = True, results_dir: Path = RESULTS,
            on_event=None, max_tool_turns: int = 20) -> dict:
    task = load_task(task_id)
    client = Client(model)
    run_id = f"{task_id}-{model}-{level}-s{sample}-{effort or 'def'}-{uuid.uuid4().hex[:6]}"
    rdir = results_dir / "runs" / run_id
    rdir.mkdir(parents=True, exist_ok=True)
    emit = on_event or (lambda *_: None)

    prompt, ctx_info = build_prompt(task, level, ctx_cap)
    messages = [{"role": "user", "content": prompt}]
    pub = [task.root / "public_tests"]
    hidden = [task.root / "hidden_tests"]
    trk = _trackio_init(run_id, dict(task=task_id, model=model, sample=sample, effort=effort, **ctx_info)) if log_trackio else None

    t0 = time.time()
    tot_p = tot_c = 0
    rounds_used = 0
    files: dict[str, str] = {}
    steps = []
    public_ok = False
    n_tool_calls = 0
    for r in range(rounds + 1):
        if level == "AG" and r == 0:
            res, inter = _explore(client, messages, RepoTools(REPOS_DIR / task.meta["repo"]), max_tokens, effort, max_tool_turns)
            for it in inter:
                n_tool_calls += len(it.tool_calls)
                tot_p += it.prompt_tokens
                tot_c += it.completion_tokens
                tstep = dict(round=0, kind="tool", prompt_tokens=it.prompt_tokens, completion_tokens=it.completion_tokens, cached=it.cached_tokens,
                             finish=it.finish_reason, latency_s=round(it.latency_s, 2), n_files=0, public_passed=0, public_total=0,
                             reasoning_chars=len(it.reasoning))
                steps.append(tstep)
                with (rdir / "messages.jsonl").open("a") as f:
                    f.write(json.dumps({**tstep, "response": "", "reasoning": it.reasoning, "public_output": "",
                                        "tool_calls": [{"name": c["name"], "arguments": c["arguments"][:300]} for c in it.tool_calls]}) + "\n")
        else:
            res = client.chat(messages, max_tokens=max_tokens, effort=effort)
        tot_p += res.prompt_tokens
        tot_c += res.completion_tokens
        files = parse_files(res.text) or files
        rep = run_tests(files, pub)
        step = dict(round=r, prompt_tokens=res.prompt_tokens, completion_tokens=res.completion_tokens, cached=res.cached_tokens,
                    finish=res.finish_reason, latency_s=round(res.latency_s, 2), n_files=len(files),
                    public_passed=rep.passed, public_total=rep.total, reasoning_chars=len(res.reasoning))
        steps.append(step)
        with (rdir / "messages.jsonl").open("a") as f:
            f.write(json.dumps({"round": r, "prompt_tail": messages[-1]["content"][-3000:], "response": res.text,
                                "reasoning": res.reasoning, "public_output": rep.output, **step}) + "\n")
        emit(step, res.text, rep.output)
        if trk:
            _trackio_log({f"round/{k}": v for k, v in step.items() if isinstance(v, (int, float))})
        rounds_used = r
        if rep.all_passed:
            public_ok = True
            break
        if r == rounds:
            break
        asst = {"role": "assistant", "content": res.text}
        if res.reasoning:  # Beam rejects history that drops earlier reasoning_content
            asst["reasoning_content"] = res.reasoning
        messages += [asst, {"role": "user", "content": _feedback(rep, files)}]

    final = run_tests(files, pub + hidden, keep=rdir)
    violations = integrity_check(files, integrity_config(task))
    out = dict(
        run_id=run_id, task=task_id, model=model, level=level, sample=sample, effort=effort,
        context_tokens=ctx_info["tokens"], context_files=ctx_info["files"], context_truncated=ctx_info["truncated"],
        revision_rounds=rounds_used, public_ok=public_ok, hidden_passed=final.passed, hidden_total=final.total,
        pass_rate=0.0 if violations else (round(final.passed / final.total, 4) if final.total else 0.0), success=final.all_passed and not violations,
        raw_pass_rate=round(final.passed / final.total, 4) if final.total else 0.0, integrity_violations=violations, disqualified=bool(violations),
        by_category=final.by_category, prompt_tokens=tot_p, completion_tokens=tot_c, runtime_s=round(time.time() - t0, 2), tool_calls=n_tool_calls,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )
    (rdir / "result.json").write_text(json.dumps({**out, "cases": final.cases, "final_output": final.output, "steps": steps}, indent=2))
    with (results_dir / "rows.jsonl").open("a") as f:
        f.write(json.dumps(out) + "\n")
    if trk:
        _trackio_log({"final/pass_rate": out["pass_rate"], "final/success": int(out["success"]), "final/rounds": rounds_used,
                      "final/prompt_tokens": tot_p, "final/completion_tokens": tot_c})
        _trackio_finish()
    return out


def _trackio_init(name: str, config: dict):
    try:
        import trackio

        trackio.init(project="repo2mini", name=name, config=config)
        return True
    except Exception as e:  # logging must never kill a run
        print(f"trackio disabled: {e}")
        return None


def _trackio_log(d: dict):
    try:
        import trackio

        trackio.log(d)
    except Exception:
        pass


def _trackio_finish():
    try:
        import trackio

        trackio.finish()
    except Exception:
        pass
