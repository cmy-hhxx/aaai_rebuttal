#!/usr/bin/env python3
"""Cross-family judge agreement and sensitivity analysis.

Compares the original k=1 gpt-5.6-luna labels with the k=3 luna run and the
k=3 gemini-3.1-pro-preview run.  Each run has one verdict per item per model
(the k=3 factor is three independent solver samples; the judge sees all three).

Outputs:
  runs/judge_k3/agreement.json
  runs/judge_k3/agreement.md

Usage:
  python3 final_experiment/analysis/rebuttal_judge_agreement.py [--allow-partial]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "final_experiment" / "run"
K3 = ROOT / "runs" / "judge_k3"
ORIGINAL = RUN / "auto" / "model_labels.jsonl"
METHODS = {"puzzleforge": "PF", "framework": "B2", "direct": "B1"}


def jl(path: Path) -> list[dict]:
    if not path.exists():
        return []
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
        out.append(border if row[0] == "-" else line(row))
    out.append(border)
    return "\n".join(out)


def load(path: Path, label: str) -> dict[str, dict]:
    rows = {}
    for row in jl(path):
        judges = row.get("judges") or []
        if not judges:
            rows[row["anon_id"]] = {"verdict": row.get("status", "unavailable"), "depth": None,
                                    "solver": [], "error_types": [], "label": label,
                                    "attempts": len(row.get("attempts") or [])}
            continue
        judge = judges[0]
        rows[row["anon_id"]] = {
            "verdict": judge["verdict"],
            "depth": judge.get("depth_score"),
            "solver": list(judge.get("solver_correct") or []),
            "error_types": list(judge.get("error_types") or []),
            "label": label,
            "attempts": len(row.get("attempts") or []),
        }
    return rows


def kappa(pairs: list[tuple[str, str]], classes: tuple[str, ...]) -> float | None:
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    counts_a = Counter(a for a, _ in pairs)
    counts_b = Counter(b for _, b in pairs)
    expected = sum((counts_a.get(c, 0) / n) * (counts_b.get(c, 0) / n) for c in classes)
    return (observed - expected) / (1 - expected) if expected < 1 else None


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def validity(rows: dict[str, dict], mode: str) -> dict[str, float]:
    values = defaultdict(list)
    for anon, row in rows.items():
        if ":" not in anon:
            continue
        method = anon.split(":")[0]
        verdicts = row["verdicts"] if isinstance(row.get("verdicts"), list) else [row["verdict"]]
        valid = [v == "valid" for v in verdicts]
        if mode == "strict":
            value = all(valid)
        elif mode == "liberal":
            value = any(valid)
        else:
            value = sum(valid) / len(valid) >= 0.5
        values[method].append(value)
    return {m: sum(v) / len(v) for m, v in values.items() if v}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--luna", default=str(K3 / "luna" / "model_labels.jsonl"))
    parser.add_argument("--gemini", default=str(K3 / "gemini" / "model_labels.jsonl"))
    args = parser.parse_args()

    original = load(ORIGINAL, "luna_k1")
    luna = load(Path(args.luna), "luna_k3")
    gemini = load(Path(args.gemini), "gemini_k3")
    if not luna or not gemini:
        raise SystemExit("judge runs are not finished; rerun with populated model_labels.jsonl")
    n = min(len(luna), len(gemini))
    if not args.allow_partial and (len(luna) < 1440 or len(gemini) < 1440):
        raise SystemExit(f"partial runs: luna={len(luna)} gemini={len(gemini)}; pass --allow-partial")

    key = {row["anon_id"]: row for row in jl(RUN / "audit" / "audit_key.jsonl")}
    blind = {row["anon_id"]: row for row in jl(RUN / "audit" / "audit_blind.jsonl")}
    common = sorted(set(luna) & set(gemini) & set(key))
    rows = {}
    for anon in common:
        rows[anon] = {
            "method": key[anon]["method"],
            "seed": key[anon]["seed_id"],
            "length": len(blind[anon]["problem"]),
            "verdicts": [luna[anon]["verdict"], gemini[anon]["verdict"]],
            "depths": [luna[anon]["depth"], gemini[anon]["depth"]],
            "solver": [luna[anon]["solver"], gemini[anon]["solver"]],
            "errors": {"luna": luna[anon]["error_types"], "gemini": gemini[anon]["error_types"]},
            "original": (original.get(anon) or {}).get("verdict"),
        }

    classes = ("valid", "invalid", "uncertain", "unavailable")
    pairs = [(r["verdicts"][0], r["verdicts"][1]) for r in rows.values()
             if r["verdicts"][0] in classes and r["verdicts"][1] in classes]
    confusion = Counter(pairs)
    agree = sum(a == b for a, b in pairs) / len(pairs) if pairs else None
    kappa_all = kappa(pairs, classes)
    binary = [(a == "valid", b == "valid") for a, b in pairs]
    kappa_binary = kappa([(str(a), str(b)) for a, b in binary], ("True", "False"))

    by_method = {}
    for method in METHODS:
        sub = [r for r in rows.values() if r["method"] == method]
        luna_valid = sum(r["verdicts"][0] == "valid" for r in sub) / len(sub)
        gemini_valid = sum(r["verdicts"][1] == "valid" for r in sub) / len(sub)
        strict = sum(r["verdicts"][0] == "valid" and r["verdicts"][1] == "valid" for r in sub) / len(sub)
        liberal = sum(r["verdicts"][0] == "valid" or r["verdicts"][1] == "valid" for r in sub) / len(sub)
        by_method[METHODS[method]] = {
            "n": len(sub), "luna": luna_valid, "gemini": gemini_valid,
            "strict": strict, "liberal": liberal,
            "k1": sum((r["original"] == "valid") for r in sub) / len(sub),
            "luna_invalid": sum(r["verdicts"][0] == "invalid" for r in sub) / len(sub),
            "gemini_invalid": sum(r["verdicts"][1] == "invalid" for r in sub) / len(sub),
            "both_invalid": sum(r["verdicts"][0] == "invalid" and r["verdicts"][1] == "invalid" for r in sub) / len(sub),
            "luna_only_invalid": sum(r["verdicts"][0] == "invalid" and r["verdicts"][1] == "valid" for r in sub) / len(sub),
            "gemini_only_invalid": sum(r["verdicts"][1] == "invalid" and r["verdicts"][0] == "valid" for r in sub) / len(sub),
        }

    # depth on items both judges call valid
    depth = {}
    for method in METHODS:
        sub = [r for r in rows.values()
               if r["method"] == method and r["verdicts"][0] == "valid" and r["verdicts"][1] == "valid"]
        luna_depths = [r["depths"][0] for r in sub if r["depths"][0] is not None]
        gemini_depths = [r["depths"][1] for r in sub if r["depths"][1] is not None]
        depth[METHODS[method]] = {
            "n": len(sub),
            "luna": statistics.fmean(luna_depths) if luna_depths else None,
            "gemini": statistics.fmean(gemini_depths) if gemini_depths else None,
        }
    depth_gap = {
        "luna": (depth["PF"]["luna"] - depth["B2"]["luna"]) if depth["PF"]["luna"] and depth["B2"]["luna"] else None,
        "gemini": (depth["PF"]["gemini"] - depth["B2"]["gemini"]) if depth["PF"]["gemini"] and depth["B2"]["gemini"] else None,
    }

    # solver difficulty, 3 samples per model
    solver = {}
    for method in METHODS:
        sub = [r for r in rows.values() if r["method"] == method]
        for index, name in ((0, "luna"), (1, "gemini")):
            rates = []
            for r in sub:
                flags = [x for x in r["solver"][index] if x is not None]
                if flags:
                    rates.append(sum(flags) / len(flags))
            solver.setdefault(METHODS[method], {})[name] = statistics.fmean(rates) if rates else None
            solver[METHODS[method]][f"{name}_n"] = len(rates)

    # disagreements, with concrete examples
    disagreements = defaultdict(list)
    for anon, r in rows.items():
        if r["verdicts"][0] != r["verdicts"][1]:
            key_name = f"{METHODS[r['method']]}:{r['verdicts'][0]} vs {r['verdicts'][1]}"
            disagreements[key_name].append(anon)

    out = {
        "meta": {"common_items": len(common), "luna_items": len(luna), "gemini_items": len(gemini),
                 "judge_k": "3 solver samples; one verdict per model",
                 "note": "Each model gives one verdict after seeing all 3 solver attempts."},
        "agreement": {"n": len(pairs), "exact": agree, "kappa_all": kappa_all,
                      "kappa_binary": kappa_binary, "confusion": {f"{a}->{b}": c for (a, b), c in confusion.items()}},
        "by_method": by_method,
        "depth": depth, "depth_gap": depth_gap,
        "solver": solver,
        "disagreements": {k: len(v) for k, v in sorted(disagreements.items(), key=lambda kv: -len(kv[1]))},
        "disagreement_examples": {k: v[:5] for k, v in sorted(disagreements.items(), key=lambda kv: -len(kv[1]))},
    }
    (K3 / "agreement.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Cross-family judge agreement", "",
             f"Common items: {len(common)}; exact verdict agreement: {agree:.3f}; "
             f"Cohen's kappa (3 classes): {kappa_all:.3f}; binary valid/not: {kappa_binary:.3f}.",
             f"k=3 = three solver samples; each model gives one verdict after seeing all three.", "",
             "## Confusion", "",
             table(["luna \\ gemini", "valid", "invalid", "uncertain", "unavailable"],
                   [[a] + [str(confusion.get((a, b), 0)) for b in classes] for a in classes],
                   "lrrrr"), "",
             "## Validity under each judge and the strict/liberal bounds", "",
             table(["method", "k=1 luna", "k=3 luna", "gemini", "both valid (strict)", "either valid (liberal)"],
                   [[m, f"{v['k1']:.3f}", f"{v['luna']:.3f}", f"{v['gemini']:.3f}",
                     f"{v['strict']:.3f}", f"{v['liberal']:.3f}"] for m, v in by_method.items()],
                   "lrrrrr"), "",
             "## Invalid rate is judge-dependent", "",
             table(["method", "luna invalid", "gemini invalid", "both", "luna only", "gemini only"],
                   [[m, f"{v['luna_invalid']:.3f}", f"{v['gemini_invalid']:.3f}",
                     f"{v['both_invalid']:.3f}", f"{v['luna_only_invalid']:.3f}",
                     f"{v['gemini_only_invalid']:.3f}"] for m, v in by_method.items()],
                   "lrrrrr"), "",
             "## Depth on items both judges call valid", "",
             table(["method", "n", "luna depth", "gemini depth"],
                   [[m, str(v["n"]), f"{v['luna']:.2f}" if v["luna"] is not None else "-",
                     f"{v['gemini']:.2f}" if v["gemini"] is not None else "-"] for m, v in depth.items()],
                   "lrrr"), "",
             f"PF - B2 depth gap: luna {depth_gap['luna']:+.3f}; gemini {depth_gap['gemini']:+.3f}." if
             depth_gap["luna"] is not None and depth_gap["gemini"] is not None else "",
             "", "## Solver difficulty (mean over 3 samples)", "",
             table(["method", "luna", "gemini"],
                   [[m, f"{v['luna']:.3f}" if v["luna"] is not None else "-",
                     f"{v['gemini']:.3f}" if v["gemini"] is not None else "-"] for m, v in solver.items()],
                   "lrr"), "",
             "## Disagreements", "",
             table(["pattern", "n"], [[k, str(v)] for k, v in out["disagreements"].items()], "lr"), ""]

    (K3 / "agreement.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(K3 / "agreement.md")
    print(json.dumps(out["agreement"], ensure_ascii=False, indent=2))
    print(json.dumps(by_method, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
