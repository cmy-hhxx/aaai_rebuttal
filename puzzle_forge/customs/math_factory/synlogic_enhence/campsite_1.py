# -*- coding: utf-8 -*-
# campsite_5.py
# 逆向生成器（随机规则集 + 掩码 + 区域配额 + 锚定方向 + 唯一解验证 + 复杂度保障）

from typing import List, Tuple, Dict, Any, Optional
import random, time

# 基础邻域与计数工具
def _neighbors_4(i: int, j: int, R: int, C: int):
    for di, dj in ((-1,0),(1,0),(0,-1),(0,1)):
        ni, nj = i + di, j + dj
        if 0 <= ni < R and 0 <= nj < C:
            yield (ni, nj)

def _neighbors_8(i: int, j: int, R: int, C: int):
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            ni, nj = i + di, j + dj
            if 0 <= ni < R and 0 <= nj < C:
                yield (ni, nj)

def _chebyshev_distance(p1: Tuple[int,int], p2: Tuple[int,int]) -> int:
    return max(abs(p1[0]-p2[0]), abs(p1[1]-p2[1]))

def _manhattan_distance(p1: Tuple[int,int], p2: Tuple[int,int]) -> int:
    return abs(p1[0]-p2[0]) + abs(p1[1]-p2[1])

def _count_by_row(grid: List[List[str]], target: str) -> List[int]:
    return [sum(1 for ch in row if ch == target) for row in grid]

def _count_by_col(grid: List[List[str]], target: str) -> List[int]:
    if not grid:
        return []
    R, C = len(grid), len(grid[0])
    res = []
    for j in range(C):
        c = 0
        for i in range(R):
            if grid[i][j] == target:
                c += 1
        res.append(c)
    return res

# 基础放置工具
def _place_Z(R: int, C: int, z_count: int) -> List[List[str]]:
    grid = [['X' for _ in range(C)] for _ in range(R)]
    cells = [(i, j) for i in range(R) for j in range(C)]
    random.shuffle(cells)
    for k in range(min(z_count, len(cells))):
        i, j = cells[k]
        grid[i][j] = 'Z'
    return grid

def _select_S_positions(grid: List[List[str]], s_num: int) -> List[Tuple[int,int]]:
    R, C = len(grid), len(grid[0])
    cand = []
    for i in range(R):
        for j in range(C):
            if grid[i][j] != 'X':
                continue
            if any(grid[ni][nj] == 'X' for (ni, nj) in _neighbors_4(i, j, R, C)):
                cand.append((i, j))
    if len(cand) < s_num:
        return []
    random.shuffle(cand)
    return cand[:s_num]

# 掩码与锚定约束
def _mask_pred(i: int, j: int, R: int, C: int, mask_type: str, parity_val: int, row_parity_val: int, col_parity_val: int) -> bool:
    if mask_type == 'none':
        return True
    if mask_type == 'checker':
        return ((i + j) % 2) == parity_val
    if mask_type == 'row_parity':
        return (i % 2) == row_parity_val
    if mask_type == 'col_parity':
        return (j % 2) == col_parity_val
    return True

def _build_anchor_rules(S_list: List[Tuple[int,int]], R: int, C: int, pct: int) -> Dict[Tuple[int,int], Tuple[int,int]]:
    dirs = [(-1,0),(1,0),(0,-1),(0,1)]
    k = max(1, int(len(S_list) * pct / 100))
    picked = random.sample(S_list, min(k, len(S_list)))
    anchor: Dict[Tuple[int,int], Tuple[int,int]] = {}
    for (si, sj) in picked:
        random.shuffle(dirs)
        for di, dj in dirs:
            ni, nj = si + di, sj + dj
            if 0 <= ni < R and 0 <= nj < C:
                anchor[(si, sj)] = (di, dj)
                break
    return anchor

# 接触与距离约束
def _e_contact_conflict(pos: Tuple[int,int], E_list: List[Tuple[int,int]], mode: str) -> bool:
    for e in E_list:
        if mode == 'no_touch_8':
            if _chebyshev_distance(pos, e) <= 1:
                return True
        elif mode == 'no_touch_4':
            if _manhattan_distance(pos, e) <= 1:
                return True
    return False

