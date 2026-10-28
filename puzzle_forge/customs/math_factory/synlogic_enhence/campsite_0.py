# -*- coding: utf-8 -*-
"""
campsite_0.py

重构版：高阶营地帐篷谜题生成与验证工具集（逆向生成 + 多层隐式约束 + 唯一解验证）。
- generate_unique_tents_puzzle: 生成随机规模与密度的唯一解实例；派生分区、棋盘、定向提示参数。
- enumerate_tent_solutions_advanced: 回溯+剪枝枚举器，支持早停(max_solutions)与时间限制(time_limit_sec)。
- function_1: 八邻域生成工具。
- function_2: 完整规则校验。
- rand_pick, rand_float: 随机辅助。
"""

from typing import List, Tuple, Set, Dict, Any
import random
import time


def rand_pick(l: List[Any]) -> Any:
    if not l:
        raise ValueError("rand_pick: empty list")
    return random.choice(l)


def rand_float(a: float, b: float) -> float:
    lo = float(a)
    hi = float(b)
    if lo > hi:
        lo, hi = hi, lo
    return random.uniform(lo, hi)


def function_1(pos: Tuple[int, int], rows: int, cols: int) -> List[Tuple[int, int]]:
    i, j = pos
    res = []
    for ni in range(max(0, i - 1), min(rows - 1, i + 1) + 1):
        for nj in range(max(0, j - 1), min(cols - 1, j + 1) + 1):
            if ni == i and nj == j:
                continue
            res.append((ni, nj))
    return res


def _orth_neighbors(pos: Tuple[int, int], rows: int, cols: int) -> List[Tuple[int, int]]:
    i, j = pos
    cand = []
    if i - 1 >= 0:
        cand.append((i - 1, j))
    if i + 1 < rows:
        cand.append((i + 1, j))
    if j - 1 >= 0:
        cand.append((i, j - 1))
    if j + 1 < cols:
        cand.append((i, j + 1))
    return cand


def function_2(grid: List[List[str]],
               tents: Set[Tuple[int, int]],
               row_constraints: List[int],
               col_constraints: List[int]) -> bool:
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    trees = [(i, j) for i in range(rows) for j in range(cols) if grid[i][j] == 'T']
    tree_count = len(trees)

    # 帐篷不在树上
    for (i, j) in tents:
        if grid[i][j] == 'T':
            return False

    # 非接触约束
    for (i, j) in tents:
        for (ni, nj) in function_1((i, j), rows, cols):
            if (ni, nj) in tents:
                return False

    # 帐篷总数等于树木总数（若不满足, 则不是合法实例）
    if len(tents) != tree_count:
        return False

    # 每个帐篷至少邻接一棵树
    for (i, j) in tents:
        if not any(grid[ti][tj] == 'T' for (ti, tj) in _orth_neighbors((i, j), rows, cols)):
            return False

    # 每棵树恰邻一个帐篷
    for (ti, tj) in trees:
        cnt = sum(((ni, nj) in tents) for (ni, nj) in _orth_neighbors((ti, tj), rows, cols))
        if cnt != 1:
            return False

    # 行列约束匹配
    row_used = [0] * rows
    col_used = [0] * cols
    for (i, j) in tents:
        row_used[i] += 1
        col_used[j] += 1
    if row_used != row_constraints:
        return False
    if col_used != col_constraints:
        return False

    return True


