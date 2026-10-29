"""Generator-level and confound controls for the rebuttal (read-only over frozen artifacts).

Why this exists: the seed-level report compares PF (a released dataset built from
multiple generators per seed) with B2 (one generator per seed). That makes
"seeds with zero valid items" and "per-generator validity" incomparable. This
script recomputes the comparison at the generator level, matches PF to one
generator per seed, splits PF by expansion variant (_0 vs _1.._3), and controls
the depth gap for problem length. Nothing here re-samples API calls or re-judges
items; it only regroups the frozen labels.

Consumes: audit/audit_blind.jsonl, audit/audit_key.jsonl,
          auto/model_labels.jsonl, records_selected.jsonl
Emits:    analysis/rebuttal_generator_level.json (+ stdout summary)
"""

from __future__ import annotations

import json
import math
import re
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

RUN = Path(__file__).resolve().parents[1] / "run"
METHODS = ("puzzleforge", "framework", "direct")


def load_jsonl(path: Path) -> list[dict]:
    # U+2029 appears in one problem text; splitlines() would break that JSON.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def label_for(labels: dict[str, dict], anon_id: str) -> dict:
    lab = labels.get(anon_id)
    if not lab:
        return {"verdict": "unavailable", "depth": None, "certificate": None}
    judge = lab["judges"][0] if lab.get("judges") else {}
    return {
        "verdict": judge.get("verdict", lab.get("status", "unavailable")),
        "depth": judge.get("depth_score"),
        "certificate": judge.get("explanation_score"),
    }


def variant_of(generator_id: str | None, seed_id: str) -> str:
    """Return '_0'..'_3' for PF generators; 'n/a' otherwise."""
    if not generator_id or not generator_id.startswith(seed_id):
        return "n/a"
    suffix = generator_id[len(seed_id) :]
    return suffix if suffix in {"_0", "_1", "_2", "_3"} else "n/a"


def ols_cluster_bootstrap(rows: list[dict], treated: str, group: str = "seed", n_boot: int = 1000) -> dict:
    """depth ~ 1 + is_treated + log(length), plus a seed-fixed-effects variant.

    Returns point estimates and a seed-cluster bootstrap 95% CI for the treated
    coefficient. rows must contain method, seed, length, depth; `treated` names
    the method coded 1.
    """
    y = np.array([r["depth"] for r in rows], dtype=float)
    pf = np.array([r["method"] == treated for r in rows], dtype=float)
    ll = np.array([math.log(max(r["length"], 1)) for r in rows], dtype=float)
    x = np.column_stack([np.ones(len(rows)), pf, ll])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)

    seeds = sorted({r[group] for r in rows})
    index = {s: i for i, s in enumerate(seeds)}
    fe = np.zeros((len(rows), len(seeds)))
    for i, r in enumerate(rows):
        fe[i, index[r[group]]] = 1.0
    x_fe = np.column_stack([fe, pf, ll])
    beta_fe, *_ = np.linalg.lstsq(x_fe, y, rcond=None)

    rng = np.random.default_rng(20261028)
    by_seed = defaultdict(list)
    for i, r in enumerate(rows):
        by_seed[r[group]].append(i)
    boot_plain, boot_fe = [], []
    for _ in range(n_boot):
        draw = rng.choice(seeds, size=len(seeds), replace=True)
        idx = [i for s in draw for i in by_seed[s]]
        if len(set(np.array([rows[i][group] for i in idx]))) < 2:
            continue
        yy, xx, xx_fe = y[idx], x[idx], x_fe[idx]
        b, *_ = np.linalg.lstsq(xx, yy, rcond=None)
        boot_plain.append(b[1])
        b_fe, *_ = np.linalg.lstsq(xx_fe, yy, rcond=None)
        boot_fe.append(b_fe[-2])

    def q(v):
        return [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] if v else None

    return {
        "n_items": len(rows),
        "raw_gap": float(y[pf == 1].mean() - y[pf == 0].mean()),
        "ols_pf_coef": float(beta[1]),
        "ols_loglen_coef": float(beta[2]),
        "ols_pf_ci": q(boot_plain),
        "ols_fe_pf_coef": float(beta_fe[-2]),
        "ols_fe_loglen_coef": float(beta_fe[-1]),
        "ols_fe_pf_ci": q(boot_fe),
        "n_boot": len(boot_plain),
    }


