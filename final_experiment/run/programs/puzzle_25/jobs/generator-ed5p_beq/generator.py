import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

# We will generate Skyscrapers puzzles (a.k.a. Towers) on n*n grid.
# Use Z3 to (1) build a full Latin square solution, (2) derive edge clues,
# (3) optionally remove/blank some clues while keeping unique solution,
# (4) output puzzle statement in Chinese with self-contained rules.
#
# Input: {"seed": int, "count": int}
# Output: JSON array length=count, each with: problem (str), answer (JSON), explanation (str)
#
# available_libraries includes: z3, sympy (we use z3)

from z3 import Solver, Int, Distinct, And, Or, sat, unsat


def visible_count(seq: List[int]) -> int:
    m = 0
    c = 0
    for h in seq:
        if h > m:
            m = h
            c += 1
    return c


def compute_clues(grid: List[List[int]]) -> Dict[str, List[int]]:
    n = len(grid)
    top = []
    bottom = []
    left = []
    right = []
    for c in range(n):
        col = [grid[r][c] for r in range(n)]
        top.append(visible_count(col))
        bottom.append(visible_count(list(reversed(col))))
    for r in range(n):
        row = grid[r]
        left.append(visible_count(row))
        right.append(visible_count(list(reversed(row))))
    return {"top": top, "bottom": bottom, "left": left, "right": right}


def latin_solution(rng: random.Random, n: int) -> List[List[int]]:
    # Build a random Latin square by starting from cyclic Latin square then applying random permutations.
    base = [[((r + c) % n) + 1 for c in range(n)] for r in range(n)]
    # Randomly permute symbols, rows, cols, and also permute row bands/col bands if desired.
    sym_perm = list(range(1, n + 1))
    rng.shuffle(sym_perm)
    row_perm = list(range(n))
    col_perm = list(range(n))
    rng.shuffle(row_perm)
    rng.shuffle(col_perm)

    grid = [[sym_perm[base[row_perm[r]][col_perm[c]] - 1] for c in range(n)] for r in range(n)]
    return grid


def build_solver_for_puzzle(n: int,
                            clues: Dict[str, List[Optional[int]]]) -> Tuple[Solver, List[List[Any]]]:
    s = Solver()
    X = [[Int(f"x_{r}_{c}") for c in range(n)] for r in range(n)]
    # domain
    for r in range(n):
        for c in range(n):
            s.add(And(X[r][c] >= 1, X[r][c] <= n))
    # Latin constraints
    for r in range(n):
        s.add(Distinct(X[r]))
    for c in range(n):
        s.add(Distinct([X[r][c] for r in range(n)]))

    # Add visibility constraints if given
    # Encode visibility count using comparisons; for n<=6 it's fine.
    # We will support n in {4,5,6}.
    def vis_count_expr(seq):
        # returns an Int expression equal to visible count
        # visibility: position i is visible if seq[i] > max(seq[0..i-1])
        # For each i, build boolean b_i and sum.
        bs = []
        for i in range(len(seq)):
            if i == 0:
                bs.append(1)  # always visible
            else:
                prev = seq[:i]
                # visible if greater than all previous
                cond = And([seq[i] > prevj for prevj in prev])
                # z3 If
                from z3 import If
                bs.append(If(cond, 1, 0))
        from z3 import Sum
        return Sum(bs)

    top = clues.get("top")
    bottom = clues.get("bottom")
    left = clues.get("left")
    right = clues.get("right")

    if top is not None:
        for c in range(n):
            if top[c] is not None:
                s.add(vis_count_expr([X[r][c] for r in range(n)]) == int(top[c]))
    if bottom is not None:
        for c in range(n):
            if bottom[c] is not None:
                s.add(vis_count_expr([X[r][c] for r in range(n - 1, -1, -1)]) == int(bottom[c]))
    if left is not None:
        for r in range(n):
            if left[r] is not None:
                s.add(vis_count_expr([X[r][c] for c in range(n)]) == int(left[r]))
    if right is not None:
        for r in range(n):
            if right[r] is not None:
                s.add(vis_count_expr([X[r][c] for c in range(n - 1, -1, -1)]) == int(right[r]))
    return s, X


