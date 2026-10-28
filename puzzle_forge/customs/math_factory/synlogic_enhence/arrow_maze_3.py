# arrow_maze_5.py
# 自定义算子：随机化布局、数值计算、文本渲染与唯一性校验（适配可变尺寸、规则变体与新增高阶约束）

from copy import deepcopy
import random
from collections import deque

# 方向编码：0=上, 1=右, 2=下, 3=左
DIRS = [(-1,0),(0,1),(1,0),(0,-1)]
SIDE_CODE = {0: 'U', 1: 'R', 2: 'D', 3: 'L'}  # 出界边标记

def _reflect_dir(d, mirror):
    # 正交反射
    if mirror == '/':
        mapping = {0:1, 1:0, 2:3, 3:2}
        return mapping[d]
    elif mirror == '\\':
        mapping = {0:3, 3:0, 2:1, 1:2}
        return mapping[d]
    else:
        return d

def _in_bounds(r, c, n):
    return 0 <= r < n and 0 <= c < n

def _is_block(cell):
    # 阻挡传播的格：陨石或数字（源）
    if cell == '#':
        return True
    if isinstance(cell, int):
        return True
    return False

def _cell_is_mirror(cell):
    return cell == '/' or cell == '\\'

def _trace_one_ray(board, sr, sc, d, visited_cells):
    """
    从源(sr, sc)朝方向d发射一条射线，返回路径长度。
    规则：
      1. 看前方格 next，如果越界或为阻挡('#'或数字源)，则立刻终止，不进入，不计步。
      2. 否则进入 next，计步+1。
      3. 若 next 为镜子，则改变方向。
      4. 若 next 已被该源的其他射线访问过（visited_cells中已有），则返回 -1（同源相交，非法）。
    """
    n = len(board)
    length = 0
    r, c = sr, sc
    while True:
        dr, dc = DIRS[d]
        nr, nc = r + dr, c + dc
        if not _in_bounds(nr, nc, n):
            return length
        cell = board[nr][nc]
        if _is_block(cell):
            return length
        if (nr, nc) in visited_cells:
            return -1
        visited_cells.add((nr, nc))
        length += 1
        if _cell_is_mirror(cell):
            d = _reflect_dir(d, cell)
        r, c = nr, nc

def _trace_one_ray_stats(board, sr, sc, d, visited_cells):
    """
    统计版本：返回 (路径长度, 反射次数, 出界边或None)。
    若同源相交，返回 (-1, 0, None)。
    """
    n = len(board)
    length = 0
    reflects = 0
    r, c = sr, sc
    dd = d
    while True:
        dr, dc = DIRS[dd]
        nr, nc = r + dr, c + dc
        if not _in_bounds(nr, nc, n):
            return length, reflects, SIDE_CODE[dd]
        cell = board[nr][nc]
        if _is_block(cell):
            return length, reflects, None
        if (nr, nc) in visited_cells:
            return -1, 0, None
        visited_cells.add((nr, nc))
        length += 1
        if _cell_is_mirror(cell):
            reflects += 1
            dd = _reflect_dir(dd, cell)
        r, c = nr, nc

def _compute_source_total(board, sr, sc):
    """
    计算单一源的四向路径总长度；若违反同源不相交，返回 None。
    """
    visited = set()
    total = 0
    for d in range(4):
        l = _trace_one_ray(board, sr, sc, d, visited)
        if l == -1:
            return None
        total += l
    return total

def _compute_source_stats(board, sr, sc):
    """
    计算单一源的统计信息：返回 (总长度, 总反射次数, 出界边计数字典)
    若违反同源不相交，返回 None。
    """
    visited = set()
    total_len = 0
    total_reflects = 0
    exit_counts = {'U':0, 'R':0, 'D':0, 'L':0}
    for d in range(4):
        l, r, side = _trace_one_ray_stats(board, sr, sc, d, visited)
        if l == -1:
            return None
        total_len += l
        total_reflects += r
        if side is not None:
            exit_counts[side] += 1
    return total_len, total_reflects, exit_counts

def _compute_source_lengths(board, sr, sc):
    """
    返回该源四向各自路径长度列表 [l_up, l_right, l_down, l_left]。
    若同源相交则返回 None。
    """
    visited = set()
    lens = []
    for d in range(4):
        l = _trace_one_ray(board, sr, sc, d, visited)
        if l == -1:
            return None
        lens.append(l)
    return lens

def fill_numbers_limit(final_grid, max_per_row):
    """
    输入包含 '#', '/', '\\' 的最终网格，其中整数格即为激光源；
    返回将每个源的四向总长度正确赋值后的 number_grid（包含 int、'#'、镜子与 '.' 空白）。
    若出现同源射线相交或其它非法情况，抛出异常。
    """
    n = len(final_grid)
    board = deepcopy(final_grid)
    # 先验证每行镜子数量（已固定镜子）
    for r in range(n):
        cnt = sum(1 for c in range(n) if _cell_is_mirror(board[r][c]))
        if cnt > int(max_per_row):
            raise ValueError(f'Row {r} has more than {max_per_row} mirrors in final_grid.')
    # 计算每个源（整数格）
    for r in range(n):
        for c in range(n):
            if isinstance(board[r][c], int):
                total = _compute_source_total(board, r, c)
                if total is None:
                    raise ValueError('Ray overlap detected for a source in final_grid.')
                board[r][c] = int(total)
    return board

def hide_mirrors(number_grid):
    """
    将 number_grid 中的镜子替换为 '?'，其余（数字、'#' 与 '.'）保持不变。
    """
    n = len(number_grid)
    res = []
    for r in range(n):
        row = []
        for c in range(n):
            cell = number_grid[r][c]
            if _cell_is_mirror(cell):
                row.append('?')
            else:
                row.append(cell)
        res.append(row)
    return res

def grid_to_string(grid):
    """
    将二维网格转为可嵌入单行 desc 的字符串：各行以空格分隔，行间用字面量 '\\n' 连接（非真实换行）。
    """
    lines = []
    for row in grid:
        tokens = []
        for cell in row:
            if isinstance(cell, int):
                tokens.append(str(cell))
            else:
                tokens.append(cell)
        lines.append(' '.join(tokens))
    return '\\n'.join(lines)

