# numbrix_0.py
# 自定义算子文件，供 YAML 的 custom_operator 引用。
# 注意：仅定义并暴露在 YAML 中使用的函数。

from typing import Dict, List, Tuple
import random
from z3 import And, Or, Implies, Sum, BoolVal  # 用于构造 Z3 约束

def build_neighbors(size: int) -> Dict[Tuple[int, int], List[Tuple[int, int]]]:
    """
    构造每个单元格的正交邻接坐标列表。
    输入:
        size: 网格边长 n
    输出:
        一个字典，键为 (i, j)，值为该格的正交邻居坐标列表 [(ni, nj), ...]
    """
    nbrs: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    for i in range(size):
        for j in range(size):
            lst: List[Tuple[int, int]] = []
            if i - 1 >= 0:
                lst.append((i - 1, j))
            if i + 1 < size:
                lst.append((i + 1, j))
            if j - 1 >= 0:
                lst.append((i, j - 1))
            if j + 1 < size:
                lst.append((i, j + 1))
            nbrs[(i, j)] = lst
    return nbrs

def clue_bounds_min(size: int) -> int:
    # 适度下调线索下界，避免显见线索
    if size <= 5:
        return 8
    if size == 6:
        return 10
    return 12  # size == 7

def clue_bounds_max(size: int) -> int:
    # 适度下调线索上界
    if size <= 5:
        return 12
    if size == 6:
        return 15
    return 17  # size == 7

def adj_pair_cap(size: int) -> int:
    # 控制 (v,v+1) 已知相邻对的上限，避免显见链式填数
    if size <= 5:
        return 2
    if size == 6:
        return 3
    return 4  # size == 7

def choose_anchors(size: int, n: int, anchor_num: int) -> List[Tuple[int, int, int]]:
    """
    选择若干锚点用于第一阶段求解以打破对称：
    - 优先在角上放置 1
    - 若 anchor_num>=2，则将 2 放在 1 的正交邻居之一（当前 YAML 仅使用 anchor_num=1）
    返回三元组列表: [(i, j, v), ...]
    """
    corners = [(0, 0), (0, size - 1), (size - 1, 0), (size - 1, size - 1)]
    i1, j1 = random.choice(corners)
    anchors: List[Tuple[int, int, int]] = [(i1, j1, 1)]
    if anchor_num >= 2:
        nbrs: List[Tuple[int, int]] = []
        if i1 - 1 >= 0: nbrs.append((i1 - 1, j1))
        if i1 + 1 < size: nbrs.append((i1 + 1, j1))
        if j1 - 1 >= 0: nbrs.append((i1, j1 - 1))
        if j1 + 1 < size: nbrs.append((i1, j1 + 1))
        if nbrs:
            i2, j2 = random.choice(nbrs)
            anchors.append((i2, j2, 2))
    return anchors

def _find_value_pos(ans_grid: List[List[int]], value: int) -> Tuple[int, int]:
    s = len(ans_grid)
    for i in range(s):
        for j in range(s):
            if ans_grid[i][j] == value:
                return (i, j)
    raise ValueError("value not found in ans_grid")

def _adjacent_pair_count(values: List[int]) -> int:
    st = set(values)
    cnt = 0
    for v in st:
        if v + 1 in st:
            cnt += 1
    return cnt

