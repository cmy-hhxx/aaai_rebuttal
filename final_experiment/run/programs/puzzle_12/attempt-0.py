import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

# We will generate and solve "weighted black cells" grid puzzles.
# Grid size n x n. Each cell can be black(1) or blank(X).
# Row constraint: sum over black cells of (column index 1..n) equals given row sum.
# Column constraint: sum over black cells of (row index 1..n) equals given column sum.
#
# We generate by sampling a binary matrix, compute sums, then verify uniqueness
# (or optionally allow multiple-solution variants with specified rule).
#
# Use z3 for solving and uniqueness checking.

from z3 import Solver, Int, Sum, And, Or, sat  # type: ignore


def z3_solve_all(n: int, row_sums: List[int], col_sums: List[int], max_solutions: int = 2):
    """Return up to max_solutions solutions as 0/1 matrices."""
    s = Solver()
    x = [[Int(f"x_{r}_{c}") for c in range(n)] for r in range(n)]
    for r in range(n):
        for c in range(n):
            s.add(Or(x[r][c] == 0, x[r][c] == 1))

    # Row constraints: weight in row is column position
    for r in range(n):
        s.add(Sum([x[r][c] * (c + 1) for c in range(n)]) == row_sums[r])

    # Column constraints: weight in column is row position
    for c in range(n):
        s.add(Sum([x[r][c] * (r + 1) for r in range(n)]) == col_sums[c])

    sols = []
    while len(sols) < max_solutions and s.check() == sat:
        m = s.model()
        sol = [[int(m.evaluate(x[r][c]).as_long()) for c in range(n)] for r in range(n)]
        sols.append(sol)
        # block this solution
        s.add(Or([x[r][c] != sol[r][c] for r in range(n) for c in range(n)]))
    return sols


def matrix_to_answer_format(sol: List[List[int]]) -> str:
    # Replace 0 with X and 1 with 1. Rows separated by commas, elements by spaces.
    rows = []
    for r in sol:
        rows.append(" ".join("1" if v == 1 else "X" for v in r))
    return "[[" + ",".join(rows) + "]]"


def compute_sums(sol: List[List[int]]) -> Tuple[List[int], List[int]]:
    n = len(sol)
    row_sums = []
    col_sums = []
    for r in range(n):
        row_sums.append(sum(sol[r][c] * (c + 1) for c in range(n)))
    for c in range(n):
        col_sums.append(sum(sol[r][c] * (r + 1) for r in range(n)))
    return row_sums, col_sums


def render_problem(n: int, row_sums: List[int], col_sums: List[int], lang: str) -> str:
    # Create a grid of X with row sums appended, and col sums appended at bottom.
    # Match seed style.
    lines = []
    if lang == "zh":
        lines.append("请根据规则将部分格子涂黑（用 1 表示），其余保持 X。")
        lines.append("规则：每行的黑格权重为该行中所在列的位置(1..n)之和等于行末数字；每列的黑格权重为该列中所在行的位置(1..n)之和等于列末数字。")
        lines.append("题目矩阵如下（每行末尾为该行约束；最后一行为各列约束）：")
    else:
        lines.append("Fill some cells as black (write 1), keep others as X.")
        lines.append("Rule: In each row, black-cell weights are their column positions (1..n); in each column, weights are their row positions (1..n). Sums must match the given numbers.")
        lines.append("Matrix (row constraints at line end; last line are column constraints):")

    for r in range(n):
        lines.append("  ".join(["X"] * n + [str(row_sums[r])]))
    lines.append("  ".join([str(v) for v in col_sums]))
    if lang == "zh":
        lines.append("请按从左到右、从上到下输出，每行用空格分隔，不同行用逗号分隔，并用双中括号包裹，例如：[[X 1,X X]]。")
    else:
        lines.append('Output left-to-right, top-to-bottom; separate elements with spaces and rows with commas, wrapped in double brackets like [[...]].')
    return "\n".join(lines)