def _v_contact_conflict(pos: Tuple[int,int], V_list: List[Tuple[int,int]], mode: str, v_mdist: int) -> bool:
    for v in V_list:
        if mode == 'no_touch_8' and _chebyshev_distance(pos, v) <= 1:
            return True
        if mode == 'no_touch_4' and _manhattan_distance(pos, v) <= 1:
            return True
        if _manhattan_distance(pos, v) < v_mdist:
            return True
    return False

# 候选集合（考虑掩码）
def _candidate_E_cells(base: List[List[str]], S_list: List[Tuple[int,int]], e_adj_type: str,
                       mask_on: bool, mask_type: str, parity_val: int, row_parity_val: int, col_parity_val: int) -> List[Tuple[int,int]]:
    R, C = len(base), len(base[0])
    S_set = set(S_list)
    cands = []
    for i in range(R):
        for j in range(C):
            if base[i][j] != 'X':
                continue
            cnt = sum(1 for (ni,nj) in _neighbors_4(i,j,R,C) if (ni,nj) in S_set)
            if e_adj_type == 'ge1' and cnt < 1:
                continue
            if e_adj_type == 'eq1' and cnt != 1:
                continue
            if mask_on and not _mask_pred(i, j, R, C, mask_type, parity_val, row_parity_val, col_parity_val):
                continue
            cands.append((i, j))
    random.shuffle(cands)
    return cands

def _candidate_V_cells(base: List[List[str]], S_list: List[Tuple[int,int]], E_list: List[Tuple[int,int]], v_s_adj_rule: str,
                       mask_on: bool, mask_type: str, parity_val: int, row_parity_val: int, col_parity_val: int) -> List[Tuple[int,int]]:
    R, C = len(base), len(base[0])
    S_set = set(S_list)
    E_set = set(E_list)
    cands = []
    for i in range(R):
        for j in range(C):
            if base[i][j] != 'X':
                continue
            if (i, j) in E_set or (i, j) in S_set:
                continue
            if v_s_adj_rule == 'no_4':
                if any((ni, nj) in S_set for (ni, nj) in _neighbors_4(i, j, R, C)):
                    continue
            if mask_on and not _mask_pred(i, j, R, C, mask_type, parity_val, row_parity_val, col_parity_val):
                continue
            cands.append((i, j))
    random.shuffle(cands)
    return cands

# 约束数组构造与区域配额
def _apply_mode_counts(counts: List[int], mode: str, slack_low: int, slack_high: int) -> List[int]:
    arr = []
    lo, hi = min(slack_low, slack_high), max(slack_low, slack_high)
    for val in counts:
        slack = random.randint(lo, hi)
        if mode == 'eq':
            arr.append(val)
        elif mode == 'ge':
            arr.append(max(0, val - slack))
        elif mode == 'le':
            arr.append(val + slack)
        else:
            arr.append(val)
    return arr

