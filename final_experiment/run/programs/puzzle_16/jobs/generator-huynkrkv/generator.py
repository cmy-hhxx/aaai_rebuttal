import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

# KenKen-like (Latin + cage arithmetic) puzzle generator with uniqueness checking via z3.
# Fix: make generation more robust so it doesn't fail for n=6 under budget.
# Strategy:
# 1) Start with many cages (more singletons and 2-cells) to strongly constrain.
# 2) Ensure each cage constraint is exact and enforce cage Distinct.
# 3) Uniqueness-check with z3; if not unique, add a few more singletons derived from solution.
# 4) Bounded attempts but with high success probability.

def latin_square(n: int) -> List[List[int]]:
    return [[((r + c) % n) + 1 for c in range(n)] for r in range(n)]

def permute_square(rng: random.Random, grid: List[List[int]]) -> List[List[int]]:
    n = len(grid)
    # symbol permutation
    perm = list(range(1, n + 1))
    rng.shuffle(perm)
    mp = {i + 1: perm[i] for i in range(n)}
    g = [[mp[v] for v in row] for row in grid]
    # row/col permutation
    rows = list(range(n))
    cols = list(range(n))
    rng.shuffle(rows)
    rng.shuffle(cols)
    return [[g[rows[r]][cols[c]] for c in range(n)] for r in range(n)]

def neighbors(cell: Tuple[int, int], n: int):
    r, c = cell
    if r + 1 < n: yield (r + 1, c)
    if r - 1 >= 0: yield (r - 1, c)
    if c + 1 < n: yield (r, c + 1)
    if c - 1 >= 0: yield (r, c - 1)

def op_apply(values: List[int], op: str) -> Optional[int]:
    if op == '+':
        return sum(values)
    if op == '*':
        p = 1
        for v in values:
            p *= v
        return p
    if op == '-':
        if len(values) != 2: return None
        return abs(values[0] - values[1])
    if op == '÷':
        if len(values) != 2: return None
        a, b = values
        hi, lo = (a, b) if a >= b else (b, a)
        if lo == 0 or hi % lo != 0:
            return None
        return hi // lo
    if op == '=':
        if len(values) != 1: return None
        return values[0]
    return None

def format_cage(cells: List[Tuple[int, int]], target: int, op: str) -> str:
    coords = ''.join([f"({r+1},{c+1})" for r, c in cells])
    if op == '=':
        return f"{coords}:{target}"
    return f"{coords}:{target}{op}"

def grid_to_answer_string(grid: List[List[int]]) -> str:
    rows = [' '.join(str(x) for x in row) for row in grid]
    return "[[" + ",".join(rows) + "]]"

def solve_kenken(n: int, cages: List[Dict[str, Any]], limit: int = 2) -> List[List[List[int]]]:
    import z3
    X = [[z3.Int(f"x_{r}_{c}") for c in range(n)] for r in range(n)]
    s = z3.Solver()

    for r in range(n):
        for c in range(n):
            s.add(X[r][c] >= 1, X[r][c] <= n)
    for r in range(n):
        s.add(z3.Distinct(X[r]))
    for c in range(n):
        s.add(z3.Distinct([X[r][c] for r in range(n)]))

    for cg in cages:
        cells = cg["cells"]
        op = cg["op"]
        target = cg["target"]
        vars_ = [X[r][c] for (r, c) in cells]

        if len(vars_) >= 2:
            s.add(z3.Distinct(vars_))

        if op == '=':
            s.add(vars_[0] == target)
        elif op == '+':
            s.add(z3.Sum(vars_) == target)
        elif op == '*':
            prod = vars_[0]
            for v in vars_[1:]:
                prod = prod * v
            s.add(prod == target)
        elif op == '-':
            a, b = vars_
            s.add(z3.Or(a - b == target, b - a == target))
        elif op == '÷':
            a, b = vars_
            s.add(z3.Or(
                z3.And(b != 0, a == b * target),
                z3.And(a != 0, b == a * target)
            ))
        else:
            return []

    sols = []
    while len(sols) < limit and s.check() == z3.sat:
        m = s.model()
        sol = [[m.evaluate(X[r][c]).as_long() for c in range(n)] for r in range(n)]
        sols.append(sol)
        s.add(z3.Or([X[r][c] != sol[r][c] for r in range(n) for c in range(n)]))
    return sols

