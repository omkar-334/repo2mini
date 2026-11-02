"""Local dashboard for Repo2Mini results. Run: uv run python dashboard/app.py  then open http://127.0.0.1:7861.

Reads results/run_task/rows.jsonl on every refresh. The effort dropdown picks which reasoning effort rows to plot:
`highest` uses, for each (model, task), the highest effort that was run; the other options show exactly that effort.
"""
import json
from pathlib import Path

import sys

import gradio as gr
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from repo2mini.pricing import PRICES, run_cost  # noqa: E402
ROWS = ROOT / "results" / "run_task" / "rows.jsonl"
LEVELS = ["L0", "L2", "L5", "XL", "XXL", "AG"]
SETTINGS = ["Write from scratch", "Agentic (tools only)", "Bug fix", "Long context (haystack)", "All settings"]
RANK = {"default": 0, "minimal": 1, "low": 2, "medium": 3, "high": 4, "xhigh": 5, "max": 6}
EFFORT_CHOICES = ["highest", "default", "low", "medium", "high"]
METRICS = {
    "Hidden test pass rate": "pass_rate",
    "Full success (all hidden tests)": "success",
    "API compatibility": "api",
    "Numeric / behavior parity": "parity",
    "Behavior checks": "behavior",
    "Completion tokens": "completion_tokens",
    "Revision rounds": "revision_rounds",
    "Runtime (s)": "runtime_s",
    "Cost per run (USD, list price)": "cost_usd",
    "Tool calls per run": "tool_calls",
    "Disqualified rate (used the original library)": "disqualified",
}
RATE_METRICS = {"pass_rate", "success", "api", "parity", "behavior", "disqualified"}
MODEL_LABEL = {"beam": "Beam", "gpt41": "GPT-4.1", "gpt52": "GPT-5.2", "gpt6astra": "GPT-6 Astra", "nemotron": "Nemotron 3 Ultra"}
PALETTE = {"Beam": "#e8590c", "GPT-4.1": "#868e96", "GPT-5.2": "#1c7ed6", "GPT-6 Astra": "#2f9e44"}
EXTRA = ["#ae3ec9", "#f59f00", "#0ca678", "#c2255c"]
EFFORT_COLOR = {"default": "#868e96", "minimal": "#adb5bd", "low": "#74c0fc", "medium": "#1c7ed6", "high": "#1864ab", "xhigh": "#5f3dc4", "max": "#862e9c"}


_COST_CACHE: dict = {}


def _cost(model: str, run_id: str) -> float:
    if model not in PRICES:
        return float("nan")
    if run_id not in _COST_CACHE:
        f = ROOT / "results" / "run_task" / "runs" / run_id / "result.json"
        _COST_CACHE[run_id] = run_cost(model, json.loads(f.read_text())["steps"]) if f.exists() else float("nan")
    return _COST_CACHE[run_id]


def load() -> pd.DataFrame:
    if not ROWS.exists():
        return pd.DataFrame()
    rows = [json.loads(l) for l in ROWS.read_text().splitlines() if l.strip()]
    df = pd.DataFrame(rows)
    df = df[df["task"] != "mini_autograd"].copy()
    df["cost_usd"] = [_cost(r["model"], r["run_id"]) for _, r in df.iterrows()]
    df["model"] = df["model"].map(lambda m: MODEL_LABEL.get(m, m))
    df["effort"] = df["effort"].fillna("default")
    for cat in ("api", "parity", "behavior"):
        df[cat] = df["by_category"].map(lambda d, c=cat: d[c][0] / d[c][1] if isinstance(d, dict) and c in d and d[c][1] else None)
    df["success"] = df["success"].astype(float)
    df["disqualified"] = df["disqualified"].fillna(False).astype(float) if "disqualified" in df else 0.0
    if "tool_calls" not in df:
        df["tool_calls"] = float("nan")
    df["setting"] = df.apply(lambda r: "Bug fix" if "__fix" in r["task"] else ("Agentic (tools only)" if r["level"] == "AG" else ("Long context (haystack)" if r["level"] in ("XL", "XXL") else "Write from scratch")), axis=1)
    df["base_task"] = df["task"].str.split("__fix").str[0]
    df["rank"] = df["effort"].map(lambda e: RANK.get(e, 0))
    return df


def color_for(model: str, i: int = 0) -> str:
    return PALETTE.get(model, EXTRA[i % len(EXTRA)])


def select(df, effort, models, tasks, level, setting="All settings"):
    d = df[df["model"].isin(models) & df["base_task"].isin(tasks)]
    if setting != "All settings":
        d = d[d["setting"] == setting]
    if level != "all":
        d = d[d["level"] == level]
    if effort == "highest":
        top = d.groupby(["model", "task", "level"])["rank"].transform("max")
        d = d[d["rank"] == top]
    else:
        d = d[d["effort"] == effort]
    return d


