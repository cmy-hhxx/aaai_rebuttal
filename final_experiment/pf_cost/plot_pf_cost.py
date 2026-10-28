"""Plot per-valid-question generation cost, including measured PF amortization."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "run"
plt.rcParams.update({"font.size": 14, "axes.titlesize": 16, "axes.labelsize": 15,
                     "xtick.labelsize": 13, "ytick.labelsize": 13, "figure.dpi": 200})

stats = json.loads((RUN / "stats.json").read_text())
pf = json.loads((HERE / "pf_cost_summary.json").read_text())
cond = stats["valid_rate_conditional"]
# generation tokens per generated question
direct_q = stats["tokens"]["per_item"]["direct"]
fw_q = stats["tokens"]["per_item"]["framework"]
direct_v = direct_q / cond["direct"]["rate"]
fw_v = fw_q / cond["framework"]["rate"]
pf20 = pf["per_valid_question"]["at_20_instances"]
pf200 = pf["per_valid_question"]["at_200_instances"]

labels = ["Direct", "Framework", "PF\n(200/gen)", "PF\n(20/gen)"]
values = [direct_v, fw_v, pf200, pf20]
colors = ["#dd6b20", "#c53030", "#2b6cb0", "#90cdf4"]

fig, ax = plt.subplots(figsize=(7.6, 4.8))
bars = ax.bar(range(4), values, color=colors, width=0.62)
ax.set_yscale("log")
ax.set_xticks(range(4), labels)
ax.set_ylabel("Generation tokens per valid question")
ax.set_title("What does one valid question cost to generate?")
for bar, value in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width() / 2, value * 1.15, f"{value:,.0f}",
            ha="center", fontsize=13, fontweight="bold")
ax.set_ylim(300, 30000)
fig.tight_layout()
fig.savefig(HERE / "fig6b_pf_cost.png", bbox_inches="tight")
fig.savefig(HERE / "fig6b_pf_cost.svg", bbox_inches="tight")
print({"direct": round(direct_v), "framework": round(fw_v), "pf_200": round(pf200), "pf_20": round(pf20)})