def grid_to_pylist(grid):
    """
    将二维网格转为 Python 列表字面量风格的单行字符串，元素使用单引号包裹（非数字）。
    例如: [[3, '#', 0], ['#', '/', 2], ...]；'.' 作为空白可通行格。
    注意: 反斜杠镜子会被转义为 '\\\\' 以保证字符串比较安全。
    """
    rows = []
    for row in grid:
        items = []
        for cell in row:
            if isinstance(cell, int):
                items.append(str(cell))
            else:
                if cell == '\\':
                    items.append("'\\\\'")
                else:
                    items.append("'" + str(cell) + "'")
        rows.append('[' + ', '.join(items) + ']')
    return '[' + ', '.join(rows) + ']'

# -------------------------
# 结构性规则检查（位置与取向相关）
# -------------------------

def _count_row_mirrors(board):
    n = len(board)
    return [sum(1 for c in range(n) if _cell_is_mirror(board[r][c])) for r in range(n)]

def _count_col_mirrors(board):
    n = len(board)
    return [sum(1 for r in range(n) if _cell_is_mirror(board[r][c])) for c in range(n)]

def _count_row_slash(board):
    n = len(board)
    return [sum(1 for c in range(n) if board[r][c] == '/') for r in range(n)]

def _count_col_slash(board):
    n = len(board)
    return [sum(1 for r in range(n) if board[r][c] == '/') for c in range(n)]

def _count_diag_slash(board):
    n = len(board)
    main = sum(1 for i in range(n) if board[i][i] == '/')
    anti = sum(1 for i in range(n) if board[i][n-1-i] == '/')
    return main, anti

def _check_no_adjacency(board):
    """
    镜子之间不能四邻接（上/下/左/右）。
    """
    n = len(board)
    for r in range(n):
        for c in range(n):
            if _cell_is_mirror(board[r][c]):
                for dr, dc in DIRS:
                    nr, nc = r + dr, c + dc
                    if _in_bounds(nr, nc, n) and _cell_is_mirror(board[nr][nc]):
                        return False
    return True

def _largest_mirror_cluster(board):
    """
    返回镜子的最大4连通块大小。
    """
    n = len(board)
    vis = [[False]*n for _ in range(n)]
    best = 0
    for r in range(n):
        for c in range(n):
            if _cell_is_mirror(board[r][c]) and not vis[r][c]:
                q = deque()
                q.append((r,c))
                vis[r][c] = True
                size = 1
                while q:
                    rr, cc = q.popleft()
                    for dr, dc in DIRS:
                        nr, nc = rr + dr, cc + dc
                        if _in_bounds(nr, nc, n) and not vis[nr][nc] and _cell_is_mirror(board[nr][nc]):
                            vis[nr][nc] = True
                            q.append((nr, nc))
                            size += 1
                if size > best:
                    best = size
    return best

def validate_grid_all(number_grid, row_limit=2, use_col_limit=False, col_limit=0,
                      adjacency_enabled=False, row_parity_mode='none', row_parity_rows=None,
                      cluster_limit=0,
                      row_orient_mode='none', row_orient_rows=None,
                      col_orient_mode='none', col_orient_cols=None,
                      diag_orient_mode='none',
                      source_turn_mode='none', source_turn_rows=None,
                      exit_mode='none', exit_sides=None):
    """
    完整校验：
      - 每行镜子数 <= row_limit（位置类内部约束）
      - 若启用列上限：每列镜子数 <= col_limit（位置类内部约束）
      - 若启用邻接禁令：镜子间不得四邻接（位置类内部约束）
      - 若启用行奇偶：指定行的镜子计数满足偶数/奇数（位置类内部约束）
      - 若启用镜子簇上限：最大镜子4连通块大小 <= cluster_limit（位置类内部约束）
      - 数字源的四向路径总长度等于该数字（核心）
      - 同一源任意两条射线不重格（核心；不同源可共享格）
      - 四向每一条射线长度均至少为 1（核心；与题面一致）
      - 行/列/对角线的 '/' 镜子数量满足偶/奇约束（核心）
      - 指定行上的源的总反射次数满足偶/奇约束（核心）
      - 指定边出界的射线数量满足偶/奇约束（核心）
    """
    n = len(number_grid)
    # 行上限
    row_counts = _count_row_mirrors(number_grid)
    for r in range(n):
        if row_counts[r] > int(row_limit):
            return False
    # 列上限
    if use_col_limit:
        col_counts = _count_col_mirrors(number_grid)
        for c in range(n):
            if col_counts[c] > int(col_limit):
                return False
    # 邻接禁令
    if adjacency_enabled:
        if not _check_no_adjacency(number_grid):
            return False
    # 行奇偶（镜子总数的奇偶）
    if row_parity_mode != 'none':
        rows_set = set(int(x) for x in (row_parity_rows or []))
        for r in rows_set:
            cnt = row_counts[r]
            if row_parity_mode == 'subset_even':
                if cnt % 2 != 0:
                    return False
            elif row_parity_mode == 'subset_odd':
                if cnt % 2 != 1:
                    return False
            else:
                return False
    # 取向约束：行/列 '/' 的奇偶
    if row_orient_mode != 'none':
        rows_set = set(int(x) for x in (row_orient_rows or []))
        row_slash = _count_row_slash(number_grid)
        for r in rows_set:
            cnt = row_slash[r]
            if row_orient_mode == 'subset_slash_even':
                if cnt % 2 != 0:
                    return False
            elif row_orient_mode == 'subset_slash_odd':
                if cnt % 2 != 1:
                    return False
            else:
                return False
    if col_orient_mode != 'none':
        cols_set = set(int(x) for x in (col_orient_cols or []))
        col_slash = _count_col_slash(number_grid)
        for c in cols_set:
            cnt = col_slash[c]
            if col_orient_mode == 'subset_slash_even':
                if cnt % 2 != 0:
                    return False
            elif col_orient_mode == 'subset_slash_odd':
                if cnt % 2 != 1:
                    return False
            else:
                return False
    if diag_orient_mode != 'none':
        main, anti = _count_diag_slash(number_grid)
        if diag_orient_mode == 'maindiag_even':
            if main % 2 != 0:
                return False
        elif diag_orient_mode == 'maindiag_odd':
            if main % 2 != 1:
                return False
        elif diag_orient_mode == 'antidiag_even':
            if anti % 2 != 0:
                return False
        elif diag_orient_mode == 'antidiag_odd':
            if anti % 2 != 1:
                return False
        else:
            return False
    # 簇上限
    if int(cluster_limit) > 0:
        if _largest_mirror_cluster(number_grid) > int(cluster_limit):
            return False
    # 数值与不相交校验 + 源反射/出界统计 + 每条射线长度下限
    exit_total = {'U':0, 'R':0, 'D':0, 'L':0}
    for r in range(n):
        for c in range(n):
            if isinstance(number_grid[r][c], int):
                expected = number_grid[r][c]
                # 每条射线长度均至少为1
                lens = _compute_source_lengths(number_grid, r, c)
                if lens is None or any(l < 1 for l in lens):
                    return False
                # 统计校验
                stats = _compute_source_stats(number_grid, r, c)
                if stats is None:
                    return False
                total_len, total_reflects, exits = stats
                if total_len != expected:
                    return False
                # 源反射约束：仅对指定行的源生效
                if source_turn_mode != 'none':
                    rows_set = set(int(x) for x in (source_turn_rows or []))
                    if r in rows_set:
                        if source_turn_mode == 'rows_subset_even':
                            if total_reflects % 2 != 0:
                                return False
                        elif source_turn_mode == 'rows_subset_odd':
                            if total_reflects % 2 != 1:
                                return False
                        else:
                            return False
                # 汇总出界
                for k in exits:
                    exit_total[k] += exits[k]
    # 出界奇偶约束
    if exit_mode != 'none':
        sides_set = set(str(x) for x in (exit_sides or []))
        for s in sides_set:
            cnt = exit_total.get(s, 0)
            if exit_mode == 'sides_even':
                if cnt % 2 != 0:
                    return False
            elif exit_mode == 'sides_odd':
                if cnt % 2 != 1:
                    return False
            else:
                return False
    return True

