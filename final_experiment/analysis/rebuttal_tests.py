"""Seed-paired statistics for the rebuttal (read-only over frozen run artifacts).

Consumes: audit/audit_blind.jsonl, audit/audit_key.jsonl, auto/model_labels.jsonl, stats.json
Emits:    analysis/rebuttal_tests.json  (+ stdout summary)

Why this exists: the frozen report gives seed-macro means and bootstrap CIs for
validity only. A rebuttal needs paired win/loss counts, effect sizes and exact
tests for every axis, plus the failure taxonomy and a filtering-equalised
sensitivity check. Nothing here re-samples or re-judges items.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

RUN = Path(__file__).resolve().parents[1] / "run"
PAIRS = [("puzzleforge", "framework"), ("puzzleforge", "direct"), ("framework", "direct")]
METRICS = ["validity", "depth", "certificate", "length", "near_dup", "tagset_dup_r", "tagset_dup_c"]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def sign_test(wins: int, losses: int) -> float:
    """Exact two-sided binomial sign test, ties removed."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(wins, losses) + 1)) / 2**n
    return min(1.0, 2.0 * tail)


def wilcoxon(diffs: list[float]) -> tuple[float, float]:
    """Wilcoxon signed-rank, normal approximation with tie and continuity correction."""
    d = [x for x in diffs if x != 0]
    n = len(d)
    if n < 10:
        return float("nan"), float("nan")
    order = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    tie_term = 0.0
    while i < n:
        j = i
        while j + 1 < n and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        avg = (i + j + 2) / 2.0  # 1-based average rank
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        t = j - i + 1
        tie_term += t**3 - t
        i = j + 1
    w_plus = sum(r for r, x in zip(ranks, d) if x > 0)
    mu = n * (n + 1) / 4.0
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0 - tie_term / 48.0)
    if sigma == 0:
        return float("nan"), float("nan")
    z = (abs(w_plus - mu) - 0.5) / sigma
    return w_plus, min(1.0, 2.0 * (1.0 - phi(max(z, 0.0))))


