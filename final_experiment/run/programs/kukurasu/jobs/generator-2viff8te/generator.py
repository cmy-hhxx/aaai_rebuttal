import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

# We generate Kukurasu puzzles (n x n).
# Rules (standard):
# - Each cell is either "1" (selected) or "X" (empty).
# - Row i constraint: sum of column indices (1..n) where cell (i,j) is 1 equals row_sum[i].
# - Column j constraint: sum of row indices (1..n) where cell (i,j) is 1 equals col_sum[j].
#
# We must output problem text (zh), answer grid (list of lists of "1"/"X"), and a brief, checkable explanation.

# --------------------- Utility: subset sums for rows/cols ---------------------

def all_row_patterns(n: int) -> Dict[int, List[int]]:
    """
    For given n, enumerate all 2^n bitmasks for a row.
    Weight of selecting column j is (j+1).
    Return dict: sum -> list of masks achieving it.
    """
    d: Dict[int, List[int]] = {}
    for mask in range(1 << n):
        s = 0
        for j in range(n):
            if (mask >> j) & 1:
                s += (j + 1)
        d.setdefault(s, []).append(mask)
    return d

def all_col_patterns(n: int) -> Dict[int, List[int]]:
    """
    For columns, weight of selecting row i is (i+1).
    But a column is also length n; sum is computed by selected row indices.
    So it's identical mapping as row patterns for n.
    """
    return all_row_patterns(n)

def mask_to_row(mask: int, n: int) -> List[str]:
    return ["1" if ((mask >> j) & 1) else "X" for j in range(n)]

def transpose_grid(grid: List[List[str]]) -> List[List[str]]:
    return [list(row) for row in zip(*grid)]

def compute_row_sums(grid: List[List[str]]) -> List[int]:
    n = len(grid)
    rs = []
    for i in range(n):
        s = 0
        for j in range(n):
            if grid[i][j] == "1":
                s += (j + 1)
        rs.append(s)
    return rs

def compute_col_sums(grid: List[List[str]]) -> List[int]:
    n = len(grid)
    cs = []
    for j in range(n):
        s = 0
        for i in range(n):
            if grid[i][j] == "1":
                s += (i + 1)
        cs.append(s)
    return cs

# --------------------- Exact solver (enumeration with pruning) ---------------------

def solve_kukurasu(n: int, row_sums: List[int], col_sums: List[int], limit: int = 2) -> List[List[List[str]]]:
    """
    Enumerate solutions up to 'limit'. Returns list of grids.
    Use row-mask backtracking with incremental column sum tracking.
    """
    row_map = all_row_patterns(n)
    # Candidate masks per row based on row sum
    candidates: List[List[int]] = []
    for s in row_sums:
        if s not in row_map:
            return []
        candidates.append(row_map[s][:])

    # Heuristic: order rows by fewest candidates
    order = sorted(range(n), key=lambda i: len(candidates[i]))
    inv_order = [0]*n
    for pos, i in enumerate(order):
        inv_order[i] = pos

    # We'll assign masks in this order and build actual row positions later.
    col_acc = [0]*n  # current column sums accumulated (weights are row indices of selected cells)
    assigned_masks = [None]*n  # in original row index
    solutions: List[List[List[str]]] = []

    # For pruning, we need to know remaining possible contribution to each column from remaining rows.
    # Simple bounds: for each remaining row r and column j, contribution is either 0 or (r+1).
    # So min remaining is 0, max remaining is sum of (r+1) over remaining rows. This is loose but effective.
    remaining_rows_by_pos = [order[pos:] for pos in range(n+1)]
    remaining_weight_sums_by_pos = []
    for pos in range(n+1):
        rem = remaining_rows_by_pos[pos]
        total = sum((r+1) for r in rem)
        remaining_weight_sums_by_pos.append(total)

    def feasible_bounds(pos: int) -> bool:
        # After assigning first pos rows in 'order', remaining weight sum total applies per column as max.
        max_add = remaining_weight_sums_by_pos[pos]
        for j in range(n):
            if col_acc[j] > col_sums[j]:
                return False
            if col_acc[j] + max_add < col_sums[j]:
                return False
        return True

    def dfs(pos: int):
        nonlocal solutions
        if len(solutions) >= limit:
            return
        if not feasible_bounds(pos):
            return
        if pos == n:
            if col_acc == col_sums:
                # Build grid in original row order
                grid = []
                for i in range(n):
                    grid.append(mask_to_row(assigned_masks[i], n))
                solutions.append(grid)
            return

        r = order[pos]  # original row index
        for mask in candidates[r]:
            # apply mask: for each column selected add (r+1) to column sum
            changed = []
            w = r + 1
            ok = True
            for j in range(n):
                if (mask >> j) & 1:
                    col_acc[j] += w
                    changed.append(j)
                    if col_acc[j] > col_sums[j]:
                        ok = False
                        break
            if ok:
                assigned_masks[r] = mask
                dfs(pos + 1)
                assigned_masks[r] = None
            # rollback
            for j in changed:
                col_acc[j] -= w
            if len(solutions) >= limit:
                return

    dfs(0)
    return solutions

# --------------------- Generator: construct instance with unique solution ---------------------

