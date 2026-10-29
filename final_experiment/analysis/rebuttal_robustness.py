#!/usr/bin/env python3
"""Robustness checks for the rebuttal's depth and cost claims.

Reads only frozen artifacts under final_experiment/run; never calls an API.

Why this exists: the seed-level depth gap (PF - B2 = +0.60) is confounded by
problem length (median 692 vs 321 chars), and the cost table mixed amortisation
scales (PF at 200 instances/generator vs B2 at 20/seed).  This script adds
length-matched estimates, a single-subquestion subgroup, length-stratified
yield, and a scale-consistent cost table.

Outputs:
  final_experiment/run/analysis/rebuttal_robustness.json
  final_experiment/run/analysis/rebuttal_robustness.md   (ASCII tables)

Usage:
  python3 final_experiment/analysis/rebuttal_robustness.py
"""
from __future__ import annotations

import json
import math
import random
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "final_experiment" / "run"
OUT_JSON = RUN / "analysis" / "rebuttal_robustness.json"
OUT_MD = RUN / "analysis" / "rebuttal_robustness.md"
RNG_SEED = 20261029


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def dwidth(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def table(header: list[str], rows: list[list[str]], aligns: str) -> str:
    widths = [max(dwidth(str(r[i])) for r in [header, *rows]) for i in range(len(header))]
    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def line(row: list[str]) -> str:
        cells = []
        for i, value in enumerate(row):
            gap = widths[i] - dwidth(str(value))
            text = (" " * gap + str(value)) if aligns[i] == "r" else str(value) + " " * gap
            cells.append(" " + text + " ")
        return "|" + "|".join(cells) + "|"

    out = [border, line(header), border]
    for row in rows:
        if row[0] == "-":
            out.append(border)
        else:
            out.append(line(row))
    out.append(border)
    return "\n".join(out)


# ---------------------------------------------------------------- data

key = {row["anon_id"]: row for row in jl(RUN / "audit" / "audit_key.jsonl")}
blind = {row["anon_id"]: row for row in jl(RUN / "audit" / "audit_blind.jsonl")}
labels = {row["anon_id"]: row for row in jl(RUN / "auto" / "model_labels.jsonl")}
records = {row["id"]: row for row in jl(RUN / "records_selected.jsonl")}

items: list[dict] = []
for anon, link in key.items():
    judges = (labels.get(anon) or {}).get("judges") or []
    if not judges:
        continue
    judge = judges[0]
    record = records[link["id"]]
    answer = str(blind[anon].get("answer") or "")
    items.append({
        "anon": anon,
        "method": link["method"],
        "seed": link["seed_id"],
        "generator": record.get("generator_id"),
        "slot": record.get("slot"),
        "length": len(blind[anon]["problem"]),
        "subanswers": answer.count("====") + 1 if answer.strip() else 0,
        "verdict": judge["verdict"],
        "valid": judge["verdict"] == "valid",
        "depth": judge.get("depth_score"),
        "solver": (judge.get("solver_correct") or [None])[0],
        "tags_r": tuple(sorted(judge.get("reasoning_type_tags") or [])),
        "tags_c": tuple(sorted(judge.get("constraint_type_tags") or [])),
        "available": True,
    })

# Unavailable slots are kept in the per-slot denominator, as in T1/T3.
# Their length is the median of the same (method, seed); only 26 items are affected.
seed_medians = defaultdict(list)
for row in items:
    seed_medians[(row["method"], row["seed"])].append(row["length"])
medians = {k: statistics.median(v) for k, v in seed_medians.items()}
for anon, link in key.items():
    lab = labels.get(anon) or {}
    if lab.get("status") != "unavailable":
        continue
    record = records[link["id"]]
    items.append({
        "anon": anon, "method": link["method"], "seed": link["seed_id"],
        "generator": record.get("generator_id"), "slot": record.get("slot"),
        "length": medians.get((link["method"], link["seed_id"]), 0),
        "subanswers": 0, "verdict": "unavailable", "valid": False,
        "depth": None, "solver": None, "tags_r": (), "tags_c": (), "available": False,
    })

PF = [x for x in items if x["method"] == "puzzleforge"]
B2 = [x for x in items if x["method"] == "framework"]
B1 = [x for x in items if x["method"] == "direct"]
PFV = [x for x in PF if x["valid"] and x["depth"] is not None]
B2V = [x for x in B2 if x["valid"] and x["depth"] is not None]
B1V = [x for x in B1 if x["valid"] and x["depth"] is not None]

assert len(items) == 1440, len(items)


def summarize(rows: list[dict]) -> dict:
    valid = [x for x in rows if x["valid"]]
    depths = [x["depth"] for x in valid if x["depth"] is not None]
    return {
        "n": len(rows),
        "valid": len(valid),
        "validity": len(valid) / len(rows) if rows else None,
        "depth_mean": statistics.fmean(depths) if depths else None,
        "ge3": sum(1 for d in depths if d >= 3),
        "ge3_rate": sum(1 for d in depths if d >= 3) / len(rows) if rows else None,
        "length_median": statistics.median([x["length"] for x in rows if x.get("available", True)]) if rows else None,
        "subanswers_mean": statistics.fmean([x["subanswers"] for x in rows]) if rows else None,
    }


summary = {m: summarize(rows) for m, rows in (("PF", PF), ("B2", B2), ("B1", B1))}

# ---------------------------------------------------------------- OLS

def ols_gap(rows: list[dict], seed_fe: bool = False) -> float:
    y = np.array([r["depth"] for r in rows], dtype=float)
    cols = [
        np.ones(len(rows)),
        np.array([1.0 if r["method"] == "puzzleforge" else 0.0 for r in rows]),
        np.log(np.array([r["length"] for r in rows], dtype=float)),
    ]
    if seed_fe:
        seeds = sorted({r["seed"] for r in rows})
        for seed in seeds[1:]:
            cols.append(np.array([1.0 if r["seed"] == seed else 0.0 for r in rows]))
    design = np.column_stack(cols)
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(beta[1])


def cluster_boot_ols(rows: list[dict], seed_fe: bool, draws: int = 1000) -> tuple[float, float]:
    by_seed = defaultdict(list)
    for row in rows:
        by_seed[row["seed"]].append(row)
    seeds = sorted(by_seed)
    rng = np.random.default_rng(RNG_SEED + int(seed_fe))
    values = []
    for _ in range(draws):
        picked = rng.choice(seeds, size=len(seeds), replace=True)
        sample = [row for seed in picked for row in by_seed[seed]]
        values.append(ols_gap(sample, seed_fe))
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


pf_b2 = PFV + B2V
ols = {
    "raw": statistics.fmean(r["depth"] for r in PFV) - statistics.fmean(r["depth"] for r in B2V),
    "log_length": ols_gap(pf_b2, False),
    "log_length_ci": cluster_boot_ols(pf_b2, False),
    "log_length_seed_fe": ols_gap(pf_b2, True),
    "log_length_seed_fe_ci": cluster_boot_ols(pf_b2, True),
    "n": [len(PFV), len(B2V)],
}

# ---------------------------------------------------------------- length matching

def loglen(x: dict) -> float:
    return math.log(x["length"])


def nearest_length_pairs(pf_rows: list[dict], b2_rows: list[dict], caliper: float) -> tuple[list[tuple[dict, dict]], int]:
    by_seed = defaultdict(list)
    for row in b2_rows:
        by_seed[row["seed"]].append(row)
    pairs, unmatched = [], 0
    for row in pf_rows:
        if row["length"] <= 0:
            unmatched += 1
            continue
        candidates = [x for x in by_seed.get(row["seed"], [])
                      if x["length"] > 0 and abs(loglen(x) - loglen(row)) <= caliper]
        if not candidates:
            unmatched += 1
            continue
        match = min(candidates, key=lambda x: abs(loglen(x) - loglen(row)))
        pairs.append((row, match))
    return pairs, unmatched


def matched_estimate(pairs: list[tuple[dict, dict]]) -> float:
    return statistics.fmean(a["depth"] - b["depth"] for a, b in pairs)


def boot_pairs(pairs: list[tuple[dict, dict]], draws: int = 2000) -> tuple[float, float]:
    by_seed = defaultdict(list)
    for a, b in pairs:
        by_seed[a["seed"]].append((a, b))
    seeds = sorted(by_seed)
    rng = np.random.default_rng(RNG_SEED + 7)
    values = []
    for _ in range(draws):
        picked = rng.choice(seeds, size=len(seeds), replace=True)
        sample = [pair for seed in picked for pair in by_seed[seed]]
        values.append(matched_estimate(sample))
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


nn = {}
for caliper in (0.10, 0.25, 0.50):
    pairs, unmatched = nearest_length_pairs(PFV, B2V, caliper)
    nn[str(caliper)] = {
        "matched": len(pairs),
        "unmatched_pf": unmatched,
        "gap": matched_estimate(pairs),
        "ci": boot_pairs(pairs),
        "median_abs_log_length_gap": statistics.median(abs(loglen(a) - loglen(b)) for a, b in pairs),
    }

# common support
lo = min(x["length"] for x in B2V)
hi = max(x["length"] for x in B2V)
common_pf = [x for x in PFV if lo <= x["length"] <= hi]
common = {
    "pf_on_b2_support": len(common_pf),
    "pf_total": len(PFV),
    "pf_depth": statistics.fmean(x["depth"] for x in common_pf),
    "b2_depth": statistics.fmean(x["depth"] for x in B2V),
    "gap": statistics.fmean(x["depth"] for x in common_pf) - statistics.fmean(x["depth"] for x in B2V),
    "b2_length_range": [lo, hi],
}

# coarsened exact matching on pooled length quintiles x seed
all_lengths = sorted(x["length"] for x in PFV + B2V)
cuts = [all_lengths[int(len(all_lengths) * q)] for q in (0.2, 0.4, 0.6, 0.8)]


def length_bin(value: int) -> int:
    for index, cut in enumerate(cuts):
        if value <= cut:
            return index
    return len(cuts)


cem_cells = defaultdict(lambda: {"pf": [], "b2": []})
for row in PFV:
    cem_cells[(row["seed"], length_bin(row["length"]))]["pf"].append(row["depth"])
for row in B2V:
    cem_cells[(row["seed"], length_bin(row["length"]))]["b2"].append(row["depth"])
cem_cells = {k: v for k, v in cem_cells.items() if v["pf"] and v["b2"]}
cem_weights = {k: len(v["pf"]) for k, v in cem_cells.items()}
cem_gap = sum(w * (statistics.fmean(cem_cells[k]["pf"]) - statistics.fmean(cem_cells[k]["b2"]))
              for k, w in cem_weights.items()) / sum(cem_weights.values())


def boot_cem(draws: int = 2000) -> tuple[float, float]:
    rng = np.random.default_rng(RNG_SEED + 11)
    seeds = sorted({k[0] for k in cem_cells})
    values = []
    for _ in range(draws):
        picked = rng.choice(seeds, size=len(seeds), replace=True)
        num = den = 0.0
        for seed in picked:
            for (s, b), cell in cem_cells.items():
                if s != seed:
                    continue
                w = len(cell["pf"])
                num += w * (statistics.fmean(cell["pf"]) - statistics.fmean(cell["b2"]))
                den += w
        values.append(num / den if den else float("nan"))
    values = [v for v in values if not math.isnan(v)]
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


cem = {
    "cells": len(cem_cells),
    "pf_matched": sum(len(v["pf"]) for v in cem_cells.values()),
    "b2_matched": sum(len(v["b2"]) for v in cem_cells.values()),
    "gap": cem_gap,
    "ci": boot_cem(),
    "weights": "number of PF valid items in each (seed, length-quintile) cell",
}

# single-subquestion subgroup
pf1 = [x for x in PFV if x["subanswers"] == 1]
b21 = [x for x in B2V if x["subanswers"] == 1]


def seed_boot_gap(pf_rows: list[dict], b2_rows: list[dict], draws: int = 2000) -> tuple[float, float]:
    by = defaultdict(lambda: {"pf": [], "b2": []})
    for row in pf_rows:
        by[row["seed"]]["pf"].append(row["depth"])
    for row in b2_rows:
        by[row["seed"]]["b2"].append(row["depth"])
    seeds = sorted(by)
    rng = np.random.default_rng(RNG_SEED + 13)
    values = []
    for _ in range(draws):
        picked = rng.choice(seeds, size=len(seeds), replace=True)
        gaps = []
        for seed in picked:
            cell = by[seed]
            if cell["pf"] and cell["b2"]:
                gaps.append(statistics.fmean(cell["pf"]) - statistics.fmean(cell["b2"]))
        values.append(statistics.fmean(gaps) if gaps else float("nan"))
    values = [v for v in values if not math.isnan(v)]
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


single_sub = {
    "pf_n": len(pf1),
    "b2_n": len(b21),
    "pf_depth": statistics.fmean(x["depth"] for x in pf1),
    "b2_depth": statistics.fmean(x["depth"] for x in b21),
    "gap": statistics.fmean(x["depth"] for x in pf1) - statistics.fmean(x["depth"] for x in b21),
    "ci": seed_boot_gap(pf1, b21),
    "pf_length_median": statistics.median(x["length"] for x in pf1),
    "b2_length_median": statistics.median(x["length"] for x in b21),
}

single_matched = {}
for caliper in (0.25, 0.50):
    pairs, unmatched = nearest_length_pairs(pf1, b21, caliper)
    single_matched[str(caliper)] = {
        "matched": len(pairs),
        "unmatched_pf": unmatched,
        "gap": matched_estimate(pairs),
        "ci": boot_pairs(pairs),
    }

# ---------------------------------------------------------------- length-stratified depth and yield

strata = []
for index in range(len(cuts) + 1):
    pf_rows = [x for x in PFV if length_bin(x["length"]) == index]
    b2_rows = [x for x in B2V if length_bin(x["length"]) == index]
    if not pf_rows or not b2_rows:
        continue
    strata.append({
        "bin": index,
        "range": [min([x["length"] for x in pf_rows + b2_rows]), max([x["length"] for x in pf_rows + b2_rows])],
        "pf_n": len(pf_rows),
        "b2_n": len(b2_rows),
        "pf_depth": statistics.fmean(x["depth"] for x in pf_rows),
        "b2_depth": statistics.fmean(x["depth"] for x in b2_rows),
        "depth_gap": statistics.fmean(x["depth"] for x in pf_rows) - statistics.fmean(x["depth"] for x in b2_rows),
        "pf_ge3": sum(1 for x in pf_rows if x["depth"] >= 3) / len(pf_rows),
        "b2_ge3": sum(1 for x in b2_rows if x["depth"] >= 3) / len(b2_rows),
    })

# ---------------------------------------------------------------- >=3 steps per requested slot, standardised by length

def ge3(rows: list[dict]) -> int:
    return sum(1 for x in rows if x["valid"] and x["depth"] is not None and x["depth"] >= 3)


def yield_standardised(pf_rows: list[dict], b2_rows: list[dict], cuts_local: list[int]) -> dict:
    def bin_of(value: int) -> int:
        for index, cut in enumerate(cuts_local):
            if value <= cut:
                return index
        return len(cuts_local)

    pf_bins = defaultdict(list)
    b2_bins = defaultdict(list)
    for row in pf_rows:
        pf_bins[bin_of(row["length"])].append(row)
    for row in b2_rows:
        b2_bins[bin_of(row["length"])].append(row)
    total_pf = len(pf_rows)
    pf_rate = ge3(pf_rows) / total_pf
    standard = 0.0
    covered = 0
    for index, rows in pf_bins.items():
        if not rows or not b2_bins.get(index):
            continue
        weight = len(rows) / total_pf
        standard += weight * (ge3(b2_bins[index]) / len(b2_bins[index]))
        covered += len(rows)
    b2_rate = ge3(b2_rows) / len(b2_rows) if b2_rows else float("nan")
    return {"pf_rate": pf_rate, "b2_rate": b2_rate, "b2_standardised": standard,
            "gap": pf_rate - standard, "raw_gap": pf_rate - b2_rate,
            "covered_pf": covered, "pf_total": total_pf}


yield_std = yield_standardised(PF, B2, cuts)


def boot_yield_std(draws: int = 2000) -> tuple[float, float]:
    by_seed = defaultdict(lambda: {"pf": [], "b2": []})
    for row in PF:
        by_seed[row["seed"]]["pf"].append(row)
    for row in B2:
        by_seed[row["seed"]]["b2"].append(row)
    seeds = sorted(by_seed)
    rng = np.random.default_rng(RNG_SEED + 17)
    values = []
    for _ in range(draws):
        picked = rng.choice(seeds, size=len(seeds), replace=True)
        pf_rows = [row for seed in picked for row in by_seed[seed]["pf"]]
        b2_rows = [row for seed in picked for row in by_seed[seed]["b2"]]
        values.append(yield_standardised(pf_rows, b2_rows, cuts)["gap"])
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


yield_std["ci"] = boot_yield_std()

# nearest-length matched yield difference (paired by matched PF item / B2 item)
matched_yield_pairs, matched_yield_unmatched = nearest_length_pairs(PF, B2, 0.25)
matched_yield_gap = statistics.fmean(
    (1.0 if a["valid"] and a["depth"] is not None and a["depth"] >= 3 else 0.0)
    - (1.0 if b["valid"] and b["depth"] is not None and b["depth"] >= 3 else 0.0)
    for a, b in matched_yield_pairs
)
def boot_binary_pairs(pairs, draws: int = 2000):
    by_seed = defaultdict(list)
    for a, b in pairs:
        by_seed[a["seed"]].append((a, b))
    seeds = sorted(by_seed)
    rng = np.random.default_rng(RNG_SEED + 19)
    values = []
    for _ in range(draws):
        picked = rng.choice(seeds, size=len(seeds), replace=True)
        sample = [pair for seed in picked for pair in by_seed[seed]]
        values.append(statistics.fmean(
            (1.0 if a["valid"] and a["depth"] is not None and a["depth"] >= 3 else 0.0)
            - (1.0 if b["valid"] and b["depth"] is not None and b["depth"] >= 3 else 0.0)
            for a, b in sample))
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))