def explain_solution(sol: List[List[int]], row_sums: List[int], col_sums: List[int], lang: str) -> str:
    n = len(sol)
    # Provide a concise, checkable explanation: show row weighted sums and col weighted sums.
    row_checks = []
    for r in range(n):
        terms = []
        total = 0
        for c in range(n):
            if sol[r][c] == 1:
                terms.append(str(c + 1))
                total += (c + 1)
        expr = "+".join(terms) if terms else "0"
        row_checks.append(f"第{r+1}行: {expr}={total}" if lang == "zh" else f"Row {r+1}: {expr}={total}")

    col_checks = []
    for c in range(n):
        terms = []
        total = 0
        for r in range(n):
            if sol[r][c] == 1:
                terms.append(str(r + 1))
                total += (r + 1)
        expr = "+".join(terms) if terms else "0"
        col_checks.append(f"第{c+1}列: {expr}={total}" if lang == "zh" else f"Col {c+1}: {expr}={total}")

    if lang == "zh":
        uniqueness = "并且用约束求解器检验该题只有一个满足所有行列和的解。"
    else:
        uniqueness = "Uniqueness was checked: exactly one solution satisfies all constraints."

    return ("行校验：\n" + "\n".join(row_checks) + "\n列校验：\n" + "\n".join(col_checks) + "\n" + uniqueness) if lang == "zh" else \
           ("Row checks:\n" + "\n".join(row_checks) + "\nColumn checks:\n" + "\n".join(col_checks) + "\n" + uniqueness)


def random_binary_matrix(rng: random.Random, n: int, density: float) -> List[List[int]]:
    # density is probability of 1
    return [[1 if rng.random() < density else 0 for _ in range(n)] for __ in range(n)]


def is_nontrivial(sol: List[List[int]]) -> bool:
    n = len(sol)
    ones = sum(sum(r) for r in sol)
    return 0 < ones < n * n  # avoid all-zero and all-one


def gen_one(rng: random.Random, lang: str, seen_signatures: set) -> Dict[str, Any]:
    # Multiple families: sizes 4..6 with different densities.
    # Ensure unique solution.
    for attempt in range(400):
        n = rng.choice([4, 5, 6])
        density = rng.choice([0.25, 0.3, 0.35, 0.4, 0.45, 0.5])
        sol = random_binary_matrix(rng, n, density)
        if not is_nontrivial(sol):
            continue

        row_sums, col_sums = compute_sums(sol)

        # Avoid degenerate constraints (all zeros etc.)
        if all(v == 0 for v in row_sums) or all(v == 0 for v in col_sums):
            continue

        # Uniqueness check using z3 enumerating up to 2 solutions
        sols = z3_solve_all(n, row_sums, col_sums, max_solutions=2)
        if len(sols) != 1:
            continue

        uniq_sol = sols[0]

        # Signature to avoid duplicates: (n, row_sums, col_sums) is enough.
        sig = (n, tuple(row_sums), tuple(col_sums))
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)

        problem = render_problem(n, row_sums, col_sums, lang)
        answer = matrix_to_answer_format(uniq_sol)
        explanation = explain_solution(uniq_sol, row_sums, col_sums, lang)

        return {"problem": problem, "answer": answer, "explanation": explanation}

    raise RuntimeError("生成失败：在采样上限内未能生成具有唯一解的题目。")


def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    # output_language is specified by the execution environment request; default zh
    # but since only stdin JSON is defined as {"seed","count"}, we keep zh by default.
    # If caller wants different language, they can embed it in seed by changing seed;
    # however spec says output_language is in code generation request, so we hardcode zh.
    lang = "zh"

    res = []
    seen = set()
    try:
        for _ in range(count):
            res.append(gen_one(rng, lang, seen))
    except Exception as e:
        print(str(e), file=sys.stderr)
        raise

    sys.stdout.write(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()