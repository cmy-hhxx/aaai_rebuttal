# minesweeper_4.py
# 强化版生成与验证：
# - 强制最少数字(min_digits)与最少正数字(min_positive_digits)，杜绝“无约束/全0”退化
# - 行/列界区间下限(bounds_min_width)，且至少一个行界与一个列界扩宽到≥2
# - 区域权重界宽度≥2，仅施加在含≥2未知格的区域；奇偶仅在含≥3未知格的区域
# - 唯一解验证早停(最多收集2解)；控制网格规模与未知上限
# - 移除劣质兜底，改为多次再播种(reseed)直到找到符合门槛的唯一解题面

import random
import time

# ---------------- 基础工具 ----------------
def _neighbors(rc, n, m, neighbor_kind_code):
    r, c = rc
    if neighbor_kind_code == 1:
        deltas = [(-1,0),(1,0),(0,-1),(0,1)]
    else:
        deltas = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    for dr, dc in deltas:
        rr, cc = r + dr, c + dc
        if 0 <= rr < n and 0 <= cc < m:
            yield (rr, cc)

def _tag_weight(tag, A_weight, B_weight, C_weight):
    if tag == 'XA': return A_weight
    if tag == 'XB': return B_weight
    if tag == 'XC': return C_weight
    raise ValueError("Unknown tag: {}".format(tag))

def pick_b_weight(a_weight, seed):
    rnd = random.Random(seed + 101)
    candidates = [2, 3, 4, 5]
    if a_weight in candidates:
        candidates.remove(a_weight)
    return rnd.choice(candidates)

def pick_c_weight(a_weight, b_weight, seed):
    rnd = random.Random(seed + 202)
    candidates = [3, 4, 5, 6]
    diff_all = [x for x in candidates if x != a_weight and x != b_weight]
    if diff_all: return rnd.choice(diff_all)
    diff_any = [x for x in candidates if (x != a_weight) or (x != b_weight)]
    return rnd.choice(diff_any)

# ---------------- 文本渲染 ----------------
def function_3(type_count, relation_code, A_weight, B_weight, C_weight, neighbor_kind_code):
    nk = '8邻域' if neighbor_kind_code == 0 else '4邻域'
    if relation_code == 0: rel = '每个数字等于其邻域雷的权重总和'
    elif relation_code == 1: rel = '每个数字是其邻域雷的权重总和的下界(不少于该值)'
    else: rel = '每个数字是其邻域雷的权重总和的上界(不大于该值)'
    if type_count == 2:
        type_part = f'未知格分两类: XA(若为雷则权重={A_weight}) 与 XB(若为雷则权重={B_weight})'
    else:
        type_part = f'未知格分三类: XA(若为雷则权重={A_weight})、XB(若为雷则权重={B_weight})、XC(若为雷则权重={C_weight})'
    return f'{type_part}; 邻域类型为{nk}; {rel}'

def function_5(rules):
    parts = []
    rb = rules.get('row_bounds', [])
    cb = rules.get('col_bounds', [])
    tq = rules.get('type_quota', {})
    pr = rules.get('parity_rules', [])
    rbs = rules.get('region_bounds', [])
    adj_b = rules.get('adjacency_no_ortho_B', False)
    if rb:
        parts.append('行权重界: ' + ', '.join([f'第{d["row"]}行总权重在[{d["min"]}, {d["max"]}]' for d in rb]))
    if cb:
        parts.append('列权重界: ' + ', '.join([f'第{d["col"]}列总权重大于等于{d["min"]}且不超过{d["max"]}' for d in cb]))
    if rbs:
        parts.append('区域权重界: ' + ', '.join([
            f'区域(({d["r0"]},{d["c0"]})到({d["r1"]},{d["c1"]}))总权重在[{d["min"]}, {d["max"]}]'
            for d in rbs
        ]))
    if tq:
        quotas = []
        for k in ['A','B','C']:
            if k in tq:
                quotas.append(f'{k}型雷个数在[{tq[k]["min"]}, {tq[k]["max"]}]')
        if quotas:
            parts.append('类型配额: ' + ', '.join(quotas))
    if pr:
        parts.append('子区域奇偶: ' + ', '.join([
            f'区域(({d["r0"]},{d["c0"]})到({d["r1"]},{d["c1"]}))的{"权重" if d["kind"]=="weight" else "数量"}为{"偶" if d["parity"]==0 else "奇"}'
            for d in pr
        ]))
    if adj_b:
        parts.append('邻接限制: 禁止B型雷在正交方向相邻')
    base = '; '.join(parts) if parts else '无额外约束'
    return base + '。注: 总权重指该行、列或指定区域内所有地雷格的权重之和'

