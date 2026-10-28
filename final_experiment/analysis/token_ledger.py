"""Consolidate every paid request in a run into a per-request token ledger.

Reads generation and judge api_cache/requests.jsonl files. Usage is only counted
for successful HTTP responses; failed attempts are listed with zero tokens so the
attempt count and failure tax remain visible.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def usage_of(event: dict[str, Any]) -> dict[str, Any]:
    return event.get("usage") or {}


def classify(tag: str, key: dict[str, dict[str, Any]]) -> tuple[str, str, str]:
    parts = tag.split(":")
    if tag.startswith("automatic-panel"):
        stage = "judge_solve" if parts[2] == "solve" else "judge_verdict"
        link = key.get(parts[1], {})
        return stage, link.get("method", "unknown"), link.get("seed_id", "unknown")
    head = tag.split("/")
    if head[0] in ("direct", "framework"):
        return "generate", head[0], head[1]
    return "other", "unknown", "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--judge-dir", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    run, out = args.run.resolve(), (args.out or args.run).resolve()
    out.mkdir(parents=True, exist_ok=True)
    key = {row["anon_id"]: row for row in read_jsonl(run / "audit/audit_key.jsonl")} \
        if (run / "audit/audit_key.jsonl").exists() else {}

    logs = [run / "api_cache/requests.jsonl"] + [d / "api_cache/requests.jsonl" for d in args.judge_dir]
    rows: list[dict[str, Any]] = []
    for log in logs:
        if not log.exists():
            continue
        starts = {json.loads(line)["digest"]: json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()}
        for event in read_jsonl(log):
            if event.get("event") != "request_success":
                continue
            usage = usage_of(event)
            stage, method, seed = classify(event["tag"], key)
            details = usage.get("completion_tokens_details") or {}
            rows.append({
                "stage": stage,
                "method": method,
                "seed": seed,
                "model": event.get("response_model") or "",
                "tag": event["tag"],
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "reasoning_tokens": details.get("reasoning_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "cost": usage.get("cost", ""),
                "time": event.get("time", ""),
            })

    rows.sort(key=lambda r: (r["stage"], r["method"], r["seed"], r["tag"]))
    fields = ["stage", "method", "seed", "model", "tag", "prompt_tokens", "completion_tokens",
              "reasoning_tokens", "total_tokens", "cost", "time"]
    with (out / "tokens_requests.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, Any] = {"requests": len(rows), "by_stage": {}, "by_method": {}, "by_model": {}}
    for group in ("stage", "method", "model"):
        bucket: dict[str, dict[str, float]] = defaultdict(lambda: {"requests": 0, "prompt": 0, "completion": 0,
                                                                   "reasoning": 0, "total": 0, "cost": 0.0})
        for row in rows:
            item = bucket[row[group]]
            item["requests"] += 1
            item["prompt"] += row["prompt_tokens"]
            item["completion"] += row["completion_tokens"]
            item["reasoning"] += row["reasoning_tokens"]
            item["total"] += row["total_tokens"]
            try:
                item["cost"] += float(row["cost"])
            except (TypeError, ValueError):
                pass
        summary[f"by_{group}"] = dict(bucket)
    summary["total"] = {
        "requests": len(rows),
        "prompt": sum(r["prompt_tokens"] for r in rows),
        "completion": sum(r["completion_tokens"] for r in rows),
        "reasoning": sum(r["reasoning_tokens"] for r in rows),
        "total": sum(r["total_tokens"] for r in rows),
        "cost": sum(float(r["cost"]) for r in rows if str(r["cost"]).strip()),
    }
    (out / "tokens_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=float) + "\n",
                                             encoding="utf-8")
    print(json.dumps(summary["total"], ensure_ascii=False))


if __name__ == "__main__":
    main()
