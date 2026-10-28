"""Summarize measured API calls/usage without inventing missing prices or tokens."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def summarize_costs(log: Path) -> dict[str, Any]:
    events = [json.loads(line) for line in log.read_text().splitlines() if line.strip()] if log.exists() else []
    starts: dict[str, float] = {}
    totals: dict[str, dict[str, Any]] = {}
    for event in events:
        arm = event.get("tag", "unknown").split("/", 1)[0]
        group = totals.setdefault(arm, {"http_attempts": 0, "successful_requests": 0,
                                       "usage_reported_requests": 0, "prompt_tokens": 0,
                                       "completion_tokens": 0, "total_tokens": 0,
                                       "http_elapsed_seconds": 0.0, "failure_attempts": 0})
        kind, digest = event["event"], event.get("digest", "")
        if kind == "request_start":
            group["http_attempts"] += 1
            starts[digest] = event["time"]
        if kind in ("request_success", "request_failure"):
            if digest in starts:
                group["http_elapsed_seconds"] += max(0, event["time"] - starts.pop(digest))
            if kind == "request_failure":
                group["failure_attempts"] += 1
                continue
            group["successful_requests"] += 1
            usage = event.get("usage")
            if isinstance(usage, dict):
                group["usage_reported_requests"] += 1
                for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    if isinstance(usage.get(name), int):
                        group[name] += usage[name]
    return {"groups": totals, "note": "Token totals cover only fields actually returned by the provider; report usage coverage. Elapsed time sums HTTP attempts, excludes backoff/local execution/idle resumes. Dollar cost unavailable without actual pricing. PF historical cost unavailable."}