def choose_clue_positions(size: int,
                          ans_grid: List[List[int]],
                          min_clues: int,
                          max_clues: int,
                          max_adj_pair: int) -> List[Tuple[int, int]]:
    """
    基于完整解 ans_grid 选择线索位置集合：
    - 必须包含 1 与 n 的位置
    - 目标线索数 target ∈ [min_clues, max_clues]
    - 控制 (v, v+1) 已知相邻对数量不超过 max_adj_pair
    - 尽量分散位置
    """
    n = size * size
    target = random.randint(min_clues, max_clues)
    pos_set = set()

    # 必含 1 与 n
    p1 = _find_value_pos(ans_grid, 1)
    pn = _find_value_pos(ans_grid, n)
    pos_set.add(p1)
    pos_set.add(pn)

    all_positions = [(i, j) for i in range(size) for j in range(size)]
    random.shuffle(all_positions)

    def ok_to_add(p: Tuple[int, int]) -> bool:
        r, c = p
        row_count = sum(1 for (i, j) in pos_set if i == r)
        col_count = sum(1 for (i, j) in pos_set if j == c)
        row_cap = max(2, size // 2)
        col_cap = max(2, size // 2)
        if row_count >= row_cap or col_count >= col_cap:
            return False
        return True

    attempts = 0
    while len(pos_set) < target and attempts < size * size * 10:
        attempts += 1
        p = random.choice(all_positions)
        if p in pos_set:
            continue
        if not ok_to_add(p):
            continue
        tmp_vals = [ans_grid[i][j] for (i, j) in pos_set] + [ans_grid[p[0]][p[1]]]
        if _adjacent_pair_count(tmp_vals) <= max_adj_pair:
            pos_set.add(p)

    attempts2 = 0
    while len(pos_set) < target and attempts2 < size * size * 10:
        attempts2 += 1
        p = random.choice(all_positions)
        if p in pos_set:
            continue
        tmp_vals = [ans_grid[i][j] for (i, j) in pos_set] + [ans_grid[p[0]][p[1]]]
        if _adjacent_pair_count(tmp_vals) <= max_adj_pair:
            pos_set.add(p)

    if len(pos_set) > target:
        pos_list = list(pos_set)
        random.shuffle(pos_list)
        pos_list = pos_list[:target]
        pos_set = set(pos_list)

    return list(pos_set)

def dir_bounds_min(size: int) -> int:
    if size <= 5:
        return 1
    if size == 6:
        return 2
    return 2  # size == 7

def dir_bounds_max(size: int) -> int:
    if size <= 5:
        return 3
    if size == 6:
        return 4
    return 5  # size == 7

def choose_direction_clues(size: int,
                           ans_grid: List[List[int]],
                           min_dir: int,
                           max_dir: int) -> List[Tuple[int, str]]:
    """
    从解中选取若干方向线索：(v, 'U'/'D'/'L'/'R')，表示 v+1 在该方向。
    避免选取端点 v=1 或 v=n-1。
    """
    n = size * size
    candidates: List[Tuple[int, str]] = []
    for v in range(1, n):
        i, j = _find_value_pos(ans_grid, v)
        dir_char = None
        if i - 1 >= 0 and ans_grid[i - 1][j] == v + 1:
            dir_char = 'U'
        elif i + 1 < size and ans_grid[i + 1][j] == v + 1:
            dir_char = 'D'
        elif j - 1 >= 0 and ans_grid[i][j - 1] == v + 1:
            dir_char = 'L'
        elif j + 1 < size and ans_grid[i][j + 1] == v + 1:
            dir_char = 'R'
        if dir_char is not None:
            if v not in (1, n - 1):
                candidates.append((v, dir_char))
    random.shuffle(candidates)
    target = random.randint(min_dir, max_dir) if candidates else 0
    return candidates[:target]

def expand_dir_clues(dir_clues: List[Tuple[int, str]]) -> List[Tuple[int, int, int]]:
    """
    将方向线索 (v, 'U'/'D'/'L'/'R') 扩展为 (v, di, dj) 形式。
    """
    vecs = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1)}
    out: List[Tuple[int, int, int]] = []
    for v, d in dir_clues:
        di, dj = vecs[d]
        out.append((v, di, dj))
    return out

def row_bounds_min(size: int) -> int:
    if size <= 5:
        return 0
    if size == 6:
        return 1
    return 1

def row_bounds_max(size: int) -> int:
    if size <= 5:
        return 1
    if size == 6:
        return 2
    return 3

def choose_row_sums(size: int,
                    ans_grid: List[List[int]],
                    min_rows: int,
                    max_rows: int) -> List[Tuple[int, int]]:
    rows = list(range(size))
    random.shuffle(rows)
    target = random.randint(min_rows, max_rows) if rows else 0
    chosen = rows[:target]
    return [(r, sum(ans_grid[r])) for r in chosen]

def monotonic_cap(size: int) -> int:
    if size <= 5:
        return 1
    if size == 6:
        return 2
    return 2  # size == 7

