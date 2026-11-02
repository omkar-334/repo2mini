"""Best variant per model chart and per task model comparison tables.
Best variant = for every (model, task, level) the reasoning effort with the highest mean pass rate.
Output: results/make_report/{best_cells.csv,pass_vs_level_best.png,per_task.html,summary.json}."""
import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "make_report"
OUT.mkdir(parents=True, exist_ok=True)
df = pd.DataFrame([json.loads(l) for l in (ROOT / "results/run_task/rows.jsonl").read_text().splitlines() if l.strip()])
df = df[df.task != "mini_autograd"].copy()
df["effort"] = df.effort.fillna("default")
df["is_fix"] = df.task.str.contains("__fix")
df["base"] = df.task.str.replace(r"__fix\d", "", regex=True)
df["success"] = df.success.astype(float)

MODELS = ["beam", "gpt41", "gpt52", "gpt6astra", "nemotron"]
LABEL = {"beam": "Beam", "gpt41": "GPT-4.1", "gpt52": "GPT-5.2", "gpt6astra": "GPT-6 Astra", "nemotron": "Nemotron 3 Ultra"}
COLOR = {"beam": "#d1495b", "gpt41": "#8d99ae", "gpt52": "#3d5a80", "gpt6astra": "#2a9d8f", "nemotron": "#e9a03b"}
LEVEL_NAME = {"L0": "L0\nno repo text", "L2": "L2\nrelevant files", "L5": "L5\nbroad slice", "XL": "240K token\nhaystack", "XXL": "600K token\nhaystack", "AG": "Agentic tools"}

# one row per (model, task, level, effort), then the best effort per (model, task, level)
cell = df.groupby(["model", "task", "base", "is_fix", "level", "effort"]).agg(pass_rate=("pass_rate", "mean"), success=("success", "mean"),
                                                                              n=("run_id", "count"), full=("success", "sum")).reset_index()
best = cell.sort_values("pass_rate", ascending=False).groupby(["model", "task", "level"], as_index=False).head(1)
best.to_csv(OUT / "best_cells.csv", index=False)
varied = df.groupby("model").effort.nunique()

# ---- chart: left, context level curve on the write tasks; right, other settings
plain = best[~best.is_fix & (best.level != "AG")]
levels = [l for l in ["L0", "L2", "L5", "XL", "XXL"] if l in set(plain.level)]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [3.2, 2]})
ends = []
for m in MODELS:
    d = plain[plain.model == m].groupby("level").pass_rate.agg(["mean", "sem"]).reindex(levels).dropna(subset=["mean"])
    if d.empty:
        continue
    x = np.array([levels.index(l) for l in d.index])
    lw, z = (3.4, 5) if m == "beam" else (1.9, 3)
    a1.fill_between(x, d["mean"] - d["sem"].fillna(0), d["mean"] + d["sem"].fillna(0), color=COLOR[m], alpha=0.0 if m != "beam" else 0.14, lw=0)
    a1.plot(x, d["mean"], marker="o", ms=8 if m == "beam" else 5, lw=lw, color=COLOR[m], zorder=z, ls="--" if m == "nemotron" else "-")
    if m == "beam":
        for xi, v in zip(x, d["mean"]):
            a1.annotate(f"{v:.2f}", (xi, v), textcoords="offset points", xytext=(0, 11), ha="center", fontsize=9.5, color=COLOR[m], weight="bold", bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85), zorder=9)
    ends.append([m, x[-1], float(d["mean"].iloc[-1])])
# direct labels at the right edge, nudged apart so none overlap
ends.sort(key=lambda e: e[2])
ys = [e[2] for e in ends]
for i in range(1, len(ys)):
    ys[i] = max(ys[i], ys[i - 1] + 0.045)
xcol = len(levels) - 1 + 0.35
for (m, xl, v), y in zip(ends, ys):
    a1.annotate(f"{LABEL[m]}  {v:.2f}", (xl, v), xytext=(xcol, y), fontsize=9.5, color=COLOR[m], weight="bold" if m == "beam" else "normal", va="center",
                annotation_clip=False, arrowprops=dict(arrowstyle="-", color=COLOR[m], lw=0.7, alpha=0.55, shrinkA=0, shrinkB=3))
a1.set_xlim(-0.2, len(levels) - 1 + 1.6)
a1.set_xticks(range(len(levels)))
a1.set_xticklabels([LEVEL_NAME[l] for l in levels], fontsize=9)
a1.set_ylim(0.2, 1.08)
a1.set_ylabel("Mean hidden pass rate (best effort per task and level)")
a1.set_title("More repo context: pass rate by level", loc="left", weight="bold")
a1.grid(axis="y", alpha=0.25)
fig.text(0.01, 0.015, "Band: standard error over tasks, each task counts equally. 600K tokens ran for Beam only. Nemotron ran L0 and L2 only (free tier). Aggregation differs slightly from the README tables, which pool runs.", fontsize=8.5, color="#666")

