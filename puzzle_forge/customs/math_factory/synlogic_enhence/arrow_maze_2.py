# arrow_maze_0.py
# -*- coding: utf-8 -*-
from typing import List, Tuple, Dict, Any
import json
import random
import time

# ----------------------------
# 基础方向与工具
# ----------------------------

DIRS4 = ['↑', '↓', '←', '→']
DIRS8 = ['↑', '↓', '←', '→', '↖', '↗', '↘', '↙']

AXIS = set(['↑', '↓', '←', '→'])
DIAG = set(['↖', '↗', '↘', '↙'])

VEC = {
    '↑': (-1, 0),
    '↓': (1, 0),
    '←': (0, -1),
    '→': (0, 1),
    '↖': (-1, -1),
    '↗': (-1, 1),
    '↘': (1, 1),
    '↙': (1, -1),
}

def in_bounds(n: int, r: int, c: int) -> bool:
    return 0 <= r < n and 0 <= c < n

def format_grid(grid: List[List[str]]) -> str:
    """
    将二维网格用 JSON 字符串格式化输出（确保中文及箭头字符不转义）。
    可用于调试，不在 YAML 中作为最终答案输出。
    """
    return json.dumps(grid, ensure_ascii=False)

def format_grid_sq(grid: List[List[str]]) -> str:
    """
    以单引号的 Python 风格列表字符串输出二维网格，适用于题面与答案（禁止双引号）。
    """
    rows = []
    for row in grid:
        cells = []
        for cell in row:
            if isinstance(cell, str):
                cells.append("'" + cell.replace("'", "\\'") + "'")
            else:
                cells.append(str(cell))
        rows.append('[' + ','.join(cells) + ']')
    return '[' + ','.join(rows) + ']'

def format_list_sq(lst: List[Any]) -> str:
    """
    单引号列表字符串输出（不含双引号）。
    """
    items = []
    for x in lst:
        if isinstance(x, str):
            items.append("'" + x.replace("'", "\\'") + "'")
        else:
            items.append(str(x))
    return '[' + ','.join(items) + ']'

def format_cells_sq(cells: List[Tuple[int, int]]) -> str:
    """
    输出坐标列表的单引号安全字符串：例如 [[0,1],[2,3]]
    """
    return '[' + ','.join('[' + str(r) + ',' + str(c) + ']' for (r, c) in cells) + ']'

def format_regions_sq(regions: List[Dict[str, int]]) -> str:
    """
    输出矩形区域列表的单引号安全字符串：例如 [[r0,c0,r1,c1], ...]
    """
    return '[' + ','.join('[' + str(reg['r0']) + ',' + str(reg['c0']) + ',' + str(reg['r1']) + ',' + str(reg['c1']) + ']' for reg in regions) + ']'

def example_answer_format() -> str:
    """
    在题面中展示的固定示例答案格式（单引号，二维数组）。
    始终使用轴向箭头+X+数字字符串，避免与方向集合产生误解。
    """
    ex = [['→', 'X'], ['1', '↓']]
    return format_grid_sq(ex)

# ----------------------------
# 几何与统计辅助
# ----------------------------

def compute_max_segments(n: int,
                         clue_pos: List[Tuple[int, int]],
                         directions: List[str]) -> Dict[Tuple[int, int], Dict[str, List[Tuple[int, int]]]]:
    """
    对每个数字格，按允许方向，计算从其相邻格出发的最大直线段（直到边界或遇到数字格前一格为止）。
    - 段不包含数字格本身
    - 段长度可能为0（若紧邻就是边界或数字），此类方向不作为候选
    """
    clue_set = set(clue_pos)
    segs: Dict[Tuple[int, int], Dict[str, List[Tuple[int, int]]]] = {}
    for (r, c) in clue_pos:
        dmap: Dict[str, List[Tuple[int, int]]] = {}
        for d in directions:
            dr, dc = VEC[d]
            rr, cc = r + dr, c + dc
            path: List[Tuple[int, int]] = []
            while in_bounds(n, rr, cc):
                if (rr, cc) in clue_set:
                    break  # 在遇到下一个数字格之前停止（不包含数字格）
                path.append((rr, cc))
                rr += dr
                cc += dc
            if len(path) > 0:
                dmap[d] = path
        if dmap:
            segs[(r, c)] = dmap
    return segs

def make_regions(n: int) -> List[Dict[str, int]]:
    """
    生成覆盖整个棋盘的矩形区域划分。
    策略：随机选择横向或纵向条带，或 2x2 分割。
    所有区域不重叠且覆盖全部格子。
    """
    typ = random.choice(['vertical', 'horizontal', 'grid2'])
    regions: List[Dict[str, int]] = []
    if typ == 'vertical':
        k = random.choice([2, 3])
        cuts = sorted(random.sample(list(range(1, n)), k - 1))
        prev = 0
        for cut in cuts + [n]:
            regions.append({'r0': 0, 'c0': prev, 'r1': n - 1, 'c1': cut - 1})
            prev = cut
    elif typ == 'horizontal':
        k = random.choice([2, 3])
        cuts = sorted(random.sample(list(range(1, n)), k - 1))
        prev = 0
        for cut in cuts + [n]:
            regions.append({'r0': prev, 'c0': 0, 'r1': cut - 1, 'c1': n - 1})
            prev = cut
    else:
        mid_r = n // 2
        mid_c = n // 2
        if mid_r == 0 or mid_c == 0:
            return make_regions(n)
        regions.append({'r0': 0, 'c0': 0, 'r1': mid_r - 1, 'c1': mid_c - 1})
        regions.append({'r0': 0, 'c0': mid_c, 'r1': mid_r - 1, 'c1': n - 1})
        regions.append({'r0': mid_r, 'c0': 0, 'r1': n - 1, 'c1': mid_c - 1})
        regions.append({'r0': mid_r, 'c0': mid_c, 'r1': n - 1, 'c1': n - 1})
    return regions

def region_index_of(regions: List[Dict[str, int]], r: int, c: int) -> int:
    for i, reg in enumerate(regions):
        if reg['r0'] <= r <= reg['r1'] and reg['c0'] <= c <= reg['c1']:
            return i
    return -1

