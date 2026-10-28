import sys, json, random
from typing import List, Tuple, Dict, Optional, Any

# We generate Numbrix-style puzzles on an N x N grid with numbers 1..N^2.
# Consecutive numbers must be orthogonally adjacent (sharing an edge).
#
# Generator strategy (constructive, then verify uniqueness):
# 1) Construct a Hamiltonian path that visits every cell exactly once.
#    We use a "snake" path by default, and sometimes apply reversible transforms:
#    - rotate (0/90/180/270)
#    - reflect (horizontal/vertical)
#    - reverse numbering (k -> N^2+1-k)
# 2) Place numbers along that path (1..N^2).
# 3) Choose a subset of clues (givens) from the solved grid with variety:
#    - include endpoints often, sometimes not
#    - include scattered numbers with spacing constraints
# 4) Check that the resulting puzzle has a UNIQUE solution under Numbrix constraints.
#    Uniqueness check is done with a Z3 model:
#      - Variables: each cell has an integer 1..N^2
#      - AllDifferent
#      - For every k, the cells of k and k+1 must be adjacent (encoded by position vars per k)
#      - Apply givens
#    Then find one solution and block it to see if another exists.
#
# Output: JSON array of {problem, answer, explanation} count items.

try:
    import z3  # type: ignore
except Exception as e:
    print("Z3 is required but not available.", file=sys.stderr)
    raise

Coord = Tuple[int, int]


def snake_path(n: int) -> List[Coord]:
    path = []
    for r in range(n):
        cols = range(n) if r % 2 == 0 else range(n - 1, -1, -1)
        for c in cols:
            path.append((r, c))
    return path


def rotate_coord(r: int, c: int, n: int, k: int) -> Coord:
    # rotate k times 90 degrees clockwise
    for _ in range(k % 4):
        r, c = c, n - 1 - r
    return r, c


