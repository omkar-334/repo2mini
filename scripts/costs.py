"""Cost metrics from logged token usage. Output: results/analyze/{costs_runs.csv,costs_by_model.csv,costs_by_model_task.csv,costs_summary.json}."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from repo2mini.pricing import PRICES, run_cost  # noqa: E402

OUT = ROOT / "results" / "analyze"
OUT.mkdir(parents=True, exist_ok=True)
rows = []
for f in (ROOT / "results/run_task/runs").glob("*/result.json"):
    r = json.loads(f.read_text())
    if r["task"] == "mini_autograd" or r["model"] not in PRICES:
        continue
    rows.append(dict(run_id=r["run_id"], model=r["model"], effort=r.get("effort") or "default", task=r["task"], level=r["level"],
                     setting=("bug fix" if "__fix" in r["task"] else ("agentic" if r["level"] == "AG" else ("long context" if r["level"] in ("XL", "XXL") else "write"))),
                     pass_rate=r["pass_rate"], success=float(r["success"]), cost_usd=run_cost(r["model"], r["steps"]),
                     prompt_tokens=sum(s["prompt_tokens"] for s in r["steps"]), completion_tokens=sum(s["completion_tokens"] for s in r["steps"])))
df = pd.DataFrame(rows)
df.to_csv(OUT / "costs_runs.csv", index=False)


def summarize(d, by):
    g = d.groupby(by).agg(runs=("run_id", "count"), total_cost=("cost_usd", "sum"), pass_rate=("pass_rate", "mean"), full_successes=("success", "sum"),
                          prompt_tokens=("prompt_tokens", "mean"), completion_tokens=("completion_tokens", "mean")).reset_index()
    g["cost_per_run"] = g["total_cost"] / g["runs"]
    g["cost_per_full_success"] = g["total_cost"] / g["full_successes"].where(g["full_successes"] > 0)
    g["pass_points_per_dollar"] = (g["pass_rate"] * g["runs"]) / g["total_cost"]
    return g.round(4)


by_model = summarize(df, ["model", "effort"])
summarize(df, ["setting", "model", "effort"]).to_csv(OUT / "costs_by_setting.csv", index=False)
by_model.to_csv(OUT / "costs_by_model.csv", index=False)
summarize(df, ["model", "effort", "task"]).to_csv(OUT / "costs_by_model_task.csv", index=False)
(OUT / "costs_summary.json").write_text(json.dumps({"prices_per_1M_tokens": PRICES, "total_cost_usd": round(float(df.cost_usd.sum()), 2),
                                                     "by_model": by_model.to_dict("records")}, indent=2, default=str))
print(summarize(df[df.effort.isin(["low", "default"])], ["setting", "model"])[["setting", "model", "runs", "cost_per_run", "pass_rate", "full_successes", "cost_per_full_success", "pass_points_per_dollar"]].to_string(index=False))
print()
print(by_model[["model", "effort", "runs", "total_cost", "cost_per_run", "pass_rate", "full_successes", "cost_per_full_success", "pass_points_per_dollar"]].to_string(index=False))
