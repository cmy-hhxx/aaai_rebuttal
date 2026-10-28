# =========================
# File: arrow_maze_0.py
# 生成 1~MAX_BLANKS 空白且唯一解的箭头迷宫
# =========================
import random, time
from typing import List, Dict, Tuple
from itertools import product

ARROWS = ['↑', '↓', '←', '→', '↖', '↗', '↘', '↙']
DIR = {'↑': (-1, 0), '↓': (1, 0), '←': (0, -1), '→': (0, 1),
       '↖': (-1, -1), '↗': (-1, 1), '↘': (1, 1), '↙': (1, -1)}
ORTH = ['↑', '↓', '←', '→']
DIAG = ['↖', '↗', '↘', '↙']

MAX_BLANKS = 6
VERIFY_LIMIT_SEC = 6
MAX_ATTEMPT = 100


def _inside(r, c, n): return 0 <= r < n and 0 <= c < n
def _dirs(m): return ARROWS if m == 'all' else (ORTH if m == 'orth' else DIAG)


def _ray_len(bd: List[List[str]], r: int, c: int, mode: str) -> int:
    n, s = len(bd), 0
    for d in _dirs(mode):
        dr, dc = DIR[d]; nr, nc = r + dr, c + dc; seen = set()
        while _inside(nr, nc, n) and bd[nr][nc] in ARROWS:
            if (nr, nc) in seen: break
            seen.add((nr, nc)); s += 1
            d2r, d2c = DIR[bd[nr][nc]]; nr += d2r; nc += d2c
    return s


# ---------- 唯一解 ----------
def _candidate_set(bd, r, c, nums, mode):
    res = []
    for a in ARROWS:
        bd[r][c] = a
        if all(_ray_len(bd, x, y, mode) <= v for (x, y), v in nums.items()):
            res.append(a)
    bd[r][c] = 'X'
    return res or ARROWS


def _dfs(blanks, idx, bd, nums, mode, found, start):
    if time.time() - start > VERIFY_LIMIT_SEC or found[0] >= 2:
        return
    if idx == len(blanks):
        if all(_ray_len(bd, x, y, mode) == v for (x, y), v in nums.items()):
            found[0] += 1
        return
    r, c = blanks[idx]
    for a in _candidate_set(bd, r, c, nums, mode):
        bd[r][c] = a
        _dfs(blanks, idx + 1, bd, nums, mode, found, start)
        if found[0] >= 2: break
    bd[r][c] = 'X'


def unique_solution(bd: List[List[str]], nums: Dict[Tuple[int, int], int], mode: str) -> bool:
    blanks = [(r, c) for r, c in product(range(len(bd)), repeat=2) if bd[r][c] == 'X']
    if not (1 <= len(blanks) <= MAX_BLANKS): return False
    temp = [row[:] for row in bd]; found = [0]
    _dfs(blanks, 0, temp, nums, mode, found, time.time())
    return found[0] == 1


# ---------- 生成器 ----------
def generate_arrow_maze(size: int,
                        density: float,
                        mode: str,
                        target_blank: int):
    attempts = 0
    while attempts < MAX_ATTEMPT:
        attempts += 1
        # 1. 生成完整箭头
        sol = [[random.choice(ARROWS) if random.random() < density else random.choice(ARROWS)
                for _ in range(size)] for _ in range(size)]

        # 2. 随机数字格
        nums: Dict[Tuple[int, int], int] = {}
        cells = list(product(range(size), repeat=2))
        num_cnt = random.randint(max(3, size), min(len(cells) // 2, size + 4))
        for r, c in random.sample(cells, num_cnt):
            v = max(1, _ray_len(sol, r, c, mode))
            nums[(r, c)] = v
            sol[r][c] = str(v)

        # 3. 隐藏箭头
        init = [row[:] for row in sol]
        hideable = [(r, c) for r, c in cells if (r, c) not in nums]
        random.shuffle(hideable)
        hidden = 0
        for r, c in hideable:
            if hidden >= target_blank or hidden >= MAX_BLANKS: break
            init[r][c] = 'X'
            if unique_solution(init, nums, mode):
                hidden += 1
            else:
                init[r][c] = sol[r][c]

        blanks_cnt = sum(cell == 'X' for row in init for cell in row)
        if 1 <= blanks_cnt <= MAX_BLANKS and unique_solution(init, nums, mode):
            return init, sol
    # 如果 M 次后仍失败，抛异常
    raise RuntimeError('Unable to generate unique maze with required blanks')


# 占位函数
def function_1(*args, **kwargs): return args[0] if args else None
def function_2(*args, **kwargs): return ','.join(map(str, args)) if args else ''