def enumerate_tent_solutions_advanced(grid: List[List[str]],
                                      row_constraints: List[int],
                                      col_constraints: List[int],
                                      max_solutions: int = 2,
                                      time_limit_sec: float = 150.0) -> List[List[List[str]]]:
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    trees: List[Tuple[int, int]] = [(i, j) for i in range(rows) for j in range(cols) if grid[i][j] == 'T']

    cand_by_tree: List[List[Tuple[int, int]]] = []
    for (ti, tj) in trees:
        cand = []
        for (ni, nj) in _orth_neighbors((ti, tj), rows, cols):
            if grid[ni][nj] != 'T':
                cand.append((ni, nj))
        cand_by_tree.append(cand)

    if any(len(c) == 0 for c in cand_by_tree):
        return []

    order = sorted(range(len(trees)), key=lambda k: len(cand_by_tree[k]))
    ordered_trees = [trees[k] for k in order]
    ordered_cands = [cand_by_tree[k] for k in order]

    solutions: List[List[List[str]]] = []
    used_tents: Set[Tuple[int, int]] = set()
    forbidden: Set[Tuple[int, int]] = set()
    row_used = [0] * rows
    col_used = [0] * cols
    chosen: List[Tuple[int, int]] = []

    start_time = time.time()

    def feasible_upper_bounds() -> bool:
        for i in range(rows):
            if row_used[i] > row_constraints[i]:
                return False
        for j in range(cols):
            if col_used[j] > col_constraints[j]:
                return False
        return True

    def place_tent(cell: Tuple[int, int]):
        used_tents.add(cell)
        i, j = cell
        row_used[i] += 1
        col_used[j] += 1
        forbidden.update(function_1(cell, rows, cols))

    def remove_tent(cell: Tuple[int, int]):
        used_tents.remove(cell)
        i, j = cell
        row_used[i] -= 1
        col_used[j] -= 1
        forbidden.clear()
        for (pi, pj) in used_tents:
            forbidden.update(function_1((pi, pj), rows, cols))

    def dfs(idx: int):
        if time.time() - start_time > time_limit_sec:
            return
        if len(solutions) >= max_solutions:
            return

        if idx == len(ordered_trees):
            tents_set = set(chosen)
            if function_2(grid, tents_set, row_constraints, col_constraints):
                out = [['X'] * cols for _ in range(rows)]
                for i in range(rows):
                    for j in range(cols):
                        if grid[i][j] == 'T':
                            out[i][j] = 'T'
                for (i, j) in tents_set:
                    out[i][j] = 'C'
                solutions.append(out)
            return

        for cell in ordered_cands[idx]:
            if len(solutions) >= max_solutions or time.time() - start_time > time_limit_sec:
                return
            if cell in used_tents or cell in forbidden:
                continue
            ci, cj = cell
            if row_used[ci] + 1 > row_constraints[ci]:
                continue
            if col_used[cj] + 1 > col_constraints[cj]:
                continue

            chosen.append(cell)
            place_tent(cell)
            if feasible_upper_bounds():
                dfs(idx + 1)
            remove_tent(cell)
            chosen.pop()

    dfs(0)
    return solutions


def _random_non_touching_tents(rows: int, cols: int, k: int) -> Set[Tuple[int, int]]:
    all_cells = [(i, j) for i in range(rows) for j in range(cols)]
    random.shuffle(all_cells)
    tents: Set[Tuple[int, int]] = set()
    forbidden: Set[Tuple[int, int]] = set()
    for (i, j) in all_cells:
        if (i, j) in forbidden:
            continue
        tents.add((i, j))
        forbidden.update(function_1((i, j), rows, cols))
        if len(tents) == k:
            break
    if len(tents) != k:
        return set()
    return tents


def _assign_unique_trees(rows: int, cols: int, tents: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
    trees: Set[Tuple[int, int]] = set()
    tent_list = list(tents)
    tent_list.sort(key=lambda p: len(_orth_neighbors(p, rows, cols)))

    others_orth: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}
    for t in tent_list:
        s: Set[Tuple[int, int]] = set()
        for o in tents:
            if o == t:
                continue
            s.update(_orth_neighbors(o, rows, cols))
        others_orth[t] = s

    for t in tent_list:
        cand = [nb for nb in _orth_neighbors(t, rows, cols)
                if (0 <= nb[0] < rows and 0 <= nb[1] < cols)
                and nb not in trees
                and nb not in others_orth[t]]
        random.shuffle(cand)
        if not cand:
            return set()
        trees.add(cand[0])
    return trees


def _build_zones(rows: int, cols: int, tents: Set[Tuple[int, int]],
                 max_zone_num: int = 3, trials: int = 24) -> List[Dict[str, Any]]:
    zones: List[Dict[str, Any]] = []
    used_rects: Set[Tuple[int, int, int, int]] = set()
    k = len(tents)
    zone_target = random.randint(1, max_zone_num)
    for _ in range(trials):
        if len(zones) >= zone_target:
            break
        r1 = random.randint(0, rows - 1)
        r2 = random.randint(r1, rows - 1)
        c1 = random.randint(0, cols - 1)
        c2 = random.randint(c1, cols - 1)
        rect = (r1, c1, r2, c2)
        if rect in used_rects:
            continue
        cells = [(i, j) for i in range(r1, r2 + 1) for j in range(c1, c2 + 1)]
        cnt = sum((i, j) in tents for (i, j) in cells)
        if cnt == 0 or cnt == len(cells) or cnt == k:
            if random.random() < 0.15:
                pass
            else:
                continue
        zones.append({"r1": r1, "c1": c1, "r2": r2, "c2": c2, "count": cnt})
        used_rects.add(rect)
    return zones


