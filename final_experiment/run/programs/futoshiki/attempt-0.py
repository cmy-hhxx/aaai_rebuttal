import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

# We will use z3 if available (as allowed) for robust solving/uniqueness checks.
try:
    from z3 import Int, Solver, Distinct, And, Or, sat, unsat
except Exception as e:
    print("Failed to import z3. Ensure z3 is available.", file=sys.stderr)
    raise

Coord = Tuple[int, int]  # 1-indexed (r,c)
Ineq = Tuple[Coord, str, Coord]  # ((r1,c1), '>' or '<', (r2,c2))

def latin_base(n: int) -> List[List[int]]:
    # Standard cyclic Latin square
    return [[((r + c) % n) + 1 for c in range(n)] for r in range(n)]

def permute_grid(grid: List[List[int]], rng: random.Random) -> List[List[int]]:
    n = len(grid)
    # Permute symbols
    sym_perm = list(range(1, n + 1))
    rng.shuffle(sym_perm)
    sym_map = {i + 1: sym_perm[i] for i in range(n)}
    g = [[sym_map[v] for v in row] for row in grid]

    # Permute rows and cols
    row_perm = list(range(n))
    col_perm = list(range(n))
    rng.shuffle(row_perm)
    rng.shuffle(col_perm)
    g2 = [[g[row_perm[r]][col_perm[c]] for c in range(n)] for r in range(n)]
    return g2

