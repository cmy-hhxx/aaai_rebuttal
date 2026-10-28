"""Run-local, generation-only recovery of real length-truncated responses.

Default invocation freezes policy only. Live execution requires --execute and
the previous process PID; never use reasoning_content as final model output.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from typing import Any

HERE = Path(__file__).resolve().parent
RUN = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from experiment import run
from experiment.api import APIError, ChatClient
from experiment.env import load_env
from experiment.executor import GeneratorError


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RecoveryClient(ChatClient):
    """Replay only exact-identity, persisted length failures, without a new call."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = threading.local()

    def _length_failure(self, identity, request_digest):
        files = sorted(self.cache_dir.glob(f"{request_digest}.failure-*.json"),
                       key=lambda path: int(path.stem.rsplit("-", 1)[1]), reverse=True)
        for path in files:
            saved = read(path)
            if saved.get("kind") != "truncated_response":
                continue
            if any(saved.get(key) != value for key, value in identity.items()):
                raise ValueError("Recovery identity mismatch; refusing replay or new sampling")
            if digest(identity) != request_digest or read(self.cache_dir / f"{request_digest}.request.json") != identity:
                raise ValueError("Recovery request digest mismatch")
            response = saved["response"]
            choice = response["choices"][0]
            if choice.get("finish_reason") != "length" or response.get("model") != identity["payload"]["model"]:
                raise ValueError("Recovery response is not the requested model's length truncation")
            message = choice["message"]
            final = message.get("content")
            if final is not None and not isinstance(final, str):
                raise ValueError("Unsupported final-content type in length response")
            self.context.empty_length = not final or not final.strip()
            self.context.method = identity["tag"].split("/", 1)[0]
            self.context.cap = identity["payload"]["max_completion_tokens"]
            self._log("generation_length_replay", digest=request_digest, tag=identity["tag"],
                      source_failure=path.name, source_sha256=file_hash(path),
                      finish_reason="length", final_content_present="content" in message,
                      final_content_type=type(final).__name__, final_content_length=len(final or ""),
                      response_model=response.get("model"), usage=response.get("usage"),
                      new_http_attempt=False)
            return response  # Unmodified raw response, including the real finish_reason.
        return None

    def _complete(self, identity: dict[str, Any], request_digest: str) -> dict[str, Any]:
        if identity["tag"].split("/", 1)[0] not in ("direct", "framework"):
            raise ValueError("Recovery adapter is restricted to generation, never evaluation")
        self.context.empty_length = False
        saved = self._length_failure(identity, request_digest)
        if saved is not None:
            return saved
        try:
            return super()._complete(identity, request_digest)
        except APIError as exc:
            if exc.kind != "truncated_response":
                raise
            saved = self._length_failure(identity, request_digest)
            if saved is None:
                raise
            return saved

    def diagnostic(self):
        task = "a concise implementation" if self.context.method == "framework" else "concise problem JSON"
        return (f"Response was truncated at unchanged {self.context.cap} token cap; "
                f"final output was empty or absent; return {task}. "
                "No reasoning_content was used as final output.")


@contextmanager
def bindings(client):
    originals = run.ChatClient, run.content_of, run.parse_rows, run.run_generator

    def final_content(response):
        choice = response["choices"][0]
        if choice.get("finish_reason") == "length" and choice["message"].get("content") is None:
            return ""  # Projection only; never add content or change the raw response.
        return originals[1](response)

    def parse(content, count):
        if not content.strip() and getattr(client.context, "empty_length", False):
            raise ValueError(client.diagnostic())
        return originals[2](content, count)

    def execute(code, *args, **kwargs):
        if not code.strip() and getattr(client.context, "empty_length", False):
            raise GeneratorError(client.diagnostic())
        return originals[3](code, *args, **kwargs)

    run.ChatClient = lambda *args, **kwargs: client  # One shared original 200-attempt budget.
    run.content_of, run.parse_rows, run.run_generator = final_content, parse, execute
    try:
        yield
    finally:
        run.ChatClient, run.content_of, run.parse_rows, run.run_generator = originals