def choose_monotonic_lines(size: int,
                           ans_grid: List[List[int]],
                           max_lines: int) -> List[Tuple[str, int, str]]:
    """
    在解中筛选本身严格单调的行/列：
    返回 ('row', idx, 'inc'/'dec') 或 ('col', idx, 'inc'/'dec')
    """
    candidates: List[Tuple[str, int, str]] = []

    # 行候选
    for r in range(size):
        inc = all(ans_grid[r][j] < ans_grid[r][j + 1] for j in range(size - 1))
        dec = all(ans_grid[r][j] > ans_grid[r][j + 1] for j in range(size - 1))
        if inc:
            candidates.append(('row', r, 'inc'))
        elif dec:
            candidates.append(('row', r, 'dec'))

    # 列候选
    for c in range(size):
        inc = all(ans_grid[i][c] < ans_grid[i + 1][c] for i in range(size - 1))
        dec = all(ans_grid[i][c] > ans_grid[i + 1][c] for i in range(size - 1))
        if inc:
            candidates.append(('col', c, 'inc'))
        elif dec:
            candidates.append(('col', c, 'dec'))

    random.shuffle(candidates)
    return candidates[:max_lines]

def decide_parity_enable(size: int) -> bool:
    # 依据尺寸决定启用奇偶约束的概率
    if size <= 5:
        p = 0.5
    elif size == 6:
        p = 0.6
    else:
        p = 0.7
    return random.random() < p

def seg_bounds_min(size: int) -> int:
    if size <= 5:
        return 1
    if size == 6:
        return 1
    return 2  # size == 7

def seg_bounds_max(size: int) -> int:
    if size <= 5:
        return 2
    if size == 6:
        return 3
    return 3  # size == 7

def seg_len_min(size: int) -> int:
    return 3

def seg_len_max(size: int) -> int:
    if size <= 5:
        return 5
    if size == 6:
        return 6
    return 6  # size == 7

def _value_pos_map(ans_grid: List[List[int]]) -> Dict[int, Tuple[int, int]]:
    s = len(ans_grid)
    mp: Dict[int, Tuple[int, int]] = {}
    for i in range(s):
        for j in range(s):
            mp[ans_grid[i][j]] = (i, j)
    return mp

def choose_orient_segments(size: int,
                           ans_grid: List[List[int]],
                           min_seg: int,
                           max_seg: int,
                           min_len: int,
                           max_len: int) -> List[Tuple[int, int, str]]:
    """
    从完整解中识别相邻方向一致的区段，随机选取若干段作为提示：
    返回列表 [(start_v, end_v, 'row'/'col')].
    """
    n = size * size
    mp = _value_pos_map(ans_grid)
    # 构建每个 k 的方向 'H'/'V'
    dirs: Dict[int, str] = {}
    for k in range(1, n):
        i, j = mp[k]
        ni, nj = mp[k + 1]
        if i == ni:
            dirs[k] = 'H'
        elif j == nj:
            dirs[k] = 'V'
        else:
            # 理论上不会发生（Numbrix 序列相邻应正交相邻），保底为 'H'
            dirs[k] = 'H'
    # 求同向的最大段
    runs: List[Tuple[int, int, str]] = []
    cur_start = 1
    cur_dir = dirs[1] if n > 1 else 'H'
    for k in range(2, n):
        if dirs[k] == cur_dir:
            continue
        else:
            runs.append((cur_start, k - 1, 'row' if cur_dir == 'H' else 'col'))
            cur_start = k
            cur_dir = dirs[k]
    runs.append((cur_start, n - 1, 'row' if cur_dir == 'H' else 'col'))
    # 按长度过滤并随机截取子段
    candidates: List[Tuple[int, int, str]] = []
    for (a, b, ori) in runs:
        length = b - a + 1
        if length >= min_len:
            Lmin, Lmax = min_len, min(max_len, length)
            if Lmax >= Lmin:
                L = random.randint(Lmin, Lmax)
                start = random.randint(a, b - L + 1)
                end = start + L - 1
                nval = size * size
                # 避开距离端点太近的区段，保证提示具有推理价值
                if start > 2 and end < nval - 2:
                    candidates.append((start, end, ori))
    random.shuffle(candidates)
    target = random.randint(min_seg, max_seg) if candidates else 0
    return candidates[:target]

