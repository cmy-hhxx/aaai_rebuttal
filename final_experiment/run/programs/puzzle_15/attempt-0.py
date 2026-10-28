import sys, json, random
from typing import List, Tuple, Optional, Dict, Any

# We generate Sudoku puzzles (9x9) with X as blanks, and output solved grid as answer
# along with a short, checkable explanation in Chinese.
#
# Key requirements implemented:
# - Deterministic with random.Random(seed)
# - No network/files/subprocess
# - Generates diverse instances (different completed grids + different masking patterns)
# - Ensures uniqueness of solution by solving with a backtracking solver that can count solutions (up to 2)
# - Cross-check: validates solution satisfies all Sudoku constraints and matches givens

DIGITS = "123456789"

def deep_copy_grid(g: List[List[int]]) -> List[List[int]]:
    return [row[:] for row in g]

def grid_to_problem_text(grid: List[List[int]], blanks: List[List[bool]]) -> str:
    # Render as 9 lines with spaces between entries, X for blank
    lines = []
    for r in range(9):
        row = []
        for c in range(9):
            row.append("X" if blanks[r][c] else str(grid[r][c]))
        lines.append(" ".join(row))
    return "\n".join(lines)

def solution_to_answer_format(sol: List[List[int]]) -> str:
    # [[r1...,r2...,...]]
    rows = []
    for r in range(9):
        rows.append(" ".join(str(sol[r][c]) for c in range(9)))
    return "[[" + ",".join(rows) + "]]"

def check_valid_solution(sol: List[List[int]]) -> bool:
    # rows
    for r in range(9):
        if sorted(sol[r]) != list(range(1,10)):
            return False
    # cols
    for c in range(9):
        col = [sol[r][c] for r in range(9)]
        if sorted(col) != list(range(1,10)):
            return False
    # blocks
    for br in range(0,9,3):
        for bc in range(0,9,3):
            blk = []
            for r in range(br, br+3):
                for c in range(bc, bc+3):
                    blk.append(sol[r][c])
            if sorted(blk) != list(range(1,10)):
                return False
    return True

