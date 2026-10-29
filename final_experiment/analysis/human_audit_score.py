#!/usr/bin/env python3
"""Score the human audit: agreement, judge FPR/FNR, severity, post-stratified rates.

Fill runs/human_audit/audit_labels.csv first (two independent reviewers, plus an
adjudicator for disagreements).  This script never calls an API.

Definitions used here:
  judge-invalid  = the k=1 gpt-5.6-luna verdict is "invalid"
  confirmed      = human valid=0 and severity >= 2
  cosmetic       = human valid=0 and severity == 1
  judge error    = human valid=1 (severity 0)

A balanced sample (25 per method x verdict) is not a prevalence sample; the
post-stratified column re-weights the two verdict strata to their population
counts.  Report both, and never quote the raw sample rate as PF-86K's error rate.

Usage:
  python3 final_experiment/analysis/human_audit_score.py
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "runs" / "human_audit"
RUN = ROOT / "final_experiment" / "run"
LABELS = AUDIT / "audit_labels.csv"
OUT_MD = AUDIT / "REPORT.md"
OUT_JSON = AUDIT / "score.json"
METHOD_LABEL = {"puzzleforge": "PF", "framework": "B2", "direct": "B1"}


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def cohen_kappa(left: list[int], right: list[int]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    n = len(left)
    observed = sum(a == b for a, b in zip(left, right)) / n
    pa = sum(left) / n
    pb = sum(right) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return (observed - expected) / (1 - expected) if expected < 1 else None


def main() -> None:
    if not LABELS.exists():
        raise SystemExit(f"missing {LABELS}")
    key = {row["anon_id"]: row for row in jl(AUDIT / "audit_key.jsonl")}
    population = Counter()
    full_key = {row["anon_id"]: row for row in jl(RUN / "audit" / "audit_key.jsonl")}
    for row in jl(RUN / "auto" / "model_labels.jsonl"):
        judges = row.get("judges") or []
        if not judges or judges[0]["verdict"] not in ("valid", "invalid"):
            continue
        link = full_key.get(row["anon_id"])
        if link:
            population[(METHOD_LABEL[link["method"]], judges[0]["verdict"])] += 1

    rows = list(csv.DictReader(LABELS.open(encoding="utf-8", newline="")))
    by_item: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        if not str(row.get("valid", "")).strip():
            continue
        anon = str(row["anon_id"]).strip()
        reviewer = str(row.get("reviewer", "")).strip()
        if not anon or not reviewer:
            continue
        by_item[anon][reviewer] = row

    resolved = {}
    for anon, reviews in by_item.items():
        independent = {name: row for name, row in reviews.items() if name in ("reviewer_1", "reviewer_2")}
        values = []
        for row in independent.values():
            raw = str(row["valid"]).strip()
            if raw in ("0", "1"):
                values.append(int(raw))
        if len(independent) == 2 and len(values) == 2 and values[0] == values[1]:
            chosen = next(iter(independent.values()))
            resolved[anon] = _parse(chosen)
        elif "adjudicator" in reviews and str(reviews["adjudicator"]["valid"]).strip() in ("0", "1"):
            resolved[anon] = _parse(reviews["adjudicator"])

    if not resolved:
        report = ("# Human audit report\n\n"
                  "No resolved labels yet. Fill `audit_labels.csv` with two independent "
                  "reviewers (and an adjudicator for disagreements), then rerun "
                  "`human_audit_score.py`.\n")
        OUT_MD.write_text(report, encoding="utf-8")
        OUT_JSON.write_text(json.dumps({"resolved": 0, "note": "no labels"}, indent=2), encoding="utf-8")
        print(report)
        return

    # reviewer agreement on the items both reviewers labelled
    both = []
    for anon, reviews in by_item.items():
        if "reviewer_1" in reviews and "reviewer_2" in reviews:
            a = str(reviews["reviewer_1"]["valid"]).strip()
            b = str(reviews["reviewer_2"]["valid"]).strip()
            if a in ("0", "1") and b in ("0", "1"):
                both.append((int(a), int(b)))
    kappa = cohen_kappa([a for a, _ in both], [b for _, b in both])
    agreement = sum(a == b for a, b in both) / len(both) if both else None

    per_method = {}
    for method in ("puzzleforge", "framework", "direct"):
        name = METHOD_LABEL[method]
        subset = [(anon, value) for anon, value in resolved.items()
                  if key[anon]["method"] == method]
        if not subset:
            continue
        judge_invalid = [(anon, value) for anon, value in subset if key[anon]["judge_verdict"] == "invalid"]
        judge_valid = [(anon, value) for anon, value in subset if key[anon]["judge_verdict"] == "valid"]
        confirmed = sum(1 for _, value in judge_invalid if value["valid"] == 0 and (value["severity"] or 0) >= 2)
        cosmetic = sum(1 for _, value in judge_invalid if value["valid"] == 0 and value["severity"] == 1)
        false_alarm = sum(1 for _, value in judge_invalid if value["valid"] == 1)
        missed = sum(1 for _, value in judge_valid if value["valid"] == 0)
        p_invalid_given_invalid = confirmed / len(judge_invalid) if judge_invalid else None
        p_invalid_given_valid = missed / len(judge_valid) if judge_valid else None
        n_pop_valid = population[(name, "valid")]
        n_pop_invalid = population[(name, "invalid")]
        n_pop = n_pop_valid + n_pop_invalid
        true_invalid = ((n_pop_valid * (p_invalid_given_valid or 0)
                         + n_pop_invalid * (p_invalid_given_invalid or 0)) / n_pop)
        per_method[name] = {
            "resolved": len(subset),
            "judge_invalid_sampled": len(judge_invalid),
            "judge_valid_sampled": len(judge_valid),
            "confirmed_invalid": confirmed,
            "cosmetic": cosmetic,
            "judge_false_alarm": false_alarm,
            "judge_missed": missed,
            "confirmed_rate_given_judge_invalid": p_invalid_given_invalid,
            "confirmed_ci": wilson(confirmed, len(judge_invalid)),
            "cosmetic_rate": cosmetic / len(judge_invalid) if judge_invalid else None,
            "false_alarm_rate": false_alarm / len(judge_invalid) if judge_invalid else None,
            "false_alarm_ci": wilson(false_alarm, len(judge_invalid)),
            "false_negative_rate": p_invalid_given_valid,
            "population": {"valid": n_pop_valid, "invalid": n_pop_invalid},
            "post_stratified_true_invalid_rate": true_invalid,
        }

    # per judge error type
    by_error = defaultdict(lambda: {"n": 0, "confirmed": 0, "cosmetic": 0, "false_alarm": 0})
    for anon, value in resolved.items():
        if key[anon]["judge_verdict"] != "invalid":
            continue
        errors = key[anon].get("judge_error_types") or ["other"]
        for error in errors:
            cell = by_error[error]
            cell["n"] += 1
            cell["confirmed"] += value["valid"] == 0 and (value["severity"] or 0) >= 2
            cell["cosmetic"] += value["valid"] == 0 and value["severity"] == 1
            cell["false_alarm"] += value["valid"] == 1

    lines = ["# Human audit report", "",
             f"Resolved items: {len(resolved)} / {len(key)} sampled. "
             f"Reviewer-1 vs reviewer-2 agreement: "
             f"{agreement:.1%} (n={len(both)}); Cohen's kappa: {kappa:.3f}." if both else
             "No item has two independent labels yet.", "",
             "A judge-invalid call is confirmed only if the human marks valid=0 and "
             "severity >= 2.  severity 1 is cosmetic (rounding/format) and is reported "
             "separately.  The post-stratified rate re-weights the judge-valid and "
             "judge-invalid strata to their population counts.", "",
             "| method | resolved | judge-invalid sampled | confirmed | cosmetic | judge false alarm | confirmed rate [95% CI] | false-alarm rate [95% CI] | false-negative rate | post-stratified invalid rate |",
             "|---|---:|---:|---:|---:|---:|---|---|---|---:|"]
    for name in ("PF", "B2", "B1"):
        cell = per_method.get(name)
        if not cell:
            continue
        ci = cell["confirmed_ci"]
        fci = cell["false_alarm_ci"]
        def fmt(value, interval):
            if value is None:
                return "n/a"
            if interval and interval[0] is not None:
                return f"{value:.3f} [{interval[0]:.3f}, {interval[1]:.3f}]"
            return f"{value:.3f}"
        lines.append(
            f"| {name} | {cell['resolved']} | {cell['judge_invalid_sampled']} | "
            f"{cell['confirmed_invalid']} | {cell['cosmetic']} | {cell['judge_false_alarm']} | "
            f"{fmt(cell['confirmed_rate_given_judge_invalid'], ci)} | "
            f"{fmt(cell['false_alarm_rate'], fci)} | "
            f"{fmt(cell['false_negative_rate'], None)} | "
            f"{fmt(cell['post_stratified_true_invalid_rate'], None)} |"
        )
    lines += ["", "## By judge error type", "",
              "| judge error type | sampled | confirmed | cosmetic | judge false alarm | confirmed share |",
              "|---|---:|---:|---:|---:|---:|"]
    for error, cell in sorted(by_error.items(), key=lambda kv: -kv[1]["n"]):
        share = cell["confirmed"] / cell["n"] if cell["n"] else None
        lines.append(f"| {error} | {cell['n']} | {cell['confirmed']} | {cell['cosmetic']} | "
                     f"{cell['false_alarm']} | {share:.2f} |" if share is not None else
                     f"| {error} | {cell['n']} | {cell['confirmed']} | {cell['cosmetic']} | {cell['false_alarm']} | - |")
    lines += ["", "## How to read this", "",
              "- If PF's confirmed rate given judge-invalid is high, the 23.1% invalid "
              "rate is a real dataset issue, not judge noise; report it in the paper and "
              "release corrected labels.",
              "- If the false-alarm rate is high, the B1 gap is partly a judge artifact; "
              "report the corrected gap, not the raw +0.484.",
              "- Post-stratified rates are still model/human estimates, not ground truth; "
              "state the sample size and the balanced design."]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps({
        "resolved": len(resolved), "agreement": agreement, "kappa": kappa,
        "per_method": per_method, "by_error": by_error,
        "population": {f"{k[0]}:{k[1]}": v for k, v in population.items()},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT_MD)
    print(OUT_JSON)


def _parse(row: dict) -> dict:
    severity = str(row.get("severity", "")).strip()
    return {
        "valid": int(str(row["valid"]).strip()),
        "severity": int(severity) if severity in ("0", "1", "2", "3") else None,
        "error_type": str(row.get("error_type", "")).strip(),
        "evidence": str(row.get("evidence", "")).strip(),
    }


if __name__ == "__main__":
    main()