def _compute_row_col_counts(grid: List[List[str]]) -> Tuple[List[int], List[int]]:
    n = len(grid)
    row_counts = [0] * n
    col_counts = [0] * n
    for r in range(n):
        for c in range(n):
            if grid[r][c] in DIRS8:
                row_counts[r] += 1
                col_counts[c] += 1
    return row_counts, col_counts

def _compute_dir_quota(grid: List[List[str]]) -> Tuple[int, int]:
    """
    返回 (轴向箭头总数, 斜向箭头总数)
    """
    axis = 0
    diag = 0
    n = len(grid)
    for r in range(n):
        for c in range(n):
            v = grid[r][c]
            if v in AXIS:
                axis += 1
            elif v in DIAG:
                diag += 1
    return axis, diag

def _compute_region_axis_diag(regions: List[Dict[str, int]], grid: List[List[str]]) -> Tuple[List[int], List[int]]:
    """
    每区域分别统计轴向与斜向箭头数量
    """
    n = len(grid)
    axis_counts = [0] * len(regions)
    diag_counts = [0] * len(regions)
    for r in range(n):
        for c in range(n):
            v = grid[r][c]
            if v in DIRS8:
                idx = region_index_of(regions, r, c)
                if idx >= 0:
                    if v in AXIS:
                        axis_counts[idx] += 1
                    elif v in DIAG:
                        diag_counts[idx] += 1
    return axis_counts, diag_counts

def _compute_perimeter_count(grid: List[List[str]]) -> int:
    """
    统计外边界（四条边）上的箭头格总数
    """
    n = len(grid)
    cnt = 0
    for r in range(n):
        for c in range(n):
            if r == 0 or c == 0 or r == n - 1 or c == n - 1:
                if grid[r][c] in DIRS8:
                    cnt += 1
    return cnt

def _compute_chess_parity_counts(grid: List[List[str]]) -> Tuple[int, int]:
    """
    黑白格（按 (r+c)%2==0 为黑格）上的箭头数
    """
    n = len(grid)
    black = 0
    white = 0
    for r in range(n):
        for c in range(n):
            v = grid[r][c]
            if v in DIRS8:
                if (r + c) % 2 == 0:
                    black += 1
                else:
                    white += 1
    return black, white

# ----------------------------
# 生成完整解（逆向构造）
# ----------------------------

def _choose_unique_assignment(segs: Dict[Tuple[int, int], Dict[str, List[Tuple[int, int]]]],
                              n: int) -> Dict[Tuple[int, int], List[str]]:
    """
    为每个数字格选择一个非空方向子集，使所有路径段互不重叠，返回方向集合。
    简单贪心+回溯，若失败返回空字典。
    """
    clues_sorted = sorted(segs.keys(), key=lambda pos: len(segs[pos]))
    used = set()
    assignment: Dict[Tuple[int, int], List[str]] = {}

    def dfs(idx: int) -> bool:
        if idx == len(clues_sorted):
            return True
        pos = clues_sorted[idx]
        dmap = segs[pos]
        dirs = list(dmap.keys())
        all_subsets: List[List[str]] = []
        for mask in range(1, 1 << len(dirs)):
            subset = [dirs[i] for i in range(len(dirs)) if (mask >> i) & 1]
            all_subsets.append(subset)
        random.shuffle(all_subsets)
        for subset in all_subsets:
            cells = []
            conflict = False
            for d in subset:
                for cell in dmap[d]:
                    if cell in used:
                        conflict = True
                        break
                    cells.append(cell)
                if conflict:
                    break
            if conflict:
                continue
            for cell in cells:
                used.add(cell)
            assignment[pos] = subset
            if dfs(idx + 1):
                return True
            for cell in cells:
                used.remove(cell)
            assignment.pop(pos, None)
        return False

    ok = dfs(0)
    return assignment if ok else {}

def _build_solution_grid(n: int,
                         clue_map: Dict[Tuple[int, int], int],
                         segs: Dict[Tuple[int, int], Dict[str, List[Tuple[int, int]]]],
                         assignment: Dict[Tuple[int, int], List[str]],
                         blocked: List[Tuple[int, int]]) -> List[List[str]]:
    """
    根据方向选择构造终盘箭头网格（数字格为数字字符串，其余为箭头字符或 X 或 '#'(阻挡格)）。
    """
    grid = [['X' for _ in range(n)] for _ in range(n)]
    for (r, c), num in clue_map.items():
        grid[r][c] = str(num)
    for pos, dirs in assignment.items():
        for d in dirs:
            for (rr, cc) in segs[pos][d]:
                grid[rr][cc] = d
    for (r, c) in blocked:
        grid[r][c] = '#'
    return grid

# ----------------------------
# 候选生成（带方向明细）
# ----------------------------

def _candidate_subsets_for_clue(n: int,
                                clue: Dict[str, int],
                                directions: List[str],
                                clue_set: set,
                                blocked_set: set) -> List[Tuple[List[str], List[Tuple[int, int]], List[Tuple[int, int, str]]]]:
    """
    对一个数字格，枚举所有非空方向子集，使其最大段长度之和等于该数字值。
    过滤：段单元格不得包含阻挡格；同一数字的不同射线也不得共享箭头格。
    返回 [(方向列表, 段单元格列表, 段单元格方向明细)]。
    """
    r, c, num = clue['r'], clue['c'], clue['num']
    segs = compute_max_segments(n, [(r, c)] + list(clue_set - {(r, c)}), directions)
    dmap = segs.get((r, c), {})
    dirs = list(dmap.keys())
    cand = []
    for mask in range(1, 1 << len(dirs)):
        subset_dirs = [dirs[i] for i in range(len(dirs)) if (mask >> i) & 1]
        total_len = sum(len(dmap[d]) for d in subset_dirs)
        if total_len == num:
            cells = []
            cells_with_dir = []
            conflict = False
            seen = set()
            for d in subset_dirs:
                for (rr, cc) in dmap[d]:
                    if (rr, cc) in seen or (rr, cc) in blocked_set:
                        conflict = True
                        break
                    seen.add((rr, cc))
                    cells.append((rr, cc))
                    cells_with_dir.append((rr, cc, d))
                if conflict:
                    break
            if conflict:
                continue
            cand.append((subset_dirs, cells, cells_with_dir))
    return cand