# ---------------- 预处理 ----------------
def _build_unknowns(grid):
    n = len(grid); m = len(grid[0]) if n>0 else 0
    unknowns = []
    for r in range(n):
        for c in range(m):
            v = grid[r][c]
            if v in ('XA','XB','XC'):
                unknowns.append((r,c,v))
    return unknowns

def _precompute_digit_neighbors(grid, rules):
    n = len(grid); m = len(grid[0])
    neighbor_kind_code = rules['neighbor_kind_code']
    A_weight = rules['weights']['A']; B_weight = rules['weights']['B']; C_weight = rules['weights']['C']
    unknowns = _build_unknowns(grid)
    pos_to_index = {(r,c): i for i,(r,c,_) in enumerate(unknowns)}
    digit_neighbors = []
    digits = []
    for r in range(n):
        for c in range(m):
            if isinstance(grid[r][c], int):
                target = grid[r][c]
                lst = []
                for rr, cc in _neighbors((r,c), n, m, neighbor_kind_code):
                    v = grid[rr][cc]
                    if v in ('XA','XB','XC'):
                        w = A_weight if v=='XA' else (B_weight if v=='XB' else C_weight)
                        lst.append((pos_to_index[(rr,cc)], w))
                digit_neighbors.append(lst)
                digits.append(target)
    return unknowns, digits, digit_neighbors

def _adjacency_list_B(grid):
    unknowns = _build_unknowns(grid)
    pos_to_index = {(r,c): i for i,(r,c,_) in enumerate(unknowns)}
    n = len(grid); m = len(grid[0])
    adj = {i: [] for i,(_,_,t) in enumerate(unknowns) if t=='XB'}
    for i,(r,c,t) in enumerate(unknowns):
        if t=='XB':
            for rr, cc in _neighbors((r,c), n, m, 1):
                if 0<=rr<n and 0<=cc<m and grid[rr][cc]=='XB':
                    j = pos_to_index.get((rr,cc))
                    if j is not None and j != i:
                        adj[i].append(j)
    return adj

def _precompute_regions(grid, rules, weights_map):
    unknowns = _build_unknowns(grid)
    pos_to_index = {(r,c): i for i,(r,c,_) in enumerate(unknowns)}
    regions = []
    for rb in rules.get('region_bounds', []):
        cells = []
        for r in range(rb['r0'], rb['r1']+1):
            for c in range(rb['c0'], rb['c1']+1):
                v = grid[r][c]
                if v in ('XA','XB','XC'):
                    idx = pos_to_index[(r,c)]
                    w = weights_map[v]
                    cells.append((idx, w))
        regions.append(cells)
    return regions