def freeze_policy(folder=RUN):
    manifest = read(folder / "manifest.json")
    c = manifest["config"]
    if c["max_calls"] != 200 or c["generation_attempts"] != 3 or c["parameters"]["max_completion_tokens"] != 32768:
        raise ValueError("Recovery must preserve the frozen 200 HTTP / 3 generation / 32768 token budgets")
    for relative, expected in manifest["input_hashes"].items():
        if file_hash(ROOT / relative) != expected:
            raise ValueError(f"Frozen source changed: {relative}")
    value = {
        "policy_version": 1, "adapter_sha256": file_hash(Path(__file__)),
        "original_manifest_sha256": file_hash(folder / "manifest.json"),
        "selection_sha256": file_hash(folder / "pilot_500/selection.json"),
        "model": c["model"], "endpoint": c["endpoint"], "parameters": c["parameters"],
        "max_http_attempts": 200, "generation_attempts_per_task": 3,
        "recovery_http_timeout_seconds": 900, "recovery_http_retries": 0,
        "initial_failure": {"tag": "framework/logic_11/0/attempt-0", "call_number": 64},
        "policy": [
            "Generation-only, identical policy for direct/framework; evaluation behavior is unchanged.",
            "Replay a persisted exact request identity and model's length response without a new HTTP call.",
            "Preserve raw finish_reason/usage/failure files; never read reasoning_content as final code.",
            "Missing/null final content is projected to an empty string only for parsing; raw response is unchanged.",
            "Empty truncated output gets truthful bounded-format feedback, then original attempt1/2 repair.",
            "No token-cap increase, extra generation attempt, new attempt0 draw, quality feedback or failed-seed reopening.",
            "Use the same client across methods; all existing request_start entries count toward 200.",
            "Infrastructure revision: use 900s HTTP timeout and no automatic HTTP retries for new calls; model/token/reasoning/generation budgets are unchanged.",
            "Timed-out or interrupted requests without usable final responses remain infrastructure failures, not fabricated bad questions; a resume may resend their identical request once with the longer timeout.",
            "Prior in-flight HTTP attempts remain counted even if their server-side completion or billing is unknown.",
            "New length failures follow this same fixed rule and are logged with identity/failure hashes.",
            "Execute only after previous generation process has exited; completed result files are never overwritten.",
        ],
    }
    initial = list((folder / "api_cache").glob("*.failure-64.json"))
    if len(initial) != 1:
        raise ValueError("Expected exactly one original call-64 failure file")
    value["initial_failure"].update(path=initial[0].name, sha256=file_hash(initial[0]))
    policy = folder / "pilot_500/generation_recovery_manifest.json"
    if policy.exists() and read(policy) != value:
        raise ValueError("Frozen recovery policy changed")
    if not policy.exists():
        run.write_json(policy, value)
    return manifest


def pending_seeds(folder, method, selected):
    starts = (0, 5, 10, 15) if method == "direct" else (0,)
    return {seed for seed in selected if any(not (folder / "results" / method / seed / f"{start:02d}.json").exists() for start in starts)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--previous-pid", type=int)
    args = parser.parse_args()
    if args.execute:
        if args.previous_pid is None or args.previous_pid <= 0:
            parser.error("--execute requires the previous generation --previous-pid")
        try:
            os.kill(args.previous_pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise RuntimeError("Previous generation process still exists; do not start recovery concurrently")
    manifest = freeze_policy()
    if not args.execute:
        print("Recovery policy frozen; no credentials read and no API called.")
        return
    load_env(ROOT / ".env")
    c = manifest["config"]
    client = RecoveryClient(c["endpoint"], c["model"], RUN / "api_cache", c["api_key_env"],
                            c["parameters"], 900, 0, c["max_calls"])
    selected = read(HERE / "selection.json")["selected_seed_ids"]
    try:
        with bindings(client):
            for method in ("direct", "framework"):
                pending = pending_seeds(RUN, method, selected)
                if pending:
                    run.generate(manifest, RUN, method, pending)
    finally:
        events = [json.loads(line) for line in client.log_path.read_text().splitlines() if line.strip()]
        exhausted = []
        for path in (RUN / "results").glob("*/*/*.json"):
            rows = read(path)
            if rows and all(row["status"] == "generation_failed" and row.get("attempts") == 3 for row in rows):
                exhausted.append(str(path.relative_to(RUN)))
        run.write_json(HERE / "generation_recovery_status.json", {
            "http_attempts_total": sum(event["event"] == "request_start" for event in events),
            "replayed_length_tags": [event["tag"] for event in events if event["event"] == "generation_length_replay"],
            "transport_failures": [{"tag": event["tag"], "attempt": event.get("attempt")} for event in events if event["event"] == "request_failure" and event.get("kind") == "transport_error"],
            "three_generation_attempts_exhausted_results": exhausted,
            "missing_result_seed_ids": {method: sorted(pending_seeds(RUN, method, selected)) for method in ("direct", "framework")},
            "interpretation": "Transport failures/interrupted calls are infrastructure events, not fabricated quality failures. Only persisted generation_failed records count as exhausted method outputs; request costs without usage may remain unknown.",
        })
    run.export(RUN)
    print("Recovery finished; existing successful and exhausted-failure results were retained.")


if __name__ == "__main__":
    main()