matched_yield_boot = boot_binary_pairs(matched_yield_pairs)

# ---------------------------------------------------------------- independent solver difficulty

solver = {}
for name, rows in (("PF", PF), ("B2", B2), ("B1", B1)):
    values = [x["solver"] for x in rows if x["valid"] and x["solver"] is not None]
    solver[name] = {
        "n": len(values),
        "solver_correct": sum(1 for value in values if value) / len(values) if values else None,
    }
for depth in range(5):
    solver[f"depth_{depth}"] = {}
    for name, rows in (("PF", PF), ("B2", B2), ("B1", B1)):
        values = [x["solver"] for x in rows
                  if x["valid"] and x["depth"] == depth and x["solver"] is not None]
        solver[f"depth_{depth}"][name] = {
            "n": len(values),
            "correct": sum(1 for value in values if value) / len(values) if values else None,
        }

# ---------------------------------------------------------------- cost, explicit scales

tokens = json.loads((RUN / "tokens_summary.json").read_text())
gen = tokens["by_stage"]["generate"]
# by_method "generate" is not separated in tokens_summary; use generation_costs.json.
gen_costs = json.loads((RUN / "generation_costs.json").read_text())["groups"]
pf_cost = json.loads((ROOT / "final_experiment" / "pf_cost" / "pf_cost_summary.json").read_text())
valid_rate = {"PF": 366 / 480, "B2": 352 / 455, "B1": 134 / 479}
seeds = 97
pf_items_per_seed = sum(1 for row in records.values() if row["method"] == "puzzleforge" and row["cohort"] == "matched") / seeds
b2_items_per_seed = sum(1 for row in records.values() if row["method"] == "framework" and row["cohort"] == "matched") / seeds
b1_items_per_seed = sum(1 for row in records.values() if row["method"] == "direct" and row["cohort"] == "matched") / seeds
gens_per_seed = 284 / seeds
b2_tokens = gen_costs["framework"]["total_tokens"]
b1_tokens = gen_costs["direct"]["total_tokens"]