def gen_instance(rng: random.Random) -> Tuple[int, List[int], List[int], List[List[str]]]:
    """
    Create a Kukurasu instance (n,row_sums,col_sums,solution_grid) with unique solution.
    We sample a random solution grid then compute sums, then verify uniqueness.
    """
    # choose n and density
    # keep n moderate to allow uniqueness checking by enumeration
    n_choices = [4, 5, 6]
    n = rng.choice(n_choices)

    # sample random grid by picking each cell with some probability
    # adjust probability to avoid trivial all-X or all-1
    p = rng.uniform(0.25, 0.6)

    # resample until good uniqueness
    for _ in range(400):
        grid = []
        ones = 0
        for i in range(n):
            row = []
            for j in range(n):
                v = "1" if (rng.random() < p) else "X"
                if v == "1":
                    ones += 1
                row.append(v)
            grid.append(row)

        # avoid too sparse/dense
        if ones < n - 1 or ones > n * n - (n - 1):
            continue

        row_sums = compute_row_sums(grid)
        col_sums = compute_col_sums(grid)

        # quick feasibility: each sum must be achievable by subset of 1..n
        row_map = all_row_patterns(n)
        if any(s not in row_map for s in row_sums):
            continue
        if any(s not in row_map for s in col_sums):
            continue

        sols = solve_kukurasu(n, row_sums, col_sums, limit=2)
        if len(sols) == 1:
            # ensure the unique solution equals our constructed grid (it should, but confirm)
            if sols[0] == grid:
                return n, row_sums, col_sums, grid
            else:
                # still a valid unique puzzle; return the solver's unique grid and sums
                return n, row_sums, col_sums, sols[0]

    raise RuntimeError("在采样上限内未能生成具有唯一解的 Kukurasu 实例。请更换 seed。")

# --------------------- Rendering (Chinese) ---------------------

def render_problem_zh(n: int, row_sums: List[int], col_sums: List[int]) -> str:
    # Create a blank grid display with row/col constraints
    header = "请解一个 {n}×{n} 的 Kukurasu 谜题。你需要把每个格子填成“1”或“X”。\n".format(n=n)
    rules = (
        "规则：\n"
        "1) 每个单元格只能是“1”或“X”。\n"
        "2) 第 i 行的加权和：该行中所有“1”所在列号之和（列号从 1 到 {n}）。\n"
        "3) 第 j 列的加权和：该列中所有“1”所在行号之和（行号从 1 到 {n}）。\n"
        "4) 每行/每列的加权和必须分别等于给定约束。\n"
    ).format(n=n)

    # grid template
    lines = []
    for i in range(n):
        row = "  ".join(["X"] * n)
        lines.append(f"{row}  |  {row_sums[i]}")
    sep = "-" * (3 * n + 6)
    bottom = "  ".join(str(x) for x in col_sums)

    statement = (
        "初始网格（所有格子未知，用 X 占位）：\n"
        + "\n".join(lines) + "\n"
        + sep + "\n"
        + " " + bottom + "\n\n"
        + f"row_sums = {row_sums}\n"
        + f"col_sums = {col_sums}\n\n"
        "任务：\n"
        " - 在网格中把部分 X 改成 1，使所有行/列约束都满足。\n"
        " - 输出完成后的网格，格式为二维列表（列表的列表），元素为字符串 \"1\" 或 \"X\"。\n"
    )
    return header + rules + statement

def explanation_zh(n: int, grid: List[List[str]], row_sums: List[int], col_sums: List[int]) -> str:
    # Provide checkable verification: list selected positions per row and per col and show sums.
    parts = []
    parts.append("校验方法：对每一行把所有“1”所在列号相加；对每一列把所有“1”所在行号相加。")
    parts.append("逐行：")
    for i in range(n):
        cols = [j+1 for j in range(n) if grid[i][j] == "1"]
        s = sum(cols)
        parts.append(f" - 第{i+1}行 1 的列号 = {cols}，和 = {s}（应为 {row_sums[i]}）")
    parts.append("逐列：")
    for j in range(n):
        rows = [i+1 for i in range(n) if grid[i][j] == "1"]
        s = sum(rows)
        parts.append(f" - 第{j+1}列 1 的行号 = {rows}，和 = {s}（应为 {col_sums[j]}）")
    parts.append("以上行列加权和均与约束一致。")
    return "\n".join(parts)

# --------------------- Main ---------------------

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])

    rng = random.Random(seed)

    out = []
    seen = set()

    # bounded attempts to avoid infinite loops
    attempts = 0
    max_attempts = 2000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            n, row_sums, col_sums, sol = gen_instance(rng)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            break

        # de-duplicate by (n, row_sums, col_sums)
        key = (n, tuple(row_sums), tuple(col_sums))
        if key in seen:
            continue
        seen.add(key)

        # final safety: verify solution satisfies constraints and is unique
        if compute_row_sums(sol) != row_sums or compute_col_sums(sol) != col_sums:
            print("内部错误：解与约束不一致。", file=sys.stderr)
            continue
        sols = solve_kukurasu(n, row_sums, col_sums, limit=2)
        if len(sols) != 1 or sols[0] != sol:
            print("内部错误：唯一性校验失败。", file=sys.stderr)
            continue

        problem = render_problem_zh(n, row_sums, col_sums)
        answer = sol
        explanation = explanation_zh(n, sol, row_sums, col_sums)

        out.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    if len(out) != count:
        print(f"生成数量不足：目标 {count}，实际 {len(out)}。可尝试更换 seed。", file=sys.stderr)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()