"""Blind audit preparation and descriptive, seed-paired quality reporting.

Uses only the standard library. Statistical intervals describe this fixed corpus;
they do not establish a causal framework effect for the historical PF test set.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

METHODS = ("puzzleforge", "direct", "framework")
AUDIT_FIELDS = ("anon_id", "reviewer", "valid", "depth", "explainability", "error_type", "evidence")


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def prepare_audit(records: list[dict[str, Any]], out_dir: Path, seed: int = 20261028,
                  per_seed: int = 2, min_count: int = 0) -> None:
    """Deterministically sample matched slots, including failures; preserve labels.

    Run records must contain every requested slot, including generation failures.
    No label file is overwritten on resume. Changing the sample creates a fresh
    output directory; a stale label file with a different sample is rejected.
    """
    if per_seed < 1 or min_count < 0:
        raise ValueError("per_seed must be positive and min_count nonnegative")
    ids = [str(row["id"]) for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate record IDs")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row["method"] not in METHODS:
            raise ValueError(f"Unknown method: {row['method']}")
        if row["cohort"] == "matched":
            grouped[(str(row["seed_id"]), row["method"])].append(row)
    chosen = []
    for key, rows in sorted(grouped.items()):
        salt = f"{seed}|{key[0]}|{key[1]}"
        ordered = sorted(rows, key=lambda row: hashlib.sha256(f"{salt}|{row['id']}".encode()).hexdigest())
        chosen.extend(ordered[:per_seed])
    if len(chosen) < min_count:
        raise ValueError(f"Blind sample has {len(chosen)} items, below required {min_count}; raise per_seed")
    random.Random(seed).shuffle(chosen)
    blind, private, native = [], [], []
    for row in chosen:
        anon = hashlib.sha256(f"audit-v1|{seed}|{row['id']}".encode()).hexdigest()[:20]
        blind.append({"anon_id": anon, "problem": row.get("problem", ""), "answer": row.get("answer")})
        native.append({"anon_id": anon, "explanation": row.get("explanation")})
        private.append({"anon_id": anon, "id": row["id"], "method": row["method"],
                        "seed_id": row["seed_id"], "slot": row["slot"]})
    out_dir.mkdir(parents=True, exist_ok=True)
    key_path, labels_path = out_dir / "audit_key.jsonl", out_dir / "audit_labels.csv"
    if labels_path.exists() and (not key_path.exists() or _jsonl(key_path) != private):
        raise ValueError("Existing labels belong to another audit sample; use a new output directory")
    _write_jsonl(out_dir / "audit_blind.jsonl", blind)
    _write_jsonl(key_path, private)
    _write_jsonl(out_dir / "audit_native_explanations.private.jsonl", native)
    if not labels_path.exists():
        with labels_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
            writer.writeheader()
            for row in blind:
                for reviewer in ("reviewer_1", "reviewer_2", "adjudicator"):
                    writer.writerow({"anon_id": row["anon_id"], "reviewer": reviewer})
    (out_dir / "AUDIT_INSTRUCTIONS.md").write_text(
        "# 盲审说明\n\n只向审核者提供 audit_blind.jsonl 及空白标注表；audit_key.jsonl 保持私有。\n"
        "原生解释另存 audit_native_explanations.private.jsonl，正确性／深度盲审时不提供，避免解释缺失泄露来源。\n"
        "两位审核者应独立作答，提交前不互看标签；reviewer_1/reviewer_2 替换为稳定的匿名人员ID。\n"
        "valid: 1=题意完整一致、可解且参考答案正确，0=不满足；无输出记0。必须填写 evidence。\n"
        "多答案任务以题目声明的答案类型为准，不能一律要求单一解。\n"
        "depth: 有效题的最短充分推理依赖链必要步骤数（非解释长度）；不能确定留空。\n"
        "explainability: 第一轮正确性／深度盲审留空；另行原生解释审核时，有效且提供了解释才评分，0=错误，1=关键步骤缺失，2=部分可核查，"
        "3=主要步骤可核查，4=完整且正确；无解释留空，另计解释提供率。\n"
        "error_type: missing_constraint/ambiguous/unsatisfiable/wrong_answer/rendering/other。\n"
        "两位valid不同由第三人用reviewer=adjudicator填valid及证据；未裁决不进入主终点。\n"
        "深度、解释评分为两位有效评分的均值，只报告可评估子集及覆盖率。\n"
        "禁止根据方法或预期结论挑选审核对象。实际独立性无法由CSV自动证明，需保留审核流程记录。\n",
        encoding="utf-8")


def _audited(labels: list[dict[str, Any]], key: list[dict[str, Any]],
             records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    known = {str(row["id"]): row for row in records}
    links = {str(row["anon_id"]): str(row["id"]) for row in key}
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in labels:
        if str(row.get("valid", "")).strip() == "":
            continue
        anon, reviewer = str(row["anon_id"]), str(row["reviewer"]).strip()
        if anon not in links or links[anon] not in known:
            raise ValueError(f"Label has no matching record: {anon}")
        if not reviewer or reviewer in grouped[anon]:
            raise ValueError(f"Empty or repeated reviewer for {anon}")
        if str(row["valid"]).strip() not in ("0", "1") or not str(row.get("evidence", "")).strip():
            raise ValueError(f"valid must be 0/1 and evidence is required: {anon}")
        grouped[anon][reviewer] = row
    resolved = {}
    for anon, reviews in grouped.items():
        independent = [row for reviewer, row in reviews.items() if reviewer != "adjudicator"]
        if len(independent) != 2:
            continue
        votes = [int(row["valid"]) for row in independent]
        if votes[0] != votes[1]:
            if "adjudicator" not in reviews:
                continue
            valid = int(reviews["adjudicator"]["valid"])
        else:
            valid = votes[0]
        record = known[links[anon]]
        if valid and (record["status"] != "ok" or not str(record.get("problem", "")).strip()):
            raise ValueError(f"A failed or empty generation cannot be labeled valid: {anon}")
        result: dict[str, Any] = {"valid": valid, "evidence": [row["evidence"] for row in reviews.values()]}
        for field in ("depth", "explainability"):
            values = [float(row[field]) for row in independent if str(row.get(field, "")).strip()]
            if any(not math.isfinite(value) or value < 0 or (field == "explainability" and value > 4) for value in values):
                raise ValueError(f"Out of range {field} in {anon}")
            # A disputed validity decision cannot supply two valid quality scores.
            score = statistics.mean(values) if valid and votes == [1, 1] and len(values) == 2 else None
            if field == "explainability" and not record.get("explanation"):
                score = None
            result[field] = score
        resolved[links[anon]] = result
    return resolved


def _paired_interval(differences: list[float], seed: int, draws: int = 2000) -> tuple[float, float, float]:
    rng, n = random.Random(seed), len(differences)
    samples = sorted(statistics.mean(rng.choices(differences, k=n)) for _ in range(draws))
    return statistics.mean(differences), samples[int(.025 * draws)], samples[int(.975 * draws) - 1]


def summarize(records: list[dict[str, Any]], labels: list[dict[str, Any]] | None = None,
              audit_key: list[dict[str, Any]] | None = None, seed: int = 20261028) -> str:
    """Return a Markdown report. No labels means no independent quality claim."""
    lines = ["# 数据质量对比报告", "", "本报告区分已生成产量与独立审核质量。历史 PuzzleForge 测试集与新生成基线不构成同模型、同预算的因果实验。", "",
             "| 方法 | 集合 | 请求槽位 | 有输出 | 生成失败 | 规范化唯一题 | 精确重复 |", "|---|---|---:|---:|---:|---:|---:|"]
    for method in METHODS:
        for cohort in ("matched", "extra"):
            rows = [r for r in records if r["method"] == method and r["cohort"] == cohort]
            ok = [r for r in rows if r["status"] == "ok" and str(r.get("problem", "")).strip()]
            unique = len({_normalized(r["problem"]) for r in ok})
            lines.append(f"| {method} | {cohort} | {len(rows)} | {len(ok)} | {len(rows)-len(ok)} | {unique} | {len(ok)-unique} |")
    lines.extend(["", "规范化仅执行 Unicode NFKC、大小写统一与空白合并；此重复率不是语义或结构多样性的替代。失败槽位保留，不能为达到配额而删除。"])
    resolved = _audited(labels or [], audit_key or [], records)
    lines.extend(["", "## 独立审核", "", f"已完成双人一致／分歧经第三人裁决的记录：{len(resolved)}。"])
    if not resolved:
        lines.extend(["", "尚无可用于主终点的独立审核标签；不能得出正确性、深度、难度或可解释性优劣结论。", "",
                      "下一步：独立双盲审阅 audit_blind.jsonl，填写 audit_labels.csv 后重新生成报告。"])
        return "\n".join(lines) + "\n"
    by_id = {str(row["id"]): row for row in records}
    matched = {rid: score for rid, score in resolved.items() if by_id[rid]["cohort"] == "matched"}
    lines.extend(["", "| 方法 | 已裁决matched题数 | 有效率 | 深度均值（n） | 解释评分均值（n） |", "|---|---:|---:|---:|---:|"])
    for method in METHODS:
        scores = [score for rid, score in matched.items() if by_id[rid]["method"] == method]
        def average(field: str) -> str:
            values = [score[field] for score in scores if score.get(field) is not None]
            return f"{statistics.mean(values):.3f} ({len(values)})" if values else "NA (0)"
        lines.append(f"| {method} | {len(scores)} | {average('valid')} | {average('depth')} | {average('explainability')} |")
    lines.extend(["", "配对比较仅使用双方都达到预定双审核样本数的相同seed；默认每seed每方法2题。"
                  "95%区间按seed成簇、配对bootstrap 2000次，不能将同生成器题目当作独立重复实验。"
                  "这里只提供区间，不提供多重检验校正后的显著性结论。", "",
                  "| PF减去基线 | 指标 | 配对seed数 | 宏平均差 | 95%区间 |", "|---|---|---:|---:|---|"])
    for baseline in ("direct", "framework"):
        for field in ("valid", "depth", "explainability"):
            buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
            for rid, score in matched.items():
                row = by_id[rid]
                if score.get(field) is not None:
                    buckets[(row["seed_id"], row["method"])].append(score[field])
            seeds = sorted({row["seed_id"] for row in records if row["cohort"] == "matched"})
            diffs = [statistics.mean(buckets[(s, "puzzleforge")]) - statistics.mean(buckets[(s, baseline)])
                     for s in seeds if len(buckets[(s, "puzzleforge")]) >= 2 and len(buckets[(s, baseline)]) >= 2]
            if len(diffs) >= 2:
                point, low, high = _paired_interval(diffs, seed)
                lines.append(f"| PF − {baseline} | {field} | {len(diffs)}/{len(seeds)} | {point:.3f} | [{low:.3f}, {high:.3f}] |")
            else:
                lines.append(f"| PF − {baseline} | {field} | {len(diffs)}/{len(seeds)} | NA | 样本不足 |")
    lines.extend(["", "## 结论边界与案例候选", "", "覆盖不全的审核结果仅是被审核seed子集的描述，不能外推完整数据。"
                  "深度与解释只在有效且可评估子集报告；缺失解释是NA，不能算0分或自动判差。"
                  "难度还需要独立解题面板，语义／结构多样性需要冻结的标签或嵌入评测，本脚本不凭精确去重代替这些证据。", "",
                  "以下按已审核seed的有效率差自动选取候选，需人工核实原题、证据和因果解释；"
                  "正差、相同、负差均展示，不允许只挑框架胜出的例子。"])
    for baseline in ("direct", "framework"):
        cases: dict[str, list[tuple[str, list[str]]]] = {"PF较好": [], "相同": [], "基线较好": []}
        seed_ids = sorted({by_id[rid]["seed_id"] for rid in matched})
        for seed_id in seed_ids:
            left = [rid for rid in matched if by_id[rid]["seed_id"] == seed_id and by_id[rid]["method"] == "puzzleforge"]
            right = [rid for rid in matched if by_id[rid]["seed_id"] == seed_id and by_id[rid]["method"] == baseline]
            if len(left) < 2 or len(right) < 2:
                continue
            diff = statistics.mean(matched[r]["valid"] for r in left) - statistics.mean(matched[r]["valid"] for r in right)
            category = "PF较好" if diff > 0 else "基线较好" if diff < 0 else "相同"
            cases[category].append((seed_id, left + right))
        for category, candidates in cases.items():
            if candidates:
                seed_id, ids = candidates[0]
                lines.append(f"\n- {baseline}／{category}：seed `{seed_id}`，原始记录ID：" + ", ".join(f"`{rid}`" for rid in ids))
                for rid in ids:
                    lines.append(f"  - `{rid}` 审核证据：" + "；".join(str(e) for e in matched[rid]["evidence"]))
            else:
                lines.append(f"\n- {baseline}／{category}：已审核样本中暂无候选，不能编造案例。")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--per-seed", type=int, default=2, help="Blind items per seed per method")
    parser.add_argument("--min-audit", type=int, default=0, help="Fail before writing if the sample is smaller")
    args = parser.parse_args()
    records = _jsonl(args.data)
    prepare_audit(records, args.out, seed=args.seed, per_seed=args.per_seed, min_count=args.min_audit)
    labels = []
    if args.labels:
        with args.labels.open(encoding="utf-8", newline="") as handle:
            labels = list(csv.DictReader(handle))
    report = summarize(records, labels, _jsonl(args.out / "audit_key.jsonl"), args.seed)
    source = args.data.resolve()
    for line_number, row in enumerate(records, start=1):
        record_id = str(row["id"])
        report = report.replace(f"`{record_id}`", f"[{record_id}](<{source}:{line_number}>)")
    (args.out / "report.md").write_text(report, encoding="utf-8")
    print(args.out / "report.md")


if __name__ == "__main__":
    main()
