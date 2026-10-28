import sys, json, random
from typing import List, Tuple, Dict, Any, Optional
from z3 import Solver, Int, Distinct, And, Or, Not, sat

# -----------------------------
# Star Battle (1 star per row/col/region) generator for n x n (here n=4 fixed by seed domain)
# Regions are labeled with letters; exactly 1 star per region; stars are non-adjacent (incl diagonals).
# Output asks: dictionary mapping each region label -> (row, col) 1-indexed, sorted by label.
# -----------------------------

def z3_solve_unique(grid: List[List[str]]) -> Tuple[Optional[Dict[str, Tuple[int,int]]], int]:
    """
    Solve and also determine uniqueness of the region->cell assignment.
    Return (solution_map, num_solutions_capped_at_2).
    solution_map uses 1-indexed coordinates.
    """
    n = len(grid)
    labels = sorted({grid[r][c] for r in range(n) for c in range(n)})
    # each label must appear at least once
    for lab in labels:
        if not any(grid[r][c] == lab for r in range(n) for c in range(n)):
            return None, 0

    # Variables: for each row r, pick a column col_r in [0, n-1] where the star is placed.
    col = [Int(f"col_{r}") for r in range(n)]
    s = Solver()
    for r in range(n):
        s.add(And(col[r] >= 0, col[r] < n))
    # exactly 1 per column
    s.add(Distinct(col))

    # adjacency constraints: no two stars adjacent (including diagonal)
    for r1 in range(n):
        for r2 in range(r1+1, n):
            dr = r2 - r1
            # adjacency only possible for dr in {0,1}; but dr>=1 here, so only dr==1 matters
            if dr == 1:
                s.add(Or(col[r1] - col[r2] >= 2, col[r2] - col[r1] >= 2))

    # region constraints: each region label exactly once.
    # For each label L, the chosen cells (r, col[r]) across rows must hit L exactly once.
    # Define for each row r whether its star is in label L via disjunction of possible columns.
    # Then sum==1. Use pseudo-boolean via Ors + counting with Int indicators.
    def in_label(r, lab):
        # returns a z3 Bool: grid[r][col[r]] == lab
        # implement as Or(col[r]==c for c where grid[r][c]==lab)
        cs = [c for c in range(n) if grid[r][c] == lab]
        if not cs:
            return False  # Python bool False, safe in constraints
        return Or([col[r] == c for c in cs])

    # count occurrences for each label == 1
    for lab in labels:
        indicators = []
        for r in range(n):
            b = in_label(r, lab)
            # If b is Python bool False, treat as 0 indicator
            if b is False:
                indicators.append(0)
            else:
                # convert Bool to Int 0/1
                v = Int(f"ind_{lab}_{r}")
                s.add(Or(And(b, v == 1), And(Not(b), v == 0)))
                indicators.append(v)
        s.add(sum(indicators) == 1)

    # Get first solution
    if s.check() != sat:
        return None, 0
    m = s.model()
    sol_cols = [m.evaluate(col[r]).as_long() for r in range(n)]

    # Build region->(row,col)
    sol_map: Dict[str, Tuple[int,int]] = {}
    for r in range(n):
        c = sol_cols[r]
        lab = grid[r][c]
        # uniqueness of region constraint ensures no duplicate label
        sol_map[lab] = (r+1, c+1)

    # Uniqueness check: block this exact assignment of (row->col) and see if another exists
    block = Or([col[r] != sol_cols[r] for r in range(n)])
    s.add(block)
    if s.check() == sat:
        return sol_map, 2
    return sol_map, 1


def pretty_grid(grid: List[List[str]]) -> str:
    # Render as JSON-like with double quotes to match seed style
    return "[\n" + ",\n".join("    " + json.dumps(row, ensure_ascii=False) for row in grid) + "\n]"


def all_partitions_of_4_into_4_parts(rng: random.Random) -> List[int]:
    # Random composition of 4 into 4 positive integers -> must be [1,1,1,1]
    # But region sizes can vary; we need 4 regions total, sizes sum 16; not this.
    return [1, 1, 1, 1]