# ----------------------------
# 回溯重解（唯一性验证与求解）
# ----------------------------

def _re_solve_count(instance: Dict[str, Any], time_limit_sec: int = 60) -> Tuple[int, List[List[str]]]:
    """
    对题面进行回溯重解，返回解的数量与（若唯一则）该解网格。
    启用的约束：行计数、列计数、区域计数、区域轴/斜配额、全局轴/斜配额、阻挡格、边界配额、黑白配额、锚点类型、邻接规则。
    """
    t0 = time.time()

    n = instance['grid_size']
    directions = instance['directions']
    clues = instance['clues']
    row_counts = instance['row_counts']
    col_counts = instance['col_counts']
    regions = instance['regions']
    region_counts = instance['region_counts']
    blocked = instance['blocked']
    use_row_counts = instance['use_row_counts']
    use_col_counts = instance['use_col_counts']
    use_region_counts = instance['use_region_counts']
    use_dir_quota = instance['use_dir_quota']
    axis_quota = instance['axis_quota']
    diag_quota = instance['diag_quota']
    use_region_axisdiag = instance.get('use_region_axisdiag', False)
    region_axis_counts = instance.get('region_axis_counts', [])
    region_diag_counts = instance.get('region_diag_counts', [])
    use_perimeter_quota = instance.get('use_perimeter_quota', False)
    perimeter_quota = instance.get('perimeter_quota', 0)
    use_parity_quota = instance.get('use_parity_quota', False)
    black_quota = instance.get('black_quota', 0)
    white_quota = instance.get('white_quota', 0)
    use_anchors = instance.get('use_anchors', False)
    anchor_axis_cells = set(instance.get('anchor_axis_cells', []))
    anchor_diag_cells = set(instance.get('anchor_diag_cells', []))
    use_adjacency_rule = instance.get('use_adjacency_rule', False)
    adj_rule_code = instance.get('adj_rule_code', '')

    clue_set = {(cl['r'], cl['c']) for cl in clues}
    blocked_set = set(blocked)

    # 为每个提示计算候选子集
    cand_per = []
    for cl in clues:
        cand = _candidate_subsets_for_clue(n, cl, directions, clue_set, blocked_set)
        if not cand:
            return 0, []
        cand_per.append((cl, cand))
    cand_per.sort(key=lambda x: len(x[1]))

    row_used = [0] * n
    col_used = [0] * n
    region_used = [0] * len(regions)
    region_axis_used = [0] * len(regions)
    region_diag_used = [0] * len(regions)
    axis_used = 0
    diag_used = 0
    perimeter_used = 0
    black_used = 0
    white_used = 0
    used_cells = set()
    cell_dir: Dict[Tuple[int, int], str] = {}

    sol_count = 0

    def check_time():
        return (time.time() - t0) <= time_limit_sec

    def is_perimeter(r: int, c: int) -> bool:
        return r == 0 or c == 0 or r == n - 1 or c == n - 1

    def check_adjacency(rr: int, cc: int, d: str) -> bool:
        """
        返回 True 表示通过邻接规则（允许放置）
        """
        if not use_adjacency_rule:
            return True
        # 四邻域
        for (dr, dc) in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = rr + dr, cc + dc
            if not in_bounds(n, nr, nc):
                continue
            nd = cell_dir.get((nr, nc), None)
            if nd is None:
                continue
            if adj_rule_code == 'no_adjacent_same_dir':
                if nd == d:
                    return False
            elif adj_rule_code == 'no_adjacent_diagonals_touch':
                if (d in DIAG) and (nd in DIAG):
                    return False
        return True

    # 初始网格用于最终解（仅在唯一解时构建）
    sol_grid = [['X' for _ in range(n)] for _ in range(n)]
    for cl in clues:
        sol_grid[cl['r']][cl['c']] = str(cl['num'])
    for (r, c) in blocked:
        sol_grid[r][c] = '#'

    def dfs(idx: int):
        nonlocal sol_count, axis_used, diag_used, perimeter_used, black_used, white_used
        if not check_time():
            return
        if sol_count > 1:
            return
        if idx == len(cand_per):
            # 最终检查：各类配额与锚点全满足
            if use_row_counts and row_used != row_counts:
                return
            if use_col_counts and col_used != col_counts:
                return
            if use_region_counts and region_used != region_counts:
                return
            if use_dir_quota:
                if axis_used != axis_quota or diag_used != diag_quota:
                    return
            if use_region_axisdiag:
                if region_axis_used != region_axis_counts:
                    return
                if region_diag_used != region_diag_counts:
                    return
            if use_perimeter_quota and perimeter_used != perimeter_quota:
                return
            if use_parity_quota and (black_used != black_quota or white_used != white_quota):
                return
            if use_anchors:
                # 所有锚点必须被填充且类型匹配
                for cell in anchor_axis_cells:
                    if cell not in used_cells:
                        return
                    if cell_dir.get(cell, '') not in AXIS:
                        return
                for cell in anchor_diag_cells:
                    if cell not in used_cells:
                        return
                    if cell_dir.get(cell, '') not in DIAG:
                        return
            sol_count += 1
            return

        cl, cand = cand_per[idx]
        for subset_dirs, cells, cells_with_dir in cand:
            # 不重叠
            if any((cell in used_cells) for cell in cells):
                continue
            # 行列不超
            tmp_row_add = [0] * n
            tmp_col_add = [0] * n
            tmp_region_add = [0] * len(regions) if use_region_counts else None
            tmp_region_axis_add = [0] * len(regions) if use_region_axisdiag else None
            tmp_region_diag_add = [0] * len(regions) if use_region_axisdiag else None
            tmp_axis_add = 0
            tmp_diag_add = 0
            tmp_perimeter_add = 0 if use_perimeter_quota else None
            tmp_black_add = 0 if use_parity_quota else None
            tmp_white_add = 0 if use_parity_quota else None

            ok = True
            # 逐格检查邻接与锚点类型、并累加配额
            for (rr, cc, d) in cells_with_dir:
                # 邻接规则
                if not check_adjacency(rr, cc, d):
                    ok = False
                    break
                # 阻挡格不可放箭头
                if (rr, cc) in blocked_set:
                    ok = False
                    break
                # 锚点类型（若该格是锚点，立即匹配）
                if use_anchors:
                    if (rr, cc) in anchor_axis_cells and d not in AXIS:
                        ok = False
                        break
                    if (rr, cc) in anchor_diag_cells and d not in DIAG:
                        ok = False
                        break
                # 行列增量
                tmp_row_add[rr] += 1
                tmp_col_add[cc] += 1
                if use_row_counts and row_used[rr] + tmp_row_add[rr] > row_counts[rr]:
                    ok = False
                    break
                if use_col_counts and col_used[cc] + tmp_col_add[cc] > col_counts[cc]:
                    ok = False
                    break
                # 区域增量
                if use_region_counts or use_region_axisdiag:
                    idx_reg = region_index_of(regions, rr, cc)
                    if idx_reg >= 0:
                        if use_region_counts:
                            tmp_region_add[idx_reg] += 1
                            if region_used[idx_reg] + tmp_region_add[idx_reg] > region_counts[idx_reg]:
                                ok = False
                                break
                        if use_region_axisdiag:
                            if d in AXIS:
                                tmp_region_axis_add[idx_reg] += 1
                                if region_axis_used[idx_reg] + tmp_region_axis_add[idx_reg] > region_axis_counts[idx_reg]:
                                    ok = False
                                    break
                            elif d in DIAG:
                                tmp_region_diag_add[idx_reg] += 1
                                if region_diag_used[idx_reg] + tmp_region_diag_add[idx_reg] > region_diag_counts[idx_reg]:
                                    ok = False
                                    break
                # 全局方向配额
                if use_dir_quota:
                    if d in AXIS:
                        tmp_axis_add += 1
                        if axis_used + tmp_axis_add > axis_quota:
                            ok = False
                            break
                    elif d in DIAG:
                        tmp_diag_add += 1
                        if diag_used + tmp_diag_add > diag_quota:
                            ok = False
                            break
                # 边界配额
                if use_perimeter_quota is True:
                    if is_perimeter(rr, cc):
                        tmp_perimeter_add += 1
                        if perimeter_used + tmp_perimeter_add > perimeter_quota:
                            ok = False
                            break
                # 黑白配额
                if use_parity_quota is True:
                    if (rr + cc) % 2 == 0:
                        tmp_black_add += 1
                        if black_used + tmp_black_add > black_quota:
                            ok = False
                            break
                    else:
                        tmp_white_add += 1
                        if white_used + tmp_white_add > white_quota:
                            ok = False
                            break

            if not ok:
                continue

            # 应用选择
            for (rr, cc, d) in cells_with_dir:
                used_cells.add((rr, cc))
                cell_dir[(rr, cc)] = d
                row_used[rr] += 1
                col_used[cc] += 1
                if use_region_counts:
                    idx_reg = region_index_of(regions, rr, cc)
                    if idx_reg >= 0:
                        region_used[idx_reg] += 1
                if use_region_axisdiag:
                    idx_reg = region_index_of(regions, rr, cc)
                    if idx_reg >= 0:
                        if d in AXIS:
                            region_axis_used[idx_reg] += 1
                        elif d in DIAG:
                            region_diag_used[idx_reg] += 1
                if use_dir_quota:
                    if d in AXIS:
                        axis_used += 1
                    elif d in DIAG:
                        diag_used += 1
                if use_perimeter_quota:
                    if is_perimeter(rr, cc):
                        perimeter_used += 1
                if use_parity_quota:
                    if (rr + cc) % 2 == 0:
                        black_used += 1
                    else:
                        white_used += 1

            dfs(idx + 1)

            # 回溯
            for (rr, cc, d) in cells_with_dir:
                used_cells.remove((rr, cc))
                cell_dir.pop((rr, cc), None)
                row_used[rr] -= 1
                col_used[cc] -= 1
                if use_region_counts:
                    idx_reg = region_index_of(regions, rr, cc)
                    if idx_reg >= 0:
                        region_used[idx_reg] -= 1
                if use_region_axisdiag:
                    idx_reg = region_index_of(regions, rr, cc)
                    if idx_reg >= 0:
                        if d in AXIS:
                            region_axis_used[idx_reg] -= 1
                        elif d in DIAG:
                            region_diag_used[idx_reg] -= 1
                if use_dir_quota:
                    if d in AXIS:
                        axis_used -= 1
                    elif d in DIAG:
                        diag_used -= 1
                if use_perimeter_quota:
                    if is_perimeter(rr, cc):
                        perimeter_used -= 1
                if use_parity_quota:
                    if (rr + cc) % 2 == 0:
                        black_used -= 1
                    else:
                        white_used -= 1

    dfs(0)

    # 若唯一解，重建带方向的网格
    if sol_count == 1:
        final_grid = [['X' for _ in range(n)] for _ in range(n)]
        for cl in clues:
            final_grid[cl['r']][cl['c']] = str(cl['num'])
        for (r, c) in blocked:
            final_grid[r][c] = '#'

        used_cells.clear()
        cell_dir.clear()
        row_used = [0] * n
        col_used = [0] * n
        region_used = [0] * len(regions)
        region_axis_used = [0] * len(regions)
        region_diag_used = [0] * len(regions)
        axis_used = 0
        diag_used = 0
        perimeter_used = 0
        black_used = 0
        white_used = 0

        def dfs_build(idx: int) -> bool:
            nonlocal axis_used, diag_used, perimeter_used, black_used, white_used
            if not check_time():
                return False
            if idx == len(cand_per):
                return True
            cl, cand = cand_per[idx]
            for subset_dirs, cells, cells_with_dir in cand:
                if any((cell in used_cells) for cell in cells):
                    continue
                tmp_row_add = [0] * n
                tmp_col_add = [0] * n
                tmp_region_add = [0] * len(regions) if use_region_counts else None
                tmp_region_axis_add = [0] * len(regions) if use_region_axisdiag else None
                tmp_region_diag_add = [0] * len(regions) if use_region_axisdiag else None
                tmp_axis_add = 0
                tmp_diag_add = 0
                tmp_perimeter_add = 0 if use_perimeter_quota else None
                tmp_black_add = 0 if use_parity_quota else None
                tmp_white_add = 0 if use_parity_quota else None

                ok = True
                for (rr, cc, d) in cells_with_dir:
                    if not check_adjacency(rr, cc, d):
                        ok = False
                        break
                    if (rr, cc) in blocked_set:
                        ok = False
                        break
                    if use_anchors:
                        if (rr, cc) in anchor_axis_cells and d not in AXIS:
                            ok = False
                            break
                        if (rr, cc) in anchor_diag_cells and d not in DIAG:
                            ok = False
                            break
                    tmp_row_add[rr] += 1
                    tmp_col_add[cc] += 1
                    if use_row_counts and row_used[rr] + tmp_row_add[rr] > row_counts[rr]:
                        ok = False
                        break
                    if use_col_counts and col_used[cc] + tmp_col_add[cc] > col_counts[cc]:
                        ok = False
                        break
                    if use_region_counts or use_region_axisdiag:
                        idx_reg = region_index_of(regions, rr, cc)
                        if idx_reg >= 0:
                            if use_region_counts:
                                tmp_region_add[idx_reg] += 1
                                if region_used[idx_reg] + tmp_region_add[idx_reg] > region_counts[idx_reg]:
                                    ok = False
                                    break
                            if use_region_axisdiag:
                                if d in AXIS:
                                    tmp_region_axis_add[idx_reg] += 1
                                    if region_axis_used[idx_reg] + tmp_region_axis_add[idx_reg] > region_axis_counts[idx_reg]:
                                        ok = False
                                        break
                                elif d in DIAG:
                                    tmp_region_diag_add[idx_reg] += 1
                                    if region_diag_used[idx_reg] + tmp_region_diag_add[idx_reg] > region_diag_counts[idx_reg]:
                                        ok = False
                                        break
                    if use_dir_quota:
                        if d in AXIS:
                            tmp_axis_add += 1
                            if axis_used + tmp_axis_add > axis_quota:
                                ok = False
                                break
                        elif d in DIAG:
                            tmp_diag_add += 1
                            if diag_used + tmp_diag_add > diag_quota:
                                ok = False
                                break
                    if use_perimeter_quota:
                        if (rr == 0 or cc == 0 or rr == n - 1 or cc == n - 1):
                            tmp_perimeter_add += 1
                            if perimeter_used + tmp_perimeter_add > perimeter_quota:
                                ok = False
                                break
                    if use_parity_quota:
                        if (rr + cc) % 2 == 0:
                            tmp_black_add += 1
                            if black_used + tmp_black_add > black_quota:
                                ok = False
                                break
                        else:
                            tmp_white_add += 1
                            if white_used + tmp_white_add > white_quota:
                                ok = False
                                break
                if not ok:
                    continue

                for (rr, cc, d) in cells_with_dir:
                    used_cells.add((rr, cc))
                    cell_dir[(rr, cc)] = d
                    final_grid[rr][cc] = d
                    row_used[rr] += 1
                    col_used[cc] += 1
                    if use_region_counts:
                        idx_reg = region_index_of(regions, rr, cc)
                        if idx_reg >= 0:
                            region_used[idx_reg] += 1
                    if use_region_axisdiag:
                        idx_reg = region_index_of(regions, rr, cc)
                        if idx_reg >= 0:
                            if d in AXIS:
                                region_axis_used[idx_reg] += 1
                            elif d in DIAG:
                                region_diag_used[idx_reg] += 1
                    if use_dir_quota:
                        if d in AXIS:
                            axis_used += 1
                        elif d in DIAG:
                            diag_used += 1
                    if use_perimeter_quota:
                        if rr == 0 or cc == 0 or rr == n - 1 or cc == n - 1:
                            perimeter_used += 1
                    if use_parity_quota:
                        if (rr + cc) % 2 == 0:
                            black_used += 1
                        else:
                            white_used += 1

                if dfs_build(idx + 1):
                    return True

                for (rr, cc, d) in cells_with_dir:
                    used_cells.remove((rr, cc))
                    cell_dir.pop((rr, cc), None)
                    final_grid[rr][cc] = 'X'
                    row_used[rr] -= 1
                    col_used[cc] -= 1
                    if use_region_counts:
                        idx_reg = region_index_of(regions, rr, cc)
                        if idx_reg >= 0:
                            region_used[idx_reg] -= 1
                    if use_region_axisdiag:
                        idx_reg = region_index_of(regions, rr, cc)
                        if idx_reg >= 0:
                            if d in AXIS:
                                region_axis_used[idx_reg] -= 1
                            elif d in DIAG:
                                region_diag_used[idx_reg] -= 1
                    if use_dir_quota:
                        if d in AXIS:
                            axis_used -= 1
                        elif d in DIAG:
                            diag_used -= 1
                    if use_perimeter_quota:
                        if rr == 0 or cc == 0 or rr == n - 1 or cc == n - 1:
                            perimeter_used -= 1
                    if use_parity_quota:
                        if (rr + cc) % 2 == 0:
                            black_used -= 1
                        else:
                            white_used -= 1
            return False

        dfs_build(0)
        return 1, final_grid

    return sol_count, []

