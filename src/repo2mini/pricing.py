"""List prices in USD per 1M tokens and a cost estimate from logged token usage.

OpenAI rates are from https://developers.openai.com/api/docs/pricing (Standard tier, read 2026-11-01).
gpt-6-astra has a long context tier for requests above 272K input tokens that applies to the whole request.
Beam: OpenRouter listing, $0.25 in and $1 out per 1M tokens. The direct Reflection API was a free beta, so this is a list price
estimate and not what was paid. Beam cached input price is not published, so every Beam prompt token is billed at the input rate.
"""
from __future__ import annotations

PRICES = {
    "nemotron": dict(input=0.0, cached=0.0, output=0.0, source="openrouter free tier (nvidia/nemotron-3-ultra-550b-a55b:free)"),
    "beam": dict(input=0.25, cached=0.25, output=1.00, source="openrouter.ai/reflection/beam-1.0-501b-a23b (listing, not billed: free beta)"),
    "gpt41": dict(input=2.00, cached=0.50, output=8.00, source="developers.openai.com/api/docs/pricing"),
    "gpt52": dict(input=1.75, cached=0.175, output=14.00, source="developers.openai.com/api/docs/pricing"),
    "gpt6astra": dict(input=10.00, cached=1.00, output=50.00, long_threshold=272_000, long_input=20.00, long_cached=2.00, long_output=75.00,
                      source="developers.openai.com/api/docs/pricing"),
}


def request_cost(model: str, prompt: int, cached: int, completion: int) -> float:
    p = PRICES[model]
    long = prompt > p.get("long_threshold", float("inf"))
    rin = p["long_input"] if long else p["input"]
    rca = p["long_cached"] if long else p["cached"]
    rout = p["long_output"] if long else p["output"]
    cached = min(cached, prompt)
    return ((prompt - cached) * rin + cached * rca + completion * rout) / 1e6


def run_cost(model: str, steps: list[dict]) -> float:
    """Sum of request costs over all rounds of one run (each round is one request, with its own prompt, cached and completion tokens)."""
    return sum(request_cost(model, s["prompt_tokens"], s.get("cached", 0) or 0, s["completion_tokens"]) for s in steps)