# B1 is linear in the number of items: its per-valid-item cost is invariant to
# the amortisation scale.  B2's program is reusable, so its API cost amortises;
# PF's spec cost is per generator.  Never mix a 200/generator PF number with a
# 20/seed B2 number (the two scales differ by 10x).
b1_produced = sum(1 for row in records.values() if row["method"] == "direct" and row["status"] == "ok")
b2_produced = sum(1 for row in records.values() if row["method"] == "framework" and row["status"] == "ok")
b1_per_valid = b1_tokens / (b1_produced * valid_rate["B1"])
b2_per_valid_20 = b2_tokens / (b2_produced * valid_rate["B2"])
b2_per_valid_200 = b2_tokens / (seeds * 200 * valid_rate["B2"])
pf_per_valid_20 = pf_cost["tokens_mean"] / 20 / valid_rate["PF"]
pf_per_valid_200 = pf_cost["tokens_mean"] / 200 / valid_rate["PF"]

cost = {
    "scales": {
        "design_200_per_unit": {
            "PF_tokens_per_valid": pf_per_valid_200,
            "PF_tokens_per_valid_median_spec": pf_cost["tokens_median"] / 200 / valid_rate["PF"],
            "B2_tokens_per_valid": b2_per_valid_200,
            "B1_tokens_per_valid": b1_per_valid,
        },
        "twenty_per_unit": {
            "PF_tokens_per_valid": pf_per_valid_20,
            "PF_tokens_per_valid_median_spec": pf_cost["tokens_median"] / 20 / valid_rate["PF"],
            "B2_tokens_per_valid": b2_per_valid_20,
            "B1_tokens_per_valid": b1_per_valid,
        },
    },
    "valid_rate": valid_rate,
    "pf_spec_tokens": {"mean": pf_cost["tokens_mean"], "median": pf_cost["tokens_median"],
                       "min": pf_cost["tokens_min"], "max": pf_cost["tokens_max"],
                       "generators_per_seed": gens_per_seed},
    "spec_tokens_per_seed": {
        "PF_mean_3gens": pf_cost["tokens_mean"] * gens_per_seed,
        "PF_median_3gens": pf_cost["tokens_median"] * gens_per_seed,
        "B2_20": b2_tokens / seeds,
        "B1_20": b1_tokens / seeds,
    },
    "projected_86k_design": {
        "PF": 86000 * pf_per_valid_200,
        "B2": 86000 * b2_per_valid_200,
        "B1": 86000 * b1_per_valid,
    },
    "notes": [
        "PF: spec (encoding+debugging) tokens per generator, amortised over 200 instances.",
        "B2: API tokens for one reusable program, amortised over 200 instances.",
        "B1: direct generation, linear; per-valid cost is scale-invariant.",
        "The audit's PF test set is a 2% holdout (13.2 slots/seed), so amortising "
        "PF's spec cost over it would overstate cost; production scales are used.",
    ],
}

