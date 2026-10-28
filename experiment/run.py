"""Prepare immutable inputs, generate two baselines, and export a comparison JSONL."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import random
import re
import shutil
import subprocess
import sys
from typing import Any

from .api import ChatClient
from .costs import summarize_costs
from .executor import GeneratorError, run_generator
from .env import load_env

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = Path(__file__).parent / "prompts"


def prompt_paths(config: dict[str, Any], method: str) -> list[Path]:
    variant = config.get("prompt_variant", "legacy")
    if variant == "legacy":
        return [PROMPTS / "quality.txt", PROMPTS / f"{method}.txt"]
    if variant == "paper_v2":
        language = config.get("prompt_language", "zh")
        if language not in ("zh", "en"):
            raise ValueError("paper_v2 prompt_language must be zh or en")
        if config.get("output_language", "zh") not in ("zh", "en"):
            raise ValueError("output_language must be zh or en")
        return [PROMPTS / "paper_v2" / language / f"{method}.txt"]
    raise ValueError(f"Unknown prompt_variant: {variant}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_for(source: str, known: set[str]) -> str:
    value = re.sub(r"_[0-3]$", "", source)
    if value not in known:
        raise ValueError(f"Cannot map source to a known seed: {source}")
    return value


def prepare(config_path: Path, out: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    selected_prompts = sorted({p for method in ("direct", "framework") for p in prompt_paths(config, method)})
    if config["per_seed"] != 20 or config["batch_size"] < 1 or config["generation_attempts"] < 1:
        raise ValueError("Frozen protocol requires 20 slots per seed and positive batch/attempt counts")
    data = (ROOT / config["source_dir"]).resolve()
    seeds = read_jsonl(data / "seed_puzzles.jsonl")
    known = {s["id"] for s in seeds}
    if len(seeds) != 129 or len(known) != 129:
        raise ValueError("Expected exactly 129 unique paper seeds")
    refs = read_jsonl(data / "test_normal.jsonl") + read_jsonl(data / "test_hard.jsonl")
    if len(refs) != 1720 or len({r["id"] for r in refs}) != 1720:
        raise ValueError("Expected the unmodified 1720 unique PF-86K test instances")
    quotas: dict[str, int] = {s: 0 for s in known}
    for row in refs:
        quotas[seed_for(row["source"], known)] += 1
    if any(n < 2 or n > 20 for n in quotas.values()):
        raise ValueError("Reference quotas cannot be paired to the frozen 20-slot design")
    # Randomly designate matched slots BEFORE generation; never select by quality.
    slots: dict[str, list[int]] = {}
    for seed in sorted(known):
        indices = list(range(20))
        random.Random(f"{config['rng_seed']}:{seed}:cohort").shuffle(indices)
        slots[seed] = sorted(indices[:quotas[seed]])
    tracked = [data / n for n in ("seed_puzzles.jsonl", "test_normal.jsonl", "test_hard.jsonl", "README.md")]
    tracked += selected_prompts + sorted(Path(__file__).parent.glob("*.py"))
    tracked.append(ROOT / "runtime-requirements.lock")
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in tracked}
    runtime_python = str((ROOT / config["python_executable"]).absolute())
    runtime = subprocess.run([runtime_python, "-I", "-c", "import sys,importlib.metadata,json; print(json.dumps({'version':sys.version,'packages':{p.metadata['Name']:p.version for p in importlib.metadata.distributions()}}))"], capture_output=True, text=True, check=True)
    manifest = {
        "config": config, "input_hashes": hashes, "matched_slots": slots,
        "quotas": quotas, "counts": {"puzzleforge": 1720, "direct": 2580, "framework": 2580},
        "python": sys.version, "platform": platform.platform(),
        "generator_runtime": json.loads(runtime.stdout),
        "packages": {p.metadata["Name"]: p.version for p in importlib.metadata.distributions()},
        "reference_status": "historical filtered test data; not a newly controlled PuzzleForge run",
    }
    out.mkdir(parents=True, exist_ok=True)
    path = out / "manifest.json"
    if path.exists():
        saved = json.loads(path.read_text())
        for key in ("config", "input_hashes", "matched_slots", "generator_runtime"):
            if saved[key] != manifest[key]:
                raise ValueError(f"Frozen run changed ({key}); use a new output directory")
        return saved
    write_json(path, manifest)
    for original in tracked:
        target = out / "snapshot" / original.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
    write_json(out / "seeds.json", seeds)
    reference = []
    for seed_id in sorted(known):
        rows = sorted((r for r in refs if seed_for(r["source"], known) == seed_id), key=lambda r: r["id"])
        for slot, row in zip(slots[seed_id], rows):
            reference.append({
                "id": f"puzzleforge/{seed_id}/{slot:02d}", "original_id": row["id"],
                "method": "puzzleforge", "seed_id": seed_id, "slot": slot,
                "problem": row["problem"], "answer": row["answer"], "explanation": None,
                "status": "ok", "cohort": "matched", "generator_id": row["source"],
                "paper_difficulty": row["difficulty"], "eval_type": row["eval_type"],
            })
    write_json(out / "reference.json", reference)
    return manifest


def record(seed_id: str, method: str, slot: int, matched: list[int], row: dict[str, Any] | None, **meta: Any) -> dict[str, Any]:
    return {
        "id": f"{method}/{seed_id}/{slot:02d}", "method": method, "seed_id": seed_id,
        "slot": slot, "cohort": "matched" if slot in matched else "extra",
        "status": "ok" if row is not None else "generation_failed",
        "problem": row["problem"] if row else "", "answer": row["answer"] if row else None,
        "explanation": row.get("explanation") if row else None, **meta,
    }


def parse_rows(content: str, count: int) -> list[dict[str, Any]]:
    if content.strip().startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    rows = json.loads(content)
    json.dumps(rows, allow_nan=False)
    if not isinstance(rows, list) or len(rows) != count:
        raise ValueError(f"Expected exactly {count} problem records")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("problem"), str) or not row["problem"].strip() or "answer" not in row:
            raise ValueError("Each record needs nonempty problem and answer")
        if not isinstance(row.get("explanation"), str):
            raise ValueError("Each record needs a checkable explanation string")
    return rows


def content_of(response: dict[str, Any]) -> str:
    return response["choices"][0]["message"]["content"]


def generate(manifest: dict[str, Any], out: Path, method: str, seed_ids: set[str] | None = None) -> None:
    c = manifest["config"]
    paths = prompt_paths(c, method)
    system_parts = []
    for path in paths:
        relative = str(path.relative_to(ROOT))
        frozen = out / "snapshot" / relative
        hashes = manifest.get("input_hashes")
        if hashes is not None:
            if relative not in hashes or not frozen.exists() or sha(frozen) != hashes[relative]:
                raise ValueError(f"Frozen prompt missing or changed: {relative}")
            system_parts.append(frozen.read_text())
        else:
            # Lightweight callers without a prepared manifest, such as unit fixtures.
            system_parts.append(path.read_text())
    system = "\n".join(system_parts)
    if not c["endpoint"]:
        raise ValueError("Set endpoint in the configuration before starting a NEW live run")
    if method == "framework":
        # Probe our own runtime before spending any tokens on generated code.
        imports = "\n".join(f"import {name}" for name in c["runtime_libraries"])
        if any(not re.fullmatch(r"[A-Za-z_]\w*", name) for name in c["runtime_libraries"]):
            raise ValueError("Runtime library names must be import identifiers")
        probe_code = imports + "\nimport json,sys; r=json.load(sys.stdin); print(json.dumps([{'problem':'runtime probe','answer':0} for _ in range(r['count'])]))"
        run_generator(probe_code, c["rng_seed"], 1, out / "runtime_probe", python_executable=str((ROOT / c["python_executable"]).absolute()))
    client = ChatClient(c["endpoint"], c["model"], out / "api_cache", c["api_key_env"], c["parameters"], c["timeout"], c["http_retries"], c["max_calls"])
    seeds = json.loads((out / "seeds.json").read_text())
    if seed_ids is not None:
        unknown = seed_ids - {s["id"] for s in seeds}
        if unknown:
            raise ValueError(f"Unknown seed IDs: {sorted(unknown)}")
        seeds = [s for s in seeds if s["id"] in seed_ids]
    def generate_seed(source: dict[str, Any]) -> None:
        sid = source["id"]
        matched = manifest["matched_slots"][sid]
        base = {"role": "user", "content": json.dumps({"seed_question": source["question"], "seed_answer": source["answer"]}, ensure_ascii=False)}
        previous: list[str] = []
        step = c["batch_size"] if method == "direct" else 20
        for start in range(0, 20, step):
            count = min(step, 20 - start)
            result_path = out / "results" / method / sid / f"{start:02d}.json"
            if result_path.exists():
                previous.extend(r["problem"] for r in json.loads(result_path.read_text()) if r["status"] == "ok")
                continue
            request = {"count": count, "already_generated_problems": previous} if method == "direct" else {"available_libraries": c["runtime_libraries"], "target_count": 20}
            if c.get("prompt_variant", "legacy") == "paper_v2":
                request["output_language"] = c.get("output_language", "zh")
            messages = [{"role": "system", "content": system}, base, {"role": "user", "content": json.dumps(request, ensure_ascii=False)}]
            rows = None
            diagnostic = ""
            tag = ""
            for attempt in range(c["generation_attempts"]):
                tag = f"{method}/{sid}/{start}/attempt-{attempt}"
                prompt_path = out / "traces" / method / sid / str(start) / f"attempt-{attempt}.json"
                if prompt_path.exists():
                    messages = json.loads(prompt_path.read_text())
                else:
                    write_json(prompt_path, messages)
                response = client.complete(messages, tag=tag)  # Infrastructure errors abort; resume later.
                answer = content_of(response)
                try:
                    if method == "direct":
                        rows = parse_rows(answer, count)
                    else:
                        # C is model-authored: the API response is the generator. This repo
                        # only provides the prompt, sandbox, probe, and repair loop.
                        code = re.sub(r"^```(?:python)?\s*|\s*```$", "", answer.strip())
                        code_dir = out / "programs" / sid
                        code_dir.mkdir(parents=True, exist_ok=True)
                        (code_dir / f"attempt-{attempt}.py").write_text(code)
                        local_seed = int(hashlib.sha256(f"{c['rng_seed']}:{sid}".encode()).hexdigest()[:8], 16)
                        kwargs = {"python_executable": str((ROOT / c["python_executable"]).absolute()), "timeout": c["runtime_timeout"]}
                        probe = run_generator(code, local_seed + 1, 3, code_dir / "jobs", **kwargs)
                        repeat = run_generator(code, local_seed + 1, 3, code_dir / "jobs", **kwargs)
                        if probe != repeat:
                            raise ValueError("Generator is not deterministic for the same sampling seed")
                        rows = run_generator(code, local_seed, count, code_dir / "jobs", **kwargs)
                        rows = parse_rows(json.dumps(rows, ensure_ascii=False), count)
                        write_json(code_dir / "accepted.json", {"attempt": attempt, "sample_seed": local_seed, "code_sha256": hashlib.sha256(code.encode()).hexdigest(), "probe": probe})
                    break
                except (ValueError, TypeError, GeneratorError) as exc:
                    rows = None
                    if "runtime not available" in str(exc):
                        raise  # A missing runtime is not a method quality failure.
                    diagnostic = str(exc)[:4096]
                    if method == "framework":
                        job_root = re.escape(str(out / "programs" / sid / "jobs"))
                        diagnostic = re.sub(job_root + r"/generator-[A-Za-z0-9_-]+", "<GENERATOR_JOB>", diagnostic)
                    messages += [{"role": "assistant", "content": answer}, {"role": "user", "content": f"Repair your output. Execution/format feedback: {diagnostic}"}]
            records = [record(sid, method, start + i, matched, rows[i] if rows else None, request_tag=tag, attempts=attempt + 1, failure=diagnostic if rows is None else None, model_requested=c["model"], model_returned=response.get("model"), generator_id=f"{sid}/attempt-{attempt}" if method == "framework" else None) for i in range(count)]
            write_json(result_path, records)
            previous.extend(r["problem"] for r in records if r["status"] == "ok")
            print(f"{method}: {sid} slots {start}-{start+count-1} saved", flush=True)

    workers = c.get("workers", 1)
    if not isinstance(workers, int) or workers < 1:
        raise ValueError("workers must be a positive integer")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # Consume every result; infrastructure errors propagate and saved batches remain resumable.
        list(pool.map(generate_seed, seeds))


def export(out: Path, seed_ids: set[str] | None = None, filename: str = "records.jsonl") -> Path:
    if Path(filename).name != filename:
        raise ValueError("filename must be a plain file name inside the run directory")
    records = json.loads((out / "reference.json").read_text())
    for p in sorted((out / "results").glob("*/*/*.json")):
        records.extend(json.loads(p.read_text()))
    if seed_ids is not None:
        records = [r for r in records if r["seed_id"] in seed_ids]
    path = out / filename
    path.write_text("".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in records), encoding="utf-8")
    return path


def main() -> None:
    load_env(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "generate", "export"])
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment.example.json")
    parser.add_argument("--out", type=Path, default=ROOT / "runs/plan")
    parser.add_argument("--method", choices=["direct", "framework", "both"], default="both")
    parser.add_argument("--seed-ids", nargs="+", help="Run selected seeds first without changing frozen inputs; omit to resume all")
    parser.add_argument("--seed-file", type=Path, help="Whitespace/newline separated seed IDs to add to --seed-ids")
    parser.add_argument("--filename", default="records.jsonl", help="Export file name inside --out (export action only)")
    args = parser.parse_args()
    out = args.out.resolve()
    selected: set[str] | None = set(args.seed_ids or [])
    if args.seed_file:
        selected = (selected or set()) | set(args.seed_file.read_text(encoding="utf-8").split())
    if not selected:
        selected = None
    if args.action == "export":
        print(export(out, selected, args.filename))
        return
    manifest = prepare(args.config.resolve(), out)
    if args.action == "generate":
        for method in (["direct", "framework"] if args.method == "both" else [args.method]):
            generate(manifest, out, method, selected)
        write_json(out / "generation_costs.json", summarize_costs(out / "api_cache/requests.jsonl"))
    print(json.dumps(manifest["counts"]))
    print(export(out))


if __name__ == "__main__":
    main()