def solve_arrow_maze(instance: Dict[str, Any]) -> List[List[str]]:
    """
    对给定题面进行重解，返回唯一解的完整网格二维数组。
    若不唯一或无解，将抛出异常（生成器应确保唯一）。
    """
    sol_cnt, grid = _re_solve_count(instance, time_limit_sec=120)
    if sol_cnt != 1:
        raise ValueError('Puzzle is not uniquely solvable: solutions=' + str(sol_cnt))
    return grid

# ----------------------------
# 规则文本构造（题面展示）
# ----------------------------

def build_rule_text(instance: Dict[str, Any]) -> str:
    """
    根据启用的约束与参数，生成单行规则说明文本片段（不含双引号；必要换行用 \\n）。
    补充了计数数组的顺序约定说明，避免歧义。
    """
    n = instance['grid_size']
    directions = instance['directions']
    directions_text = format_list_sq(directions)
    base = (
        '可用箭头方向集合为 ' + directions_text +
        '；箭头只能放在非数字、非阻挡的格子；从每个数字格的相邻格出发，沿箭头所指方向形成若干条不拐弯的直线射线，'
        '同一数字的不同射线不得共享箭头格，不同数字的射线之间也不得共享任何箭头格，且射线不会穿越其他数字格；'
        '每个数字等于从该数字出发的所有射线长度之和。'
        '每条射线从与箭头方向一致的紧邻起始格开始，连续由同方向箭头格组成，直到越界或在到达另一数字格前的最后一个格停止；'
        '射线不包含数字格本身，长度按箭头格数量计数；射线不得包含阻挡格。'
        '所有箭头必须属于某个数字的射线；未放置箭头的空格请以字符 X 保持为空；答案中的数字与 # 必须原样保留，数字以字符串形式出现。'
        '若本题方向集合不含斜向箭头，则涉及斜向的条款不适用。'
    )
    parts = []
    # 基础计数
    if instance.get('use_row_counts', False):
        parts.append('每一行的箭头格数量分别为 ' + format_list_sq(instance['row_counts']) + '（按行索引从上到下：0..' + str(n - 1) + '）')
    if instance.get('use_col_counts', False):
        parts.append('每一列的箭头格数量分别为 ' + format_list_sq(instance['col_counts']) + '（按列索引从左到右：0..' + str(n - 1) + '）')
    # 区域计数
    if instance.get('use_region_counts', False):
        parts.append('将棋盘划分为若干矩形区域 ' + format_regions_sq(instance['regions']) + '（坐标与索引均从 0 开始；格式为 [r0,c0,r1,c1]，含边界；区域列表的顺序即区域编号顺序 0..' + str(len(instance['regions']) - 1) + '），各区域的箭头格数量分别为 ' + format_list_sq(instance['region_counts']))
    # 轴向/斜向字样
    if any(d in DIAG for d in directions):
        axis_diag_desc = '其中，轴向箭头为 [\'↑\',\'↓\',\'←\',\'→\']，斜向箭头为 [\'↖\',\'↗\',\'↘\',\'↙\']。'
    else:
        axis_diag_desc = '本题不含斜向箭头，轴向箭头为 [\'↑\',\'↓\',\'←\',\'→\']。'
    parts.append(axis_diag_desc)
    # 全局配额
    if instance.get('use_dir_quota', False):
        parts.append('总箭头配额：轴向箭头数量为 ' + str(instance['axis_quota']) + '，斜向箭头数量为 ' + str(instance['diag_quota']))
    # 区域轴/斜配额
    if instance.get('use_region_axisdiag', False):
        parts.append('各区域的轴向箭头数量分别为 ' + format_list_sq(instance.get('region_axis_counts', [])) + '；斜向箭头数量分别为 ' + format_list_sq(instance.get('region_diag_counts', [])))
    # 邻接规则（与方向集合一致）
    if instance.get('use_adjacency_rule', False):
        code = instance.get('adj_rule_code', '')
        if code == 'no_adjacent_same_dir':
            parts.append('邻接规则：任意两个上下左右相邻的格子若都放置箭头，则两者箭头方向不得相同')
        elif code == 'no_adjacent_diagonals_touch':
            parts.append('邻接规则：任意两个上下左右相邻的格子不得同时放置斜向箭头')
    # 锚点类型
    if instance.get('use_anchors', False):
        if len(instance.get('anchor_axis_cells', [])) > 0:
            parts.append('以下格必须放置轴向箭头（坐标从 0 开始）：' + format_cells_sq(instance.get('anchor_axis_cells', [])))
        if len(instance.get('anchor_diag_cells', [])) > 0:
            parts.append('以下格必须放置斜向箭头（坐标从 0 开始）：' + format_cells_sq(instance.get('anchor_diag_cells', [])))
    # 阻挡格
    if len(instance.get('blocked', [])) > 0:
        parts.append('以下格为不可放箭头的阻挡格（始终用符号 # 表示；坐标从 0 开始）：' + format_cells_sq(instance['blocked']))
    # 边界配额
    if instance.get('use_perimeter_quota', False):
        parts.append('外边界箭头格总数为 ' + str(instance.get('perimeter_quota', 0)) + '（外边界指四条边上的格子；计数不去重）')
    # 黑白配额
    if instance.get('use_parity_quota', False):
        parts.append('棋盘黑白格配额：以 (r+c)%2==0 判定为黑格，其余为白格；黑格箭头数为 ' + str(instance.get('black_quota', 0)) + '，白格箭头数为 ' + str(instance.get('white_quota', 0)))

    extra = ('；'.join(parts)) if parts else ''
    if extra:
        return base + ' ' + extra
    return base

