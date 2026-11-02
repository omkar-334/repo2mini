"""Aggregate results/run_task/rows.jsonl. Output: results/analyze/{table.csv,by_level.csv,summary.json,pass_vs_level.png}."""
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from repo2mini.tasks import load_task  # noqa: E402

OUT = ROOT / "results" / "analyze"
OUT.mkdir(parents=True, exist_ok=True)
rows = [json.loads(l) for l in (ROOT / "results" / "run_task" / "rows.jsonl").read_text().splitlines() if l.strip()]
df = pd.DataFrame(rows)
df = df[~df["task"].isin(["mini_autograd"])]
df["familiarity"] = df["task"].map(lambda t: load_task(t).meta.get("familiarity", "?"))
df["effort"] = df["effort"].fillna("default")
for cat in ("api", "parity", "behavior"):
    df[f"{cat}_rate"] = df["by_category"].map(lambda d, c=cat: d[c][0] / d[c][1] if c in d and d[c][1] else None)
df["total_tokens"] = df["prompt_tokens"] + df["completion_tokens"]

agg = dict(runs=("run_id", "count"), pass_rate=("pass_rate", "mean"), success=("success", "mean"), api=("api_rate", "mean"),
           parity=("parity_rate", "mean"), behavior=("behavior_rate", "mean"), rounds=("revision_rounds", "mean"),
           out_tokens=("completion_tokens", "mean"), in_tokens=("prompt_tokens", "mean"), runtime_s=("runtime_s", "mean"))
table = df.groupby(["task", "model", "effort", "level"]).agg(**agg).round(3).reset_index()
by_level = df.groupby(["familiarity", "model", "effort", "level"]).agg(**agg).round(3).reset_index()
table.to_csv(OUT / "table.csv", index=False)
by_level.to_csv(OUT / "by_level.csv", index=False)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(14, 3.8), sharey=True)
order = ["L0", "L2", "L5", "XL", "XXL", "AG"]
for ax, metric, title in zip(axes, ["pass_rate", "api", "parity"], ["All hidden tests", "API conventions", "Numeric/behavior parity"]):
    for (mod, fam, eff), g in by_level.groupby(["model", "familiarity", "effort"]):
        g = g.set_index("level").reindex(order)
        ax.plot(order, g[metric], marker="o", label=f"{mod}, {fam}, effort {eff}")
    ax.set_title(title)
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.3)
axes[0].set_ylabel("mean pass rate")
axes[0].legend(fontsize=7)
fig.tight_layout()
fig.savefig(OUT / "pass_vs_level.png", dpi=140)

summary = dict(n_runs=len(df), generated=time.strftime("%Y-%m-%dT%H:%M:%S"), models=sorted(df["model"].unique().tolist()),
               total_completion_tokens=int(df["completion_tokens"].sum()), total_prompt_tokens=int(df["prompt_tokens"].sum()),
               overall_success=float(df["success"].mean()))
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(table.to_string(index=False))
print(summary)
