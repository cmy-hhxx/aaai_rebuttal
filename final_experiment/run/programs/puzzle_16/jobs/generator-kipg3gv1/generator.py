import sys, json, random, itertools
from typing import List, Tuple, Dict, Any, Optional

# We generate KenKen-like puzzles (Latin square with cage constraints).
# Output language: Chinese (zh) as requested.

def latin_square(n: int) -> List[List[int]]:
    return [[((r + c) % n) + 1 for c in range(n)] for r in range(n)]

def permute_square(rng: random.Random, grid: List[List[int]]) -> List[List[int]]:
    n = len(grid)
    # permute symbols
    perm = list(range(1, n + 1))
    rng.shuffle(perm)
    mp = {i + 1: perm[i] for i in range(n)}
    g = [[mp[v] for v in row] for row in grid]

    # permute rows and cols
    rows = list(range(n))
    cols = list(range(n))
    rng.shuffle(rows)
    rng.shuffle(cols)
    g2 = [[g[rows[r]][cols[c]] for c in range(n)] for r in range(n)]
    return g2

def neighbors(cell: Tuple[int, int], n: int):
    r, c = cell
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < n and 0 <= cc < n:
            yield (rr, cc)

def op_apply(values: List[int], op: str) -> Optional[int]:
    if op == '+':
        return sum(values)
    if op == '*':
        prod = 1
        for v in values:
            prod *= v
        return prod
    if op == '-':
        if len(values) != 2:
            return None
        a, b = values
        return abs(a - b)
    if op == '÷':
        if len(values) != 2:
            return None
        a, b = values
        hi, lo = (a, b) if a >= b else (b, a)
        if lo == 0: 
            return None
        if hi % lo != 0:
            return None
        return hi // lo
    if op == '=':
        if len(values) != 1:
            return None
        return values[0]
    return None

def op_valid(values: List[int], op: str, target: int) -> bool:
    t = op_apply(values, op)
    return t == target

def format_cage(cells: List[Tuple[int,int]], target: int, op: str) -> str:
    # Coordinates are 1-based in statement
    coords = ''.join([f"({r+1},{c+1})" for r,c in cells])
    if op == '=':
        return f"{coords}:{target}"
    else:
        return f"{coords}:{target}{op}"

def grid_to_answer_string(grid: List[List[int]]) -> str:
    rows = [ ' '.join(str(x) for x in row) for row in grid ]
    return "[[" + ",".join(rows) + "]]"

