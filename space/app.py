"""Repo2Mini Space. Replay tab reads saved runs. Run tab calls a model live, capped by a daily counter."""
import json
import sys
import time
from pathlib import Path

import gradio as gr
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE if (HERE / "results").exists() else HERE.parents[0]
sys.path.insert(0, str(ROOT / "src"))
from repo2mini.providers import MODELS  # noqa: E402
from repo2mini.tasks import list_tasks, load_task  # noqa: E402

RESULTS = ROOT / "results" / "run_task"
LIVE = any((p / "hidden_tests").exists() for p in (ROOT / "tasks").glob("*")) and bool(__import__("os").environ.get("REFLECTION_API_KEY"))
COUNTER = ROOT / "results" / "live_counter.json"
DAILY_CAP = 20


def rows() -> pd.DataFrame:
    f = RESULTS / "rows.jsonl"
    if not f.exists():
        return pd.DataFrame()
    return pd.DataFrame([json.loads(l) for l in f.read_text().splitlines() if l.strip()])


def run_choices() -> list[str]:
    df = rows()
    return [] if df.empty else df["run_id"].tolist()[::-1]


def load_run(run_id):
    if not run_id:
        return "", "", "", ""
    d = RESULTS / "runs" / run_id
    res = json.loads((d / "result.json").read_text())
    code = "\n\n".join(f"# {p.name}\n{p.read_text()}" for p in sorted((d / "solution").glob("*.py")))
    steps = pd.DataFrame(res["steps"]).to_markdown(index=False)
    cats = ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in res["by_category"].items())
    head = (f"**{res['model']}** on `{res['task']}` at **{res['level']}** | hidden pass rate **{res['pass_rate']:.0%}** "
            f"({res['hidden_passed']}/{res['hidden_total']}) | success **{res['success']}** | rounds {res['revision_rounds']} | "
            f"tokens in/out {res['prompt_tokens']}/{res['completion_tokens']} | {res['runtime_s']}s\n\nBy category: {cats}")
    return head, code, steps, res.get("final_output", "")


def summary():
    df = rows()
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    df = df[df["task"] != "mini_autograd"].copy()
    df["effort"] = df["effort"].fillna("default")
    for cat in ("api", "parity", "behavior"):
        df[cat] = df["by_category"].map(lambda d, c=cat: d[c][0] / d[c][1] if c in d and d[c][1] else None)
    g = df.groupby(["task", "model", "effort", "level"]).agg(
        runs=("run_id", "count"), pass_rate=("pass_rate", "mean"), full_success=("success", "mean"), api=("api", "mean"),
        parity=("parity", "mean"), behavior=("behavior", "mean"), rounds=("revision_rounds", "mean"),
        out_tokens=("completion_tokens", "mean")).round(3).reset_index()
    p = df.pivot_table(index=["effort", "level"], columns="model", values="pass_rate").round(3).reset_index()
    return g, p


def chart():
    f = ROOT / "results" / "analyze" / "pass_vs_level.png"
    return str(f) if f.exists() else None


def _count() -> int:
    try:
        d = json.loads(COUNTER.read_text())
        return d["n"] if d["day"] == time.strftime("%Y-%m-%d") else 0
    except Exception:
        return 0


def live_run(task, model, level, effort, rounds):
    from repo2mini.pipeline import run_one

    if _count() >= DAILY_CAP:
        yield "Daily live cap reached. Use the Replay tab to browse stored runs.", ""
        return
    COUNTER.write_text(json.dumps({"day": time.strftime("%Y-%m-%d"), "n": _count() + 1}))
    log, code = [], ""

    def ev(step, text, out):
        nonlocal code
        code = text
        log.append(f"round {step['round']}: public {step['public_passed']}/{step['public_total']}, "
                   f"{step['completion_tokens']} out tokens, {step['latency_s']}s")

    yield "running...", ""
    try:
        r = run_one(task, model, level, 0, int(rounds), effort or None, on_event=ev)
        yield "\n".join(log) + f"\n\nHidden pass rate {r['pass_rate']:.0%} ({r['hidden_passed']}/{r['hidden_total']}), success={r['success']}", code
    except Exception as e:
        yield f"error: {e}", code


with gr.Blocks(title="Repo2Mini") as demo:
    gr.Markdown("# Repo2Mini\nCan a model rebuild a mini version of a repo, and does more repo context help? "
                "Scored by hidden tests (parity, behavior, API compatibility). Built with Beam for Build with Beam.")
    with gr.Tab("Summary"):
        img = gr.Image(label="Pass rate vs context level (run scripts/analyze.py to refresh)", value=chart())
        t1, t2 = gr.Dataframe(label="Per task, model, effort, level"), gr.Dataframe(label="Mean hidden pass rate by level")
        gr.Button("Refresh").click(lambda: (*summary(), chart()), outputs=[t1, t2, img])
        demo.load(summary, outputs=[t1, t2])
    with gr.Tab("Replay"):
        dd = gr.Dropdown(run_choices(), label="Run")
        head = gr.Markdown()
        code = gr.Code(language="python", label="Generated solution")
        steps = gr.Markdown(label="Rounds")
        out = gr.Textbox(label="Final test output", lines=8)
        dd.change(load_run, dd, [head, code, steps, out])
        gr.Button("Reload runs").click(lambda: gr.Dropdown(choices=run_choices()), outputs=dd)
    with gr.Tab("Run live", visible=LIVE):
        gr.Markdown(f"Live calls are capped at {DAILY_CAP} per day. Fixed tasks only.")
        with gr.Row():
            tk = gr.Dropdown(list_tasks(), value=list_tasks()[0] if list_tasks() else None, label="Task")
            md = gr.Dropdown(list(MODELS), value="mock", label="Model")
            lv = gr.Dropdown(["L0", "L2", "L5"], value="L0", label="Context level")
            ef = gr.Dropdown(["", "low", "medium", "high"], value="", label="reasoning_effort")
            rd = gr.Slider(0, 3, value=3, step=1, label="Revision rounds")
        go = gr.Button("Run", variant="primary")
        lg, cd = gr.Textbox(label="Log", lines=6), gr.Code(language="python", label="Latest code")
        go.click(live_run, [tk, md, lv, ef, rd], [lg, cd])

if __name__ == "__main__":
    demo.launch()
