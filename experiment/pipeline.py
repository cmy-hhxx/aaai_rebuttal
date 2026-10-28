"""One-command generation, offline checks, blind sampling and optional model assessment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import unicodedata

from .autojudge import run_audit
from .costs import summarize_costs
from .evaluation import prepare_audit, summarize
from .env import load_env
from .metrics import lexical_metrics
from .run import ROOT, export, generate, prepare, read_jsonl, write_json


def main() -> None:
    load_env(ROOT / ".env")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    manifest = prepare(a.config.resolve(), out)
    try:
        for method in ("direct", "framework"):
            generate(manifest, out, method)
    finally:
        # A stopped run still has a readable export; it is not declared complete.
        export(out)
        write_json(out / "generation_costs.json", summarize_costs(out / "api_cache/requests.jsonl"))
    records = read_jsonl(out / "records.jsonl")
    if len(records) != 6880 or len({r["id"] for r in records}) != 6880:
        raise ValueError("Run is incomplete; expected all 6880 slots including failures")
    yields = {}
    for method in ("direct", "framework"):
        ok = [r for r in records if r["method"] == method and r["status"] == "ok"]
        unique = {" ".join(unicodedata.normalize("NFKC", r["problem"]).casefold().split()) for r in ok}
        yields[method] = {"output_count": len(ok), "unique_count": len(unique), "at_least_2000_unique": len(unique) >= 2000}
    write_json(out / "yield_status.json", yields)
    write_json(out / "lexical_metrics.json", lexical_metrics(records))
    audit = out / "audit"
    prepare_audit(records, audit)
    (out / "report.md").write_text(summarize(records), encoding="utf-8")
    e = manifest["config"].get("evaluation", {})
    if e.get("models"):
        run_audit(read_jsonl(audit / "audit_blind.jsonl"), out / "auto",
                  e.get("endpoint", manifest["config"]["endpoint"]), e["models"],
                  key=read_jsonl(audit / "audit_key.jsonl"), k=e["k"], max_calls=e["max_calls"],
                  api_key_env=e.get("api_key_env", manifest["config"]["api_key_env"]), parameters=e["parameters"],
                  workers=e.get("workers", 1))
        print(out / "auto/auto_report.md")
        write_json(out / "evaluation_costs.json", summarize_costs(out / "auto/api_cache/requests.jsonl"))
    else:
        print("All planned generation slots attempted; automatic assessment not configured. Run experiment.autojudge separately when panel models are available.")
    print(json.dumps({"yield_targets": yields}, ensure_ascii=False))
    print(out / "records.jsonl")


if __name__ == "__main__":
    main()