def _region_quota_desc_and_values(final_grid: List[List[str]], modeE: str, modeV: str, kind: str,
                                  slack_low: int, slack_high: int) -> Tuple[str, Dict[str, Any], str, str]:
    R, C = len(final_grid), len(final_grid[0])
    if kind == 'none':
        return '区域配额未设置', {}, modeE, modeV
    E_left = E_right = E_top = E_bottom = 0
    V_left = V_right = V_top = V_bottom = 0
    for i in range(R):
        for j in range(C):
            ch = final_grid[i][j]
            if j < C // 2:
                if ch == 'E': E_left += 1
                if ch == 'V': V_left += 1
            else:
                if ch == 'E': E_right += 1
                if ch == 'V': V_right += 1
            if i < R // 2:
                if ch == 'E': E_top += 1
                if ch == 'V': V_top += 1
            else:
                if ch == 'E': E_bottom += 1
                if ch == 'V': V_bottom += 1
    values: Dict[str, Any] = {}
    lo, hi = min(slack_low, slack_high), max(slack_low, slack_high)
    def apply_pair(valL: int, valR: int, mode: str, prefix: str):
        slackL = random.randint(lo, hi)
        slackR = random.randint(lo, hi)
        if mode == 'eq':
            values[f'{prefix}_L'] = valL
            values[f'{prefix}_R'] = valR
        elif mode == 'ge':
            values[f'{prefix}_L'] = max(0, valL - slackL)
            values[f'{prefix}_R'] = max(0, valR - slackR)
        elif mode == 'le':
            values[f'{prefix}_L'] = valL + slackL
            values[f'{prefix}_R'] = valR + slackR
        else:
            values[f'{prefix}_L'] = valL
            values[f'{prefix}_R'] = valR
    if kind == 'vertical_half':
        apply_pair(E_left, E_right, modeE, 'E_half')
        apply_pair(V_left, V_right, modeV, 'V_half')
        desc = '区域配额为左右半区：E/V 在左/右半区的数量需满足相应模式（eq/ge/le）。'
        return desc, values, modeE, modeV
    else:
        apply_pair(E_top, E_bottom, modeE, 'E_half_row')
        apply_pair(V_top, V_bottom, modeV, 'V_half_row')
        desc = '区域配额为上下半区：E/V 在上/下半区的数量需满足相应模式（eq/ge/le）。'
        return desc, values, modeE, modeV

def _build_final_grid(base: List[List[str]], E_list: List[Tuple[int,int]], V_list: List[Tuple[int,int]]) -> List[List[str]]:
    R, C = len(base), len(base[0])
    g = [[ch for ch in row] for row in base]
    for (ei, ej) in E_list:
        g[ei][ej] = 'E'
    for (vi, vj) in V_list:
        if g[vi][vj] == 'X':
            g[vi][vj] = 'V'
    return g

def _check_region_quota(grid: List[List[str]], kind: str, quota_values: Dict[str, Any], modeE: str, modeV: str) -> bool:
    R, C = len(grid), len(grid[0])
    if not quota_values or kind == 'none':
        return True
    def cmp(val: int, target: int, mode: str) -> bool:
        if mode == 'eq':
            return val == target
        if mode == 'ge':
            return val >= target
        if mode == 'le':
            return val <= target
        return True
    if kind == 'vertical_half':
        E_left = E_right = V_left = V_right = 0
        for i in range(R):
            for j in range(C):
                ch = grid[i][j]
                if j < C // 2:
                    if ch == 'E': E_left += 1
                    if ch == 'V': V_left += 1
                else:
                    if ch == 'E': E_right += 1
                    if ch == 'V': V_right += 1
        return (cmp(E_left, quota_values['E_half_L'], modeE) and
                cmp(E_right, quota_values['E_half_R'], modeE) and
                cmp(V_left, quota_values['V_half_L'], modeV) and
                cmp(V_right, quota_values['V_half_R'], modeV))
    else:
        E_top = E_bottom = V_top = V_bottom = 0
        for i in range(R):
            for j in range(C):
                ch = grid[i][j]
                if i < R // 2:
                    if ch == 'E': E_top += 1
                    if ch == 'V': V_top += 1
                else:
                    if ch == 'E': E_bottom += 1
                    if ch == 'V': V_bottom += 1
        return (cmp(E_top, quota_values['E_half_row_L'], modeE) and
                cmp(E_bottom, quota_values['E_half_row_R'], modeE) and
                cmp(V_top, quota_values['V_half_row_L'], modeV) and
                cmp(V_bottom, quota_values['V_half_row_R'], modeV))

