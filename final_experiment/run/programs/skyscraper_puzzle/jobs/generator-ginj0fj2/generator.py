import sys, json, itertools, random
from typing import List, Tuple, Dict, Any, Optional

# ---------------------------
# Skyscrapers (摩天楼) puzzle generator + solver (4x4)
# Output: JSON array of {problem, answer, explanation}
# Deterministic with random.Random(seed)
# ---------------------------

N = 4
DIGITS = list(range(1, N + 1))
ALL_ROWS = list(itertools.permutations(DIGITS, N))

def visible_count(seq: Tuple[int, ...]) -> int:
    """How many buildings visible from left along seq."""
    m = 0
    c = 0
    for x in seq:
        if x > m:
            m = x
            c += 1
    return c

def compute_clues(grid: List[List[int]]) -> Dict[str, List[int]]:
    """Compute edge clues from a full grid."""
    top = []
    bottom = []
    left = []
    right = []
    for c in range(N):
        col = [grid[r][c] for r in range(N)]
        top.append(visible_count(tuple(col)))
        bottom.append(visible_count(tuple(reversed(col))))
    for r in range(N):
        row = grid[r]
        left.append(visible_count(tuple(row)))
        right.append(visible_count(tuple(reversed(row))))
    return {"top": top, "bottom": bottom, "left": left, "right": right}

def format_clues_text(clues: Dict[str, List[int]], style: str, rng: random.Random) -> str:
    """
    Render clues in Chinese problem statement.
    style A: matrix-like
    style B: explicit lists
    style C: mixed (top/bottom lists, left/right per row)
    """
    top = clues["top"]
    bottom = clues["bottom"]
    left = clues["left"]
    right = clues["right"]

    if style == "A":
        # Matrix-like display similar to classic
        def rowline(vals):
            return "  ".join(str(v) for v in vals)

        lines = []
        lines.append("上边线索（从上往下看每列可见楼数）: " + rowline(top))
        lines.append("左/右线索在每行两侧，右侧为从右往左看的可见楼数。")
        lines.append("")
        # Build an ASCII board
        header = "      " + "   ".join(str(v) for v in top)
        lines.append(header)
        for r in range(N):
            lines.append(f"{left[r]}     " + "   ".join("X" for _ in range(N)) + f"   {right[r]}")
        footer = "      " + "   ".join(str(v) for v in bottom)
        lines.append(footer)
        return "\n".join(lines)

    if style == "B":
        return (
            "边缘线索如下（均为可见楼数）：\n"
            f"- 上(top): {top}\n"
            f"- 下(bottom): {bottom}\n"
            f"- 左(left): {left}\n"
            f"- 右(right): {right}\n"
        )

    # style C
    lines = []
    lines.append(f"上(top)每列线索: {top}")
    lines.append(f"下(bottom)每列线索: {bottom}")
    lines.append("每行线索（左->右 / 右->左）如下：")
    for r in range(N):
        lines.append(f"- 第{r+1}行: 左={left[r]}, 右={right[r]}")
    return "\n".join(lines)

def row_matches(row: Tuple[int, ...], left: int, right: int) -> bool:
    return visible_count(row) == left and visible_count(tuple(reversed(row))) == right

def col_matches(col: Tuple[int, ...], top: int, bottom: int) -> bool:
    return visible_count(col) == top and visible_count(tuple(reversed(col))) == bottom

def solve_skyscraper_4x4(clues: Dict[str, List[int]]) -> List[List[List[int]]]:
    """
    Solve 4x4 skyscraper with brute force + pruning.
    Returns list of all solutions (each a grid list of lists).
    """
    top = clues["top"]
    bottom = clues["bottom"]
    left = clues["left"]
    right = clues["right"]

    # Pre-filter possible rows by left/right clues
    row_candidates = []
    for r in range(N):
        cands = [row for row in ALL_ROWS if row_matches(row, left[r], right[r])]
        row_candidates.append(cands)
        if not cands:
            return []

    solutions = []
    # Backtracking with column uniqueness + partial column visibility pruning
    partial_cols = [[None]*N for _ in range(N)]  # will store values as we place rows

    def partial_visibility_possible(prefix: List[int], clue_from_top: int) -> bool:
        """
        Quick necessary condition for top clue given current prefix.
        For prefix, compute visible so far. Remaining can at most add (N-len(prefix)) more.
        Also at least visible_so_far (cannot decrease).
        """
        vis = visible_count(tuple(prefix))
        remaining = N - len(prefix)
        return (vis <= clue_from_top) and (vis + remaining >= clue_from_top)

    def partial_visibility_possible_from_bottom(suffix: List[int], clue_from_bottom: int) -> bool:
        vis = visible_count(tuple(suffix))
        remaining = N - len(suffix)
        return (vis <= clue_from_bottom) and (vis + remaining >= clue_from_bottom)

    def backtrack(r: int, grid_rows: List[Tuple[int, ...]]):
        if r == N:
            # check full columns top/bottom
            grid = [list(row) for row in grid_rows]
            for c in range(N):
                col = tuple(grid[i][c] for i in range(N))
                if not col_matches(col, top[c], bottom[c]):
                    return
            solutions.append(grid)
            return

        for row in row_candidates[r]:
            # column uniqueness check with previous rows
            ok = True
            for c in range(N):
                for rr in range(r):
                    if grid_rows[rr][c] == row[c]:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                continue

            # partial column visibility feasibility check (top and bottom)
            # Build current column prefix and suffix info
            for c in range(N):
                prefix = [grid_rows[i][c] for i in range(r)] + [row[c]]
                if not partial_visibility_possible(prefix, top[c]):
                    ok = False
                    break
                # for bottom, we can check suffix from bottom when enough rows placed:
                # use placed values as part of suffix if r is near bottom? not directly.
                # We'll do a necessary check on the suffix of placed rows if we imagine building from bottom:
                # Take values of already-placed rows in that column, but they correspond to top part.
                # A safe necessary check for bottom clue: consider known cells at bottom only if any.
                # We'll check when r reaches N-1 (last row), full check happens anyway.
            if not ok:
                continue

            grid_rows.append(row)
            backtrack(r + 1, grid_rows)
            grid_rows.pop()

    backtrack(0, [])
    return solutions

