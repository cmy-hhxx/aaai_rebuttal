# calcudoko_1.py
# 自定义算子：
# - function_1(n, max_cage_size, ineq_num, seed): 生成随机解与随机化规则（笼子、不等号、属性、加权行列、区块和、链式不等、对角和、文本）
# - function_2(n): 返回 1..n 的质数列表

from typing import List, Dict, Tuple
import random

def function_2(n: int) -> List[int]:
    """返回 [1..n] 范围内的质数列表。"""
    if n < 2:
        return []
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    p = 2
    while p * p <= n:
        if sieve[p]:
            for k in range(p * p, n + 1, p):
                sieve[k] = False
        p += 1
    return [i for i in range(2, n + 1) if sieve[i]]

def _cell_id(r: int, c: int) -> str:
    return f"R{r}C{c}"

def _build_cyclic_latin(n: int) -> List[List[int]]:
    """基础循环拉丁方：((r+c) mod n) + 1。"""
    return [[((r + c) % n) + 1 for c in range(n)] for r in range(n)]

def _randomize_latin(grid: List[List[int]], n: int, rng: random.Random) -> List[List[int]]:
    """对拉丁方做值置换、行列置换，得到随机解。"""
    # 值置换
    perm = list(range(1, n + 1))
    rng.shuffle(perm)
    vmap = {i + 1: perm[i] for i in range(n)}
    grid = [[vmap[v] for v in row] for row in grid]
    # 行置换
    ridx = list(range(n))
    rng.shuffle(ridx)
    grid = [grid[i] for i in ridx]
    # 列置换
    cidx = list(range(n))
    rng.shuffle(cidx)
    grid = [[row[j] for j in cidx] for row in grid]
    return grid