# 唯一解枚举（E）
def _enumerate_E_unique(base: List[List[str]], S_list: List[Tuple[int,int]], e_target: int,
                        e_adj_type: str, e_contact_mode: str,
                        mask_on: bool, mask_type: str, parity_val: int, row_parity_val: int, col_parity_val: int,
                        row_mode_E: str, row_arr_E: List[int],
                        col_mode_E: str, col_arr_E: List[int],
                        region_kind: str, quota_values: Dict[str, Any], region_mode_E: str,
                        anchors: Dict[Tuple[int,int], Tuple[int,int]],
                        time_deadline: float) -> Tuple[Optional[List[Tuple[int,int]]], int]:
    R, C = len(base), len(base[0])
    cand = _candidate_E_cells(base, S_list, e_adj_type, mask_on, mask_type, parity_val, row_parity_val, col_parity_val)
    row_cnt = [0]*R
    col_cnt = [0]*C
    E_list: List[Tuple[int,int]] = []
    solutions = 0
    best_sol: Optional[List[Tuple[int,int]]] = None

    def priority(cell):
        i, j = cell
        score = 0
        if row_mode_E == 'eq':
            score += (row_arr_E[i] - row_cnt[i])
        if col_mode_E == 'eq':
            score += (col_arr_E[j] - col_cnt[j])
        return score
    cand.sort(key=priority)

    def ok_row(i):
        if row_mode_E == 'le':
            return row_cnt[i] <= row_arr_E[i]
        return True

    def ok_col(j):
        if col_mode_E == 'le':
            return col_cnt[j] <= col_arr_E[j]
        return True

    def feasible():
        if time.monotonic() > time_deadline:
            return False
        if row_mode_E == 'eq':
            for i in range(R):
                if row_cnt[i] > row_arr_E[i]:
                    return False
        if col_mode_E == 'eq':
            for j in range(C):
                if col_cnt[j] > col_arr_E[j]:
                    return False
        return True

    def satisfy_anchors(e_list: List[Tuple[int,int]]) -> bool:
        for (si, sj), (di, dj) in anchors.items():
            ni, nj = si + di, sj + dj
            if (ni, nj) not in e_list:
                return False
        return True

    def dfs(idx: int):
        nonlocal solutions, best_sol
        if time.monotonic() > time_deadline or solutions >= 2:
            return
        if len(E_list) == e_target:
            fg = _build_final_grid(base, E_list, [])
            if not _check_region_quota(fg, region_kind, quota_values, region_mode_E, region_mode_E):
                return
            if row_mode_E == 'eq' and any(row_cnt[i] != row_arr_E[i] for i in range(R)):
                return
            if row_mode_E == 'ge' and any(row_cnt[i] < row_arr_E[i] for i in range(R)):
                return
            if col_mode_E == 'eq' and any(col_cnt[j] != col_arr_E[j] for j in range(C)):
                return
            if col_mode_E == 'ge' and any(col_cnt[j] < col_arr_E[j] for j in range(C)):
                return
            if not satisfy_anchors(E_list):
                return
            solutions += 1
            if solutions == 1:
                best_sol = list(E_list)
            return
        if idx >= len(cand):
            return
        i, j = cand[idx]
        if not _e_contact_conflict((i, j), E_list, e_contact_mode):
            row_cnt[i] += 1
            col_cnt[j] += 1
            if ok_row(i) and ok_col(j) and feasible():
                E_list.append((i, j))
                dfs(idx + 1)
                E_list.pop()
            row_cnt[i] -= 1
            col_cnt[j] -= 1
        dfs(idx + 1)

    dfs(0)
    return best_sol, solutions