def _build_chess_parity(rows: int, cols: int, tents: Set[Tuple[int, int]]) -> Dict[str, Any]:
    offset = random.randint(0, 1)
    black_count = sum(1 for (i, j) in tents if ((i + j + offset) % 2 == 0))
    return {"offset": offset, "black_count": black_count}


def _build_directional_hints(rows: int, cols: int,
                             tents: Set[Tuple[int, int]],
                             trees: Set[Tuple[int, int]]) -> List[Tuple[int, int, List[str]]]:
    hints: List[Tuple[int, int, List[str]]] = []
    trees_list = list(trees)
    random.shuffle(trees_list)
    hint_num = random.randint(0, max(0, (len(trees) + 1) // 2))
    chosen = trees_list[:hint_num]

    for (ti, tj) in chosen:
        nbrs = _orth_neighbors((ti, tj), rows, cols)
        real_dirs: List[str] = []
        for (ni, nj) in nbrs:
            if (ni, nj) in tents:
                if ni == ti - 1 and nj == tj:
                    real_dirs.append('N')
                elif ni == ti + 1 and nj == tj:
                    real_dirs.append('S')
                elif ni == ti and nj == tj - 1:
                    real_dirs.append('W')
                elif ni == ti and nj == tj + 1:
                    real_dirs.append('E')
        if not real_dirs:
            continue
        real_dir = real_dirs[0]
        dirs_pool = ['N', 'S', 'W', 'E']
        dirs_pool.remove(real_dir)
        allow = [real_dir] if random.random() < 0.6 else [real_dir, random.choice(dirs_pool)]
        hints.append((ti, tj, allow))

    return hints


def generate_unique_tents_puzzle(min_rows: int, max_rows: int,
                                 min_cols: int, max_cols: int,
                                 alpha_min: float, alpha_max: float,
                                 max_tries: int = 100) -> Dict[str, Any]:
    if min_rows > max_rows or min_cols > max_cols:
        raise ValueError("min_rows/max_rows 或 min_cols/max_cols 参数不合法")

    for _ in range(max_tries):
        rows = random.randint(min_rows, max_rows)
        cols = random.randint(min_cols, max_cols)
        area = rows * cols

        lo = max(1, int(area * alpha_min))
        hi = max(lo, int(area * alpha_max))
        theoretical_cap = (area + 1) // 2
        hi = min(hi, theoretical_cap)
        if lo > hi:
            lo, hi = 1, max(1, theoretical_cap)
        k = random.randint(max(1, lo), max(1, hi))

        tents = _random_non_touching_tents(rows, cols, k)
        if not tents:
            continue

        trees = _assign_unique_trees(rows, cols, tents)
        if not trees or len(trees) != len(tents):
            continue

        grid = [['X'] * cols for _ in range(rows)]
        for (ti, tj) in trees:
            grid[ti][tj] = 'T'

        row_constraints = [0] * rows
        col_constraints = [0] * cols
        for (ci, cj) in tents:
            row_constraints[ci] += 1
            col_constraints[cj] += 1

        sols = enumerate_tent_solutions_advanced(
            grid, row_constraints, col_constraints, max_solutions=2, time_limit_sec=150.0
        )
        if len(sols) != 1:
            continue

        solution_grid = [['X'] * cols for _ in range(rows)]
        for i in range(rows):
            for j in range(cols):
                if grid[i][j] == 'T':
                    solution_grid[i][j] = 'T'
        for (ci, cj) in tents:
            solution_grid[ci][cj] = 'C'

        zones = _build_zones(rows, cols, tents, max_zone_num=3, trials=24)
        chess = _build_chess_parity(rows, cols, tents)
        dir_hints = _build_directional_hints(rows, cols, tents, set(trees))

        return {
            'grid': grid,
            'row_constraints': row_constraints,
            'col_constraints': col_constraints,
            'solution_grid': solution_grid,
            'zones': zones,
            'chess': chess,
            'dir_hints': dir_hints
        }

    raise RuntimeError("未在给定重试次数内生成唯一解实例, 请放宽参数或提高 max_tries")


# 简单自测
if __name__ == "__main__":
    random.seed()
    puzzle = generate_unique_tents_puzzle(4, 8, 3, 6, 0.2, 0.5, 300)
    print("grid:", puzzle['grid'])
    print("row_constraints:", puzzle['row_constraints'])
    print("col_constraints:", puzzle['col_constraints'])
    print("solution_grid:", puzzle['solution_grid'])
    print("zones:", puzzle['zones'])
    print("chess:", puzzle['chess'])
    print("dir_hints:", puzzle['dir_hints'])