def _all_adjacents(n: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """所有水平与垂直相邻坐标对（左-右、上-下）。"""
    pairs = []
    for r in range(1, n + 1):
        for c in range(1, n):
            pairs.append(((r, c), (r, c + 1)))
    for r in range(1, n):
        for c in range(1, n + 1):
            pairs.append(((r, c), (r + 1, c)))
    return pairs

def _partition_cells(n: int, max_cage_size: int, rng: random.Random) -> List[List[Tuple[int, int]]]:
    """将全部格子随机分区为若干笼子（每笼大小 1..max_cage_size）。"""
    cells = [(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]
    rng.shuffle(cells)
    res = []
    i = 0
    while i < len(cells):
        remain = len(cells) - i
        size = rng.randint(1, max_cage_size)
        size = min(size, remain)
        res.append(cells[i:i + size])
        i += size
    return res

def _cage_op_and_target(values: List[int], rng: random.Random) -> Tuple[str, int]:
    """
    按值选择可用运算与目标：
    - len==1: eq
    - len==2: 随机从 add|sub|div|mul 中选可用；div 要整除
    - len>2: add
    """
    if len(values) == 1:
        return "eq", values[0]
    if len(values) == 2:
        ops = ["add", "sub", "div", "mul"]
        rng.shuffle(ops)
        a, b = values
        for op in ops:
            if op == "add":
                return "add", a + b
            elif op == "sub":
                return "sub", abs(a - b)
            elif op == "div":
                mx, mn = (a, b) if a >= b else (b, a)
                if mn != 0 and mx % mn == 0:
                    return "div", mx // mn
            elif op == "mul":
                return "mul", a * b
        return "add", a + b
    return "add", sum(values)

def _choose_parity_enabled(rng: random.Random) -> bool:
    """以较高概率启用奇偶平衡，以提升唯一性概率。"""
    return rng.random() < 0.8

def _prop_rule_pool(n: int, rng: random.Random) -> List[Dict]:
    """构造候选的属性类型构造器，供实例化使用。"""
    primes = function_2(n)
    evens = [v for v in range(1, n + 1) if v % 2 == 0]
    odds = [v for v in range(1, n + 1) if v % 2 == 1]
    pools = []
    if primes:
        pools.append(("in_set", {"set": primes}))
    if evens:
        pools.append(("in_set", {"set": evens}))
    if odds:
        pools.append(("in_set", {"set": odds}))
    pools.append(("parity", {"parity": "odd"}))
    pools.append(("parity", {"parity": "even"}))
    for _ in range(3):
        lo = rng.randint(1, n)
        hi = rng.randint(lo, n)
        pools.append(("range", {"lo": lo, "hi": hi}))
    return pools

def _instantiate_prop_rules(grid: List[List[int]], n: int, rng: random.Random) -> List[Dict]:
    """基于解矩阵实例化若干属性规则（与解一致）。"""
    rules = []
    candidates = _prop_rule_pool(n, rng)
    total = rng.randint(max(2, n // 2), n)
    all_ids = [_cell_id(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]
    for _ in range(total):
        t, params = rng.choice(candidates)
        cell_count = rng.randint(1, max(1, n // 2))
        rng.shuffle(all_ids)
        cells = all_ids[:cell_count]
        if t == "in_set":
            pr = {"type": "in_set", "set": params["set"], "cells": []}
            for cid in cells:
                r = int(cid[1:cid.find('C')]); c = int(cid[cid.find('C') + 1:])
                if grid[r - 1][c - 1] in params["set"]:
                    pr["cells"].append(cid)
            if pr["cells"]:
                rules.append(pr)
        elif t == "parity":
            want_odd = params["parity"] == "odd"
            pr = {"type": "parity", "parity": params["parity"], "cells": []}
            for cid in cells:
                r = int(cid[1:cid.find('C')]); c = int(cid[cid.find('C') + 1:])
                if (grid[r - 1][c - 1] % 2 == 1) == want_odd:
                    pr["cells"].append(cid)
            if pr["cells"]:
                rules.append(pr)
        elif t == "range":
            lo, hi = params["lo"], params["hi"]
            pr = {"type": "range", "lo": lo, "hi": hi, "cells": []}
            for cid in cells:
                r = int(cid[1:cid.find('C')]); c = int(cid[cid.find('C') + 1:])
                v = grid[r - 1][c - 1]
                if lo <= v <= hi:
                    pr["cells"].append(cid)
            if pr["cells"]:
                rules.append(pr)
    # 额外补充若干 not_in_set 规则（小集合，确保与解不冲突）
    extras = rng.randint(1, max(1, n // 3))
    for _ in range(extras):
        all_ids2 = [_cell_id(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]
        rng.shuffle(all_ids2)
        cells = all_ids2[:rng.randint(1, max(1, n // 2))]
        s = set()
        good_cells = []
        for cid in cells:
            r = int(cid[1:cid.find('C')]); c = int(cid[cid.find('C') + 1:])
            avoid = grid[r - 1][c - 1]
            candidates_vals = [v for v in range(1, n + 1) if v != avoid]
            if candidates_vals:
                k = min(len(candidates_vals), rng.randint(1, max(1, n // 3)))
                s.update(rng.sample(candidates_vals, k))
                good_cells.append(cid)
        if good_cells:
            rules.append({"type": "not_in_set", "set": sorted(list(s)), "cells": good_cells})
    return rules

def _make_row_lin_rules(grid: List[List[int]], n: int, rng: random.Random) -> List[Dict]:
    """随机若干行的加权和规则，权重为 1..3 的小整数。"""
    count = rng.randint(2, 3)
    rows = list(range(1, n + 1))
    rng.shuffle(rows)
    res = []
    for r in rows[:count]:
        weights = [rng.randint(1, 3) for _ in range(n)]
        target = sum(grid[r - 1][c - 1] * weights[c - 1] for c in range(1, n + 1))
        res.append({"row": r, "weights": weights, "target": target})
    return res

def _make_col_lin_rules(grid: List[List[int]], n: int, rng: random.Random) -> List[Dict]:
    """随机若干列的加权和规则，权重为 1..3 的小整数。"""
    count = rng.randint(2, 3)
    cols = list(range(1, n + 1))
    rng.shuffle(cols)
    res = []
    for c in cols[:count]:
        weights = [rng.randint(1, 3) for _ in range(n)]
        target = sum(grid[r - 1][c - 1] * weights[r - 1] for r in range(1, n + 1))
        res.append({"col": c, "weights": weights, "target": target})
    return res

def _make_block_sum_rules(grid: List[List[int]], n: int, rng: random.Random) -> List[Dict]:
    """随机选取若干 2×2 区块的和约束。"""
    starts = [(r, c) for r in range(1, n) for c in range(1, n)]
    rng.shuffle(starts)
    count = rng.randint(n, min(n * (n - 1), len(starts)))
    res = []
    for (r, c) in starts[:count]:
        cells = [_cell_id(r, c), _cell_id(r, c + 1), _cell_id(r + 1, c), _cell_id(r + 1, c + 1)]
        target = grid[r - 1][c - 1] + grid[r - 1][c] + grid[r][c - 1] + grid[r][c]
        res.append({"cells": cells, "target": target})
    return res

def _make_chain_ineqs(grid: List[List[int]], n: int, rng: random.Random) -> List[Dict]:
    """生成若干长度为3的链式相邻不等关系组，ops 为 gt/lt。"""
    triples = []
    for r in range(1, n + 1):
        for c in range(1, n - 1):
            triples.append([_cell_id(r, c), _cell_id(r, c + 1), _cell_id(r, c + 2)])
    for c in range(1, n + 1):
        for r in range(1, n - 1):
            triples.append([_cell_id(r, c), _cell_id(r + 1, c), _cell_id(r + 2, c)])
    rng.shuffle(triples)
    count = rng.randint(max(n // 2, 2), n)
    res = []
    for cells in triples[:count]:
        ops = []
        vals = []
        for cid in cells:
            r = int(cid[1:cid.find('C')]); c = int(cid[cid.find('C') + 1:])
            vals.append(grid[r - 1][c - 1])
        for k in range(2):
            a, b = vals[k], vals[k + 1]
            if a == b:
                ops.append("gt")
            else:
                if rng.random() < 0.5:
                    ops.append("gt" if a > b else "lt")
                else:
                    ops.append("lt" if a < b else "gt")
        res.append({"cells": cells, "ops": ops})
    return res

def function_1(n: int, max_cage_size: int, ineq_num: int, seed: int) -> Dict[str, object]:
    """
    返回：
      grid, cages, ineqs, prop_rules, row_lin_rules, col_lin_rules,
      block_sum_rules, chain_ineqs, diag, enable_parity,
      texts: 逐条列出的规则明细（字符串）
    """
    rng = random.Random(seed)
    # 1) 随机解
    base = _build_cyclic_latin(n)
    grid = _randomize_latin(base, n, rng)

    # 2) 基础映射
    grid_map = {_cell_id(r, c): grid[r - 1][c - 1] for r in range(1, n + 1) for c in range(1, n + 1)}

    # 3) 奇偶开关
    enable_parity = _choose_parity_enabled(rng)

    # 4) 笼子
    raw_cages = _partition_cells(n, max_cage_size, rng)
    cages = []
    for cells in raw_cages:
        vals = [grid[r - 1][c - 1] for (r, c) in cells]
        op, target = _cage_op_and_target(vals, rng)
        cages.append({"cells": [_cell_id(r, c) for (r, c) in cells], "op": op, "target": target})

    # 5) 不等号
    adj = _all_adjacents(n)
    rng.shuffle(adj)
    ineqs = []
    for (a, b) in adj:
        (r1, c1), (r2, c2) = a, b
        v1 = grid[r1 - 1][c1 - 1]; v2 = grid[r2 - 1][c2 - 1]
        if v1 == v2:
            continue
        if rng.random() < 0.5:
            if v1 > v2:
                ineqs.append({"lhs": _cell_id(r1, c1), "rhs": _cell_id(r2, c2), "op": "gt"})
            else:
                ineqs.append({"lhs": _cell_id(r2, c2), "rhs": _cell_id(r1, c1), "op": "gt"})
        else:
            if v1 < v2:
                ineqs.append({"lhs": _cell_id(r1, c1), "rhs": _cell_id(r2, c2), "op": "lt"})
            else:
                ineqs.append({"lhs": _cell_id(r2, c2), "rhs": _cell_id(r1, c1), "op": "lt"})
        if len(ineqs) >= ineq_num:
            break

    # 6) 属性规则
    prop_rules = _instantiate_prop_rules(grid, n, rng)

    # 7) 复合约束
    row_lin_rules = _make_row_lin_rules(grid, n, rng)
    col_lin_rules = _make_col_lin_rules(grid, n, rng)
    block_sum_rules = _make_block_sum_rules(grid, n, rng)
    chain_ineqs = _make_chain_ineqs(grid, n, rng)

    # 8) 对角线和（概率启用）
    diag = []
    diag_long = "主对角线和未启用"
    if rng.random() < 0.6:
        cells_d = [_cell_id(i, i) for i in range(1, n + 1)]
        target_d = sum(grid[i - 1][i - 1] for i in range(1, n + 1))
        diag.append({"cells": cells_d, "target": target_d})
        diag_long = f"[{','.join(cells_d)}] sum={target_d}"

    # 9) 文本片段
    def list_cages():
        items = []
        for cg in cages:
            if cg["op"] == "add":
                items.append(f"({','.join(cg['cells'])}) sum={cg['target']}")
            elif cg["op"] == "sub":
                items.append(f"({','.join(cg['cells'])}) diff={cg['target']}")
            elif cg["op"] == "mul":
                items.append(f"({','.join(cg['cells'])}) prod={cg['target']}")
            elif cg["op"] == "div":
                items.append(f"({','.join(cg['cells'])}) div={cg['target']}")
            elif cg["op"] == "eq":
                items.append(f"({','.join(cg['cells'])}) = {cg['target']}")
        return "; ".join(items)

    def list_ineqs():
        items = []
        for i in ineqs:
            op = ">" if i["op"] == "gt" else "<"
            items.append(f"{i['lhs']} {op} {i['rhs']}")
        return "; ".join(items)

    def list_props():
        items = []
        for pr in prop_rules:
            if pr["type"] == "in_set":
                items.append(f"[{','.join(pr['cells'])}] in [{','.join(str(v) for v in pr['set'])}]")
            elif pr["type"] == "not_in_set":
                items.append(f"[{','.join(pr['cells'])}] not-in [{','.join(str(v) for v in pr['set'])}]")
            elif pr["type"] == "parity":
                items.append(f"[{','.join(pr['cells'])}] parity={pr['parity']}")
            elif pr["type"] == "range":
                items.append(f"[{','.join(pr['cells'])}] range=[{pr['lo']}..{pr['hi']}]")
        return "; ".join(items) if items else "无"

    def list_row_lin():
        items = []
        for rr in row_lin_rules:
            items.append(f"row {rr['row']} weights[{','.join(str(w) for w in rr['weights'])}] -> {rr['target']}")
        return "; ".join(items) if items else "无"

    def list_col_lin():
        items = []
        for cc in col_lin_rules:
            items.append(f"col {cc['col']} weights[{','.join(str(w) for w in cc['weights'])}] -> {cc['target']}")
        return "; ".join(items) if items else "无"

    def list_block_sum():
        items = []
        for br in block_sum_rules:
            items.append(f"[{','.join(br['cells'])}] sum={br['target']}")
        return "; ".join(items) if items else "无"

    def list_chain():
        items = []
        for ch in chain_ineqs:
            op1 = ">" if ch["ops"][0] == "gt" else "<"
            op2 = ">" if ch["ops"][1] == "gt" else "<"
            items.append(f"{ch['cells'][0]} {op1} {ch['cells'][1]} {op2} {ch['cells'][2]}")
        return "; ".join(items) if items else "无"

    cages_long = list_cages()
    ineq_long = list_ineqs()
    props_long = list_props()
    row_lin_long = list_row_lin()
    col_lin_long = list_col_lin()
    block_sum_long = list_block_sum()
    chain_long = list_chain()
    parity_text = "启用奇偶平衡：每行每列奇数与偶数各为 n/2" if enable_parity else "未启用奇偶平衡"

    return {
        "grid": grid,
        "cages": cages,
        "ineqs": ineqs,
        "prop_rules": prop_rules,
        "row_lin_rules": row_lin_rules,
        "col_lin_rules": col_lin_rules,
        "block_sum_rules": block_sum_rules,
        "chain_ineqs": chain_ineqs,
        "diag": [{"cells": d["cells"], "target": d["target"]} for d in diag] if diag else [],
        "enable_parity": enable_parity,
        "texts": {
            "cages_long": cages_long,
            "ineq_long": ineq_long,
            "props_long": props_long,
            "row_lin_long": row_lin_long,
            "col_lin_long": col_lin_long,
            "block_sum_long": block_sum_long,
            "chain_long": chain_long,
            "parity": parity_text,
            "diag_long": diag_long,
        },
    }