others = [("Agentic tools", best[(best.level == "AG") & ~best.is_fix]), ("Bug fix L0", best[best.is_fix & (best.level == "L0")]),
          ("Bug fix L2", best[best.is_fix & (best.level == "L2")])]
ms = [m for m in MODELS if m != "nemotron"]
w = 0.2
for j, m in enumerate(ms):
    vals = [o[o.model == m].pass_rate.mean() for _, o in others]
    bars = a2.bar(np.arange(len(others)) + (j - 1.5) * w, vals, w, color=COLOR[m], label=LABEL[m], edgecolor="white")
    for b, v in zip(bars, vals):
        a2.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.2f}", ha="center", fontsize=7, rotation=90, va="bottom")
a2.set_xticks(range(len(others)))
a2.set_xticklabels([n for n, _ in others], fontsize=9)
a2.tick_params(axis="x", pad=4)
a2.set_ylim(0, 1.18)
a2.set_title("Tools and bug fixing", loc="left", weight="bold")
a2.legend([plt.Rectangle((0,0),1,1,color=COLOR[m]) for m in ms], [LABEL[m] for m in ms], frameon=False, fontsize=8.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16), columnspacing=1.0, handlelength=1.0)
a2.grid(axis="y", alpha=0.25)
for a in (a1, a2):
    for s in ("top", "right"):
        a.spines[s].set_visible(False)
fig.suptitle("Repo2Mini: best variant of each model", x=0.01, ha="left", fontsize=14, weight="bold")
fig.subplots_adjust(left=0.06, right=0.985, top=0.86, bottom=0.2, wspace=0.28)
fig.savefig(OUT / "pass_vs_level_best.png", dpi=160)

# ---- per task tables: models side by side
ROWS = [("L0", False, "L0 write, no repo text"), ("L2", False, "L2 write, relevant files"), ("L5", False, "L5 write, broad slice"),
        ("AG", False, "Agentic, tools only"), ("L0", True, "Bug fix, L0"), ("L2", True, "Bug fix, L2"),
        ("XL", False, "Long context, 240K"), ("XXL", False, "Long context, 600K")]


def agg(sub):
    """Cell value for one model: mean pass rate over its (task, level) best cells, with full success counts."""
    if sub.empty:
        return None
    return dict(p=float(np.average(sub.pass_rate, weights=sub.n)), full=int(round(sub.full.sum())), n=int(sub.n.sum()))


def block(title, tasks_df, note=""):
    out = [f"<h3>{html.escape(title)}</h3>{note}<table class='cmp'><thead><tr><th>Setting</th>" + "".join(f"<th>{LABEL[m]}</th>" for m in MODELS) + "</tr></thead><tbody>"]
    for lvl, fix, name in ROWS:
        sub = tasks_df[(tasks_df.level == lvl) & (tasks_df.is_fix == fix)]
        vals = {m: agg(sub[sub.model == m]) for m in MODELS}
        if all(v is None for v in vals.values()):
            continue
        top = max(v["p"] for v in vals.values() if v)
        cells = []
        for m in MODELS:
            v = vals[m]
            if v is None:
                cells.append("<td class='na'>not run</td>")
                continue
            cls = "best" if abs(v["p"] - top) < 1e-9 else ""
            shade = f"background:rgba(42,157,143,{0.08 + 0.45 * max(0, v['p']):.2f})"
            cells.append(f"<td class='{cls}' style='{shade}'><b>{v['p']:.2f}</b><span>{v['full']}/{v['n']} full</span></td>")
        out.append(f"<tr><th>{html.escape(name)}</th>{''.join(cells)}</tr>")
    out.append("</tbody></table>")
    return "".join(out)


parts = [block("All tasks pooled", best, "<p class='m'>Mean over tasks, runs weighted. Bold with a teal frame is the best model in that row.</p>")]
for t in sorted(set(best.base)):
    sub = best[best.base == t]
    parts.append(block(t, sub))
(OUT / "per_task.html").write_text("\n".join(parts))

wins = {}
for t in sorted(set(best.base)):
    for lvl, fix, name in ROWS:
        sub = best[(best.base == t) & (best.level == lvl) & (best.is_fix == fix)]
        vals = {m: agg(sub[sub.model == m]) for m in MODELS if agg(sub[sub.model == m])}
        if len(vals) > 1:
            top = max(v["p"] for v in vals.values())
            for m, v in vals.items():
                if abs(v["p"] - top) < 1e-9:
                    wins[m] = wins.get(m, 0) + 1
(OUT / "summary.json").write_text(json.dumps({"cells": len(best), "rows_won_by_model": wins, "models_with_multiple_efforts": {k: int(v) for k, v in varied.items()}}, indent=2))
print(json.dumps({"wins": wins}))
