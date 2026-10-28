# number_wall_0.py
import random
import json
from collections import deque

def grid_to_json(grid):
    """以 JSON 字符串形式输出网格（双引号、Unicode 友好）。"""
    return json.dumps(grid, ensure_ascii=False)

def gen_unique_island_puzzle(rows, cols, max_attempts=1500):
    """
    逆向随机生成岛屿类谜题（保证唯一解）：
    1) 随机生成最终拓扑（'A' 墙，'X' 岛），并通过质量过滤（无 2x2 全墙、墙整体连通、无整行整列全墙、多岛且岛面积分布合理）；
    2) 每个岛随机放置唯一数字（数字=岛面积），其余岛格为 'X'，形成题面 initial；
    3) 回溯计数求解，若唯一（count==1）则返回题面、唯一解以及 ASCII 展示文本。
    """
    for _ in range(max_attempts):
        sol_topo = _random_solution_grid(rows, cols)
        if sol_topo is None:
            continue
        initial = _make_puzzle_from_solution(sol_topo)
        cnt, one_sol = _count_solutions(initial, limit=2)
        if cnt == 1 and one_sol is not None:
            return {
                'initial': initial,
                'solution': one_sol,
                'grid_text': _format_ascii_initial(initial)
            }
    raise RuntimeError("Failed to generate a unique puzzle after many attempts.")

########################
# 生成随机解与质量约束 #
########################

def _random_solution_grid(rows, cols):
    """
    随机生成一个符合规则的最终解拓扑：
    - 'A' 为墙，'X' 为岛；
    - 不存在 2×2 全 'A'；
    - 墙整体通过上下左右连通（一个连通块）；
    - 不存在整行或整列全为墙（避免过度简化的强约束）；
    - 岛的数量在 3~6 之间，且每个岛面积 2~9；
    - 至少存在一个面积 >= 4 的岛；
    - 至少有两种不同的岛面积（避免过于单调）。
    """
    for _ in range(900):
        wall_ratio = random.uniform(0.32, 0.52)  # 墙密度控制，避免过多预置墙
        g = [[('A' if random.random() < wall_ratio else 'X') for _ in range(cols)] for _ in range(rows)]

        # 过滤：禁止 2x2 全墙
        if not _check_no_2x2_walls(g):
            continue

        # 过滤：墙数量适中且墙整体连通
        wall_cnt = sum(1 for r in range(rows) for c in range(cols) if g[r][c] == 'A')
        if not (6 <= wall_cnt <= 16):  # 在 25 格中约 24%~64% 为墙
            continue
        if wall_cnt == 0 or not _check_walls_connected(g):
            continue

        # 过滤：避免整行或整列全墙
        if any(all(g[r][c] == 'A' for c in range(cols)) for r in range(rows)):
            continue
        if any(all(g[r][c] == 'A' for r in range(rows)) for c in range(cols)):
            continue

        # 连通岛列表（由 'X' 构成的连通块）
        comps = _connected_components(g, target='X')
        if not (3 <= len(comps) <= 6):
            continue

        sizes = [len(comp) for comp in comps]
        if min(sizes) < 2:
            continue
        if max(sizes) > 9:   # 避免过大的岛提示降低合理性
            continue
        if max(sizes) < 4:   # 至少有一个较大的岛，增加推理性
            continue
        if len(set(sizes)) < 2:  # 至少两种不同的尺寸，避免平凡
            continue

        # 通过基本质量过滤，接受该拓扑
        return g
    return None

def _check_walls_connected(grid):
    """检查所有 'A' 格是否构成一个上下左右连通的整体（至少一个墙格）。"""
    R, C = len(grid), len(grid[0])
    start = None
    total_walls = 0
    for r in range(R):
        for c in range(C):
            if grid[r][c] == 'A':
                total_walls += 1
                if start is None:
                    start = (r, c)
    if total_walls == 0:
        return False
    q = deque([start])
    vis = set([start])
    while q:
        x, y = q.popleft()
        for nx, ny in _neighbors(x, y, R, C):
            if grid[nx][ny] == 'A' and (nx, ny) not in vis:
                vis.add((nx, ny))
                q.append((nx, ny))
    return len(vis) == total_walls

