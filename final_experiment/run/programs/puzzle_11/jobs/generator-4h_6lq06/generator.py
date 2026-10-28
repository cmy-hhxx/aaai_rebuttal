import sys, json, random, itertools
from typing import List, Tuple, Dict, Any, Optional

# We generate and solve "fill X with given numbers, each used once, row/col sums match" puzzles.
# The last column provides row sums; the last row provides column sums (standard).
# Output language: Chinese by default; can be set by input's "output_language".

def to_json(obj):
    return json.dumps(obj, ensure_ascii=False)

def randint_distinct(rng: random.Random, pool: List[int], k: int) -> List[int]:
    return rng.sample(pool, k)

def format_grid_problem(grid: List[List[Optional[int]]], row_sums: List[int], col_sums: List[int], lang: str) -> str:
    r, c = len(grid), len(grid[0])
    # grid is r x c (without sums). We'll print with extra sums row/col.
    lines = []
    for i in range(r):
        row_cells = []
        for j in range(c):
            v = grid[i][j]
            row_cells.append("X" if v is None else str(v))
        row_cells.append(str(row_sums[i]))
        lines.append("  ".join(row_cells))
    # last line: col sums plus corner total as sum of row sums
    total = sum(row_sums)
    last = [str(s) for s in col_sums] + [str(total)]
    lines.append("  ".join(last))

    if lang == "en":
        instr = (
            "给定一个矩形网格，末列/末行给出每行/每列的目标和。用指定数字集合填入所有 X，"
            "每个数字只能用一次，使得每行每列之和都匹配。\n\n"
            "题目矩阵如下（X 表示空格）：\n"
        )
        # Even if 'en', we keep it bilingual? No; keep English:
        instr = (
            "A rectangular grid is given. The last number of each row is the row sum, "
            "and the last row gives the column sums. Replace each X with a number from the given set, "
            "each number used exactly once, so that all row/column sums match.\n\n"
            "Matrix (X are blanks):\n"
        )
        outfmt = (
            "\nFinal answer: list the filled grid (without the sums) from left to right, top to bottom; "
            "elements separated by a space, rows separated by commas. Wrap in double square brackets like [[...]]."
        )
        return instr + "\n".join(lines) + outfmt
    else:
        instr = (
            "给定一个矩形网格。每行末尾的数字是该行目标和；最后一行给出每列目标和。"
            "请用指定数字集合替换所有 X，且每个数字只能使用一次，使所有行/列之和都匹配。\n\n"
            "题目矩阵如下（X 表示空格）：\n"
        )
        outfmt = (
            "\n\n最终答案要求：按“从左到右、从上到下”的行顺序写出填好的网格（不含和那一行/列），"
            "同一行元素用空格分隔，不同行用英文逗号 , 分隔，并用双中括号包裹，例如 [[a b c,d e f]]。"
        )
        return instr + "\n".join(lines) + outfmt

def format_answer_grid(filled: List[List[int]]) -> str:
    rows = []
    for row in filled:
        rows.append(" ".join(str(x) for x in row))
    return "[[" + ",".join(rows) + "]]"