def statement_zh(n: int, cages: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append(f"网格大小为 {n}×{n}。请在每一行、每一列填入 1 到 {n}，且每行每列不重复。")
    lines.append("网格被划分为若干笼区。每个笼区给出若干坐标与“目标数+运算符”。笼区内数字不重复，且按运算得到目标数。")
    lines.append("运算：+ 求和；* 求积；- 为两数差的绝对值；÷ 为两数相除得到整数商（顺序不定）；单格笼区直接等于目标数。")
    lines.append("笼区条件：")
    for cg in cages:
        cells = sorted(cg["cells"])
        lines.append("  " + format_cage(cells, cg["target"], cg["op"]))
    lines.append("输出格式：按行从左到右列出，元素用空格分隔，行用逗号分隔，最外层用双中括号包裹，例如 [[1 2,3 4]]。")
    return "\n".join(lines)

def explain_zh(sol: List[List[int]], cages: List[Dict[str, Any]]) -> str:
    n = len(sol)
    lines = []
    lines.append("验证：每行每列均为1..N的排列；并逐笼区代入满足目标。")
    lines.append(f"例如第1行：{' '.join(map(str, sol[0]))}；第1列：{' '.join(str(sol[r][0]) for r in range(n))}。")
    lines.append("笼区校验（取值 -> 运算结果）：")
    for cg in cages:
        cells = sorted(cg["cells"])
        vals = [sol[r][c] for r, c in cells]
        got = op_apply(vals, cg["op"])
        lines.append(f"  {format_cage(cells, cg['target'], cg['op'])}：{vals} -> {got}")
    return "\n".join(lines)

def make_initial_cages(rng: random.Random, sol: List[List[int]]) -> List[Dict[str, Any]]:
    # Strongly constraining baseline:
    # - many singletons
    # - remaining cells mostly 2-cages; occasional 3-cages
    n = len(sol)
    cells = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(cells)
    unused = set(cells)
    cages: List[Dict[str, Any]] = []

    # choose singleton count
    if n == 4:
        singleton_target = rng.randint(4, 6)
    elif n == 5:
        singleton_target = rng.randint(6, 9)
    else:  # n==6
        singleton_target = rng.randint(10, 14)

    # create singletons
    for cell in list(cells):
        if len([cg for cg in cages if cg["op"] == '=']) >= singleton_target:
            break
        if cell in unused:
            r, c = cell
            cages.append({"cells": [cell], "op": "=", "target": sol[r][c]})
            unused.remove(cell)

    # helper to pick a connected pair
    def pick_pair() -> Optional[List[Tuple[int, int]]]:
        if not unused:
            return None
        start = next(iter(unused))
        nbrs = [nb for nb in neighbors(start, n) if nb in unused]
        if not nbrs:
            return [start]
        nb = rng.choice(nbrs)
        return sorted([start, nb])

    # fill the rest
    while unused:
        # sometimes try size 3 cage
        make3 = (n >= 5 and rng.random() < 0.18)
        if make3 and len(unused) >= 3:
            start = next(iter(unused))
            cand = [nb for nb in neighbors(start, n) if nb in unused]
            rng.shuffle(cand)
            if len(cand) >= 2:
                cage_cells = sorted([start, cand[0], cand[1]])
            elif len(cand) == 1:
                # try extend from cand[0]
                cand2 = [nb for nb in neighbors(cand[0], n) if nb in unused and nb != start]
                if cand2:
                    cage_cells = sorted([start, cand[0], cand2[0]])
                else:
                    cage_cells = None
            else:
                cage_cells = None
            if cage_cells and all(c in unused for c in cage_cells):
                for c in cage_cells:
                    unused.remove(c)
                vals = [sol[r][c] for r, c in cage_cells]
                if rng.random() < 0.65:
                    op = '+'
                    target = sum(vals)
                else:
                    op = '*'
                    p = 1
                    for v in vals: p *= v
                    target = p
                cages.append({"cells": cage_cells, "op": op, "target": target})
                continue

        pair = pick_pair()
        if pair is None:
            break
        for c in pair:
            if c in unused:
                unused.remove(c)

        vals = [sol[r][c] for r, c in pair]
        if len(pair) == 1:
            r, c = pair[0]
            cages.append({"cells": pair, "op": "=", "target": sol[r][c]})
            continue

        a, b = vals
        ops = []
        ops.append(('+', a + b))
        ops.append(('*', a * b))
        ops.append(('-', abs(a - b)))
        hi, lo = (a, b) if a >= b else (b, a)
        if lo != 0 and hi % lo == 0:
            ops.append(('÷', hi // lo))

        # choose with bias to - and ÷ (more restrictive), then * then +
        pref = {'÷': 0, '-': 1, '*': 2, '+': 3}
        ops.sort(key=lambda x: pref.get(x[0], 9))
        # add some randomness among top 2
        topk = ops[:min(2, len(ops))]
        op, target = rng.choice(topk)
        cages.append({"cells": pair, "op": op, "target": target})

    rng.shuffle(cages)
    return cages

def add_more_singletons(rng: random.Random, cages: List[Dict[str, Any]], sol: List[List[int]], k: int) -> List[Dict[str, Any]]:
    n = len(sol)
    used_single = set()
    for cg in cages:
        if cg["op"] == '=':
            used_single.add(cg["cells"][0])
    # pick cells not already singleton
    all_cells = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(all_cells)
    added = 0
    for cell in all_cells:
        if added >= k:
            break
        if cell in used_single:
            continue
        r, c = cell
        cages.append({"cells": [cell], "op": "=", "target": sol[r][c]})
        used_single.add(cell)
        added += 1
    return cages

def generate_one(rng: random.Random) -> Dict[str, Any]:
    n = rng.choice([4, 4, 5, 5, 6])
    sol = permute_square(rng, latin_square(n))

    # Try multiple times with progressive strengthening
    for _ in range(80):
        cages = make_initial_cages(rng, sol)

        # Uniqueness loop: if multiple solutions, add a few singletons and re-check
        strengthened = False
        for step in range(6):
            sols = solve_kenken(n, cages, limit=2)
            if len(sols) == 1:
                sol_use = sols[0]
                problem = statement_zh(n, cages)
                answer = grid_to_answer_string(sol_use)
                explanation = explain_zh(sol_use, cages)
                return {"problem": problem, "answer": answer, "explanation": explanation}
            if len(sols) == 0:
                break  # inconsistent, restart
            # multiple solutions -> strengthen by adding some singletons
            add_k = 1 if n == 4 else (2 if n == 5 else 3)
            cages = add_more_singletons(rng, cages, sol, add_k)
            strengthened = True

        # If we strengthened a lot and still not unique, restart with new cage partition
        _ = strengthened

    raise RuntimeError(f"生成失败：未能在预算内生成唯一解题目 (n={n})")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    out = []
    seen = set()
    tries = 0
    while len(out) < count and tries < count * 200:
        tries += 1
        item = generate_one(rng)
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    if len(out) != count:
        print(f"生成不足：{len(out)}/{count}", file=sys.stderr)
        raise SystemExit(1)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()