# star_placement_puzzle_0.py
import random, string, json
from typing import Dict, List, Tuple
import itertools

# custom operator for yaml
def json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False)

def get_region_cells(grid: List[List[str]]) -> Dict[str, List[Tuple[int, int]]]:
    d: Dict[str, List[Tuple[int, int]]] = {}
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            d.setdefault(ch, []).append((r, c))
    return d

def get_adjacent_pairs(size: int, include_diag: bool = True):
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if include_diag:
        moves.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
    pairs = []
    for r in range(size):
        for c in range(size):
            for dr, dc in moves:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size and (r, c) < (nr, nc):
                    pairs.append(((r, c), (nr, nc)))
    return pairs

# grid generator
_BASE = [[2, 2, 2, 0],
         [2, 3, 0, 0],
         [1, 1, 1, 0],
         [3, 1, 3, 3]]

def _rot(mat): return [list(reversed(col)) for col in zip(*mat)]
def _mirror(mat): return [row[::-1] for row in mat]

def generate_random_grid():
    g = [row[:] for row in _BASE]
    for _ in range(random.randint(0, 3)):
        g = _rot(g)
    if random.choice([True, False]):
        g = _mirror(g)
    letters = random.sample(string.ascii_uppercase, 4)
    m = {i: letters[i] for i in range(4)}
    return [[m[v] for v in row] for row in g]

def star_positions_json(model, star_dict, region_cells):
    ans = {k: [] for k in region_cells}
    for k, cells in region_cells.items():
        for r, c in sorted(cells):
            if bool(model.evaluate(star_dict[(str(r), str(c))], model_completion=True)):
                ans[k].append([r + 1, c + 1])
    return json.dumps(ans, ensure_ascii=False)