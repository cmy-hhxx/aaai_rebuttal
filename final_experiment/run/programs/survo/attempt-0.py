import sys, json, random
from typing import List, Tuple, Optional, Dict, Any

# We generate Survo puzzles (sum rows/cols with missing X cells) with a given multiset of numbers.
# Ensure: self-contained, solvable, and (by enumeration) unique solution for the asked fill-ins.

def make_rng(seed: int) -> random.Random:
    return random.Random(seed)

def fmt_matrix(mat: List[List[Any]]) -> str:
    # Render as Python-like list for clarity
    return json.dumps(mat, ensure_ascii=False)

def compute_sums(grid_vals: List[List[int]]) -> Tuple[List[int], List[int]]:
    r = len(grid_vals)
    c = len(grid_vals[0])
    row_sums = [sum(grid_vals[i][j] for j in range(c)) for i in range(r)]
    col_sums = [sum(grid_vals[i][j] for i in range(r)) for j in range(c)]
    return row_sums, col_sums

def build_survo_with_sums(base: List[List[int]], unknowns: List[Tuple[int,int]]) -> Tuple[List[List[Any]], List[int]]:
    """
    base: r x c full numeric grid (no sums included)
    unknowns: positions in base to replace with 'X'
    Return puzzle matrix of size (r+1) x (c+1) where last row/col are sums,
    with X inserted in the (r x c) interior.
    Also returns the list of hidden numbers (multiset) at those X positions in order.
    """
    r, c = len(base), len(base[0])
    row_sums, col_sums = compute_sums(base)
    total = sum(row_sums)
    # Build matrix with sums
    mat = []
    hidden = []
    unknown_set = set(unknowns)
    for i in range(r):
        row = []
        for j in range(c):
            if (i,j) in unknown_set:
                row.append("X")
                hidden.append(base[i][j])
            else:
                row.append(base[i][j])
        row.append(row_sums[i])
        mat.append(row)
    # last row: column sums + grand total
    last = []
    for j in range(c):
        last.append(col_sums[j])
    last.append(total)
    mat.append(last)
    return mat, hidden