def region_bounds_max(size: int) -> int:
    if size <= 5:
        return 2
    if size == 6:
        return 3
    return 3  # size == 7

def choose_region_sums(size: int,
                       ans_grid: List[List[int]],
                       max_regions: int) -> List[Tuple[int, int, int, int, int]]:
    """
    随机选取若干不重叠小矩形区域，返回 (i0, j0, h, w, sum) 列表：
    允许大小：2x2、2x3、3x2；不重叠
    """
    shapes = [(2, 2), (2, 3), (3, 2)]
    candidates: List[Tuple[int, int, int, int, int]] = []
    rects: List[Tuple[int, int, int, int]] = []
    for h, w in shapes:
        for i0 in range(0, size - h + 1):
            for j0 in range(0, size - w + 1):
                rects.append((i0, j0, h, w))
    random.shuffle(rects)
    used: List[Tuple[int, int, int, int]] = []
    for (i0, j0, h, w) in rects:
        overlap = False
        for (ii, jj, hh, ww) in used:
            if not (i0 + h <= ii or ii + hh <= i0 or j0 + w <= jj or jj + ww <= j0):
                overlap = True
                break
        if overlap:
            continue
        s = 0
        for di in range(h):
            for dj in range(w):
                s += ans_grid[i0 + di][j0 + dj]
        candidates.append((i0, j0, h, w, s))
        used.append((i0, j0, h, w))
        if len(candidates) >= max_regions:
            break
    return candidates

def turn_bounds_max(size: int) -> int:
    if size <= 5:
        return 2
    if size == 6:
        return 3
    return 3  # size == 7

def choose_turn_hints(size: int,
                      ans_grid: List[List[int]],
                      max_turns: int) -> List[int]:
    """
    选择若干“拐点”数值 v（1 < v < n），要求：
    (v-1 → v) 与 (v → v+1) 的相邻方向不同
    """
    n = size * size
    mp = _value_pos_map(ans_grid)
    dirs: Dict[int, str] = {}
    for k in range(1, n):
        i, j = mp[k]
        ni, nj = mp[k + 1]
        if i == ni:
            dirs[k] = 'H'
        elif j == nj:
            dirs[k] = 'V'
        else:
            dirs[k] = 'H'
    candidates: List[int] = []
    for v in range(2, n - 1):
        if dirs[v - 1] != dirs[v]:
            candidates.append(v)
    random.shuffle(candidates)
    return candidates[:max_turns]

# ----------------------
# 复杂约束构造器（供 YAML formula 直接调用）
# ----------------------

def build_core_adjacency(size: int,
                         n: int,
                         neighbors: Dict[Tuple[int, int], List[Tuple[int, int]]],
                         cells_s):
    """
    核心 Numbrix 约束：对每个格 (i,j)，若其值 c != n，则存在一个正交邻居值为 c+1。
    """
    exprs = []
    for i in range(size):
        for j in range(size):
            c = cells_s[(str(i), str(j))].get('value')
            neigh_vals = [cells_s[(str(ni), str(nj))].get('value') for (ni, nj) in neighbors[(i, j)]]
            cond = Or(*[nv == c + 1 for nv in neigh_vals]) if neigh_vals else BoolVal(False)
            exprs.append(Implies(c != n, cond))
    return And(exprs) if exprs else BoolVal(True)

def build_parity_core(size: int,
                      parity_on: bool,
                      anchor_triples: List[Tuple[int, int, int]],
                      cells_s):
    """
    奇偶核心约束（第一阶段）：若启用，则以锚点 1 的坐标 (i1,j1) 为起点双色标记：
    - 与 (i1+j1) 同奇偶的格填奇数
    - 与 (i1+j1) 异奇偶的格填偶数
    """
    if not parity_on:
        return BoolVal(True)
    i1, j1, _ = anchor_triples[0]
    start_parity = (i1 + j1) % 2
    exprs = []
    for i in range(size):
        for j in range(size):
            c = cells_s[(str(i), str(j))].get('value')
            if ((i + j) % 2) == start_parity:
                exprs.append(c % 2 == 1)
            else:
                exprs.append(c % 2 == 0)
    return And(exprs) if exprs else BoolVal(True)