def transform_grid(grid: List[List[int]], rot_k: int, flip_h: bool, flip_v: bool) -> List[List[int]]:
    n = len(grid)
    out = [[0] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            rr, cc = rotate_coord(r, c, n, rot_k)
            if flip_h:
                cc = n - 1 - cc
            if flip_v:
                rr = n - 1 - rr
            out[rr][cc] = grid[r][c]
    return out


def reverse_numbers(grid: List[List[int]]) -> List[List[int]]:
    n = len(grid)
    m = n * n
    return [[m + 1 - grid[r][c] for c in range(n)] for r in range(n)]


def build_solution(n: int, rng: random.Random) -> List[List[int]]:
    # base solution along snake path
    path = snake_path(n)
    grid = [[0] * n for _ in range(n)]
    for k, (r, c) in enumerate(path, start=1):
        grid[r][c] = k

    # apply random transforms
    rot_k = rng.randrange(4)
    flip_h = rng.choice([False, True])
    flip_v = rng.choice([False, True])
    grid = transform_grid(grid, rot_k, flip_h, flip_v)

    if rng.random() < 0.5:
        grid = reverse_numbers(grid)

    return grid


def format_grid_with_X(givens: Dict[Coord, int], n: int) -> str:
    # Render as a simple ASCII table, X for blanks.
    # Keep it compact and self-contained.
    lines = []
    sep = "+" + "+".join(["----"] * n) + "+"
    for r in range(n):
        lines.append(sep)
        row_cells = []
        for c in range(n):
            if (r, c) in givens:
                v = givens[(r, c)]
                row_cells.append(f"{v:>3} ")
            else:
                row_cells.append("  X ")
        lines.append("|" + "|".join(row_cells) + "|")
    lines.append(sep)
    return "\n".join(lines)


def adjacency(a: Coord, b: Coord) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def compute_positions(grid: List[List[int]]) -> Dict[int, Coord]:
    n = len(grid)
    pos = {}
    for r in range(n):
        for c in range(n):
            pos[grid[r][c]] = (r, c)
    return pos


def choose_clues(
    sol: List[List[int]],
    rng: random.Random,
    min_clues: int,
    max_clues: int
) -> Dict[Coord, int]:
    n = len(sol)
    m = n * n
    pos = compute_positions(sol)

    # Candidate clue numbers: prefer a mix of endpoints and interior.
    # We'll enforce some spacing to avoid too clustered clues.
    clue_count = rng.randint(min_clues, max_clues)

    forced_nums = []
    # Often include 1 and m, but not always.
    if rng.random() < 0.75:
        forced_nums.append(1)
    if rng.random() < 0.75:
        forced_nums.append(m)

    # Sometimes include a mid anchor
    if rng.random() < 0.60:
        forced_nums.append(rng.choice([m // 2, m // 2 + 1, n, m - n + 1]))

    forced_nums = list(dict.fromkeys([x for x in forced_nums if 1 <= x <= m]))

    chosen_nums = set(forced_nums)

    def far_enough(num: int) -> bool:
        # Keep Manhattan distance between clue cells at least 2 with high probability,
        # but allow some closer clues occasionally.
        (r0, c0) = pos[num]
        for v in chosen_nums:
            (r1, c1) = pos[v]
            d = abs(r0 - r1) + abs(c0 - c1)
            if d <= 1:
                return False
            if d == 2 and rng.random() < 0.65:
                return False
        return True

    # Fill remaining with random numbers, biased to include some consecutive runs sometimes.
    attempts = 0
    while len(chosen_nums) < clue_count and attempts < 5000:
        attempts += 1
        if rng.random() < 0.30 and chosen_nums:
            base = rng.choice(list(chosen_nums))
            cand = base + rng.choice([-3, -2, -1, 1, 2, 3])
        else:
            cand = rng.randint(1, m)
        if not (1 <= cand <= m):
            continue
        if cand in chosen_nums:
            continue
        if far_enough(cand):
            chosen_nums.add(cand)

    # If we failed to reach desired count, just accept what we have.
    givens = {pos[k]: k for k in chosen_nums}
    return givens


def z3_unique_solution(n: int, givens: Dict[Coord, int]) -> Tuple[bool, Optional[List[List[int]]], str]:
    """
    Returns (is_unique, solution_grid, explanation_note).
    """
    m = n * n
    s = z3.Solver()

    # Cell values
    cell = [[z3.Int(f"c_{r}_{c}") for c in range(n)] for r in range(n)]
    for r in range(n):
        for c in range(n):
            s.add(cell[r][c] >= 1, cell[r][c] <= m)
    s.add(z3.Distinct([cell[r][c] for r in range(n) for c in range(n)]))

    # Position of each number k: (rk, ck)
    rk = [z3.Int(f"r_{k}") for k in range(m + 1)]
    ck = [z3.Int(f"col_{k}") for k in range(m + 1)]
    for k in range(1, m + 1):
        s.add(rk[k] >= 0, rk[k] < n, ck[k] >= 0, ck[k] < n)

        # Link pos vars with cell grid:
        # Exactly one cell equals k, and rk/ck match that cell.
        # We can encode:
        #   Or_{r,c} (cell[r][c]==k and rk[k]==r and ck[k]==c)
        ors = []
        for r in range(n):
            for c in range(n):
                ors.append(z3.And(cell[r][c] == k, rk[k] == r, ck[k] == c))
        s.add(z3.Or(ors))

    # Consecutive adjacency constraint:
    for k in range(1, m):
        s.add(z3.Abs(rk[k] - rk[k + 1]) + z3.Abs(ck[k] - ck[k + 1]) == 1)

    # Apply givens
    for (r, c), v in givens.items():
        s.add(cell[r][c] == v)

    # Find first solution
    if s.check() != z3.sat:
        return (False, None, "给定线索导致无解。")

    model = s.model()
    sol1 = [[model.evaluate(cell[r][c]).as_long() for c in range(n)] for r in range(n)]

    # Block the found solution to test uniqueness
    block = z3.Or([cell[r][c] != sol1[r][c] for r in range(n) for c in range(n)])
    s.add(block)

    if s.check() == z3.sat:
        return (False, sol1, "存在多解（至少两组不同填法）。")
    return (True, sol1, "唯一解已通过“阻断首解再求解”的方式验证。")


def grid_to_pylist_str(grid: List[List[int]]) -> str:
    return "[\n" + ",\n".join("  " + str(row) for row in grid) + "\n]"


def make_problem_text(n: int, givens: Dict[Coord, int], output_language: str) -> str:
    # Only Chinese required by user, but keep a simple switch.
    table = format_grid_with_X(givens, n)
    if output_language == "zh":
        return (
            f"考虑一个 {n}×{n} 的 Numbrix（数字相邻）谜题网格。你需要在网格中填入从 1 到 {n*n} 的数字，使得连续数字总是正交相邻（共享一条边）。\n"
            f"规则：\n"
            f"1) 从 1 到 {n*n} 的每个数字必须恰好出现一次。\n"
            f"2) 相差为 1 的两个数字必须放在上下左右相邻的格子中。\n"
            f"3) 表格中给出了一些线索数字，其余位置用 X 表示。\n\n"
            f"输入网格（X 表示空格）：\n{table}\n\n"
            f"任务：在所有 X 中填入适当数字，满足上述规则。请以 Python 二维列表（列表的列表）形式输出完整网格。"
        )
    else:
        # fallback minimal English
        return (
            f"Solve the {n}x{n} Numbrix grid with numbers 1..{n*n}, consecutive numbers orthogonally adjacent.\n\n"
            f"Grid (X are blanks):\n{table}\n\n"
            f"Output the completed grid as a Python 2D list."
        )


def make_explanation(sol: List[List[int]], givens: Dict[Coord, int], unique_note: str, output_language: str) -> str:
    n = len(sol)
    m = n * n
    pos = compute_positions(sol)

    # Provide a few concrete verifiable checks: show neighbor relationships for a few k's and confirm givens.
    sample_ks = [1, 2, 3, m - 2, m - 1, m]
    # Add a couple random-ish middle ones deterministically from solution content:
    mid_candidates = [m // 3, m // 2, (2 * m) // 3]
    for k in mid_candidates:
        if 1 <= k <= m:
            sample_ks.append(k)
    sample_ks = list(dict.fromkeys([k for k in sample_ks if 1 <= k <= m]))

    def neigh_str(k: int) -> str:
        parts = []
        (r, c) = pos[k]
        if k > 1:
            (r0, c0) = pos[k - 1]
            parts.append(f"{k-1}在({r0+1},{c0+1})")
        if k < m:
            (r1, c1) = pos[k + 1]
            parts.append(f"{k+1}在({r1+1},{c1+1})")
        return f"{k}在({r+1},{c+1})，" + "，".join(parts)

    given_checks = []
    for (r, c), v in list(givens.items())[: min(8, len(givens))]:
        given_checks.append(f"线索 {v} 位于({r+1},{c+1})，解中该格为 {sol[r][c]}")

    if output_language == "zh":
        return (
            f"解为一个从 1 到 {m} 的连续路径填满整个 {n}×{n} 网格，并满足相邻差 1 必须正交相邻。\n"
            f"一致性抽查（坐标为“行,列”，从 1 开始计数）：\n"
            + "\n".join(f"- {neigh_str(k)}" for k in sample_ks)
            + "\n\n线索核对（节选）：\n"
            + ("\n".join(f"- {x}" for x in given_checks) if given_checks else "-（无）")
            + f"\n\n唯一性：{unique_note}"
        )
    else:
        return (
            f"One valid filling is shown as the answer. Sample adjacency checks:\n"
            + "\n".join(f"- {neigh_str(k)}" for k in sample_ks)
            + "\nUniqueness: " + unique_note
        )


def signature_of_problem(n: int, givens: Dict[Coord, int]) -> str:
    # Canonical signature to avoid duplicates across generated items.
    items = sorted(((r, c, v) for (r, c), v in givens.items()))
    return f"{n}|" + ";".join(f"{r},{c}:{v}" for r, c, v in items)


def generate_one(rng: random.Random, output_language: str) -> Dict[str, Any]:
    # Choose size with some diversity while keeping solvable fast.
    n = rng.choices([5, 6, 7], weights=[2, 5, 3], k=1)[0]

    sol = build_solution(n, rng)

    # clue count range depends on size
    if n == 5:
        min_c, max_c = 6, 10
    elif n == 6:
        min_c, max_c = 7, 12
    else:  # 7
        min_c, max_c = 9, 15

    # Resample clues until unique (bounded attempts)
    last_note = ""
    for _ in range(60):
        givens = choose_clues(sol, rng, min_c, max_c)
        unique, sol_check, note = z3_unique_solution(n, givens)
        last_note = note
        if unique and sol_check is not None:
            # Ensure answer matches our constructed solution? Use the solver's unique solution as truth.
            answer_grid = sol_check
            problem = make_problem_text(n, givens, output_language)
            explanation = make_explanation(answer_grid, givens, note, output_language)
            return {
                "problem": problem,
                "answer": answer_grid,
                "explanation": explanation
            }

    raise RuntimeError(f"Failed to generate a unique puzzle after many attempts. Last status: {last_note}")


def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data) if data.strip() else {}
    except json.JSONDecodeError as e:
        print("Invalid JSON input.", file=sys.stderr)
        raise

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))

    # Optional parameters from the outer wrapper (not required by spec, but accepted if present)
    output_language = req.get("output_language", "zh")
    if output_language not in ("zh", "en"):
        output_language = "zh"

    rng = random.Random(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = 4000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng, output_language)
        except Exception as e:
            # Log and continue; bounded by max_attempts
            print(f"[gen-fail] {e}", file=sys.stderr)
            continue

        # De-dup by signature of givens extracted from the rendered problem isn't easy,
        # so regenerate signature by parsing: we saved givens only inside generation.
        # Instead, compute a rough signature by hashing the problem text (stable here).
        # To reduce collision risk, use full problem string as key.
        sig = item["problem"]
        if sig in seen:
            continue
        seen.add(sig)
        results.append(item)

    if len(results) < count:
        raise RuntimeError(f"Only generated {len(results)} items out of requested {count} within attempt limit.")

    sys.stdout.write(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()