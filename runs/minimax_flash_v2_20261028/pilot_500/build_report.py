"""Offline, reproducible report for the v2 held-out 492-slot pilot.

Requires completed generation exports and all 84 evaluation outcomes. This file
never reads credentials, calls an API, edits source data, or invents a winner.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from experiment.autojudge import _paired_proxy, consensus
from experiment.evaluation import _paired_interval
from experiment.metrics import lexical_metrics

METHODS = ("puzzleforge", "direct", "framework")
LABELS = {"puzzleforge": "历史PF参考", "direct": "API直接造题 v2", "framework": "API编写生成器 v2"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def mean(values):
    return statistics.mean(values) if values else None


def entropy(values):
    return -sum((n/len(values))*math.log2(n/len(values)) for n in Counter(values).values()) if values else None


def number(value, digits=3):
    return f"{value:.{digits}f}" if value is not None else "NA"


def link(path, label=None, line=None):
    target = str(path.resolve()) + (f":{line}" if line else "")
    return f"[{label or path.name}](<{target}>)"


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def measured_usage(log):
    events = jsonl(log) if log.exists() else []
    groups = {}
    for event in events:
        tag = event.get("tag", "")
        method = tag.split("/", 1)[0] if tag.startswith(("direct/", "framework/")) else "evaluation"
        group = groups.setdefault(method, {"http_attempts": 0, "successful_responses": 0, "cache_hits": 0,
                                          "failure_attempts": 0, "failure_kinds": {}, "usage_responses": 0,
                                          "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                                          "usage_field_coverage": {name: 0 for name in ("prompt_tokens", "completion_tokens", "total_tokens")}})
        if event["event"] == "request_start":
            group["http_attempts"] += 1
        elif event["event"] == "cache_hit":
            group["cache_hits"] += 1
        elif event["event"] == "request_failure":
            group["failure_attempts"] += 1
            kind = event.get("kind", "unknown")
            group["failure_kinds"][kind] = group["failure_kinds"].get(kind, 0) + 1
        elif event["event"] == "request_success":
            group["successful_responses"] += 1
            usage = event.get("usage")
            if isinstance(usage, dict):
                group["usage_responses"] += 1
                for field in group["usage_field_coverage"]:
                    if type(usage.get(field)) is int:
                        group[field] += usage[field]
                        group["usage_field_coverage"][field] += 1
    return groups


def item_score(row, field):
    if consensus(row) != "valid" or row.get("label_origin") == "execution_policy":
        return None
    values = [judge[field] for judge in row["judges"] if judge.get(field) is not None]
    return mean(values)


def paired_quality(labels, key, field, selected):
    links = {row["anon_id"]: row for row in key}
    grouped = defaultdict(list)
    for row in labels:
        score = item_score(row, field)
        if score is not None:
            item = links[row["anon_id"]]
            grouped[(item["seed_id"], item["method"])].append(score)
    output = []
    for baseline in ("direct", "framework"):
        common = [seed for seed in selected if grouped[(seed, "puzzleforge")] and grouped[(seed, baseline)]]
        differences = [statistics.mean(grouped[(seed, "puzzleforge")]) - statistics.mean(grouped[(seed, baseline)]) for seed in common]
        estimate = _paired_interval(differences, 20261028) if len(differences) >= 2 else (mean(differences), None, None)
        output.append({"baseline": baseline, "metric": field, "seed_coverage": len(common), "seed_total": len(selected),
                       "paired_seed_mean_difference": estimate[0], "bootstrap_95": [estimate[1], estimate[2]],
                       "per_seed_item_counts": {seed: {"puzzleforge": len(grouped[(seed, "puzzleforge")]),
                                                       baseline: len(grouped[(seed, baseline)])} for seed in common}})
    return output


def main(validation_paths):
    selection = read(HERE / "selection.json")
    selected = selection["selected_seed_ids"]
    records = jsonl(HERE / "records_492.jsonl")
    raw_records = jsonl(HERE / "records_raw_selected.jsonl")
    labels, key = jsonl(HERE / "auto/model_labels.jsonl"), jsonl(HERE / "audit/audit_key.jsonl")
    if len(selected) != 14 or len(records) != 492 or len(labels) != 84 or len(key) != 84:
        raise ValueError("Need all 492 matched slots and 84 fixed evaluation outcomes; do not report an incomplete run")
    if len({r["anon_id"] for r in labels}) != 84:
        raise ValueError("Duplicate anonymous evaluation IDs")
    links = {row["anon_id"]: row for row in key}
    lexical = lexical_metrics(records)
    question_exports = []
    for method in METHODS:
        path = HERE / f"{method}.questions.jsonl"
        values = [row for row in records if row["method"] == method and row["status"] == "ok"]
        path.write_text("".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in values), encoding="utf-8")
        question_exports.append({"path": str(path.relative_to(ROOT)), "method": method, "scope": "matched successful questions only",
                                 "count": len(values), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    for method in ("direct", "framework"):
        path = HERE / f"{method}.raw.questions.jsonl"
        values = [row for row in raw_records if row["method"] == method and row["status"] == "ok"]
        path.write_text("".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in values), encoding="utf-8")
        question_exports.append({"path": str(path.relative_to(ROOT)), "method": method, "scope": "all selected 14 seeds, successful raw questions only",
                                 "count": len(values), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    groups = {}
    for method in METHODS:
        matched = [r for r in records if r["method"] == method]
        raw = [r for r in raw_records if r["method"] == method]
        actual = [r for r in matched if r["status"] == "ok"]
        sample = [r for r in labels if links[r["anon_id"]]["method"] == method]
        if len(matched) != 164 or len(sample) != 28 or (method != "puzzleforge" and len(raw) != 280):
            raise ValueError(f"Unexpected fixed group size: {method}")
        verdicts = Counter(consensus(r) for r in sample)
        existing_audit_n = len(sample) - verdicts["unavailable"]
        valid = [r for r in sample if consensus(r) == "valid"]
        scores = {field: [score for r in sample if (score := item_score(r, field)) is not None]
                  for field in ("depth_score", "explanation_score")}
        correct = []
        for row in valid:
            if len(row["attempts"]) != 1:
                raise ValueError("This pilot report supports only k=1")
            flags = [judge["solver_correct"][0] for judge in row["judges"]]
            if flags and None not in flags and len(set(flags)) == 1:
                correct.append(int(flags[0]))
        tags, tag_entropy = {}, {}
        for field in ("reasoning_type_tags", "constraint_type_tags", "scenario"):
            values = [tag for r in valid for j in r["judges"] for tag in (j[field] if isinstance(j[field], list) else [j[field]])]
            tags[field], tag_entropy[field] = dict(sorted(Counter(values).items())), entropy(values)
        structures = {tuple(sorted(j["reasoning_type_tags"])) + ("|",) + tuple(sorted(j["constraint_type_tags"]))
                      for r in valid for j in r["judges"]}
        lexical_rows = [r for r in lexical if r["method"] == method]
        groups[method] = {
            "raw_planned_slots": 280 if method != "puzzleforge" else None, "raw_persisted_slots": len(raw),
            "raw_actual_questions": sum(r["status"] == "ok" for r in raw), "matched_slots": len(matched),
            "matched_actual_questions": len(actual), "matched_generation_failed": len(matched)-len(actual),
            "native_explanation_provided": sum(bool(str(r.get("explanation") or "").strip()) for r in actual),
            "problem_character_length": {"mean": mean([len(r["problem"]) for r in actual]),
                                         "median": statistics.median([len(r["problem"]) for r in actual]) if actual else None},
            "cjk_ge20": sum(len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", r["problem"])) >= 20 for r in actual),
            "audit_slots": len(sample), "verdicts": dict(verdicts),
            "model_valid": verdicts["valid"], "model_invalid": verdicts["invalid"],
            "model_uncertain": sum(consensus(r) == "uncertain" and r.get("label_origin") != "execution_policy" for r in sample),
            "execution_unknown": sum(r.get("assessment_status") == "execution_unknown" for r in sample),
            "execution_unknown_breakdown": dict(Counter(
                f"{r['execution_error']['kind']}:{r['execution_error']['phase']}" for r in sample
                if r.get("assessment_status") == "execution_unknown")),
            "unavailable": verdicts["unavailable"], "validity_proxy_lower": verdicts["valid"]/28,
            "validity_proxy_upper": (verdicts["valid"]+verdicts["uncertain"])/28,
            "validity_proxy_definition": "effective valid questions per planned audited slot; includes generation failures as zero, not correctness conditional on produced questions",
            "effective_delivery_proxy": {"lower": verdicts["valid"]/28, "upper": (verdicts["valid"]+verdicts["uncertain"])/28,
                                         "planned_audit_slots": len(sample)},
            "conditional_validity_proxy": {"lower": verdicts["valid"]/existing_audit_n if existing_audit_n else None,
                                           "upper": (verdicts["valid"]+verdicts["uncertain"])/existing_audit_n if existing_audit_n else None,
                                           "audited_existing_questions": existing_audit_n},
            **{field: {"mean": mean(values), "n": len(values)} for field, values in scores.items()},
            "solve_success_k1": {"mean": mean(correct), "n": len(correct)}, "tag_distributions": tags,
            "tag_entropy_bits": tag_entropy, "distinct_structure_tag_combinations": len(structures),
            "normalized_exact_duplicate_items": len(actual)-len({normalized(r["problem"]) for r in actual}),
            "lexical_near_duplicate_items": sum(r["near_duplicate_items"] for r in lexical_rows),
            "lexical_near_duplicate_denominator": sum(r["n"] for r in lexical_rows)}
    validity = _paired_proxy(labels, key)
    quality = paired_quality(labels, key, "depth_score", selected) + paired_quality(labels, key, "explanation_score", selected)
    costs = {"generation": measured_usage(RUN / "api_cache/requests.jsonl"), "evaluation": measured_usage(HERE / "auto/api_cache/requests.jsonl")}
    if sum(r["http_attempts"] for r in costs["evaluation"].values()) > 400:
        raise ValueError("Evaluation exceeded frozen 400 HTTP-attempt limit")
    for path in validation_paths:
        if not path.is_file():
            raise ValueError(f"Missing independent validation file: {path}")
    recovery_manifest_path = HERE / "generation_recovery_manifest.json"
    recovery_status_path = HERE / "generation_recovery_status.json"
    recovery = None
    if recovery_manifest_path.exists():
        if not recovery_status_path.exists():
            raise ValueError("Generation recovery status is missing; cannot conceal an unfinished protocol amendment")
        recovery_manifest, recovery_status = read(recovery_manifest_path), read(recovery_status_path)
        original_config = read(RUN / "manifest.json")["config"]
        recovery = {"manifest": recovery_manifest, "status": recovery_status,
                    "original_http_timeout_seconds": original_config["timeout"],
                    "original_http_retries": original_config["http_retries"],
                    "manifest_path": str(recovery_manifest_path.relative_to(ROOT)),
                    "status_path": str(recovery_status_path.relative_to(ROOT))}
        if any(recovery_status["missing_result_seed_ids"].values()):
            raise ValueError("Recovery still reports missing generation results")
    unknown_causes = dict(Counter(row["execution_error"]["kind"] for row in labels
                                  if row.get("assessment_status") == "execution_unknown"))
    result = {"groups": groups, "validity_seed_comparisons": validity, "quality_seed_comparisons": quality,
              "execution_unknown_causes_total": unknown_causes,
              "validity_seed_comparisons_estimand": "effective valid questions per planned audited slot, including generation failures as zero; not conditional correctness",
              "api_measurements": costs, "lexical_per_seed": lexical,
              "question_exports": question_exports, "generation_protocol_amendment": recovery,
              "independent_validation_files": [str(p.resolve()) for p in validation_paths]}
    (HERE / "final_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    line_numbers = {row["id"]: i+1 for i,row in enumerate(records)}
    def record_link(record):
        return link(HERE / "records_492.jsonl", record["id"], line_numbers[record["id"]])
    actual_total = sum(r["matched_actual_questions"] for r in groups.values())
    raw_actual = sum(groups[m]["raw_actual_questions"] for m in ("direct", "framework"))
    pf, direct, framework = [groups[m] for m in METHODS]
    text = ["# v2 新种子试跑：约500道题的质量比较", "",
            "本报告将实际产量、固定盲评与独立核验分开呈现，保留未决、无输出、区间和不利结果；模型标签不能当作人工真值。", "",
            "**这轮观察：** "
            f"主比较492个计划槽实际得到{actual_total}道题；两个baseline的560个原始计划槽实际得到{raw_actual}道。"
            f"固定抽评每种方法28槽，模型valid分别为PF {pf['model_valid']}、直接造题 {direct['model_valid']}、生成框架 {framework['model_valid']}；"
            f"执行未决分别为{pf['execution_unknown']}、{direct['execution_unknown']}、{framework['execution_unknown']}，"
            f"无输出分别为{pf['unavailable']}、{direct['unavailable']}、{framework['unavailable']}。"
            "这些是本次实测代理数值，总体解释须结合84槽评测与独立核验，不预设任何方法获胜。", "",
            f"本轮固定14个未用于旧pilot的seed；主比较492个配对槽（每方法164），实际有题{actual_total}道。"
            f"两条新baseline另保留各280个原始计划槽，共560个新题计划槽，实际得到{raw_actual}道；原始产量与主比较样本不能混算。"
            "历史参考总集有1720道，本轮只取这14个seed对应的164道作配对比较，其余参考题不进入主表。", "",
            "生成请求采用中文v2提示词和output_language=zh，保留L1–L4、未向模型发送论文专名；"
            "生成骨干为MiniMax-M3.1-Flash。固定盲评84槽，单模型k=1、medium、16384 tokens、8 workers、累计HTTP上限400。"
            "截断或三次schema耗尽仅标执行未决；不为该题重复抽解直到成功。", "",
            f"实际模型判定共{sum(row['model_valid']+row['model_invalid']+row['model_uncertain'] for row in groups.values())}槽，"
            f"模型uncertain共{sum(row['model_uncertain'] for row in groups.values())}槽。"
            f"另有{sum(row['execution_unknown'] for row in groups.values())}槽执行unknown："
            f"{unknown_causes.get('schema_exhausted',0)}槽三次schema修复仍耗尽、"
            f"{unknown_causes.get('truncated_response',0)}槽真实token截断；PF占{pf['execution_unknown']}槽、"
            f"生成器占{framework['execution_unknown']}槽。它们不是模型uncertain或模型判错，不能合并误报；"
            f"另有{sum(row['unavailable'] for row in groups.values())}槽为真实无输出。", "",
            "| 方法 | raw计划/实际题 | matched实际题/槽 | 模型valid | 模型invalid | 模型uncertain | 执行unknown | 无输出 | 有效题/计划槽代理（含生成失败，N=28） |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for method, row in groups.items():
        raw_count = f"{row['raw_planned_slots']}/{row['raw_actual_questions']}" if row["raw_planned_slots"] else "历史参考"
        text.append(f"| {LABELS[method]} | {raw_count} | {row['matched_actual_questions']}/164 | {row['model_valid']} | {row['model_invalid']} | "
                    f"{row['model_uncertain']} | {row['execution_unknown']} | {row['unavailable']} | {row['validity_proxy_lower']:.1%}—{row['validity_proxy_upper']:.1%} |")
    text += ["", "真实题文件：失败槽仍完整保留在records_492.jsonl和records_raw_selected.jsonl，以下JSONL仅平铺status=ok的真实题，未修题或改答案。", ""]
    for exported in question_exports:
        text.append(f"- {link(ROOT / exported['path'])}：{exported['count']}道；{exported['scope']}。")
    if recovery is not None:
        revision = recovery["manifest"]
        status = recovery["status"]
        text += ["", "**运行中的生成协议修订（不是原预注册不变运行）：** "
                 f"原HTTP超时{recovery['original_http_timeout_seconds']}秒、自动重试{recovery['original_http_retries']}次，"
                 f"调整为{revision['recovery_http_timeout_seconds']}秒、零自动HTTP重试。"
                 "真实finish_reason=length且无最终代码的已保存响应，仅按原请求identity原样回放给原流程，"
                 "原持久化响应不改，缺失final仅在解析时投影为空字符串；"
                 "不重新抽attempt-0、不把reasoning_content当最终代码；随后仍只占用原有剩余生成尝试。"
                 f"模型仍为{revision['model']}，reasoning_effort={revision['parameters']['reasoning_effort']}、"
                 f"max_completion_tokens={revision['parameters']['max_completion_tokens']}；每任务仍最多{revision['generation_attempts_per_task']}次生成尝试，"
                 f"累计HTTP上限仍为{revision['max_http_attempts']}。已有三次耗尽的failed结果不重开。", "",
                 f"恢复状态记录HTTP累计{status['http_attempts_total']}次，真实length回放事件{len(status['replayed_length_tags'])}条，"
                 f"transport失败事件{len(status['transport_failures'])}条；耗尽结果文件：{status['three_generation_attempts_exhausted_results']}。"
                 "网络/超时/中断属于基础设施事件，不能伪装成坏题；只有持久化的generation_failed槽计为方法未产出。"
                 "未取得可用响应的超时/中断请求可能由恢复流程以更长超时重发相同请求，先前已发尝试仍计入预算，服务端完成情况和账单可能未知。", "",
                 f"完整政策与状态：{link(recovery_manifest_path)}、{link(recovery_status_path)}。"]
    text += ["", "上表为有效题交付到计划槽的代理：未决分别计0/1，无输出两端均计0，包含生成失败。"
             "它不是已有题的条件正确率，也不是人审有效率置信界。没有输出只能说明没有交付题目，不能证明已经生成的题质量低。", "",
             "| 方法 | 已有实际题抽评n（28减无输出） | 已有题条件有效性代理下—上 |", "|---|---:|---:|"]
    for method, row in groups.items():
        conditional = row["conditional_validity_proxy"]
        bounds = (f"{conditional['lower']:.1%}—{conditional['upper']:.1%}" if conditional["lower"] is not None else "NA（无已有题）")
        text.append(f"| {LABELS[method]} | {conditional['audited_existing_questions']} | {bounds} |")
    text += ["", "条件代理以valid/(28−unavailable)及(valid+uncertain)/(28−unavailable)计算；"
             "execution_unknown仍按0/1作敏感性处理。该条件指标与含失败的交付代理回答不同问题，不能混用。", "",
             "| 方法 | 深度代理0–4(n) | 统一外部证书可核查度0–4(n) | k1解题成功率(n) | 原生解释提供数/实际题 |",
             "|---|---:|---:|---:|---:|"]
    for method, row in groups.items():
        d, e, s = row["depth_score"], row["explanation_score"], row["solve_success_k1"]
        text.append(f"| {LABELS[method]} | {number(d['mean'])} ({d['n']}) | {number(e['mean'])} ({e['n']}) | {number(s['mean'])} ({s['n']}) | "
                    f"{row['native_explanation_provided']}/{row['matched_actual_questions']} |")
    text += ["", "深度和解题成功率只在模型判有效且可评估子集上计算，错误/未决题不算难题；"
             "深度是有锚点的模型评分，未声称等于最短证明长度。单条reference常含多个小问，baseline可能仅含单问；"
             "尚未做逐小问严格规范，独立小问数量或字长都不能算推理依赖深度，当前代理不能证明结构深度优势。"
             "历史PF缺少原生解释，保留为null而非0分；"
             "外部证书由统一评测模型生成，不能将其评分称为原生解释质量，原生解释全量另行导出且主评隐藏。", "",
             "| PF减去基线 | 有效题/计划槽低代理宏平均差 | 95%seed bootstrap | 未决最不利分配差范围 | 共同seed |",
             "|---|---:|---:|---:|---:|"]
    for comparison in validity:
        m = comparison["metrics"]
        point, low, high = m["lower_minus_lower"]
        text.append(f"| {comparison['baseline']} | {number(point)} | [{number(low)}, {number(high)}] | "
                    f"[{number(m['difference_lower'][0])}, {number(m['difference_upper'][0])}] | {comparison['n']}/{comparison['eligible']} |")
    text += ["", "上述配对区间针对含生成失败的有效题交付代理，不是已有题条件正确率的比较。", "",
             "| PF减去基线 | 条件指标 | 同seed宏平均差 | 95%seed bootstrap | 有效评分共同seed |", "|---|---|---:|---:|---:|"]
    for comparison in quality:
        low, high = comparison["bootstrap_95"]
        text.append(f"| {comparison['baseline']} | {comparison['metric']} | {number(comparison['paired_seed_mean_difference'])} | "
                    f"[{number(low)}, {number(high)}] | {comparison['seed_coverage']}/{comparison['seed_total']} |")
    depth_pairs = {r["baseline"]: r for r in quality if r["metric"] == "depth_score"}
    text += ["", "**综合观察与可支持的限定结论。**", "",
             f"- 当前最明确的相对信号是模型判有效子集的深度代理：PF均值{number(pf['depth_score']['mean'])}，"
             f"直接造题{number(direct['depth_score']['mean'])}，生成器{number(framework['depth_score']['mean'])}。"
             f"PF对直接造题的同seed条件差为{number(depth_pairs['direct']['paired_seed_mean_difference'])}，"
             f"95%区间[{number(depth_pairs['direct']['bootstrap_95'][0])}, {number(depth_pairs['direct']['bootstrap_95'][1])}]，"
             f"覆盖{depth_pairs['direct']['seed_coverage']}/14个seed；对生成器为{number(depth_pairs['framework']['paired_seed_mean_difference'])}，"
             f"区间[{number(depth_pairs['framework']['bootstrap_95'][0])}, {number(depth_pairs['framework']['bootstrap_95'][1])}]，"
             f"覆盖{depth_pairs['framework']['seed_coverage']}/14。"
             "这是自动评分下的条件观察，不能改写为结构深度的确定优势：多小问、长度和有效子集筛选仍可能影响评分。",
             f"- 在同一解题预算下，有效题的k1成功率为PF {number(pf['solve_success_k1']['mean'])}、"
             f"直接造题{number(direct['solve_success_k1']['mean'])}、生成器{number(framework['solve_success_k1']['mean'])}。"
             "较低成功率是对该模型更具挑战性的线索；它不是普遍难度真值，更不能把未决或错误题也算作困难题。",
             f"- 正确性/交付率尚不能排序：PF的{pf['execution_unknown']}/28槽是执行未决而非模型判错，"
             f"其中按原因和阶段分解为{pf['execution_unknown_breakdown']}。"
             f"PF有效题/计划槽代理范围{pf['validity_proxy_lower']:.1%}—{pf['validity_proxy_upper']:.1%}，"
             f"直接造题{direct['validity_proxy_lower']:.1%}，生成器{framework['validity_proxy_lower']:.1%}—{framework['validity_proxy_upper']:.1%}；"
             "未决的不同归属会改变比较方向，配对交付代理差的统计区间也跨0。不能把PF未决一律当坏题，亦不能当正确题。",
             f"- 统一外部证书评分PF {number(pf['explanation_score']['mean'])}、直接造题{number(direct['explanation_score']['mean'])}、"
             f"生成器{number(framework['explanation_score']['mean'])}，条件配对差区间均跨0。"
             "本轮不支持PF解释性更优；这些证书由评测模型生成，历史PF没有原生解释，不能据此判断其原生解释质量。",
             "- 多样性指标没有给出一致的胜负：词面近重复、推理/约束/场景标签熵和结构标签组合分别反映不同代理；"
             "有效样本量也不同。不能只挑其中有利的一项写成整体语义多样性优势。", "",
             "**可用于论文的限定表述（探索性结果，需保留限制）：**", "",
             "We conducted an exploratory same-seed comparison on 14 seed families excluded from the previous pilot, "
             "using historical PF instances, direct API synthesis, and API-authored generators. "
             f"In a single-model audit of 28 slots per method with one solve per item, PF received a depth-proxy mean of {number(pf['depth_score']['mean'])}, "
             f"compared with {number(direct['depth_score']['mean'])} and {number(framework['depth_score']['mean'])} for the baselines on model-validated subsets. "
             f"The conditional seed-paired depth differences were {number(depth_pairs['direct']['paired_seed_mean_difference'])} and "
             f"{number(depth_pairs['framework']['paired_seed_mean_difference'])}, respectively. "
             f"However, {pf['execution_unknown']} PF audit slots remained unresolved within the fixed assessment limits. "
             "We therefore do not establish superior validity or explainability. These automated, subset-conditional findings "
             "should not be interpreted as proof of structural reasoning depth or a causal framework advantage, given historical "
             "backbone/filtering differences, multi-query composition and limited assessment coverage.", ""]
    text += ["", "每seed先平均再配对，2000次bootstrap、随机种子20261028。条件指标仅纳双方至少1道有效评分题的seed；"
             "覆盖与每seed评分题数保存在JSON，不能把不同有效题子集当完全配对的题目实验。未作多重比较显著性断言。", "",
             "| 方法 | CJK≥20题/实际题 | 题面字符数均值/中位数 | 精确重复 | 词面近重复/实际题 | 推理/约束/场景标签熵bits | 结构标签组合 |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for method, row in groups.items():
        ent = row["tag_entropy_bits"]
        length = row["problem_character_length"]
        text.append(f"| {LABELS[method]} | {row['cjk_ge20']}/{row['matched_actual_questions']} | {number(length['mean'],1)}/{number(length['median'],1)} | "
                    f"{row['normalized_exact_duplicate_items']} | "
                    f"{row['lexical_near_duplicate_items']}/{row['lexical_near_duplicate_denominator']} | "
                    f"{number(ent['reasoning_type_tags'])}/{number(ent['constraint_type_tags'])}/{number(ent['scenario'])} | {row['distinct_structure_tag_combinations']} |")
    text += ["", "CJK门槛只是中文合规指示，不能证明语言风格完全相同。词面近重复为同seed词/标点5-gram Jaccard≥0.85；"
             "标签是模型在有效题子集上给出的固定词表代理，组合数不是独立生成结构真值。二者不能直接证明语义多样性或推理深度。"
             "字符长度仅描述题量/渲染复杂度，不是难度或深度指标；单条题多小问会增加整条全部正确的要求，仍有任务量混杂。", "",
             "| 阶段/方法 | HTTP尝试 | 成功响应 | 返回usage响应/成功响应 | prompt tokens | completion tokens | total tokens |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for stage, entries in costs.items():
        for method, usage in entries.items():
            text.append(f"| {stage}/{method} | {usage['http_attempts']} | {usage['successful_responses']} | {usage['usage_responses']}/{usage['successful_responses']} | "
                        f"{usage['prompt_tokens']} | {usage['completion_tokens']} | {usage['total_tokens']} |")
    text += ["", "Token仅汇总成功响应中provider实际返回的字段，字段覆盖另存JSON；失败/截断可能也耗费token但不在成功响应合计内。"
             "历史PF生成开销未知；未核对实际价格/账单，因此不编造美元费用。", "", "独立核验与具体原题：", ""]
    if validation_paths:
        text += [f"- {link(path)}" for path in validation_paths]
    else:
        text += ["独立核验文件尚未提供；模型评语仍是待核查线索，不能当作证据。"]
    verified_cases = ROOT / "output/minimax_flash_v2_500_verified_cases.md"
    checks = ROOT / "output/validation/v2_20261028/independent_checks.json"
    logic_checks = ROOT / "output/validation/v2_20261028/logic_4_check.json"
    if all(path in validation_paths for path in (verified_cases, checks, logic_checks)):
        text += ["", "已核验的机制案例（不加入84槽抽评的总体分母）：", "",
                 "- 直接造题`direct/cipher_4/02`把C的坐标22写成25，正确应为`[[222566661552]]====2`；"
                 "同源历史PF与生成器案例均通过独立密码变换。这个具体错误支持逐字符回算的必要性，不证明直接造题普遍更差。",
                 "- `cipher_17`的三方法案例均通过独立栅格变换，说明baseline可以产出正确题；"
                 "`framework/logic_4/00`及`02`的归结步骤、终止轮次和原生解释也由独立归结程序与完整布尔枚举核对一致。",
                 "- 历史PF反例`puzzleforge/operation_5/14`把操作日程周期7误当作数值一般项周期：题面与金标要求n mod7=0时值174，"
                 "独立递推在n=7得到123。S2、S12、S55等其他小问算对，错误应限定在一般项/相应输出要求，而非笼统判整题每一问都错。",
                 "这些案例共同支持增加题面—答案独立回算、渲染一致性和周期/约束检查；"
                 "尚未证明某个框架组件必然带来多少收益，仍需组件消融及独立人工审核。"]
    text += ["", f"每组三道原样样题见{link(ROOT / 'output/minimax_flash_v2_500_examples.md')}；"
             "核验文件须给出同一原题ID、重算/反例及原始文件SHA，定向案例不加入84槽抽评分母。", "",
             "局限：历史PF与新baseline存在模型和先验过滤混杂；本轮中文控制仍需看实际输出，不能只相信提示词。"
             "14个seed、单模型k1、28槽/方法不足以证明普遍优势。新旧cohort的seed和语言条件不同，"
             "这些代理不能证明历史PF在所有质量维度都优于两种baseline。"
             "禁止直接用v1旧pilot与本轮分数之差声称v2 prompt带来提升；需要在同一批保留seed上做受控prompt消融。"]
    target = ROOT / "output/minimax_flash_v2_500_report.md"
    target.write_text("\n".join(text) + "\n", encoding="utf-8")
    preview = ["# v2：每组三道原样样题", "", "样题按预先列出的cipher_18、logic_4、word_sorting选取，"
               "每组取同seed首个matched槽；不按评测分数挑题，未生成时如实显示空槽。题面、答案和原生解释均未修订。", ""]
    for method in METHODS:
        preview += [f"## {LABELS[method]}", ""]
        for seed in ("cipher_18", "logic_4", "word_sorting"):
            record = min((r for r in records if r["method"] == method and r["seed_id"] == seed), key=lambda r:r["slot"])
            preview += [f"### {record_link(record)}", "", f"状态：{record['status']}", "", "```text", record["problem"] or "未生成题目", "```", "",
                        "原答案：", "```json", json.dumps(record["answer"], ensure_ascii=False), "```", "", "原生解释：", "```text",
                        record.get("explanation") or "未提供", "```", ""]
            if method == "framework":
                accepted = RUN / "programs" / seed / "accepted.json"
                if accepted.exists():
                    code = RUN / "programs" / seed / f"attempt-{read(accepted)['attempt']}.py"
                    preview += [f"生成程序：{link(code)}", ""]
    (ROOT / "output/minimax_flash_v2_500_examples.md").write_text("\n".join(preview), encoding="utf-8")
    sources = [HERE / "selection.json", HERE / "records_492.jsonl", HERE / "records_raw_selected.jsonl",
               HERE / "auto/model_labels.jsonl", HERE / "audit/audit_key.jsonl", Path(__file__), *validation_paths]
    if recovery is not None:
        sources += [recovery_manifest_path, recovery_status_path]
    (HERE / "report_reproduction.json").write_text(json.dumps({"sha256": {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        "outputs": [str(target.relative_to(ROOT)), "output/minimax_flash_v2_500_examples.md", *[item["path"] for item in question_exports]],
        "question_exports": question_exports,
        "bootstrap_seed": 20261028, "bootstrap_draws": 2000}, ensure_ascii=False, indent=2))
    print(target)
    print(HERE / "final_metrics.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation", type=Path, action="append", default=[], help="Existing independent validation report/script; never invented")
    args = parser.parse_args()
    main([path.resolve() for path in args.validation])
