"""Tiny connectivity check. Logs to results/ping/log.jsonl."""
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repo2mini.providers import Client  # noqa: E402

alias = sys.argv[1] if len(sys.argv) > 1 else "beam"
effort = sys.argv[2] if len(sys.argv) > 2 else None
out = Path(__file__).resolve().parents[1] / "results" / "ping"
out.mkdir(parents=True, exist_ok=True)
try:
    r = Client(alias).chat([{"role": "user", "content": 'How many Rs in "strawberry"? Answer briefly.'}], max_tokens=2000, effort=effort)
    row = dict(alias=alias, effort=effort, ok=True, text=r.text[:300], reasoning_chars=len(r.reasoning), prompt=r.prompt_tokens,
               completion=r.completion_tokens, finish=r.finish_reason, latency_s=round(r.latency_s, 2), model=r.model)
except Exception as e:
    row = dict(alias=alias, effort=effort, ok=False, error=str(e)[:500])
row["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
with (out / "log.jsonl").open("a") as f:
    f.write(json.dumps(row) + "\n")
print(json.dumps(row))