def model_to_grid(m, X) -> List[List[int]]:
    n = len(X)
    return [[int(m.evaluate(X[r][c]).as_long()) for c in range(n)] for r in range(n)]


def count_solutions(n: int, clues: Dict[str, List[Optional[int]]], limit: int = 2) -> Tuple[int, List[List[List[int]]]]:
    s, X = build_solver_for_puzzle(n, clues)
    sols = []
    cnt = 0
    from z3 import Not, And as zAnd
    while cnt < limit and s.check() == sat:
        m = s.model()
        g = model_to_grid(m, X)
        sols.append(g)
        cnt += 1
        # block this solution
        s.add(Not(zAnd([X[r][c] == g[r][c] for r in range(n) for c in range(n)])))
    return cnt, sols


def pretty_grid(grid: List[List[int]]) -> str:
    return ",".join(" ".join(str(x) for x in row) for row in grid)


def render_problem(n: int, clues: Dict[str, List[Optional[int]]], lang: str = "zh") -> str:
    # Render like seed: top clues line, then each row with left/right, bottom line.
    top = clues["top"]
    bottom = clues["bottom"]
    left = clues["left"]
    right = clues["right"]

    def show(v):
        return "?" if v is None else str(v)

    lines = []
    # Instructions in Chinese
    lines.append("你需要解一个“摩天楼（Skyscrapers）”逻辑题。规则如下：")
    lines.append(f"1) 棋盘是 {n}×{n}。每个格子填入 1~{n} 的整数，表示楼高。")
    lines.append("2) 同一行、同一列中数字不得重复。")
    lines.append("3) 四周的提示数表示从该方向看过去能看到的楼数：更高的楼会遮挡其后更矮的楼。")
    lines.append("4) 题面中网格用 X 表示待填。")
    lines.append("请根据四周提示填完整个矩阵。")
    lines.append("")
    lines.append("题目（上/下为列提示，左/右为行提示；? 表示该方向不给提示）：")

    # header with column indices and top clues
    col_ids = "\t".join(str(i + 1) for i in range(n))
    top_clues = "\t".join(show(top[i]) for i in range(n))
    lines.append(f"\t{col_ids}\t")
    lines.append(f"\t{top_clues}\t")

    # rows
    for r in range(n):
        row = "\t".join(["X"] * n)
        lines.append(f"{show(left[r])}\t{row}\t{show(right[r])}")

    # bottom clues
    bottom_clues = "\t".join(show(bottom[i]) for i in range(n))
    lines.append(f"\t{bottom_clues}\t")

    lines.append("")
    lines.append("作答格式：从左到右、从上到下给出每行；元素用空格分隔，行与行用逗号分隔；最外层用双中括号包裹。")
    lines.append("例如：[[1 2 3 4,2 3 4 1,...]]")
    return "\n".join(lines)


def render_answer(grid: List[List[int]]) -> str:
    return "[[" + pretty_grid(grid) + "]]"


def explanation_text(n: int, solution: List[List[int]], clues_used: Dict[str, List[Optional[int]]]) -> str:
    # Provide verifiable evidence: show final grid and computed clues (full), and mention uniqueness check.
    full_clues = compute_clues(solution)

    def fmt(arr): return " ".join(str(x) for x in arr)

    # Also show which clues were given (with ?)
    def fmt_given(arr):
        return " ".join("?" if v is None else str(v) for v in arr)

    lines = []
    lines.append("解题要点（可复核）：")
    lines.append(f"- 满足每行每列都是 1~{n} 且不重复（拉丁方约束）。")
    lines.append("- 从四个方向的可见楼数与题面提示一致。")
    lines.append("")
    lines.append("最终解矩阵：")
    lines.append(render_answer(solution))
    lines.append("")
    lines.append("该解对应的四周可见数（由解直接计算）：")
    lines.append(f"上(top):    {fmt(full_clues['top'])}")
    lines.append(f"下(bottom): {fmt(full_clues['bottom'])}")
    lines.append(f"左(left):   {fmt(full_clues['left'])}")
    lines.append(f"右(right):  {fmt(full_clues['right'])}")
    lines.append("")
    lines.append("题面实际给出的提示（? 表示未给）：")
    lines.append(f"上(top):    {fmt_given(clues_used['top'])}")
    lines.append(f"下(bottom): {fmt_given(clues_used['bottom'])}")
    lines.append(f"左(left):   {fmt_given(clues_used['left'])}")
    lines.append(f"右(right):  {fmt_given(clues_used['right'])}")
    return "\n".join(lines)