# ----------------------------
# 实例生成（逆向构造 + 唯一性重解验证）
# ----------------------------

def gen_arrow_maze_instance() -> Dict[str, Any]:
    """
    随机生成一个唯一解的箭头迷宫实例（带随机规则模板）：
    - 随机网格大小（5~7）、方向集合（4或8方向）
    - 随机数字位置与方向选择（逆向），保证段互斥
    - 随机阻挡格（从非数字且非箭头格中抽取少量）
    - 规则模板组合：行计数/列计数/区域计数/方向配额/区域轴斜配额/边界配额/黑白配额/邻接规则/锚点类型 中随机启用至少四项（其中主约束至少两项）
    - 回溯重解校验唯一性；不唯一则重试
    返回实例字典，包含题面所需全部参数
    """
    for _ in range(800):
        n = random.randint(5, 7)
        use_diag = random.choice([True, False])
        directions = DIRS8[:] if use_diag else DIRS4[:]

        # 随机放置数字位置
        clue_num = random.randint(max(3, n // 2 + 1), n + 2)
        all_cells = [(r, c) for r in range(n) for c in range(n)]
        random.shuffle(all_cells)
        clue_pos = []
        for (r, c) in all_cells:
            clue_pos.append((r, c))
            if len(clue_pos) == clue_num:
                break

        # 计算最大段并过滤无候选数字
        segs = compute_max_segments(n, clue_pos, directions)
        clue_pos = [pos for pos in clue_pos if pos in segs]
        if len(clue_pos) < max(3, n // 2 + 1):
            continue

        # 选择互斥方向子集（构造唯一解候选）
        assignment = _choose_unique_assignment(segs, n)
        if not assignment or len(assignment) != len(clue_pos):
            continue

        # 由选择的方向子集，计算每个数字的值（长度之和）
        clue_map: Dict[Tuple[int, int], int] = {}
        for pos, dirs in assignment.items():
            total_len = sum(len(segs[pos][d]) for d in dirs)
            clue_map[pos] = total_len

        # 初步构造解网格并统计行列计数
        sol_grid = _build_solution_grid(n, clue_map, segs, assignment, blocked=[])
        row_counts, col_counts = _compute_row_col_counts(sol_grid)

        # 生成区域划分与区域计数
        regions = make_regions(n)
        region_counts = [0] * len(regions)
        for r in range(n):
            for c in range(n):
                if sol_grid[r][c] in DIRS8:
                    idx = region_index_of(regions, r, c)
                    if idx >= 0:
                        region_counts[idx] += 1

        # 区域轴斜配额（在含斜向时开启概率更高）
        region_axis_counts, region_diag_counts = _compute_region_axis_diag(regions, sol_grid)
        use_region_axisdiag = use_diag and random.choice([True, False])

        # 全局方向配额（仅在8方向时有斜向配额；4方向时斜向配额为0）
        axis_quota, diag_quota = _compute_dir_quota(sol_grid)
        use_dir_quota = random.choice([True, False]) if use_diag else False

        # 阻挡格：从非数字且非箭头的格中抽取少量（0~min(3,n-2)）
        empties = [(r, c) for r in range(n) for c in range(n) if sol_grid[r][c] == 'X']
        random.shuffle(empties)
        block_cnt = random.randint(0, min(3, max(0, len(empties) // 4)))
        blocked = empties[:block_cnt]
        sol_grid_with_block = _build_solution_grid(n, clue_map, segs, assignment, blocked=blocked)

        # 边界配额与黑白配额
        perimeter_quota = _compute_perimeter_count(sol_grid_with_block)
        use_perimeter_quota = random.choice([True, False])
        black_quota, white_quota = _compute_chess_parity_counts(sol_grid_with_block)
        use_parity_quota = random.choice([True, False])

        # 邻接规则（与方向集合一致）
        use_adjacency_rule = random.choice([True, False])
        if use_adjacency_rule:
            if use_diag:
                adj_rule_code = random.choice(['no_adjacent_same_dir', 'no_adjacent_diagonals_touch'])
            else:
                adj_rule_code = 'no_adjacent_same_dir'
        else:
            adj_rule_code = ''

        # 锚点类型（抽少量箭头格为轴/斜锚点）
        arrow_cells = [(r, c) for r in range(n) for c in range(n) if sol_grid_with_block[r][c] in DIRS8]
        random.shuffle(arrow_cells)
        anchor_axis_cells: List[Tuple[int, int]] = []
        anchor_diag_cells: List[Tuple[int, int]] = []
        use_anchors = random.choice([True, False]) and len(arrow_cells) > 0
        if use_anchors:
            k = random.randint(1, min(5, max(1, len(arrow_cells) // 5)))
            for i in range(k):
                rr, cc = arrow_cells[i]
                d = sol_grid_with_block[rr][cc]
                if d in AXIS:
                    anchor_axis_cells.append((rr, cc))
                elif d in DIAG:
                    anchor_diag_cells.append((rr, cc))

        # 行列与区域计数至少启用两项（行计数优先启用）
        use_row_counts = True
        use_col_counts = random.choice([True, False])
        use_region_counts = random.choice([True, False])
        enabled_primary = [use_row_counts, use_col_counts, use_region_counts]
        if sum(1 for x in enabled_primary if x) < 2:
            use_col_counts = True  # 保证至少两项

        # 至少启用四类约束（含主约束≥2），优先补齐一种“形态类”约束（邻接或锚点），再补其余
        categories = [
            use_row_counts, use_col_counts, use_region_counts,
            use_dir_quota, use_region_axisdiag, use_perimeter_quota,
            use_parity_quota, use_adjacency_rule, use_anchors
        ]

        def count_enabled(lst: List[bool]) -> int:
            return sum(1 for x in lst if x)

        # 若未包含形态类约束，优先添加一个（邻接 或 锚点），以增强推理深度
        if not use_adjacency_rule and not use_anchors:
            if len(arrow_cells) > 0 and random.choice([True, False]):
                use_anchors = True
                if not anchor_axis_cells and not anchor_diag_cells:
                    k = random.randint(1, min(5, max(1, len(arrow_cells) // 5)))
                    for i in range(k):
                        rr, cc = arrow_cells[i]
                        d = sol_grid_with_block[rr][cc]
                        if d in AXIS:
                            anchor_axis_cells.append((rr, cc))
                        elif d in DIAG:
                            anchor_diag_cells.append((rr, cc))
            else:
                use_adjacency_rule = True
                if adj_rule_code == '':
                    adj_rule_code = random.choice(['no_adjacent_same_dir', 'no_adjacent_diagonals_touch']) if use_diag else 'no_adjacent_same_dir'

        categories = [
            use_row_counts, use_col_counts, use_region_counts,
            use_dir_quota, use_region_axisdiag, use_perimeter_quota,
            use_parity_quota, use_adjacency_rule, use_anchors
        ]

        if count_enabled(categories) < 4:
            # 构造可补充的约束池（尽量选择有效的）
            candidates = []
            if not use_dir_quota and use_diag:
                candidates.append('dir_quota')
            if not use_region_axisdiag and use_diag:
                candidates.append('region_axisdiag')
            if not use_perimeter_quota:
                candidates.append('perimeter')
            if not use_parity_quota:
                candidates.append('parity')
            # 邻接/锚点如未开启也加入候选（若上一步未开启）
            if not use_adjacency_rule:
                candidates.append('adjacency')
            if not use_anchors and len(arrow_cells) > 0:
                candidates.append('anchors')
            random.shuffle(candidates)
            for name in candidates:
                if count_enabled(categories) >= 4:
                    break
                if name == 'dir_quota':
                    use_dir_quota = True
                elif name == 'region_axisdiag':
                    use_region_axisdiag = True
                elif name == 'perimeter':
                    use_perimeter_quota = True
                elif name == 'parity':
                    use_parity_quota = True
                elif name == 'adjacency':
                    use_adjacency_rule = True
                    if adj_rule_code == '':
                        adj_rule_code = random.choice(['no_adjacent_same_dir', 'no_adjacent_diagonals_touch']) if use_diag else 'no_adjacent_same_dir'
                elif name == 'anchors':
                    use_anchors = True
                    if not anchor_axis_cells and not anchor_diag_cells and len(arrow_cells) > 0:
                        k = random.randint(1, min(5, max(1, len(arrow_cells) // 5)))
                        for i in range(k):
                            rr, cc = arrow_cells[i]
                            d = sol_grid_with_block[rr][cc]
                            if d in AXIS:
                                anchor_axis_cells.append((rr, cc))
                            elif d in DIAG:
                                anchor_diag_cells.append((rr, cc))
                categories = [
                    use_row_counts, use_col_counts, use_region_counts,
                    use_dir_quota, use_region_axisdiag, use_perimeter_quota,
                    use_parity_quota, use_adjacency_rule, use_anchors
                ]

        # 构造题面初始网格（数字+X+#）
        given_grid = [['X' for _ in range(n)] for _ in range(n)]
        for (r, c), num in clue_map.items():
            given_grid[r][c] = str(num)
        for (r, c) in blocked:
            given_grid[r][c] = '#'

        inst = {
            'grid_size': n,
            'directions': directions,
            'clues': [{'r': r, 'c': c, 'num': clue_map[(r, c)]} for (r, c) in sorted(clue_map.keys())],
            'row_counts': row_counts,
            'col_counts': col_counts,
            'given_grid': given_grid,
            'solution_grid': sol_grid_with_block,
            'regions': regions,
            'region_counts': region_counts,
            'blocked': blocked,
            'use_row_counts': use_row_counts,
            'use_col_counts': use_col_counts,
            'use_region_counts': use_region_counts,
            'use_dir_quota': use_dir_quota,
            'axis_quota': axis_quota,
            'diag_quota': diag_quota,
            'use_region_axisdiag': use_region_axisdiag,
            'region_axis_counts': region_axis_counts if use_region_axisdiag else [],
            'region_diag_counts': region_diag_counts if use_region_axisdiag else [],
            'use_perimeter_quota': use_perimeter_quota,
            'perimeter_quota': perimeter_quota if use_perimeter_quota else 0,
            'use_parity_quota': use_parity_quota,
            'black_quota': black_quota if use_parity_quota else 0,
            'white_quota': white_quota if use_parity_quota else 0,
            'use_adjacency_rule': use_adjacency_rule,
            'adj_rule_code': adj_rule_code if use_adjacency_rule else '',
            'use_anchors': use_anchors,
            'anchor_axis_cells': anchor_axis_cells if use_anchors else [],
            'anchor_diag_cells': anchor_diag_cells if use_anchors else []
        }

        sol_cnt, _ = _re_solve_count(inst, time_limit_sec=60)
        if sol_cnt == 1:
            return inst
        # 否则重试

    # 保底简单实例（不保证唯一，但尽量）
    n = 5
    directions = DIRS4[:]
    clue_pos = [(2, 2)]
    segs = compute_max_segments(n, clue_pos, directions)
    assignment = _choose_unique_assignment(segs, n)
    if not assignment:
        pos = (2, 2)
        dirs = list(segs[pos].keys())
        assignment = {pos: [max(dirs, key=lambda d: len(segs[pos][d]))]}
    clue_map = {(2, 2): sum(len(segs[(2, 2)][d]) for d in assignment[(2, 2)])}
    blocked = []
    sol_grid = _build_solution_grid(n, clue_map, segs, assignment, blocked=blocked)
    row_counts, col_counts = _compute_row_col_counts(sol_grid)
    regions = make_regions(n)
    region_counts = [0] * len(regions)
    for r in range(n):
        for c in range(n):
            if sol_grid[r][c] in DIRS8:
                idx = region_index_of(regions, r, c)
                if idx >= 0:
                    region_counts[idx] += 1
    axis_quota, diag_quota = _compute_dir_quota(sol_grid)
    given_grid = [['X' for _ in range(n)] for _ in range(n)]
    given_grid[2][2] = str(clue_map[(2, 2)])
    return {
        'grid_size': n,
        'directions': directions,
        'clues': [{'r': 2, 'c': 2, 'num': clue_map[(2, 2)]}],
        'row_counts': row_counts,
        'col_counts': col_counts,
        'given_grid': given_grid,
        'solution_grid': sol_grid,
        'regions': regions,
        'region_counts': region_counts,
        'blocked': blocked,
        'use_row_counts': True,
        'use_col_counts': False,
        'use_region_counts': True,
        'use_dir_quota': False,
        'axis_quota': axis_quota,
        'diag_quota': diag_quota,
        'use_region_axisdiag': False,
        'region_axis_counts': [],
        'region_diag_counts': [],
        'use_perimeter_quota': False,
        'perimeter_quota': 0,
        'use_parity_quota': False,
        'black_quota': 0,
        'white_quota': 0,
        'use_adjacency_rule': False,
        'adj_rule_code': '',
        'use_anchors': False,
        'anchor_axis_cells': [],
        'anchor_diag_cells': []
    }

# ----------------------------
# 便于 YAML 使用的导出接口
# ----------------------------
# gen_arrow_maze_instance
# solve_arrow_maze
# format_grid
# format_grid_sq
# format_list_sq
# format_regions_sq
# format_cells_sq
# build_rule_text
# example_answer_format
# （以上函数名需在 YAML custom_operator 中显式引入）