# 唯一解枚举（V）
def _enumerate_V_unique(base: List[List[str]], S_list: List[Tuple[int,int]], E_list: List[Tuple[int,int]],
                        v_target_min: int, v_target_max: int,
                        v_contact_mode: str, v_s_adj_rule: str, v_mdist: int,
                        mask_on: bool, mask_type: str, parity_val: int, row_parity_val: int, col_parity_val: int,
                        row_mode_V: str, row_arr_V: List[int],
                        col_mode_V: str, col_arr_V: List[int],
                        region_kind: str, quota_values: Dict[str, Any], region_mode_V: str,
                        time_deadline: float) -> Tuple[Optional[List[Tuple[int,int]]], int]:
    R, C = len(base), len(base[0])
    cand = _candidate_V_cells(base, S_list, E_list, v_s_adj_rule, mask_on, mask_type, parity_val, row_parity_val, col_parity_val)
    row_cnt = [0]*R
    col_cnt = [0]*C
    V_list: List[Tuple[int,int]] = []
    solutions = 0
    best_sol: Optional[List[Tuple[int,int]]] = None

    def priority(cell):
        i, j = cell
        score = 0
        if row_mode_V == 'eq':
            score += (row_arr_V[i] - row_cnt[i])
        if col_mode_V == 'eq':
            score += (col_arr_V[j] - col_cnt[j])
        return score
    cand.sort(key=priority)

    def ok_row(i):
        if row_mode_V == 'le':
            return row_cnt[i] <= row_arr_V[i]
        return True

    def ok_col(j):
        if col_mode_V == 'le':
            return col_cnt[j] <= col_arr_V[j]
        return True

    def feasible():
        if time.monotonic() > time_deadline:
            return False
        if row_mode_V == 'eq':
            for i in range(R):
                if row_cnt[i] > row_arr_V[i]:
                    return False
        if col_mode_V == 'eq':
            for j in range(C):
                if col_cnt[j] > col_arr_V[j]:
                    return False
        return True

    def dfs(idx: int):
        nonlocal solutions, best_sol
        if time.monotonic() > time_deadline or solutions >= 2:
            return
        if len(V_list) > v_target_max:
            return
        if idx >= len(cand):
            # 完成度与区域配额
            if len(V_list) < v_target_min or len(V_list) > v_target_max:
                return
            fg = _build_final_grid(base, E_list, V_list)
            if not _check_region_quota(fg, region_kind, quota_values, region_mode_V, region_mode_V):
                return
            if row_mode_V == 'eq' and any(row_cnt[i] != row_arr_V[i] for i in range(R)):
                return
            if row_mode_V == 'ge' and any(row_cnt[i] < row_arr_V[i] for i in range(R)):
                return
            if col_mode_V == 'eq' and any(col_cnt[j] != col_arr_V[j] for j in range(C)):
                return
            if col_mode_V == 'ge' and any(col_cnt[j] < col_arr_V[j] for j in range(C)):
                return
            solutions += 1
            if solutions == 1:
                best_sol = list(V_list)
            return
        i, j = cand[idx]
        if not _v_contact_conflict((i, j), V_list, v_contact_mode, v_mdist):
            row_cnt[i] += 1
            col_cnt[j] += 1
            if ok_row(i) and ok_col(j) and feasible():
                V_list.append((i, j))
                dfs(idx + 1)
                V_list.pop()
            row_cnt[i] -= 1
            col_cnt[j] -= 1
        dfs(idx + 1)

    dfs(0)
    return best_sol, solutions

