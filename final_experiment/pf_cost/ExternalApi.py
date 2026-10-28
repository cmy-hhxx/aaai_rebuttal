"""Minimal drop-in for PuzzleClone's missing ExternalApi, with token accounting.

The upstream pipeline imports ``DEEPSEEKClient`` / ``GPT5Client`` from a module that
is not shipped in the repository (it points at a private absolute path). This shim
implements only the surface the pipeline uses: async ``text2text({"messages": [...]})``
returning ``{"content": ...}`` and async ``close()``.

Every call is appended to ``$PF_USAGE_LOG`` as JSON with prompt/completion tokens
and the provider-reported cost, so a sample run can be priced.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.request
from pathlib import Path

ENDPOINT = os.environ.get(
    "PF_ENDPOINT",
    "https://internal-idc-equ.ainvest.com/ind/iwc-aime-model/litellm/v1/chat/completions",
)
MODEL = os.environ.get("PF_MODEL", "gpt-5.2")
KEY_ENV = os.environ.get("PF_KEY_ENV", "OPENAI_API_KEY")
LOG = Path(os.environ.get("PF_USAGE_LOG", "pf_usage.jsonl"))
MAX_CALLS = int(os.environ.get("PF_MAX_CALLS", "40"))
MAX_TOKENS = int(os.environ.get("PF_MAX_COMPLETION_TOKENS", "32768"))
TIMEOUT = float(os.environ.get("PF_TIMEOUT", "600"))


def _post(body: dict, key: str, tag: str) -> dict:
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as reply:
        return json.loads(reply.read().decode())


class GPT5Client:
    def __init__(self, model: str | None = None):
        self.model = model or MODEL
        self.key = os.environ.get(KEY_ENV, "")
        self.calls = 0
        self.tag = "gpt5"

    async def text2text(self, payload: dict) -> dict:
        messages = payload.get("messages") if isinstance(payload, dict) else None
        if not messages:
            raise ValueError("text2text requires {'messages': [...]}")
        if not self.key:
            raise RuntimeError(f"{KEY_ENV} is not set")
        if self.calls >= MAX_CALLS:
            raise RuntimeError(f"PF call budget exhausted ({MAX_CALLS})")
        self.calls += 1
        body = {"model": self.model, "messages": messages, "max_completion_tokens": MAX_TOKENS}
        started = time.time()
        data = await asyncio.to_thread(_post, body, self.key, self.tag)
        usage = data.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        record = {
            "time": started,
            "elapsed": round(time.time() - started, 3),
            "tag": self.tag,
            "call": self.calls,
            "model": self.model,
            "returned_model": data.get("model"),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": details.get("reasoning_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "cost": usage.get("cost", ""),
            "prompt_chars": sum(len(str(m.get("content", ""))) for m in messages),
        }
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        content = data["choices"][0]["message"]["content"]
        return {"content": content, "usage": usage}

    async def close(self) -> None:
        return None


class DEEPSEEKClient(GPT5Client):
    def __init__(self, model: str | None = None):
        super().__init__(model or os.environ.get("PF_DEEPSEEK_MODEL", "gpt-5.2"))
        self.tag = "deepseek"