def bootstrap_ci(diffs: list[float], n_boot: int = 2000, alpha: float = 0.05) -> tuple[float, float]:
    rng = np.random.default_rng(20261028)
    arr = np.asarray(diffs, dtype=float)
    means = np.array([arr[rng.integers(0, len(arr), len(arr))].mean() for _ in range(n_boot)])
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def cliffs_delta(diffs: list[float]) -> float:
    wins = sum(1 for d in diffs if d > 0)
    losses = sum(1 for d in diffs if d < 0)
    return (wins - losses) / len(diffs) if diffs else float("nan")


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = [(k, p) for k, p in pvals.items() if not math.isnan(p)]
    items.sort(key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for rank, (k, p) in enumerate(items):
        adj = min(1.0, max(running, (m - rank) * p))
        running = adj
        out[k] = adj
    return out


def main() -> None:
    key = {r["anon_id"]: r for r in load_jsonl(RUN / "audit" / "audit_key.jsonl")}
    blind = {r["anon_id"]: r for r in load_jsonl(RUN / "audit" / "audit_blind.jsonl")}
    labels = {r["anon_id"]: r for r in load_jsonl(RUN / "auto" / "model_labels.jsonl")}
    frozen = json.loads((RUN / "stats.json").read_text(encoding="utf-8"))

    items = []
    for anon_id, meta in key.items():
        lab = labels.get(anon_id)
        judge = lab["judges"][0] if lab and lab["judges"] else {}
        verdict = judge.get("verdict", lab["status"] if lab else "unavailable")
        items.append(
            {
                "method": meta["method"],
                "seed": meta["seed_id"],
                "verdict": verdict,
                "depth": judge.get("depth_score"),
                "certificate": judge.get("explanation_score"),
                "length": len(blind[anon_id]["problem"]) if anon_id in blind else None,
                "errors": judge.get("error_types") or [],
                "rtags": frozenset(judge.get("reasoning_type_tags") or []),
                "ctags": frozenset(judge.get("constraint_type_tags") or []),
                "scenario": judge.get("scenario"),
            }
        )

    by_seed: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for it in items:
        by_seed[(it["seed"], it["method"])].append(it)

    seeds = sorted({it["seed"] for it in items})
    near_dup = {m: dict(zip(frozen["seeds"], frozen["diversity"][m]["seed_rates"])) for m in frozen["diversity"]}

    per_seed: dict[str, dict[str, dict]] = {m: {} for m in ("puzzleforge", "framework", "direct")}
    for (seed, method), rows in by_seed.items():
        valid = [r for r in rows if r["verdict"] == "valid"]
        depths = [r["depth"] for r in valid if r["depth"] is not None]
        certs = [r["certificate"] for r in valid if r["certificate"] is not None]
        lengths = [r["length"] for r in rows if r["length"]]
        tag_rows = [r for r in rows if r["rtags"]]
        tag_pairs = list(combinations(tag_rows, 2))
        per_seed[method][seed] = {
            "n": len(rows),
            "n_valid": len(valid),
            "validity": len(valid) / len(rows),
            "depth": statistics.fmean(depths) if depths else None,
            "certificate": statistics.fmean(certs) if certs else None,
            "length": statistics.median(lengths) if lengths else None,
            "near_dup": near_dup[method].get(seed),
            "tagset_dup_r": (
                sum(1 for x, y in tag_pairs if x["rtags"] == y["rtags"]) / len(tag_pairs) if tag_pairs else None
            ),
            "tagset_dup_c": (
                sum(1 for x, y in tag_pairs if x["ctags"] == y["ctags"]) / len(tag_pairs) if tag_pairs else None
            ),
        }

    # ---- paired comparisons -------------------------------------------------
    results: dict[str, dict] = {}
    pvals: dict[str, float] = {}
    for a, b in PAIRS:
        tag = f"{a}_vs_{b}"
        results[tag] = {}
        for metric in METRICS:
            diffs = [
                per_seed[a][s][metric] - per_seed[b][s][metric]
                for s in seeds
                if per_seed[a].get(s, {}).get(metric) is not None and per_seed[b].get(s, {}).get(metric) is not None
            ]
            if len(diffs) < 10:
                continue
            lo, hi = bootstrap_ci(diffs)
            w = sum(1 for d in diffs if d > 0)
            l = sum(1 for d in diffs if d < 0)
            w_stat, p_w = wilcoxon(diffs)
            p_s = sign_test(w, l)
            entry = {
                "n_pairs": len(diffs),
                "mean_diff": statistics.fmean(diffs),
                "ci": [lo, hi],
                "wins": w,
                "ties": len(diffs) - w - l,
                "losses": l,
                "median_diff": statistics.median(diffs),
                "cliffs_delta": cliffs_delta(diffs),
                "p_sign": p_s,
                "p_wilcoxon": p_w,
                "wilcoxon_stat": w_stat,
            }
            pvals[f"{tag}:{metric}"] = min(p_s, p_w if not math.isnan(p_w) else 1.0)
            results[tag][metric] = entry

    adjusted = holm(pvals)

    # ---- failure taxonomy ---------------------------------------------------
    taxonomy = {}
    for method in ("puzzleforge", "framework", "direct"):
        rows = [it for it in items if it["method"] == method]
        invalid = [r for r in rows if r["verdict"] == "invalid"]
        counts = Counter(e for r in invalid for e in r["errors"])
        taxonomy[method] = {
            "n_items": len(rows),
            "n_invalid": len(invalid),
            "no_output": sum(1 for r in rows if r["verdict"] == "unavailable"),
            "uncertain": sum(1 for r in rows if r["verdict"] == "uncertain"),
            "errors": dict(counts.most_common()),
        }

    # ---- structural duplication (tag-set identity within seed) --------------
    structural = {}
    for method in ("puzzleforge", "framework", "direct"):
        identical_r, identical_c, pairs = 0, 0, 0
        distinct_r, distinct_c = [], []
        for seed in seeds:
            rows = [r for r in by_seed.get((seed, method), []) if r["rtags"]]
            distinct_r.append(len({r["rtags"] for r in rows}))
            distinct_c.append(len({r["ctags"] for r in rows}))
            for x, y in combinations(rows, 2):
                pairs += 1
                identical_r += x["rtags"] == y["rtags"]
                identical_c += x["ctags"] == y["ctags"]
        structural[method] = {
            "pairs": pairs,
            "identical_reasoning_tagset_rate": identical_r / pairs if pairs else None,
            "identical_constraint_tagset_rate": identical_c / pairs if pairs else None,
            "mean_distinct_reasoning_tagsets": statistics.fmean(distinct_r),
            "mean_distinct_constraint_tagsets": statistics.fmean(distinct_c),
        }

    # ---- certificate vs depth ----------------------------------------------
    valid_items = [r for r in items if r["verdict"] == "valid" and r["depth"] is not None and r["certificate"] is not None]
    xs = np.array([r["depth"] for r in valid_items], dtype=float)
    ys = np.array([r["certificate"] for r in valid_items], dtype=float)

    def pearson(u, v):
        return float(np.corrcoef(u, v)[0, 1])

    def rank(u):
        order = np.argsort(np.argsort(u))
        return order.astype(float)

    cert_depth = {
        "n": len(valid_items),
        "pearson": pearson(xs, ys),
        "spearman": pearson(rank(xs), rank(ys)),
        "by_depth": {
            str(int(d)): {
                "n": int((xs == d).sum()),
                "mean_certificate": float(ys[xs == d].mean()) if (xs == d).any() else None,
            }
            for d in sorted(set(xs.tolist()))
        },
    }

    # ---- seed-level yield ---------------------------------------------------
    yield_stats = {}
    for method in ("puzzleforge", "framework", "direct"):
        rates = [per_seed[method][s]["validity"] for s in seeds]
        counts = [per_seed[method][s]["n_valid"] for s in seeds]
        yield_stats[method] = {
            "seeds_with_zero_valid": sum(1 for c in counts if c == 0),
            "seeds_with_at_least_3_of_5": sum(1 for c in counts if c >= 3),
            "median_valid_per_seed": statistics.median(counts),
            "mean_valid_per_seed": statistics.fmean(counts),
            "median_seed_validity": statistics.median(rates),
            "iqr_seed_validity": [
                float(np.quantile(rates, 0.25)),
                float(np.quantile(rates, 0.75)),
            ],
        }

    # ---- within-method certificate/depth relation ---------------------------
    def corr(u, v):
        u, v = np.asarray(u, dtype=float), np.asarray(v, dtype=float)
        return float(np.corrcoef(u, v)[0, 1]) if len(u) > 2 else float("nan")

    within = {}
    for method in ("puzzleforge", "framework", "direct"):
        rows = [r for r in items if r["method"] == method and r["verdict"] == "valid"]
        rows = [r for r in rows if r["depth"] is not None and r["certificate"] is not None]
        within[method] = {
            "n": len(rows),
            "pearson_depth_vs_certificate": corr([r["depth"] for r in rows], [r["certificate"] for r in rows]),
        }

    # ---- filtering-equalised sensitivity -----------------------------------
    # A generator-level filter can only remove seeds whose generator produced
    # nothing at all (all sampled slots unavailable). Seed-level "zero valid
    # items" is a quality outcome, not an authoring failure, and excluding it
    # would be survivorship. Restrict the equalisation to no-output seeds.
    no_output = [
        s
        for s in seeds
        if per_seed["framework"][s]["n"] > 0
        and per_seed["framework"][s]["n_valid"] == 0
        and all(r["verdict"] == "unavailable" for r in by_seed[(s, "framework")])
    ]
    kept = [s for s in seeds if s not in no_output]

    def macro(method: str, subset: list[str]) -> float:
        return statistics.fmean(per_seed[method][s]["validity"] for s in subset)

    sensitivity = {
        "excluded_no_output_seeds": no_output,
        "n_excluded": len(no_output),
        "validity_all_seeds": {m: macro(m, seeds) for m in per_seed},
        "validity_after_removing_no_output_seed": {m: macro(m, kept) for m in per_seed},
        "delta_pf_minus_framework_all": macro("puzzleforge", seeds) - macro("framework", seeds),
        "delta_pf_minus_framework_equalised": macro("puzzleforge", kept) - macro("framework", kept),
        "delta_pf_minus_framework_depth_equalised": statistics.fmean(
            per_seed["puzzleforge"][s]["depth"] - per_seed["framework"][s]["depth"]
            for s in kept
            if per_seed["puzzleforge"][s]["depth"] is not None and per_seed["framework"][s]["depth"] is not None
        ),
        "delta_pf_minus_framework_tagset_r_equalised": statistics.fmean(
            per_seed["puzzleforge"][s]["tagset_dup_r"] - per_seed["framework"][s]["tagset_dup_r"]
            for s in kept
            if per_seed["puzzleforge"][s]["tagset_dup_r"] is not None
            and per_seed["framework"][s]["tagset_dup_r"] is not None
        ),
    }


    # ---- per-seed triple dominance -----------------------------------------
    def dominates(seed: str) -> bool:
        pf, fw = per_seed["puzzleforge"].get(seed), per_seed["framework"].get(seed)
        if not pf or not fw or pf["depth"] is None or fw["depth"] is None or pf["near_dup"] is None or fw["near_dup"] is None:
            return False
        return pf["validity"] >= fw["validity"] and pf["depth"] >= fw["depth"] and pf["near_dup"] <= fw["near_dup"]

    triple = sum(dominates(s) for s in seeds)

    out = {
        "meta": {
            "seeds": len(seeds),
            "items": len(items),
            "pairs": [list(p) for p in PAIRS],
            "bootstrap": "2000 resamples over seeds, percentile CI",
            "p_sign": "exact two-sided binomial (ties removed)",
            "p_wilcoxon": "normal approximation, tie + continuity corrected",
            "family": sorted(pvals),
            "holm": adjusted,
        },
        "per_seed": per_seed,
        "paired": results,
        "taxonomy": taxonomy,
        "structural": structural,
        "seed_yield": yield_stats,
        "within_method_certificate_depth": within,
        "certificate_vs_depth": cert_depth,
        "sensitivity": sensitivity,
        "framework_triple_dominance_seeds": triple,
    }
    (RUN / "analysis").mkdir(exist_ok=True)
    (RUN / "analysis" / "rebuttal_tests.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({k: out[k] for k in ("taxonomy", "structural", "certificate_vs_depth", "sensitivity")}, indent=2, ensure_ascii=False))
    print("\n=== paired ===")
    for tag, metrics in results.items():
        for metric, e in metrics.items():
            print(
                f"{tag:22s} {metric:12s} d={e['mean_diff']:+.3f} CI[{e['ci'][0]:+.3f},{e['ci'][1]:+.3f}] "
                f"W/T/L={e['wins']}/{e['ties']}/{e['losses']} delta={e['cliffs_delta']:+.2f} "
                f"p_sign={e['p_sign']:.2e} p_wilcox={e['p_wilcoxon']:.2e}"
            )
    print("\n=== holm ===")
    for k, v in adjusted.items():
        print(f"{k:40s} p_holm={v:.2e}")
    print(f"\ntriple dominance seeds: {triple}/{len(seeds)}")


if __name__ == "__main__":
    main()
