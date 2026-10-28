"""Prepare and assess the frozen v2 holdout pilot without changing experiment code.

Credentials are read only from the configured environment variable, never .env.
No API request is made by prepare or report. Evaluate requires --endpoint.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import threading

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from experiment.api import APIError, ChatClient
from experiment.autojudge import (
    EvaluationError, JUDGE_SYSTEM, SOLVE_SYSTEM, _assessment, _digest, _judge,
    _outputs, _paired_proxy, _solution, consensus,
)
from experiment.evaluation import prepare_audit
from experiment.metrics import lexical_metrics

MODEL = "MiniMax-M3.1-Flash"
PARAMETERS = {"reasoning_effort": "medium", "max_completion_tokens": 16384}
APPROVED_SEEDS = ["cipher_18", "cipher_4", "cipher_8", "cipher_17", "logic_4", "logic_11", "logic_17", "logic_3",
                  "operation_22", "operation_20", "operation_24", "operation_5", "word_sorting", "puzzle_15"]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path, value, frozen=False):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if frozen and path.exists() and path.read_text(encoding="utf-8") != text:
        raise ValueError(f"Frozen input changed: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path, values):
    text = "".join(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n" for value in values)
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise ValueError(f"Frozen corpus changed: {path}")
    path.write_text(text, encoding="utf-8")


def prepare():
    selection, manifest = read(HERE / "selection.json"), read(RUN / "manifest.json")
    selected = selection["selected_seed_ids"]
    if selected != APPROVED_SEEDS:
        raise ValueError("Selection differs from the 14 explicitly confirmed holdout seeds")
    old = read(ROOT / "runs/minimax_flash_20261028/pilot_500/selection.json")["selected_seed_ids"]
    if set(selected) & set(old):
        raise ValueError("New holdout overlaps old pilot")
    records, raw_selected, source_files = [], [], [HERE / "selection.json", RUN / "manifest.json"]
    for method in ("puzzleforge", "direct", "framework"):
        files = [RUN / "reference.json"] if method == "puzzleforge" else sorted(
            path for seed in selected for path in (RUN / "results" / method / seed).glob("*.json"))
        source_files += files
        candidates = [row for path in files for row in read(path)]
        raw = [row for row in candidates if row["seed_id"] in selected]
        if method != "puzzleforge":
            for seed in selected:
                if sorted(row["slot"] for row in raw if row["seed_id"] == seed) != list(range(20)):
                    raise ValueError(f"All 20 raw generated slots must be persisted first: {method}/{seed}")
        raw_selected.extend(sorted(raw, key=lambda row: (selected.index(row["seed_id"]), row["slot"])))
        chosen = [row for row in candidates if row["seed_id"] in selected
                  and row["slot"] in manifest["matched_slots"][row["seed_id"]]]
        for seed in selected:
            actual = sorted(row["slot"] for row in chosen if row["seed_id"] == seed)
            if actual != sorted(manifest["matched_slots"][seed]):
                raise ValueError(f"Missing or duplicate persisted slots: {method}/{seed}; do not fabricate failures")
        if len(chosen) != 164:
            raise ValueError(f"Expected 164 matched slots per method, got {method}={len(chosen)}")
        records.extend(sorted(chosen, key=lambda row: (selected.index(row["seed_id"]), row["slot"])))
    write_jsonl(HERE / "records_492.jsonl", records)
    write_jsonl(HERE / "records_raw_selected.jsonl", raw_selected)
    write_jsonl(HERE / "native_explanations.jsonl", [
        {field: row.get(field) for field in ("id", "method", "seed_id", "slot", "cohort", "status", "problem", "answer", "explanation")}
        for row in raw_selected])
    prepare_audit(records, HERE / "audit", seed=20261028, per_seed=2)
    audit = jsonl(HERE / "audit/audit_blind.jsonl")
    if len(audit) != 84:
        raise ValueError("Expected exactly 84 frozen blind evaluation slots")
    source_files += [HERE / "records_492.jsonl", HERE / "audit/audit_blind.jsonl", HERE / "audit/audit_key.jsonl"]
    write_json(HERE / "corpus_reproduction.json", {
        "counts": {"matched_slots": 492, "per_method": 164, "audit_slots": 84, "per_seed_method": 2},
        "sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
        "language_policy": "Generation output_language must be explicitly zh; CJK>=20 is descriptive only"}, frozen=True)
    print(f"Prepared 492 matched slots / 84 blind evaluation slots in {HERE}", flush=True)


def evaluate(endpoint, api_key_env="MINIMAX_API_KEY"):
    items, key = jsonl(HERE / "audit/audit_blind.jsonl"), jsonl(HERE / "audit/audit_key.jsonl")
    if len(items) != 84 or len({r["anon_id"] for r in items}) != 84:
        raise ValueError("Expected exactly 84 distinct frozen blind items")
    out = HERE / "auto"
    state_dir = out / "items"
    state_dir.mkdir(parents=True, exist_ok=True)
    source_paths = [Path(__file__), ROOT / "experiment/api.py", ROOT / "experiment/autojudge.py", ROOT / "experiment/evaluation.py"]
    manifest = {"model": MODEL, "endpoint": endpoint, "api_key_env": api_key_env, "parameters": PARAMETERS,
                "k": 1, "workers": 8, "timeout_seconds": 300, "http_retries": 1, "max_http_attempts": 400,
                "input_hash": _digest(items), "key_hash": _digest(key), "prompt_hash": _digest([SOLVE_SYSTEM, JUDGE_SYSTEM]),
                "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths},
                "unknown_policy": "No solve resampling after truncated response; three schema attempts then execution_unknown. Other API failures propagate."}
    write_json(out / "evaluation_manifest.json", manifest, frozen=True)
    client = ChatClient(endpoint, MODEL, out / "api_cache", api_key_env, PARAMETERS, timeout=300, retries=1, max_calls=400)
    stop = threading.Event()

    def request(model, messages, tag):
        if stop.is_set():
            raise RuntimeError("Evaluation stopped after infrastructure failure")
        if model != MODEL:
            raise ValueError("Only the approved MiniMax Flash model may be requested")
        return client.complete(messages, tag)

    def process(item):
        path = state_dir / f"{_digest(item)}.json"
        if path.exists():
            return read(path)
        row = {"anon_id": item["anon_id"], "k": 1, "models": [MODEL], "attempts": [], "judges": []}
        if not str(item.get("problem", "")).strip():
            row["status"] = "unavailable"
            write_json(path, row)
            return row
        phase, tag = "solve", ""
        try:
            messages = [{"role": "system", "content": SOLVE_SYSTEM},
                        {"role": "user", "content": json.dumps({"problem": item["problem"]}, ensure_ascii=False)}]
            tag = f"holdout-paper-v2:{item['anon_id']}:solve:0:0"
            solved = _assessment(request, MODEL, messages, tag, _solution)
            row["attempts"] = [{"panel": 0, "sample": 0, "answer": solved["answer"], "certificate": solved["certificate"]}]
            phase = "judge"
            messages = [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": json.dumps({
                "problem": item["problem"], "canonical_answer": item["answer"], "attempts": row["attempts"]}, ensure_ascii=False)}]
            tag = f"holdout-paper-v2:{item['anon_id']}:judge:0"
            row["judges"] = [_assessment(request, MODEL, messages, tag, lambda value: _judge(value, 1))]
            row["label_origin"] = "model"
            row["assessment_status"] = "model_judgment"
        except (APIError, EvaluationError) as exc:
            if isinstance(exc, APIError) and exc.kind != "truncated_response":
                raise
            # Empty judges means uncertain in the existing consensus helper; no fake model review is created.
            row.update(label_origin="execution_policy", assessment_status="execution_unknown", judges=[],
                       execution_error={"type": type(exc).__name__, "kind": getattr(exc, "kind", "schema_exhausted"),
                                        "message": str(exc), "phase": phase, "tag_prefix": tag})
        row["status"] = "completed"  # Processing completed; not a claim of a completed model judgment.
        write_json(path, row)
        return row

    def saved():
        return [read(path) for item in items if (path := state_dir / f"{_digest(item)}.json").exists()]

    try:
        with ThreadPoolExecutor(max_workers=8, thread_name_prefix="holdout-eval") as pool:
            futures = [pool.submit(process, item) for item in items]
            try:
                for index, future in enumerate(as_completed(futures), 1):
                    future.result()
                    if index % 10 == 0:
                        print(f"v2 automatic pilot: {index}/84 processed", flush=True)
                    if index % 20 == 0:
                        outcomes = saved()
                        _outputs(outcomes, items, out, [MODEL], key)
                        fix_banner(outcomes)
            except BaseException:
                stop.set()
                for future in futures:
                    future.cancel()
                raise
    finally:
        outcomes = saved()
        _outputs(outcomes, items, out, [MODEL], key)
        fix_banner(outcomes)
    print(f"v2 automatic pilot finished: {len(saved())}/84 processed", flush=True)


def fix_banner(labels):
    report = HERE / "auto/auto_report.md"
    if not report.exists():
        return
    actual = sum(r.get("assessment_status") == "model_judgment" for r in labels)
    unknown = sum(r.get("assessment_status") == "execution_unknown" for r in labels)
    unavailable = sum(r["status"] == "unavailable" for r in labels)
    text = re.sub(r"有完整模型评估 \d+ 题；无输出槽位 \d+。?",
                  f"真实模型判定 {actual} 题；执行未决 {unknown} 题；无输出槽位 {unavailable}题",
                  report.read_text(), count=1)
    text = text.replace("| 完整评估 |", "| 已处理有题(含执行未决) |")
    text = text.replace("已处理槽（完整评估或unavailable）", "已处理槽（含执行未决的有题槽或unavailable）")
    explanation = ("处理口径：已处理有题仅表示执行流程终结，包含execution_unknown，不能称为完整模型评审。"
                   "真实模型判定、执行未决和无输出的逐组拆分，以final_metrics.json及用户主报告为准。")
    if explanation not in text:
        text = text.replace("\n\n模型共识", f"\n\n{explanation}\n\n模型共识", 1)
    report.write_text(text)


def report():
    corpus, labels = jsonl(HERE / "records_492.jsonl"), jsonl(HERE / "auto/model_labels.jsonl")
    key = jsonl(HERE / "audit/audit_key.jsonl")
    links = {r["anon_id"]: r for r in key}
    statistics = {}
    for method in ("puzzleforge", "direct", "framework"):
        planned = [r for r in corpus if r["method"] == method]
        ok = [r for r in planned if r["status"] == "ok"]
        sample = [r for r in labels if links[r["anon_id"]]["method"] == method]
        statistics[method] = {"slots": len(planned), "actual_questions": len(ok),
                              "cjk_ge20": sum(len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", r["problem"])) >= 20 for r in ok),
                              "processed": len(sample), "verdicts": dict(Counter(consensus(r) for r in sample)),
                              "execution_unknown": sum(r.get("assessment_status") == "execution_unknown" for r in sample),
                              "model_judgments": sum(r.get("assessment_status") == "model_judgment" for r in sample)}
    write_json(HERE / "analysis_summary.json", {"groups": statistics,
               "paired_seed_comparisons": _paired_proxy(labels, key), "lexical_metrics": lexical_metrics(corpus),
               "warning": "Single-model k1 proxy; no preset winner. Historical model/filter confounding remains; inspect actual language compliance."})
    fix_banner(labels)
    print(json.dumps(statistics, ensure_ascii=False), flush=True)
    print(HERE / "auto/auto_report.md", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["prepare", "evaluate", "report"])
    p.add_argument("--endpoint")
    p.add_argument("--api-key-env", default="MINIMAX_API_KEY")
    args = p.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "evaluate":
        if not args.endpoint:
            p.error("evaluate requires --endpoint; credentials must already be set in the environment")
        evaluate(args.endpoint, args.api_key_env)
    else:
        report()