# -------------------------
# 唯一性校验优化：GF(2) 满秩判定 + 奇偶快速预检查
# -------------------------

def _build_parity_system(size, mirrors_pos,
                         row_orient_mode='none', row_orient_rows=None,
                         col_orient_mode='none', col_orient_cols=None,
                         diag_orient_mode='none'):
    """
    构造 M, b（模2）：
      - 每个镜子 i 对应变量 x_i ∈ {0,1}，1表示'/'，0表示'\\'
      - 约束行：对指定集合内的镜子求和 ≡ 目标奇偶（偶=0，奇=1）
    """
    m = len(mirrors_pos)
    idx_map = {mirrors_pos[i]: i for i in range(m)}
    A = []
    b = []

    if row_orient_rows is None:
        row_orient_rows = []
    if col_orient_cols is None:
        col_orient_cols = []

    # 行约束（斜杠'/'数量）
    if row_orient_mode in ('subset_slash_even', 'subset_slash_odd'):
        target = 0 if row_orient_mode == 'subset_slash_even' else 1
        for r in set(int(x) for x in row_orient_rows):
            row = [0] * m
            have = False
            for i, (rr, cc) in enumerate(mirrors_pos):
                if rr == r:
                    row[i] = 1
                    have = True
            if have:
                A.append(row)
                b.append(target)
            else:
                if target == 1:
                    A.append([0]*m)
                    b.append(1)

    # 列约束（斜杠'/'数量）
    if col_orient_mode in ('subset_slash_even', 'subset_slash_odd'):
        target = 0 if col_orient_mode == 'subset_slash_even' else 1
        for c in set(int(x) for x in col_orient_cols):
            row = [0] * m
            have = False
            for i, (rr, cc) in enumerate(mirrors_pos):
                if cc == c:
                    row[i] = 1
                    have = True
            if have:
                A.append(row)
                b.append(target)
            else:
                if target == 1:
                    A.append([0]*m)
                    b.append(1)

    # 对角线约束（斜杠'/'数量）
    if diag_orient_mode in ('maindiag_even', 'maindiag_odd', 'antidiag_even', 'antidiag_odd'):
        target = 1 if ('odd' in diag_orient_mode) else 0
        row = [0] * m
        have = False
        if 'maindiag' in diag_orient_mode:
            for i, (rr, cc) in enumerate(mirrors_pos):
                if rr == cc:
                    row[i] = 1
                    have = True
        else:
            for i, (rr, cc) in enumerate(mirrors_pos):
                if rr + cc == size - 1:
                    row[i] = 1
                    have = True
        if have:
            A.append(row)
            b.append(target)
        else:
            if target == 1:
                A.append([0]*m)
                b.append(1)

    return A, b

def _gf2_rank_and_consistent(A, b):
    """
    计算模2线性系统的秩与一致性。
    返回 (rank, consistent: bool)。
    """
    if not A:
        return 0, True
    A = [row[:] for row in A]
    b = b[:]
    r = 0
    m = len(A[0])
    n = len(A)
    for c in range(m):
        pivot = -1
        for i in range(r, n):
            if A[i][c] == 1:
                pivot = i
                break
        if pivot == -1:
            continue
        # 交换到当前行
        A[r], A[pivot] = A[pivot], A[r]
        b[r], b[pivot] = b[pivot], b[r]
        # 对其它行消元
        for i in range(n):
            if i != r and A[i][c] == 1:
                for j in range(m):
                    A[i][j] ^= A[r][j]
                b[i] ^= b[r]
        r += 1
        if r == n:
            break
    # 检查不一致：全零行但常数项为1
    for i in range(n):
        if all(v == 0 for v in A[i]) and b[i] == 1:
            return r, False
    return r, True

