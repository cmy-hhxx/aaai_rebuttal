# sudoku_0.py
# Pro-level reverse Sudoku generator with composite constraints, implicit auxiliaries, and efficient uniqueness verification (< 3 minutes).
# Exposes:
#  - gen_sudoku_pro(size, box_size, clue_target, symmetry, rules_cfg, structures_cfg, seed=None, time_limit=180)
# Also keeps function_1/function_2 placeholders.

from typing import List, Dict, Any, Optional, Tuple, Set
import random
import time

def function_1(x: int) -> int:
    return x + 1

def function_2(seq: List[int]) -> List[int]:
    return list(seq)

def _make_complete_solution(size: int, box_size: int, rng: random.Random) -> List[List[int]]:
    assert box_size * box_size == size, "size must equal box_size^2 for standard Sudoku."
    base = box_size
    side = size
    def pattern(r: int, c: int) -> int:
        return (base * (r % base) + r // base + c) % side
    r_base = list(range(base))
    rows = [g * base + r for g in rng.sample(r_base, base) for r in rng.sample(r_base, base)]
    cols = [g * base + c for g in rng.sample(r_base, base) for c in rng.sample(r_base, base)]
    nums = rng.sample(range(1, side + 1), side)
    grid = [[nums[pattern(r, c)] for c in cols] for r in rows]
    return grid

_KNIGHT_DIRS = [(1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)]
_KING_DIRS   = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
_ORTHO_DIRS  = [(-1,0),(1,0),(0,-1),(0,1)]

def _solution_satisfies_base_and_diags(sol: List[List[int]], size: int, box_size: int, rules_cfg: Dict[str, bool]) -> bool:
    if rules_cfg.get('diag_main', False):
        if len({sol[i][i] for i in range(size)}) != size:
            return False
    if rules_cfg.get('diag_anti', False):
        if len({sol[i][size - 1 - i] for i in range(size)}) != size:
            return False
    return True

def _random_cells(size: int, rng: random.Random) -> List[Tuple[int, int]]:
    cells = [(r, c) for r in range(size) for c in range(size)]
    rng.shuffle(cells)
    return cells

def _gen_cages(sol: List[List[int]], size: int, target_num: int, min_sz: int, max_sz: int, rng: random.Random) -> List[Dict[str, Any]]:
    cages = []
    used: Set[Tuple[int,int]] = set()
    attempts = 0
    while len(cages) < target_num and attempts < 2000:
        attempts += 1
        cells = _random_cells(size, rng)
        for (r, c) in cells:
            if (r, c) in used:
                continue
            k = rng.randint(min_sz, max_sz)
            cage = [(r, c)]
            neighbors = [(r+dr, c+dc) for dr, dc in _ORTHO_DIRS if 0 <= r+dr < size and 0 <= c+dc < size]
            rng.shuffle(neighbors)
            for (rr, cc) in neighbors:
                if len(cage) >= k:
                    break
                if (rr, cc) not in used and (rr, cc) not in cage:
                    cage.append((rr, cc))
            if len(cage) < k:
                more = [xy for xy in cells if xy not in used and xy not in cage]
                rng.shuffle(more)
                cage += more[:(k - len(cage))]
            if len(cage) != k:
                continue
            digits = [sol[rr][cc] for (rr, cc) in cage]
            if len(set(digits)) != len(digits):
                continue
            s = sum(digits)
            cages.append({"cells": cage, "sum": s, "no_repeat": True})
            for xy in cage:
                used.add(xy)
            break
    return cages

def _gen_thermos(sol: List[List[int]], size: int, target_num: int, min_len: int, max_len: int, rng: random.Random) -> List[List[Tuple[int,int]]]:
    thermos: List[List[Tuple[int,int]]] = []
    attempts = 0
    while len(thermos) < target_num and attempts < 3000:
        attempts += 1
        start_cells = _random_cells(size, rng)
        for (r, c) in start_cells:
            length = rng.randint(min_len, max_len)
            path = [(r, c)]
            for _ in range(length - 1):
                nbrs = [(path[-1][0]+dr, path[-1][1]+dc) for dr, dc in _ORTHO_DIRS]
                nbrs = [(rr, cc) for (rr, cc) in nbrs if 0 <= rr < size and 0 <= cc < size and (rr, cc) not in path]
                if not nbrs:
                    path = []
                    break
                path.append(rng.choice(nbrs))
            if not path or len(path) != length:
                continue
            if all(sol[path[i][0]][path[i][1]] < sol[path[i+1][0]][path[i+1][1]] for i in range(length - 1)):
                thermos.append(path)
                break
    return thermos

def _gen_arrows(sol: List[List[int]], size: int, target_num: int, min_len: int, max_len: int, rng: random.Random) -> List[Dict[str, Any]]:
    arrows: List[Dict[str, Any]] = []
    attempts = 0
    while len(arrows) < target_num and attempts < 3000:
        attempts += 1
        start_cells = _random_cells(size, rng)
        for (r, c) in start_cells:
            length = rng.randint(min_len, max_len)
            path = [(r, c)]
            for _ in range(length - 1):
                nbrs = [(path[-1][0]+dr, path[-1][1]+dc) for dr, dc in _ORTHO_DIRS]
                nbrs = [(rr, cc) for (rr, cc) in nbrs if 0 <= rr < size and 0 <= cc < size and (rr, cc) not in path]
                if not nbrs:
                    path = []
                    break
                path.append(rng.choice(nbrs))
            if not path or len(path) != length:
                continue
            s = sum(sol[rr][cc] for (rr, cc) in path)
            if s > 9:
                continue
            candidates = [(rr, cc) for rr in range(size) for cc in range(size) if sol[rr][cc] == s and (rr, cc) not in path]
            if not candidates:
                continue
            circle = rng.choice(candidates)
            arrows.append({"circle": circle, "path": path, "sum": s})
            break
    return arrows

def _gen_parity(sol: List[List[int]], size: int, even_num: int, odd_num: int, rng: random.Random) -> Dict[str, List[Tuple[int,int]]]:
    even_cells = [(r, c) for r in range(size) for c in range(size) if sol[r][c] % 2 == 0]
    odd_cells = [(r, c) for r in range(size) for c in range(size) if sol[r][c] % 2 == 1]
    rng.shuffle(even_cells)
    rng.shuffle(odd_cells)
    return {"even_cells": even_cells[:even_num], "odd_cells": odd_cells[:odd_num]}

def _count_solutions_composite(board: List[List[int]], size: int, box_size: int, rules_cfg: Dict[str, bool], structures: Dict[str, Any], limit: int, time_limit: float, start_time: float) -> int:
    side = size
    digits = range(1, side + 1)
    def box_index(r: int, c: int) -> int:
        return (r // box_size) * box_size + (c // box_size)
    row_used = [set() for _ in range(side)]
    col_used = [set() for _ in range(side)]
    box_used = [set() for _ in range(side)]
    diag_main_used = set()
    diag_anti_used = set()
    cages = structures.get("cages", [])
    thermos = structures.get("thermos", [])
    arrows = structures.get("arrows", [])
    parity_even_cells = set(structures.get("parity_even_cells", []))
    parity_odd_cells = set(structures.get("parity_odd_cells", []))
    cell_to_cage: Dict[Tuple[int,int], int] = {}
    for ci, cage in enumerate(cages):
        for xy in cage["cells"]:
            cell_to_cage[tuple(xy)] = ci
    cell_to_thermo: Dict[Tuple[int,int], Tuple[int,int]] = {}
    for ti, path in enumerate(thermos):
        for pos, xy in enumerate(path):
            cell_to_thermo[tuple(xy)] = (ti, pos)
    cell_to_arrow_path: Dict[Tuple[int,int], int] = {}
    cell_to_arrow_circle: Dict[Tuple[int,int], int] = {}
    for ai, arrow in enumerate(arrows):
        for xy in arrow["path"]:
            cell_to_arrow_path[tuple(xy)] = ai
        cell_to_arrow_circle[tuple(arrow["circle"])] = ai
    cage_sum_assigned = [0 for _ in cages]
    cage_assigned_cells: List[Set[int]] = [set() for _ in cages]
    arrow_path_sum_assigned = [0 for _ in arrows]
    arrow_path_remaining = [len(arrows[i]["path"]) for i in range(len(arrows))]
    arrow_circle_value = [None for _ in arrows]
    for r in range(side):
        for c in range(side):
            v = board[r][c]
            if v:
                row_used[r].add(v)
                col_used[c].add(v)
                box_used[box_index(r, c)].add(v)
                if rules_cfg.get('diag_main', False) and r == c:
                    diag_main_used.add(v)
                if rules_cfg.get('diag_anti', False) and r + c == side - 1:
                    diag_anti_used.add(v)
                xy = (r, c)
                if xy in cell_to_cage:
                    ci = cell_to_cage[xy]
                    cage_sum_assigned[ci] += v
                    cage_assigned_cells[ci].add(v)
                if xy in cell_to_arrow_path:
                    ai = cell_to_arrow_path[xy]
                    arrow_path_sum_assigned[ai] += v
                    arrow_path_remaining[ai] -= 1
                if xy in cell_to_arrow_circle:
                    ai = cell_to_arrow_circle[xy]
                    arrow_circle_value[ai] = v
    blanks = [(r, c) for r in range(side) for c in range(side) if board[r][c] == 0]
    def candidates(r: int, c: int) -> List[int]:
        used = row_used[r] | col_used[c] | box_used[box_index(r, c)]
        if rules_cfg.get('diag_main', False) and r == c:
            used |= diag_main_used
        if rules_cfg.get('diag_anti', False) and r + c == side - 1:
            used |= diag_anti_used
        xy = (r, c)
        if xy in parity_even_cells:
            base_cands = [d for d in digits if d not in used and d in (2,4,6,8)]
        elif xy in parity_odd_cells:
            base_cands = [d for d in digits if d not in used and d in (1,3,5,7,9)]
        else:
            base_cands = [d for d in digits if d not in used]
        if not base_cands:
            return []
        def ok(v: int) -> bool:
            if rules_cfg.get('anti_knight', False):
                for dr, dc in _KNIGHT_DIRS:
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < side and 0 <= cc < side:
                        w = board[rr][cc]
                        if w != 0 and w == v:
                            return False
            if rules_cfg.get('anti_king', False):
                for dr, dc in _KING_DIRS:
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < side and 0 <= cc < side:
                        w = board[rr][cc]
                        if w != 0 and w == v:
                            return False
            if rules_cfg.get('non_consecutive', False):
                for dr, dc in _ORTHO_DIRS:
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < side and 0 <= cc < side:
                        w = board[rr][cc]
                        if w != 0 and abs(v - w) == 1:
                            return False
            if xy in cell_to_cage:
                ci = cell_to_cage[xy]
                target = cages[ci]["sum"]
                current = cage_sum_assigned[ci]
                k_left = len(cages[ci]["cells"]) - len(cage_assigned_cells[ci])
                if cages[ci].get("no_repeat", False) and v in cage_assigned_cells[ci]:
                    return False
                if current + v > target:
                    return False
                min_possible = current + v + (k_left - 1) * 1
                max_possible = current + v + (k_left - 1) * 9
                if min_possible > target or max_possible < target:
                    return False
            if xy in cell_to_thermo:
                ti, pos = cell_to_thermo[xy]
                path = thermos[ti]
                if pos - 1 >= 0:
                    pr = path[pos - 1]
                    w = board[pr[0]][pr[1]]
                    if w != 0 and not (w < v):
                        return False
                if pos + 1 < len(path):
                    su = path[pos + 1]
                    w = board[su[0]][su[1]]
                    if w != 0 and not (v < w):
                        return False
            if xy in cell_to_arrow_path:
                ai = cell_to_arrow_path[xy]
                circle_val = arrow_circle_value[ai]
                current_sum = arrow_path_sum_assigned[ai]
                remaining_after = arrow_path_remaining[ai] - 1
                new_sum = current_sum + v
                if circle_val is not None:
                    if new_sum > circle_val:
                        return False
                    if new_sum + remaining_after * 1 > circle_val:
                        return False
                else:
                    if new_sum > 9:
                        return False
            if xy in cell_to_arrow_circle:
                ai = cell_to_arrow_circle[xy]
                current_sum = arrow_path_sum_assigned[ai]
                remaining = arrow_path_remaining[ai]
                min_sum = current_sum + remaining * 1
                max_sum = current_sum + remaining * 9
                if not (min_sum <= v <= max_sum):
                    return False
            return True
        return [v for v in base_cands if ok(v)]
    def select_blank() -> Optional[Tuple[int, int, List[int]]]:
        best = None
        best_cands = None
        for (r, c) in blanks:
            if board[r][c] != 0:
                continue
            cands = candidates(r, c)
            if not cands:
                return None
            if best is None or len(cands) < len(best_cands):
                best = (r, c)
                best_cands = cands
                if len(best_cands) == 1:
                    break
        if best is None:
            return None
        return best[0], best[1], best_cands
    count = 0
    def backtrack():
        nonlocal count
        if count >= limit:
            return
        if time.time() - start_time > time_limit:
            return
        sel = select_blank()
        if sel is None:
            for rr in range(side):
                for cc in range(side):
                    if board[rr][cc] == 0:
                        return
            for ci, cage in enumerate(cages):
                if cage_sum_assigned[ci] != cage["sum"]:
                    return
            for ai, arrow in enumerate(arrows):
                if arrow_circle_value[ai] is None:
                    return
                if arrow_circle_value[ai] != arrow_path_sum_assigned[ai]:
                    return
            count += 1
            return
        r, c, cands = sel
        bi = box_index(r, c)
        for v in cands:
            board[r][c] = v
            row_used[r].add(v)
            col_used[c].add(v)
            box_used[bi].add(v)
            dm_added = False
            da_added = False
            if rules_cfg.get('diag_main', False) and r == c:
                diag_main_used.add(v); dm_added = True
            if rules_cfg.get('diag_anti', False) and r + c == side - 1:
                diag_anti_used.add(v); da_added = True
            xy = (r, c)
            if xy in cell_to_cage:
                ci = cell_to_cage[xy]
                cage_sum_assigned[ci] += v
                cage_assigned_cells[ci].add(v)
            if xy in cell_to_arrow_path:
                ai = cell_to_arrow_path[xy]
                arrow_path_sum_assigned[ai] += v
                arrow_path_remaining[ai] -= 1
            if xy in cell_to_arrow_circle:
                ai = cell_to_arrow_circle[xy]
                arrow_circle_value[ai] = v
            backtrack()
            if xy in cell_to_arrow_circle:
                ai = cell_to_arrow_circle[xy]
                arrow_circle_value[ai] = None
            if xy in cell_to_arrow_path:
                ai = cell_to_arrow_path[xy]
                arrow_path_remaining[ai] += 1
                arrow_path_sum_assigned[ai] -= v
            if xy in cell_to_cage:
                ci = cell_to_cage[xy]
                cage_assigned_cells[ci].remove(v)
                cage_sum_assigned[ci] -= v
            if da_added:
                diag_anti_used.remove(v)
            if dm_added:
                diag_main_used.remove(v)
            box_used[bi].remove(v)
            col_used[c].remove(v)
            row_used[r].remove(v)
            board[r][c] = 0
            if count >= limit or time.time() - start_time > time_limit:
                return
    backtrack()
    return count

def _make_puzzle_from_solution(sol: List[List[int]], size: int, box_size: int, clue_target: int, symmetry: bool, rules_cfg: Dict[str, bool], structures: Dict[str, Any], rng: random.Random, time_limit: float) -> List[List[int]]:
    side = size
    board = [row[:] for row in sol]
    def symmetric_pos(r: int, c: int) -> Tuple[int, int]:
        return (side - 1 - r, side - 1 - c)
    positions = [(r, c) for r in range(side) for c in range(side)]
    rng.shuffle(positions)
    clues = side * side
    target = max(17, min(clue_target, side * side))
    visited = set()
    start_time = time.time()
    for (r, c) in positions:
        if clues <= target or time.time() - start_time > time_limit:
            break
        if (r, c) in visited:
            continue
        r2, c2 = symmetric_pos(r, c)
        to_remove = [(r, c)]
        if symmetry and (r2, c2) != (r, c):
            to_remove.append((r2, c2))
        if any(board[rr][cc] == 0 for (rr, cc) in to_remove):
            visited.update(to_remove); continue
        saved_vals = [board[rr][cc] for (rr, cc) in to_remove]
        for (rr, cc) in to_remove:
            board[rr][cc] = 0
        sol_count = _count_solutions_composite([row[:] for row in board], size, box_size, rules_cfg, structures, limit=2, time_limit=max(1.0, time_limit - (time.time() - start_time)), start_time=start_time)
        if sol_count == 1:
            clues -= len(to_remove)
        else:
            for (idx, (rr, cc)) in enumerate(to_remove):
                board[rr][cc] = saved_vals[idx]
        visited.update(to_remove)
    if clues > target and symmetry and (time.time() - start_time) < time_limit:
        flat_positions = [(r, c) for r in range(side) for c in range(side)]
        rng.shuffle(flat_positions)
        for (r, c) in flat_positions:
            if clues <= target or time.time() - start_time > time_limit:
                break
            if board[r][c] == 0:
                continue
            saved = board[r][c]
            board[r][c] = 0
            if _count_solutions_composite([row[:] for row in board], size, box_size, rules_cfg, structures, limit=2, time_limit=max(1.0, time_limit - (time.time() - start_time)), start_time=start_time) == 1:
                clues -= 1
            else:
                board[r][c] = saved
    return board

def _build_rule_text(rules_cfg: Dict[str, bool]) -> str:
    parts = []
    if rules_cfg.get('diag_main', False):
        parts.append('主对角线不重复: 从左上到右下的对角线上数字互不相同')
    if rules_cfg.get('diag_anti', False):
        parts.append('副对角线不重复: 从右上到左下的对角线上数字互不相同')
    if rules_cfg.get('anti_knight', False):
        parts.append('反马步: 任何马步距离的两个格子不允许放相同数字')
    if rules_cfg.get('anti_king', False):
        parts.append('反王: 任何相邻（含对角）两个格子不允许放相同数字')
    if rules_cfg.get('non_consecutive', False):
        parts.append('不连续: 任意正交相邻的两个格子上的数字不允许相差1')
    if not parts:
        parts.append('无额外变体规则: 仅遵循标准数独规则')
    return '; '.join(parts)

def _coord_str(c: Tuple[int,int]) -> str:
    return f"(r{c[0]+1},c{c[1]+1})"

def _build_shapes_text(structures: Dict[str, Any]) -> str:
    parts = []
    cages = structures.get("cages", [])
    if cages:
        cages_desc = []
        for i, cage in enumerate(cages, 1):
            cells = ','.join(_coord_str(tuple(xy)) for xy in cage["cells"])
            cages_desc.append(f"C{i}: sum={cage['sum']}, cells=[{cells}]")
        parts.append("Killer加法区: " + '; '.join(cages_desc))
    thermos = structures.get("thermos", [])
    if thermos:
        thermo_desc = []
        for i, path in enumerate(thermos, 1):
            cells = '->'.join(_coord_str(tuple(xy)) for xy in path)
            thermo_desc.append(f"T{i}: path={cells}")
        parts.append("温度计(严格递增): " + '; '.join(thermo_desc))
    arrows = structures.get("arrows", [])
    if arrows:
        arrow_desc = []
        for i, a in enumerate(arrows, 1):
            circle = _coord_str(tuple(a["circle"]))
            path = '+'.join(_coord_str(tuple(xy)) for xy in a["path"])
            arrow_desc.append(f"A{i}: circle={circle}, sum(path)={a['sum']}, path=[{path}]")
        parts.append("箭头(圆圈等于箭头路径之和): " + '; '.join(arrow_desc))
    even_cells = structures.get("parity_even_cells", [])
    odd_cells = structures.get("parity_odd_cells", [])
    if even_cells or odd_cells:
        pe = ','.join(_coord_str(tuple(xy)) for xy in even_cells)
        po = ','.join(_coord_str(tuple(xy)) for xy in odd_cells)
        if pe:
            parts.append("偶性提示: 偶数格 " + pe)
        if po:
            parts.append("奇性提示: 奇数格 " + po)
    if not parts:
        parts.append("无结构线索")
    return '; '.join(parts)

def gen_sudoku_pro(size: int, box_size: int, clue_target: int, symmetry: bool, rules_cfg: Dict[str, bool], structures_cfg: Dict[str, Any], seed: Optional[int] = None, time_limit: float = 180.0) -> Dict[str, Any]:
    rng = random.Random(seed)
    attempts = 0
    cfg = dict(rules_cfg)
    while True:
        sol = _make_complete_solution(size, box_size, rng)
        if _solution_satisfies_base_and_diags(sol, size, box_size, cfg):
            break
        attempts += 1
        if attempts > 2000:
            cfg['diag_main'] = False
            cfg['diag_anti'] = False
            break
    structures: Dict[str, Any] = {}
    if structures_cfg.get('use_cages', False) and structures_cfg.get('cage_num', 0) > 0:
        cages = _gen_cages(sol, size, structures_cfg['cage_num'], structures_cfg['cage_min_size'], structures_cfg['cage_max_size'], rng)
        structures["cages"] = cages
    if structures_cfg.get('use_thermos', False) and structures_cfg.get('thermo_num', 0) > 0:
        thermos = _gen_thermos(sol, size, structures_cfg['thermo_num'], structures_cfg['thermo_min_len'], structures_cfg['thermo_max_len'], rng)
        structures["thermos"] = thermos
    if structures_cfg.get('use_arrows', False) and structures_cfg.get('arrow_num', 0) > 0:
        arrows = _gen_arrows(sol, size, structures_cfg['arrow_num'], structures_cfg['arrow_min_len'], structures_cfg['arrow_max_len'], rng)
        structures["arrows"] = arrows
    if structures_cfg.get('use_parity', False):
        parity = _gen_parity(sol, size, structures_cfg.get('parity_even_num', 0), structures_cfg.get('parity_odd_num', 0), rng)
        structures["parity_even_cells"] = parity["even_cells"]
        structures["parity_odd_cells"] = parity["odd_cells"]
    rule_text = _build_rule_text(cfg)
    shapes_text = _build_shapes_text(structures)
    givens = _make_puzzle_from_solution(sol, size, box_size, clue_target, symmetry, cfg, structures, rng, time_limit=time_limit)
    return {"givens": givens, "solution": sol, "rule_text": rule_text, "shapes_text": shapes_text}