def make_puzzle(rng: random.Random, n: int) -> Tuple[Dict[str, List[Optional[int]]], List[List[int]]]:
    # Start from a random Latin square solution, compute full clues.
    sol = latin_solution(rng, n)
    full = compute_clues(sol)

    # Start with all clues, then remove some while keeping unique solution.
    # Ensure not too trivial by keeping at least min_clues.
    # Also allow some sides partially missing for variety.
    clues = {k: [int(x) for x in v] for k, v in full.items()}

    # Decide target clue count range
    total = 4 * n
    min_keep = rng.randint(max(n, total // 3), max(n + 2, total // 2))  # e.g., 4x4 keep 5-8
    max_remove = total - min_keep

    positions = [(side, i) for side in ["top", "bottom", "left", "right"] for i in range(n)]
    rng.shuffle(positions)

    removed = 0
    for side, i in positions:
        if removed >= max_remove:
            break
        old = clues[side][i]
        clues[side][i] = None
        # Check uniqueness
        cnt, _ = count_solutions(n, clues, limit=2)
        if cnt != 1:
            clues[side][i] = old
        else:
            removed += 1

    # Final uniqueness assertion
    cnt, sols = count_solutions(n, clues, limit=2)
    if cnt != 1:
        raise RuntimeError("Failed to ensure unique solution after clue removal.")
    # Ensure the unique solution equals our constructed one; if not, use the solver's solution as truth.
    unique_sol = sols[0]
    return clues, unique_sol


def signature_of_puzzle(n: int, clues: Dict[str, List[Optional[int]]]) -> Tuple:
    # Used to avoid duplicates across generated set
    def pack(arr):
        return tuple(-1 if v is None else int(v) for v in arr)
    return (n, pack(clues["top"]), pack(clues["bottom"]), pack(clues["left"]), pack(clues["right"]))


def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    # Choose sizes with some variety but keep solver cheap.
    sizes = [4, 5, 6]
    # Weighted: more 4x4 and 5x5
    weights = [0.45, 0.40, 0.15]

    def choice_weighted():
        x = rng.random()
        cum = 0.0
        for s, w in zip(sizes, weights):
            cum += w
            if x <= cum:
                return s
        return sizes[-1]

    out = []
    seen = set()
    attempts = 0
    max_attempts = 400

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        n = choice_weighted()

        try:
            clues, sol = make_puzzle(rng, n)
        except Exception as e:
            print(f"[gen] retry due to error: {e}", file=sys.stderr)
            continue

        sig = signature_of_puzzle(n, clues)
        if sig in seen:
            continue

        # Final sanity: solver uniqueness and solution matches all given clues
        cnt, sols = count_solutions(n, clues, limit=2)
        if cnt != 1:
            continue
        sol2 = sols[0]

        # Cross-check: computed clues must match given ones wherever not None
        full2 = compute_clues(sol2)
        ok = True
        for side in ["top", "bottom", "left", "right"]:
            for i, v in enumerate(clues[side]):
                if v is not None and int(v) != int(full2[side][i]):
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            continue

        problem = render_problem(n, clues, lang="zh")
        answer = render_answer(sol2)
        explanation = explanation_text(n, sol2, clues)

        out.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })
        seen.add(sig)

    if len(out) != count:
        raise SystemExit(f"Unable to generate required count={count}. Generated {len(out)} after {attempts} attempts.")

    sys.stdout.write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()