# ---------------------------------------------------------------- output

out = {
    "meta": {
        "items": len(items),
        "generated": RNG_SEED,
        "cut_points_pooled_depth": cuts,
        "bootstrap": "2000 seed resamples; OLS 1000",
        "note": "Depth is conditional on the judge's valid label; >=3-step yield is per requested slot.",
    },
    "summary": summary,
    "ols": ols,
    "nearest_length": nn,
    "common_support": common,
    "cem": cem,
    "single_subquestion": single_sub,
    "single_subquestion_matched": single_matched,
    "length_strata": strata,
    "yield_standardised": yield_std,
    "yield_length_matched": {
        "matched": len(matched_yield_pairs),
        "unmatched_pf": matched_yield_unmatched,
        "gap": matched_yield_gap,
        "ci": matched_yield_boot,
    },
    "solver": solver,
    "cost": cost,
}
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

lines = ["# Robustness appendix (generated)", "",
         f"Items: {len(items)}; depth cut points: {cuts}; seed bootstrap 2,000.", ""]

lines += ["## R1 - depth gap under length controls", "",
          table(["estimator", "PF - B2", "95% CI", "n (PF / B2)"],
                [["raw", f"{ols['raw']:+.3f}", "", f"{ols['n'][0]} / {ols['n'][1]}"],
                 ["OLS + log(length)", f"{ols['log_length']:+.3f}",
                  f"[{ols['log_length_ci'][0]:+.3f}, {ols['log_length_ci'][1]:+.3f}]", ""],
                 ["OLS + log(length) + seed FE", f"{ols['log_length_seed_fe']:+.3f}",
                  f"[{ols['log_length_seed_fe_ci'][0]:+.3f}, {ols['log_length_seed_fe_ci'][1]:+.3f}]", ""]],
                "lrrr"), ""]

