"""Measure PuzzleClone spec-construction cost on a seed sample.

Runs the upstream langgraph pipeline once per seed with the ExternalApi shim,
which logs every model call. Writes one JSON line per seed with calls, tokens,
provider cost, and whether a final YAML was produced.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/cmy/Desktop/aaai_rebuttal")
PF = ROOT / "puzzle_forge"
SHIM = ROOT / "final_experiment/pf_cost"
OUT = ROOT / "final_experiment/pf_cost"
WORK = ROOT / "tmp/pf_sample"
PY = ROOT / "tmp/pfvenv/bin/python"
SEEDS = ["cipher_4", "logic_3", "logic_11", "operation_5", "operation_22",
         "word_sorting", "puzzle_15", "futoshiki", "arrow_maze", "skyscraper_puzzle"]
BUDGET = int(os.environ.get("PF_CALL_BUDGET", "25"))


def question(seed_id: str) -> str:
    for line in (ROOT / "sources/puzzleforge_supplement/data/seed_puzzles.jsonl").read_text().split("\n"):
        if not line.strip():
            continue
        row = json.loads(line)
        if row["id"] == seed_id:
            return row["question"] + " answer: " + json.dumps(row["answer"], ensure_ascii=False)
    raise KeyError(seed_id)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    summary_path = OUT / "pf_sample.jsonl"
    key = ""
    for line in (ROOT / ".env").read_text().split("\n"):
        if line.startswith("OPENAI_API_KEY="):
            key = line.split("=", 1)[1].strip()
    env = {
        **os.environ,
        "PATH": f"{PY.parent}:{os.environ['PATH']}",
        "PYTHONPATH": str(SHIM),
        "OPENAI_API_KEY": key,
        "PF_MAX_CALLS": str(BUDGET),
    }
    with summary_path.open("w", encoding="utf-8") as handle:
        for seed_id in SEEDS:
            usage_path = WORK / f"{seed_id}.usage.jsonl"
            usage_path.unlink(missing_ok=True)
            env["PF_USAGE_LOG"] = str(usage_path)
            work = WORK / seed_id
            command = [str(PY), "run_support_code_langgraph.py",
                       "-question", question(seed_id),
                       "-question_name", f"pf_{seed_id}",
                       "-output_folder", str(work),
                       "-workspace", str(PF)]
            record = {"seed_id": seed_id}
            try:
                done = subprocess.run(command, cwd=PF, env=env, capture_output=True,
                                      text=True, timeout=1200)
                record["returncode"] = done.returncode
                record["tail"] = done.stdout.strip().split("\n")[-3:]
            except subprocess.TimeoutExpired:
                record["returncode"] = "timeout"
            calls = []
            if usage_path.exists():
                calls = [json.loads(line) for line in usage_path.read_text().split("\n") if line.strip()]
            record.update({
                "calls": len(calls),
                "prompt_tokens": sum(c.get("prompt_tokens", 0) for c in calls),
                "completion_tokens": sum(c.get("completion_tokens", 0) for c in calls),
                "total_tokens": sum(c.get("total_tokens", 0) for c in calls),
                "cost": round(sum(float(c.get("cost") or 0) for c in calls), 5),
                "final_yaml": (work / "attempt_1/question_1/final_corrected_output.yaml").exists(),
            })
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
