"""Uniform chat interface over OpenAI compatible endpoints, plus a mock for plumbing tests."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# alias -> (provider, model id, base_url, key env). Vercel base url and model id verified 2026-10-31 via GET /v1/models (reflection/beam-free, 1,048,576 ctx, 131072 max out, implicit-caching, free).
MODELS = {
    "beam": ("reflection", "Beam-1.0-501B-A23B", "https://api.reflection.ai/openai/v1", "REFLECTION_API_KEY"),
    "beam-vercel": ("vercel", "reflection/beam-free", "https://ai-gateway.vercel.sh/v1", "AI_GATEWAY_API_KEY"),
    "openai": ("openai", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"), None, "OPENAI_API_KEY"),
    "gpt41": ("openai", "gpt-4.1", None, "OPENAI_API_KEY"),
    "gpt52": ("openai", "gpt-5.2", None, "OPENAI_API_KEY"),
    "gpt6astra": ("openai", "gpt-6-astra", None, "OPENAI_API_KEY"),
    "nemotron": ("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "gptoss": ("groq", "openai/gpt-oss-120b", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "qwen27": ("groq", "qwen/qwen3.8-27b", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "mock": ("mock", "mock", None, ""),
}


@dataclass
class ChatResult:
    text: str
    reasoning: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    finish_reason: str = ""
    tool_calls: list = field(default_factory=list)  # [{id, name, arguments}]
    message: dict = field(default_factory=dict)  # assistant message to append to history
    latency_s: float = 0.0
    model: str = ""
    extra: dict = field(default_factory=dict)


def _usage(u) -> tuple[int, int, int]:
    if u is None:
        return 0, 0, 0
    details = getattr(u, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0) or 0 if details else 0
    return u.prompt_tokens or 0, u.completion_tokens or 0, cached


class Client:
    def __init__(self, alias: str):
        if alias not in MODELS:
            raise ValueError(f"unknown model alias {alias}, choose from {list(MODELS)}")
        self.alias = alias
        self.provider, self.model, base_url, key_env = MODELS[alias]
        self._mock = None
        if self.provider == "mock":
            return
        key = os.environ.get(key_env, "")
        if not key:
            raise RuntimeError(f"{key_env} is not set. Put it in .env")
        from openai import OpenAI

        self._client = OpenAI(base_url=base_url, api_key=key, timeout=600, max_retries=0)

    # models whose reasoning cannot be combined with function tools on chat completions use the Responses API in tool conversations
    RESPONSES_FOR_TOOLS = {"gpt6astra"}

    def _uses_responses(self, messages, tools) -> bool:
        return self.alias in self.RESPONSES_FOR_TOOLS and (bool(tools) or any(m.get("tool_calls") or m["role"] == "tool" for m in messages))

    @staticmethod
    def _responses_input(messages):
        """Chat style history to Responses items. Resumes from the last reply that carries a response_id."""
        last = max((i for i, m in enumerate(messages) if m["role"] == "assistant" and m.get("response_id")), default=-1)
        prev = messages[last]["response_id"] if last >= 0 else None
        items = []
        for m in messages[last + 1:]:
            if m["role"] in ("user", "system"):
                items.append({"role": m["role"], "content": m["content"]})
            elif m["role"] == "assistant":
                if m.get("content"):
                    items.append({"role": "assistant", "content": m["content"]})
                for tc in m.get("tool_calls", []):
                    items.append({"type": "function_call", "call_id": tc["id"], "name": tc["function"]["name"], "arguments": tc["function"]["arguments"]})
            elif m["role"] == "tool":
                items.append({"type": "function_call_output", "call_id": m["tool_call_id"], "output": m["content"]})
        return prev, items

    def _chat_responses(self, messages, max_tokens, effort, tools, retries=4) -> ChatResult:
        prev, items = self._responses_input(messages)
        kwargs: dict = {"model": self.model, "input": items, "max_output_tokens": max_tokens}
        if prev:
            kwargs["previous_response_id"] = prev
        if effort:
            kwargs["reasoning"] = {"effort": effort}
        if tools:
            kwargs["tools"] = [{"type": "function", "name": t["function"]["name"], "description": t["function"]["description"],
                                "parameters": t["function"]["parameters"]} for t in tools]
        last = None
        for attempt in range(retries + 1):
            t0 = time.time()
            try:
                r = self._client.responses.create(**kwargs)
                calls = [{"id": it.call_id, "name": it.name, "arguments": it.arguments} for it in r.output if it.type == "function_call"]
                u = r.usage
                cached = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
                msg = {"role": "assistant", "content": r.output_text or "", "response_id": r.id}
                if calls:
                    msg["tool_calls"] = [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls]
                return ChatResult(text=r.output_text or "", prompt_tokens=u.input_tokens, completion_tokens=u.output_tokens, cached_tokens=cached,
                                  finish_reason=getattr(r, "status", "") or "", tool_calls=calls, message=msg, latency_s=time.time() - t0,
                                  model=getattr(r, "model", self.model))
            except Exception as e:
                last = e
                status = getattr(e, "status_code", None)
                if status is not None and status < 500 and status != 429:
                    raise
                time.sleep(min(2 ** attempt * 2, 30))
        raise RuntimeError(f"responses call failed after retries: {last}")

    def chat(self, messages: list[dict], *, max_tokens: int = 16000, temperature: float | None = 0.7,
             top_p: float | None = None, effort: str | None = None, retries: int = 4, tools: list | None = None) -> ChatResult:
        if self.provider == "mock":
            return self._mock_chat(messages)
        if self._uses_responses(messages, tools):
            return self._chat_responses(messages, max_tokens, effort, tools, retries)
        kwargs: dict = {"model": self.model, "messages": messages}
        if self.provider == "openai":
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                kwargs["temperature"] = temperature
            if top_p is not None:
                kwargs["top_p"] = top_p
        if effort:
            kwargs["extra_body"] = {"reasoning_effort": effort}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        last = None
        for attempt in range(retries + 1):
            t0 = time.time()
            try:
                r = self._client.chat.completions.create(**kwargs)
                m = r.choices[0].message
                p, c, cached = _usage(r.usage)
                reasoning = getattr(m, "reasoning_content", None) or getattr(m, "reasoning", None) or ""
                calls = [{"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments} for tc in (m.tool_calls or [])]
                msg = {"role": "assistant", "content": m.content or ""}
                if calls:
                    msg["tool_calls"] = [{"id": c_["id"], "type": "function", "function": {"name": c_["name"], "arguments": c_["arguments"]}} for c_ in calls]
                if reasoning:  # Beam rejects history that drops earlier reasoning_content
                    msg["reasoning_content"] = reasoning
                return ChatResult(text=m.content or "", reasoning=reasoning, prompt_tokens=p, completion_tokens=c,
                                  cached_tokens=cached, finish_reason=r.choices[0].finish_reason or "", tool_calls=calls, message=msg,
                                  latency_s=time.time() - t0, model=r.model or self.model)
            except Exception as e:  # network, 429, 5xx
                last = e
                status = getattr(e, "status_code", None)
                if status is not None and status < 500 and status != 429:
                    raise
                time.sleep(min(2 ** attempt * 2, 30))
        raise RuntimeError(f"chat failed after retries: {last}")

    # mock: replays reference/broken then reference/solution so the whole loop is exercisable offline
    def _mock_chat(self, messages: list[dict]) -> ChatResult:
        from .tasks import load_task

        task_id = next((m["content"].split("TASK_ID:")[1].split()[0] for m in messages if "TASK_ID:" in m["content"]), None)
        task = load_task(task_id)
        n_assistant = sum(1 for m in messages if m["role"] == "assistant")
        folder = "broken" if n_assistant == 0 and (task.root / "reference" / "broken").exists() else "solution"
        body = ""
        for f in sorted((task.root / "reference" / folder).glob("*.py")):
            body += f"FILE: solution/{f.name}\n```python\n{f.read_text()}\n```\n"
        return ChatResult(text=body, prompt_tokens=sum(len(m["content"]) // 4 for m in messages),
                          completion_tokens=len(body) // 4, finish_reason="stop", model="mock")
