"""Generate fixed-width ASCII tables and inject them into the rebuttal docs.

Every table is plain ASCII (|, +, -) so it survives mail clients, PDF
conversion and terminal copy-paste.  Cell widths are computed with a
CJK-aware display width, so mixed zh/en rows still line up.

Usage:
    python3 tools/make_tables_ascii.py --check      # print tables + verify hashes
    python3 tools/make_tables_ascii.py --inject     # splice into *.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "final_experiment"


def dwidth(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def pad(text: str, width: int, align: str) -> str:
    gap = width - dwidth(text)
    if gap <= 0:
        return text
    if align == "r":
        return " " * gap + text
    if align == "c":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def table(header: list[str], rows: list[list[str]], aligns: str) -> str:
    ncols = len(header)
    widths = [
        max(dwidth(str(row[i])) for row in [header, *rows]) for i in range(ncols)
    ]
    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def line(row: list[str]) -> str:
        cells = [
            " " + pad(str(row[i]), widths[i], aligns[i]) + " " for i in range(ncols)
        ]
        return "|" + "|".join(cells) + "|"

    out = [border, line(header), border]
    for row in rows:
        if row[0] == "-":                       # rule between row groups
            out.append(border)
            continue
        out.append(line(row))
    out.append(border)
    return "\n".join(out)


# ---------------------------------------------------------------- tables

T1 = table(
    ["", "PF", "B2", "B1"],
    [
        ["valid items (of 480 slots)", "366 (76.3%)", "352 (73.3%)", "134 (27.9%)"],
        ["valid, >=3 dependent steps", "301 (62.7%)", "162 (33.8%)", "28 (5.8%)"],
        ["reasoning depth, mean (0-4)", "2.94", "2.34", "1.93"],
        ["median problem length (chars)", "692", "321", "297"],
        ["near-duplicate pairs @0.8", "3.0%", "24.9%", "6.2%"],
        ["generators represented", "284", "97", "97"],
        ["tokens per valid item", "1,227", "527", "4,571"],
    ],
    "lccc",
)

T1_FULL = table(
    ["", "PF", "B2", "B1"],
    [
        ["valid items (of 480 slots)", "366 (76.3%)", "352 (73.3%)", "134 (27.9%)"],
        ["valid, >=3 dependent steps", "301 (62.7%)", "162 (33.8%)", "28 (5.8%)"],
        ["valid, >=2 dependent steps", "355 (74.0%)", "276 (57.5%)", "89 (18.5%)"],
        ["reasoning depth, mean (0-4)", "2.94", "2.34", "1.93"],
        ["depth distribution 0/1/2/3/4", "0/11/54/246/55", "8/68/114/120/42", "2/43/61/19/9"],
        ["median problem length (chars)", "692", "321", "297"],
        ["near-duplicate pairs @0.8", "3.0%", "24.9%", "6.2%"],
        ["identical constraint-tag sets", "15.2%", "50.4%", "42.6%"],
        ["generators represented", "284", "97", "97"],
        ["seeds that produced no item", "0/97", "5/97", "0/97"],
        ["tokens per valid item", "1,227", "527", "4,571"],
    ],
    "lccc",
)

T2 = table(
    ["metric", "PF - B2", "W/T/L", "p", "PF - B1", "W/T/L", "p"],
    [
        ["validity (seed macro)", "+0.027 [-0.054, +0.114]", "31/24/42", "0.48",
         "+0.484 [+0.406, +0.556]", "77/12/8", "5.0e-14"],
        ["reasoning depth", "+0.605 [+0.432, +0.780]", "59/8/17", "4.9e-7",
         "+0.844 [+0.616, +1.075]", "36/1/7", "5.7e-6"],
        ["problem length (chars)", "+373 [+293, +459]", "80/0/12", "2.7e-12",
         "+435 [+367, +504]", "91/0/6", "2.8e-19"],
        ["near-duplicate @0.8", "-22.8 pp [-29.8, -16.5]", "0/36/56", "5.6e-16",
         "-0.7 pp [-2.4, +0.8]", "42/49/6", "1.2e-6"],
        ["identical reasoning-tag sets", "-20.1 pp [-27.2, -12.9]", "18/21/53", "9.7e-6",
         "-20.3 pp [-27.0, -13.6]", "16/22/59", "1.9e-6"],
        ["identical constraint-tag sets", "-34.6 pp [-41.8, -26.7]", "11/12/69", "2.9e-10",
         "-27.3 pp [-34.1, -20.7]", "12/11/74", "7.0e-11"],
        ["explanation (certificate) score", "-0.14 [-0.35, +0.07]", "24/17/43", "0.14",
         "-0.34 [-0.57, -0.11]", "11/9/24", "0.071"],
    ],
    "lrrrrrr",
)

T3 = table(
    ["", "PF", "B2", "B1"],
    [
        ["seeds with zero valid items (see T8)", "1", "13", "53"],
        ["seeds with >=3 of 5 valid", "80", "77", "25"],
        ["median valid items per seed (of 5)", "4", "4", "0"],
        ["items with no output at all", "0/480", "25/480", "1/480"],
        ["items judged invalid", "111 (23.1%)", "103 (21.5%)", "344 (71.7%)"],
        ["-", "", "", ""],
        ["  wrong canonical answer", "89", "71", "331"],
        ["  unsatisfiable as written", "15", "7", "113"],
        ["  ambiguous / under-specified", "34", "49", "46"],
        ["  missing constraint", "26", "41", "44"],
        ["  rendering defect", "3", "8", "4"],
        ["  other", "0", "3", "3"],
    ],
    "lrrr",
)

T4 = table(
    ["", "PF", "B2", "B1"],
    [
        ["near-duplicate @0.5 / 0.7 / 0.8", "18.4 / 7.4 / 3.0%", "70.4 / 46.4 / 24.9%",
         "35.8 / 16.8 / 6.2%"],
        ["seeds with >=50% near-duplicate pairs", "1/97", "21/92", "3/97"],
        ["seeds with 100% near-duplicate pairs", "1/97", "11/92", "2/97"],
        ["identical reasoning-tag sets (pair rate)", "33.1%", "54.4%", "53.9%"],
        ["identical constraint-tag sets (pair rate)", "15.2%", "50.4%", "42.6%"],
        ["distinct reasoning-tag sets per seed", "2.84", "2.05", "2.19"],
        ["distinct constraint-tag sets per seed", "3.88", "2.26", "2.60"],
    ],
    "lccc",
)

T5 = table(
    ["typical depth", "n (valid items)", "mean certificate score"],
    [
        ["0 steps", "10", "3.60"],
        ["1 step", "122", "3.73"],
        ["2 steps", "229", "3.69"],
        ["3 steps", "385", "3.22"],
        ["4 steps", "105", "2.19"],
    ],
    "lrr",
)

T6 = table(
    ["scale", "PF (mean spec)", "PF (median spec)", "B2", "B1"],
    [
        ["200 instances / unit", "1,227", "761", "49.9", "4,571"],
        ["20 instances / unit", "12,267", "7,611", "526.6", "4,571"],
        ["-", "", "", "", ""],
        ["spec tokens / seed", "~0.55M", "~0.34M", "7.7k", "25.5k"],
        ["spec tokens / generator", "187k", "116k", "-", "-"],
    ],
    "lrrrr",
)

T7 = table(
    ["stage", "requests", "prompt", "completion", "of which reasoning", "total", "USD"],
    [
        ["direct generation", "391", "1,519,200", "954,940", "0", "2,474,140", "14.97"],
        ["framework generation", "116", "336,295", "413,235", "0", "749,530", "6.10"],
        ["judge: solve", "1,421", "741,205", "2,092,446", "1,839,144", "2,833,651", "2.56"],
        ["judge: verdict", "1,474", "1,915,649", "1,598,368", "1,209,031", "3,514,017", "2.23"],
        ["-", "", "", "", "", "", ""],
        ["total", "3,402", "4,512,349", "5,058,989", "3,048,175", "9,571,338", "25.86"],
    ],
    "lrrrrrr",
)

T8 = table(
    ["artifact", "chars", "sha256 (first 16)", "used as"],
    [
        ["prompts/paper_v2/zh/direct.txt", "1,586", "26264280a10085d7", "B1"],
        ["prompts/paper_v2/zh/framework.txt", "2,077", "61ace6c3be2d6e2f", "B2"],
        ["prompts/paper_v2/en/direct.txt", "4,300", "0c92421f7a3c230f", "-"],
        ["prompts/paper_v2/en/framework.txt", "5,851", "ca7bda22252b107e", "-"],
        ["autojudge.py SOLVE_SYSTEM", "PENDING", "PENDING", "solver"],
        ["autojudge.py JUDGE_SYSTEM", "PENDING", "PENDING", "judge"],
    ],
    "lrrc",
)

T0 = table(
    ["field", "value"],
    [
        ["seeds", "97 (Chinese-language subset of the paper's 129)"],
        ["matched slots per seed", "4/6/8/12/14/16 (median 16); 1,284 per condition"],
        ["items blind-judged", "480 per condition; 5 per seed (4 for 5 seeds)"],
        ["generator", "gpt-5.2, max_completion_tokens=32768"],
        ["generators per seed", "PF 3-4 (129 x 4 = 516; 432 verified); B2/B1 1"],
        ["judge", "gpt-5.6-luna, k=1, max_completion_tokens=16384"],
        ["prompts", "paper_v2 / zh; one prompt per condition"],
        ["repair budget", "B1 3 repairs/batch; B2 3 attempts/seed"],
        ["decoding", "only max_completion_tokens is set"],
        ["sampling seed", "rng_seed 20261028 (slot order)"],
    ],
    "ll",
)

T9 = table(
    ["artifact", "count", "what it pins down"],
    [
        ["checksums.sha256", "11,564 files", "every archived byte"],
        ["run/manifest.json", "-", "config, prompt and input hashes"],
        ["run/seeds.json + reference.json", "97 / 1,720", "exact inputs used"],
        ["run/records_selected.jsonl", "5,164 rows", "all three conditions"],
        ["run/programs/", "97 dirs, 116 attempts", "every generator written"],
        ["run/traces/", "507", "every generation request/response"],
        ["run/audit/", "1,440 x2", "blind items + sealed key"],
        ["run/auto/model_labels.jsonl", "1,440", "per-item verdicts and tags"],
        ["run/tokens_requests.csv", "3,402 rows", "per-request token ledger"],
        ["run/tokens_summary.json", "-", "T6/T7 stage totals"],
        ["run/analysis/rebuttal_tests.json", "-", "paired statistics behind T1-T5"],
    ],
    "lrl",
)

F1 = table(
    ["id", "file", "shows", "table", "use"],
    [
        ["fig1", "fig1_validity", "valid fraction per condition, 95% CI", "T1", "main"],
        ["fig2", "fig2_per_seed", "per-seed validity, PF vs baseline scatter", "T2", "main"],
        ["fig3", "fig3_diversity", "near-dup rate vs threshold 0.3-0.9", "T4", "main"],
        ["fig3b", "fig3b_seed_ecdf", "ECDF of per-seed near-dup rate", "T4", "main"],
        ["fig4", "fig4_novelty", "novelty decay by item position", "T4", "supp"],
        ["fig5", "fig5_cost_pareto", "token spend by component, cumulative share", "T7", "supp"],
        ["fig6", "fig6_cost_per_question", "per generated vs per valid", "T6", "supp"],
        ["fig6b", "fig6b_pf_cost", "tokens per valid question, PF@200/@20", "T6", "main"],
        ["fig7", "fig7_depth_length", "depth and length distributions", "T1", "main"],
    ],
    "lllcc",
)

T11 = table(
    ["item", "expected", "observed"],
    [
        ["seeds", "97", "97"],
        ["matched slots per condition", "1,284", "1,284"],
        ["raw slots per condition", "1,940", "1,940"],
        ["records_selected.jsonl rows", "5,164", "5,164"],
        ["blind-judged items", "1,440", "1,440"],
        ["generation requests", "~485 + repairs", "507"],
        ["judge requests", "~2,880 + repairs", "2,895"],
        ["total tokens", "-", "9,571,338"],
        ["total cost", "-", "$25.86"],
    ],
    "lrr",
)


T8_GL = table(
    ["unit", "PF", "B2", "B1"],
    [
        ["judged units (generators)", "284", "97", "97"],
        ["unit-level validity, mean", "0.775", "0.774", "0.278"],
        ["units with zero valid items", "46/284 (16.2%)", "13/97 (13.4%)", "53/97 (54.6%)"],
        ["units with zero valid, >=2 judged", "17/141 (12.1%)", "-", "-"],
        ["-", "", "", ""],
        ["PF matched to one generator per seed", "", "", ""],
        ["  zero-valid seeds, mean [95% CI]", "14.0 [9, 19]", "13", "-"],
        ["  unit-level validity, mean", "0.773", "0.774", "-"],
        ["  valid, >=3 dependent steps", "63.8% [56.6, 70.5]", "33.8%", "-"],
    ],
    "lccc",
)

T9_VAR = table(
    ["PF generator variant", "judged", "valid", "validity", "depth mean", "valid >=3 steps", "median length"],
    [
        ["_0 (no expansion)", "113", "79", "0.699", "2.91", "63 (55.8%)", "711"],
        ["_1", "132", "99", "0.750", "2.96", "84 (63.6%)", "729"],
        ["_2", "131", "104", "0.794", "2.95", "84 (64.1%)", "590"],
        ["_3", "104", "84", "0.808", "2.94", "70 (67.3%)", "739"],
        ["-", "", "", "", "", "", ""],
        ["_1.._3 pooled", "367", "287", "0.782", "2.95", "238 (64.9%)", "687"],
    ],
    "lrrrrrr",
)

T10_LEN = table(
    ["comparison", "raw gap", "controlled gap [95% CI]", "n (PF / B2)"],
    [
        ["PF - B2: + log(length)", "+0.602", "+0.418 [+0.150, +0.702]", "366 / 352"],
        ["PF - B2: + log(length) + seed FE", "", "+0.382 [+0.149, +0.645]", "366 / 352"],
        ["B2 - B1: + log(length)", "+0.416", "+0.380 [+0.126, +0.634]", "352 / 134"],
        ["B2 - B1: + log(length) + seed FE", "", "+0.148 [+0.023, +0.267]", "352 / 134"],
        ["-", "", "", ""],
        ["strata [53, 303]", "+0.49", "", "21 / 159"],
        ["strata [303, 493]", "+0.18", "", "64 / 115"],
        ["strata [493, 759]", "+0.89", "", "129 / 50"],
        ["strata [759, 6085]", "+0.30", "", "152 / 28"],
    ],
    "lrrr",
)


T11_DIV = table(
    ["unit", "PF", "B2", "B1"],
    [
        ["near-dup @0.8, within unit", "13.2%", "24.9%", "6.2%"],
        ["  pairs", "1,918", "8,091", "8,413"],
        ["identical reasoning-tag sets", "46.1%", "56.8%", "53.7%"],
        ["identical constraint-tag sets", "30.2%", "53.1%", "42.4%"],
    ],
    "lccc",
)

TABLES = {
    "T1": T1,
    "T1_FULL": T1_FULL,
    "T2": T2,
    "T3": T3,
    "T4": T4,
    "T5": T5,
    "T6": T6,
    "T7": T7,
    "T8": T8,
    "F1": F1,
    "T0": T0,
    "T11": T11,
    "T9": T9,
    "T8_GL": T8_GL,
    "T9_VAR": T9_VAR,
    "T10_LEN": T10_LEN,
    "T11_DIV": T11_DIV,
}

TARGETS = [
    "rebuttal_response_zh.md",
    "rebuttal_response.md",
    "rebuttal_tables.md",
    "rebuttal_figures.md",
    "rebuttal_reproducibility.md",
]


def prompt_facts() -> dict[str, tuple[int, str]]:
    """Read the judge prompts out of autojudge.py and verify the recorded hash."""
    source = (ROOT / "experiment" / "autojudge.py").read_text(encoding="utf-8")
    ns: dict[str, object] = {}
    start = source.index('SOLVE_SYSTEM = """')
    end = source.index('"""', source.index('JUDGE_SYSTEM = """') + 20) + 3
    exec(compile(source[start:end], "<prompts>", "exec"), ns)  # noqa: S102
    solve = str(ns["SOLVE_SYSTEM"])
    judge = str(ns["JUDGE_SYSTEM"])
    digest = hashlib.sha256(
        json.dumps([solve, judge], sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()
    recorded = json.loads((FE / "run" / "auto" / "manifest.json").read_text(encoding="utf-8"))[
        "prompt_hash"
    ]
    assert digest == recorded, f"judge prompt hash mismatch: {digest} != {recorded}"
    return {
        "solve": (len(solve), hashlib.sha256(solve.encode()).hexdigest()[:16]),
        "judge": (len(judge), hashlib.sha256(judge.encode()).hexdigest()[:16]),
        "pair": digest,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--inject", action="store_true")
    args = parser.parse_args()

    facts = prompt_facts()
    t8 = table(
        ["artifact", "chars", "sha256 (first 16)", "used as"],
        [
            ["prompts/paper_v2/zh/direct.txt", "1,586", "26264280a10085d7", "B1"],
            ["prompts/paper_v2/zh/framework.txt", "2,077", "61ace6c3be2d6e2f", "B2"],
            ["prompts/paper_v2/en/direct.txt", "4,300", "0c92421f7a3c230f", "-"],
            ["prompts/paper_v2/en/framework.txt", "5,851", "ca7bda22252b107e", "-"],
            ["autojudge.py SOLVE_SYSTEM", f"{facts['solve'][0]:,}", facts["solve"][1], "solver"],
            ["autojudge.py JUDGE_SYSTEM", f"{facts['judge'][0]:,}", facts["judge"][1], "judge"],
        ],
        "lrrc",
    )
    TABLES["T8"] = t8

    if args.check:
        for name, block in TABLES.items():
            print(f"@@{name}")
            print(block)
            print()
        print(f"judge prompt pair hash: {facts['pair']} (verified against auto/manifest.json)")

    if args.inject:
        for name in TARGETS:
            path = ROOT / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")

            def repl(match: re.Match[str]) -> str:
                key = match.group(1)
                if key not in TABLES:
                    raise SystemExit(f"unknown table {key} in {name}")
                return "```\n" + TABLES[key] + "\n```"

            new = re.sub(r"<!--TABLE:([A-Z0-9_]+)-->", repl, text)
            if new != text:
                path.write_text(new, encoding="utf-8")
                print(f"injected: {name}")


if __name__ == "__main__":
    main()