def random_latin_square_4(rng: random.Random) -> List[List[int]]:
    """
    Generate a 4x4 Latin square by permuting a base pattern.
    Start from cyclic Latin square and apply random row/col/number permutations.
    """
    base = [[(i + j) % N + 1 for j in range(N)] for i in range(N)]
    # permute symbols
    sym = DIGITS[:]
    rng.shuffle(sym)
    grid = [[sym[val-1] for val in row] for row in base]
    # permute rows and columns independently
    rows = list(range(N))
    cols = list(range(N))
    rng.shuffle(rows)
    rng.shuffle(cols)
    grid = [[grid[rows[i]][cols[j]] for j in range(N)] for i in range(N)]
    return grid

def puzzle_from_solution(solution: List[List[int]]) -> Dict[str, List[int]]:
    return compute_clues(solution)

def is_unique(clues: Dict[str, List[int]]) -> Tuple[bool, List[List[int]]]:
    sols = solve_skyscraper_4x4(clues)
    if len(sols) == 1:
        return True, sols[0]
    return False, (sols[0] if sols else None)

def make_explanation(clues: Dict[str, List[int]], sol: List[List[int]], rng: random.Random) -> str:
    """
    Provide brief, checkable explanation: show each row satisfies its left/right clues,
    each column satisfies top/bottom clues, and row/col uniqueness.
    """
    parts = []
    parts.append("解的校验要点（可逐项复核）：")
    # rows
    parts.append("1) 每行 1-4 不重复，且满足左右可见楼数：")
    for r in range(N):
        row = tuple(sol[r])
        lv = visible_count(row)
        rv = visible_count(tuple(reversed(row)))
        parts.append(f"   - 第{r+1}行 {list(row)}：左可见={lv}（线索{clues['left'][r]}），右可见={rv}（线索{clues['right'][r]}）")
    parts.append("2) 每列 1-4 不重复，且满足上下可见楼数：")
    for c in range(N):
        col = tuple(sol[r][c] for r in range(N))
        tv = visible_count(col)
        bv = visible_count(tuple(reversed(col)))
        parts.append(f"   - 第{c+1}列 {[col[r] for r in range(N)]}：上可见={tv}（线索{clues['top'][c]}），下可见={bv}（线索{clues['bottom'][c]}）")
    parts.append("因此该网格满足题面全部规则。")
    return "\n".join(parts)

def build_problem_text(clues: Dict[str, List[int]], style: str, rng: random.Random, lang: str="zh") -> str:
    assert lang == "zh"
    clue_text = format_clues_text(clues, style, rng)
    return (
        f"摩天楼谜题（{N}×{N}）：\n"
        f"- 在每个格子填入 1 到 {N} 的整数，表示摩天楼高度。\n"
        f"- 每行与每列的数字都不能重复。\n"
        f"- 边缘线索表示从该方向看进去能看到的楼数：更高的楼会挡住后面更矮的楼。\n\n"
        f"{clue_text}\n\n"
        f"任务：求出完整的 {N}×{N} 网格，并用 Python 的二维列表（列表的列表）形式输出。"
    )

def gen_one(rng: random.Random, seen: set, max_tries: int = 2000) -> Dict[str, Any]:
    styles = ["A", "B", "C"]
    for _ in range(max_tries):
        sol = random_latin_square_4(rng)
        clues = puzzle_from_solution(sol)

        # Ensure uniqueness
        uniq, canonical_sol = is_unique(clues)
        if not uniq:
            continue

        # Deduplicate by clue signature (problem uniqueness)
        sig = (tuple(clues["top"]), tuple(clues["bottom"]), tuple(clues["left"]), tuple(clues["right"]))
        if sig in seen:
            continue
        seen.add(sig)

        style = rng.choice(styles)
        problem = build_problem_text(clues, style, rng, lang="zh")
        explanation = make_explanation(clues, canonical_sol, rng)
        return {"problem": problem, "answer": canonical_sol, "explanation": explanation}

    raise RuntimeError("生成失败：在尝试次数上限内未能生成满足唯一解与去重条件的题目。")

def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data)
    except Exception as e:
        print(f"输入不是合法 JSON: {e}", file=sys.stderr)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))
    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    seen = set()
    out = []
    try:
        for _ in range(count):
            item = gen_one(rng, seen)
            # basic non-empty checks
            if not item["problem"] or item["answer"] is None:
                raise RuntimeError("内部错误：生成了空题面或空答案。")
            out.append(item)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()