def solve_by_enumeration(grid: List[List[Optional[int]]],
                         row_sums: List[int],
                         col_sums: List[int],
                         numbers: List[int],
                         require_unique: bool = True,
                         limit_solutions: int = 2) -> Tuple[List[List[int]], int]:
    """
    Backtracking with pruning. Returns (one_solution, num_solutions_found up to limit_solutions).
    """
    r, c = len(grid), len(grid[0])
    # positions of blanks
    blanks = [(i, j) for i in range(r) for j in range(c) if grid[i][j] is None]
    # Precompute known sums per row/col
    known_row = [sum(grid[i][j] for j in range(c) if grid[i][j] is not None) for i in range(r)]
    known_col = [sum(grid[i][j] for i in range(r) if grid[i][j] is not None) for j in range(c)]
    # Remaining blanks per row/col
    rem_row = [sum(1 for j in range(c) if grid[i][j] is None) for i in range(r)]
    rem_col = [sum(1 for i in range(r) if grid[i][j] is None) for j in range(c)]

    # Order blanks by most constrained: row+col remaining small
    blanks.sort(key=lambda pos: (rem_row[pos[0]] + rem_col[pos[1]], rem_row[pos[0]], rem_col[pos[1]]))

    nums_set = set(numbers)
    used = set()
    sol = [[grid[i][j] if grid[i][j] is not None else 0 for j in range(c)] for i in range(r)]
    solutions = []

    # For pruning, keep running sums
    cur_row = known_row[:]
    cur_col = known_col[:]
    cur_rem_row = rem_row[:]
    cur_rem_col = rem_col[:]

    # For faster bounds, keep sorted remaining numbers each step by recomputing small lists (grid sizes are small).
    def feasible_bounds(target: int, current: int, k: int, remaining_nums: List[int]) -> bool:
        """Check if we can reach target from current by choosing k numbers from remaining."""
        if k == 0:
            return current == target
        if len(remaining_nums) < k:
            return False
        remaining_nums_sorted = sorted(remaining_nums)
        min_add = sum(remaining_nums_sorted[:k])
        max_add = sum(remaining_nums_sorted[-k:])
        return current + min_add <= target <= current + max_add

    def backtrack(idx: int):
        if len(solutions) >= limit_solutions:
            return
        if idx == len(blanks):
            # Verify all sums exact
            for i in range(r):
                if cur_row[i] != row_sums[i]:
                    return
            for j in range(c):
                if cur_col[j] != col_sums[j]:
                    return
            solutions.append([row[:] for row in sol])
            return

        i, j = blanks[idx]
        remaining_nums = [x for x in numbers if x not in used]

        # Additional pruning: check row/col bounds before trying values (based on remaining counts after filling this cell)
        # We'll try values in a heuristic order: those that move row/col closer.
        target_row = row_sums[i]
        target_col = col_sums[j]
        # sort by closeness
        remaining_nums.sort(key=lambda x: abs((cur_row[i] + x) - target_row) + abs((cur_col[j] + x) - target_col))

        for x in remaining_nums:
            # place x
            used.add(x)
            sol[i][j] = x
            cur_row[i] += x
            cur_col[j] += x
            cur_rem_row[i] -= 1
            cur_rem_col[j] -= 1

            # Prune: row/col sums cannot exceed targets
            if cur_row[i] <= row_sums[i] and cur_col[j] <= col_sums[j]:
                rem_after = [v for v in numbers if v not in used]
                ok = True

                # Bounds for this row and col
                if not feasible_bounds(row_sums[i], cur_row[i], cur_rem_row[i], rem_after):
                    ok = False
                if ok and not feasible_bounds(col_sums[j], cur_col[j], cur_rem_col[j], rem_after):
                    ok = False

                # Also check other rows/cols quickly (cheap): only those with few remaining blanks
                if ok:
                    # check rows
                    for rr in range(r):
                        if cur_rem_row[rr] >= 0:
                            if cur_row[rr] > row_sums[rr]:
                                ok = False
                                break
                            if not feasible_bounds(row_sums[rr], cur_row[rr], cur_rem_row[rr], rem_after):
                                ok = False
                                break
                    # check cols
                if ok:
                    for cc in range(c):
                        if cur_rem_col[cc] >= 0:
                            if cur_col[cc] > col_sums[cc]:
                                ok = False
                                break
                            if not feasible_bounds(col_sums[cc], cur_col[cc], cur_rem_col[cc], rem_after):
                                ok = False
                                break

                if ok:
                    backtrack(idx + 1)

            # undo
            cur_rem_row[i] += 1
            cur_rem_col[j] += 1
            cur_row[i] -= x
            cur_col[j] -= x
            sol[i][j] = 0
            used.remove(x)

    backtrack(0)
    if not solutions:
        raise ValueError("No solution found")
    return solutions[0], len(solutions)