def build_cages_from_solution(rng: random.Random, sol: List[List[int]]) -> List[Dict[str, Any]]:
    n = len(sol)
    all_cells = [(r,c) for r in range(n) for c in range(n)]
    rng.shuffle(all_cells)
    unassigned = set(all_cells)
    cages = []
    # bias cage sizes
    if n <= 4:
        size_choices = [1,2,2,3]
    elif n == 5:
        size_choices = [1,2,2,3,3,4]
    else:
        size_choices = [1,2,2,3,3,4,4]
    while unassigned:
        start = next(iter(unassigned))
        # grow a connected cage
        max_size = rng.choice(size_choices)
        cage_cells = [start]
        unassigned.remove(start)
        frontier = [start]
        while len(cage_cells) < max_size and frontier:
            cur = frontier.pop(0)
            nbrs = [nb for nb in neighbors(cur, n) if nb in unassigned]
            rng.shuffle(nbrs)
            if nbrs:
                nb = nbrs[0]
                cage_cells.append(nb)
                unassigned.remove(nb)
                frontier.append(nb)
                frontier.append(cur)  # allow further growth around
        # choose operator based on size
        vals = [sol[r][c] for r,c in cage_cells]
        if len(cage_cells) == 1:
            op = '='
            target = vals[0]
        elif len(cage_cells) == 2:
            a,b = vals
            ops = []
            ops.append(('+', a+b))
            ops.append(('*', a*b))
            ops.append(('-', abs(a-b)))
            hi, lo = (a,b) if a>=b else (b,a)
            if lo != 0 and hi % lo == 0:
                ops.append(('÷', hi//lo))
            # pick an op with some balance
            rng.shuffle(ops)
            # avoid too many '+' on large n to keep variety
            preferred = ['÷','-','*','+']
            ops.sort(key=lambda x: preferred.index(x[0]) if x[0] in preferred else 99)
            op, target = ops[0]
        else:
            # size >=3: use + or *
            if rng.random() < 0.6:
                op = '+'
                target = sum(vals)
            else:
                op = '*'
                prod = 1
                for v in vals:
                    prod *= v
                op = '*'
                target = prod
        cages.append({"cells": cage_cells, "op": op, "target": target})
    # canonicalize cell order for stable printing: sort by (r,c)
    for cg in cages:
        cg["cells"] = sorted(cg["cells"])
    # randomize cage order in statement
    rng.shuffle(cages)
    return cages

def solve_kenken(n: int, cages: List[Dict[str, Any]], limit: int = 2) -> List[List[List[int]]]:
    try:
        import z3
    except Exception as e:
        raise RuntimeError("需要 z3 库") from e

    X = [[z3.Int(f"x_{r}_{c}") for c in range(n)] for r in range(n)]
    s = z3.Solver()

    # domain and latin constraints
    for r in range(n):
        for c in range(n):
            s.add(X[r][c] >= 1, X[r][c] <= n)
    for r in range(n):
        s.add(z3.Distinct(X[r]))
    for c in range(n):
        s.add(z3.Distinct([X[r][c] for r in range(n)]))

    # cage constraints
    for cage in cages:
        cells = cage["cells"]
        op = cage["op"]
        target = cage["target"]
        vars_ = [X[r][c] for (r,c) in cells]

        # numbers in each region cannot repeat (given in rule)
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
            if len(vars_) != 2:
                return []
            a,b = vars_
            s.add(z3.Or(a - b == target, b - a == target))
        elif op == '÷':
            if len(vars_) != 2:
                return []
            a,b = vars_
            # a/b == target or b/a == target with exact division
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
        # block this solution
        s.add(z3.Or([X[r][c] != sol[r][c] for r in range(n) for c in range(n)]))
    return sols

def statement_zh(n: int, cages: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append(f"网格大小为 {n}×{n}。请在每一行、每一列填入 1 到 {n}，且每行每列不重复。")
    lines.append("网格被划分为若干“笼区”，每个笼区给出坐标、目标数与运算符；笼区内数字不重复，且按给定运算得到目标数。")
    lines.append("坐标格式为(行,列)，行列从1开始。运算规则：")
    lines.append("  + 表示求和；* 表示求积；- 表示两数之差的绝对值；÷ 表示两数相除得到整数商（顺序不定）；单格笼区直接等于目标数。")
    lines.append("笼区条件如下：")
    for cg in cages:
        op = cg["op"]
        target = cg["target"]
        cells = cg["cells"]
        if op == '=':
            lines.append("  " + format_cage(cells, target, op))
        else:
            lines.append("  " + format_cage(cells, target, op))
    lines.append("请按从左到右、从上到下给出答案：每行用空格分隔，行与行之间用逗号分隔，最外层用双中括号包裹，例如 [[1 2,3 4]]。")
    return "\n".join(lines)

def explain_zh(sol: List[List[int]], cages: List[Dict[str, Any]]) -> str:
    # Provide concise verifiable evidence: show each cage computed from solution.
    parts = []
    parts.append("校验要点：该解每行每列均为1..N的一个排列；并逐笼区代入满足目标。")
    n = len(sol)
    # row/col checks brief
    parts.append(f"行校验示例：第1行为 {' '.join(map(str, sol[0]))}；列校验示例：第1列为 {' '.join(str(sol[r][0]) for r in range(n))}。")
    parts.append("笼区代入：")
    for cg in cages:
        cells = cg["cells"]
        vals = [sol[r][c] for r,c in cells]
        op = cg["op"]
        target = cg["target"]
        if op == '=':
            expr = f"{vals[0]}"
        elif op == '+':
            expr = " + ".join(map(str, vals))
        elif op == '*':
            expr = " * ".join(map(str, vals))
        elif op == '-':
            expr = f"|{vals[0]} - {vals[1]}|"
        elif op == '÷':
            a,b = vals
            hi, lo = (a,b) if a>=b else (b,a)
            expr = f"{hi} ÷ {lo}"
        else:
            expr = "?"
        got = op_apply(vals, op)
        parts.append(f"  {format_cage(cells, target, op)}：取值{vals}，{expr} = {got}，匹配目标{target}。")
    return "\n".join(parts)

def generate_one(rng: random.Random, idx: int) -> Dict[str, Any]:
    # choose size and variant
    n = rng.choice([4,4,5,5,6])  # bias to 4-6 like seed
    base = latin_square(n)
    sol = permute_square(rng, base)

    # build cages and ensure unique solution
    for _attempt in range(200):
        cages = build_cages_from_solution(rng, sol)

        # Ensure enough cages and not too many singletons
        singletons = sum(1 for cg in cages if cg["op"] == '=')
        if singletons > max(2, n//2):
            continue

        sols = solve_kenken(n, cages, limit=2)
        if len(sols) != 1:
            continue
        if sols[0] != sol:
            # In rare cases due to symbol/row perm, might mismatch; accept solver's unique sol as truth
            sol = sols[0]

        problem = statement_zh(n, cages)
        answer = grid_to_answer_string(sol)
        explanation = explain_zh(sol, cages)

        return {"problem": problem, "answer": answer, "explanation": explanation}

    raise RuntimeError(f"生成失败：在给定预算内未能生成唯一解题目 (n={n})")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    out = []
    seen = set()
    # bounded retries for duplicates / failures
    tries = 0
    while len(out) < count and tries < count * 60:
        tries += 1
        item = generate_one(rng, len(out))
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    if len(out) != count:
        print(f"仅生成 {len(out)}/{count} 道题（可能因为唯一解约束导致采样不足）", file=sys.stderr)
        # If insufficient, raise to be explicit per requirements
        raise SystemExit(1)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()