def all_cells(n: int) -> List[Coord]:
    return [(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]

def neighbors(n: int) -> List[Tuple[Coord, Coord]]:
    pairs = []
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            if r < n:
                pairs.append(((r, c), (r + 1, c)))
            if c < n:
                pairs.append(((r, c), (r, c + 1)))
    return pairs

def build_solver(n: int, givens: Dict[Coord, int], ineqs: List[Ineq]) -> Tuple[Solver, Dict[Coord, Any]]:
    S = Solver()
    X = {(r, c): Int(f"x_{r}_{c}") for r in range(1, n + 1) for c in range(1, n + 1)}
    # Domain
    for rc, var in X.items():
        S.add(And(var >= 1, var <= n))
    # Row/col all-different
    for r in range(1, n + 1):
        S.add(Distinct([X[(r, c)] for c in range(1, n + 1)]))
    for c in range(1, n + 1):
        S.add(Distinct([X[(r, c)] for r in range(1, n + 1)]))
    # Givens
    for (r, c), v in givens.items():
        S.add(X[(r, c)] == v)
    # Inequalities
    for (a, op, b) in ineqs:
        if op == ">":
            S.add(X[a] > X[b])
        elif op == "<":
            S.add(X[a] < X[b])
        else:
            raise ValueError("Unknown op")
    return S, X

def solve_one(n: int, givens: Dict[Coord, int], ineqs: List[Ineq]) -> Optional[List[List[int]]]:
    S, X = build_solver(n, givens, ineqs)
    if S.check() != sat:
        return None
    m = S.model()
    grid = [[m.evaluate(X[(r, c)]).as_long() for c in range(1, n + 1)] for r in range(1, n + 1)]
    return grid

def is_unique(n: int, givens: Dict[Coord, int], ineqs: List[Ineq], solution: List[List[int]]) -> bool:
    S, X = build_solver(n, givens, ineqs)
    if S.check() != sat:
        return False
    # Block the given solution
    block = []
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            block.append(X[(r, c)] == solution[r - 1][c - 1])
    S.add(NotAllEqual(block))
    return S.check() == unsat

def NotAllEqual(eq_list):
    # Negation of conjunction: not (a1 & a2 & ...), equivalent to exists i: not ai
    return Or([NotEq(e) for e in eq_list])

def NotEq(eq):
    # eq is a z3 BoolRef like (x == v)
    # its negation is simply Not(eq), but import Not lazily to avoid name clash
    from z3 import Not
    return Not(eq)

def compute_ineqs_from_solution(sol: List[List[int]], rng: random.Random, density: float) -> List[Ineq]:
    n = len(sol)
    ineqs = []
    for (a, b) in neighbors(n):
        (r1, c1), (r2, c2) = a, b
        v1 = sol[r1 - 1][c1 - 1]
        v2 = sol[r2 - 1][c2 - 1]
        if v1 == v2:
            continue
        # choose include based on density
        if rng.random() <= density:
            op = ">" if v1 > v2 else "<"
            ineqs.append((a, op, b))
    rng.shuffle(ineqs)
    return ineqs

def pretty_grid_with_X(n: int, givens: Dict[Coord, int]) -> str:
    lines = []
    for r in range(1, n + 1):
        row = []
        for c in range(1, n + 1):
            row.append(str(givens[(r, c)]) if (r, c) in givens else "X")
        lines.append(" ".join(row))
    return "\n".join(lines)

def format_ineqs(ineqs: List[Ineq]) -> str:
    return "\n".join([f"({a[0]},{a[1]}) {op} ({b[0]},{b[1]})" for (a, op, b) in ineqs])

def explain(n: int, givens: Dict[Coord, int], ineqs: List[Ineq], sol: List[List[int]]) -> str:
    # Provide concise, checkable explanation: mention row/col constraint + verify each inequality and givens.
    parts = []
    parts.append(f"这是一个{n}x{n}不等式数独（拉丁方）：每行每列都必须恰好包含1~{n}各一次。")
    if givens:
        gv = ", ".join([f"({r},{c})={v}" for (r, c), v in sorted(givens.items())])
        parts.append(f"题目给定提示：{gv}。")
    if ineqs:
        parts.append(f"题目给出{len(ineqs)}条相邻格不等式。将解代入可逐条核对均成立，例如：")
        show = ineqs[:min(4, len(ineqs))]
        for (a, op, b) in show:
            va = sol[a[0]-1][a[1]-1]
            vb = sol[b[0]-1][b[1]-1]
            parts.append(f"  ({a[0]},{a[1]})={va} {op} ({b[0]},{b[1]})={vb}")
        if len(ineqs) > len(show):
            parts.append("其余不等式同理代入验证均成立。")
    parts.append("同时检查每行每列均为1~n的一个排列，因此该矩阵是合法解。")
    parts.append("本题通过约束求解检查该解为唯一解（不存在不同的另一组满足全部提示与不等式的填法）。")
    return "\n".join(parts)

def generate_one(rng: random.Random, n: int = 4) -> Dict[str, Any]:
    # Construct a solvable instance with unique solution by selecting givens + inequalities derived from a hidden solution.
    base = latin_base(n)
    sol = permute_grid(base, rng)

    # Decide style parameters for diversity
    # density of inequalities and number of givens
    density = rng.uniform(0.25, 0.75)   # probability to include each neighbor inequality
    ineqs = compute_ineqs_from_solution(sol, rng, density)

    # Ensure at least some inequalities
    if len(ineqs) < 3:
        # force include a few random neighbor constraints
        neigh = neighbors(n)
        rng.shuffle(neigh)
        for (a, b) in neigh:
            v1 = sol[a[0]-1][a[1]-1]
            v2 = sol[b[0]-1][b[1]-1]
            if v1 == v2:
                continue
            op = ">" if v1 > v2 else "<"
            ineqs.append((a, op, b))
            if len(ineqs) >= 4:
                break
        rng.shuffle(ineqs)

    # Pick givens: start with 0..k then adjust until unique
    # To avoid triviality, we don't allow all givens.
    min_g, max_g = (0, 6)
    k = rng.randint(min_g, max_g)
    cells = all_cells(n)
    rng.shuffle(cells)
    givens = {(r, c): sol[r-1][c-1] for (r, c) in cells[:k]}

    # Try to reach uniqueness by adding constraints (givens or inequalities) within bounds
    # Use bounded loop to avoid infinite.
    for _ in range(80):
        candidate = solve_one(n, givens, ineqs)
        if candidate is None:
            # too tight; relax by dropping a random inequality if possible
            if ineqs:
                ineqs.pop()
                continue
            else:
                # restart
                return generate_one(rng, n)

        # Check uniqueness
        if check_unique_via_second_solution(n, givens, ineqs, candidate):
            sol_final = candidate
            # avoid over-constrained: try remove some givens/ineqs greedily a bit
            sol_final = candidate
            givens2, ineqs2 = minimize_instance(rng, n, givens, ineqs, sol_final)
            return render_problem(n, givens2, ineqs2, sol_final)

        # Not unique: add constraint
        action = rng.random()
        if action < 0.55 and len(givens) < 8:
            # add a new given
            remaining = [rc for rc in cells if rc not in givens]
            if remaining:
                rc = rng.choice(remaining)
                givens[rc] = sol[rc[0]-1][rc[1]-1]
            else:
                # fallback add inequality
                ineqs = add_more_ineqs_from_solution(sol, ineqs, rng)
        else:
            ineqs = add_more_ineqs_from_solution(sol, ineqs, rng)

    # If fail, restart
    return generate_one(rng, n)

def add_more_ineqs_from_solution(sol: List[List[int]], ineqs: List[Ineq], rng: random.Random) -> List[Ineq]:
    n = len(sol)
    existing = set((a, op, b) for (a, op, b) in ineqs)
    # try add a missing neighbor relation
    neigh = neighbors(n)
    rng.shuffle(neigh)
    for (a, b) in neigh:
        v1 = sol[a[0]-1][a[1]-1]
        v2 = sol[b[0]-1][b[1]-1]
        if v1 == v2:
            continue
        op = ">" if v1 > v2 else "<"
        tpl = (a, op, b)
        if tpl not in existing:
            ineqs.append(tpl)
            return ineqs
    return ineqs

def check_unique_via_second_solution(n: int, givens: Dict[Coord, int], ineqs: List[Ineq], sol: List[List[int]]) -> bool:
    # Independent-ish check: ask z3 for a *different* solution by blocking all cells equalities.
    # If unsat => unique.
    S, X = build_solver(n, givens, ineqs)
    if S.check() != sat:
        return False
    # block current sol
    from z3 import Not
    S.add(Or([X[(r,c)] != sol[r-1][c-1] for r in range(1,n+1) for c in range(1,n+1)]))
    return S.check() == unsat

def minimize_instance(rng: random.Random, n: int, givens: Dict[Coord,int], ineqs: List[Ineq], sol: List[List[int]]):
    # Try removing some constraints while keeping unique; bounded attempts.
    givens = dict(givens)
    ineqs = list(ineqs)

    # Random order removals
    for _ in range(30):
        changed = False
        # Try remove a given
        if givens and rng.random() < 0.5:
            rc = rng.choice(list(givens.keys()))
            v = givens.pop(rc)
            if not check_unique_via_second_solution(n, givens, ineqs, sol):
                givens[rc] = v
            else:
                changed = True
        # Try remove an inequality
        if ineqs and rng.random() < 0.7:
            idx = rng.randrange(len(ineqs))
            removed = ineqs.pop(idx)
            if not check_unique_via_second_solution(n, givens, ineqs, sol):
                ineqs.insert(idx, removed)
            else:
                changed = True
        if not changed:
            # small chance to stop early
            if rng.random() < 0.3:
                break
    return givens, ineqs

def render_problem(n: int, givens: Dict[Coord,int], ineqs: List[Ineq], sol: List[List[int]]) -> Dict[str, Any]:
    grid_txt = pretty_grid_with_X(n, givens)
    ineq_txt = format_ineqs(ineqs) if ineqs else "（无）"
    problem = (
        f"这是一个{n}x{n}的不等式数独。游戏规则：\n"
        f"1. 在{n}x{n}的网格中填入数字，每行和每列必须包含1到{n}的所有数字且不能重复。\n"
        f"2. 网格中的不等式符号（\">\"或\"<\"）表示相邻格子之间的数值大小关系。\n"
        f"3. 部分格子会预先填入数字作为提示。\n"
        f"4. 题目以矩阵形式给出，下方附有不等式约束，格式为(第i行,第j列) > (第x行,第y列)。\n\n"
        f"当前题目：\n{grid_txt}\n\n"
        f"不等式约束：\n{ineq_txt}\n\n"
        "请按如下格式输出答案（用二维数组表示整张网格）：\n"
        f"例如输出 [[A,B,...],[...],...]。"
    )
    ans = sol
    exp = explain(n, givens, ineqs, sol)
    return {"problem": problem, "answer": ans, "explanation": exp}

def canonical_signature(item: Dict[str, Any]) -> str:
    # Dedup by normalized problem text
    return item["problem"].strip()

def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data)
        seed = int(req["seed"])
        count = int(req["count"])
    except Exception as e:
        print("Input must be JSON with keys: seed (int), count (positive int).", file=sys.stderr)
        raise

    if count <= 0:
        print("count must be positive.", file=sys.stderr)
        raise SystemExit(1)

    rng = random.Random(seed)

    out = []
    seen = set()
    attempts = 0
    max_attempts = 5000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        item = generate_one(rng, n=4)

        sig = canonical_signature(item)
        if sig in seen:
            continue

        # Final sanity: solve and verify matches answer
        givens, ineqs = parse_from_problem(item["problem"])
        sol = solve_one(4, givens, ineqs)
        if sol is None:
            continue
        if sol != item["answer"]:
            continue
        if not check_unique_via_second_solution(4, givens, ineqs, sol):
            continue

        seen.add(sig)
        out.append(item)

    if len(out) < count:
        print(f"Generation failed: produced {len(out)}/{count} after {attempts} attempts.", file=sys.stderr)
        raise SystemExit(2)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))