# ---------------- 唯一性枚举(早停) ----------------
def _enumerate_solutions(grid, rules, time_limit_sec, max_solutions=2):
    t0 = time.time()
    unknowns, digits, digit_neighbors = _precompute_digit_neighbors(grid, rules)
    n = len(grid); m = len(grid[0]); U = len(unknowns)
    weights_map = {'XA': rules['weights']['A'], 'XB': rules['weights']['B'], 'XC': rules['weights']['C']}
    row_bounds = rules.get('row_bounds', [])
    col_bounds = rules.get('col_bounds', [])
    region_bounds = rules.get('region_bounds', [])
    type_quota = rules.get('type_quota', {})
    parities = rules.get('parity_rules', [])
    relation_code = rules['relation_code']
    adj_list_B = _adjacency_list_B(grid) if rules.get('adjacency_no_ortho_B', False) else {}
    pos_index = [(r,c,t) for (r,c,t) in unknowns]

    # 状态初始化
    D = len(digits)
    digit_cur = [0]*D
    digit_rem = [sum(w for _,w in dn) for dn in digit_neighbors]
    row_cur = [0]*n; row_rem = [0]*n
    col_cur = [0]*m; col_rem = [0]*m
    type_cur = {'A':0,'B':0,'C':0}
    type_rem = {'A':0,'B':0,'C':0}
    for i,(r,c,t) in enumerate(pos_index):
        w = weights_map[t]
        row_rem[r] += w; col_rem[c] += w
        key = 'A' if t=='XA' else ('B' if t=='XB' else 'C')
        type_rem[key] += 1
    regions = _precompute_regions(grid, rules, weights_map)
    R = len(regions)
    region_cur = [0]*R
    region_rem = [sum(w for _,w in cells) for cells in regions]

    # 变量顺序：参与数字约束数 * 权重 降序
    deg = []
    for i in range(U):
        w = weights_map[pos_index[i][2]]
        used_by = sum(1 for dn in digit_neighbors if any(idx==i for idx,_ in dn))
        deg.append((used_by*w, i))
    order = [i for _,i in sorted(deg, key=lambda x: (-x[0], x[1]))]

    assigned = [None]*U
    solutions = []

    def check_digits():
        for d in range(D):
            s = digit_cur[d]; rem = digit_rem[d]; tgt = digits[d]
            if relation_code == 0:
                if not (s <= tgt <= s + rem): return False
            elif relation_code == 1:
                if s + rem < tgt: return False
            else:
                if s > tgt: return False
        return True

    def check_rows_cols():
        for rb in row_bounds:
            r = rb['row']; low, high = rb['min'], rb['max']
            if row_cur[r] > high: return False
            if row_cur[r] + row_rem[r] < low: return False
        for cb in col_bounds:
            c = cb['col']; low, high = cb['min'], cb['max']
            if col_cur[c] > high: return False
            if col_cur[c] + col_rem[c] < low: return False
        return True

    def check_regions():
        for k, cells in enumerate(regions):
            if not cells: continue
            low, high = region_bounds[k]['min'], region_bounds[k]['max']
            if region_cur[k] > high: return False
            if region_cur[k] + region_rem[k] < low: return False
        return True

    def check_types():
        for k, lim in type_quota.items():
            low, high = lim['min'], lim['max']
            if type_cur[k] > high: return False
            if type_cur[k] + type_rem[k] < low: return False
        return True

    def parity_leaf_ok():
        for pr in parities:
            r0,c0,r1,c1 = pr['r0'], pr['c0'], pr['r1'], pr['c1']
            cells = []
            for idx,(rr,cc,t) in enumerate(pos_index):
                if r0 <= rr <= r1 and c0 <= cc <= c1: cells.append(idx)
            if pr['kind'] == 'weight':
                s = 0
                for idx in cells:
                    if assigned[idx] == 1:
                        t = pos_index[idx][2]
                        s += weights_map[t]
                if (s % 2) != pr['parity']: return False
            else:
                cnt = sum(1 for idx in cells if assigned[idx]==1)
                if (cnt % 2) != pr['parity']: return False
        return True

    def leaf_digits_ok():
        if relation_code == 0: return all(digit_cur[d] == digits[d] for d in range(D))
        if relation_code == 1: return all(digit_cur[d] >= digits[d] for d in range(D))
        return all(digit_cur[d] <= digits[d] for d in range(D))

    touch_list = [[] for _ in range(U)]
    for d, dn in enumerate(digit_neighbors):
        for idx, ww in dn:
            touch_list[idx].append(('digit', d, ww))
    for k, cells in enumerate(regions):
        for idx, w in cells:
            touch_list[idx].append(('region', k, w))

    def dfs(k):
        if time.time() - t0 > time_limit_sec or len(solutions) >= max_solutions: return
        if k == U:
            if not leaf_digits_ok(): return
            if not parity_leaf_ok(): return
            solutions.append(assigned[:]); return
        i = order[k]
        r,c,t = pos_index[i]; w = weights_map[t]
        for val in (1, 0):
            b_digit_cur = digit_cur[:]; b_digit_rem = digit_rem[:]
            b_row_cur = row_cur[:]; b_row_rem = row_rem[:]
            b_col_cur = col_cur[:]; b_col_rem = col_rem[:]
            b_type_cur = dict(type_cur); b_type_rem = dict(type_rem)
            b_region_cur = region_cur[:]; b_region_rem = region_rem[:]
            prev = assigned[i]
            assigned[i] = val
            for tag, idx, ww in touch_list[i]:
                if tag == 'digit':
                    if val == 1: digit_cur[idx] += ww
                    digit_rem[idx] -= ww
                else:
                    if val == 1: region_cur[idx] += ww
                    region_rem[idx] -= ww
            if val == 1:
                row_cur[r] += w; col_cur[c] += w
            row_rem[r] -= w; col_rem[c] -= w
            key = 'A' if t=='XA' else ('B' if t=='XB' else 'C')
            if val == 1: type_cur[key] += 1
            type_rem[key] -= 1
            if rules.get('adjacency_no_ortho_B', False) and t=='XB' and val == 1:
                # 预构建的邻接（常数开销检查）
                bad = any(assigned[j] == 1 for j in adj_list_B.get(i, []))
                if bad:
                    digit_cur[:] = b_digit_cur; digit_rem[:] = b_digit_rem
                    row_cur[:] = b_row_cur; row_rem[:] = b_row_rem
                    col_cur[:] = b_col_cur; col_rem[:] = b_col_rem
                    type_cur.clear(); type_cur.update(b_type_cur)
                    type_rem.clear(); type_rem.update(b_type_rem)
                    region_cur[:] = b_region_cur; region_rem[:] = b_region_rem
                    assigned[i] = prev
                    continue
            if check_digits() and check_rows_cols() and check_regions() and check_types():
                dfs(k+1)
            digit_cur[:] = b_digit_cur; digit_rem[:] = b_digit_rem
            row_cur[:] = b_row_cur; row_rem[:] = b_row_rem
            col_cur[:] = b_col_cur; col_rem[:] = b_col_rem
            type_cur.clear(); type_cur.update(b_type_cur)
            type_rem.clear(); type_rem.update(b_type_rem)
            region_cur[:] = b_region_cur; region_rem[:] = b_region_rem
            assigned[i] = prev

    dfs(0)
    timed_out = (time.time() - t0 > time_limit_sec)
    return solutions, timed_out

