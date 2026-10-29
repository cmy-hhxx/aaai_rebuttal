#!/usr/bin/env python3
"""Draw a stratified human-audit sample for the rebuttal.

The sample is balanced on method x judge verdict (25 per cell, 150 total) and,
within the invalid cells, round-robins over the judge's error types so that
wrong-answer, ambiguity, missing-constraint, unsatisfiable and rendering calls
are all represented.  Selection is deterministic (hash order), and the sealed
key is written separately from the blind sheet.

Outputs under runs/human_audit/:
  audit_blind.jsonl   anon_id, problem, answer        (give this to reviewers)
  audit_key.jsonl     sealed mapping + judge labels   (do not give to reviewers)
  audit_labels.csv    empty template, 2 reviewers + adjudicator
  INSTRUCTIONS.md     annotation protocol (EN + ZH)
  SAMPLING.md         counts and caveats

Usage:
  python3 final_experiment/analysis/human_audit_sample.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "final_experiment" / "run"
OUT = ROOT / "runs" / "human_audit"
SEED = "human-audit-20261029"
PER_CELL = 25
METHODS = ("puzzleforge", "framework", "direct")
LABEL_METHOD = {"puzzleforge": "PF", "framework": "B2", "direct": "B1"}


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def order(anon: str) -> str:
    return hashlib.sha256(f"{SEED}|{anon}".encode()).hexdigest()


key = {row["anon_id"]: row for row in jl(RUN / "audit" / "audit_key.jsonl")}
blind = {row["anon_id"]: row for row in jl(RUN / "audit" / "audit_blind.jsonl")}
labels = {row["anon_id"]: row for row in jl(RUN / "auto" / "model_labels.jsonl")}

strata: dict[tuple[str, str], list[dict]] = defaultdict(list)
for anon, link in key.items():
    row = labels.get(anon) or {}
    judges = row.get("judges") or []
    if not judges:
        continue
    judge = judges[0]
    verdict = judge["verdict"]
    if verdict not in ("valid", "invalid"):
        continue
    strata[(link["method"], verdict)].append({
        "anon_id": anon,
        "method": link["method"],
        "seed_id": link["seed_id"],
        "id": link["id"],
        "slot": link["slot"],
        "verdict": verdict,
        "error_types": list(judge.get("error_types") or []),
        "depth": judge.get("depth_score"),
        "solver_correct": (judge.get("solver_correct") or [None])[0],
        "problem": blind[anon].get("problem", ""),
        "answer": blind[anon].get("answer"),
        "length": len(blind[anon].get("problem", "")),
    })

sample: list[dict] = []
for method in METHODS:
    for verdict in ("valid", "invalid"):
        pool = strata[(method, verdict)]
        if verdict == "valid":
            picked = sorted(pool, key=lambda r: order(r["anon_id"]))[:PER_CELL]
        else:
            groups: dict[str, list[dict]] = defaultdict(list)
            for row in pool:
                primary = row["error_types"][0] if row["error_types"] else "other"
                groups[primary].append(row)
            for rows in groups.values():
                rows.sort(key=lambda r: order(r["anon_id"]))
            picked = []
            names = sorted(groups)
            index = 0
            while len(picked) < PER_CELL and any(groups[name] for name in names):
                name = names[index % len(names)]
                if groups[name]:
                    picked.append(groups[name].pop(0))
                index += 1
        for row in picked:
            row["stratum"] = f"{LABEL_METHOD[method]}:{verdict}"
        sample.extend(picked)

sample.sort(key=lambda r: order(r["anon_id"]))
assert len(sample) == 6 * PER_CELL, len(sample)
assert len({r["anon_id"] for r in sample}) == len(sample)

OUT.mkdir(parents=True, exist_ok=True)
with (OUT / "audit_blind.jsonl").open("w", encoding="utf-8") as handle:
    for row in sample:
        handle.write(json.dumps({
            "anon_id": row["anon_id"],
            "problem": row["problem"],
            "answer": row["answer"],
        }, ensure_ascii=False) + "\n")

with (OUT / "audit_key.jsonl").open("w", encoding="utf-8") as handle:
    for row in sample:
        handle.write(json.dumps({
            "anon_id": row["anon_id"],
            "id": row["id"],
            "method": row["method"],
            "seed_id": row["seed_id"],
            "slot": row["slot"],
            "judge_verdict": row["verdict"],
            "judge_error_types": row["error_types"],
            "judge_depth": row["depth"],
            "judge_solver_correct": row["solver_correct"],
            "stratum": row["stratum"],
        }, ensure_ascii=False) + "\n")

with (OUT / "audit_labels.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=[
        "anon_id", "reviewer", "valid", "severity", "error_type", "evidence", "notes",
    ])
    writer.writeheader()
    for row in sample:
        for reviewer in ("reviewer_1", "reviewer_2", "adjudicator"):
            writer.writerow({"anon_id": row["anon_id"], "reviewer": reviewer})

counts = Counter(row["stratum"] for row in sample)
errors = Counter(error for row in sample for error in row["error_types"])

instructions = f"""# Human audit of the blind sample

