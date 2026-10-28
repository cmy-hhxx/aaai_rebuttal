# number_wall_5.py
import random
import time
from collections import deque

# 缓存，避免对同一grid与同一规则重复求解
_LAST_GRID_REF = None
_LAST_RULES_KEY = None
_LAST_SOLUTION = None
_LAST_COUNT = None

def neighbors4(r, c, rows, cols):
    for dr, dc in ((1,0), (-1,0), (0,1), (0,-1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < rows and 0 <= cc < cols:
            yield rr, cc

def neighbors8(r, c, rows, cols):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < rows and 0 <= cc < cols:
                yield rr, cc

def extract_clues(grid):
    """从网格中提取线索：返回[(r,c,val), ...]，其中val为正整数。"""
    clues = []
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if isinstance(v, int) and v > 0:
                clues.append((r, c, v))
    return clues

def gen_connected_shapes(start, size, rows, cols, forbidden, connectivity=4):
    """
    生成所有包含 start 且大小为 size 的连通格集合（连通性可选4或8；集合中不得包含 forbidden 的格）。
    返回列表[set((r,c), ...), ...]。
    """
    sr, sc = start
    if (sr, sc) in forbidden:
        return []
    nbr = neighbors4 if connectivity == 4 else neighbors8
    shapes = []
    seen = set()

    def backtrack(current_set):
        if len(current_set) == size:
            fs = frozenset(current_set)
            if fs not in seen:
                seen.add(fs)
                shapes.append(set(current_set))
            return
        frontier = set()
        for (r, c) in current_set:
            for (rr, cc) in nbr(r, c, rows, cols):
                if (rr, cc) not in current_set and (rr, cc) not in forbidden:
                    frontier.add((rr, cc))
        # 固定顺序，保证生成一致性
        for cell in sorted(frontier):
            current_set.add(cell)
            backtrack(current_set)
            current_set.remove(cell)

    backtrack({(sr, sc)})
    return shapes

def water_connected_and_no_kxk(water, rows, cols, k, need_single=True):
    """
    按4连通检查水域连通性与禁止k×k全水方块（k>=2时生效；k<=1视为不检查）。
    need_single=True 则要求单连通；否则不检查连通性。
    """
    if not water:
        return False
    # 连通性检查（按4连通）
    if need_single:
        start = next(iter(water))
        q = deque([start])
        visited = {start}
        while q:
            r, c = q.popleft()
            for rr, cc in neighbors4(r, c, rows, cols):
                if (rr, cc) in water and (rr, cc) not in visited:
                    visited.add((rr, cc))
                    q.append((rr, cc))
        if len(visited) != len(water):
            return False
    # 禁止k×k全水
    if k and k >= 2:
        for r in range(rows - (k - 1)):
            for c in range(cols - (k - 1)):
                all_in = True
                for dr in range(k):
                    for dc in range(k):
                        if (r + dr, c + dc) not in water:
                            all_in = False
                            break
                    if not all_in:
                        break
                if all_in:
                    return False
    return True

def islands_separation_ok(shapes, mode='no_orth'):
    """
    不同岛屿的相邻禁忌检查：
    - 'no_orth': 禁止正交相邻（对角允许）
    - 'no_adjacent': 禁止任意相邻（正交或对角都不允许）
    """
    for i in range(len(shapes)):
        for j in range(i+1, len(shapes)):
            si, sj = shapes[i], shapes[j]
            for (r, c) in si:
                # 正交
                if (r+1, c) in sj or (r-1, c) in sj or (r, c+1) in sj or (r, c-1) in sj:
                    return False
                if mode == 'no_adjacent':
                    # 对角
                    if (r+1, c+1) in sj or (r+1, c-1) in sj or (r-1, c+1) in sj or (r-1, c-1) in sj:
                        return False
    return True

def render_grid_text(grid):
    """将 grid 渲染为单行字符串 '[ a, b; c, d ]' 格式。"""
    parts = []
    for row in grid:
        row_s = ', '.join(str(x) for x in row)
        parts.append(row_s)
    return '[ ' + '; '.join(parts) + ' ]'

def _canonical_islands_pairs_str(clues, shapes_in_original_order):
    """
    新版：返回无空格、无花括号的标准化字符串：
    '[(r,c)->[(r1,c1),(r2,c2)],(r2,c2)->[(...),(...)] ]'
    键与列表均按坐标字典序（先r再c升序）排序。
    """
    items = []
    for (r, c, _sz), shape in sorted(zip(clues, shapes_in_original_order), key=lambda x: (x[0][0], x[0][1])):
        arr = sorted(list(shape))
        v = '[' + ','.join(f'({rr},{cc})' for (rr,cc) in arr) + ']'
        items.append(f'({r},{c})->{v}')
    return '[' + ','.join(items) + ']'

def _rules_key(rules_cfg):
    """将规则配置压缩为可缓存的短键。"""
    ic = rules_cfg.get('island_conn', 4)
    ia = rules_cfg.get('island_adj_mode', 'no_orth')
    wk = rules_cfg.get('forbid_block_k', 2)
    ws = rules_cfg.get('water_conn_single', True)
    bt = rules_cfg.get('border_touch_req', 3)
    wm = rules_cfg.get('water_topology_mode', 'robust')
    return f'ic={ic}|ia={ia}|wk={wk}|ws={int(bool(ws))}|bt={bt}|wm={wm}'

def border_touch_count(water, rows, cols):
    """计算河道触及的边数（上下左右四边）。"""
    touches = 0
    if any((0, c) in water for c in range(cols)): touches += 1
    if any((rows-1, c) in water for c in range(cols)): touches += 1
    if any((r, 0) in water for r in range(rows)): touches += 1
    if any((r, cols-1) in water for r in range(rows)): touches += 1
    return touches

def water_articulation_points(water, rows, cols):
    """
    计算水域的割点（关键节点）集合，按4连通图进行Tarjan算法。
    返回set((r,c), ...)，可能为空集合。
    """
    if not water:
        return set()
    # 建图
    adj = {}
    for (r, c) in water:
        adj[(r, c)] = []
        for rr, cc in neighbors4(r, c, rows, cols):
            if (rr, cc) in water:
                adj[(r, c)].append((rr, cc))

    # Tarjan割点
    time_idx = 0
    disc = {}
    low = {}
    parent = {}
    ap = set()

    def dfs(u):
        nonlocal time_idx
        children = 0
        time_idx += 1
        disc[u] = time_idx
        low[u] = time_idx
        for v in adj[u]:
            if v not in disc:
                parent[v] = u
                children += 1
                dfs(v)
                low[u] = min(low[u], low[v])
                # 根节点情况
                if u not in parent and children > 1:
                    ap.add(u)
                # 非根节点情况
                if u in parent and low[v] >= disc[u]:
                    ap.add(u)
            elif parent.get(u) != v:
                low[u] = min(low[u], disc[v])

    for u in adj:
        if u not in disc:
            dfs(u)
    return ap

def enumerate_solutions(grid, rules_cfg, time_limit_sec=150, limit=None):
    """
    枚举所有满足规则的完整配置（岛屿形状组合），返回解payload列表。
    每个payload包含：
    - 'water_set': set((r,c), ...)
    - 'A_count': int
    - 'A_coords_str': '[(r,c),...]'（无空格，按(r,c)升序）
    - 'A_coords_key': [(r,c), ...]（用于规范化比较的排序键）
    - 'islands_pairs_str': '[(r,c)->[(r1,c1),...], ...]'（无空格）
    剪枝：按候选形状数量与线索大小排序，逐步尝试；每步检查相邻禁忌与占用。
    limit: 若非None，则当解数量达到limit后停止搜索（用于唯一性验证早停）。
    """
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    clues = extract_clues(grid)
    start_time = time.perf_counter()

    # 预设水域格 'A'
    preA = set()
    for r in range(rows):
        for c in range(cols):
            v = grid[r][c]
            if isinstance(v, str) and v.upper() == 'A':
                preA.add((r, c))

    # 线索坐标集合
    clue_positions = {(r, c) for (r, c, _) in clues}

    ia_mode = rules_cfg.get('island_adj_mode', 'no_orth')
    forbid_block_k = rules_cfg.get('forbid_block_k', 2)
    need_single = bool(rules_cfg.get('water_conn_single', True))
    border_req = int(rules_cfg.get('border_touch_req', 3))
    topo_mode = str(rules_cfg.get('water_topology_mode', 'robust'))
    island_conn = rules_cfg.get('island_conn', 4)

    # 生成每个线索的所有可能形状（不可包含其它线索格与预设水域格，且避免与其它线索起点相邻的格）
    all_shape_lists = []
    for (r, c, sz) in clues:
        # 基本禁区：其他线索位置与预设水域
        forbidden = (clue_positions - {(r, c)}) | preA
        # 额外禁区：避免与其它线索起点相邻（与题面规则一致的预剪枝）
        for (rr, cc) in (clue_positions - {(r, c)}):
            if ia_mode == 'no_adjacent':
                for pos in neighbors8(rr, cc, rows, cols):
                    forbidden.add(pos)
            else:
                for pos in neighbors4(rr, cc, rows, cols):
                    forbidden.add(pos)
        shapes = gen_connected_shapes((r, c), sz, rows, cols, forbidden, connectivity=island_conn)
        if not shapes:
            return []  # 无法构造该线索的岛，直接无解
        all_shape_lists.append(shapes)

    # 线索重排：先处理候选形状数少的，以加快回溯
    order = list(range(len(clues)))
    order.sort(key=lambda i: (len(all_shape_lists[i]), clues[i][2]))
    ordered_shapes = [all_shape_lists[i] for i in order]

    solutions = []
    occupied = set()
    chosen = [None] * len(ordered_shapes)

    def touch_forbidden(s1, s2):
        # 返回是否触犯当前模式（相邻禁忌）
        for (r, c) in s1:
            # 正交
            if (r+1, c) in s2 or (r-1, c) in s2 or (r, c+1) in s2 or (r, c-1) in s2:
                return True
            if ia_mode == 'no_adjacent':
                if (r+1, c+1) in s2 or (r+1, c-1) in s2 or (r-1, c+1) in s2 or (r-1, c-1) in s2:
                    return True
        return False

    def backtrack(idx):
        # 时间与数量限制
        if time.perf_counter() - start_time > time_limit_sec:
            return
        if limit is not None and len(solutions) >= limit:
            return

        if idx == len(ordered_shapes):
            # 还原为原线索顺序
            shapes_in_original_order = [None] * len(ordered_shapes)
            for k, i_orig in enumerate(order):
                shapes_in_original_order[i_orig] = chosen[k]
            # 岛屿之间相邻禁忌
            if not islands_separation_ok(shapes_in_original_order, mode=ia_mode):
                return
            # 计算水域（补全集合：所有非岛格即为水域）
            land = set()
            for s in shapes_in_original_order:
                land |= s
            all_cells = {(r, c) for r in range(rows) for c in range(cols)}
            water = all_cells - land
            # 预设水域必须包含
            if not preA.issubset(water):
                return
            # 水域连通性与禁止k×k全水块（按4连通）
            if not water_connected_and_no_kxk(water, rows, cols, forbid_block_k, need_single=need_single):
                return
            # 边界触达数量
            bt = border_touch_count(water, rows, cols)
            if bt < border_req:
                return
            # 拓扑模式：割点数目限制（按4连通图）
            aps = water_articulation_points(water, rows, cols)
            if topo_mode == 'robust':
                if len(aps) != 0:
                    return
            elif topo_mode == 'bridge_once':
                if len(aps) != 1:
                    return
            else:
                return  # 未知拓扑模式，视为不合格

            coords_sorted = sorted(list(water))
            islands_pairs_str = _canonical_islands_pairs_str(clues, shapes_in_original_order)
            payload = {
                'water_set': water,
                'A_count': len(water),
                'A_coords_key': coords_sorted,  # 稳定排序键（列表[(r,c),...]）
                'A_coords_str': '[' + ','.join(f'({r},{c})' for (r,c) in coords_sorted) + ']',
                'islands_pairs_str': islands_pairs_str
            }
            solutions.append(payload)
            return

        for shape in ordered_shapes[idx]:
            # 与已选形状不重叠
            if any(cell in occupied for cell in shape):
                continue
            # 相邻禁忌剪枝
            ok_isolation = True
            for prev in range(idx):
                if chosen[prev] is None:
                    continue
                if touch_forbidden(chosen[prev], shape):
                    ok_isolation = False
                    break
            if not ok_isolation:
                continue
            # 放置形状
            for cell in shape:
                occupied.add(cell)
            chosen[idx] = shape
            backtrack(idx + 1)
            # 回退
            for cell in shape:
                occupied.remove(cell)
            chosen[idx] = None

    backtrack(0)
    return solutions

def solve_green_valley(grid, rules_cfg):
    """
    在题面规则下求解并返回规范化（按 A_coords_key 词典序最小）的解。
    生成器确保唯一解；若非唯一，答案函数将据 _LAST_COUNT 抛错。
    """
    global _LAST_GRID_REF, _LAST_RULES_KEY, _LAST_SOLUTION, _LAST_COUNT
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    # 缓存命中
    key = _rules_key(rules_cfg)
    if _LAST_GRID_REF is grid and _LAST_RULES_KEY == key and _LAST_SOLUTION is not None:
        return _LAST_SOLUTION

    sols = enumerate_solutions(grid, rules_cfg, time_limit_sec=150, limit=None)
    if not sols:
        raise ValueError('No valid configuration found under given constraints.')

    # 使用稳定的 A_coords_key 进行规范化排序
    sols_sorted = sorted(sols, key=lambda s: s['A_coords_key'])
    best_payload = sols_sorted[0]
    _LAST_GRID_REF = grid
    _LAST_RULES_KEY = key
    _LAST_SOLUTION = best_payload
    _LAST_COUNT = len(sols_sorted)
    return best_payload

def check_unique_solution(grid, rules_cfg, time_limit_sec=150):
    """枚举全部解并检查唯一性（数量为1）。发现第2个解即早停。"""
    sols = enumerate_solutions(grid, rules_cfg, time_limit_sec=time_limit_sec, limit=2)
    return len(sols) == 1

def solve_green_valley_A_count(grid, rules_cfg):
    """返回规范化（唯一化）解中A（水域）格子的数量。若非唯一，抛出异常提示生成器需重试。"""
    sol = solve_green_valley(grid, rules_cfg)
    if _LAST_COUNT is not None and _LAST_COUNT != 1:
        raise ValueError('Non-unique solution encountered; generation should enforce uniqueness.')
    return sol['A_count']

def solve_green_valley_A_coords_str(grid, rules_cfg):
    """返回规范化（唯一化）解中所有A坐标的标准字符串表示（无空格）。"""
    sol = solve_green_valley(grid, rules_cfg)
    if _LAST_COUNT is not None and _LAST_COUNT != 1:
        raise ValueError('Non-unique solution encountered; generation should enforce uniqueness.')
    return sol['A_coords_str']

def solve_green_valley_islands_pairs_str(grid, rules_cfg):
    """返回规范化（唯一化）解中每个线索对应的岛屿坐标关系列表字符串（无空格，无花括号）。"""
    sol = solve_green_valley(grid, rules_cfg)
    if _LAST_COUNT is not None and _LAST_COUNT != 1:
        raise ValueError('Non-unique solution encountered; generation should enforce uniqueness.')
    return sol['islands_pairs_str']

def choose_clue_num(rows, cols):
    """
    根据尺寸随机选取线索数量，控制复杂度与唯一性成功率：
    - 5x5: 3~4
    - 6x5/5x6: 4~5
    - 6x6: 4~5
    """
    area = rows * cols
    if area <= 25:
        lo, hi = 3, 4
    elif area <= 30:
        lo, hi = 4, 5
    else:
        lo, hi = 4, 5
    return random.randint(lo, hi)

def choose_preA_num(rows, cols):
    """
    预设水格数量：小尺寸偏少，0~2之间随机，偏向0或1。
    """
    r = random.random()
    if r < 0.6:
        return 0
    elif r < 0.9:
        return 1
    else:
        return 2

def _pick_non_adjacent_positions(rows, cols, k):
    """
    选择k个互不正交相邻的位置（避免相邻线索直接判为非法），若失败返回None。
    """
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    random.shuffle(cells)
    chosen = []
    for (r, c) in cells:
        ok = True
        for (rr, cc) in chosen:
            if abs(rr - r) + abs(cc - c) == 1:
                ok = False
                break
        if ok:
            chosen.append((r, c))
            if len(chosen) == k:
                break
    if len(chosen) < k:
        return None
    return chosen

def choose_forbid_block_k(rows, cols):
    """
    随机选择禁止的全A方块大小k：
    - 概率分布：k=2 概率约0.7；k=3 概率约0.2；k=0（不启用）概率约0.1
    """
    r = random.random()
    if r < 0.7:
        return 2
    elif r < 0.9:
        return 3
    else:
        return 0

def choose_island_adj_mode():
    """
    随机选择不同岛屿之间的相邻禁忌模式：
    - 'no_orth' 概率约0.75（禁止正交相邻，可对角）
    - 'no_adjacent' 概率约0.25（禁止任意相邻）
    """
    return 'no_orth' if random.random() < 0.75 else 'no_adjacent'

def choose_island_conn():
    """
    随机选择岛屿连通性：
    - 4连通 概率约0.85
    - 8连通 概率约0.15
    """
    return 4 if random.random() < 0.85 else 8

def choose_water_conn_single():
    """
    是否要求水域单一连通：
    - 当前版本固定为 True（保留为函数以便后续拓展）
    """
    return True

def choose_border_touch_req(rows, cols):
    """
    河道触达边数的随机需求：
    - 触达至少3条边的概率约0.6
    - 触达全部4条边的概率约0.4
    """
    return 3 if random.random() < 0.6 else 4

def choose_water_topology_mode():
    """
    河道拓扑模式随机选择：
    - 'robust'（无关键节点）概率约0.6
    - 'bridge_once'（恰有一个关键节点）概率约0.4
    """
    return 'robust' if random.random() < 0.6 else 'bridge_once'

def make_rules_config(forbid_block_k, island_adj_mode, island_conn, water_conn_single,
                      border_touch_req, water_topology_mode):
    """
    组装规则配置字典，便于在生成与求解时统一使用。
    """
    return {
        'forbid_block_k': int(forbid_block_k),
        'island_adj_mode': str(island_adj_mode),
        'island_conn': int(island_conn),
        'water_conn_single': bool(water_conn_single),
        'border_touch_req': int(border_touch_req),
        'water_topology_mode': str(water_topology_mode),
    }

def render_rules_text(rows, cols, forbid_block_k, island_adj_mode, island_conn,
                      border_touch_req, water_topology_mode):
    """
    生成题面中的规则文本（单行、无双引号、无需花括号；不包含唯一化/生成逻辑）。
    按顺序：
    (1) 划分规则；(2) 数字—岛规则；(3) 水域单连通；(4) 禁止k×k全A；
    (5) 岛屿相互隔离；(6) 岛屿连通性；(7) 预设A不可被覆盖；(8) 边界触达；(9) 拓扑模式。
    """
    parts = []
    # 1) 划分规则
    parts.append('(1) 所有格子必须被划分为A水域或某个岛屿格，二者必居其一')
    # 2) 数字—岛规则
    parts.append('(2) 每个数字格所在的岛屿恰含这一个数字格，且该岛屿大小等于该数字，所有岛屿彼此不重叠')
    # 3) 水域单连通（明确4连通）
    parts.append('(3) 所有A必须形成单一连通网络（按4连通）')
    # 4) 禁止k×k全A
    if int(forbid_block_k) >= 2:
        parts.append(f'(4) 禁止出现任何{int(forbid_block_k)}×{int(forbid_block_k)}的全A方块')
    else:
        parts.append('(4) 本关不启用针对方形全A的禁止规则')
    # 5) 岛屿相邻禁忌
    if island_adj_mode == 'no_adjacent':
        parts.append('(5) 不同岛屿之间必须由A完全分隔且不允许任意相邻')
    else:
        parts.append('(5) 不同岛屿之间必须由A完全分隔且不允许水平或垂直相接')
    # 6) 岛屿连通与大小
    if int(island_conn) == 8:
        parts.append('(6) 每个岛屿分量必须为8连通')
    else:
        parts.append('(6) 每个岛屿分量必须为4连通')
    # 7) 预设A格
    parts.append('(7) 若某格在题面中标记为A，则该格预设为水域且不得被任何岛屿覆盖')
    # 8) 边界触达要求
    if int(border_touch_req) == 4:
        parts.append('(8) 河道必须触及四条边中的全部4条边（上、下、左、右）')
    else:
        parts.append(f'(8) 河道必须至少触及四条边中的{int(border_touch_req)}条边（上、下、左、右中任意{int(border_touch_req)}条）')
    # 9) 拓扑模式说明（明确4连通图）
    if water_topology_mode == 'robust':
        parts.append('(9) 拓扑要求：河道在按4连通图判定下不存在任何关键节点（移除此格会将河道分成多个连通片的河道格称为关键节点）')
    else:
        parts.append('(9) 拓扑要求：河道在按4连通图判定下恰好存在一个关键节点（移除此格会将河道分成多个连通片的河道格称为关键节点）')
    return '；'.join(parts)

def generate_green_valley_instance(rows, cols, clue_num, size_low, size_high, preA_num, rules_cfg):
    """
    生成一个随机网格（包含'X'、正整数线索、可选'A'），并保证在题面规则下可求解且唯一。
    若尝试一定次数仍失败，将自适应减小线索数量后继续尝试，整体时间不超过约180秒。
    """
    def try_once(k_clues, deadline):
        # 初始化全'X'
        grid = [['X' for _ in range(cols)] for _ in range(rows)]
        # 选线索位置，避免正交相邻
        positions = _pick_non_adjacent_positions(rows, cols, k_clues)
        if positions is None:
            return None
        # 随机给线索大小（缩减上限后，枚举更稳定）
        sizes = [random.randint(size_low, size_high) for _ in range(k_clues)]
        # 写入线索
        for (r, c), sz in zip(positions, sizes):
            grid[r][c] = sz
        # 预设水格'A'
        free_cells = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] == 'X']
        random.shuffle(free_cells)
        chosen_A = []
        for (r, c) in free_cells:
            if len(chosen_A) == preA_num:
                break
            # 不与已有'A'正交相邻（提高可行性）
            ok = True
            for (rr, cc) in chosen_A:
                if abs(rr - r) + abs(cc - c) == 1:
                    ok = False
                    break
            if ok:
                chosen_A.append((r, c))
        for (r, c) in chosen_A:
            grid[r][c] = 'A'
        # 可解与唯一性检查（带时间限制，第二解早停）
        if time.perf_counter() > deadline:
            return None
        try:
            unique = check_unique_solution(grid, rules_cfg, time_limit_sec=max(1, int(deadline - time.perf_counter())))
            if unique:
                # 调用一次求解以填充缓存（可选）
                _ = solve_green_valley(grid, rules_cfg)
                return grid
            else:
                return None
        except Exception:
            return None

    deadline_global = time.perf_counter() + 180.0  # 总时限约3分钟
    k = clue_num
    while k >= 3 and time.perf_counter() < deadline_global:
        for _ in range(200):
            g = try_once(k, deadline_global)
            if g is not None:
                return g
        k -= 1  # 降低线索数量以提高成功率
    raise ValueError('Failed to generate a valid unique instance with given parameters under current rules.')