def strata(rows: list[dict], cuts: list[float]) -> list[dict]:
    out = []
    for lo, hi in zip(cuts[:-1], cuts[1:]):
        cell = {}
        for method in ("puzzleforge", "framework", "direct"):
            vals = [r["depth"] for r in rows if r["method"] == method and lo <= r["length"] <= hi]
            cell[method] = {"n": len(vals), "mean_depth": statistics.fmean(vals) if vals else None}
        pf, fw = cell["puzzleforge"], cell["framework"]
        gap = (
            pf["mean_depth"] - fw["mean_depth"]
            if pf["mean_depth"] is not None and fw["mean_depth"] is not None
            else None
        )
        out.append({"lo": lo, "hi": hi, "cell": cell, "pf_minus_fw": gap})
    return out


def main() -> None:
    key = {r["anon_id"]: r for r in load_jsonl(RUN / "audit" / "audit_key.jsonl")}
    blind = {r["anon_id"]: r for r in load_jsonl(RUN / "audit" / "audit_blind.jsonl")}
    labels = {r["anon_id"]: r for r in load_jsonl(RUN / "auto" / "model_labels.jsonl")}
    records = {r["id"]: r for r in load_jsonl(RUN / "records_selected.jsonl")}

    items = []
    for anon_id, meta in key.items():
        rec = records.get(meta["id"], {})
        lab = label_for(labels, anon_id)
        items.append(
            {
                "anon_id": anon_id,
                "method": meta["method"],
                "seed": meta["seed_id"],
                "generator": rec.get("generator_id"),
                "variant": variant_of(rec.get("generator_id"), meta["seed_id"]),
                "length": len(blind[anon_id]["problem"]) if anon_id in blind else None,
                "verdict": lab["verdict"],
                "depth": lab["depth"],
                "certificate": lab["certificate"],
            }
        )

    seeds = sorted({it["seed"] for it in items})
    valid = [it for it in items if it["verdict"] == "valid" and it["depth"] is not None]

    # ---- generator-level yield ------------------------------------------------
    per_gen = defaultdict(lambda: {"n": 0, "valid": 0, "depths": [], "seed": None, "variant": None})
    for it in items:
        if it["method"] != "puzzleforge":
            continue
        g = per_gen[it["generator"]]
        g["n"] += 1
        g["valid"] += it["verdict"] == "valid"
        g["seed"] = it["seed"]
        g["variant"] = it["variant"]
        if it["verdict"] == "valid" and it["depth"] is not None:
            g["depths"].append(it["depth"])

    def gen_stats(min_judged: int) -> dict:
        sub = {g: v for g, v in per_gen.items() if v["n"] >= min_judged}
        zero = sum(1 for v in sub.values() if v["valid"] == 0)
        return {
            "n_generators": len(sub),
            "zero_valid": zero,
            "zero_valid_rate": zero / len(sub) if sub else None,
            "mean_validity": statistics.fmean(v["valid"] / v["n"] for v in sub.values()) if sub else None,
        }

    gen_level = {f"min_{n}_judged": gen_stats(n) for n in (1, 2, 3, 4)}

    # per-seed generator counts
    gens_per_seed = defaultdict(set)
    for it in items:
        if it["method"] == "puzzleforge" and it["generator"]:
            gens_per_seed[it["seed"]].add(it["generator"])
    gen_count_dist = Counter(len(gens_per_seed[s]) for s in seeds)

    # ---- match PF to one generator per seed -----------------------------------
    per_seed_gens = defaultdict(lambda: defaultdict(lambda: {"n": 0, "valid": 0, "ge3": 0, "depths": []}))
    for it in items:
        if it["method"] != "puzzleforge" or not it["generator"]:
            continue
        cell = per_seed_gens[it["seed"]][it["generator"]]
        cell["n"] += 1
        cell["valid"] += it["verdict"] == "valid"
        if it["verdict"] == "valid" and it["depth"] is not None:
            cell["depths"].append(it["depth"])
            cell["ge3"] += it["depth"] >= 3

    rng = np.random.default_rng(20261028)
    zero_draws, val_draws, depth_draws, ge3_draws = [], [], [], []
    for _ in range(2000):
        z, vals, deps, ge3 = 0, [], [], []
        for seed in seeds:
            gens = per_seed_gens[seed]
            if not gens:
                continue
            g = list(gens)[int(rng.integers(0, len(gens)))]
            cell = gens[g]
            if cell["n"] == 0:
                continue
            vals.append(cell["valid"] / cell["n"])
            ge3.append(cell["ge3"] / cell["n"])
            z += cell["valid"] == 0
            deps.extend(cell["depths"])
        zero_draws.append(z)
        val_draws.append(statistics.fmean(vals))
        ge3_draws.append(statistics.fmean(ge3))
        depth_draws.append(statistics.fmean(deps) if deps else float("nan"))

    one_gen_matched = {
        "draws": 2000,
        "zero_valid_seeds_mean": statistics.fmean(zero_draws),
        "zero_valid_seeds_ci": [
            float(np.quantile(zero_draws, 0.025)),
            float(np.quantile(zero_draws, 0.975)),
        ],
        "validity_mean": statistics.fmean(val_draws),
        "validity_ci": [float(np.quantile(val_draws, 0.025)), float(np.quantile(val_draws, 0.975))],
        "depth_mean": statistics.fmean(d for d in depth_draws if not math.isnan(d)),
        "depth_ci": [
            float(np.quantile([d for d in depth_draws if not math.isnan(d)], 0.025)),
            float(np.quantile([d for d in depth_draws if not math.isnan(d)], 0.975)),
        ],
        "valid_ge3_steps_mean": statistics.fmean(ge3_draws),
        "valid_ge3_steps_ci": [float(np.quantile(ge3_draws, 0.025)), float(np.quantile(ge3_draws, 0.975))],
    }

    # deterministic single-generator picks for a reproducible table
    det = {}
    for name, pick in (
        ("max_judged", lambda gs: max(gs, key=lambda g: (gs[g]["n"], g))),
        ("first_id", lambda gs: sorted(gs)[0]),
    ):
        z, vals = 0, []
        for seed in seeds:
            gens = per_seed_gens[seed]
            if not gens:
                continue
            cell = gens[pick(gens)]
            vals.append(cell["valid"] / cell["n"])
            z += cell["valid"] == 0
        det[name] = {"zero_valid_seeds": z, "validity_mean": statistics.fmean(vals)}

    # ---- independence model ---------------------------------------------------
    q_gen = gen_stats(1)["zero_valid_rate"]
    expected_zero = sum(q_gen ** len(gens_per_seed[s]) for s in seeds)
    independence = {
        "per_generator_zero_rate": q_gen,
        "generators_per_seed_distribution": {str(k): v for k, v in sorted(gen_count_dist.items())},
        "expected_zero_valid_seeds": expected_zero,
        "observed_zero_valid_seeds": sum(
            1 for s in seeds if all(v["valid"] == 0 for v in per_seed_gens[s].values())
        ),
    }

    # ---- variant split --------------------------------------------------------
    variant = defaultdict(lambda: {"n": 0, "valid": 0, "depths": [], "lengths": [], "ge3": 0})
    for it in valid:
        if it["method"] != "puzzleforge" or it["variant"] == "n/a":
            continue
        v = variant[it["variant"]]
        v["depths"].append(it["depth"])
        v["ge3"] += it["depth"] >= 3
    for it in items:
        if it["method"] != "puzzleforge" or it["variant"] == "n/a":
            continue
        v = variant[it["variant"]]
        v["n"] += it["verdict"] != "unavailable"
        v["valid"] += it["verdict"] == "valid"
        if it["length"]:
            v["lengths"].append(it["length"])
    variant_split = {
        k: {
            "n_judged": v["n"],
            "valid": v["valid"],
            "validity": v["valid"] / v["n"] if v["n"] else None,
            "mean_depth": statistics.fmean(v["depths"]) if v["depths"] else None,
            "valid_ge3_steps": v["ge3"],
            "median_length": statistics.median(v["lengths"]) if v["lengths"] else None,
        }
        for k, v in sorted(variant.items())
    }

    # ---- length-controlled depth ---------------------------------------------
    pf_fw = [it for it in valid if it["method"] in ("puzzleforge", "framework")]
    fw_b1 = [it for it in valid if it["method"] in ("framework", "direct")]
    length_control = {
        "pf_vs_framework": ols_cluster_bootstrap(pf_fw, "puzzleforge"),
        "framework_vs_direct": ols_cluster_bootstrap(fw_b1, "framework"),
        "strata_quartiles": strata(pf_fw, list(np.quantile([it["length"] for it in pf_fw], [0, 0.25, 0.5, 0.75, 1.0]))),
    }

    # ---- B2 per-generator (one generator per seed) ----------------------------
    b2 = defaultdict(lambda: {"n": 0, "valid": 0, "depths": []})
    for it in items:
        if it["method"] != "framework":
            continue
        c = b2[it["seed"]]
        c["n"] += it["verdict"] != "unavailable"
        c["valid"] += it["verdict"] == "valid"
        if it["verdict"] == "valid" and it["depth"] is not None:
            c["depths"].append(it["depth"])
    b2_seed = {
        "seeds": len(b2),
        "zero_valid_seeds": sum(1 for v in b2.values() if v["valid"] == 0),
        "validity_mean": statistics.fmean(v["valid"] / v["n"] for v in b2.values() if v["n"]),
        "mean_depth": statistics.fmean(d for v in b2.values() for d in v["depths"]),
    }


    # ---- within-unit diversity (near-dup and tag-set identity) --------------
    def normalise(text: str) -> str:
        return re.sub(r"\s+", "", text)

    def grams(text: str, n: int = 4) -> set[str]:
        text = normalise(text)
        return {text[i : i + n] for i in range(max(0, len(text) - n + 1))}

    def jaccard(a: set[str], b: set[str]) -> float:
        return len(a & b) / len(a | b) if a and b else 0.0

    near_groups = defaultdict(list)
    for r in records.values():
        if r.get("cohort") != "matched" or r.get("status") != "ok":
            continue
        unit = r.get("generator_id") if r["method"] == "puzzleforge" else r["seed_id"]
        near_groups[(r["method"], unit)].append(r)
    near_stats = {}
    for m in METHODS:
        near = total = 0
        units = 0
        for (mm, unit), rows in near_groups.items():
            if mm != m:
                continue
            units += 1
            rows = sorted(rows, key=lambda r: r.get("slot", 0))
            gs = [grams(r["problem"]) for r in rows]
            for i, j in combinations(range(len(gs)), 2):
                total += 1
                near += jaccard(gs[i], gs[j]) >= 0.8
        near_stats[m] = {"units": units, "pairs": total, "near_dup_0_8": near / total if total else None}

    tag_groups = defaultdict(list)
    for it in items:
        unit = it["generator"] if it["method"] == "puzzleforge" else it["seed"]
        if unit is None:
            continue
        lab = labels.get(it["anon_id"])
        judge = lab["judges"][0] if lab and lab.get("judges") else {}
        tag_groups[(it["method"], unit)].append(
            (frozenset(judge.get("reasoning_type_tags") or []), frozenset(judge.get("constraint_type_tags") or []))
        )
    tag_stats = {}
    for m in METHODS:
        rp = cp = total = 0
        for (mm, unit), rows in tag_groups.items():
            if mm != m:
                continue
            for x, y in combinations(rows, 2):
                total += 1
                rp += x[0] == y[0]
                cp += x[1] == y[1]
        tag_stats[m] = {
            "pairs": total,
            "identical_reasoning_tagset": rp / total if total else None,
            "identical_constraint_tagset": cp / total if total else None,
        }

    gen_variant = {}
    for r in records.values():
        if r["method"] == "puzzleforge" and r.get("generator_id"):
            gid, sid = r["generator_id"], r["seed_id"]
            gen_variant[gid] = gid[len(sid) :] if gid.startswith(sid) else "n/a"
    variant_near = {}
    for v in ("_0", "_1", "_2", "_3"):
        near = total = 0
        for (m, unit), rows in near_groups.items():
            if m != "puzzleforge" or gen_variant.get(unit) != v:
                continue
            rows = sorted(rows, key=lambda r: r.get("slot", 0))
            gs = [grams(r["problem"]) for r in rows]
            for i, j in combinations(range(len(gs)), 2):
                total += 1
                near += jaccard(gs[i], gs[j]) >= 0.8
        variant_near[v] = {"pairs": total, "near_dup_0_8": near / total if total else None}

    within_unit_diversity = {"near_dup": near_stats, "tagset": tag_stats, "variant_near_dup": variant_near}

    out = {
        "meta": {
            "seeds": len(seeds),
            "items": len(items),
            "note": "generator-level regrouping of frozen labels; no new API calls",
            "bootstrap": "2000 draws over seeds for one-generator matching; 1000 cluster bootstrap for OLS",
        },
        "generator_level": {
            "by_min_judged": gen_level,
            "generators_per_seed": {str(k): v for k, v in sorted(gen_count_dist.items())},
        },
        "one_generator_matched": {**one_gen_matched, "deterministic": det},
        "independence_model": independence,
        "variant_split": variant_split,
        "length_control": length_control,
        "framework_seed_level": b2_seed,
        "within_unit_diversity": within_unit_diversity,
    }
    (RUN / "analysis").mkdir(exist_ok=True)
    (RUN / "analysis" / "rebuttal_generator_level.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps({k: out[k] for k in ("generator_level", "one_generator_matched", "independence_model", "variant_split", "framework_seed_level", "within_unit_diversity")}, indent=2, ensure_ascii=False))
    print("\n=== length control ===")
    for name, e in length_control.items():
        if name == "strata_quartiles":
            for s in e:
                print(f"  [{int(s['lo'])},{int(s['hi'])}] PF {s['cell']['puzzleforge']} FW {s['cell']['framework']}")
        else:
            print(f"  {name}: raw {e['raw_gap']:+.3f} ols {e['ols_pf_coef']:+.3f} CI {e['ols_pf_ci']} fe {e['ols_fe_pf_coef']:+.3f} CI {e['ols_fe_pf_ci']}")


if __name__ == "__main__":
    main()
