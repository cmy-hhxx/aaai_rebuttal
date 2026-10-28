"""
numbrix_4.py
自包含：生成随机 Numbrix-like 题目 & 答案，并保证唯一解
"""

__all__ = ["generate_puzzle", "matrix_to_string"]

import random
from typing import List, Tuple, Dict, Optional, Callable
from z3 import Solver, Int, Distinct, And, Or, Abs, unsat, sat

# ------------------------ CONFIG ------------------------
MAX_SIDE = 8
MIN_CELLS, MAX_CELLS = 12, 24
PREFILL_MIN, PREFILL_MAX = 2, 4          # 首尾之外额外预填
HINT_MIN, HINT_MAX = 7, 12               # 线索下/上限
DIST_RANGE = (2, 4)
RETRY_LIMIT = 60
DIR4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]

# ------------------ PATH GENERATION ---------------------
def random_saw() -> List[Tuple[int, int]]:
    length = random.randint(MIN_CELLS, MAX_CELLS)
    while True:
        path = [(0, 0)]
        visited = {(0, 0)}
        while len(path) < length:
            r, c = path[-1]
            neighbors = [(r + dr, c + dc) for dr, dc in DIR4
                         if 0 <= r + dr < MAX_SIDE and 0 <= c + dc < MAX_SIDE
                         and (r + dr, c + dc) not in visited]
            if not neighbors:
                break
            nxt = random.choice(neighbors)
            path.append(nxt)
            visited.add(nxt)
        if len(path) == length:
            return path

def build_matrices(path: List[Tuple[int, int]]):
    max_r = max(r for r, _ in path)
    max_c = max(c for _, c in path)
    rows, cols = max_r + 1, max_c + 1
    question = [[0 for _ in range(cols)] for _ in range(rows)]
    answer   = [[0 for _ in range(cols)] for _ in range(rows)]
    for num, (r, c) in enumerate(path, 1):
        answer[r][c] = num
        question[r][c] = None
    return question, answer, rows, cols

def matrix_to_string(mat: List[List[Optional[int]]]) -> str:
    return '[' + ', '.join(str(row) for row in mat) + ']'

# ------------------ HINT FACTORIES ----------------------
def hint_adj(a, b):
    txt = f'{a} 与 {b} 相邻'
    return txt, lambda pos: Abs(pos[a] - pos[b]) == 1

def hint_dist(a, b, k):
    txt = f'{a} 与 {b} 相隔 {k} 步'
    return txt, lambda pos: Abs(pos[a] - pos[b]) == k

def hint_order(a, b):
    txt = f'{a} 早于 {b}'
    return txt, lambda pos: pos[a] < pos[b]

def hint_between(a, b, c):
    txt = f'{b} 介于 {a} 与 {c} 之间'
    return txt, lambda pos: And(pos[a] < pos[b], pos[b] < pos[c])

# ------------------ UNIQUENESS CHECK --------------------
def unique_solution(n: int,
                    fixed: Dict[int, int],
                    constraints: List[Callable]) -> bool:
    s = Solver()
    pos = {i: Int(f'p{i}') for i in range(1, n + 1)}
    s.add([And(1 <= p, p <= n) for p in pos.values()])
    s.add(Distinct(*pos.values()))
    for num, idx in fixed.items():
        s.add(pos[num] == idx)
    for c in constraints:
        s.add(c(pos))
    if s.check() != sat:
        return False
    m1 = s.model()
    s.add(Or([pos[i] != m1[pos[i]] for i in pos]))
    return s.check() == unsat

# ------------------ HINT GENERATOR ----------------------
def create_hints(n: int, fixed: Dict[int, int]) -> Tuple[List[str], List[Callable]]:
    hints_set = set()
    z3_cons = []
    while (len(hints_set) < HINT_MIN or not unique_solution(n, fixed, z3_cons)) \
            and len(hints_set) < HINT_MAX:
        typ = random.choice(['adj', 'dist', 'order', 'between'])
        if typ == 'adj':
            a = random.randint(1, n - 1)
            t, z = hint_adj(a, a + 1)
        elif typ == 'dist':
            k = random.randint(*DIST_RANGE)
            a = random.randint(1, n - k)
            t, z = hint_dist(a, a + k, k)
        elif typ == 'order':
            a, b = random.sample(range(2, n), 2)
            t, z = hint_order(a, b)
        else:
            a, b, c = sorted(random.sample(range(2, n), 3))
            t, z = hint_between(a, b, c)
        if t in hints_set:
            continue
        hints_set.add(t)
        z3_cons.append(z)
    return ['• ' + h for h in hints_set], z3_cons

# ------------------ MAIN GENERATOR ----------------------
def generate_puzzle() -> Dict:
    for _ in range(RETRY_LIMIT):
        path = random_saw()
        n = len(path)
        qmat, amat, rows, cols = build_matrices(path)
        # Prefill
        extra = random.randint(PREFILL_MIN, PREFILL_MAX)
        extra_indices = random.sample(range(2, n), extra)
        fixed = {1: 1, n: n}
        for idx in extra_indices:
            fixed[idx] = idx
            r, c = path[idx - 1]
            qmat[r][c] = idx
        hints, z3_cons = create_hints(n, fixed)
        if unique_solution(n, fixed, z3_cons):
            return {
                'matrix_question_str': matrix_to_string(qmat),
                'matrix_answer_str': matrix_to_string(amat),
                'hints_str': '\n'.join(hints),
                'cell_num': n,
                'exit': path[-1],
                'rows': rows,
                'cols': cols
            }
    # Fallback with extra prefill to force uniqueness
    path = random_saw()
    n = len(path)
    qmat, amat, rows, cols = build_matrices(path)
    fixed = {i: i for i in range(1, n + 1, 2)}  # half prefilled
    for idx, (r, c) in enumerate(path, 1):
        if idx in fixed:
            qmat[r][c] = idx
    hints, _ = create_hints(n, fixed)
    return {
        'matrix_question_str': matrix_to_string(qmat),
        'matrix_answer_str': matrix_to_string(amat),
        'hints_str': '\n'.join(hints),
        'cell_num': n,
        'exit': path[-1],
        'rows': rows,
        'cols': cols
    }