def _quick_parity_satisfied(board,
                            row_orient_mode='none', row_orient_rows=None,
                            col_orient_mode='none', col_orient_cols=None,
                            diag_orient_mode='none'):
    """
    快速奇偶预检查：只检查行/列/对角线的斜杠'/'奇偶是否满足。
    """
    n = len(board)
    if row_orient_rows is None:
        row_orient_rows = []
    if col_orient_cols is None:
        col_orient_cols = []

    # 行
    if row_orient_mode != 'none':
        rows_set = set(int(x) for x in row_orient_rows)
        row_slash = _count_row_slash(board)
        for r in rows_set:
            cnt = row_slash[r]
            if row_orient_mode == 'subset_slash_even':
                if cnt % 2 != 0:
                    return False
            elif row_orient_mode == 'subset_slash_odd':
                if cnt % 2 != 1:
                    return False
            else:
                return False
    # 列
    if col_orient_mode != 'none':
        cols_set = set(int(x) for x in col_orient_cols)
        col_slash = _count_col_slash(board)
        for c in cols_set:
            cnt = col_slash[c]
            if col_orient_mode == 'subset_slash_even':
                if cnt % 2 != 0:
                    return False
            elif col_orient_mode == 'subset_slash_odd':
                if cnt % 2 != 1:
                    return False
            else:
                return False
    # 对角线
    if diag_orient_mode != 'none':
        main, anti = _count_diag_slash(board)
        if diag_orient_mode == 'maindiag_even':
            if main % 2 != 0:
                return False
        elif diag_orient_mode == 'maindiag_odd':
            if main % 2 != 1:
                return False
        elif diag_orient_mode == 'antidiag_even':
            if anti % 2 != 0:
                return False
        elif diag_orient_mode == 'antidiag_odd':
            if anti % 2 != 1:
                return False
        else:
            return False
    return True

def validate_unique_all(number_grid, row_limit=2, use_col_limit=False, col_limit=0,
                        adjacency_enabled=False, row_parity_mode='none', row_parity_rows=None,
                        cluster_limit=0,
                        row_orient_mode='none', row_orient_rows=None,
                        col_orient_mode='none', col_orient_cols=None,
                        diag_orient_mode='none',
                        source_turn_mode='none', source_turn_rows=None,
                        exit_mode='none', exit_sides=None):
    """
    在 validate_grid_all 基础上增加唯一性校验（优化版）：
      - 若行/列/对角线斜杠奇偶约束构成的GF(2)线性系统满秩且一致（唯一解），则直接判定唯一；
      - 否则保持镜子位置固定，仅枚举所有镜子朝向 2^m 种组合（m 为镜子数，限定 <=12），
        对每个组合先执行快速奇偶预检查，不通过则跳过，减少完整校验次数；
      - 若存在除当前朝向外的任何组合仍满足所有规则与数字提示，则判定非唯一。
    返回 True 表示既有效又唯一；False 表示无效或不唯一。
    """
    if not validate_grid_all(number_grid, row_limit, use_col_limit, col_limit,
                             adjacency_enabled, row_parity_mode, row_parity_rows,
                             cluster_limit,
                             row_orient_mode, row_orient_rows,
                             col_orient_mode, col_orient_cols,
                             diag_orient_mode,
                             source_turn_mode, source_turn_rows,
                             exit_mode, exit_sides):
        return False
    n = len(number_grid)
    mirrors = []
    for r in range(n):
        for c in range(n):
            if _cell_is_mirror(number_grid[r][c]):
                mirrors.append((r, c, number_grid[r][c]))
    m = len(mirrors)
    if m == 0:
        return False
    # 上限避免指数爆炸
    if m > 12:
        return False

    # 若GF(2)线性系统满秩且一致，则奇偶约束已唯一确定镜子朝向，直接判定唯一
    pos = [(r, c) for (r, c, ch) in mirrors]
    A, b = _build_parity_system(n, pos, row_orient_mode, row_orient_rows,
                                col_orient_mode, col_orient_cols,
                                diag_orient_mode)
    rank, ok = _gf2_rank_and_consistent(A, b)
    if ok and rank == m and A:
        return True

    # 遍历其他朝向
    for mask in range(1, 1 << m):  # 排除原解（mask=0）
        cand = deepcopy(number_grid)
        for i, (r, c, ch) in enumerate(mirrors):
            if (mask >> i) & 1:
                cand[r][c] = '/' if ch == '\\' else '\\'
        # 快速奇偶预检查，不满足则直接跳过
        if not _quick_parity_satisfied(cand, row_orient_mode, row_orient_rows,
                                       col_orient_mode, col_orient_cols,
                                       diag_orient_mode):
            continue
        if validate_grid_all(cand, row_limit, use_col_limit, col_limit,
                             adjacency_enabled, row_parity_mode, row_parity_rows,
                             cluster_limit,
                             row_orient_mode, row_orient_rows,
                             col_orient_mode, col_orient_cols,
                             diag_orient_mode,
                             source_turn_mode, source_turn_rows,
                             exit_mode, exit_sides):
            return False
    return True

def _rotate_grid_once(g):
    # 90度顺时针旋转
    n = len(g)
    return [[g[n-1-c][r] for c in range(n)] for r in range(n)]

def _rotate_grid(g, k):
    k = k % 4
    res = deepcopy(g)
    for _ in range(k):
        res = _rotate_grid_once(res)
    return res

def permute_grid(base_grid, seed, rotate_k):
    """
    安全版本：不做行列置换，不做旋转，直接返回拷贝。
    原因：行列置换会破坏网格几何邻接，旋转会将“行上限”约束映射到原列上，导致后续校验失配。
    若需保留对称变换，应将变换纳入生成与校验流程内统一处理。
    """
    return deepcopy(base_grid)

# -------------------------
# 计数选择器（完全参数化，概率下调以提升可行率）
# -------------------------