def build_parity_lock(size: int,
                      start_parity: int,
                      cells_s):
    """
    奇偶最终锁定（第二阶段）：固定起点色后施加与之匹配的奇偶约束。
    """
    exprs = []
    for i in range(size):
        for j in range(size):
            c = cells_s[(str(i), str(j))].get('value')
            if ((i + j) % 2) == start_parity:
                exprs.append(c % 2 == 1)
            else:
                exprs.append(c % 2 == 0)
    return And(exprs) if exprs else BoolVal(True)

def build_dir_constraints(size: int,
                          dir_vecs: List[Tuple[int, int, int]],
                          cells_s):
    """
    方向线索：(v, di, dj)，表示 v+1 在 (di, dj) 方向上。
    对所有格子 (i, j)：
    - 若邻居存在：Implies(cell==v, neighbor==v+1)
    - 若邻居不存在：禁止 cell==v
    """
    exprs = []
    for (v, di, dj) in dir_vecs:
        for i in range(size):
            for j in range(size):
                ni = i + di
                nj = j + dj
                c = cells_s[(str(i), str(j))].get('value')
                if 0 <= ni < size and 0 <= nj < size:
                    nbr = cells_s[(str(ni), str(nj))].get('value')
                    exprs.append(Implies(c == v, nbr == v + 1))
                else:
                    exprs.append(c != v)
    return And(exprs) if exprs else BoolVal(True)

def build_row_sum_constraints(size: int,
                              row_hints: List[Tuple[int, int]],
                              cells_s):
    """
    行和提示：(row, sum)。
    """
    exprs = []
    for (r, s) in row_hints:
        row_cells = [cells_s[(str(r), str(j))].get('value') for j in range(size)]
        exprs.append(Sum(row_cells) == s)
    return And(exprs) if exprs else BoolVal(True)

def build_monotone_constraints(size: int,
                               mono_hints: List[Tuple[str, int, str]],
                               cells_s):
    """
    单调提示：('row'/'col', idx, 'inc'/'dec')
    inc: 严格递增（相邻格逐一比较 a<b）
    dec: 严格递减（相邻格逐一比较 a>b）
    """
    exprs = []
    for (kind, idx, direction) in mono_hints:
        if kind == 'row':
            pairs = [(cells_s[(str(idx), str(j))].get('value'),
                      cells_s[(str(idx), str(j + 1))].get('value')) for j in range(size - 1)]
        else:
            pairs = [(cells_s[(str(i), str(idx))].get('value'),
                      cells_s[(str(i + 1), str(idx))].get('value')) for i in range(size - 1)]
        if direction == 'inc':
            exprs.extend([a < b for (a, b) in pairs])
        else:
            exprs.extend([a > b for (a, b) in pairs])
    return And(exprs) if exprs else BoolVal(True)

def build_segment_constraints_row(size: int,
                                  seg_hints: List[Tuple[int, int, str]],
                                  cells_s):
    """
    段方向提示（水平）：(start, end, 'row')，表示区间 [start..end] 内每一步相邻均为水平。
    对每个 k∈[start..end]、每个格 (i,j)：
    Implies(cell==k, Or(left/right==k+1) ∧ up!=k+1 ∧ down!=k+1)
    """
    exprs = []
    for (a, b, ori) in seg_hints:
        if ori != 'row':
            continue
        for k in range(a, b + 1):
            for i in range(size):
                for j in range(size):
                    c = cells_s[(str(i), str(j))].get('value')
                    # 水平可选邻居
                    horiz_checks = []
                    if j - 1 >= 0:
                        horiz_checks.append(cells_s[(str(i), str(j - 1))].get('value') == k + 1)
                    if j + 1 < size:
                        horiz_checks.append(cells_s[(str(i), str(j + 1))].get('value') == k + 1)
                    # 竖直不允许
                    up_not = cells_s[(str(i - 1), str(j))].get('value') != k + 1 if i - 1 >= 0 else BoolVal(True)
                    down_not = cells_s[(str(i + 1), str(j))].get('value') != k + 1 if i + 1 < size else BoolVal(True)
                    cond = And(Or(*horiz_checks) if horiz_checks else BoolVal(False),
                               And(up_not, down_not))
                    exprs.append(Implies(c == k, cond))
    return And(exprs) if exprs else BoolVal(True)