rows = []
for caliper, value in nn.items():
    rows.append([f"nearest length, caliper {caliper}", f"{value['gap']:+.3f}",
                 f"[{value['ci'][0]:+.3f}, {value['ci'][1]:+.3f}]",
                 f"{value['matched']}", f"{value['unmatched_pf']}"])
rows.append(["coarsened exact matching (seed x quintile)", f"{cem['gap']:+.3f}",
             f"[{cem['ci'][0]:+.3f}, {cem['ci'][1]:+.3f}]",
             f"{cem['pf_matched']}", ""])
rows.append(["common length support", f"{common['gap']:+.3f}", "",
             f"{common['pf_on_b2_support']} / {len(B2V)}", ""])
lines += ["## R2 - matched depth gap", "",
          table(["estimator", "PF - B2", "95% CI", "matched pairs", "unmatched PF"],
                rows, "lrrrr"), ""]

rows = []
for cell in strata:
    rows.append([f"Q{cell['bin'] + 1} [{cell['range'][0]}, {cell['range'][1]}]",
                 f"{cell['pf_depth']:.2f}", f"{cell['b2_depth']:.2f}", f"{cell['depth_gap']:+.2f}",
                 f"{cell['pf_n']} / {cell['b2_n']}"])
lines += ["## R3 - depth by pooled length quintile", "",
          table(["stratum (chars)", "PF depth", "B2 depth", "gap", "n (PF / B2)"],
                rows, "lrrrr"), ""]