def choose_src_num(size, seed):
    """
    随机选择源的数量：约在 [max(2, size//3), max(3, size//2+1)] 范围内。
    """
    rng = random.Random(int(seed) ^ 0x51c3a)
    lo = max(2, size // 3)
    hi = max(3, size // 2 + 1)
    if lo > hi:
        lo, hi = hi, lo
    return rng.randint(lo, hi)

def choose_rock_num(size, src_num, seed):
    """
    随机选择陨石数量：不超过网格总格子的约 5%~12%，同时留足空间给镜子与源。
    """
    rng = random.Random(int(seed) ^ 0x7f19b)
    n2 = size * size
    hi = max(1, int(n2 * 0.12))
    lo = max(0, int(n2 * 0.05))
    rock = rng.randint(lo, hi)
    return max(0, rock)

def choose_mirror_num(size, row_limit, src_num, rock_num, seed):
    """
    随机选择镜子数量：不超过每行上限总和 row_limit*size，且限制在 12 以内以便唯一性枚举。
    下限自适应：尽量 ≥3；容量不足时取最大可放。
    """
    rng = random.Random(int(seed) ^ 0x9a2e5)
    max_rows_cap = int(row_limit) * size
    n2 = size * size
    available = n2 - int(src_num) - int(rock_num)
    max_m = max(0, min(available, max_rows_cap, 12))
    # 自适应下限：常规 ≥3，随尺寸微调；保底尽量不为0
    baseline = max(3, size - 4)
    min_m = min(baseline, max_m) if max_m >= 3 else max_m
    if max_m == 0:
        return 0
    if min_m < 3:
        return max_m
    if max_m < min_m:
        return max_m
    return rng.randint(min_m, max_m)

def choose_col_limit(size, seed):
    """
    随机决定是否启用列上限，并给出列上限值。
    返回 (use_col_limit: bool, col_limit: int)。
    """
    rng = random.Random(int(seed) ^ 0x2b137)
    use = rng.random() < 0.25  # 略提高至约25%启用
    if not use:
        return False, 0
    # 列上限在 [1, 3]，并受尺寸影响
    if size <= 6:
        cap = rng.randint(1, 2)
    else:
        cap = rng.randint(2, 3)
    return True, cap

def choose_adjacency(seed):
    """
    随机决定是否启用镜子四邻接禁令。
    """
    rng = random.Random(int(seed) ^ 0x3f8c1)
    return rng.random() < 0.12  # 少量提高至约12%启用

def choose_row_parity(size, seed):
    """
    随机决定行奇偶模式与受约束的行集合。
    模式之一：
      - 'none': 不启用
      - 'subset_even': 指定的少量行镜子计数为偶数
      - 'subset_odd': 指定的少量行镜子计数为奇数
    返回 (mode, rows_list)；当 mode='none' 时 rows_list 可为空列表。
    """
    rng = random.Random(int(seed) ^ 0x61e77)
    p = rng.random()
    if p < 0.85:
        return 'none', []
    elif p < 0.92:
        k = rng.randint(1, min(2, size))
        rows = rng.sample(list(range(size)), k)
        return 'subset_even', rows
    else:
        k = rng.randint(1, min(2, size))
        rows = rng.sample(list(range(size)), k)
        return 'subset_odd', rows

def choose_cluster_limit(size, mirror_num, seed):
    """
    随机选择镜子4连通块大小上限；0 表示不启用。
    根据镜子数量与尺寸给出合理上限，避免不可行。
    """
    rng = random.Random(int(seed) ^ 0x45a63)
    use = rng.random() < 0.12  # 略提高触发概率
    if not use:
        return 0
    cap_lo = 2
    cap_hi = max(2, mirror_num // 2 + 1)
    if cap_lo > cap_hi:
        cap_lo, cap_hi = cap_hi, cap_lo
    return rng.randint(cap_lo, cap_hi)

# -------------------------
# 新增：取向与反射约束的随机选择器（提高触发率 + 兜底保证至少一类取向约束）
# -------------------------

def choose_orient_parity(size, seed):
    """
    随机选择取向奇偶规则包：
      返回 (row_orient_mode, row_orient_rows, col_orient_mode, col_orient_cols, diag_orient_mode)
      模式取值：
        - row_orient_mode: 'none' 或 'subset_slash_even' 或 'subset_slash_odd'
        - col_orient_mode: 同上
        - diag_orient_mode: 'none' 或 'maindiag_even'/'maindiag_odd'/'antidiag_even'/'antidiag_odd'
      提高触发率，并设置兜底：若三者均为'none'，强制开启其中一类。
    """
    rng = random.Random(int(seed) ^ 0x8d2f1)
    # 行
    rp = rng.random()
    if rp < 0.60:
        row_mode = 'none'
        row_rows = []
    else:
        row_mode = 'subset_slash_even' if rng.random() < 0.5 else 'subset_slash_odd'
        k = rng.randint(1, min(2, size))
        row_rows = rng.sample(list(range(size)), k)
    # 列
    cp = rng.random()
    if cp < 0.60:
        col_mode = 'none'
        col_cols = []
    else:
        col_mode = 'subset_slash_even' if rng.random() < 0.5 else 'subset_slash_odd'
        k = rng.randint(1, min(2, size))
        col_cols = rng.sample(list(range(size)), k)
    # 对角线
    dp = rng.random()
    if dp < 0.55:
        diag_mode = 'none'
    else:
        diag_mode = rng.choice(['maindiag_even', 'maindiag_odd', 'antidiag_even', 'antidiag_odd'])

    # 兜底：保证至少一类取向约束被启用
    if row_mode == 'none' and col_mode == 'none' and diag_mode == 'none':
        pick = rng.choice(['row', 'col', 'diag'])
        if pick == 'row':
            row_mode = 'subset_slash_even' if rng.random() < 0.5 else 'subset_slash_odd'
            k = rng.randint(1, min(2, size))
            row_rows = rng.sample(list(range(size)), k)
        elif pick == 'col':
            col_mode = 'subset_slash_even' if rng.random() < 0.5 else 'subset_slash_odd'
            k = rng.randint(1, min(2, size))
            col_cols = rng.sample(list(range(size)), k)
        else:
            diag_mode = rng.choice(['maindiag_even', 'maindiag_odd', 'antidiag_even', 'antidiag_odd'])

    return row_mode, row_rows, col_mode, col_cols, diag_mode

def choose_source_turn_rows(size, seed):
    """
    随机选择源反射次数奇偶约束：
      返回 (source_turn_mode, source_turn_rows)
      模式取值：'none'、'rows_subset_even'、'rows_subset_odd'
      提高触发率至约35%。
    """
    rng = random.Random(int(seed) ^ 0x77b24)
    p = rng.random()
    if p < 0.65:
        return 'none', []
    mode = 'rows_subset_even' if rng.random() < 0.5 else 'rows_subset_odd'
    k = rng.randint(1, min(2, size))
    rows = rng.sample(list(range(size)), k)
    return mode, rows

def choose_exit_parity(size, seed):
    """
    随机选择边界出界奇偶约束：
      返回 (exit_mode, exit_sides)，
      模式取值：'none'、'sides_even'、'sides_odd'；sides 为 ['U','R','D','L'] 子集。
      提高触发率至约45%。
    """
    rng = random.Random(int(seed) ^ 0x6ae91)
    p = rng.random()
    if p < 0.55:
        return 'none', []
    mode = 'sides_even' if rng.random() < 0.5 else 'sides_odd'
    k = 1  # 仅选择1个边，避免过度耦合
    sides = rng.sample(['U','R','D','L'], k)
    return mode, sides

# -------------------------
# 随机布局生成（包含新增规则 + 唯一性筛选）
# -------------------------

def _place_distinct_cells(rng, size, count, forbidden):
    """
    从 size*size 的网格中选择 count 个与 forbidden 不重合的随机坐标。
    """
    candidates = [(r, c) for r in range(size) for c in range(size) if (r, c) not in forbidden]
    if len(candidates) < count:
        return None
    rng.shuffle(candidates)
    return candidates[:count]

def _cluster_size_if_add(mirrors_set, size, add_rc):
    """
    若在 mirrors_set 中加入 add_rc（r,c），返回其所在4连通簇的大小。
    """
    mirrors = set(mirrors_set)
    mirrors.add(add_rc)
    r0, c0 = add_rc
    q = deque([(r0, c0)])
    seen = {add_rc}
    while q:
        r, c = q.popleft()
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and (nr, nc) in mirrors and (nr, nc) not in seen:
                seen.add((nr, nc))
                q.append((nr, nc))
    return len(seen)

def _diag_counts_from_set(size, used_set):
    main = sum(1 for (r, c) in used_set if r == c)
    anti = sum(1 for (r, c) in used_set if r + c == size - 1)
    return main, anti

def _place_mirrors_with_constraints(rng, size, mirror_num, row_limit, occupied,
                                    use_col_limit=False, col_limit=0,
                                    adjacency_enabled=False,
                                    row_parity_mode='none', row_parity_rows=None,
                                    cluster_limit=0,
                                    row_orient_mode='none', row_orient_rows=None,
                                    col_orient_mode='none', col_orient_cols=None,
                                    diag_orient_mode='none'):
    """
    放置镜子位置，满足：
      - 每行镜子数不超过 row_limit
      - 若启用列上限：每列镜子数不超过 col_limit
      - 若启用四邻接禁令：镜子之间不能四邻接
      - 若启用行奇偶：指定行镜子计数满足偶/奇
      - 若启用簇上限：最大4连通镜子块大小不超过 cluster_limit
    并进行斜杠奇偶约束的可行性预检（位置层面）：
      - 若某行/列要求斜杠奇数，则该行/列至少有一个镜子位置
      - 若主/副对角线要求斜杠奇数，则对应对角线上至少有一个镜子位置
    返回坐标列表或 None。
    """
    row_limit = int(row_limit)
    col_limit = int(col_limit)
    if row_parity_rows is None:
        row_parity_rows = []
    if row_orient_rows is None:
        row_orient_rows = []
    if col_orient_cols is None:
        col_orient_cols = []

    parity_rows = set(int(x) for x in row_parity_rows)
    orient_rows = set(int(x) for x in row_orient_rows)
    orient_cols = set(int(x) for x in col_orient_cols)

    free_cells = [(r, c) for r in range(size) for c in range(size) if (r, c) not in occupied]
    rng.shuffle(free_cells)

    # 快速可容量估算
    row_cap_avail = [sum(1 for c in range(size) if (r, c) in free_cells) for r in range(size)]
    total_cap = sum(min(row_limit, row_cap_avail[r]) for r in range(size))
    if mirror_num > total_cap:
        return None

    MAX_TRIES = 15000
    for _ in range(MAX_TRIES):
        mirrors = []
        row_used = [0] * size
        col_used = [0] * size
        used_set = set()
        rng.shuffle(free_cells)
        ok = True
        # 逐个选择镜子位置
        for _k in range(mirror_num):
            candidates = []
            for (r, c) in free_cells:
                if (r, c) in used_set:
                    continue
                # 行列限额
                if row_used[r] >= row_limit:
                    continue
                if use_col_limit and col_used[c] >= col_limit:
                    continue
                # 邻接禁令
                if adjacency_enabled:
                    adj_bad = False
                    for dr, dc in DIRS:
                        nr, nc = r + dr, c + dc
                        if (nr, nc) in used_set:
                            adj_bad = True
                            break
                    if adj_bad:
                        continue
                # 簇上限
                if int(cluster_limit) > 0:
                    new_size = _cluster_size_if_add(used_set, size, (r, c))
                    if new_size > int(cluster_limit):
                        continue
                candidates.append((r, c))
            if not candidates:
                ok = False
                break
            pick = rng.choice(candidates)
            mirrors.append(pick)
            used_set.add(pick)
            rr, cc = pick
            row_used[rr] += 1
            col_used[cc] += 1
        if not ok:
            continue
        # 检查行奇偶约束（镜子总数的奇偶）
        if row_parity_mode != 'none':
            good = True
            for r in parity_rows:
                cnt = row_used[r]
                if row_parity_mode == 'subset_even':
                    if cnt % 2 != 0:
                        good = False
                        break
                elif row_parity_mode == 'subset_odd':
                    if cnt % 2 != 1:
                        good = False
                        break
                else:
                    good = False
                    break
            if not good:
                continue
        # 斜杠奇偶约束的可行性预检：若要求奇数，则集合必须有镜子
        feasible = True
        if row_orient_mode == 'subset_slash_odd':
            for r in orient_rows:
                if row_used[r] == 0:
                    feasible = False
                    break
        if not feasible:
            continue
        if col_orient_mode == 'subset_slash_odd':
            for c in orient_cols:
                if col_used[c] == 0:
                    feasible = False
                    break
        if not feasible:
            continue
        if diag_orient_mode in ('maindiag_odd', 'antidiag_odd'):
            main, anti = _diag_counts_from_set(size, used_set)
            if diag_orient_mode == 'maindiag_odd' and main == 0:
                feasible = False
            if diag_orient_mode == 'antidiag_odd' and anti == 0:
                feasible = False
        if not feasible:
            continue

        # 通过所有定位约束与可行性预检
        return mirrors
    return None

# -------------------------
# 斜杠'/'奇偶线性求解器（GF(2)）
# -------------------------

def _solve_gf2_linear_system(A, b, rng):
    """
    求解 A x = b (mod 2)，返回一个解向量 x（0/1列表），若无解返回 None。
    若存在自由变量，随机赋值以生成一个具体解。
    """
    A = [row[:] for row in A]
    b = b[:]
    r = 0  # 当前处理的行
    m = len(A[0]) if A else 0
    n = len(A)
    pivot_col = [-1] * n

    # 高斯消元（模2）
    for c in range(m):
        pivot = -1
        for i in range(r, n):
            if A[i][c] == 1:
                pivot = i
                break
        if pivot == -1:
            continue
        A[r], A[pivot] = A[pivot], A[r]
        b[r], b[pivot] = b[pivot], b[r]
        pivot_col[r] = c
        for i in range(n):
            if i != r and A[i][c] == 1:
                for j in range(m):
                    A[i][j] ^= A[r][j]
                b[i] ^= b[r]
        r += 1
        if r == n:
            break

    # 检查无解：全零行但 b 非零
    for i in range(n):
        if all(v == 0 for v in A[i]) and b[i] == 1:
            return None

    # 回代：自由变量随机
    x = [0] * m
    free_cols = set(range(m))
    for i in range(n):
        if pivot_col[i] != -1 and pivot_col[i] in free_cols:
            free_cols.remove(pivot_col[i])
    for c in free_cols:
        x[c] = 1 if rng.random() < 0.5 else 0
    for i in range(n-1, -1, -1):
        pc = pivot_col[i]
        if pc == -1:
            continue
        s = 0
        for j in range(pc+1, m):
            if A[i][j] == 1:
                s ^= x[j]
        x[pc] = s ^ b[i]
    return x

def _orient_mirrors_by_parity(size, mirrors_pos, rng,
                              row_orient_mode='none', row_orient_rows=None,
                              col_orient_mode='none', col_orient_cols=None,
                              diag_orient_mode='none',
                              max_try=200):
    """
    基于斜杠奇偶约束为镜子分配朝向：
      - 若无约束，返回随机朝向
      - 若有约束，构造线性方程组并在自由变量空间采样多解
      - 返回一组可行朝向（列表，元素为'/'或'\\'），若不可行返回 None
    """
    m = len(mirrors_pos)
    if m == 0:
        return None
    A, b = _build_parity_system(size, mirrors_pos,
                                row_orient_mode, row_orient_rows,
                                col_orient_mode, col_orient_cols,
                                diag_orient_mode)
    if not A:
        return ['/' if rng.random() < 0.5 else '\\' for _ in range(m)]
    for _ in range(max_try):
        x = _solve_gf2_linear_system(A, b, rng)
        if x is None:
            return None
        ori = ['/' if (xi == 1) else '\\' for xi in x]
        return ori
    return None

def gen_layout(size, src_num, rock_num, mirror_num, row_limit, seed,
               use_col_limit=False, col_limit=0, adjacency_enabled=False,
               row_parity_mode='none', row_parity_rows=None, cluster_limit=0,
               row_orient_mode='none', row_orient_rows=None,
               col_orient_mode='none', col_orient_cols=None,
               diag_orient_mode='none',
               source_turn_mode='none', source_turn_rows=None,
               exit_mode='none', exit_sides=None):
    """
    生成包含 整数源、'#', '/', '\\' 的基础网格（未旋转/置换）。
    逻辑：
      - 随机选点放置源（整数占位）与陨石；
      - 按约束放置镜子位置（含奇偶可行性预检）；
      - 用斜杠奇偶线性求解器构造镜子朝向（满足所有斜杠奇偶约束），并在自由变量空间多次采样；
      - 对每次取向采样：
          * 计算数字
          * 校验所有结构性与反射/出界/取向规则
          * 唯一性校验：固定镜子位置下，镜子朝向唯一
      - 第一组通过校验的采样即作为解返回
    若失败，抛出异常以触发上层重试。
    """
    size = int(size)
    src_num = int(src_num)
    rock_num = int(rock_num)
    mirror_num = int(mirror_num)
    row_limit = int(row_limit)
    rng = random.Random(int(seed) ^ 0x3d49c)
    MAX_LAYOUT_TRIES = 20000
    ORI_SAMPLE_TRIES = 200  # 提高采样次数，增强可行率
    MIN_TOTAL_PER_SOURCE = max(2, size // 5)

    if row_parity_rows is None:
        row_parity_rows = []
    if row_orient_rows is None:
        row_orient_rows = []
    if col_orient_cols is None:
        col_orient_cols = []
    if source_turn_rows is None:
        source_turn_rows = []
    if exit_sides is None:
        exit_sides = []

    for _ in range(MAX_LAYOUT_TRIES):
        # 放源与陨石
        occupied = set()
        src_cells = _place_distinct_cells(rng, size, src_num, occupied)
        if src_cells is None:
            continue
        for p in src_cells:
            occupied.add(p)

        rock_cells = _place_distinct_cells(rng, size, rock_num, occupied)
        if rock_cells is None:
            continue
        for p in rock_cells:
            occupied.add(p)

        # 放镜子位置
        mirrors_pos = _place_mirrors_with_constraints(
            rng, size, mirror_num, row_limit, occupied,
            use_col_limit=use_col_limit, col_limit=col_limit,
            adjacency_enabled=adjacency_enabled,
            row_parity_mode=row_parity_mode, row_parity_rows=row_parity_rows,
            cluster_limit=cluster_limit,
            row_orient_mode=row_orient_mode, row_orient_rows=row_orient_rows,
            col_orient_mode=col_orient_mode, col_orient_cols=col_orient_cols,
            diag_orient_mode=diag_orient_mode
        )
        if mirrors_pos is None:
            continue

        # 基于奇偶线性求解器多次采样朝向，尝试满足反射/出界等复杂约束
        success = False
        for _ori_try in range(ORI_SAMPLE_TRIES):
            ori = _orient_mirrors_by_parity(
                size, mirrors_pos, rng,
                row_orient_mode, row_orient_rows,
                col_orient_mode, col_orient_cols,
                diag_orient_mode,
                max_try=200
            )
            if ori is None:
                # 奇偶系统无解，直接放弃当前镜子位置
                success = False
                break

            # 构造候选板面
            board = [['.' for _ in range(size)] for _ in range(size)]
            for (r, c) in src_cells:
                board[r][c] = 0  # 占位整数，后续填充真实总长度
            for (r, c) in rock_cells:
                board[r][c] = '#'
            for (r, c), ch in zip(mirrors_pos, ori):
                board[r][c] = ch

            # 计算数字并检查
            try:
                ng = fill_numbers_limit(board, row_limit)
            except Exception:
                continue

            # 检查每源的总长度下限与四向单条下限
            good_lengths = True
            for (r, c) in src_cells:
                val = ng[r][c]
                if not isinstance(val, int) or val < MIN_TOTAL_PER_SOURCE:
                    good_lengths = False
                    break
                lens = _compute_source_lengths(ng, r, c)
                if lens is None or any(l < 1 for l in lens):
                    good_lengths = False
                    break
            if not good_lengths:
                continue

            # 综合验证新增约束
            if not validate_grid_all(
                ng, row_limit, use_col_limit, col_limit,
                adjacency_enabled, row_parity_mode, row_parity_rows,
                cluster_limit,
                row_orient_mode, row_orient_rows,
                col_orient_mode, col_orient_cols,
                diag_orient_mode,
                source_turn_mode, source_turn_rows,
                exit_mode, exit_sides
            ):
                continue

            # 唯一性校验：固定镜子位置下的朝向唯一（优化版）
            if not validate_unique_all(
                ng, row_limit, use_col_limit, col_limit,
                adjacency_enabled, row_parity_mode, row_parity_rows,
                cluster_limit,
                row_orient_mode, row_orient_rows,
                col_orient_mode, col_orient_cols,
                diag_orient_mode,
                source_turn_mode, source_turn_rows,
                exit_mode, exit_sides
            ):
                continue

            # 找到一个可行且唯一的布局，返回该布局（含 整数、'#', '/', '\\'）
            return board

        # 本轮镜子位置未找到可行取向，继续外层尝试
        continue

    raise ValueError('Failed to generate a valid unique-ready layout under randomized constraints.')

# -------------------------
# 规则文本渲染（位置类约束 + 取向/反射相关约束，完整一致）
# -------------------------

def _rows_to_1based(rows):
    return ','.join(str(int(x)+1) for x in (rows or []))

def _cols_to_1based(cols):
    return ','.join(str(int(x)+1) for x in (cols or []))

def _sides_to_cn(sides):
    mapping = {'U':'上', 'R':'右', 'D':'下', 'L':'左'}
    return '、'.join(mapping.get(s, s) for s in (sides or []))

def rules_to_string(row_limit, use_col_limit, col_limit, adjacency_enabled,
                    row_parity_mode, row_parity_rows, cluster_limit,
                    row_orient_mode, row_orient_rows,
                    col_orient_mode, col_orient_cols,
                    diag_orient_mode,
                    source_turn_mode, source_turn_rows,
                    exit_mode, exit_sides):
    """
    将所有会影响答案有效性的规则渲染为中文文本（单行片段，可嵌入题面）。
    包含：位置类约束 + 取向/反射相关约束。
    """
    parts = []
    # 位置类约束
    parts.append(f'(1) 每行镜子数量不超过 {int(row_limit)}')
    if use_col_limit:
        parts.append(f'(2) 每列镜子数量不超过 {int(col_limit)}')
    else:
        parts.append('(2) 列方向的镜子数量不设上限')
    if adjacency_enabled:
        parts.append('(3) 镜子之间不得四邻接（上/下/左/右）')
    else:
        parts.append('(3) 镜子之间的四邻接不设限制')
    if row_parity_mode == 'subset_even':
        parts.append(f'(4) 第[{_rows_to_1based(row_parity_rows)}]行的镜子总数为偶数')
    elif row_parity_mode == 'subset_odd':
        parts.append(f'(4) 第[{_rows_to_1based(row_parity_rows)}]行的镜子总数为奇数')
    else:
        parts.append('(4) 行的镜子总数奇偶不设限制')
    if int(cluster_limit) > 0:
        parts.append(f'(5) 镜子4连通块的最大大小不超过 {int(cluster_limit)}')
    else:
        parts.append('(5) 镜子4连通块大小不设上限')

    # 取向/反射相关约束（斜杠'/'奇偶）
    if row_orient_mode == 'subset_slash_even':
        parts.append(f'(6) 第[{_rows_to_1based(row_orient_rows)}]行的斜杠\'/\'镜子总数为偶数')
    elif row_orient_mode == 'subset_slash_odd':
        parts.append(f'(6) 第[{_rows_to_1based(row_orient_rows)}]行的斜杠\'/\'镜子总数为奇数')
    else:
        parts.append('(6) 行方向的斜杠\'/\'数量不设奇偶限制')
    if col_orient_mode == 'subset_slash_even':
        parts.append(f'(7) 第[{_cols_to_1based(col_orient_cols)}]列的斜杠\'/\'镜子总数为偶数')
    elif col_orient_mode == 'subset_slash_odd':
        parts.append(f'(7) 第[{_cols_to_1based(col_orient_cols)}]列的斜杠\'/\'镜子总数为奇数')
    else:
        parts.append('(7) 列方向的斜杠\'/\'数量不设奇偶限制')
    if diag_orient_mode == 'maindiag_even':
        parts.append('(8) 主对角线上的斜杠\'/\'镜子总数为偶数')
    elif diag_orient_mode == 'maindiag_odd':
        parts.append('(8) 主对角线上的斜杠\'/\'镜子总数为奇数')
    elif diag_orient_mode == 'antidiag_even':
        parts.append('(8) 副对角线上的斜杠\'/\'镜子总数为偶数')
    elif diag_orient_mode == 'antidiag_odd':
        parts.append('(8) 副对角线上的斜杠\'/\'镜子总数为奇数')
    else:
        parts.append('(8) 对角线的斜杠\'/\'数量不设奇偶限制')

    # 源反射奇偶
    if source_turn_mode == 'rows_subset_even':
        parts.append(f'(9) 位于第[{_rows_to_1based(source_turn_rows)}]行的每个源，其四条正交射线的总反射次数为偶数')
    elif source_turn_mode == 'rows_subset_odd':
        parts.append(f'(9) 位于第[{_rows_to_1based(source_turn_rows)}]行的每个源，其四条正交射线的总反射次数为奇数')
    else:
        parts.append('(9) 源的总反射次数不设奇偶限制')

    # 出界奇偶（方位说明）
    if exit_mode == 'sides_even':
        parts.append(f'(10) 从[{_sides_to_cn(exit_sides)}]边界出界的射线总数为偶数（U=上, R=右, D=下, L=左）')
    elif exit_mode == 'sides_odd':
        parts.append(f'(10) 从[{_sides_to_cn(exit_sides)}]边界出界的射线总数为奇数（U=上, R=右, D=下, L=左）')
    else:
        parts.append('(10) 射线出界边的总数不设奇偶限制（U=上, R=右, D=下, L=左）')
    return '；'.join(parts)