def solve_by_enumeration(puzzle: List[List[Any]], numbers: List[int]) -> List[List[List[int]]]:
    """
    Enumerate all assignments of given numbers to X cells (each used exactly once)
    and return all solutions as full interior grid (without sums row/col).
    Assumes puzzle is (r+1)x(c+1).
    """
    r1 = len(puzzle)
    c1 = len(puzzle[0])
    r, c = r1 - 1, c1 - 1

    # collect X positions
    xs = []
    fixed = [[None]*c for _ in range(r)]
    for i in range(r):
        for j in range(c):
            v = puzzle[i][j]
            if v == "X":
                xs.append((i,j))
            else:
                fixed[i][j] = int(v)

    if len(xs) != len(numbers):
        return []

    # target sums
    row_target = [int(puzzle[i][c]) for i in range(r)]
    col_target = [int(puzzle[r][j]) for j in range(c)]
    total_target = int(puzzle[r][c])

    # quick consistency check with totals
    if sum(row_target) != total_target or sum(col_target) != total_target:
        return []

    # Precompute fixed contributions
    fixed_row_sum = [0]*r
    fixed_col_sum = [0]*c
    for i in range(r):
        for j in range(c):
            if fixed[i][j] is not None:
                fixed_row_sum[i] += fixed[i][j]
                fixed_col_sum[j] += fixed[i][j]

    # remaining sums required by Xs per row/col
    x_in_row = [0]*r
    x_in_col = [0]*c
    for (i,j) in xs:
        x_in_row[i] += 1
        x_in_col[j] += 1

    # multiset permutations enumeration with pruning
    nums = list(numbers)
    nums.sort()

    # generate unique permutations of multiset
    def uniq_perms(arr):
        used = [False]*len(arr)
        curr = []

        def backtrack():
            if len(curr) == len(arr):
                yield list(curr)
                return
            prev = None
            for k in range(len(arr)):
                if used[k]:
                    continue
                if prev is not None and arr[k] == prev:
                    continue
                prev = arr[k]
                used[k] = True
                curr.append(arr[k])

                yield from backtrack()

                curr.pop()
                used[k] = False
        yield from backtrack()

    solutions = []
    # Simple pruning during assignment: track partial row/col sums and remaining slots
    # We'll do backtracking directly on xs with multiset counts (more pruning).
    from collections import Counter
    cnt = Counter(nums)

    row_partial = [0]*r
    col_partial = [0]*c
    row_used = [0]*r
    col_used = [0]*c

    assign = [None]*len(xs)

    distinct_vals = sorted(cnt.keys())

    def feasible_bounds_row(i):
        # remaining cells in row i: k
        k = x_in_row[i] - row_used[i]
        need = row_target[i] - fixed_row_sum[i] - row_partial[i]
        if k == 0:
            return need == 0
        # bounds using smallest/largest available numbers
        available = []
        for v in distinct_vals:
            available += [v]*cnt[v]
        if len(available) < k:
            return False
        available.sort()
        min_sum = sum(available[:k])
        max_sum = sum(available[-k:])
        return min_sum <= need <= max_sum

    def feasible_bounds_col(j):
        k = x_in_col[j] - col_used[j]
        need = col_target[j] - fixed_col_sum[j] - col_partial[j]
        if k == 0:
            return need == 0
        available = []
        for v in distinct_vals:
            available += [v]*cnt[v]
        if len(available) < k:
            return False
        available.sort()
        min_sum = sum(available[:k])
        max_sum = sum(available[-k:])
        return min_sum <= need <= max_sum

    # choose next variable by most constrained: row/col with smallest remaining slots
    def pick_next_index():
        best = None
        best_score = None
        for idx, (i,j) in enumerate(xs):
            if assign[idx] is not None:
                continue
            # smaller remaining in its row/col -> more constrained
            score = (x_in_row[i] - row_used[i]) + (x_in_col[j] - col_used[j])
            if best is None or score < best_score:
                best = idx
                best_score = score
        return best

    def backtrack():
        if all(a is not None for a in assign):
            # verify exact
            for i in range(r):
                if fixed_row_sum[i] + row_partial[i] != row_target[i]:
                    return
            for j in range(c):
                if fixed_col_sum[j] + col_partial[j] != col_target[j]:
                    return
            # construct full interior
            sol = [[fixed[i][j] for j in range(c)] for i in range(r)]
            for idx, (i,j) in enumerate(xs):
                sol[i][j] = assign[idx]
            solutions.append(sol)
            return

        idx = pick_next_index()
        i, j = xs[idx]

        # Try values in a deterministic order for reproducibility
        for v in distinct_vals:
            if cnt[v] <= 0:
                continue

            # tentative update
            cnt[v] -= 1
            assign[idx] = v
            row_partial[i] += v
            col_partial[j] += v
            row_used[i] += 1
            col_used[j] += 1

            ok = True
            # quick feasibility checks for affected row/col
            if not feasible_bounds_row(i):
                ok = False
            if ok and not feasible_bounds_col(j):
                ok = False

            # also check rows/cols that have become complete
            if ok and (x_in_row[i] == row_used[i]):
                if fixed_row_sum[i] + row_partial[i] != row_target[i]:
                    ok = False
            if ok and (x_in_col[j] == col_used[j]):
                if fixed_col_sum[j] + col_partial[j] != col_target[j]:
                    ok = False

            if ok:
                backtrack()

            # revert
            row_used[i] -= 1
            col_used[j] -= 1
            row_partial[i] -= v
            col_partial[j] -= v
            assign[idx] = None
            cnt[v] += 1

            # early stop if too many solutions (we only need uniqueness check)
            if len(solutions) > 1:
                return

    backtrack()
    return solutions

def render_problem_zh(puzzle: List[List[Any]], numbers: List[int], variant: str) -> str:
    # Provide clear rules and ask for filled matrix (with sums kept).
    mat_str = fmt_matrix(puzzle)
    nums_str = json.dumps(numbers, ensure_ascii=False)
    if variant == "matrix_full":
        ask = "请给出填充后的完整矩阵（包含最后一列与最后一行的和）。"
    else:
        ask = "请给出所有 X 位置应填入的数字（按从上到下、从左到右的顺序列出）。"
    return (
        "请完成下面的 Survo 谜题。\n"
        f"给定一个矩阵（最后一列/最后一行是对应行/列的数字之和）：\n{mat_str}\n"
        f"矩阵中的 'X' 需要填入数字。你可使用的数字多重集为：{nums_str}，每个数字只能使用一次。\n"
        f"{ask}\n"
        "输出格式要求：若要求矩阵，则输出形如 [[...], [...], ...] 的 JSON 数组；"
        "若要求 X 的序列，则输出形如 [a,b,c] 的 JSON 数组。"
    )