# ---------------- 答案计算(全解交集) ----------------
def function_2(grid, rules):
    sols, _ = _enumerate_solutions(grid, rules, time_limit_sec=3, max_solutions=2)
    if not sols: return []
    U = len(_build_unknowns(grid))
    must = [1]*U
    for bits in sols:
        for i in range(U):
            must[i] = must[i] and (bits[i]==1)
    unknowns = _build_unknowns(grid)
    out = []
    for i,(r,c,t) in enumerate(unknowns):
        if must[i]:
            out.append(((r,c), 'A' if t=='XA' else ('B' if t=='XB' else 'C')))
    return sorted(out, key=lambda x: (x[0][0], x[0][1], x[1]))

# ---------------- 世界一次生成 ----------------
def _gen_world_once(rnd, n_rows, n_cols, type_count,
                    unk_pct, xa_pct, xb_pct, xc_pct,
                    p_mA, p_mB, p_mC, safe_pct,
                    relation_code, A_weight, B_weight, C_weight,
                    neighbor_kind_code, row_bound_target, col_bound_target, region_bound_target, bounds_min_width):
    n, m = n_rows, n_cols
    # 比例
    p_unk = max(0.0, min(1.0, unk_pct/100.0))
    p_safe = max(0.0, min(1.0, safe_pct/100.0))
    p_xa = max(0.0, min(1.0, xa_pct/100.0))
    p_xb = max(0.0, min(1.0, xb_pct/100.0))
    p_xc = max(0.0, min(1.0, xc_pct/100.0)) if type_count==3 else 0.0
    base_sum = p_xa+p_xb+p_xc
    if base_sum <= 0:
        p_xa,p_xb,p_xc = (0.5,0.5,0.0) if type_count==2 else (0.4,0.4,0.2)
    else:
        p_xa/=base_sum; p_xb/=base_sum; p_xc/=base_sum
    # 分类
    cell_kind = [['' for _ in range(m)] for __ in range(n)]
    for r in range(n):
        for c in range(m):
            if rnd.random() < p_unk: cell_kind[r][c] = 'U'
            else: cell_kind[r][c] = 'S' if rnd.random() < p_safe else 'C'
    if not any(cell_kind[r][c]=='C' for r in range(n) for c in range(m)):
        pool = [(r,c) for r in range(n) for c in range(m) if cell_kind[r][c] != 'U'] or [(r,c) for r in range(n) for c in range(m)]
        rr,cc = rnd.choice(pool); cell_kind[rr][cc] = 'C'
    # 未知类型与真值
    u_type = [[None for _ in range(m)] for __ in range(n)]
    u_is_mine = [[False for _ in range(m)] for __ in range(n)]
    for r in range(n):
        for c in range(m):
            if cell_kind[r][c]=='U':
                x = rnd.random()
                if x < p_xa:
                    u_type[r][c] = 'XA'; u_is_mine[r][c] = rnd.random() < p_mA
                elif x < p_xa + p_xb:
                    u_type[r][c] = 'XB'; u_is_mine[r][c] = rnd.random() < p_mB
                else:
                    u_type[r][c] = 'XC' if type_count==3 else ('XB' if rnd.random()<0.5 else 'XA')
                    if u_type[r][c]=='XC': u_is_mine[r][c] = rnd.random() < p_mC
                    else: u_is_mine[r][c] = rnd.random() < (p_mB if u_type[r][c]=='XB' else p_mA)
    adjacency_no_ortho_B = rnd.random() < 0.3
    if adjacency_no_ortho_B:
        for r in range(n):
            for c in range(m):
                if cell_kind[r][c]=='U' and u_type[r][c]=='XB' and u_is_mine[r][c]:
                    for rr,cc in _neighbors((r,c), n,m, 1):
                        if cell_kind[rr][cc]=='U' and u_type[rr][cc]=='XB' and u_is_mine[rr][cc]:
                            if rnd.random() < 0.5: u_is_mine[rr][cc] = False
                            else: u_is_mine[r][c] = False
    # 组装grid
    grid = [[None for _ in range(m)] for __ in range(n)]
    for r in range(n):
        for c in range(m):
            if cell_kind[r][c]=='U': grid[r][c] = u_type[r][c]
            elif cell_kind[r][c]=='S': grid[r][c] = 'S'
            else:
                ssum = 0
                for rr,cc in _neighbors((r,c), n,m, neighbor_kind_code):
                    if cell_kind[rr][cc]=='U' and u_is_mine[rr][cc]:
                        ssum += _tag_weight(u_type[rr][cc], A_weight, B_weight, C_weight)
                if relation_code==0: val = ssum
                elif relation_code==1: val = ssum + (rnd.randint(1,2) if rnd.random()<0.7 else 0)
                else:
                    dec = (rnd.randint(1, min(2, ssum)) if ssum>0 and rnd.random()<0.7 else 0)
                    val = max(0, ssum - dec)
                grid[r][c] = val
    # 真实行列权重
    row_weight_true = [0]*n; col_weight_true = [0]*m
    for r in range(n):
        for c in range(m):
            if cell_kind[r][c]=='U' and u_is_mine[r][c]:
                w = _tag_weight(u_type[r][c], A_weight, B_weight, C_weight)
                row_weight_true[r] += w; col_weight_true[c] += w
    # 规则
    rules = {
        'neighbor_kind_code': neighbor_kind_code,
        'relation_code': relation_code,
        'weights': {'A': A_weight, 'B': B_weight, 'C': C_weight},
        'row_bounds': [], 'col_bounds': [],
        'region_bounds': [], 'type_quota': {},
        'parity_rules': [], 'adjacency_no_ortho_B': adjacency_no_ortho_B
    }
    # 行界
    rows = list(range(n)); rnd.shuffle(rows)
    row_pick = rows[:max(1, min(n, row_bound_target))]
    for r in row_pick:
        base = row_weight_true[r]
        low = max(0, base - rnd.randint(bounds_min_width, bounds_min_width+1))
        high = base + rnd.randint(bounds_min_width, bounds_min_width+2)
        if high <= low: high = low + bounds_min_width
        rules['row_bounds'].append({'row': r, 'min': low, 'max': high})
    if rules['row_bounds']:
        i = rnd.randrange(len(rules['row_bounds']))
        rb = rules['row_bounds'][i]
        if rb['max'] - rb['min'] < 2: rb['max'] = rb['min'] + 2
    # 列界
    cols = list(range(m)); rnd.shuffle(cols)
    col_pick = cols[:max(1, min(m, col_bound_target))]
    for c in col_pick:
        base = col_weight_true[c]
        low = max(0, base - rnd.randint(bounds_min_width, bounds_min_width+1))
        high = base + rnd.randint(bounds_min_width, bounds_min_width+2)
        if high <= low: high = low + bounds_min_width
        rules['col_bounds'].append({'col': c, 'min': low, 'max': high})
    if rules['col_bounds']:
        i = rnd.randrange(len(rules['col_bounds']))
        cb = rules['col_bounds'][i]
        if cb['max'] - cb['min'] < 2: cb['max'] = cb['min'] + 2
    # 类型配额
    cntA = sum(1 for r in range(n) for c in range(m) if cell_kind[r][c]=='U' and u_is_mine[r][c] and u_type[r][c]=='XA')
    cntB = sum(1 for r in range(n) for c in range(m) if cell_kind[r][c]=='U' and u_is_mine[r][c] and u_type[r][c]=='XB')
    cntC = sum(1 for r in range(n) for c in range(m) if cell_kind[r][c]=='U' and u_is_mine[r][c] and u_type[r][c]=='XC')
    def quota_range(base):
        lo = max(0, base - rnd.randint(1,2)); hi = base + rnd.randint(1,3)
        if hi <= lo: hi = lo + 1
        return {'min': lo, 'max': hi}
    rules['type_quota']['A'] = quota_range(cntA)
    rules['type_quota']['B'] = quota_range(cntB)
    if type_count==3: rules['type_quota']['C'] = quota_range(cntC)
    # 区域权重界：宽度≥2，仅施加在含≥2未知格的区域
    tries_rb = 0
    while len(rules['region_bounds']) < max(0, int(region_bound_target)) and tries_rb < 20:
        tries_rb += 1
        r0 = rnd.randint(0, n-1); c0 = rnd.randint(0, m-1)
        r1 = rnd.randint(r0, n-1); c1 = rnd.randint(c0, m-1)
        cells = []; base_sum = 0
        for r in range(r0, r1+1):
            for c in range(c0, c1+1):
                if cell_kind[r][c]=='U':
                    cells.append((r,c))
                    if u_is_mine[r][c]:
                        base_sum += _tag_weight(u_type[r][c], A_weight, B_weight, C_weight)
        if len(cells) < 2: continue
        low = max(0, base_sum - rnd.randint(1,2))
        high = base_sum + rnd.randint(2,4)
        if high <= low + 1: high = low + 2
        rules['region_bounds'].append({'r0': r0, 'c0': c0, 'r1': r1, 'c1': c1, 'min': low, 'max': high})
    # 奇偶约束：仅施加在含≥3未知格的区域
    if rnd.random() < 0.6:
        for _ in range(10):
            r0 = rnd.randint(0, n-1); c0 = rnd.randint(0, m-1)
            r1 = rnd.randint(r0, n-1); c1 = rnd.randint(c0, m-1)
            cnt_unknown = sum(1 for r in range(r0, r1+1) for c in range(c0, c1+1) if cell_kind[r][c]=='U')
            if cnt_unknown >= 3:
                wsum = 0; cnt = 0
                for r in range(r0, r1+1):
                    for c in range(c0, c1+1):
                        if cell_kind[r][c]=='U' and u_is_mine[r][c]:
                            wsum += _tag_weight(u_type[r][c], A_weight, B_weight, C_weight); cnt += 1
                kind = 'weight' if rnd.random() < 0.5 else 'count'
                target_parity = (wsum % 2) if kind=='weight' else (cnt % 2)
                rules['parity_rules'].append({'r0': r0, 'c0': c0, 'r1': r1, 'c1': c1, 'kind': kind, 'parity': target_parity})
                break
    return {'grid': grid, 'rules': rules, 'meta': {'cell_kind': cell_kind, 'u_type': u_type, 'u_is_mine': u_is_mine}}

