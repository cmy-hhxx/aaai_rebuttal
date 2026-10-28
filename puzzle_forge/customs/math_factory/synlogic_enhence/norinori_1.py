# norinori_5.py （与上一版相同，已确保包含 generate_unique_puzzle 与 format_dominoes）
import random
from typing import List, Tuple, Dict
from z3 import Solver, Bool, And, Or, Not, AtLeast, AtMost, sat

GridCoord = Tuple[int, int]
Domino = Tuple[int, int, int, int]

def format_dominoes(doms: List[Domino]) -> str:
    return ",".join(f"({a},{b},{c},{d})" for a, b, c, d in doms)

def _all_cells(n: int):
    return [(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]

def _adjacent_pairs(n: int):
    return [(r, c, r, c + 1) for r in range(1, n + 1) for c in range(1, n)] + \
           [(r, c, r + 1, c) for r in range(1, n) for c in range(1, n + 1)]

def _exactly_one(bools):
    return And(AtLeast(*bools, 1), AtMost(*bools, 1))

def _random_x_coords(num: int, n: int, cap: int):
    cells = _all_cells(n)
    while True:
        xs = random.sample(cells, num)
        row = [0]*(n+1)
        col = [0]*(n+1)
        for r, c in xs:
            row[r] += 1
            col[c] += 1
        if max(row) <= cap and max(col) <= cap:
            return xs

def _unique_domino_cover(n: int, X: List[GridCoord], timeout=600):
    doms = _adjacent_pairs(n)
    v = {d: Bool(f"d{d}") for d in doms}
    inc = {c: [] for c in _all_cells(n)}
    for d, sym in v.items():
        inc[(d[0], d[1])].append(sym)
        inc[(d[2], d[3])].append(sym)

    s = Solver()
    s.set(timeout=timeout)
    for cell, lst in inc.items():
        if cell in X:
            s.add(And(Not(b) for b in lst))
        else:
            s.add(_exactly_one(lst))

    if s.check() != sat:
        return None
    m = s.model()
    sol = [d for d, sym in v.items() if m.evaluate(sym)]

    s.add(Or([sym if not m.evaluate(sym) else Not(sym) for sym in v.values()]))
    if s.check() == sat:
        return None
    return sorted(sol)

def generate_unique_puzzle(n: int, max_x: int, attempts=500):
    for k in range(max_x, 8, -1):
        for _ in range(attempts):
            X = _random_x_coords(k, n, 3)
            doms = _unique_domino_cover(n, X)
            if doms:
                return {"X": X, "D": doms}
    fallback_X = [(1,2),(1,5),(2,3),(2,6),(3,1),(3,4),
                  (4,2),(4,5),(5,3),(6,4),(6,1),(5,6)]
    doms = _unique_domino_cover(6, fallback_X)
    return {"X": fallback_X, "D": doms}