"""Analysis and figures for the 14-seed / ~204-item comparison run.

Reads records_selected.jsonl, audit/, auto/ and tokens_requests.csv. Writes
stats.json plus publication-style PNG/SVG figures with large fonts.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RUN = Path(__file__).resolve().parent
METHODS = ("puzzleforge", "direct", "framework")
COLORS = {"puzzleforge": "#2b6cb0", "direct": "#dd6b20", "framework": "#c53030"}
LABELS = {"puzzleforge": "PF", "direct": "Direct", "framework": "Framework"}
FIGS = RUN / "figures"
FIGS.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.size": 14, "axes.titlesize": 16, "axes.labelsize": 15,
    "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 13,
    "figure.dpi": 200, "savefig.dpi": 200, "axes.spines.top": False,
    "axes.spines.right": False, "font.family": "DejaVu Sans",
})
RNG = np.random.default_rng(20261028)


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def consensus(row: dict) -> str:
    if row["status"] == "unavailable":
        return "unavailable"
    if row["status"] == "execution_unknown":
        return "unknown"
    verdicts = {judge["verdict"] for judge in row["judges"]}
    return next(iter(verdicts)) if len(verdicts) == 1 and "uncertain" not in verdicts else "uncertain"


def boot_ci(values: np.ndarray, rounds: int = 2000) -> tuple[float, float]:
    if len(values) < 2:
        return float("nan"), float("nan")
    draws = RNG.integers(0, len(values), (rounds, len(values)))
    means = values[draws].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def normalise(text: str) -> str:
    return re.sub(r"\s+", "", text)


def grams(text: str, n: int = 4) -> set[str]:
    text = normalise(text)
    return {text[i:i + n] for i in range(max(0, len(text) - n + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def save(fig, name: str) -> None:
    for ext in ("png", "svg"):
        fig.savefig(FIGS / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    global RUN, FIGS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=RUN)
    parser.add_argument("--figs", type=Path, default=None)
    args = parser.parse_args()
    RUN = args.run.resolve()
    FIGS = (args.figs or RUN / "figures").resolve()
    FIGS.mkdir(parents=True, exist_ok=True)
    records = jsonl(RUN / "records_selected.jsonl")
    key = {row["anon_id"]: row for row in jsonl(RUN / "audit/audit_key.jsonl")}
    blind = {row["anon_id"]: row for row in jsonl(RUN / "audit/audit_blind.jsonl")}
    labels = jsonl(RUN / "auto/model_labels.jsonl")
    verdict = {row["anon_id"]: consensus(row) for row in labels}
    by_method = {m: [a for a in verdict if key[a]["method"] == m] for m in METHODS}
    seeds = sorted({row["seed_id"] for row in key.values()})

    # ---- validity ----
    valid_rate, per_seed_rate = {}, {}
    for method in METHODS:
        per_seed_rate[method] = {}
        for seed in seeds:
            ids = [a for a in by_method[method] if key[a]["seed_id"] == seed]
            if ids:
                per_seed_rate[method][seed] = float(np.mean([verdict[a] == "valid" for a in ids]))
        arr = np.array([per_seed_rate[method][s] for s in seeds if s in per_seed_rate[method]])
        valid_rate[method] = {"mean": float(arr.mean()), "ci": boot_ci(arr), "n_items": len(by_method[method])}

    conditional = {}
    for method in METHODS:
        available = [a for a in by_method[method] if blind[a]["problem"].strip()]
        conditional[method] = {
            "available": len(available),
            "valid": int(sum(verdict[a] == "valid" for a in available)),
            "rate": float(np.mean([verdict[a] == "valid" for a in available])) if available else None,
        }

    paired = {}
    for baseline in ("direct", "framework"):
        diffs = np.array([per_seed_rate["puzzleforge"][s] - per_seed_rate[baseline][s]
                          for s in seeds if s in per_seed_rate["puzzleforge"] and s in per_seed_rate[baseline]])
        paired[baseline] = {"mean": float(diffs.mean()), "ci": boot_ci(diffs), "seeds": len(diffs)}

    # ---- depth / explanation / length ----
    depth, explanation, lengths = {}, {}, {}
    for method in METHODS:
        rows = [row for row in labels if key[row["anon_id"]]["method"] == method and row["judges"]]
        depth[method] = [judge["depth_score"] for row in rows for judge in row["judges"]
                         if verdict[row["anon_id"]] == "valid" and judge.get("depth_score") is not None]
        explanation[method] = [judge["explanation_score"] for row in rows for judge in row["judges"]
                               if verdict[row["anon_id"]] == "valid" and judge.get("explanation_score") is not None]
        lengths[method] = [len(blind[a]["problem"]) for a in by_method[method] if blind[a]["problem"].strip()]

    # ---- diversity ----
    diversity, novelty = {}, {}
    for method in METHODS:
        items = defaultdict(list)
        for row in records:
            if row["method"] == method and row["cohort"] == "matched" and row["status"] == "ok":
                items[row["seed_id"]].append(row)
        near = total = 0
        thresholds = (0.5, 0.6, 0.7, 0.8, 0.9)
        near_by_thr = {t: 0 for t in thresholds}
        per_pair = defaultdict(lambda: [0, 0])
        curves = defaultdict(list)
        for seed, rows in items.items():
            rows = sorted(rows, key=lambda r: r["slot"])
            gs = [grams(r["problem"]) for r in rows]
            for i, j in combinations(range(len(gs)), 2):
                total += 1
                per_pair[seed][1] += 1
                score = jaccard(gs[i], gs[j])
                for t in thresholds:
                    if score >= t:
                        near_by_thr[t] += 1
                if score >= 0.8:
                    near += 1
                    per_pair[seed][0] += 1
            for i in range(1, len(gs)):
                curves[i].append(max(jaccard(gs[i], h) for h in gs[:i]))
        rates = np.array([per_pair[s][0] / per_pair[s][1] for s in per_pair if per_pair[s][1]])
        diversity[method] = {"near_dup": near / total if total else 0.0, "pairs": total,
                             "ci": boot_ci(rates),
                             "seed_rates": sorted(float(x) for x in rates),
                             "curve": {str(t): near_by_thr[t] / total if total else 0.0 for t in thresholds}}
        idx = sorted(curves)
        novelty[method] = {"x": [i + 1 for i in idx],
                           "mean": [float(np.mean(curves[i])) for i in idx],
                           "lo": [boot_ci(np.array(curves[i]))[0] for i in idx],
                           "hi": [boot_ci(np.array(curves[i]))[1] for i in idx]}
    pf_items = defaultdict(list)
    for row in records:
        if row["method"] == "puzzleforge" and row["cohort"] == "matched" and row["status"] == "ok":
            pf_items[row["seed_id"]].append(row)
    pf_means = []
    for seed, rows in pf_items.items():
        rows = sorted(rows, key=lambda r: r["slot"])
        gs = [grams(r["problem"]) for r in rows]
        vals = [max(jaccard(gs[i], h) for h in gs[:i]) for i in range(1, len(gs))]
        if vals:
            pf_means.append(float(np.mean(vals)))
    novelty["pf_reference"] = {"mean": float(np.mean(pf_means)), "ci": boot_ci(np.array(pf_means))}

    # ---- tokens ----
    import csv
    ledger = list(csv.DictReader((RUN / "tokens_requests.csv").open(encoding="utf-8")))
    comp = defaultdict(int)
    for row in ledger:
        stage, method = row["stage"], row["method"]
        if stage == "generate":
            comp[f"{method}_prompt"] += int(row["prompt_tokens"])
            comp[f"{method}_completion"] += int(row["completion_tokens"])
        elif stage == "judge_verdict":
            comp["judge_verdict"] += int(row["total_tokens"])
        elif stage == "judge_solve":
            comp["judge_solve"] += int(row["total_tokens"])
    gen_tokens = {m: comp[f"{m}_prompt"] + comp[f"{m}_completion"] for m in ("direct", "framework")}
    raw_produced = {m: sum(1 for r in records if r["method"] == m and r["status"] == "ok")
                    for m in ("direct", "framework")}
    matched_produced = {m: sum(1 for r in records if r["method"] == m and r["cohort"] == "matched"
                               and r["status"] == "ok") for m in ("direct", "framework")}
    tokens = {"components": dict(comp), "generation": gen_tokens,
              "raw_produced": raw_produced, "matched_produced": matched_produced,
              "per_item": {m: gen_tokens[m] / raw_produced[m] if raw_produced[m] else None for m in gen_tokens},
              "per_valid": {m: gen_tokens[m] / (raw_produced[m] * conditional[m]["rate"])
                            if raw_produced[m] and conditional[m]["rate"] else None for m in gen_tokens},
              "judge_total": comp["judge_solve"] + comp["judge_verdict"],
              "judge_items": len(labels)}

    stats = {"seeds": seeds, "verdict_counts": {m: dict(Counter(verdict[a] for a in by_method[m])) for m in METHODS},
             "valid_rate": valid_rate, "valid_rate_conditional": conditional,
             "paired": paired, "per_seed_rate": per_seed_rate,
             "depth": {m: {"mean": float(np.mean(v)) if v else None, "n": len(v)} for m, v in depth.items()},
             "explanation": {m: {"mean": float(np.mean(v)) if v else None, "n": len(v)} for m, v in explanation.items()},
             "length": {m: {"median": float(np.median(v)) if v else None, "n": len(v)} for m, v in lengths.items()},
             "diversity": diversity, "tokens": tokens}
    (RUN / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- figures ----
    # 1 validity
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for i, method in enumerate(METHODS):
        mean = valid_rate[method]["mean"]
        lo, hi = valid_rate[method]["ci"]
        ax.bar(i, mean, color=COLORS[method], width=0.62)
        ax.errorbar(i, mean, yerr=[[mean - lo], [hi - mean]], color="black", capsize=6, lw=1.6)
        ax.text(i, hi + 0.02, f"{mean:.2f}", ha="center", fontsize=15, fontweight="bold")
    ax.set_xticks(range(3), [LABELS[m] for m in METHODS])
    ax.set_ylabel("Valid fraction")
    ax.set_ylim(0, 1.06)
    ax.set_title("Blind validity by method")
    save(fig, "fig1_validity")

    # 2 per-seed paired scatter (compact for 97 seeds)
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6))
    for ax, baseline in zip(axes, ("direct", "framework")):
        x = [per_seed_rate[baseline].get(s, np.nan) for s in seeds]
        y = [per_seed_rate["puzzleforge"].get(s, np.nan) for s in seeds]
        ax.scatter(x, y, s=30, color=COLORS[baseline], alpha=0.75, edgecolors="none")
        ax.plot([0, 1], [0, 1], ls="--", lw=1.2, color="#888")
        ax.set_xlim(-0.03, 1.03)
        ax.set_ylim(-0.03, 1.03)
        ax.set_xlabel(f"{LABELS[baseline]} valid fraction")
        ax.set_ylabel("PF valid fraction")
        ax.set_title(f"PF vs {LABELS[baseline]}")
    fig.tight_layout()
    save(fig, "fig2_per_seed")

    # 3 diversity across thresholds
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    thresholds = (0.5, 0.6, 0.7, 0.8, 0.9)
    for method in METHODS:
        xs = [t * 100 for t in thresholds]
        ys = [diversity[method]["curve"][str(t)] * 100 for t in thresholds]
        ax.plot(xs, ys, marker="o", ms=7, lw=2.4, color=COLORS[method], label=LABELS[method])
    ax.set_xlabel("Similarity threshold (Jaccard, %)")
    ax.set_ylabel("Near-duplicate pairs (%)")
    ax.set_title("Within-seed repetition vs threshold")
    ax.legend(frameon=False)
    ax.grid(axis="y", color="#e6e6e6")
    save(fig, "fig3_diversity")

    # 3b per-seed ECDF of repetition
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for method in METHODS:
        rates = np.array(diversity[method]["seed_rates"])
        ax.step(rates, np.arange(1, len(rates) + 1) / len(rates), where="post",
                color=COLORS[method], lw=2.4, label=f"{LABELS[method]} (n={len(rates)})")
    ax.axvline(0.5, color="#888", ls=":", lw=1.4)
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Per-seed near-duplicate rate")
    ax.set_ylabel("Cumulative share of seeds")
    ax.set_title("How many seeds collapse?")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "fig3b_seed_ecdf")

    # 4 novelty curves
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for method in ("direct", "framework"):
        curve = novelty[method]
        ax.plot(curve["x"], curve["mean"], color=COLORS[method], lw=2.4, label=LABELS[method])
        ax.fill_between(curve["x"], curve["lo"], curve["hi"], color=COLORS[method], alpha=0.18)
    ref = novelty["pf_reference"]
    ax.axhspan(ref["ci"][0], ref["ci"][1], color=COLORS["puzzleforge"], alpha=0.10)
    ax.axhline(ref["mean"], color=COLORS["puzzleforge"], ls="--", lw=2, label="PF (reference)")
    ax.set_xlabel("Item position within seed")
    ax.set_ylabel("Max similarity to earlier items")
    ax.set_title("Novelty decay (mean, 95% CI across seeds)")
    ax.legend(frameon=False)
    save(fig, "fig4_novelty")

    # 5 cost pareto
    names = {"judge_verdict": "Judge verdict", "judge_solve": "Judge solve",
             "direct_prompt": "Direct prompt", "direct_completion": "Direct output",
             "framework_completion": "Framework output", "framework_prompt": "Framework prompt"}
    ordered = sorted(comp.items(), key=lambda kv: -kv[1])
    total = sum(comp.values())
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    xs = np.arange(len(ordered))
    vals = [v / 1000 for _, v in ordered]
    ax.bar(xs, vals, color="#4a5568")
    ax.set_xticks(xs, [names.get(k, k) for k, _ in ordered], rotation=25, ha="right")
    ax.set_ylabel("Tokens (thousands)")
    ax2 = ax.twinx()
    cum = np.cumsum([v for _, v in ordered]) / total * 100
    ax2.plot(xs, cum, color="#c53030", marker="o", lw=2)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("Cumulative share (%)")
    ax.set_title("Token cost Pareto")
    save(fig, "fig5_cost_pareto")

    # 6 cost per item / per valid item
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    width = 0.34
    for i, method in enumerate(("direct", "framework")):
        ax.bar(i - width / 2, tokens["per_item"][method], width, color=COLORS[method],
               label="per generated" if i == 0 else None)
        ax.bar(i + width / 2, tokens["per_valid"][method], width, color=COLORS[method], alpha=0.45,
               hatch="//", label="per valid (est.)" if i == 0 else None)
        ax.text(i - width / 2, tokens["per_item"][method] * 1.02, f"{tokens['per_item'][method]:,.0f}",
                ha="center", fontsize=12)
        ax.text(i + width / 2, tokens["per_valid"][method] * 1.02, f"{tokens['per_valid'][method]:,.0f}",
                ha="center", fontsize=12)
    ax.set_xticks(range(2), ["Direct", "Framework"])
    ax.set_ylabel("Generation tokens per question")
    ax.set_title("Generation cost per usable question")
    ax.legend(frameon=False)
    save(fig, "fig6_cost_per_question")

    # 7 depth + length
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4))
    ax = axes[0]
    for i, method in enumerate(METHODS):
        vals = depth[method]
        ax.scatter(np.full(len(vals), i) + RNG.normal(0, 0.06, len(vals)), vals, s=22,
                   color=COLORS[method], alpha=0.75)
        if vals:
            ax.hlines(np.mean(vals), i - 0.26, i + 0.26, color="black", lw=2)
    ax.set_xticks(range(3), [LABELS[m] for m in METHODS])
    ax.set_ylabel("Depth score (0–4)")
    ax.set_title("Reasoning depth (valid items)")
    ax = axes[1]
    for i, method in enumerate(METHODS):
        vals = lengths[method]
        ax.scatter(np.full(len(vals), i) + RNG.normal(0, 0.06, len(vals)), vals, s=18,
                   color=COLORS[method], alpha=0.6)
        ax.hlines(np.median(vals), i - 0.26, i + 0.26, color="black", lw=2)
    ax.set_yscale("log")
    ax.set_xticks(range(3), [LABELS[m] for m in METHODS])
    ax.set_ylabel("Problem length (characters, log)")
    ax.set_title("Problem length")
    fig.tight_layout()
    save(fig, "fig7_depth_length")

    print(json.dumps({"valid_rate": valid_rate, "paired": paired, "diversity":
                      {m: diversity[m]["near_dup"] for m in METHODS}, "tokens": tokens}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
