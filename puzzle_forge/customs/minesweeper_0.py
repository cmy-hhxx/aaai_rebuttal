import random

def _neighbors(r, c, R, C):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < R and 0 <= cc < C:
                yield rr, cc

def find_definite_mines(grid):
    """
    基于“一步逻辑”规则，返回所有必为地雷的坐标列表。
    """
    R = len(grid)
    C = len(grid[0]) if R else 0
    definite = set()

    for r in range(R):
        for c in range(C):
            val = grid[r][c]
            if isinstance(val, int):
                unknowns = [(rr, cc) for rr, cc in _neighbors(r, c, R, C) if grid[rr][cc] == 'X']
                if len(unknowns) > 0 and val == len(unknowns):
                    definite.update(unknowns)

    return sorted(list(definite))

def count_forcing_cells(grid):
    """
    统计能触发“一步逻辑”的格子数量。
    """
    R = len(grid)
    C = len(grid[0]) if R else 0
    cnt = 0
    for r in range(R):
        for c in range(C):
            val = grid[r][c]
            if isinstance(val, int):
                unknowns = [(rr, cc) for rr, cc in _neighbors(r, c, R, C) if grid[rr][cc] == 'X']
                if len(unknowns) > 0 and val == len(unknowns):
                    cnt += 1
    return cnt

def gen_minesweeper_grid(n_rows, n_cols, max_trials=200):
    """
    随机生成一个 n_rows x n_cols 的局面：
    修正点：生成的数字不会超过该位置实际拥有的邻居总数。
    """
    R, C = n_rows, n_cols
    cells = [(r, c) for r in range(R) for c in range(C)]

    for _ in range(max_trials):
        # 1) 选择数字格数目
        M = random.randint(1, min(6, R * C - 1))
        number_positions = random.sample(cells, M)
        
        # 2) 构建初始网格
        grid = [['X' for _ in range(C)] for _ in range(R)]
        for (r, c) in number_positions:
            grid[r][c] = 0 

        # 3) 选择一个强制触发格 p0
        p0 = random.choice(number_positions)

        # 4) 为 p0 赋值
        r0, c0 = p0
        unk0 = [(rr, cc) for rr, cc in _neighbors(r0, c0, R, C) if grid[rr][cc] == 'X']
        if len(unk0) == 0:
            continue
        grid[r0][c0] = len(unk0) # 这里必然 <= 邻居总数，因为 X 只是邻居的一部分

        # 5) 其它数字格赋值 (修正逻辑在这里)
        ok_assign = True
        for (r, c) in number_positions:
            if (r, c) == p0:
                continue
            
            # 获取相邻未揭示格（X）的数量
            unk = [(rr, cc) for rr, cc in _neighbors(r, c, R, C) if grid[rr][cc] == 'X']
            ui = len(unk)
            
            # --- 修改开始 ---
            # 计算该位置实际拥有的物理邻居总数 (角:3, 边:5, 中:8)
            total_neighbors = list(_neighbors(r, c, R, C))
            max_val = len(total_neighbors)
            
            # 候选值必须满足两个条件：
            # 1. 0 <= v <= max_val (不超过物理邻居上限)
            # 2. v != ui (不让它成为触发格，保证唯一解逻辑)
            candidates = [v for v in range(0, max_val + 1) if v != ui]
            # --- 修改结束 ---

            if not candidates:
                ok_assign = False
                break
            grid[r][c] = random.choice(candidates)
        
        if not ok_assign:
            continue

        # 6) 校验唯一性与非空答案
        if count_forcing_cells(grid) == 1:
            mines = find_definite_mines(grid)
            if len(mines) > 0:
                return grid

    # 兜底策略
    grid = [['X' for _ in range(C)] for _ in range(R)]
    grid[1][1] = 0 
    unk = [(rr, cc) for rr, cc in _neighbors(1, 1, R, C) if grid[rr][cc] == 'X']
    grid[1][1] = len(unk) if len(unk) > 0 else 1
    return grid