# ---------------- 世界生成 + 唯一解验证(多次再播种) ----------------
def function_1(seed, n_rows, n_cols, type_count,
               unknown_density_percent, xa_ratio_percent, xb_ratio_percent, xc_ratio_percent,
               mine_a_percent, mine_b_percent, mine_c_percent,
               safe_ratio_percent, relation_code,
               A_weight, B_weight, C_weight,
               neighbor_kind_code, row_bound_target, col_bound_target, region_bound_target, bounds_min_width,
               unknown_upper_bound, min_digits, min_positive_digits, min_forced, time_limit_sec):
    # 多轮尝试 + 再播种确保不输出劣质题面
    outer_reseeds = 12
    tries_per_seed = 280
    base_rng = random.Random(seed)
    for reseed_id in range(outer_reseeds):
        local_seed = seed + 7919 * (reseed_id + 1) + base_rng.randint(0, 10**6)
        rnd = random.Random(local_seed)
        best = None; best_forced_cnt = -1
        for _ in range(tries_per_seed):
            world = _gen_world_once(rnd, n_rows, n_cols, type_count,
                                    unknown_density_percent, xa_ratio_percent, xb_ratio_percent, xc_ratio_percent,
                                    mine_a_percent/100.0, mine_b_percent/100.0, (mine_c_percent/100.0 if type_count==3 else 0.0),
                                    safe_ratio_percent, relation_code,
                                    A_weight, B_weight, C_weight,
                                    neighbor_kind_code, row_bound_target, col_bound_target, region_bound_target, bounds_min_width)
            grid = world['grid']; rules = world['rules']
            U = len(_build_unknowns(grid))
            if U > unknown_upper_bound: continue
            digits = [(r,c) for r in range(n_rows) for c in range(n_cols) if isinstance(grid[r][c], int)]
            if len(digits) < min_digits: continue
            positive_digits = sum(1 for r,c in digits if grid[r][c] > 0)
            if positive_digits < min_positive_digits: continue
            # 唯一性验证（早停）
            sols, timed_out = _enumerate_solutions(grid, rules, time_limit_sec=time_limit_sec, max_solutions=2)
            if timed_out or not sols: continue
            if len(sols) != 1: continue
            forced = function_2(grid, rules)
            cnt = len(forced)
            if cnt >= max(1, int(min_forced)):
                return world
            if cnt > best_forced_cnt:
                best_forced_cnt = cnt; best = world
        if best is not None:
            # 次优返回（唯一解已保证，因为只有唯一解才会进入best的更新）
            return best
    # 极端失败：抛出异常，交由上层重试，不返回劣质题面
    raise RuntimeError('Failed to generate a high-quality unique puzzle within time and attempt limits.')