lines += ["## R4 - single-subquestion subgroup", "",
          table(["", "PF", "B2", "gap"],
                [["n", f"{single_sub['pf_n']}", f"{single_sub['b2_n']}", ""],
                 ["mean depth", f"{single_sub['pf_depth']:.2f}", f"{single_sub['b2_depth']:.2f}",
                  f"{single_sub['gap']:+.3f} [{single_sub['ci'][0]:+.3f}, {single_sub['ci'][1]:+.3f}]"],
                 ["median length (chars)", f"{single_sub['pf_length_median']:.0f}",
                  f"{single_sub['b2_length_median']:.0f}", ""]],
                "lrrr"), "",
          table(["matched single-subquestion", "PF - B2", "95% CI", "pairs"],
                [[f"nearest length, caliper {cal}", f"{v['gap']:+.3f}",
                  f"[{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}]", str(v["matched"])]
                 for cal, v in single_matched.items()], "lrrr"), ""]

lines += ["## R5 - >=3 dependent steps per requested slot, length-standardised", "",
          table(["estimator", "PF", "B2", "gap", "95% CI"],
                [["raw (480 slots each)", f"{yield_std['pf_rate']:.3f}", f"{yield_std['b2_rate']:.3f}",
                  f"{yield_std['raw_gap']:+.3f}", ""],
                 ["standardised to PF length distribution", f"{yield_std['pf_rate']:.3f}",
                  f"{yield_std['b2_standardised']:.3f}", f"{yield_std['gap']:+.3f}",
                  f"[{yield_std['ci'][0]:+.3f}, {yield_std['ci'][1]:+.3f}]"],
                 ["nearest-length matched", "", "",
                  f"{matched_yield_gap:+.3f} [{matched_yield_boot[0]:+.3f}, {matched_yield_boot[1]:+.3f}]",
                  ""]],
                "lrrrr"), ""]