def solve_count_solutions(givens: List[List[int]], limit: int = 2) -> Tuple[int, Optional[List[List[int]]]]:
    # Backtracking with MRV. counts solutions up to limit.
    grid = deep_copy_grid(givens)

    rows_used = [set() for _ in range(9)]
    cols_used = [set() for _ in range(9)]
    blks_used = [set() for _ in range(9)]

    def blk_id(r, c): return (r//3)*3 + (c//3)

    # init
    for r in range(9):
        for c in range(9):
            v = grid[r][c]
            if v != 0:
                if (v in rows_used[r]) or (v in cols_used[c]) or (v in blks_used[blk_id(r,c)]):
                    return 0, None
                rows_used[r].add(v)
                cols_used[c].add(v)
                blks_used[blk_id(r,c)].add(v)

    # Precompute empties
    empties = [(r,c) for r in range(9) for c in range(9) if grid[r][c] == 0]

    def candidates(r, c):
        used = rows_used[r] | cols_used[c] | blks_used[blk_id(r,c)]
        return [v for v in range(1,10) if v not in used]

    # choose next by MRV
    def pick_unassigned():
        best = None
        best_cands = None
        for (r,c) in empties:
            if grid[r][c] != 0:
                continue
            cands = candidates(r,c)
            if len(cands) == 0:
                return (r,c), []
            if best is None or len(cands) < len(best_cands):
                best = (r,c)
                best_cands = cands
                if len(best_cands) == 1:
                    break
        return best, best_cands

    sol_found = None
    count = 0

    def dfs():
        nonlocal count, sol_found
        if count >= limit:
            return
        pos, cands = pick_unassigned()
        if pos is None:
            # solved
            count += 1
            if sol_found is None:
                sol_found = deep_copy_grid(grid)
            return
        r,c = pos
        if len(cands) == 0:
            return
        b = blk_id(r,c)
        for v in cands:
            grid[r][c] = v
            rows_used[r].add(v); cols_used[c].add(v); blks_used[b].add(v)
            dfs()
            rows_used[r].remove(v); cols_used[c].remove(v); blks_used[b].remove(v)
            grid[r][c] = 0
            if count >= limit:
                return

    dfs()
    return count, sol_found

def random_complete_sudoku(rng: random.Random) -> List[List[int]]:
    # Build a full valid grid by randomized backtracking from empty.
    grid = [[0]*9 for _ in range(9)]
    rows_used = [set() for _ in range(9)]
    cols_used = [set() for _ in range(9)]
    blks_used = [set() for _ in range(9)]

    def blk_id(r, c): return (r//3)*3 + (c//3)

    # random fill order with symmetry: shuffle positions
    positions = [(r,c) for r in range(9) for c in range(9)]
    # A fixed ordering tends to be slow; use an order that spreads constraints:
    # interleave blocks
    block_positions = []
    for br in range(0,9,3):
        for bc in range(0,9,3):
            cells = [(r,c) for r in range(br, br+3) for c in range(bc, bc+3)]
            rng.shuffle(cells)
            block_positions.extend(cells)
    positions = block_positions

    def candidates(r,c):
        used = rows_used[r] | cols_used[c] | blks_used[blk_id(r,c)]
        cand = [v for v in range(1,10) if v not in used]
        rng.shuffle(cand)
        return cand

    def pick_next():
        # MRV among unfilled cells for speed
        best = None
        best_cands = None
        for (r,c) in positions:
            if grid[r][c] != 0:
                continue
            cands = candidates(r,c)
            if len(cands) == 0:
                return (r,c), []
            if best is None or len(cands) < len(best_cands):
                best = (r,c); best_cands = cands
                if len(best_cands) == 1:
                    break
        return best, best_cands

    def dfs():
        pos, cands = pick_next()
        if pos is None:
            return True
        r,c = pos
        if not cands:
            return False
        b = blk_id(r,c)
        for v in cands:
            grid[r][c] = v
            rows_used[r].add(v); cols_used[c].add(v); blks_used[b].add(v)
            if dfs():
                return True
            rows_used[r].remove(v); cols_used[c].remove(v); blks_used[b].remove(v)
            grid[r][c] = 0
        return False

    ok = dfs()
    if not ok:
        raise RuntimeError("生成完整数独失败（回溯未找到解）。")
    return grid

def make_puzzle_from_solution(rng: random.Random, sol: List[List[int]],
                             min_givens: int, max_givens: int) -> Tuple[List[List[int]], List[List[bool]]]:
    # Start with full grid as givens, remove cells while keeping unique solution.
    givens = deep_copy_grid(sol)
    blanks = [[False]*9 for _ in range(9)]

    # Choose a target number of givens
    target = rng.randint(min_givens, max_givens)
    # Removal order: consider symmetry pairs sometimes
    cells = [(r,c) for r in range(9) for c in range(9)]
    rng.shuffle(cells)

    def current_givens_count():
        return sum(1 for r in range(9) for c in range(9) if givens[r][c] != 0)

    # Attempt removals with a cap
    attempts = 0
    max_attempts = 400
    i = 0
    while current_givens_count() > target and attempts < max_attempts and i < len(cells):
        r,c = cells[i]
        i += 1
        if givens[r][c] == 0:
            continue

        # sometimes remove symmetrically to diversify styles
        do_sym = rng.random() < 0.55
        r2, c2 = (8 - r, 8 - c) if do_sym else (r, c)

        saved1 = givens[r][c]
        saved2 = givens[r2][c2]

        givens[r][c] = 0
        if (r2, c2) != (r, c):
            givens[r2][c2] = 0

        # Check uniqueness
        cnt, _ = solve_count_solutions(givens, limit=2)
        if cnt != 1:
            # revert
            givens[r][c] = saved1
            if (r2, c2) != (r, c):
                givens[r2][c2] = saved2
            attempts += 1
            continue

        # accept removal
        attempts += 1

    # Build blanks matrix
    for r in range(9):
        for c in range(9):
            blanks[r][c] = (givens[r][c] == 0)

    return givens, blanks

def render_problem_zh(givens: List[List[int]]) -> str:
    # Problem statement in Chinese, self-contained.
    grid_lines = []
    for r in range(9):
        row = []
        for c in range(9):
            row.append("X" if givens[r][c] == 0 else str(givens[r][c]))
        grid_lines.append(" ".join(row))
    grid_text = "\n".join(grid_lines)

    return (
        "请解一个数独（9×9）。规则：\n"
        "1）每一行必须包含 1 到 9 且不重复；\n"
        "2）每一列必须包含 1 到 9 且不重复；\n"
        "3）每个 3×3 宫（共 9 个）必须包含 1 到 9 且不重复；\n"
        "题面用矩阵给出，空格用 X 表示。\n\n"
        "题目：\n"
        f"{grid_text}\n\n"
        "请按“从左到右、从上到下”的顺序输出每个元素；同一行元素用空格分隔，行与行之间用逗号分隔；"
        "并确保最终答案用双层方括号包裹。\n"
        "例如：[[A B C,D E F,G H I]]"
    )

def explanation_zh(givens: List[List[int]], sol: List[List[int]]) -> str:
    # Provide a short, checkable verification evidence:
    # - list number of givens
    # - show that the final grid matches all givens
    # - show one row/col/block as sample + mention all checked programmatically
    giv_cnt = sum(1 for r in range(9) for c in range(9) if givens[r][c] != 0)

    # pick a random row/col/block to cite (but deterministic from givens via hash-like sum)
    s = sum((r+1)*17*(c+1)*givens[r][c] for r in range(9) for c in range(9))
    rr = s % 9
    cc = (s // 9) % 9
    br = (s // 81) % 3
    bc = (s // 243) % 3
    br *= 3; bc *= 3

    row_vals = sol[rr]
    col_vals = [sol[r][cc] for r in range(9)]
    blk_vals = [sol[r][c] for r in range(br, br+3) for c in range(bc, bc+3)]

    # check givens match
    mismatch = []
    for r in range(9):
        for c in range(9):
            if givens[r][c] != 0 and givens[r][c] != sol[r][c]:
                mismatch.append((r,c,givens[r][c],sol[r][c]))
    ok_match = (len(mismatch) == 0)

    return (
        f"已给出数字数量：{giv_cnt}。\n"
        f"校验1（与题面一致）：所有非 X 位置在答案中保持相同数值：{'是' if ok_match else '否'}。\n"
        f"校验2（示例行）：第 {rr+1} 行为 {row_vals}，包含 1-9 各一次。\n"
        f"校验3（示例列）：第 {cc+1} 列为 {col_vals}，包含 1-9 各一次。\n"
        f"校验4（示例宫）：左上角坐标为({br+1},{bc+1}) 的 3×3 宫为 {blk_vals}，包含 1-9 各一次。\n"
        "其余行/列/九宫格同理；程序已逐项检查整盘满足数独三大约束。"
    )

def generate_one(rng: random.Random) -> Dict[str, Any]:
    # Difficulty variety by givens range
    # Ensure uniqueness.
    mode = rng.random()
    if mode < 0.34:
        min_g, max_g = 26, 32
    elif mode < 0.72:
        min_g, max_g = 33, 40
    else:
        min_g, max_g = 41, 50

    # generate solution
    sol = random_complete_sudoku(rng)

    # make puzzle
    givens, _ = make_puzzle_from_solution(rng, sol, min_g, max_g)

    # verify uniqueness and correctness
    cnt, found = solve_count_solutions(givens, limit=2)
    if cnt != 1 or found is None:
        raise RuntimeError("唯一解校验失败：生成的题目不是唯一解。")
    if not check_valid_solution(found):
        raise RuntimeError("解合法性校验失败：求得解不满足数独约束。")
    # Ensure found equals original sol (not strictly necessary, but a strong sanity check)
    if found != sol:
        # This can happen if sol differs but still fits givens uniquely; however uniqueness implies same.
        # If mismatch, keep found as the canonical answer.
        sol = found

    # Ensure givens consistent with sol
    for r in range(9):
        for c in range(9):
            if givens[r][c] != 0 and givens[r][c] != sol[r][c]:
                raise RuntimeError("题面与答案不一致（内部错误）。")

    problem = render_problem_zh(givens)
    answer = solution_to_answer_format(sol)
    expl = explanation_zh(givens, sol)
    return {"problem": problem, "answer": answer, "explanation": expl}

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results = []
    seen = set()
    # bounded resampling
    max_tries = count * 30
    tries = 0
    while len(results) < count and tries < max_tries:
        tries += 1
        try:
            item = generate_one(rng)
        except Exception as e:
            print(f"[stderr] 生成失败，重试：{e}", file=sys.stderr)
            continue

        # de-dup by problem text
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    if len(results) != count:
        raise RuntimeError(f"在尝试 {tries} 次后仅生成 {len(results)}/{count} 道题，未达标。")

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()