def _make_puzzle_from_solution(sol_grid):
    """
    sol_grid：包含 'A' 和 'X' 的终局形态。
    处理：
    - 找出所有岛屿连通块（由 X 组成）
    - 每个岛随机选一个格子放数字（数字=该岛面积），
    - 其余格（包括原墙 A 区域）均设为 'X'，形成题面 initial。
    返回：题面 initial_grid（含数字与 X）
    """
    rows, cols = len(sol_grid), len(sol_grid[0])
    comps = _connected_components(sol_grid, target='X')
    
    # 核心修改：初始网格应全部为 'X'，然后只覆盖数字提示
    initial = [['X' for _ in range(cols)] for _ in range(rows)]
    
    for comp in comps:
        size = len(comp)
        r, c = random.choice(comp)
        initial[r][c] = size  # 放数字（每岛唯一）
    return initial

def _format_ascii_initial(initial):
    rows, cols = len(initial), len(initial[0])
    line = "+" + "+".join(["----"] * cols) + "+\n"
    out = []
    for r in range(rows):
        out.append(line)
        cells = []
        for c in range(cols):
            v = initial[r][c]
            cells.append(f" {v}  ")
        out.append("|" + "|".join(cells) + "| \n")
    out.append(line.rstrip("\n"))
    return "".join(out).rstrip("\n")

def _check_no_2x2_walls(grid):
    R, C = len(grid), len(grid[0])
    for r in range(R - 1):
        for c in range(C - 1):
            if grid[r][c] == 'A' and grid[r+1][c] == 'A' and grid[r][c+1] == 'A' and grid[r+1][c+1] == 'A':
                return False
    return True

