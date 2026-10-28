"""Offline final-report consistency checks; run after build_report.py.

Checks arithmetic, coverage and required interpretation boundaries. Does not
certify model judgments or replace reading concrete independent case evidence.
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def check(metrics_path, report_path, examples_path):
    metrics = json.loads(metrics_path.read_text())
    report, examples = report_path.read_text(), examples_path.read_text()
    groups = metrics["groups"]
    assert set(groups) == {"puzzleforge", "direct", "framework"}
    assert sum(r["matched_slots"] for r in groups.values()) == 492
    assert sum(groups[m]["raw_planned_slots"] for m in ("direct", "framework")) == 560
    for method, row in groups.items():
        total = sum(row[name] for name in ("model_valid", "model_invalid", "model_uncertain", "execution_unknown", "unavailable"))
        assert total == row["audit_slots"] == 28, (method, "evaluation denominator changed")
        assert row["matched_actual_questions"] + row["matched_generation_failed"] == 164
        assert abs(row["validity_proxy_lower"] - row["model_valid"]/28) < 1e-12
        upper = (row["model_valid"] + row["model_uncertain"] + row["execution_unknown"])/28
        assert abs(row["validity_proxy_upper"] - upper) < 1e-12
        existing_n = 28 - row["unavailable"]
        conditional = row["conditional_validity_proxy"]
        assert conditional["audited_existing_questions"] == existing_n
        if existing_n:
            assert abs(conditional["lower"] - row["model_valid"]/existing_n) < 1e-12
            assert abs(conditional["upper"] - (row["model_valid"] + row["model_uncertain"] + row["execution_unknown"])/existing_n) < 1e-12
        else:
            assert conditional["lower"] is None and conditional["upper"] is None
        assert row["depth_score"]["n"] <= row["model_valid"]
        assert row["explanation_score"]["n"] <= row["model_valid"]
        assert row["solve_success_k1"]["n"] <= row["model_valid"]
        assert row["cjk_ge20"] <= row["matched_actual_questions"]
    required = ("不能证明历史PF在所有质量维度都优于", "模型标签不能当作人工真值", "历史PF缺少原生解释",
                "外部证书", "单条reference常含多个小问", "字符长度仅描述", "单模型k=1", "先验过滤混杂",
                "禁止直接用v1旧pilot与本轮分数之差声称v2 prompt带来提升", "不编造美元")
    for phrase in required:
        assert phrase in report, f"Missing interpretation boundary: {phrase}"
    for phrase in ("有效题/计划槽代理（含生成失败", "已有题条件有效性代理", "不能证明已经生成的题质量低"):
        assert phrase in report, f"Missing delivery-versus-conditional distinction: {phrase}"
    for phrase in ("所有维度均胜出", "已证明结构深度优势", "原生解释质量全面优于", "v2 prompt显著提升"):
        assert phrase not in report, f"Unsupported conclusion: {phrase}"
    assert "原生解释" in examples and "未提供" in examples
    assert "不按评测分数挑题" in examples
    for comparison in metrics["quality_seed_comparisons"]:
        assert comparison["seed_coverage"] <= comparison["seed_total"] == 14
        if comparison["seed_coverage"] < 2:
            assert comparison["bootstrap_95"] == [None, None]
    print("Final report arithmetic, coverage and interpretation checks passed. Independent case evidence still requires review.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", type=Path, default=HERE / "final_metrics.json")
    parser.add_argument("--report", type=Path, default=ROOT / "output/minimax_flash_v2_500_report.md")
    parser.add_argument("--examples", type=Path, default=ROOT / "output/minimax_flash_v2_500_examples.md")
    args = parser.parse_args()
    check(args.metrics, args.report, args.examples)