rows = []
for panel, values in cost["scales"].items():
    rows.append([panel, f"{values['PF_tokens_per_valid']:,.0f}",
                 f"{values['PF_tokens_per_valid_median_spec']:,.0f}",
                 f"{values['B2_tokens_per_valid']:,.1f}",
                 f"{values['B1_tokens_per_valid']:,.0f}"])
lines += ["## R6 - cost per valid item at explicit amortisation scales", "",
          table(["scale", "PF (mean spec)", "PF (median spec)", "B2", "B1"],
                rows, "lrrrr"), "",
          "PF tokens per valid item; B2/B1 token counts are API generation tokens only "
          "(local execution is free). Both scales put PF, B2 and B1 on the same "
          "instances-per-unit basis; PF/B2 is ~25x at either scale. PF's 187k mean is "
          "outlier-driven (median 116k, range 56k-434k).", ""]

lines += ["## R7 - independent solver difficulty on judge-valid items", "",
          table(["condition", "n", "solver correct"],
                [[name, f"{solver[name]['n']}", f"{solver[name]['solver_correct']:.3f}"]
                 for name in ("PF", "B2", "B1")], "lrr"), ""]

OUT_MD.write_text("\n".join(lines), encoding="utf-8")

print(OUT_JSON)
print(OUT_MD)
print(json.dumps({k: out[k] for k in ("ols", "nearest_length", "cem", "single_subquestion",
                                     "yield_standardised", "yield_length_matched", "cost")},
                 ensure_ascii=False, indent=2)[:4000])