def build_explanation_zh(puzzle: List[List[Any]], numbers: List[int], solution: List[List[int]], variant: str) -> str:
    r1, c1 = len(puzzle), len(puzzle[0])
    r, c = r1-1, c1-1
    # Derive the X list in scan order
    xs = []
    for i in range(r):
        for j in range(c):
            if puzzle[i][j] == "X":
                xs.append((i,j))
    xvals = [solution[i][j] for (i,j) in xs]
    # Provide one or two concrete row/col checks
    # Find a row with at least one X
    checks = []
    for i in range(r):
        if any(puzzle[i][j] == "X" for j in range(c)):
            row_vals = [solution[i][j] for j in range(c)]
            checks.append(f"第{i+1}行校验：{row_vals} 之和 = {sum(row_vals)}，等于题面给定的 {int(puzzle[i][c])}。")
            break
    for j in range(c):
        if any(puzzle[i][j] == "X" for i in range(r)):
            col_vals = [solution[i][j] for i in range(r)]
            checks.append(f"第{j+1}列校验：{col_vals} 之和 = {sum(col_vals)}，等于题面给定的 {int(puzzle[r][j])}。")
            break
    if not checks:
        checks.append("该题无 X（退化情形），直接由题面给定矩阵确定。")
    if variant == "matrix_full":
        # rebuild full matrix with sums
        base = [row[:] for row in solution]
        row_sums, col_sums = compute_sums(base)
        total = sum(row_sums)
        full = []
        for i in range(r):
            full.append(base[i] + [row_sums[i]])
        full.append(col_sums + [total])
        return (
            "把给定数字依次填入所有 X，使得每行/列的和满足最后一列/最后一行。\n"
            f"一种满足条件的填法对应的 X 值（从上到下、从左到右）为：{xvals}（恰好用尽 {numbers}）。\n"
            + "；".join(checks)
        )
    else:
        return (
            "根据每行/列的和约束，且必须恰好使用给定数字多重集一次，可确定唯一填法。\n"
            f"按从上到下、从左到右读取 X 的位置，其取值为：{xvals}。\n"
            + "；".join(checks)
        )

def generate_instance(rng: random.Random) -> Optional[Dict[str, Any]]:
    # Choose size 3x3 or 4x4 interior to add diversity, then add sums row/col.
    # Keep unknown count small for feasible uniqueness enumeration.
    interior_size = rng.choice([(3,3), (4,4)])
    r, c = interior_size

    # Choose number of Xs
    k = rng.choice([2,3,3,4]) if r == 4 else rng.choice([2,2,3])
    k = min(k, r*c - 1)

    # Create a full interior grid with small positive ints.
    # Use a mix of repeated numbers and distinct numbers.
    values_pool = list(range(1, 10))  # 1..9
    base = [[rng.choice(values_pool) for _ in range(c)] for _ in range(r)]

    # Choose X positions
    all_pos = [(i,j) for i in range(r) for j in range(c)]
    rng.shuffle(all_pos)
    unknowns = all_pos[:k]

    # Extract numbers to use = the hidden values; but to make it nontrivial,
    # we may optionally "swap" some hidden values with visible values by re-sampling base
    # while preserving consistency; simplest is accept as is.
    puzzle, numbers = build_survo_with_sums(base, unknowns)

    # Ensure at least one X per puzzle (k>=2 already) and avoid too-large sums row/col text
    # Solve and check uniqueness
    sols = solve_by_enumeration(puzzle, numbers)
    if len(sols) != 1:
        return None
    sol = sols[0]

    # Variant: ask for full matrix or just X-sequence
    variant = rng.choice(["matrix_full", "x_list"])

    problem = render_problem_zh(puzzle, numbers, variant)

    if variant == "matrix_full":
        row_sums, col_sums = compute_sums(sol)
        total = sum(row_sums)
        full = []
        for i in range(r):
            full.append(sol[i] + [row_sums[i]])
        full.append(col_sums + [total])
        answer = full
    else:
        xs = []
        for i in range(r):
            for j in range(c):
                if puzzle[i][j] == "X":
                    xs.append((i,j))
        answer = [sol[i][j] for (i,j) in xs]

    explanation = build_explanation_zh(puzzle, numbers, sol, variant)
    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = make_rng(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = 4000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        inst = generate_instance(rng)
        if inst is None:
            continue
        key = inst["problem"]
        if key in seen:
            continue
        seen.add(key)
        results.append(inst)

    if len(results) < count:
        print(f"Failed to generate enough unique valid puzzles: {len(results)}/{count} after {attempts} attempts", file=sys.stderr)
        # Still output what we have to avoid crashing, but spec wants exactly count items.
        # Therefore raise an error.
        raise RuntimeError("generation_failed")

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()