def empty_fig(msg: str) -> go.Figure:
    f = go.Figure()
    f.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font=dict(size=15, color="#495057"))
    f.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", xaxis_visible=False, yaxis_visible=False, height=380)
    return f


def style(f: go.Figure, title: str, metric: str, height=420) -> go.Figure:
    f.update_layout(template="plotly_white", paper_bgcolor="white", plot_bgcolor="white", title=dict(text=title, x=0.01, font=dict(size=16)),
                    height=height, margin=dict(l=50, r=20, t=60, b=50), legend=dict(orientation="h", y=-0.2), font=dict(color="#212529"))
    if metric in RATE_METRICS:
        f.update_yaxes(range=[0, 1.05], tickformat=".0%")
    return f


def agg(d, by, metric):
    g = d.groupby(by).agg(value=(metric, "mean"), n=("run_id", "count")).reset_index()
    return g


def fmt(v, metric):
    return f"{v:.0%}" if metric in RATE_METRICS else f"{v:,.1f}"


def kpi_md(d, label):
    if d.empty:
        return "### No runs for this selection"
    rows = []
    for m, g in sorted(d.groupby("model"), key=lambda kv: -kv[1]["pass_rate"].mean()):
        used = g.groupby("effort")["task"].nunique().sort_values(ascending=False)
        eff = ", ".join(f"{e} on {n} task{'s' if n != 1 else ''}" for e, n in used.items())
        rows.append(f"| **{m}** | {g['pass_rate'].mean():.1%} | {g['success'].mean():.0%} | {g['api'].mean():.1%} | {len(g)} | {eff}{(' · disqualified ' + str(int(g['disqualified'].sum()))) if g['disqualified'].sum() else ''} |")
    head = "| Model | Hidden tests passed | Full success | API compatibility | Runs | Effort used |\n| --- | --- | --- | --- | --- | --- |\n"
    return f"### {label}\n\n" + head + "\n".join(rows)


