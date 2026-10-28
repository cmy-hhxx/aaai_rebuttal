# sudoku_0.py
import random
from typing import List, Tuple, Dict
import z3

# --------------- 工具与参数 ---------------

def _rng(seed: int) -> random.Random:
    r = random.Random()
    r.seed(seed)
    return r

def _sqrt_int(n: int) -> int:
    # 适配9x9数独（block 3x3），保留扩展性
    for k in range(1, n + 1):
        if k * k == n:
            return k
    raise ValueError("dim must be a perfect square.")

def _sym_pair(symmetry: str, i: int, j: int, dim: int) -> Tuple[int, int]:
    n = dim - 1
    if symmetry == 'central':
        return (n - i, n - j)
    elif symmetry == 'horizontal':
        return (n - i, j)
    elif symmetry == 'vertical':
        return (i, n - j)
    elif symmetry == 'diagonal':
        # 主对角线镜像
        return (j, i)
    else:
        # none: 自身
        return (i, j)

def _rows_str_from_matrix(matrix: List[List[int]]) -> List[str]:
    return [''.join([str(v) if v != 0 else 'X' for v in row]) for row in matrix]

# --------------- 生成完整解 ---------------

def function_1(seed: int) -> List[List[int]]:
    """
    生成一个完整合法的9x9数独解（可复现）。
    基于3x3块的行/列分组与数字随机重排。
    """
    base = 3
    side = base * base
    rnd = _rng(seed)

    def pattern(r, c):
        return (base * (r % base) + r // base + c) % side

    rBase = list(range(base))
    rows = [g * base + r for g in rnd.sample(rBase, base) for r in rnd.sample(rBase, base)]
    cols = [g * base + c for g in rnd.sample(rBase, base) for c in rnd.sample(rBase, base)]
    nums = rnd.sample(list(range(1, side + 1)), side)

    grid = [[nums[pattern(r, c)] for c in cols] for r in rows]
    return grid

# --------------- Z3 建模与唯一性检测 ---------------

def _build_solver(givens: List[List[int]], timeout_ms: int = 300) -> Tuple[z3.Solver, List[List[z3.IntNumRef]]]:
    dim = len(givens)
    b = _sqrt_int(dim)
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    cell = [[z3.Int(f"X_{i}_{j}") for j in range(dim)] for i in range(dim)]
    # 范围
    for i in range(dim):
        for j in range(dim):
            s.add(cell[i][j] >= 1, cell[i][j] <= dim)
    # 行列唯一
    for i in range(dim):
        s.add(z3.Distinct(*cell[i]))
    for j in range(dim):
        s.add(z3.Distinct(*[cell[i][j] for i in range(dim)]))
    # 块唯一
    for br in range(0, dim, b):
        for bc in range(0, dim, b):
            s.add(z3.Distinct(*[cell[i][j] for i in range(br, br + b) for j in range(bc, bc + b)]))
    # 给定
    for i in range(dim):
        for j in range(dim):
            if givens[i][j] != 0:
                s.add(cell[i][j] == givens[i][j])
    return s, cell

def _unique_and_solution(givens: List[List[int]], timeout_ms: int = 300) -> Tuple[bool, List[List[int]]]:
    dim = len(givens)
    s, cell = _build_solver(givens, timeout_ms)
    if s.check() != z3.sat:
        return (False, [])
    m = s.model()
    sol = [[m.eval(cell[i][j]).as_long() for j in range(dim)] for i in range(dim)]
    # second check
    s2, cell2 = _build_solver(givens, timeout_ms)
    s2.add(z3.Or(*[cell2[i][j] != sol[i][j] for i in range(dim) for j in range(dim)]))
    uniq = (s2.check() != z3.sat)
    return (uniq, sol)

# --------------- 难度评估（稳定化） ---------------

def _rate_nodes(givens: List[List[int]], repeats: int, seed: int) -> int:
    """
    回溯节点数作为近似难度。为了稳定：
      - 候选选择顺序固定：最少候选优先；
      - 多次测量（不同内部扰动）取中位数。
    """
    scores = []
    for k in range(repeats):
        rnd = _rng(seed + 7919 * (k + 1))
        scores.append(_rate_by_backtrack(givens, rnd))
    scores.sort()
    mid = scores[len(scores) // 2]
    return mid

def _rate_by_backtrack(givens: List[List[int]], rnd: random.Random) -> int:
    dim = len(givens)
    b = _sqrt_int(dim)

    rows = [set(range(1, dim + 1)) for _ in range(dim)]
    cols = [set(range(1, dim + 1)) for _ in range(dim)]
    boxes = [set(range(1, dim + 1)) for _ in range(dim)]

    def box_id(i, j): return (i // b) * b + (j // b)

    grid = [[0] * dim for _ in range(dim)]
    for i in range(dim):
        for j in range(dim):
            v = givens[i][j]
            if v:
                grid[i][j] = v
                rows[i].discard(v)
                cols[j].discard(v)
                boxes[box_id(i, j)].discard(v)

    nodes = 0

    def candidates(i, j):
        if grid[i][j] != 0:
            return []
        return list(rows[i] & cols[j] & boxes[box_id(i, j)])

    def select_cell():
        best = None
        best_len = dim + 1
        for i in range(dim):
            for j in range(dim):
                if grid[i][j] == 0:
                    cand = candidates(i, j)
                    ln = len(cand)
                    if ln < best_len:
                        best = (i, j, cand)
                        best_len = ln
                        if best_len <= 1:
                            return best
        return best

    def dfs():
        nonlocal nodes
        sel = select_cell()
        if sel is None:
            return True
        i, j, cand = sel
        if len(cand) == 0:
            return False
        # 固定顺序：减少波动（仍加入轻微随机扰动以避免偏置）
        rnd.shuffle(cand)
        cand.sort()
        for v in cand:
            nodes += 1
            grid[i][j] = v
            rows[i].discard(v)
            cols[j].discard(v)
            boxes[box_id(i, j)].discard(v)
            if dfs():
                return True
            grid[i][j] = 0
            rows[i].add(v)
            cols[j].add(v)
            boxes[box_id(i, j)].add(v)
        return False

    dfs()
    return nodes

def _target_band(diff: str) -> Tuple[int, int]:
    # 经验区间；可根据需要调整
    if diff == 'easy':
        return (0, 80)
    elif diff == 'medium':
        return (80, 250)
    elif diff == 'hard':
        return (250, 1200)
    else:
        return (1200, 9999999)

# --------------- 题面构造（严格对称 + 约束维护） ---------------

def function_2(sol_grid: List[List[int]],
               difficulty: str,
               symmetry: str,
               minimal_clue: bool,
               min_clues: int,
               max_clues: int,
               block_min_per_box: bool,
               seed: int) -> Dict[str, List]:
    """
    从完整解出发，严格对称化挖洞：
      - 初始给定：从完整解开始（全给定），只通过对称成对移除；
      - 任意移除操作同时检查两个位置所在块的最小给定数（如启用）；
      - 始终保持对称；
      - 始终验证唯一性（双解检测，含Z3超时保护）；
      - 调整线索数到[min_clues, max_clues]范围；
      - 难度通过回溯节点数的中位数近似评估并筛选；
      - 可选最小题面：尽量移除所有非必要的对称线索（保持唯一与目标难度区间）。
    """
    dim = len(sol_grid)
    b = _sqrt_int(dim)
    rnd = _rng(seed)

    # 初始为完整给定
    givens = [row[:] for row in sol_grid]

    def clue_count() -> int:
        return sum(1 for i in range(dim) for j in range(dim) if givens[i][j] != 0)

    def block_count(i: int, j: int) -> int:
        br = (i // b) * b
        bc = (j // b) * b
        return sum(1 for ii in range(br, br + b) for jj in range(bc, bc + b) if givens[ii][jj] != 0)

    def can_remove_pair(i: int, j: int) -> bool:
        ii, jj = _sym_pair(symmetry, i, j, dim)
        # 自身对称时（none 或对角线上）视为单点移除
        pts = {(i, j), (ii, jj)}
        # 块最小给定约束
        if block_min_per_box:
            # 对每个受影响的块，移除后至少保留1个给定
            # 计算每个块的现状
            blocks = set()
            for (x, y) in pts:
                blocks.add(((x // b) * b, (y // b) * b))
            for (br, bc) in blocks:
                cnt = sum(1 for xx in range(br, br + b) for yy in range(bc, bc + b) if givens[xx][yy] != 0)
                # 若此块中移除的点位于此块中，移除数量为该块内落在pts的个数
                rm = sum(1 for xx in range(br, br + b) for yy in range(bc, bc + b) if (xx, yy) in pts and givens[xx][yy] != 0)
                if cnt - rm < 1:
                    return False
        # 试移除并检查唯一性
        removed = []
        for (x, y) in pts:
            if givens[x][y] != 0:
                removed.append((x, y, givens[x][y]))
                givens[x][y] = 0
        uniq, _ = _unique_and_solution(givens)
        # 回滚
        for (x, y, v) in removed:
            givens[x][y] = v
        return uniq

    # 候选坐标集：对称去重（只考虑一半）
    coords = []
    seen = set()
    for i in range(dim):
        for j in range(dim):
            ii, jj = _sym_pair(symmetry, i, j, dim)
            key = tuple(sorted([(i, j), (ii, jj)]))
            if key not in seen:
                seen.add(key)
                coords.append((i, j))
    rnd.shuffle(coords)

    # 目标线索数（在区间内取一个随机目标）
    target_clues = rnd.randint(min_clues, max_clues)

    # 从完整给定向 target_clues 挖洞
    for (i, j) in coords:
        if clue_count() <= target_clues:
            break
        if givens[i][j] == 0:
            continue
        ii, jj = _sym_pair(symmetry, i, j, dim)
        # 同时撤销两个位置（对称），若唯一性保持则应用
        if can_remove_pair(i, j):
            prev1, prev2 = givens[i][j], givens[ii][jj]
            givens[i][j] = 0
            givens[ii][jj] = 0

    # 如果线索数仍大于max_clues，继续尝试移除；如果小于min_clues，随机回填保持对称
    attempts = 0
    while (clue_count() > max_clues or clue_count() < min_clues) and attempts < 200:
        attempts += 1
        if clue_count() > max_clues:
            # 尝试继续移除
            rnd.shuffle(coords)
            progress = False
            for (i, j) in coords:
                if givens[i][j] == 0:
                    continue
                if can_remove_pair(i, j):
                    ii, jj = _sym_pair(symmetry, i, j, dim)
                    givens[i][j] = 0
                    givens[ii][jj] = 0
                    progress = True
                    if clue_count() <= max_clues:
                        break
            if not progress:
                break
        else:
            # 小于最小线索，成对回填
            rnd.shuffle(coords)
            progress = False
            for (i, j) in coords:
                if givens[i][j] != 0:
                    continue
                ii, jj = _sym_pair(symmetry, i, j, dim)
                # 回填后仍须唯一
                prev1, prev2 = givens[i][j], givens[ii][jj]
                givens[i][j] = sol_grid[i][j]
                givens[ii][jj] = sol_grid[ii][jj]
                uniq, _ = _unique_and_solution(givens)
                if uniq:
                    progress = True
                    if clue_count() >= min_clues:
                        break
                else:
                    # 回滚
                    givens[i][j], givens[ii][jj] = prev1, prev2
            if not progress:
                break

    # 再次确保唯一性
    uniq, _ = _unique_and_solution(givens)
    if not uniq:
        # 若失败，返回较保守的题面（全部给定），由框架丢弃该实例
        return {'matrix': [row[:] for row in sol_grid],
                'rows': _rows_str_from_matrix(sol_grid),
                'clues': dim * dim,
                'nodes': 0,
                'difficulty_band': 'easy',
                'symmetry': symmetry}

    # 难度评估与调整（有限次）
    nodes_min, nodes_max = _target_band(difficulty)
    adjust_limit = 120
    k = 0
    while k < adjust_limit:
        k += 1
        nodes = _rate_nodes(givens, repeats=3, seed=seed + 13331)
        if nodes_min <= nodes <= nodes_max:
            break
        if nodes > nodes_max and clue_count() < max_clues:
            # 太难：成对回填（保持唯一）
            rnd.shuffle(coords)
            adjusted = False
            for (i, j) in coords:
                if givens[i][j] != 0:
                    continue
                ii, jj = _sym_pair(symmetry, i, j, dim)
                prev1, prev2 = givens[i][j], givens[ii][jj]
                givens[i][j] = sol_grid[i][j]
                givens[ii][jj] = sol_grid[ii][jj]
                u2, _ = _unique_and_solution(givens)
                if u2:
                    adjusted = True
                    break
                else:
                    givens[i][j], givens[ii][jj] = prev1, prev2
            if not adjusted:
                break
        elif nodes < nodes_min and clue_count() > min_clues:
            # 太易：成对移除（保持唯一）
            rnd.shuffle(coords)
            adjusted = False
            for (i, j) in coords:
                if givens[i][j] == 0:
                    continue
                if can_remove_pair(i, j):
                    ii, jj = _sym_pair(symmetry, i, j, dim)
                    givens[i][j] = 0
                    givens[ii][jj] = 0
                    adjusted = True
                    break
            if not adjusted:
                break
        else:
            break

    # 最小题面：贪心移除所有非必要对称线索（保持唯一、难度区间、线索范围和块约束）
    if minimal_clue:
        order = [(i, j) for i in range(dim) for j in range(dim) if givens[i][j] != 0]
        # 对称去重
        unique_seeds = []
        used = set()
        for (i, j) in order:
            ii, jj = _sym_pair(symmetry, i, j, dim)
            key = tuple(sorted([(i, j), (ii, jj)]))
            if key not in used:
                used.add(key)
                unique_seeds.append((i, j))
        rnd.shuffle(unique_seeds)
        for (i, j) in unique_seeds:
            if clue_count() <= min_clues:
                break
            # 测试移除
            if givens[i][j] == 0:
                continue
            ii, jj = _sym_pair(symmetry, i, j, dim)
            # 移除并测试
            prev1, prev2 = givens[i][j], givens[ii][jj]
            givens[i][j] = 0
            givens[ii][jj] = 0
            # 线索范围
            if clue_count() < min_clues:
                givens[i][j], givens[ii][jj] = prev1, prev2
                continue
            # 唯一性与难度
            u2, _ = _unique_and_solution(givens)
            if not u2:
                givens[i][j], givens[ii][jj] = prev1, prev2
                continue
            cur_nodes = _rate_nodes(givens, repeats=3, seed=seed + 9001)
            if not (nodes_min <= cur_nodes <= nodes_max):
                givens[i][j], givens[ii][jj] = prev1, prev2
                continue
            # 块约束（如启用）
            if block_min_per_box:
                # 若移除违反块最小线索，则回滚
                ok = True
                for (x, y) in {(i, j), (ii, jj)}:
                    br = (x // b) * b; bc = (y // b) * b
                    cnt = sum(1 for xx in range(br, br + b) for yy in range(bc, bc + b) if givens[xx][yy] != 0)
                    if cnt < 1:
                        ok = False
                        break
                if not ok:
                    givens[i][j], givens[ii][jj] = prev1, prev2
                    continue

    # 返回前最终线索数校验与微调
    attempts2 = 0
    while (clue_count() < min_clues or clue_count() > max_clues) and attempts2 < 100:
        attempts2 += 1
        if clue_count() < min_clues:
            # 回填
            rnd.shuffle(coords)
            changed = False
            for (i, j) in coords:
                if givens[i][j] != 0:
                    continue
                ii, jj = _sym_pair(symmetry, i, j, dim)
                prev1, prev2 = givens[i][j], givens[ii][jj]
                givens[i][j] = sol_grid[i][j]
                givens[ii][jj] = sol_grid[ii][jj]
                u2, _ = _unique_and_solution(givens)
                if u2:
                    changed = True
                    break
                else:
                    givens[i][j], givens[ii][jj] = prev1, prev2
            if not changed:
                break
        else:
            # 移除
            rnd.shuffle(coords)
            changed = False
            for (i, j) in coords:
                if givens[i][j] == 0:
                    continue
                if can_remove_pair(i, j):
                    ii, jj = _sym_pair(symmetry, i, j, dim)
                    givens[i][j] = 0
                    givens[ii][jj] = 0
                    changed = True
                    break
            if not changed:
                break

    # 再次唯一性检查
    uniq, _ = _unique_and_solution(givens)
    if not uniq:
        # 失败，返回完整给定（由框架丢弃）
        return {'matrix': [row[:] for row in sol_grid],
                'rows': _rows_str_from_matrix(sol_grid),
                'clues': dim * dim,
                'nodes': 0,
                'difficulty_band': 'easy',
                'symmetry': symmetry}

    final_nodes = _rate_nodes(givens, repeats=3, seed=seed + 4243)
    band = difficulty
    lo, hi = _target_band(difficulty)
    if not (lo <= final_nodes <= hi):
        # 调整失败时，标注为近似难度带（仅信息，不影响约束）
        if final_nodes < 80:
            band = 'easy'
        elif final_nodes < 250:
            band = 'medium'
        elif final_nodes < 1200:
            band = 'hard'
        else:
            band = 'expert'

    matrix = [row[:] for row in givens]
    rows_str = _rows_str_from_matrix(matrix)
    return {
        'matrix': matrix,
        'rows': rows_str,
        'clues': clue_count(),
        'nodes': final_nodes,
        'difficulty_band': band,
        'symmetry': symmetry
    }