def parse_from_problem(problem: str) -> Tuple[Dict[Coord,int], List[Ineq]]:
    # Simple parser for our own rendered format (for sanity checks only).
    # Extract the 4 lines after "当前题目："
    lines = problem.splitlines()
    givens = {}
    ineqs = []

    # Find current grid
    try:
        idx = lines.index("当前题目：")
    except ValueError:
        return givens, ineqs

    grid_lines = []
    for k in range(idx + 1, len(lines)):
        if lines[k].strip() == "":
            break
        grid_lines.append(lines[k].strip())
    n = 4
    if len(grid_lines) >= n:
        grid_lines = grid_lines[:n]
        for r in range(1, n + 1):
            tokens = grid_lines[r-1].split()
            for c in range(1, n + 1):
                t = tokens[c-1]
                if t != "X":
                    givens[(r,c)] = int(t)

    # Find inequalities section
    try:
        j = lines.index("不等式约束：")
    except ValueError:
        return givens, ineqs

    for k in range(j + 1, len(lines)):
        s = lines[k].strip()
        if not s:
            break
        if s == "（无）":
            break
        # format: (a,b) > (c,d)
        try:
            left, op, right = s.split()
            a = left.strip()[1:-1]
            b = right.strip()[1:-1]
            r1, c1 = map(int, a.split(","))
            r2, c2 = map(int, b.split(","))
            if op not in (">", "<"):
                continue
            ineqs.append(((r1,c1), op, (r2,c2)))
        except Exception:
            continue

    return givens, ineqs

if __name__ == "__main__":
    main()