def _neighbors(r, c, R, C):
    for dr, dc in ((1,0), (-1,0), (0,1), (0,-1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < R and 0 <= nc < C:
            yield nr, nc

def _connected_components(grid, target='X'):
    """计算由 target 字符构成的连通块（上下左右连通）。"""
    R, C = len(grid), len(grid[0])
    vis = [[False]*C for _ in range(R)]
    comps = []
    for r in range(R):
        for c in range(C):
            if not vis[r][c] and grid[r][c] == target:
                q = deque([(r,c)])
                vis[r][c] = True
                comp = [(r,c)]
                while q:
                    x,y = q.popleft()
                    for nx, ny in _neighbors(x,y,R,C):
                        if not vis[nx][ny] and grid[nx][ny] == target:
                            vis[nx][ny] = True
                            q.append((nx,ny))
                            comp.append((nx,ny))
                comps.append(comp)
    return comps

########################
#   求解与唯一性计数   #
########################

def _count_solutions(initial_grid, limit=2):
    """
    回溯计数（判定唯一解）：
    - 每数字为岛种子，岛面积=数字（含数字格）；
    - 岛仅上下左右连通；
    - 岛间不得正交相邻（需被墙 A 隔开）；
    - 墙无 2×2 全 A，且整体上下左右连通；
    - 输出解与题面同构：数字保留数字，岛内非数字格为 'X'，墙为 'A'。
    返回：(count, one_solution_grid or None)
    """
    rows, cols = len(initial_grid), len(initial_grid[0])

    # 收集数字种子
    seeds = []  # (sid, r, c, size)
    seed_map = [[-1]*cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if isinstance(initial_grid[r][c], int):
                sid = len(seeds)
                seeds.append((sid, r, c, initial_grid[r][c]))
                seed_map[r][c] = sid

    # 初始状态编码：-1 未定；-2 墙 A；>=0 岛 id
    state = [[-1]*cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if initial_grid[r][c] == 'A':
                state[r][c] = -2
    island_cells = {}
    for sid, r, c, size in seeds:
        state[r][c] = sid
        island_cells[sid] = {(r, c)}

    # 种子间若正交相邻 => 必须无解（不同岛必须以墙隔开）
    for sid, r, c, _ in seeds:
        for nr, nc in _neighbors(r, c, rows, cols):
            if isinstance(initial_grid[nr][nc], int) and seed_map[nr][nc] != sid:
                return (0, None)

    undecided = [(r, c) for r in range(rows) for c in range(cols) if state[r][c] == -1]

    solution_count = 0
    one_solution = None

    def need(sid):
        target = seeds[sid][3]
        return target - len(island_cells[sid])

    def violates_2x2_wall(r, c):
        if state[r][c] != -2:
            return False
        for dr in (0, -1):
            for dc in (0, -1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < rows-1 and 0 <= cc < cols-1:
                    if state[rr][cc] == -2 and state[rr+1][cc] == -2 and state[rr][cc+1] == -2 and state[rr+1][cc+1] == -2:
                        return True
        return False

    def max_reachable_for_island(sid):
        """从当前岛出发，经由未定(-1)格估计最多还能拓展的数量（不可穿越墙/其他岛）。"""
        seen = set(island_cells[sid])
        q = deque(island_cells[sid])
        count = 0
        while q:
            x, y = q.popleft()
            for nx, ny in _neighbors(x, y, rows, cols):
                if (nx, ny) in seen:
                    continue
                if state[nx][ny] == -1:
                    seen.add((nx, ny))
                    q.append((nx, ny))
                    count += 1
                elif state[nx][ny] == sid:
                    seen.add((nx, ny))
                    q.append((nx, ny))
        return count

    def prune_reachability():
        for sid, _, _, _ in seeds:
            rem = need(sid)
            if rem < 0:
                return True
            if rem > 0 and max_reachable_for_island(sid) < rem:
                return True
        return False

    def islands_touching_diff_ids(r, c, assign_id):
        """若赋为 assign_id，检查是否与其他岛正交相邻（不允许）。"""
        for nr, nc in _neighbors(r, c, rows, cols):
            if state[nr][nc] >= 0 and state[nr][nc] != assign_id:
                return True
        return False

    def must_be_wall_cell(r, c):
        """若该未定格与两个及以上不同岛正交相邻，则该格必须为墙。"""
        adj_ids = set()
        for nr, nc in _neighbors(r, c, rows, cols):
            if state[nr][nc] >= 0:
                adj_ids.add(state[nr][nc])
        return len(adj_ids) >= 2

    def pick_next_cell():
        # 选择策略：优先必须为墙的格；其次选择与某岛相邻的格（更受约束）；否则任取
        for (r, c) in undecided:
            if must_be_wall_cell(r, c):
                return (r, c)
        candidates = [(r, c) for (r, c) in undecided if any(state[nr][nc] >= 0 for nr, nc in _neighbors(r, c, rows, cols))]
        if candidates:
            return random.choice(candidates)
        return random.choice(undecided) if undecided else None

    def build_solution_grid():
        ans = []
        is_number = [[False]*cols for _ in range(rows)]
        for sid, r, c, _ in seeds:
            is_number[r][c] = True
        for r in range(rows):
            row = []
            for c in range(cols):
                if state[r][c] == -2:
                    row.append('A')
                elif state[r][c] >= 0:
                    row.append(initial_grid[r][c] if is_number[r][c] else 'X')
                else:
                    # 不应出现（完整解时所有格均应已定），为鲁棒性仍填 'A'
                    row.append('A')
            ans.append(row)
        return ans

    def walls_connected_final():
        """最终检查：所有墙格是否构成一个上下左右连通的整体（至少一个墙格）。"""
        R, C = rows, cols
        walls = [(r, c) for r in range(R) for c in range(C) if state[r][c] == -2]
        if not walls:
            return False
        start = walls[0]
        q = deque([start])
        vis = set([start])
        while q:
            x, y = q.popleft()
            for nx, ny in _neighbors(x, y, R, C):
                if state[nx][ny] == -2 and (nx, ny) not in vis:
                    vis.add((nx, ny))
                    q.append((nx, ny))
        return len(vis) == len(walls)

    def finished_and_valid():
        # 岛面积达标
        for sid, _, _, target in seeds:
            if len(island_cells[sid]) != target:
                return False
        # 墙 2x2 检查（全局）
        for r in range(rows-1):
            for c in range(cols-1):
                if state[r][c] == -2 and state[r+1][c] == -2 and state[r][c+1] == -2 and state[r+1][c+1] == -2:
                    return False
        # 墙整体连通
        if not walls_connected_final():
            return False
        return True

    def dfs():
        nonlocal solution_count, one_solution
        if solution_count >= limit:
            return
        if not undecided:
            if finished_and_valid():
                solution_count += 1
                if one_solution is None:
                    one_solution = build_solution_grid()
            return

        if prune_reachability():
            return

        r, c = pick_next_cell()
        undecided.remove((r, c))

        # 分支 1：该格为墙
        if must_be_wall_cell(r, c):
            state[r][c] = -2
            if not violates_2x2_wall(r, c):
                dfs()
            state[r][c] = -1
            undecided.append((r, c))
            return

        state[r][c] = -2
        if not violates_2x2_wall(r, c) and not prune_reachability():
            dfs()
        state[r][c] = -1

        # 分支 2：加入相邻岛之一
        adj_islands = set()
        for nr, nc in _neighbors(r, c, rows, cols):
            if state[nr][nc] >= 0:
                adj_islands.add(state[nr][nc])

        for sid in list(adj_islands):
            if islands_touching_diff_ids(r, c, sid):
                continue
            if need(sid) <= 0:
                continue
            state[r][c] = sid
            island_cells[sid].add((r, c))
            if not prune_reachability():
                dfs()
            island_cells[sid].remove((r, c))
            state[r][c] = -1

        undecided.append((r, c))

    dfs()
    return solution_count, one_solution