def build_segment_constraints_col(size: int,
                                  seg_hints: List[Tuple[int, int, str]],
                                  cells_s):
    """
    段方向提示（竖直）：(start, end, 'col')，表示区间 [start..end] 内每一步相邻均为竖直。
    对每个 k∈[start..end]、每个格 (i,j)：
    Implies(cell==k, Or(up/down==k+1) ∧ left!=k+1 ∧ right!=k+1)
    """
    exprs = []
    for (a, b, ori) in seg_hints:
        if ori != 'col':
            continue
        for k in range(a, b + 1):
            for i in range(size):
                for j in range(size):
                    c = cells_s[(str(i), str(j))].get('value')
                    # 竖直可选邻居
                    vert_checks = []
                    if i - 1 >= 0:
                        vert_checks.append(cells_s[(str(i - 1), str(j))].get('value') == k + 1)
                    if i + 1 < size:
                        vert_checks.append(cells_s[(str(i + 1), str(j))].get('value') == k + 1)
                    # 水平不允许
                    left_not = cells_s[(str(i), str(j - 1))].get('value') != k + 1 if j - 1 >= 0 else BoolVal(True)
                    right_not = cells_s[(str(i), str(j + 1))].get('value') != k + 1 if j + 1 < size else BoolVal(True)
                    cond = And(Or(*vert_checks) if vert_checks else BoolVal(False),
                               And(left_not, right_not))
                    exprs.append(Implies(c == k, cond))
    return And(exprs) if exprs else BoolVal(True)

def build_region_sum_constraints(region_hints: List[Tuple[int, int, int, int, int]],
                                 cells_s):
    """
    小矩形区域和提示：(i0, j0, h, w, s)。
    """
    exprs = []
    for (i0, j0, h, w, s) in region_hints:
        cells = []
        for di in range(h):
            for dj in range(w):
                cells.append(cells_s[(str(i0 + di), str(j0 + dj))].get('value'))
        exprs.append(Sum(cells) == s)
    return And(exprs) if exprs else BoolVal(True)

def build_turn_constraints(size: int,
                           turn_hints: List[int],
                           cells_s):
    """
    拐点提示：v 的位置需同时存在一个水平邻居在 {v-1,v+1}，且一个竖直邻居在 {v-1,v+1}。
    """
    exprs = []
    for v in turn_hints:
        for i in range(size):
            for j in range(size):
                c = cells_s[(str(i), str(j))].get('value')
                # 竖直方向命中 v±1
                vert = []
                if i - 1 >= 0:
                    vert.append(cells_s[(str(i - 1), str(j))].get('value') == v - 1)
                    vert.append(cells_s[(str(i - 1), str(j))].get('value') == v + 1)
                if i + 1 < size:
                    vert.append(cells_s[(str(i + 1), str(j))].get('value') == v - 1)
                    vert.append(cells_s[(str(i + 1), str(j))].get('value') == v + 1)
                # 水平方向命中 v±1
                horiz = []
                if j - 1 >= 0:
                    horiz.append(cells_s[(str(i), str(j - 1))].get('value') == v - 1)
                    horiz.append(cells_s[(str(i), str(j - 1))].get('value') == v + 1)
                if j + 1 < size:
                    horiz.append(cells_s[(str(i), str(j + 1))].get('value') == v - 1)
                    horiz.append(cells_s[(str(i), str(j + 1))].get('value') == v + 1)
                cond = And(Or(*vert) if vert else BoolVal(False),
                           Or(*horiz) if horiz else BoolVal(False))
                exprs.append(Implies(c == v, cond))
    return And(exprs) if exprs else BoolVal(True)