def build(effort, models, tasks, level, metric_label, setting):
    df = load()
    metric = METRICS[metric_label]
    if df.empty:
        e = empty_fig("No results found in results/run_task/rows.jsonl")
        return ("### No data", pd.DataFrame(), e, e, e, e, e, e, pd.DataFrame(), pd.DataFrame(), e, e, e, pd.DataFrame())
    models = models or sorted(df["model"].unique())
    tasks = tasks or sorted(df["base_task"].unique())
    d = select(df, effort, models, tasks, level, setting)
    lvl = "all context levels" if level == "all" else f"context {level}"
    label = f"{setting}  ·  Effort: {effort}  ·  {lvl}  ·  {len(d)} runs"
    if d.empty:
        msg = f"No runs with effort '{effort}' for this selection. See the Coverage tab for what was run."
        e = empty_fig(msg)
        return (kpi_md(d, label) + f"\n\n{msg}", pd.DataFrame(), e, e, e, e, e, e, pd.DataFrame(), coverage(df), e, e, e, pd.DataFrame())

    order = list(agg(d, "model", metric).sort_values("value", ascending=False)["model"])
    # 1. model comparison
    g = agg(d, "model", metric).set_index("model").loc[order].reset_index()
    f1 = go.Figure(go.Bar(x=g["model"], y=g["value"], marker_color=[color_for(m, i) for i, m in enumerate(g["model"])],
                          text=[fmt(v, metric) for v in g["value"]], textposition="outside", customdata=g["n"],
                          hovertemplate="%{x}<br>" + metric_label + ": %{y:.3f}<br>runs: %{customdata}<extra></extra>"))
    style(f1, f"{metric_label} by model", metric)
    # 2. by context level (always all levels)
    d_levels = select(df, effort, models, tasks, "all", setting)
    f2 = go.Figure()
    for i, m in enumerate(order):
        gm = agg(d_levels[d_levels["model"] == m], "level", metric).set_index("level").reindex(LEVELS).reset_index()
        f2.add_trace(go.Scatter(x=gm["level"], y=gm["value"], mode="lines+markers", name=m, line=dict(color=color_for(m, i), width=3),
                                marker=dict(size=9), customdata=gm["n"], hovertemplate=m + " %{x}<br>%{y:.3f}<br>runs: %{customdata}<extra></extra>"))
    style(f2, f"{metric_label} versus context level (L0 none, L2 relevant files, L5 broad slice)", metric)
    # 3. heatmap task x model
    pv = d.pivot_table(index="base_task", columns="model", values=metric, aggfunc="mean").reindex(columns=order)
    z = pv.values
    f3 = go.Figure(go.Heatmap(z=z, x=list(pv.columns), y=list(pv.index), colorscale="RdYlGn" if metric in RATE_METRICS else "Blues",
                              zmin=0 if metric in RATE_METRICS else None, zmax=1 if metric in RATE_METRICS else None,
                              text=[[("" if pd.isna(v) else fmt(v, metric)) for v in row] for row in z], texttemplate="%{text}",
                              hovertemplate="%{y} / %{x}<br>%{z:.3f}<extra></extra>", colorbar=dict(title="")))
    style(f3, f"{metric_label}: task by model", "none", height=max(300, 60 * len(pv.index) + 140))
    f3.update_yaxes(autorange="reversed")
    # 4. grouped bars per task
    f4 = go.Figure()
    for i, m in enumerate(order):
        gm = agg(d[d["model"] == m], "base_task", metric)
        f4.add_trace(go.Bar(x=gm["base_task"], y=gm["value"], name=m, marker_color=color_for(m, i), customdata=gm["n"],
                            hovertemplate=m + " %{x}<br>%{y:.3f}<br>runs: %{customdata}<extra></extra>"))
    style(f4, f"{metric_label} per task", metric, height=440)
    f4.update_layout(barmode="group")
    # 5. cost vs quality
    gs = d.groupby(["model", "level"]).agg(tokens=("completion_tokens", "mean"), q=("pass_rate", "mean"), n=("run_id", "count")).reset_index()
    f5 = go.Figure()
    for i, m in enumerate(order):
        gm = gs[gs["model"] == m]
        f5.add_trace(go.Scatter(x=gm["tokens"], y=gm["q"], mode="markers+text", name=m, text=gm["level"], textposition="top center",
                                marker=dict(size=[10 + 3 * n ** 0.5 for n in gm["n"]], color=color_for(m, i), opacity=0.85),
                                hovertemplate=m + " %{text}<br>tokens %{x:,.0f}<br>pass %{y:.1%}<extra></extra>"))
    style(f5, "Quality versus cost (mean completion tokens per run, includes reasoning)", "pass_rate")
    f5.update_xaxes(title="mean completion tokens per run", type="log")
    f5.update_yaxes(title="hidden tests passed")
    # 6. effort comparison, ignores the effort dropdown
    de = df[df["model"].isin(models) & df["base_task"].isin(tasks)]
    if setting != "All settings":
        de = de[de["setting"] == setting]
    if level != "all":
        de = de[de["level"] == level]
    f6 = go.Figure()
    for e in sorted(de["effort"].unique(), key=lambda x: RANK.get(x, 0)):
        ge = agg(de[de["effort"] == e], "model", metric).set_index("model").reindex(order).reset_index()
        f6.add_trace(go.Bar(x=ge["model"], y=ge["value"], name=f"effort {e}", marker_color=EFFORT_COLOR.get(e, "#495057"), customdata=ge["n"],
                            hovertemplate="%{x} effort " + e + "<br>%{y:.3f}<br>runs: %{customdata}<extra></extra>"))
    style(f6, f"{metric_label} by reasoning effort (all efforts that were run; efforts are not run on equal tasks)", metric)
    f6.update_layout(barmode="group")

    gc = d.groupby("model").agg(runs=("run_id", "count"), cost=("cost_usd", "sum"), q=("pass_rate", "sum"), succ=("success", "sum")).reindex(order)
    cols = [color_for(m, i) for i, m in enumerate(order)]
    c1 = go.Figure(go.Bar(x=order, y=gc["cost"] / gc["runs"], marker_color=cols, text=[f"${v:.3f}" for v in gc["cost"] / gc["runs"]], textposition="outside",
                          hovertemplate="%{x}<br>$%{y:.4f} per run<extra></extra>"))
    style(c1, "Cost per run (USD, list price)", "none", height=380)
    cps = gc["cost"] / gc["succ"].where(gc["succ"] > 0)
    c2 = go.Figure(go.Bar(x=order, y=cps, marker_color=cols, text=[("no full success" if pd.isna(v) else f"${v:.3f}") for v in cps], textposition="outside",
                          hovertemplate="%{x}<br>$%{y:.4f} per fully passing run<extra></extra>"))
    style(c2, "Cost per fully passing run (USD)", "none", height=380)
    ppd = gc["q"] / gc["cost"]
    c3 = go.Figure(go.Bar(x=order, y=ppd, marker_color=cols, text=[f"{v:.1f}" for v in ppd], textposition="outside",
                          hovertemplate="%{x}<br>%{y:.1f} pass rate points per dollar<extra></extra>"))
    style(c3, "Pass rate points per dollar (higher is better)", "none", height=380)
    cost_tbl = pd.DataFrame({"model": order, "runs": gc["runs"].values, "total_cost_usd": gc["cost"].round(2).values,
                             "cost_per_run": (gc["cost"] / gc["runs"]).round(4).values, "full_successes": gc["succ"].astype(int).values,
                             "cost_per_full_success": cps.round(4).values, "pass_points_per_dollar": ppd.round(1).values})
    summary = d.groupby("model").agg(runs=("run_id", "count"), pass_rate=("pass_rate", "mean"), full_success=("success", "mean"),
                                     api=("api", "mean"), parity=("parity", "mean"), behavior=("behavior", "mean"),
                                     completion_tokens=("completion_tokens", "mean"), rounds=("revision_rounds", "mean"),
                                     runtime_s=("runtime_s", "mean"), cost_usd=("cost_usd", "mean")).round(3).reset_index().sort_values("pass_rate", ascending=False)
    runs = d[["model", "effort", "setting", "task", "level", "sample", "pass_rate", "success", "hidden_passed", "hidden_total", "api", "parity", "behavior",
              "completion_tokens", "prompt_tokens", "tool_calls", "disqualified", "revision_rounds", "runtime_s", "cost_usd", "run_id"]].round(3).sort_values(["task", "model", "level", "sample"])
    return kpi_md(d, label), summary, f1, f2, f3, f4, f5, f6, runs, coverage(df), c1, c2, c3, cost_tbl