def generate_grid_via_solution(rng: random.Random, n: int = 4, max_tries: int = 2000) -> List[List[str]]:
    """
    Construct a region-letter grid that admits a unique valid star placement.
    Strategy:
      1) Sample a star permutation col[r] with non-adjacency.
      2) Place 4 region labels A,B,C,D each assigned to exactly one star cell.
      3) Fill remaining cells with labels while ensuring each label appears >=1 and
         final puzzle has unique solution (checked by solver).
    """
    labels = ["A", "B", "C", "D"]
    assert n == 4

    def sample_star_cols():
        # sample permutation of 0..3 with adjacent-row column distance >=2
        cols = list(range(n))
        for _ in range(200):
            rng.shuffle(cols)
            ok = True
            for r in range(n-1):
                if abs(cols[r] - cols[r+1]) <= 1:
                    ok = False
                    break
            if ok:
                return cols
        return None

    for attempt in range(max_tries):
        cols = sample_star_cols()
        if cols is None:
            continue

        # base grid unknown
        grid = [[None for _ in range(n)] for _ in range(n)]
        star_cells = [(r, cols[r]) for r in range(n)]
        # Assign labels to star cells: bijection between labels and star cells
        perm_labels = labels[:]
        rng.shuffle(perm_labels)
        for lab, (r, c) in zip(perm_labels, star_cells):
            grid[r][c] = lab

        # Fill remaining cells with labels with some structure variability:
        # - Sometimes create a "band" or "patches" by biasing to neighbor labels.
        # - Ensure all labels present (already, via star cells).
        for r in range(n):
            for c in range(n):
                if grid[r][c] is not None:
                    continue
                # neighbor bias
                neighbor_labs = []
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    rr, cc = r+dr, c+dc
                    if 0 <= rr < n and 0 <= cc < n and grid[rr][cc] is not None:
                        neighbor_labs.append(grid[rr][cc])
                if neighbor_labs and rng.random() < 0.65:
                    lab = rng.choice(neighbor_labs)
                else:
                    lab = rng.choice(labels)
                grid[r][c] = lab

        # Occasionally mutate some cells to increase diversity
        if rng.random() < 0.5:
            k = rng.randint(1, 4)
            for _ in range(k):
                r = rng.randrange(n)
                c = rng.randrange(n)
                if (r, c) not in star_cells:
                    grid[r][c] = rng.choice(labels)

        # Check uniqueness
        sol, num = z3_solve_unique(grid)  # also verifies satisfiable
        if sol is None or num != 1:
            continue

        # Additional sanity: every label appears at least twice sometimes for variety
        counts = {lab: 0 for lab in labels}
        for r in range(n):
            for c in range(n):
                counts[grid[r][c]] += 1
        # Avoid extremely lopsided grids to keep puzzles reasonable
        if max(counts.values()) >= 13:
            continue

        return grid

    raise RuntimeError("在采样上限内未能生成具有唯一解的 4x4 分区星星题。")


