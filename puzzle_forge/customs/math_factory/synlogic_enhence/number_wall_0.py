# number_wall_0.py
# 逆向生成 Nurikabe：规则随机化 + 随机实例生成 + 严格校验 + 强化唯一性验证（提示强度受控，区分玩家提示与内部提示）
from typing import List, Union, Tuple, Dict, Any, Set
import json, random, time
from collections import deque

Cell = Union[str, int]
Grid = List[List[Cell]]

def grid_to_str(grid: Grid) -> str:
    return json.dumps(grid, ensure_ascii=False, indent=2)

def _in_bounds(r: int, c: int, R: int, C: int) -> bool:
    return 0 <= r < R and 0 <= c < C

def _neighbors(r: int, c: int) -> List[Tuple[int, int]]:
    return [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]

def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True

def build_rule_profile(rows: int, cols: int) -> Dict[str, Any]:
    enforce_no_2x2_wall = True
    enforce_wall_connected = random.random() < 0.7
    enforce_single_number_island = True
    enforce_island_size_equals_number = True
    enforce_land_orth_conn = True
    modes = [
        ('none', 50),
        ('at_least_one_even', 20),
        ('at_least_one_prime', 15),
        ('all_even', 5),
        ('all_odd', 5),
        ('all_prime', 5),
    ]
    total_w = sum(w for _, w in modes)
    r = random.randint(1, total_w); acc = 0
    number_property_mode = 'none'
    for m, w in modes:
        acc += w
        if r <= acc:
            number_property_mode = m
            break
    max_hint = max(1, (rows + cols) // 3)
    min_island_count = random.randint(1, max_hint)
    # 玩家提示的启用概率（受控，避免显见线索）
    enable_row_col_counts = random.random() < 0.6
    enable_given_walls = random.random() < 0.7
    enable_given_islands = random.random() < 0.6
    adjacency_hints_count = random.randint(0, 2)
    return {
        'enforce_no_2x2_wall': enforce_no_2x2_wall,
        'enforce_wall_connected': enforce_wall_connected,
        'enforce_single_number_island': enforce_single_number_island,
        'enforce_island_size_equals_number': enforce_island_size_equals_number,
        'enforce_land_orth_conn': enforce_land_orth_conn,
        'number_property_mode': number_property_mode,
        'min_island_count': min_island_count,
        'enable_row_col_counts': enable_row_col_counts,
        'enable_given_walls': enable_given_walls,
        'enable_given_islands': enable_given_islands,
        'adjacency_hints_count': adjacency_hints_count,
    }

def render_rule_desc(rule_profile: Dict[str, Any]) -> str:
    items: List[str] = []
    items.append('岛必须通过水平或垂直方式连通')
    if rule_profile.get('enforce_single_number_island', True):
        items.append('每个岛恰好包含一个数字')
    if rule_profile.get('enforce_island_size_equals_number', True):
        items.append('每个岛的格子总数(含数字格)必须等于该数字')
    if rule_profile.get('enforce_no_2x2_wall', True):
        items.append('墙 A 不允许出现任何 2×2 的全 A 块')
    if rule_profile.get('enforce_wall_connected', False):
        items.append('所有墙 A 必须整体四连通')
    mode = rule_profile.get('number_property_mode', 'none')
    if mode == 'all_even':
        items.append('所有岛的数字必须为偶数')
    elif mode == 'all_odd':
        items.append('所有岛的数字必须为奇数')
    elif mode == 'all_prime':
        items.append('所有岛的数字必须为质数(大于1且只有1与自身两个正因数)')
    elif mode == 'at_least_one_even':
        items.append('至少有一个岛的数字为偶数')
    elif mode == 'at_least_one_prime':
        items.append('至少有一个岛的数字为质数')
    mic = rule_profile.get('min_island_count', None)
    if isinstance(mic, int) and mic > 0:
        items.append(f'岛屿数量不得少于 {mic}')
    return '；\n'.join(items)

def render_hints_desc(hints: Dict[str, Any]) -> str:
    parts: List[str] = []
    rc = hints.get('row_wall_counts'); cc = hints.get('col_wall_counts')
    if isinstance(rc, list):
        parts.append(f'行的墙计数为 [{", ".join(str(x) for x in rc)}]，顺序对应自上而下各行')
    if isinstance(cc, list):
        parts.append(f'列的墙计数为 [{", ".join(str(x) for x in cc)}]，顺序对应自左而右各列')
    given_A = hints.get('given_walls', []); given_X = hints.get('given_islands', [])
    if given_A:
        parts.append(f'已知 A 的坐标数量为 {len(given_A)} (坐标格式为 [r,c]，从 0 开始计)')
    if given_X:
        parts.append(f'已知岛格 X 的坐标数量为 {len(given_X)}')
    adjh = hints.get('adjacency_hints', [])
    if adjh:
        parts.append(f'邻接约束共 {len(adjh)} 条，例如 [r,c,k] 表示该格周围四邻必须恰有 k 个 A')
    if not parts:
        return '无额外提示'
    return '；\n'.join(parts)

# ---------- 通用连通分量与墙生成 ----------
def _components(mask: List[List[bool]], target: bool) -> List[List[Tuple[int, int]]]:
    R, C = len(mask), len(mask[0])
    vis = [[False]*C for _ in range(R)]
    comps: List[List[Tuple[int, int]]] = []
    for r in range(R):
        for c in range(C):
            if (mask[r][c] == target) and not vis[r][c]:
                q = deque([(r,c)]); vis[r][c] = True
                comp: List[Tuple[int,int]] = []
                while q:
                    cr, cc = q.popleft(); comp.append((cr,cc))
                    for nr, nc in _neighbors(cr, cc):
                        if _in_bounds(nr, nc, R, C) and not vis[nr][nc] and mask[nr][nc] == target:
                            vis[nr][nc] = True; q.append((nr, nc))
                comps.append(comp)
    return comps

def _gen_A_mask_no_2x2(R: int, C: int, p: float) -> List[List[bool]]:
    mask = [[False]*C for _ in range(R)]
    for r in range(R):
        for c in range(C):
            if random.random() < p:
                mask[r][c] = True
                def cell_is_A(rr, cc):
                    return 0 <= rr < R and 0 <= cc < C and mask[rr][cc]
                bad = False
                for dr, dc in [(0,0), (-1,0), (0,-1), (-1,-1)]:
                    r0, c0 = r+dr, c+dc
                    if 0 <= r0 < R-1 and 0 <= c0 < C-1:
                        if (cell_is_A(r0, c0) and cell_is_A(r0, c0+1) and
                            cell_is_A(r0+1, c0) and cell_is_A(r0+1, c0+1)):
                            bad = True; break
                if bad:
                    mask[r][c] = False
    if all(mask[r][c] for r in range(R) for c in range(C)):
        rr, cc = random.randrange(R), random.randrange(C)
        mask[rr][cc] = False
    return mask

def _try_connect_wall(mask: List[List[bool]], max_steps: int = 200) -> bool:
    R, C = len(mask), len(mask[0])
    def forms_2x2_if_set_A(r: int, c: int) -> bool:
        mask[r][c] = True; bad = False
        for dr, dc in [(0,0), (-1,0), (0,-1), (-1,-1)]:
            r0, c0 = r+dr, c+dc
            if 0 <= r0 < R-1 and 0 <= c0 < C-1:
                if (mask[r0][c0] and mask[r0][c0+1] and mask[r0+1][c0] and mask[r0+1][c0+1]):
                    bad = True; break
        mask[r][c] = False
        return bad
    def connect_pair(a: Tuple[int,int], b: Tuple[int,int]) -> bool:
        r, c = a; tr, tc = b; steps = 0
        dr = 1 if tr > r else (-1 if tr < r else 0)
        while r != tr and steps < max_steps:
            nr, nc = r+dr, c
            if not mask[nr][nc]:
                if forms_2x2_if_set_A(nr, nc): return False
                mask[nr][nc] = True
            r = nr; steps += 1
        dc = 1 if tc > c else (-1 if tc < c else 0)
        while c != tc and steps < max_steps:
            nr, nc = r, c+dc
            if not mask[nr][nc]:
                if forms_2x2_if_set_A(nr, nc): return False
                mask[nr][nc] = True
            c = nc; steps += 1
        return True
    for _ in range(10):
        comps = _components(mask, True)
        if len(comps) <= 1: return True
        base = comps[0][0]; ok_all = True
        for comp in comps[1:]:
            b = min(comp, key=lambda xy: abs(xy[0]-base[0]) + abs(xy[1]-base[1]))
            if not connect_pair(base, b): ok_all = False; break
            base = b
        if ok_all and len(_components(mask, True)) == 1: return True
    return False

def _solution_from_mask_and_numbers(mask: List[List[bool]], comps: List[List[Tuple[int,int]]]) -> Grid:
    R, C = len(mask), len(mask[0])
    sol: Grid = [['A' if mask[r][c] else 'X' for c in range(C)] for r in range(R)]
    for comp in comps:
        size = len(comp)
        rnum, cnum = random.choice(comp)
        sol[rnum][cnum] = size
    return sol

def _count_walls_grid(grid: Grid) -> Tuple[List[int], List[int]]:
    R, C = len(grid), len(grid[0])
    row_counts = [sum(1 for c in range(C) if grid[r][c] == 'A') for r in range(R)]
    col_counts = [sum(1 for r in range(R) if grid[r][c] == 'A') for c in range(C)]
    return row_counts, col_counts

def _check_no_2x2_A(grid: Grid) -> bool:
    R, C = len(grid), len(grid[0])
    for r in range(R-1):
        for c in range(C-1):
            block = [grid[r][c], grid[r][c+1], grid[r+1][c], grid[r+1][c+1]]
            if all(x == 'A' for x in block): return False
    return True

def _check_wall_connected(grid: Grid) -> bool:
    R, C = len(grid), len(grid[0])
    vis = [[False]*C for _ in range(R)]
    start = None
    for r in range(R):
        for c in range(C):
            if grid[r][c] == 'A':
                start = (r,c); break
        if start: break
    if not start: return False
    q = deque([start]); vis[start[0]][start[1]] = True; cnt = 0
    while q:
        cr, cc = q.popleft(); cnt += 1
        for nr, nc in _neighbors(cr, cc):
            if _in_bounds(nr, nc, R, C) and not vis[nr][nc] and grid[nr][nc] == 'A':
                vis[nr][nc] = True; q.append((nr, nc))
    totalA = sum(1 for r in range(R) for c in range(C) if grid[r][c] == 'A')
    return cnt == totalA

def _check_adjacency_hints(grid: Grid, hints: Dict[str, Any]) -> bool:
    adjh = hints.get('adjacency_hints', [])
    R, C = len(grid), len(grid[0])
    for r, c, k in adjh:
        cnt = 0
        for nr, nc in _neighbors(r, c):
            if _in_bounds(nr, nc, R, C) and grid[nr][nc] == 'A':
                cnt += 1
        if cnt != k: return False
    return True

# ---------- 校验函数 ----------
def validate_solution(given_grid: Grid, solution_grid: Grid, rule_profile: Dict[str, Any], hints: Dict[str, Any]) -> bool:
    if not given_grid or not solution_grid or not rule_profile: return False
    R, C = len(given_grid), len(given_grid[0])
    if len(solution_grid) != R or any(len(row) != C for row in solution_grid): return False
    given_islands_set = set(tuple(x) for x in hints.get('given_islands', []))
    for r in range(R):
        for c in range(C):
            g = given_grid[r][c]; s = solution_grid[r][c]
            if isinstance(g, int):
                if s != g: return False
            elif g == 'A':
                if s != 'A': return False
            elif g == 'X':
                if (r, c) in given_islands_set and s != 'X': return False
            else:
                return False
            if not (s == 'A' or s == 'X' or isinstance(s, int)): return False
    if rule_profile.get('enforce_no_2x2_wall', True) and not _check_no_2x2_A(solution_grid): return False
    vis = [[False]*C for _ in range(R)]
    def is_land(x): return x != 'A'
    comps = []
    for r in range(R):
        for c in range(C):
            if is_land(solution_grid[r][c]) and not vis[r][c]:
                q = deque([(r,c)]); vis[r][c] = True
                comp = []; nums = []
                while q:
                    cr, cc = q.popleft(); comp.append((cr,cc))
                    v = solution_grid[cr][cc]
                    if isinstance(v, int): nums.append(v)
                    for nr, nc in _neighbors(cr, cc):
                        if _in_bounds(nr, nc, R, C) and not vis[nr][nc] and is_land(solution_grid[nr][nc]):
                            vis[nr][nc] = True; q.append((nr, nc))
                comps.append(comp)
                if rule_profile.get('enforce_single_number_island', True) and len(nums) != 1: return False
                if rule_profile.get('enforce_island_size_equals_number', True):
                    if len(nums) != 1 or len(comp) != nums[0]: return False
    mic = rule_profile.get('min_island_count', None)
    if isinstance(mic, int) and mic > 0 and len(comps) < mic: return False
    numbers = [solution_grid[r][c] for r in range(R) for c in range(C) if isinstance(solution_grid[r][c], int)]
    mode = rule_profile.get('number_property_mode', 'none')
    if mode == 'all_even' and (not numbers or any(n % 2 != 0 for n in numbers)): return False
    if mode == 'all_odd' and (not numbers or any(n % 2 == 0 for n in numbers)): return False
    if mode == 'all_prime' and (not numbers or any(not _is_prime(n) for n in numbers)): return False
    if mode == 'at_least_one_even' and not any(n % 2 == 0 for n in numbers): return False
    if mode == 'at_least_one_prime' and not any(_is_prime(n) for n in numbers): return False
    if rule_profile.get('enforce_wall_connected', False) and not _check_wall_connected(solution_grid): return False
    rc_hint = hints.get('row_wall_counts'); cc_hint = hints.get('col_wall_counts')
    if isinstance(rc_hint, list) or isinstance(cc_hint, list):
        row_counts, col_counts = _count_walls_grid(solution_grid)
        if isinstance(rc_hint, list) and rc_hint != row_counts: return False
        if isinstance(cc_hint, list) and cc_hint != col_counts: return False
    if not _check_adjacency_hints(solution_grid, hints): return False
    return True

# ---------- 候选枚举与唯一性 ----------
def _enumerate_island_candidates(R: int, C: int, given_grid: Grid, num_pos: Tuple[int, int], size: int, forbidden: Set[Tuple[int,int]], max_cand: int = 200) -> List[Set[Tuple[int,int]]]:
    r0, c0 = num_pos
    if (r0, c0) in forbidden: return []
    candidates: List[Set[Tuple[int,int]]] = []
    stack: List[Set[Tuple[int,int]]] = [{(r0, c0)}]
    visited_states = set()
    other_numbers = {(r, c) for r in range(R) for c in range(C) if isinstance(given_grid[r][c], int) and (r, c) != (r0, c0)}
    def ok_cell(r: int, c: int) -> bool:
        if not _in_bounds(r, c, R, C): return False
        if given_grid[r][c] == 'A': return False
        if (r, c) in other_numbers: return False
        return True
    def within_radius(r: int, c: int) -> bool:
        return abs(r - r0) + abs(c - c0) <= size
    while stack and len(candidates) < max_cand:
        comp = stack.pop()
        if len(comp) == size:
            candidates.append(comp); continue
        frontier = set()
        for (r, c) in comp:
            for nr, nc in _neighbors(r, c):
                if ok_cell(nr, nc) and within_radius(nr, nc) and (nr, nc) not in comp:
                    frontier.add((nr, nc))
        f_sorted = sorted(frontier, key=lambda xy: abs(xy[0]-r0)+abs(xy[1]-c0))
        for v in f_sorted:
            new_comp = set(comp); new_comp.add(v)
            key = tuple(sorted(new_comp))
            if key in visited_states: continue
            visited_states.add(key); stack.append(new_comp)
    return candidates

def validate_unique(given_grid: Grid, rule_profile: Dict[str, Any], hints: Dict[str, Any], timeout_sec: int) -> bool:
    start_time = time.time()
    R, C = len(given_grid), len(given_grid[0])
    islands_info: List[Tuple[Tuple[int,int], int]] = []
    for r in range(R):
        for c in range(C):
            if isinstance(given_grid[r][c], int):
                islands_info.append(((r, c), given_grid[r][c]))
    if not islands_info: return False
    forced_A: Set[Tuple[int,int]] = set(tuple(x) for x in hints.get('given_walls', []))
    forced_X_global: Set[Tuple[int,int]] = set(tuple(x) for x in hints.get('given_islands', [])) | set([(r,c) for (r,c), _ in islands_info])

    cand_list: List[List[Set[Tuple[int,int]]]] = []
    for (pos, size) in islands_info:
        cands = _enumerate_island_candidates(R, C, given_grid, pos, size, forbidden=forced_A, max_cand=220)
        if not cands: return False
        cand_list.append(cands)

    order = sorted(range(len(islands_info)), key=lambda i: len(cand_list[i]))
    assigned: List[Set[Tuple[int,int]]] = [set() for _ in islands_info]
    used: Set[Tuple[int,int]] = set()
    solutions_found = 0

    rc_hint = hints.get('row_wall_counts'); cc_hint = hints.get('col_wall_counts'); adjh = hints.get('adjacency_hints', [])

    def partial_rowcol_possible() -> bool:
        if not (isinstance(rc_hint, list) or isinstance(cc_hint, list)): return True
        current_X = used | forced_X_global
        current_A = set(forced_A)
        if isinstance(rc_hint, list):
            for r in range(R):
                minA = sum(1 for c in range(C) if (r,c) in current_A)
                maxA = C - sum(1 for c in range(C) if (r,c) in current_X)
                if not (minA <= rc_hint[r] <= maxA): return False
        if isinstance(cc_hint, list):
            for c in range(C):
                minA = sum(1 for r in range(R) if (r,c) in current_A)
                maxA = R - sum(1 for r in range(R) if (r,c) in current_X)
                if not (minA <= cc_hint[c] <= maxA): return False
        return True

    def partial_adjacency_possible() -> bool:
        if not adjh: return True
        current_X = used | forced_X_global
        current_A = set(forced_A)
        for r, c, k in adjh:
            fixedA = 0; unknown = 0
            for nr, nc in _neighbors(r, c):
                if not _in_bounds(nr, nc, R, C): continue
                if (nr, nc) in current_A: fixedA += 1
                elif (nr, nc) in current_X: pass
                else: unknown += 1
            if not (fixedA <= k <= fixedA + unknown): return True  # 允许继续探索
        return True

    def check_partial_no_2x2() -> bool:
        grid = [['?' for _ in range(C)] for _ in range(R)]
        for (rA,cA) in forced_A: grid[rA][cA] = 'A'
        for (rX,cX) in (used | forced_X_global):
            grid[rX][cX] = 'X'
        for r in range(R-1):
            for c in range(C-1):
                block = [grid[r][c], grid[r][c+1], grid[r+1][c], grid[r+1][c+1]]
                if all(x == 'A' for x in block): return False
        return True

    def build_grid_from_assignment() -> Grid:
        grid: Grid = [['?' for _ in range(C)] for _ in range(R)]
        for idx, s in enumerate(assigned):
            for (r,c) in s: grid[r][c] = 'X'
            nr, nc = list(islands_info[idx][0]); grid[nr][nc] = islands_info[idx][1]
        for (rA,cA) in forced_A: grid[rA][cA] = 'A'
        for (rX,cX) in forced_X_global:
            if not isinstance(grid[rX][cX], int): grid[rX][cX] = 'X'
        for r in range(R):
            for c in range(C):
                if grid[r][c] == '?': grid[r][c] = 'A'
        return grid

    def backtrack(k: int) -> bool:
        nonlocal solutions_found
        if time.time() - start_time > timeout_sec: return True
        if not partial_rowcol_possible(): return True
        if not check_partial_no_2x2(): return True
        if k == len(order):
            grid = build_grid_from_assignment()
            if isinstance(rc_hint, list) or isinstance(cc_hint, list):
                row_counts, col_counts = _count_walls_grid(grid)
                if isinstance(rc_hint, list) and rc_hint != row_counts: return False
                if isinstance(cc_hint, list) and cc_hint != col_counts: return False
            if not _check_adjacency_hints(grid, hints): return False
            if not validate_solution(given_grid, grid, rule_profile, hints): return False
            solutions_found += 1
            return solutions_found < 2
        i = order[k]
        cands = sorted(cand_list[i], key=lambda s: sum(1 for v in s if v in used))
        for s in cands:
            if any(v in used for v in s): continue
            nr, nc = islands_info[i][0]
            if (nr, nc) not in s: continue
            assigned[i] = s
            for v in s: used.add(v)
            if not backtrack(k+1): return False
            for v in s: used.remove(v)
            assigned[i] = set()
        return True

    ok = backtrack(0)
    return ok and solutions_found == 1

# ---------- 生成器（分离玩家提示与内部提示） ----------
def _ensure_uniqueness_internal(given_grid: Grid, hints_internal: Dict[str, Any], rule_profile: Dict[str, Any], solution_grid: Grid, max_rounds: int = 6) -> bool:
    R, C = len(solution_grid), len(solution_grid[0])
    for round_idx in range(max_rounds):
        # 内部提示：两类计数
        row_counts, col_counts = _count_walls_grid(solution_grid)
        hints_internal['row_wall_counts'] = row_counts
        hints_internal['col_wall_counts'] = col_counts
        # 已知 A/X 增强（稍多于玩家端）
        all_A = [(r,c) for r in range(R) for c in range(C) if solution_grid[r][c] == 'A']
        all_X = [(r,c) for r in range(R) for c in range(C) if solution_grid[r][c] == 'X']
        addA_num = max(1, int(len(all_A) * min(0.12, 0.06 + 0.02*round_idx)))
        addX_num = max(1, int(len(all_X) * min(0.12, 0.06 + 0.02*round_idx)))
        hints_internal.setdefault('given_walls', [])
        hints_internal.setdefault('given_islands', [])
        add_A = random.sample(all_A, min(addA_num, len(all_A)))
        add_X = random.sample(all_X, min(addX_num, len(all_X)))
        hints_internal['given_walls'].extend([[r,c] for r,c in add_A])
        hints_internal['given_islands'].extend([[r,c] for r,c in add_X])
        # 邻接约束增强（内部最多 4 条）
        candidates = [(r,c) for r in range(R) for c in range(C) if not isinstance(solution_grid[r][c], int)]
        random.shuffle(candidates)
        adjh = hints_internal.get('adjacency_hints', [])
        target_add = min(4, 2 + round_idx)
        for (r, c) in candidates[:target_add]:
            k = sum(1 for nr, nc in _neighbors(r, c) if _in_bounds(nr, nc, R, C) and solution_grid[nr][nc] == 'A')
            adjh.append([r, c, k])
        hints_internal['adjacency_hints'] = adjh
        if validate_unique(given_grid, rule_profile, hints_internal, timeout_sec=25):
            return True
    return False

def build_random_nurikabe(rows: int, cols: int, wall_density_pct: int, rule_profile: Dict[str, Any]) -> Dict[str, Grid]:
    R, C = rows, cols
    p = max(0.05, min(0.95, wall_density_pct / 100.0))
    for attempt in range(400):
        mask = _gen_A_mask_no_2x2(R, C, p)
        if rule_profile.get('enforce_wall_connected', False):
            if not _try_connect_wall(mask, max_steps=R*C*2):
                p = max(0.05, min(0.95, p*(0.9 if random.random()<0.5 else 1.1)))
                continue
        land_comps = _components(mask, False)
        if len(land_comps) == 0:
            rr, cc = random.randrange(R), random.randrange(C)
            mask[rr][cc] = False
            land_comps = _components(mask, False)
        mic = rule_profile.get('min_island_count', 0)
        if isinstance(mic, int) and mic > 0 and len(land_comps) < mic:
            p = max(0.05, min(0.95, p*0.9)); continue
        solution_grid = _solution_from_mask_and_numbers(mask, land_comps)
        numbers = [solution_grid[r][c] for r in range(R) for c in range(C) if isinstance(solution_grid[r][c], int)]
        mode = rule_profile.get('number_property_mode', 'none')
        ok_prop = True
        if mode == 'all_even': ok_prop = numbers and all(n%2==0 for n in numbers)
        elif mode == 'all_odd': ok_prop = numbers and all(n%2==1 for n in numbers)
        elif mode == 'all_prime': ok_prop = numbers and all(_is_prime(n) for n in numbers)
        elif mode == 'at_least_one_even': ok_prop = any(n%2==0 for n in numbers)
        elif mode == 'at_least_one_prime': ok_prop = any(_is_prime(n) for n in numbers)
        if not ok_prop: continue

        # 初始题面：仅保留数字
        given_grid: Grid = [['X' for _ in range(C)] for _ in range(R)]
        for r in range(R):
            for c in range(C):
                if isinstance(solution_grid[r][c], int):
                    given_grid[r][c] = solution_grid[r][c]

        # 玩家提示：受控弱提示
        hints_public: Dict[str, Any] = {}
        if rule_profile.get('enable_row_col_counts', False):
            row_counts, col_counts = _count_walls_grid(solution_grid)
            if random.random() < 0.5:
                hints_public['row_wall_counts'] = row_counts
            else:
                hints_public['col_wall_counts'] = col_counts
        if rule_profile.get('enable_given_walls', False):
            all_A = [(r,c) for r in range(R) for c in range(C) if solution_grid[r][c] == 'A']
            kA = max(1, int(len(all_A) * random.uniform(0.04, 0.08)))
            given_A = random.sample(all_A, min(kA, len(all_A)))
            hints_public['given_walls'] = [[r,c] for r,c in given_A]
            for r,c in given_A:
                if given_grid[r][c] == 'X': given_grid[r][c] = 'A'
        if rule_profile.get('enable_given_islands', False):
            all_X = [(r,c) for r in range(R) for c in range(C) if solution_grid[r][c] == 'X']
            kX = max(1, int(len(all_X) * random.uniform(0.04, 0.08)))
            given_X = random.sample(all_X, min(kX, len(all_X)))
            hints_public['given_islands'] = [[r,c] for r,c in given_X]
            for r,c in given_X:
                if not isinstance(given_grid[r][c], int): given_grid[r][c] = 'X'
        adjh_num = rule_profile.get('adjacency_hints_count', 0)
        if adjh_num > 0:
            candidates = [(r,c) for r in range(R) for c in range(C) if not isinstance(solution_grid[r][c], int)]
            random.shuffle(candidates)
            adjacency_hints: List[List[int]] = []
            for (r,c) in candidates[:adjh_num]:
                k = sum(1 for nr, nc in _neighbors(r, c) if _in_bounds(nr, nc, R, C) and solution_grid[nr][nc] == 'A')
                adjacency_hints.append([r,c,k])
            hints_public['adjacency_hints'] = adjacency_hints

        # 内部提示：强提示（不展示）
        hints_internal: Dict[str, Any] = {}
        # 先从玩家提示拷贝，再逐步增强
        for k in ['row_wall_counts','col_wall_counts','given_walls','given_islands','adjacency_hints']:
            if k in hints_public:
                hints_internal[k] = json.loads(json.dumps(hints_public[k]))  # 深拷贝
        # 保证唯一性
        if not _ensure_uniqueness_internal(given_grid, hints_internal, rule_profile, solution_grid, max_rounds=6):
            # 若仍未唯一，尝试进一步增强内部提示：两类计数 + 少量增补 A/X
            row_counts, col_counts = _count_walls_grid(solution_grid)
            hints_internal['row_wall_counts'] = row_counts
            hints_internal['col_wall_counts'] = col_counts
            all_A = [(r,c) for r in range(R) for c in range(C) if solution_grid[r][c] == 'A']
            all_X = [(r,c) for r in range(R) for c in range(C) if solution_grid[r][c] == 'X']
            add_A2 = random.sample(all_A, max(1, int(len(all_A) * 0.08)))
            add_X2 = random.sample(all_X, max(1, int(len(all_X) * 0.08)))
            hints_internal.setdefault('given_walls', []); hints_internal.setdefault('given_islands', [])
            hints_internal['given_walls'].extend([[r,c] for r,c in add_A2])
            hints_internal['given_islands'].extend([[r,c] for r,c in add_X2])
            candidates = [(r,c) for r in range(R) for c in range(C) if not isinstance(solution_grid[r][c], int)]
            random.shuffle(candidates)
            adjh = hints_internal.get('adjacency_hints', [])
            for (r,c) in candidates[:2]:
                k = sum(1 for nr, nc in _neighbors(r, c) if _in_bounds(nr, nc, R, C) and solution_grid[nr][nc] == 'A')
                adjh.append([r,c,k])
            hints_internal['adjacency_hints'] = adjh

        # 玩家提示校验（对外约束）
        if not validate_solution(given_grid, solution_grid, rule_profile, hints_public):
            continue
        # 内部唯一性快速校验
        if validate_unique(given_grid, rule_profile, hints_internal, timeout_sec=30):
            return {'solution_grid': solution_grid, 'given_grid': given_grid, 'hints_public': hints_public, 'hints_internal': hints_internal}
        # 调整密度继续尝试
        p = max(0.05, min(0.95, p*(0.95 if random.random()<0.5 else 1.05)))

    # 兜底：强内部提示保证唯一性，玩家提示仍受控弱提示
    mask = _gen_A_mask_no_2x2(R, C, p); land_comps = _components(mask, False)
    if len(land_comps) == 0:
        rr, cc = random.randrange(R), random.randrange(C)
        mask[rr][cc] = False; land_comps = _components(mask, False)
    solution_grid = _solution_from_mask_and_numbers(mask, land_comps)
    given_grid: Grid = [['X' for _ in range(C)] for _ in range(R)]
    for r in range(R):
        for c in range(C):
            if isinstance(solution_grid[r][c], int):
                given_grid[r][c] = solution_grid[r][c]
    # 玩家提示：只给一类计数 + 少量 A/X + 少量邻接
    hints_public: Dict[str, Any] = {}
    row_counts, col_counts = _count_walls_grid(solution_grid)
    if random.random() < 0.5:
        hints_public['row_wall_counts'] = row_counts
    else:
        hints_public['col_wall_counts'] = col_counts
    all_A = [(r,c) for r in range(R) for c in range(C) if solution_grid[r][c] == 'A']
    all_X = [(r,c) for r in range(R) for c in range(C) if solution_grid[r][c] == 'X']
    given_A = random.sample(all_A, max(1, int(len(all_A) * 0.06)))
    given_X = random.sample(all_X, max(1, int(len(all_X) * 0.06)))
    hints_public['given_walls'] = [[r,c] for r,c in given_A]
    hints_public['given_islands'] = [[r,c] for r,c in given_X]
    for r,c in given_A:
        if given_grid[r][c] == 'X': given_grid[r][c] = 'A'
    for r,c in given_X:
        if not isinstance(given_grid[r][c], int): given_grid[r][c] = 'X'
    adjacency_hints: List[List[int]] = []
    candidates = [(r,c) for r in range(R) for c in range(C) if not isinstance(solution_grid[r][c], int)]
    random.shuffle(candidates)
    for (r,c) in candidates[:2]:
        k = sum(1 for nr, nc in _neighbors(r, c) if _in_bounds(nr, nc, R, C) and solution_grid[nr][nc] == 'A')
        adjacency_hints.append([r,c,k])
    hints_public['adjacency_hints'] = adjacency_hints
    # 内部提示：两类计数 + 更多 A/X
    hints_internal: Dict[str, Any] = {
        'row_wall_counts': row_counts,
        'col_wall_counts': col_counts,
        'given_walls': [[r,c] for r in range(R) for c in range(C) if solution_grid[r][c] == 'A'],
        'given_islands': [[r,c] for r in range(R) for c in range(C) if solution_grid[r][c] == 'X'],
        'adjacency_hints': adjacency_hints
    }
    return {'solution_grid': solution_grid, 'given_grid': given_grid, 'hints_public': hints_public, 'hints_internal': hints_internal}

def gen_puzzle() -> Dict[str, Any]:
    rows = random.randint(5, 7); cols = random.randint(5, 7)
    wall_density_pct = random.randint(30, 60)
    rule_profile = build_rule_profile(rows, cols)
    inst = build_random_nurikabe(rows, cols, wall_density_pct, rule_profile)
    timeout_sec = random.randint(100, 180)
    # 外部再进行一次长时唯一性检测（内部提示，不向玩家暴露）
    validate_unique(inst['given_grid'], rule_profile, inst['hints_internal'], timeout_sec)
    return {
        'rows': rows, 'cols': cols, 'wall_density_pct': wall_density_pct,
        'rule_profile': rule_profile,
        'rule_desc_str': render_rule_desc(rule_profile),
        'given_grid': inst['given_grid'], 'solution_grid': inst['solution_grid'],
        'given_grid_str': grid_to_str(inst['given_grid']),
        'solution_grid_str': grid_to_str(inst['solution_grid']),
        'hints_public': inst['hints_public'], 'hint_desc_str': render_hints_desc(inst['hints_public']),
        'hints_internal': inst['hints_internal'],
        'unique_timeout_sec': timeout_sec,
    }