Give reviewers only `audit_blind.jsonl`.  Keep `audit_key.jsonl` sealed until both
reviewers have submitted.  The sample is stratified on method x judge verdict
({PER_CELL} per cell, 150 items); it is not a prevalence sample of PF-86K.

## For each item (problem + canonical answer)

1. `valid`: 1 if the problem is complete, consistent, solvable as written, and the
   canonical answer is correct; otherwise 0.  If the problem is ambiguous or has
   missing constraints, mark 0 even if the canonical answer is plausible.
2. `severity` (only for valid=0):
   - 0 = the item is actually fine (judge false positive),
   - 1 = cosmetic: rounding/format/rendering issue, but the intended answer is
     recoverable and the puzzle is solvable,
   - 2 = substantive: ambiguous, missing constraint, unsatisfiable, or wrong
     answer for part of the item,
   - 3 = fatal: canonical answer is wrong, no answer, or the item cannot be used.
3. `error_type`: one of `none`, `wrong_answer`, `ambiguous`, `missing_constraint`,
   `unsatisfiable`, `rendering`, `other`.
4. `evidence`: one concrete check, counterexample, or the exact fix.  No
   "looks fine"; state what you verified.
5. Do not use the item's style, language, or length to guess its method.  Two
   reviewers work independently; `adjudicator` fills only disagreements.

## Reporting

`human_audit_score.py` computes per-method agreement, judge false-positive rate
on judge-invalid items, judge false-negative rate on judge-valid items, and a
severity breakdown.  A judge-invalid call is "confirmed" only if the human marks
valid=0 and severity >= 2; severity 1 is reported separately as cosmetic.

## 中文说明

- 只把 `audit_blind.jsonl` 给审核者；`audit_key.jsonl` 封存到两人提交后。
- `valid=1` 要求题面完整、可解、规范答案正确；`valid=0` 时填 severity：
  0=judge 误判、1=舍入/格式瑕疵、2=实质问题、3=致命错误。
- 每条必须写可核验的 evidence，不能只写“没问题”。
- 两位审核者独立完成，分歧由 adjudicator 裁决。
"""
(OUT / "INSTRUCTIONS.md").write_text(instructions, encoding="utf-8")

sampling = ["# Sampling report", "",
            f"Seed: `{SEED}`; {PER_CELL} items per method x judge-verdict cell; {len(sample)} total.", "",
            "| stratum | n |", "|---|---:|"]
for name in sorted(counts):
    sampling.append(f"| {name} | {counts[name]} |")
sampling += ["", "Judge error types represented among the 75 invalid items:", "",
             "| judge error type | n |", "|---|---:|"]
for name, count in errors.most_common():
    sampling.append(f"| {name} | {count} |")
sampling += ["", "The sample is balanced by judge verdict, so raw agreement is not a "
             "prevalence estimate. The scorer post-stratifies to the population counts.",
             "", "Population (judge labels, all 1,440):", ""]
population = Counter((LABEL_METHOD[link["method"]], (labels.get(anon) or {}).get("judges", [{}])[0].get("verdict"))
                     for anon, link in key.items() if (labels.get(anon) or {}).get("judges"))
sampling += ["| stratum | population |", "|---|---:|"]
for name, count in sorted(population.items()):
    if name[0] in LABEL_METHOD.values() and name[1] in ("valid", "invalid"):
        sampling.append(f"| {name[0]}:{name[1]} | {count} |")
(OUT / "SAMPLING.md").write_text("\n".join(sampling) + "\n", encoding="utf-8")

print(OUT)
print(json.dumps({"total": len(sample), "strata": dict(sorted(counts.items())),
                  "error_types": dict(errors.most_common())}, ensure_ascii=False, indent=2))