def solve_and_explain(grid: List[List[str]], output_language: str = "zh") -> Tuple[Dict[str, Tuple[int,int]], str]:
    sol, num = z3_solve_unique(grid)
    if sol is None:
        raise RuntimeError("内部错误：生成的题目不可解。")
    if num != 1:
        raise RuntimeError("内部错误：生成的题目不是唯一解。")

    labels = sorted(sol.keys())
    # Build explanation with verifiable checks
    # Also include row/col star positions derived from sol for easier verification
    n = len(grid)
    stars = [sol[lab] for lab in labels]
    # For row-wise view:
    row_to_col = {}
    for lab, (r, c) in sol.items():
        row_to_col[r] = c
    row_list = [(r, row_to_col[r]) for r in sorted(row_to_col)]

    # adjacency verification text
    def adjacent(p, q):
        return max(abs(p[0]-q[0]), abs(p[1]-q[1])) == 1

    adj_pairs = []
    for i in range(len(stars)):
        for j in range(i+1, len(stars)):
            if adjacent(stars[i], stars[j]):
                adj_pairs.append((stars[i], stars[j]))

    # region check: each star lies in its label
    region_ok = all(grid[r-1][c-1] == lab for lab, (r,c) in sol.items())

    if output_language == "zh":
        expl = []
        expl.append("解的坐标采用 1-based（行,列）。")
        expl.append("按区域字母得到的星星位置为："
                    + ", ".join([f"{lab}:{sol[lab]}" for lab in labels]) + "。")
        expl.append("逐行恰好 1 颗星：各行星星列号分别为 "
                    + ", ".join([f"第{r}行→第{c}列" for r, c in row_list]) + "。")
        expl.append("逐列恰好 1 颗星：这些列号互不相同（形成一个 4 列的排列）。")
        expl.append("逐区域恰好 1 颗星：上面每个字母区域各出现一次，且每颗星都落在对应字母格内。"
                    + ("（已核对通过）" if region_ok else "（核对失败：这不应发生）"))
        if adj_pairs:
            expl.append("相邻性检查：发现存在相邻星星对：" + str(adj_pairs) + "（这不应发生）")
        else:
            expl.append("相邻性检查：任意两颗星的行列差不同时为 0/1，因此不存在横、竖或对角相邻。")
        return sol, "\n".join(expl)
    else:
        # fallback (still no external translation)
        expl = []
        expl.append("Coordinates are 1-based (row,col).")
        expl.append("Region-sorted stars: " + ", ".join([f"{lab}:{sol[lab]}" for lab in labels]) + ".")
        return sol, "\n".join(expl)


def make_problem_text(grid: List[List[str]], output_language: str = "zh") -> str:
    g = pretty_grid(grid)
    if output_language == "zh":
        return (
            "在这个分区的 4 x 4 网格中，每个分区用不同的字母标记。请放置星星，满足以下条件：\n"
            "1) 每行恰好有 1 颗星星；\n"
            "2) 每列恰好有 1 颗星星；\n"
            "3) 每个字母区域恰好有 1 颗星星；\n"
            "4) 任何两颗星星都不能相邻（包括对角线方向）。\n\n"
            "给定以下区域网格：\n\n"
            f"{g}\n\n"
            "请按字母顺序输出每个字母区域中星星的坐标 (行,列，均从 1 开始)。\n"
            "答案以字典形式返回，例如：{'A': (1,1), 'B': (3,2), ...}。\n"
        )
    else:
        return (
            "In this 4x4 partitioned grid, each region is marked by a letter. Place stars such that:\n"
            "1) Each row has exactly 1 star;\n"
            "2) Each column has exactly 1 star;\n"
            "3) Each lettered region has exactly 1 star;\n"
            "4) No two stars are adjacent (including diagonals).\n\n"
            "Region grid:\n\n"
            f"{g}\n\n"
            "Output the star coordinates (row,col, 1-based) for each region letter in alphabetical order as a dict.\n"
        )


def canonical_signature(grid: List[List[str]]) -> str:
    # Use the full grid serialization as signature to avoid duplicates
    return json.dumps(grid, ensure_ascii=False)


def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    # optional settings passed by outer harness
    output_language = data.get("output_language", "zh")

    rng = random.Random(seed)
    seen = set()
    out = []
    attempts = 0
    max_total_attempts = 20000

    while len(out) < count and attempts < max_total_attempts:
        attempts += 1
        try:
            grid = generate_grid_via_solution(rng, n=4, max_tries=200)
        except Exception as e:
            print(f"[stderr] 生成失败（attempt {attempts}）：{e}", file=sys.stderr)
            continue

        sig = canonical_signature(grid)
        if sig in seen:
            continue

        try:
            ans, expl = solve_and_explain(grid, output_language=output_language)
        except Exception as e:
            print(f"[stderr] 求解/校验失败：{e}", file=sys.stderr)
            continue

        seen.add(sig)
        out.append({
            "problem": make_problem_text(grid, output_language=output_language),
            "answer": {k: ans[k] for k in sorted(ans.keys())},
            "explanation": expl
        })

    if len(out) != count:
        raise RuntimeError(f"仅生成了 {len(out)}/{count} 题；请更换 seed 或减少 count。")

    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()