# star_placement_puzzle_1.py
# ---------------------------------------------------------------
# Advanced Star-Battle puzzle generator with composite constraints
# ---------------------------------------------------------------
import random
import string
from typing import List, Tuple, Dict, Optional
from time import time
from z3 import Solver, Bool, Sum, If, Or, sat

# ---------- adjacency helpers ----------
def rook_neigh(i: int, j: int, n: int):
    return [(i-1, j) if i else None,
            (i+1, j) if i < n-1 else None,
            (i, j-1) if j else None,
            (i, j+1) if j < n-1 else None]

def king_neigh(i: int, j: int, n: int):
    return [(r, c)
            for r in range(max(0, i-1), min(n, i+2))
            for c in range(max(0, j-1), min(n, j+2))
            if (r, c) != (i, j)]

# ---------- uniqueness check ----------
def is_unique(s: Solver, stars) -> bool:
    if s.check() != sat:
        return False
    m = s.model()
    s.push()
    s.add(Or(*[stars[r][c] != m.eval(stars[r][c])
               for r in range(len(stars))
               for c in range(len(stars))]))
    res = s.check()
    s.pop()
    return res != sat  # False => 有多解

# ---------- generator ----------
def generate_star_battle(timeout: int = 180) -> Dict[str, object]:
    start = time()
    letters = list(string.ascii_uppercase)

    while time() - start < timeout:
        size = random.randint(5, 7)
        k = 2                                   # 提升难度：固定为2
        adjacency_mode = random.choice(["rook", "king"])
        block_used = random.choice([True, False])
        block_max = random.choice([1, 2]) if block_used else None

        diag_type: Optional[str] = random.choice(["main", "anti", None])
        diag_k = 0
        if diag_type:
            diag_k = random.choice([k, min(k + 1, size)])

        # --------- 区域划分 ----------
        region_cnt = size
        region_map = [[None]*size for _ in range(size)]
        pattern = random.choice(["row", "col", "checker", "random"])
        if pattern == "row":
            for r in range(size):
                for c in range(size):
                    region_map[r][c] = letters[r]
        elif pattern == "col":
            for c in range(size):
                for r in range(size):
                    region_map[r][c] = letters[c]
        elif pattern == "checker":
            for r in range(size):
                for c in range(size):
                    region_map[r][c] = letters[(r+c) % region_cnt]
        else:
            for r in range(size):
                for c in range(size):
                    region_map[r][c] = letters[random.randrange(region_cnt)]

        region_cells = {lt: [] for lt in letters[:region_cnt]}
        for r in range(size):
            for c in range(size):
                region_cells[region_map[r][c]].append((r, c))
        if any(len(v) < k for v in region_cells.values()):
            continue

        board = [row[:] for row in region_map]
        for _ in range(random.randint(0, size)):          # 随机障碍
            rr, cc = random.randrange(size), random.randrange(size)
            board[rr][cc] = "X"

        # --------- Z3 建模 ----------
        stars = [[Bool(f"s_{r}_{c}") for c in range(size)] for r in range(size)]
        s = Solver()
        # 障碍
        for r in range(size):
            for c in range(size):
                if board[r][c] == "X":
                    s.add(stars[r][c] == False)
        # 行列
        for r in range(size):
            s.add(Sum([If(stars[r][c], 1, 0) for c in range(size)]) == k)
        for c in range(size):
            s.add(Sum([If(stars[r][c], 1, 0) for r in range(size)]) == k)
        # 区域
        for cells in region_cells.values():
            s.add(Sum([If(stars[r][c], 1, 0) for r, c in cells]) == k)
        # 相邻
        neigh_fn = rook_neigh if adjacency_mode == "rook" else king_neigh
        for r in range(size):
            for c in range(size):
                for nr, nc in filter(None, neigh_fn(r, c, size)):
                    s.add(Or(stars[r][c] == False, stars[nr][nc] == False))
        # 2×2
        if block_used:
            for r in range(size-1):
                for c in range(size-1):
                    s.add(Sum([If(stars[r+dr][c+dc],1,0) for dr in (0,1) for dc in (0,1)]) <= block_max)
        # 对角线
        if diag_type == "main":
            s.add(Sum([If(stars[i][i],1,0) for i in range(size)]) == diag_k)
        elif diag_type == "anti":
            s.add(Sum([If(stars[i][size-1-i],1,0) for i in range(size)]) == diag_k)

        if s.check() != sat or not is_unique(s, stars):
            continue
        s.check()              # 重新获取模型（保证存在）
        model = s.model()
        solution = [(r, c) for r in range(size) for c in range(size) if model.eval(stars[r][c])]

        # 随机提示星
        hint_ratio = random.uniform(0, 0.2)
        revealed = random.sample(solution, int(len(solution)*hint_ratio))
        if revealed:
            s.push()
            for r,c in revealed:
                s.add(stars[r][c] == True)
            if not is_unique(s, stars):
                s.pop()
                continue
            s.pop()

        return {
            "size": size,
            "k": k,
            "adjacency_mode": adjacency_mode,
            "block_used": block_used,
            "block_max": block_max,
            "diag_type": diag_type,
            "diag_k": diag_k,
            "region_map": board,
            "stars": solution,
            "revealed": revealed
        }
    raise RuntimeError("Generator timeout (>180s)")

# ---------- formatting ----------
def format_coords(coords: List[Tuple[int, int]]) -> str:
    return " ".join(f"({r+1},{c+1})" for r, c in sorted(coords))