# 主生成函数
def function_1(R_low: int, R_high: int, C_low: int, C_high: int,
               z_pct_low: int, z_pct_high: int, s_pct_low: int, s_pct_high: int,
               v_pct_low: int, v_pct_high: int, max_retry: int,
               e_adj_type_pool, e_contact_pool, v_contact_pool, v_s_adj_pool,
               row_mode_pool, col_mode_pool, e_equals_s_flag_pool,
               mask_type_pool, mask_on_E_pool, mask_on_V_pool,
               anchor_pct_low: int, anchor_pct_high: int,
               region_quota_pool, v_mdist_low: int, v_mdist_high: int,
               slack_low: int, slack_high: int,
               search_time_low: int, search_time_high: int,
               prefer_eq_low: int, prefer_eq_high: int) -> Dict[str, Any]:
    if R_low > R_high: R_low, R_high = R_high, R_low
    if C_low > C_high: C_low, C_high = C_high, C_low
    z_low, z_high = min(z_pct_low, z_pct_high), max(z_pct_low, z_pct_high)
    s_low, s_high = min(s_pct_low, s_pct_high), max(s_pct_low, s_pct_high)
    v_low, v_high = min(v_pct_low, v_pct_high), max(v_pct_low, v_pct_high)
    v_m_low, v_m_high = min(v_mdist_low, v_mdist_high), max(v_mdist_low, v_mdist_high)
    slack_low, slack_high = min(slack_low, slack_high), max(slack_low, slack_high)
    anchor_low, anchor_high = min(anchor_pct_low, anchor_pct_high), max(anchor_pct_low, anchor_pct_high)
    prefer_eq_low, prefer_eq_high = min(prefer_eq_low, prefer_eq_high), max(prefer_eq_low, prefer_eq_high)
    max_retry = max(120, int(max_retry))

    for _ in range(max_retry):
        prefer_eq_prob = random.randint(prefer_eq_low, prefer_eq_high) / 100.0
        def pick_mode(pool):
            return 'eq' if random.random() < prefer_eq_prob else random.choice(list(pool))

        e_adj_type = random.choice(list(e_adj_type_pool))
        e_contact_mode = random.choice(list(e_contact_pool))
        v_contact_mode = random.choice(list(v_contact_pool))
        v_s_adj_rule = random.choice(list(v_s_adj_pool))

        row_mode_E = pick_mode(row_mode_pool)
        row_mode_V = pick_mode(row_mode_pool)
        col_mode_E = pick_mode(col_mode_pool)
        col_mode_V = pick_mode(col_mode_pool)
        # 防止四个全 eq
        if all(m == 'eq' for m in [row_mode_E, row_mode_V, col_mode_E, col_mode_V]):
            idx = random.randint(0, 3)
            modes = ['ge', 'le']
            if idx == 0: row_mode_E = random.choice(modes)
            elif idx == 1: row_mode_V = random.choice(modes)
            elif idx == 2: col_mode_E = random.choice(modes)
            else: col_mode_V = random.choice(modes)

        e_equals_s_flag = random.choice(list(e_equals_s_flag_pool))
        v_mdist = random.randint(v_m_low, v_m_high)

        mask_type = random.choice(list(mask_type_pool))
        mask_on_E = random.choice(list(mask_on_E_pool))
        mask_on_V = random.choice(list(mask_on_V_pool))
        parity_val = random.randint(0, 1)
        row_parity_val = random.randint(0, 1)
        col_parity_val = random.randint(0, 1)

        anchor_pct = random.randint(anchor_low, anchor_high)
        region_kind = random.choice(list(region_quota_pool))
        search_time_limit = random.randint(search_time_low, search_time_high)
        deadline = time.monotonic() + search_time_limit

        R = random.randint(R_low, R_high)
        C = random.randint(C_low, C_high)
        N = R * C

        z_frac = random.randint(z_low, z_high) / 100.0
        s_frac = random.randint(s_low, s_high) / 100.0
        v_frac = random.randint(v_low, v_high) / 100.0

        z_count = min(int(N * z_frac), max(0, N - 10))
        base = _place_Z(R, C, z_count)
        remain_X = sum(1 for i in range(R) for j in range(C) if base[i][j] == 'X')
        if remain_X < 10:
            continue

        s_cap = max(4, int(N * s_frac))
        s_max = min(remain_X // 2, s_cap)
        s_min = min(max(4, int(N * 0.08)), s_max)
        if s_max < s_min:
            continue
        s_num = random.randint(s_min, s_max)
        S_list = _select_S_positions(base, s_num)
        if len(S_list) != s_num:
            continue
        for (si, sj) in S_list:
            base[si][sj] = 'S'

        anchors = _build_anchor_rules(S_list, R, C, anchor_pct)

        E_cand = _candidate_E_cells(base, S_list, e_adj_type, mask_on_E, mask_type, parity_val, row_parity_val, col_parity_val)
        if not E_cand:
            continue

        if e_equals_s_flag:
            e_target = len(S_list)
        else:
            low = max(3, int(len(S_list) * 0.6))
            high = min(len(S_list) + 4, int(len(S_list) * 1.3))
            if low > high: low, high = high, low
            e_target = random.randint(low, high)

        # 贪心初解（用于反推约束）
        E_list: List[Tuple[int,int]] = []
        for (i, j) in E_cand:
            if len(E_list) >= e_target:
                break
            if _e_contact_conflict((i, j), E_list, e_contact_mode):
                continue
            E_list.append((i, j))
        if len(E_list) != e_target:
            continue

        v_cap = max(2, int(N * v_frac))  # 保证至少有 2 个 V
        V_cand = _candidate_V_cells(base, S_list, E_list, v_s_adj_rule, mask_on_V, mask_type, parity_val, row_parity_val, col_parity_val)
        V_list: List[Tuple[int,int]] = []
        for (i, j) in V_cand:
            if len(V_list) >= v_cap:
                break
            if _v_contact_conflict((i, j), V_list, v_contact_mode, v_mdist):
                continue
            V_list.append((i, j))

        final_grid = _build_final_grid(base, E_list, V_list)

        # 行列约束（模式化）
        row_constraints_E = _apply_mode_counts(_count_by_row(final_grid, 'E'), row_mode_E, slack_low, slack_high)
        row_constraints_V = _apply_mode_counts(_count_by_row(final_grid, 'V'), row_mode_V, slack_low, slack_high)
        col_constraints_E = _apply_mode_counts(_count_by_col(final_grid, 'E'), col_mode_E, slack_low, slack_high)
        col_constraints_V = _apply_mode_counts(_count_by_col(final_grid, 'V'), col_mode_V, slack_low, slack_high)

        # 复杂度保障：至少一个约束数组含正数
        if sum(row_constraints_E) == 0 and sum(col_constraints_E) == 0:
            continue
        if sum(row_constraints_V) == 0 and sum(col_constraints_V) == 0:
            continue

        # 区域配额
        rq_desc, rq_values, rq_modeE, rq_modeV = _region_quota_desc_and_values(final_grid, row_mode_E, row_mode_V, region_kind, slack_low, slack_high)

        # 唯一性验证：E
        best_E, cnt_E = _enumerate_E_unique(
            base, S_list, e_target, e_adj_type, e_contact_mode,
            mask_on_E, mask_type, parity_val, row_parity_val, col_parity_val,
            row_mode_E, row_constraints_E,
            col_mode_E, col_constraints_E,
            region_kind, rq_values, rq_modeE,
            anchors,
            deadline
        )
        if cnt_E != 1 or best_E is None:
            continue

        # 唯一性验证：V
        # 计算 V 范围
        total_rowV = sum(row_constraints_V)
        total_colV = sum(col_constraints_V)
        v_min, v_max = 0, len(V_cand)
        if row_mode_V == 'eq':
            v_min = v_max = total_rowV
        elif row_mode_V == 'ge':
            v_min = max(v_min, total_rowV)
        elif row_mode_V == 'le':
            v_max = min(v_max, total_rowV)
        if col_mode_V == 'eq':
            v_min = max(v_min, total_colV)
            v_max = min(v_max, total_colV)
        elif col_mode_V == 'ge':
            v_min = max(v_min, total_colV)
        elif col_mode_V == 'le':
            v_max = min(v_max, total_colV)
        if v_min < 2:  # 至少 2 个 V
            v_min = 2
        if v_min > v_max:
            continue

        best_V, cnt_V = _enumerate_V_unique(
            base, S_list, best_E,
            v_min, v_max,
            v_contact_mode, v_s_adj_rule, v_mdist,
            mask_on_V, mask_type, parity_val, row_parity_val, col_parity_val,
            row_mode_V, row_constraints_V,
            col_mode_V, col_constraints_V,
            region_kind, rq_values, rq_modeV,
            deadline
        )
        if cnt_V != 1 or best_V is None:
            continue

        # 基础输入网格（仅 S/Z/X）
        base_input = [['X' for _ in range(C)] for _ in range(R)]
        for i in range(R):
            for j in range(C):
                if base[i][j] == 'Z':
                    base_input[i][j] = 'Z'
        for (si, sj) in S_list:
            base_input[si][sj] = 'S'

        # 文本摘要
        e_adj_text = "扶梯 E 与站点 S 至少一个正交邻接" if e_adj_type == 'ge1' else "扶梯 E 必须恰好与一个站点 S 正交邻接"
        e_contact_text = "扶梯之间不得 8 邻接（含对角）" if e_contact_mode == 'no_touch_8' else "扶梯之间不得 4 邻接（不含对角）"
        v_contact_text = "通风口之间不得 8 邻接（含对角）" if v_contact_mode == 'no_touch_8' else "通风口之间不得 4 邻接（不含对角）"
        v_s_text = "通风口不得与站点 S 正交相邻" if v_s_adj_rule == 'no_4' else "通风口与站点 S 的正交邻接不作限制"
        e_total_text = "扶梯总数必须等于站点总数" if e_equals_s_flag else "扶梯总数不固定，但每个扶梯必须满足邻接条件"
        v_mdist_text = f"任意两座通风口的曼哈顿距离至少为 {v_mdist}"
        rules_summary = f"[{e_adj_text}; {e_contact_text}; {v_contact_text}; {v_s_text}; {v_mdist_text}; {e_total_text}]"

        def mask_desc_for(which: str, on: bool):
            if not on:
                return f"{which} 未启用掩码约束"
            if mask_type == 'checker':
                return f"{which} 需放在棋盘格的 {('深色' if parity_val==1 else '浅色')}格上（按 (行+列) 奇偶定义）"
            if mask_type == 'row_parity':
                return f"{which} 需放在 {'奇数' if row_parity_val==1 else '偶数'}行"
            if mask_type == 'col_parity':
                return f"{which} 需放在 {'奇数' if col_parity_val==1 else '偶数'}列"
            return f"{which} 未启用掩码约束"
        mask_desc = f"{mask_desc_for('E', mask_on_E)}；{mask_desc_for('V', mask_on_V)}"

        anchor_desc = f"存在 {len(anchors)} 个锚定方向约束：部分站点 S 的扶梯必须在指定方向的邻位" if anchors else "未设置锚定方向约束"
        constraints_summary = f"行约束模式：E={row_mode_E}, V={row_mode_V}; 列约束模式：E={col_mode_E}, V={col_mode_V}。eq 表示等于，ge 表示至少，le 表示至多。"

        final_grid_verified = _build_final_grid(base, best_E, best_V)
        return {
            'R': R,
            'C': C,
            'grid': base_input,
            'final_grid': final_grid_verified,
            'row_constraints_E': row_constraints_E,
            'row_constraints_V': row_constraints_V,
            'col_constraints_E': col_constraints_E,
            'col_constraints_V': col_constraints_V,
            'region_quota_desc': rq_desc,
            'mask_desc': mask_desc,
            'anchor_desc': anchor_desc,
            'rules_summary': rules_summary,
            'constraints_summary': constraints_summary,
            'S_count': len(S_list),
            'E_count': len(best_E),
            'V_count': len(best_V),
        }

    # 保底微型实例（保证闭环）
    R, C = 6, 5
    base = [['X' for _ in range(C)] for _ in range(R)]
    S_list = [(1,1), (1,3), (3,2), (4,4)]
    for (si,sj) in S_list:
        base[si][sj] = 'S'
    E_list = [(1,0),(1,2),(3,1),(4,3)]
    V_list = [(0,4),(5,0)]
    final_grid = _build_final_grid(base, E_list, V_list)
    return {
        'R': R,
        'C': C,
        'grid': base,
        'final_grid': final_grid,
        'row_constraints_E': _apply_mode_counts(_count_by_row(final_grid,'E'),'eq',0,0),
        'row_constraints_V': _apply_mode_counts(_count_by_row(final_grid,'V'),'eq',0,0),
        'col_constraints_E': _apply_mode_counts(_count_by_col(final_grid,'E'),'eq',0,0),
        'col_constraints_V': _apply_mode_counts(_count_by_col(final_grid,'V'),'eq',0,0),
        'region_quota_desc': '区域配额未设置',
        'mask_desc': 'E/V 未启用掩码约束',
        'anchor_desc': '未设置锚定方向约束',
        'rules_summary': '[扶梯 E 与站点 S 至少一个正交邻接; 扶梯之间不得 8 邻接; 通风口之间不得 8 邻接; 通风口不得与站点 S 正交相邻; 任意两座通风口的曼哈顿距离至少为 2; 扶梯总数必须等于站点总数]',
        'constraints_summary': '行列约束模式均为 eq（等于）。',
        'S_count': len(S_list),
        'E_count': len(E_list),
        'V_count': len(V_list),
    }

def function_2(grid: List[List[str]]) -> Tuple[Tuple[str, ...], ...]:
    return tuple(tuple(row) for row in grid)