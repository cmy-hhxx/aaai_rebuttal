"""Offline lexical redundancy metrics; these do not measure reasoning diversity."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata
from typing import Any


def shingles(text: str) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+|[^\w\s]", unicodedata.normalize("NFKC", text).casefold())
    width = min(5, len(words))
    return {tuple(words[i:i + width]) for i in range(len(words) - width + 1)} if width else set()


def lexical_metrics(records: list[dict[str, Any]], threshold: float = .85) -> list[dict[str, Any]]:
    """Within-seed near duplicates, with the same frozen threshold for every arm."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row["status"] == "ok" and row["cohort"] == "matched":
            groups[(row["method"], row["seed_id"])].append(row)
    output = []
    for (method, seed), rows in sorted(groups.items()):
        sets = [shingles(r["problem"]) for r in rows]
        duplicated = set()
        for i, left in enumerate(sets):
            for j in range(i + 1, len(sets)):
                right = sets[j]
                union = len(left | right)
                if union and len(left & right) / union >= threshold:
                    duplicated.update((i, j))
        output.append({"method": method, "seed_id": seed, "n": len(rows),
                       "near_duplicate_items": len(duplicated),
                       "near_duplicate_rate": len(duplicated) / len(rows) if rows else None,
                       "threshold": threshold, "scope": "within-seed word/punctuation 5-gram Jaccard; lexical proxy only"})
    return output


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    rows = [json.loads(line) for line in a.data.read_text().splitlines() if line.strip()]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(lexical_metrics(rows), ensure_ascii=False, indent=2) + "\n")
    print(a.out)


if __name__ == "__main__":
    main()