def generate_instance(rng: random.Random) -> Dict[str, Any]:
    """
    Generate one puzzle instance with a guaranteed (typically unique) solution.
    We'll construct a full solution grid from a set of distinct numbers, then hide some cells.
    """
    # Choose grid size (without sums)
    size_choices = [(3, 4), (3, 5), (4, 4)]
    r, c = rng.choice(size_choices)

    # Choose number pool and pick r*c distinct numbers
    # Keep numbers moderate for human solving.
    pool = list(range(1, 26))
    nums = randint_distinct(rng, pool, r * c)

    # Construct full grid by shuffling
    rng.shuffle(nums)
    full = [nums[i * c:(i + 1) * c] for i in range(r)]

    row_sums = [sum(full[i]) for i in range(r)]
    col_sums = [sum(full[i][j] for i in range(r)) for j in range(c)]

    # Hide pattern: ensure at least 1 blank per row and per col, and not too many given.
    total_cells = r * c
    # target blanks ~ 40%-65%
    blanks_target = rng.randint(max(4, total_cells * 2 // 5), max(5, total_cells * 2 // 3))
    blanks_target = min(blanks_target, total_cells - (r + c))  # keep enough givens
    blanks_target = max(blanks_target, r + c)  # enough blanks to be meaningful

    positions = [(i, j) for i in range(r) for j in range(c)]
    rng.shuffle(positions)

    hidden = set()
    # First, guarantee at least one blank per row/col
    for i in range(r):
        j = rng.randrange(c)
        hidden.add((i, j))
    for j in range(c):
        i = rng.randrange(r)
        hidden.add((i, j))

    for (i, j) in positions:
        if len(hidden) >= blanks_target:
            break
        hidden.add((i, j))

    grid = [[None if (i, j) in hidden else full[i][j] for j in range(c)] for i in range(r)]

    # The "specified set of numbers" should be exactly the missing numbers (common in these puzzles).
    missing_numbers = [full[i][j] for i in range(r) for j in range(c) if grid[i][j] is None]
    missing_numbers_sorted = sorted(missing_numbers)

    # Validate by solving from public info; require uniqueness most of the time.
    sol, nsol = solve_by_enumeration(grid, row_sums, col_sums, missing_numbers_sorted, require_unique=False, limit_solutions=2)

    # Check that solution matches constructed full grid (it should) and uniqueness.
    ok_match = (sol == full)
    # If not matching, something wrong with our solve model (shouldn't happen); reject.
    if not ok_match:
        raise ValueError("Internal mismatch: solver solution != constructed grid")

    # Prefer unique solutions; if not unique, sometimes allow but then question would be ambiguous.
    # We'll enforce uniqueness.
    if nsol != 1:
        raise ValueError("Non-unique instance")

    # Build explanation with concrete checks
    # Provide: missing set, then show one row/col equation to illustrate.
    ex_lines = []
    ex_lines.append(f"缺失数字集合为：{', '.join(map(str, missing_numbers_sorted))}（每个只用一次）。")
    # Pick a row and col with at least 2 blanks if possible to show computation.
    row_blank_counts = [sum(1 for j in range(c) if grid[i][j] is None) for i in range(r)]
    col_blank_counts = [sum(1 for i in range(r) if grid[i][j] is None) for j in range(c)]
    ri = max(range(r), key=lambda i: row_blank_counts[i])
    cj = max(range(c), key=lambda j: col_blank_counts[j])
    # Show equation for that row and column using the final solution.
    row_expr = " + ".join(str(sol[ri][j]) for j in range(c))
    col_expr = " + ".join(str(sol[i][cj]) for i in range(r))
    ex_lines.append(f"例如第 {ri+1} 行：{row_expr} = {row_sums[ri]}。")
    ex_lines.append(f"例如第 {cj+1} 列：{col_expr} = {col_sums[cj]}。")
    ex_lines.append("按相同方式可核对所有行、列的目标和都满足，因此填法唯一。")

    return {
        "r": r, "c": c,
        "grid": grid,
        "row_sums": row_sums,
        "col_sums": col_sums,
        "missing_numbers": missing_numbers_sorted,
        "solution": sol,
        "explanation": "\n".join(ex_lines),
    }

def canonical_signature(inst: Dict[str, Any]) -> str:
    # Signature to avoid duplicates: structure + givens positions + sums + missing set
    grid = inst["grid"]
    r, c = inst["r"], inst["c"]
    giv = []
    for i in range(r):
        for j in range(c):
            giv.append("X" if grid[i][j] is None else str(grid[i][j]))
    sig = f"{r}x{c}|" + ",".join(giv) + "|R" + ",".join(map(str, inst["row_sums"])) + "|C" + ",".join(map(str, inst["col_sums"])) + "|M" + ",".join(map(str, inst["missing_numbers"]))
    return sig

def make_problem_object(inst: Dict[str, Any], lang: str) -> Dict[str, Any]:
    problem = format_grid_problem(inst["grid"], inst["row_sums"], inst["col_sums"], lang)
    answer = format_answer_grid(inst["solution"])
    return {
        "problem": problem,
        "answer": answer,
        "explanation": inst["explanation"] if lang != "en" else inst["explanation"],  # explanation already Chinese; acceptable per default
    }

def main():
    raw = sys.stdin.read()
    try:
        inp = json.loads(raw)
    except Exception as e:
        print(f"Failed to parse JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    seed = int(inp.get("seed", 0))
    count = int(inp.get("count", 1))
    lang = inp.get("output_language", "zh")
    rng = random.Random(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            inst = generate_instance(rng)
            sig = canonical_signature(inst)
            if sig in seen:
                continue
            seen.add(sig)
            results.append(make_problem_object(inst, lang))
        except Exception:
            # resample
            continue

    if len(results) < count:
        print(f"Generation failed: only generated {len(results)}/{count} within {attempts} attempts.", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(to_json(results))

if __name__ == "__main__":
    main()