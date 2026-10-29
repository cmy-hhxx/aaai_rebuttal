#!/usr/bin/env python3
"""Figures for the illustrated rebuttal document.

Reads frozen artifacts only; writes tmp/doc_figures/fig{1..4}.png.
Run with tmp/figvenv/bin/python (matplotlib 3.11) and MPLCONFIGDIR=tmp/mplconfig.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "final_experiment" / "run"
OUT = ROOT / "tmp" / "doc_figures"
OUT.mkdir(parents=True, exist_ok=True)

COL = {"PF": "#2b6cb0", "B2": "#c53030", "B1": "#dd6b20"}
NAME = {"PF": "PF", "B2": "B2\n(one-pass generator)", "B1": "B1\n(direct)"}
PURPLE = "#6b46c1"
GRAY = "#4a5568"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 200,
    "savefig.dpi": 200,
})


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- fig 1
stats = json.loads((RUN / "stats.json").read_text(encoding="utf-8"))
order = ["PF", "B2", "B1"]
method_key = {"PF": "puzzleforge", "B2": "framework", "B1": "direct"}
means = [stats["valid_rate"][method_key[m]]["mean"] for m in order]
lo = [stats["valid_rate"][method_key[m]]["ci"][0] for m in order]
hi = [stats["valid_rate"][method_key[m]]["ci"][1] for m in order]

fig, ax = plt.subplots(figsize=(5.4, 3.6))
x = np.arange(3)
bars = ax.bar(x, means, color=[COL[m] for m in order], width=0.62, zorder=2)
ax.errorbar(x, means, yerr=[np.array(means) - lo, np.array(hi) - means], fmt="none",
            ecolor="#1a202c", elinewidth=1.2, capsize=5, capthick=1.2, zorder=3)
for i, (m, value) in enumerate(zip(order, means)):
    ax.text(i, hi[i] + 0.025, f"{value:.2f}", ha="center", va="bottom", fontweight="bold", fontsize=11)
ax.set_xticks(x)
ax.set_xticklabels([NAME[m] for m in order])
ax.set_ylim(0, 1.0)
ax.set_ylabel("Valid fraction")
ax.set_title("Blind validity by pipeline (480 items each)", pad=10)
ax.grid(axis="y", color="#e2e8f0", linewidth=0.8, zorder=0)
ax.set_axisbelow(True)
save(fig, "fig1_validity")

# ---------------------------------------------------------------- fig 2
agreement = json.loads((ROOT / "runs" / "judge_k3" / "agreement.json").read_text(encoding="utf-8"))
by = agreement["by_method"]
fig, ax = plt.subplots(figsize=(6.2, 3.4))
ys = np.arange(3)[::-1]
for y, m in zip(ys, order):
    cell = by[m]
    ax.plot([cell["strict"], cell["liberal"]], [y, y], color="#cbd5e0", linewidth=9, solid_capstyle="round", zorder=1)
    ax.scatter([cell["luna"]], [y], color=COL["PF"], s=55, zorder=3, label="gpt-5.6-luna" if m == "PF" else None)
    ax.scatter([cell["gemini"]], [y], color=PURPLE, s=55, marker="D", zorder=3,
               label="gemini-3.1-pro-preview" if m == "PF" else None)
    ax.scatter([cell["strict"]], [y], facecolor="white", edgecolor=GRAY, s=45, marker="s", zorder=4,
               label="both valid (strict)" if m == "PF" else None)
    ax.scatter([cell["liberal"]], [y], facecolor="white", edgecolor=GRAY, s=45, marker="o", zorder=4,
               label="either valid (liberal)" if m == "PF" else None)
    ax.text(cell["luna"], y + 0.18, f"{cell['luna']:.2f}", ha="center", va="bottom", fontsize=8,
            color=COL["PF"], clip_on=False)
    ax.text(cell["gemini"], y - 0.22, f"{cell['gemini']:.2f}", ha="center", va="top", fontsize=8,
            color=PURPLE, clip_on=False)
ax.set_yticks(ys)
ax.set_yticklabels([NAME[m] for m in order])
ax.set_xlim(0, 1)
ax.set_ylim(-0.65, 2.55)
ax.set_xlabel("Valid fraction")
ax.set_title("Validity under two judge families (560-item overlap)", pad=10)
ax.grid(axis="x", color="#e2e8f0", linewidth=0.8, zorder=0)
ax.set_axisbelow(True)
ax.legend(loc="lower right", fontsize=7, frameon=True, framealpha=0.95, ncol=1)
save(fig, "fig2_judges")

# ---------------------------------------------------------------- data for fig 3
key = {row["anon_id"]: row for row in jl(RUN / "audit" / "audit_key.jsonl")}
blind = {row["anon_id"]: row for row in jl(RUN / "audit" / "audit_blind.jsonl")}
labels = {row["anon_id"]: row for row in jl(RUN / "auto" / "model_labels.jsonl")}
rob = json.loads((RUN / "analysis" / "rebuttal_robustness.json").read_text(encoding="utf-8"))
cuts = rob["meta"]["cut_points_pooled_depth"]


def length_bin(value: int) -> int:
    for index, cut in enumerate(cuts):
        if value <= cut:
            return index
    return len(cuts)


items = []
for anon, link in key.items():
    judges = (labels.get(anon) or {}).get("judges") or []
    if not judges:
        continue
    judge = judges[0]
    items.append({
        "method": {"puzzleforge": "PF", "framework": "B2", "direct": "B1"}[link["method"]],
        "length": len(blind[anon]["problem"]),
        "valid": judge["verdict"] == "valid",
        "depth": judge.get("depth_score"),
    })

bins = [length_bin(row["length"]) for row in items]
edges = [0] + cuts + [max(row["length"] for row in items) + 1]
labels_x = [f"Q{i + 1}\n[{edges[i]}, {edges[i + 1]})" for i in range(len(cuts) + 1)]

depth_mean = {}
yield_rate = {}
n_valid = {}
for method in ("PF", "B2"):
    depth_mean[method] = []
    yield_rate[method] = []
    n_valid[method] = []
    for index in range(len(cuts) + 1):
        sub = [row for row, b in zip(items, bins) if row["method"] == method and b == index]
        valid = [row for row in sub if row["valid"] and row["depth"] is not None]
        depth_mean[method].append(statistics.fmean(row["depth"] for row in valid) if valid else 0.0)
        yield_rate[method].append(sum(1 for row in sub if row["valid"] and row["depth"] is not None and row["depth"] >= 3) / len(sub) if sub else 0.0)
        n_valid[method].append(len(valid))

fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.6))
x = np.arange(len(labels_x))
width = 0.36
for ax, values, ylabel, title, ymax in (
    (axes[0], depth_mean, "Mean depth (0–4)", "Depth among valid items", 4.0),
    (axes[1], yield_rate, "Valid >=3-step items / slot", ">=3-step yield per requested slot", 0.8),
):
    for offset, method in ((-width / 2, "PF"), (width / 2, "B2")):
        bars = ax.bar(x + offset, values[method], width=width, color=COL[method], label=method, zorder=2)
        for rect, value, n in zip(bars, values[method], n_valid[method]):
            ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + (0.03 if ymax < 1 else 0.08),
                    f"{value:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels_x, fontsize=7)
    ax.set_ylabel(ylabel)
    ax.set_title(title, pad=8)
    ax.set_ylim(0, ymax)
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
fig.suptitle("Depth and yield by pooled problem-length quintile", fontsize=12, y=1.01)
save(fig, "fig3_length")

# ---------------------------------------------------------------- fig 4
cost = rob["cost"]["scales"]
fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4), sharey=True)
for ax, scale, title in (
    (axes[0], "design_200_per_unit", "200 instances / unit"),
    (axes[1], "twenty_per_unit", "20 instances / unit"),
):
    values = [cost[scale][f"{m}_tokens_per_valid"] for m in order]
    bars = ax.bar(np.arange(3), values, color=[COL[m] for m in order], width=0.6, zorder=2)
    for rect, value in zip(bars, values):
        ax.text(rect.get_x() + rect.get_width() / 2, value * 1.08, f"{value:,.0f}",
                ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels([NAME[m] for m in order], fontsize=8)
    ax.set_yscale("log")
    ax.set_title(title, pad=8)
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
axes[0].set_ylabel("Generation tokens per valid item (log)")
axes[0].set_ylim(30, 26000)
fig.suptitle("PF/B2 is ~25x at either scale", fontsize=12, y=1.02)
save(fig, "fig4_cost")

print(OUT)
for path in sorted(OUT.glob("*.png")):
    print(path, f"{path.stat().st_size / 1024:.0f} KB")