def coverage(df):
    g = df.groupby(["model", "effort"]).agg(runs=("run_id", "count"), tasks=("task", "nunique"), levels=("level", "nunique"),
                                            samples_per_cell=("sample", "nunique")).reset_index()
    g["tasks_covered"] = df.groupby(["model", "effort"])["task"].apply(lambda s: ", ".join(sorted(s.unique()))).values
    return g


def options():
    df = load()
    return (sorted(df["model"].unique()) if not df.empty else []), (sorted(df["base_task"].unique()) if not df.empty else [])


MODELS, TASKS = options()

with gr.Blocks(title="Repo2Mini dashboard") as demo:
    gr.Markdown("# Repo2Mini dashboard\nHow much does repository context help, and how do Beam and the OpenAI models compare? "
                "Pick the setting (write from scratch, agentic with tools, bug fix) and the reasoning effort. **highest** uses, for each model, task and level, the highest effort that was run. "
                "Bug fix tasks are grouped under the task they came from.")
    with gr.Row():
        effort = gr.Dropdown(EFFORT_CHOICES, value="highest", label="Reasoning effort", scale=1)
        setting = gr.Dropdown(SETTINGS, value="Write from scratch", label="Setting", scale=2)
        level = gr.Dropdown(["all"] + LEVELS, value="all", label="Context level", scale=1)
        metric = gr.Dropdown(list(METRICS), value="Hidden test pass rate", label="Metric", scale=2)
        refresh = gr.Button("Reload data", scale=1)
    with gr.Row():
        models = gr.CheckboxGroup(MODELS, value=MODELS, label="Models")
        tasks = gr.CheckboxGroup(TASKS, value=TASKS, label="Tasks")
    kpi = gr.Markdown()
    with gr.Tabs():
        with gr.Tab("Overview"):
            with gr.Row():
                p1, p2 = gr.Plot(label="By model"), gr.Plot(label="By context level")
            summary = gr.Dataframe(label="Summary", interactive=False)
        with gr.Tab("By task"):
            p3 = gr.Plot(label="Heatmap")
            p4 = gr.Plot(label="Per task")
        with gr.Tab("Cost vs quality"):
            p5 = gr.Plot(label="Scatter")
        with gr.Tab("Cost"):
            gr.Markdown("Costs use list prices on the logged tokens (cached input at the cached rate). OpenAI: developers.openai.com/api/docs/pricing. "
                        "Beam: OpenRouter listing, $0.25 in and $1 out per 1M tokens, which was not billed (free beta).")
            with gr.Row():
                q1, q2, q3 = gr.Plot(), gr.Plot(), gr.Plot()
            cost_df = gr.Dataframe(interactive=False)
        with gr.Tab("Effort comparison"):
            p6 = gr.Plot(label="By effort")
        with gr.Tab("All runs"):
            runs = gr.Dataframe(label="Runs for this selection", interactive=False)
        with gr.Tab("Coverage"):
            gr.Markdown("What was actually run. `high` has no runs yet, so choosing it shows an empty chart.")
            cov = gr.Dataframe(interactive=False)
    ins = [effort, models, tasks, level, metric, setting]
    outs = [kpi, summary, p1, p2, p3, p4, p5, p6, runs, cov, q1, q2, q3, cost_df]
    for c in ins:
        c.change(build, ins, outs)
    refresh.click(build, ins, outs)
    demo.load(build, ins, outs)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7861, theme=gr.themes.Soft(), css=".gradio-container{max-width:1280px !important}")
