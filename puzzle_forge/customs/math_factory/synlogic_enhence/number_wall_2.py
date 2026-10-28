# number_wall_0.py
# -*- coding: utf-8 -*-
import random
import time
import json
import hashlib
from collections import deque

# ================================================================
# Helper: Grid utilities
# ================================================================
def _inb(r, c, R, C):
    return 0 <= r < R and 0 <= c < C

def _neighbors4(r, c):
    return [(r+1,c),(r-1,c),(r,c+1),(r,c-1)]

def _check_no_2x2_walls_by_assign(assign):
    R = len(assign)
    C = len(assign[0])
    for r in range(R-1):
        for c in range(C-1):
            if (assign[r][c] == -1 and assign[r+1][c] == -1 and
                assign[r][c+1] == -1 and assign[r+1][c+1] == -1):
                return False
    return True

def _check_no_2x2_walls_by_solution(solution):
    R = len(solution)
    C = len(solution[0])
    for r in range(R-1):
        for c in range(C-1):
            if (solution[r][c] == 0 and solution[r+1][c] == 0 and
                solution[r][c+1] == 0 and solution[r+1][c+1] == 0):
                return False
    return True

def _check_no_2x2_islands(solution):
    R = len(solution)
    C = len(solution[0])
    for r in range(R-1):
        for c in range(C-1):
            v00 = solution[r][c] != 0
            v10 = solution[r+1][c] != 0
            v01 = solution[r][c+1] != 0
            v11 = solution[r+1][c+1] != 0
            if v00 and v10 and v01 and v11:
                return False
    return True

def _check_no_2x2_islands_partial(assign):
    R = len(assign)
    C = len(assign[0])
    for r in range(R-1):
        for c in range(C-1):
            vals = [assign[r][c], assign[r+1][c], assign[r][c+1], assign[r+1][c+1]]
            if all(v is not None and v != -1 for v in vals):
                return False
    return True

def _check_walls_connected(solution):
    R = len(solution)
    C = len(solution[0])
    walls = [(r, c) for r in range(R) for c in range(C) if solution[r][c] == 0]
    if not walls:
        return False
    seen = [[False]*C for _ in range(R)]
    dq = deque([walls[0]])
    seen[walls[0][0]][walls[0][1]] = True
    cnt = 0
    while dq:
        r, c = dq.popleft()
        cnt += 1
        for nr, nc in _neighbors4(r, c):
            if _inb(nr, nc, R, C) and not seen[nr][nc] and solution[nr][nc] == 0:
                seen[nr][nc] = True
                dq.append((nr, nc))
    return cnt == len(walls)

# ================================================================
# Hints indexing and partial pruning support
# ================================================================
def _build_hint_index(rules_pack, R, C):
    hints = rules_pack.get('hints', {}) if rules_pack else {}
    idx = {
        'row': hints.get('row', []),
        'col': hints.get('col', []),
        'region': [],
        'neighbor_require': {},
        'anchor_adj': [],
        'parity_row': hints.get('parity_row', []),
        'parity_col': hints.get('parity_col', []),
        'global': hints.get('global', [])
    }
    for rh in hints.get('region', []):
        r0 = rh['r0']; c0 = rh['c0']; h = rh['h']; w = rh['w']
        cells = [(rr, cc) for rr in range(r0, r0+h) for cc in range(c0, c0+w) if _inb(rr, cc, R, C)]
        idx['region'].append({'cells': cells, 'kind': rh['kind'], 'op': rh['op'], 'val': rh['val']})
    for nh in hints.get('neighbor', []):
        ar = nh['r']; ac = nh['c']; d = nh['dir']
        dr = -1 if d == 'N' else (1 if d == 'S' else 0)
        dc = 1 if d == 'E' else (-1 if d == 'W' else 0)
        nr = ar + dr; nc = ac + dc
        if _inb(nr, nc, R, C):
            idx['neighbor_require'][(nr, nc)] = nh['type']
    for ah in hints.get('anchor_adj', []):
        idx['anchor_adj'].append(ah)
    return idx

def _partial_counts_feasible(assign, hint_index, islands, require_2x2_island=False):
    R = len(assign); C = len(assign[0])
    if not _check_no_2x2_walls_by_assign(assign):
        return False
    if require_2x2_island and not _check_no_2x2_islands_partial(assign):
        return False
    # Row constraints
    for h in hint_index['row']:
        idx = h['idx']
        unknowns = sum(1 for x in assign[idx] if x is None)
        if h['kind'] == 'walls':
            assigned = sum(1 for x in assign[idx] if x == -1)
        else:
            assigned = sum(1 for x in assign[idx] if (x is not None and x != -1))
        op = h['op']; val = h['val']
        if op == 'eq':
            if assigned > val: return False
            if assigned + unknowns < val: return False
        elif op == 'ge':
            if assigned + unknowns < val: return False
        elif op == 'le':
            if assigned > val: return False
    # Col constraints
    for h in hint_index['col']:
        idx = h['idx']
        col_vals = [assign[r][idx] for r in range(R)]
        unknowns = sum(1 for x in col_vals if x is None)
        if h['kind'] == 'walls':
            assigned = sum(1 for x in col_vals if x == -1)
        else:
            assigned = sum(1 for x in col_vals if (x is not None and x != -1))
        op = h['op']; val = h['val']
        if op == 'eq':
            if assigned > val: return False
            if assigned + unknowns < val: return False
        elif op == 'ge':
            if assigned + unknowns < val: return False
        elif op == 'le':
            if assigned > val: return False
    # Region constraints
    for rh in hint_index['region']:
        cells = rh['cells']
        vals = [assign[rr][cc] for (rr, cc) in cells]
        unknowns = sum(1 for x in vals if x is None)
        if rh['kind'] == 'walls':
            assigned = sum(1 for x in vals if x == -1)
        else:
            assigned = sum(1 for x in vals if (x is not None and x != -1))
        op = rh['op']; val = rh['val']
        if op == 'eq':
            if assigned > val: return False
            if assigned + unknowns < val: return False
        elif op == 'ge':
            if assigned + unknowns < val: return False
        elif op == 'le':
            if assigned > val: return False
    # Global constraints (partial)
    for gh in hint_index['global']:
        kind = gh['kind']; op = gh['op']; val = gh['val']
        unknowns = 0
        assigned = 0
        for r in range(R):
            for c in range(C):
                v = assign[r][c]
                if v is None:
                    unknowns += 1
                else:
                    if kind == 'walls':
                        if v == -1: assigned += 1
                    else:
                        if v != -1: assigned += 1
        if op == 'eq':
            if assigned > val: return False
            if assigned + unknowns < val: return False
        elif op == 'ge':
            if assigned + unknowns < val: return False
        elif op == 'le':
            if assigned > val: return False
    # Neighbor requirements
    for (rr, cc), typ in hint_index['neighbor_require'].items():
        v = assign[rr][cc]
        if v is None:
            continue
        if typ == 'must_wall' and v != -1:
            return False
        if typ == 'must_island' and v == -1:
            return False
    # Anchor adjacency constraints
    if hint_index['anchor_adj']:
        for ah in hint_index['anchor_adj']:
            ar = ah['r']; ac = ah['c']
            typ = ah['type']; op = ah['op']; val = ah['val']
            nb = _neighbors4(ar, ac)
            low = 0; unknowns = 0
            if typ == 'walls':
                for (nr, nc) in nb:
                    if not _inb(nr, nc, R, C): continue
                    v = assign[nr][nc]
                    if v == -1: low += 1
                    elif v is None: unknowns += 1
                high = low + unknowns
                if op == 'eq':
                    if low > val: return False
                    if high < val: return False
                elif op == 'ge':
                    if high < val: return False
                elif op == 'le':
                    if low > val: return False
            else:
                for (nr, nc) in nb:
                    if not _inb(nr, nc, R, C): continue
                    v = assign[nr][nc]
                    if v is None:
                        unknowns += 1
                    elif v != -1:
                        low += 1
                high = low + unknowns
                if op == 'eq':
                    if low > val: return False
                    if high < val: return False
                elif op == 'ge':
                    if high < val: return False
                elif op == 'le':
                    if low > val: return False
    return True

# ================================================================
# Solver core with constraints and time limit
# ================================================================
def _apply_hints_ok(solution, rules_pack):
    if not rules_pack:
        return True
    R = len(solution); C = len(solution[0])
    rules = rules_pack.get('rules', {})
    hints = rules_pack.get('hints', {})
    # Optional global rules
    if rules.get('forbid_island_2x2', False):
        if not _check_no_2x2_islands(solution):
            return False
    if rules.get('require_wall_connected', False):
        if not _check_walls_connected(solution):
            return False
    if rules.get('forbid_wall_2x2', False):
        if not _check_no_2x2_walls_by_solution(solution):
            return False
    # Row hints
    for h in hints.get('row', []):
        idx = h['idx']
        if not (0 <= idx < R):
            return False
        if h['kind'] == 'walls':
            cnt = sum(1 for x in solution[idx] if x == 0)
        else:
            cnt = sum(1 for x in solution[idx] if x != 0)
        op = h['op']; val = h['val']
        if op == 'eq' and not (cnt == val): return False
        if op == 'ge' and not (cnt >= val): return False
        if op == 'le' and not (cnt <= val): return False
    # Col hints
    for h in hints.get('col', []):
        idx = h['idx']
        if not (0 <= idx < C):
            return False
        col_vals = [solution[r][idx] for r in range(R)]
        if h['kind'] == 'walls':
            cnt = sum(1 for x in col_vals if x == 0)
        else:
            cnt = sum(1 for x in col_vals if x != 0)
        op = h['op']; val = h['val']
        if op == 'eq' and not (cnt == val): return False
        if op == 'ge' and not (cnt >= val): return False
        if op == 'le' and not (cnt <= val): return False
    # Region hints
    for rh in hints.get('region', []):
        r0 = rh['r0']; c0 = rh['c0']; h = rh['h']; w = rh['w']
        cells = [(rr, cc) for rr in range(r0, r0+h) for cc in range(c0, c0+w) if _inb(rr, cc, R, C)]
        if rh['kind'] == 'walls':
            cnt = sum(1 for (rr, cc) in cells if solution[rr][cc] == 0)
        else:
            cnt = sum(1 for (rr, cc) in cells if solution[rr][cc] != 0)
        op = rh['op']; val = rh['val']
        if op == 'eq' and not (cnt == val): return False
        if op == 'ge' and not (cnt >= val): return False
        if op == 'le' and not (cnt <= val): return False
    # Parity hints
    for ph in hints.get('parity_row', []):
        idx = ph['idx']
        if not (0 <= idx < R): return False
        if ph['kind'] == 'walls':
            cnt = sum(1 for x in solution[idx] if x == 0)
        else:
            cnt = sum(1 for x in solution[idx] if x != 0)
        par_ok = (cnt % 2 == 0) if ph['par'] == 'even' else (cnt % 2 == 1)
        if not par_ok: return False
    for ph in hints.get('parity_col', []):
        idx = ph['idx']
        if not (0 <= idx < C): return False
        col_vals = [solution[r][idx] for r in range(R)]
        if ph['kind'] == 'walls':
            cnt = sum(1 for x in col_vals if x == 0)
        else:
            cnt = sum(1 for x in col_vals if x != 0)
        par_ok = (cnt % 2 == 0) if ph['par'] == 'even' else (cnt % 2 == 1)
        if not par_ok: return False
    # Anchor adjacency counts
    for ah in hints.get('anchor_adj', []):
        ar = ah['r']; ac = ah['c']
        if not _inb(ar, ac, R, C): return False
        nb = _neighbors4(ar, ac)
        if ah['type'] == 'walls':
            cnt = 0
            for (nr, nc) in nb:
                if _inb(nr, nc, R, C) and solution[nr][nc] == 0:
                    cnt += 1
        else:
            cnt = 0
            for (nr, nc) in nb:
                if _inb(nr, nc, R, C) and solution[nr][nc] != 0:
                    cnt += 1
        op = ah['op']; val = ah['val']
        if op == 'eq' and not (cnt == val): return False
        if op == 'ge' and not (cnt >= val): return False
        if op == 'le' and not (cnt <= val): return False
    # Neighbor must constraints
    for nh in hints.get('neighbor', []):
        ar = nh['r']; ac = nh['c']; d = nh['dir']
        dr = -1 if d == 'N' else (1 if d == 'S' else 0)
        dc = 1 if d == 'E' else (-1 if d == 'W' else 0)
        nr = ar + dr; nc = ac + dc
        if not _inb(nr, nc, R, C): return False
        if nh['type'] == 'must_wall':
            if not (solution[nr][nc] == 0): return False
        else:
            if not (solution[nr][nc] != 0): return False
    # Global hints
    for gh in hints.get('global', []):
        kind = gh['kind']; op = gh['op']; val = gh['val']
        if kind == 'walls':
            cnt = sum(1 for r in range(R) for c in range(C) if solution[r][c] == 0)
        else:
            cnt = sum(1 for r in range(R) for c in range(C) if solution[r][c] != 0)
        if op == 'eq' and not (cnt == val): return False
        if op == 'ge' and not (cnt >= val): return False
        if op == 'le' and not (cnt <= val): return False
    return True

def _solve_and_count(clue, rules_pack=None, limit=2, time_limit_sec=45.0):
    start_time = time.time()
    R = len(clue)
    C = len(clue[0])
    # Gather islands
    islands = []
    for r in range(R):
        for c in range(C):
            if isinstance(clue[r][c], int) and clue[r][c] >= 2:
                islands.append((r, c, int(clue[r][c])))
    K = len(islands)
    if K == 0:
        return 0, None
    # assignment grid
    assign = [[None]*C for _ in range(R)]
    need = []
    for i, (r, c, v) in enumerate(islands):
        assign[r][c] = i
        need.append(v - 1)
    to_fill = [(r, c) for r in range(R) for c in range(C) if clue[r][c] == -1]

    hint_index = _build_hint_index(rules_pack, R, C)
    rules = rules_pack.get('rules', {}) if rules_pack else {}
    require_2x2_island = rules.get('forbid_island_2x2', False)

    # Pre-fill from neighbor hints: only must_wall; must_island 不预填
    if rules_pack:
        for nh in rules_pack.get('hints', {}).get('neighbor', []):
            ar = nh['r']; ac = nh['c']; d = nh['dir']
            dr = -1 if d == 'N' else (1 if d == 'S' else 0)
            dc = 1 if d == 'E' else (-1 if d == 'W' else 0)
            nr = ar + dr; nc = ac + dc
            if not _inb(nr, nc, R, C): 
                return 0, None
            if assign[nr][nc] is None:
                if nh['type'] == 'must_wall':
                    assign[nr][nc] = -1

    # Feasibility after pre-fill
    if not _partial_counts_feasible(assign, hint_index, islands, require_2x2_island):
        return 0, None

    def potential_ok():
        for i, (sr, sc, target) in enumerate(islands):
            seen = [[False]*C for _ in range(R)]
            dq = deque()
            dq.append((sr, sc))
            seen[sr][sc] = True
            cnt = 0
            while dq:
                rr, cc = dq.popleft()
                cnt += 1
                for nr, nc in _neighbors4(rr, cc):
                    if not _inb(nr, nc, R, C):
                        continue
                    if seen[nr][nc]:
                        continue
                    a = assign[nr][nc]
                    if a == -1:
                        continue
                    if (a is not None) and (a != i):
                        continue
                    seen[nr][nc] = True
                    dq.append((nr, nc))
            if cnt < target:
                return False
        return True

    def separation_ok(r, c, set_to):
        if set_to == -1:
            return True
        adjacent_same = False
        for nr, nc in _neighbors4(r, c):
            if not _inb(nr, nc, R, C):
                continue
            a = assign[nr][nc]
            if a is None:
                continue
            if a != -1 and a != set_to:
                return False
            if a == set_to:
                adjacent_same = True
        return adjacent_same

    def pick_next():
        best = None
        best_score = None
        for (r, c) in to_fill:
            if assign[r][c] is not None:
                continue
            poss = 1  # wall
            adj_islands = 0
            for i in range(K):
                if need[i] <= 0:
                    continue
                if separation_ok(r, c, i):
                    # 粗略前向检查
                    assign[r][c] = i
                    need[i] -= 1
                    ok_quick = _partial_counts_feasible(assign, hint_index, islands, require_2x2_island)
                    need[i] += 1
                    assign[r][c] = None
                    if ok_quick:
                        poss += 1
                        adj_islands += 1
            score = (poss, -adj_islands, r, c)
            if best is None or score < best_score:
                best = (r, c)
                best_score = score
        return best

    sol_count = 0
    first_solution = None

    def record_solution():
        nonlocal sol_count, first_solution
        bak = []
        ok = True
        for (r, c) in to_fill:
            if assign[r][c] is None:
                assign[r][c] = -1
                bak.append((r, c))
                if not _check_no_2x2_walls_by_assign(assign):
                    ok = False
                    break
        if ok and potential_ok():
            out = [[0]*C for _ in range(R)]
            for r in range(R):
                for c in range(C):
                    if clue[r][c] >= 2:
                        out[r][c] = clue[r][c]
                    else:
                        a = assign[r][c]
                        if a == -1 or a is None:
                            out[r][c] = 0
                        else:
                            out[r][c] = 1
            # 硬规则检查
            if _check_no_2x2_walls_by_solution(out):
                if _apply_hints_ok(out, rules_pack):
                    sol_count += 1
                    if first_solution is None:
                        first_solution = [row[:] for row in out]
        for rr, cc in bak:
            assign[rr][cc] = None

    def dfs():
        nonlocal sol_count, first_solution
        if time.time() - start_time > time_limit_sec:
            return
        if sol_count >= limit:
            return
        if all(n == 0 for n in need):
            if _partial_counts_feasible(assign, hint_index, islands, require_2x2_island):
                record_solution()
            return
        nxt = pick_next()
        if nxt is None:
            return
        r, c = nxt

        # Try wall
        assign[r][c] = -1
        if _partial_counts_feasible(assign, hint_index, islands, require_2x2_island) and potential_ok():
            dfs()
            if sol_count >= limit or time.time() - start_time > time_limit_sec:
                assign[r][c] = None
                return
        assign[r][c] = None

        # Try islands
        for i in range(K):
            if need[i] <= 0:
                continue
            if not separation_ok(r, c, i):
                continue
            assign[r][c] = i
            need[i] -= 1
            if _partial_counts_feasible(assign, hint_index, islands, require_2x2_island) and potential_ok():
                dfs()
                if sol_count >= limit or time.time() - start_time > time_limit_sec:
                    need[i] += 1
                    assign[r][c] = None
                    return
            need[i] += 1
            assign[r][c] = None

    if not potential_ok():
        return 0, None

    dfs()
    return sol_count, first_solution

# ================================================================
# Generator: base island placement
# ================================================================
def _random_island_sizes(rows, cols):
    total = rows * cols
    low = max(6, int(total * 0.30))
    high = max(low + 2, int(total * 0.55))
    target_area = random.randint(low, high)
    sizes = []
    remaining = target_area
    cap = max(2, min(7, (rows + cols)//2))
    while remaining >= 2:
        if remaining == 3:
            s = 3
        else:
            s_max = min(cap, remaining)
            s = random.randint(2, s_max)
        sizes.append(s)
        remaining -= s
    if remaining == 1:
        if sizes:
            idx = random.randrange(len(sizes))
            sizes[idx] += 1
            remaining = 0
        else:
            sizes = [2]
            remaining = 0
    random.shuffle(sizes)
    if len(sizes) < 3 and sum(sizes) >= 6:
        idx = None
        for i, v in enumerate(sizes):
            if v >= 4:
                idx = i
                break
        if idx is not None:
            v = sizes.pop(idx)
            cut = random.randint(2, v - 2)
            sizes.append(cut)
            sizes.append(v - cut)
    return sizes

def _place_islands(rows, cols, sizes, max_tries=180):
    for _ in range(max_tries):
        owner = [[-1]*cols for _ in range(rows)]
        ok = True
        for i, size in enumerate(sizes):
            seeds = []
            for r in range(rows):
                for c in range(cols):
                    if owner[r][c] != -1:
                        continue
                    bad = False
                    for nr, nc in _neighbors4(r, c):
                        if _inb(nr, nc, rows, cols) and owner[nr][nc] >= 0:
                            bad = True
                            break
                    if not bad:
                        seeds.append((r, c))
            if not seeds:
                ok = False
                break
            sr, sc = random.choice(seeds)
            owner[sr][sc] = i
            cells = [(sr, sc)]
            for _step in range(size - 1):
                frontier = set()
                for (r, c) in cells:
                    for nr, nc in _neighbors4(r, c):
                        if not _inb(nr, nc, rows, cols):
                            continue
                        if owner[nr][nc] != -1:
                            continue
                        bad = False
                        for xr, xc in _neighbors4(nr, nc):
                            if _inb(xr, xc, rows, cols):
                                if owner[xr][xc] >= 0 and owner[xr][xc] != i:
                                    bad = True
                                    break
                        if not bad:
                            frontier.add((nr, nc))
                if not frontier:
                    ok = False
                    break
                nr, nc = random.choice(list(frontier))
                owner[nr][nc] = i
                cells.append((nr, nc))
            if not ok:
                break
        if not ok:
            continue
        solution = [[0]*cols for _ in range(rows)]
        island_cells = [[] for _ in sizes]
        for r in range(rows):
            for c in range(cols):
                if owner[r][c] >= 0:
                    island_cells[owner[r][c]].append((r, c))
        for i, cells in enumerate(island_cells):
            ar, ac = random.choice(cells)
            for (r, c) in cells:
                solution[r][c] = 1
            solution[ar][ac] = len(cells)
        # 硬规则过滤：2x2 全墙、2x2 全岛、墙四连通
        if not _check_no_2x2_walls_by_solution(solution):
            continue
        if not _check_no_2x2_islands(solution):
            continue
        if not _check_walls_connected(solution):
            continue
        return solution
    return None

def _make_clue_from_solution(solution):
    R = len(solution)
    C = len(solution[0])
    clue = [[-1]*C for _ in range(R)]
    for r in range(R):
        for c in range(C):
            v = solution[r][c]
            if v >= 2:
                clue[r][c] = v
            else:
                clue[r][c] = -1
    return clue

# ================================================================
# Rules/hints generation, rendering, and uniqueness enforcement
# ================================================================
def _collect_anchors(solution):
    anchors = []
    R = len(solution); C = len(solution[0])
    for r in range(R):
        for c in range(C):
            if solution[r][c] >= 2:
                anchors.append((r, c))
    return anchors

def _constraint_nontrivial(kind, op, val, span_size):
    if op == 'eq':
        if val == 0 or val == span_size:
            return False
    elif op == 'ge':
        if val <= 0 or val >= span_size:
            return False
    elif op == 'le':
        if val >= span_size or val <= 0:
            return False
    return True

def _gen_candidate_hints(solution, max_per_type=3):
    R = len(solution); C = len(solution[0])
    pool_row = []
    pool_col = []
    pool_nei = []
    pool_region = []
    pool_parity_row = []
    pool_parity_col = []
    pool_anchor_adj = []
    pool_global = []
    rows_idx = list(range(R))
    cols_idx = list(range(C))
    random.shuffle(rows_idx)
    random.shuffle(cols_idx)
    # 行提示：倾向使用ge/le，且避免显见 eq=0/eq=span
    for ridx in rows_idx[:max_per_type]:
        walls_cnt = sum(1 for x in solution[ridx] if x == 0)
        islands_cnt = sum(1 for x in solution[ridx] if x != 0)
        op = random.choices(['eq','ge','le'], weights=[1,2,2])[0]
        if random.random() < 0.5:
            if _constraint_nontrivial('walls', op, walls_cnt, C):
                pool_row.append({'idx': ridx, 'kind': 'walls', 'op': op, 'val': walls_cnt})
        else:
            if _constraint_nontrivial('islands', op, islands_cnt, C):
                pool_row.append({'idx': ridx, 'kind': 'islands', 'op': op, 'val': islands_cnt})
        kind = 'walls' if random.random() < 0.5 else 'islands'
        cnt = walls_cnt if kind == 'walls' else islands_cnt
        par = 'even' if cnt % 2 == 0 else 'odd'
        pool_parity_row.append({'idx': ridx, 'kind': kind, 'par': par})
    # 列提示：倾向使用ge/le，避免显见 eq=0/eq=span
    for cidx in cols_idx[:max_per_type]:
        col_vals = [solution[r][cidx] for r in range(R)]
        walls_cnt = sum(1 for x in col_vals if x == 0)
        islands_cnt = sum(1 for x in col_vals if x != 0)
        op = random.choices(['eq','ge','le'], weights=[1,2,2])[0]
        if random.random() < 0.5:
            if _constraint_nontrivial('walls', op, walls_cnt, R):
                pool_col.append({'idx': cidx, 'kind': 'walls', 'op': op, 'val': walls_cnt})
        else:
            if _constraint_nontrivial('islands', op, islands_cnt, R):
                pool_col.append({'idx': cidx, 'kind': 'islands', 'op': op, 'val': islands_cnt})
        kind = 'walls' if random.random() < 0.5 else 'islands'
        cnt = walls_cnt if kind == 'walls' else islands_cnt
        par = 'even' if cnt % 2 == 0 else 'odd'
        pool_parity_col.append({'idx': cidx, 'kind': kind, 'par': par})
    # 锚点邻格
    anchors = _collect_anchors(solution)
    random.shuffle(anchors)
    dirs = ['N','S','E','W']
    for (ar, ac) in anchors[:max_per_type]:
        d = random.choice(dirs)
        dr = -1 if d == 'N' else (1 if d == 'S' else 0)
        dc = 1 if d == 'E' else (-1 if d == 'W' else 0)
        nr = ar + dr; nc = ac + dc
        if not _inb(nr, nc, R, C):
            continue
        typ = 'must_wall' if solution[nr][nc] == 0 else 'must_island'
        pool_nei.append({'r': ar, 'c': ac, 'dir': d, 'type': typ})
    # 子矩形区域提示（2x2/3x3/2x3等）
    rect_candidates = []
    for h in range(2, min(4, R+1)):
        for w in range(2, min(4, C+1)):
            for r0 in range(0, R - h + 1):
                for c0 in range(0, C - w + 1):
                    rect_candidates.append((r0, c0, h, w))
    random.shuffle(rect_candidates)
    for (r0, c0, h, w) in rect_candidates[:max_per_type*2]:
        cells = [(rr, cc) for rr in range(r0, r0+h) for cc in range(c0, c0+w)]
        walls_cnt = sum(1 for (rr, cc) in cells if solution[rr][cc] == 0)
        islands_cnt = sum(1 for (rr, cc) in cells if solution[rr][cc] != 0)
        kind = 'walls' if random.random() < 0.5 else 'islands'
        val = walls_cnt if kind == 'walls' else islands_cnt
        op = random.choices(['eq','ge','le'], weights=[1,2,2])[0]
        if _constraint_nontrivial(kind, op, val, h*w):
            pool_region.append({'r0': r0, 'c0': c0, 'h': h, 'w': w, 'kind': kind, 'op': op, 'val': val})
    # 锚点四邻计数提示
    for (ar, ac) in anchors[:max_per_type]:
        nb = _neighbors4(ar, ac)
        walls_cnt = 0
        islands_cnt = 0
        for (nr, nc) in nb:
            if _inb(nr, nc, R, C):
                if solution[nr][nc] == 0:
                    walls_cnt += 1
                else:
                    islands_cnt += 1
        if random.random() < 0.5:
            kind = 'walls'; val = walls_cnt
        else:
            kind = 'islands'; val = islands_cnt
        op = random.choices(['eq','ge','le'], weights=[1,2,2])[0]
        pool_anchor_adj.append({'r': ar, 'c': ac, 'type': kind, 'op': op, 'val': val})
    # 全局提示（非显见）
    walls_total = sum(1 for r in range(R) for c in range(C) if solution[r][c] == 0)
    islands_total = R*C - walls_total
    op_w = random.choice(['ge','le'])
    op_i = random.choice(['ge','le'])
    val_w = max(0, min(R*C, walls_total + random.choice([-1,0,1])))
    val_i = max(0, min(R*C, islands_total + random.choice([-1,0,1])))
    pool_global.append({'kind': 'walls', 'op': op_w, 'val': val_w})
    pool_global.append({'kind': 'islands', 'op': op_i, 'val': val_i})
    return pool_row, pool_col, pool_nei, pool_region, pool_parity_row, pool_parity_col, pool_anchor_adj, pool_global

def _render_hint_text(rows, cols, rules_pack):
    rules = rules_pack.get('rules', {})
    hints = rules_pack.get('hints', {})
    parts = []
    # 环境与核心规则
    parts.append('所有已知锚点位置与数值固定，不可更改；除题面给出的锚点外，其余格不得为数字锚点（k≥2）；每个岛恰含一个数字锚点且其岛大小等于该数字；同一岛的所有格须四连通；不同岛必须由墙隔开（不同岛的格子不能正交相邻）；任意 2×2 子块不可全为墙')
    if rules.get('require_wall_connected', False):
        parts.append('所有墙必须四连通（海洋为一个整体）')
    if rules.get('forbid_island_2x2', False):
        parts.append('不允许出现 2×2 子块全为岛格（包含锚点）')
    # 计数与结构提示
    for h in hints.get('row', []):
        kind_txt = '墙格' if h['kind'] == 'walls' else '岛格（含锚点）'
        op_txt = '恰好' if h['op'] == 'eq' else ('不少于' if h['op'] == 'ge' else '不多于')
        parts.append(f'第 {h["idx"]+1} 行的{kind_txt}{op_txt} {h["val"]} 个')
    for h in hints.get('col', []):
        kind_txt = '墙格' if h['kind'] == 'walls' else '岛格（含锚点）'
        op_txt = '恰好' if h['op'] == 'eq' else ('不少于' if h['op'] == 'ge' else '不多于')
        parts.append(f'第 {h["idx"]+1} 列的{kind_txt}{op_txt} {h["val"]} 个')
    for rh in hints.get('region', []):
        kind_txt = '墙格' if rh['kind'] == 'walls' else '岛格（含锚点）'
        op_txt = '恰好' if rh['op'] == 'eq' else ('不少于' if rh['op'] == 'ge' else '不多于')
        r1 = rh['r0'] + 1; r2 = rh['r0'] + rh['h']
        c1 = rh['c0'] + 1; c2 = rh['c0'] + rh['w']
        parts.append(f'子矩形区域（行 {r1} 至 {r2}，列 {c1} 至 {c2}）的{kind_txt}{op_txt} {rh["val"]} 个')
    for ph in hints.get('parity_row', []):
        kind_txt = '墙格' if ph['kind'] == 'walls' else '岛格（含锚点）'
        parts.append(f'第 {ph["idx"]+1} 行的{kind_txt}数量为{("偶数" if ph["par"]=="even" else "奇数")}')
    for ph in hints.get('parity_col', []):
        kind_txt = '墙格' if ph['kind'] == 'walls' else '岛格（含锚点）'
        parts.append(f'第 {ph["idx"]+1} 列的{kind_txt}数量为{("偶数" if ph["par"]=="even" else "奇数")}')
    for ah in hints.get('anchor_adj', []):
        typ_txt = '墙格' if ah['type'] == 'walls' else '岛格（含锚点）'
        op_txt = '恰好' if ah['op'] == 'eq' else ('不少于' if ah['op'] == 'ge' else '不多于')
        parts.append(f'位于第 {ah["r"]+1} 行第 {ah["c"]+1} 列的锚点的四邻{typ_txt}{op_txt} {ah["val"]} 个（不区分所属岛）')
    for h in hints.get('neighbor', []):
        dir_txt = {'N':'北','S':'南','E':'东','W':'西'}[h['dir']]
        if h['type'] == 'must_wall':
            parts.append(f'位于第 {h["r"]+1} 行第 {h["c"]+1} 列的锚点的{dir_txt}侧邻格必须是墙')
        else:
            parts.append(f'位于第 {h["r"]+1} 行第 {h["c"]+1} 列的锚点的{dir_txt}侧邻格必须是岛格（不要求该邻格属于该锚点所在的岛）')
    for gh in hints.get('global', []):
        kind_txt = '墙格' if gh['kind'] == 'walls' else '岛格（含锚点）'
        op_txt = '恰好' if gh['op'] == 'eq' else ('不少于' if gh['op'] == 'ge' else '不多于')
        parts.append(f'全局{kind_txt}{op_txt} {gh["val"]} 个')
    parts.append('行列与坐标均从1开始计数')
    return '；'.join(parts)

def _pack_from_chosen(rules, chosen):
    hints = {
        'row': list(chosen.get('row', [])),
        'col': list(chosen.get('col', [])),
        'neighbor': list(chosen.get('neighbor', [])),
        'region': list(chosen.get('region', [])),
        'parity_row': list(chosen.get('parity_row', [])),
        'parity_col': list(chosen.get('parity_col', [])),
        'anchor_adj': list(chosen.get('anchor_adj', [])),
        'global': list(chosen.get('global', []))
    }
    return {'rules': dict(rules), 'hints': hints}

def _solution_digest(sol):
    s = json.dumps(sol, separators=(',',':'))
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

# 显见线索合取过滤
def _has_apparent_combo(hints, R, C):
    row_le1 = set()
    row_odd = set()
    for h in hints.get('row', []):
        if h['kind'] == 'islands' and h['op'] == 'le' and h['val'] == 1:
            row_le1.add(h['idx'])
    for ph in hints.get('parity_row', []):
        if ph['kind'] == 'islands' and ph['par'] == 'odd':
            row_odd.add(ph['idx'])
    if row_le1 & row_odd:
        return True
    col_le1 = set()
    col_odd = set()
    for h in hints.get('col', []):
        if h['kind'] == 'islands' and h['op'] == 'le' and h['val'] == 1:
            col_le1.add(h['idx'])
    for ph in hints.get('parity_col', []):
        if ph['kind'] == 'islands' and ph['par'] == 'odd':
            col_odd.add(ph['idx'])
    return len(col_le1 & col_odd) > 0

def _is_nontrivial_eq(count, span):
    return 0 < count < span

def _row_col_counts_hints(sol):
    R = len(sol); C = len(sol[0])
    hints = {'row': [], 'col': []}
    # 仅对非平凡计数生成 eq
    for r in range(R):
        walls_cnt = sum(1 for x in sol[r] if x == 0)
        if _is_nontrivial_eq(walls_cnt, C):
            hints['row'].append({'idx': r, 'kind': 'walls', 'op': 'eq', 'val': walls_cnt})
    for c in range(C):
        col_vals = [sol[r][c] for r in range(R)]
        walls_cnt = sum(1 for v in col_vals if v == 0)
        if _is_nontrivial_eq(walls_cnt, R):
            hints['col'].append({'idx': c, 'kind': 'walls', 'op': 'eq', 'val': walls_cnt})
    return hints

def _all_anchor_neighbor_hints(sol, max_dirs_per_anchor=2):
    R = len(sol); C = len(sol[0])
    neighbor_hints = []
    anchors = _collect_anchors(sol)
    for (ar, ac) in anchors:
        dirs = ['N','S','E','W']
        random.shuffle(dirs)
        used = 0
        for d in dirs:
            if used >= max_dirs_per_anchor:
                break
            dr = -1 if d == 'N' else (1 if d == 'S' else 0)
            dc = 1 if d == 'E' else (-1 if d == 'W' else 0)
            nr = ar + dr; nc = ac + dc
            if _inb(nr, nc, R, C):
                typ = 'must_wall' if sol[nr][nc] == 0 else 'must_island'
                neighbor_hints.append({'r': ar, 'c': ac, 'dir': d, 'type': typ})
                used += 1
    return neighbor_hints

def _add_2x2_regions_eq(sol, hints):
    R = len(sol); C = len(sol[0])
    regions = []
    for r in range(R-1):
        for c in range(C-1):
            cells = [(r,c),(r+1,c),(r,c+1),(r+1,c+1)]
            walls_cnt = sum(1 for (rr, cc) in cells if sol[rr][cc] == 0)
            regions.append({'r0': r, 'c0': c, 'h': 2, 'w': 2, 'kind': 'walls', 'op': 'eq', 'val': walls_cnt})
    hints['region'] = hints.get('region', []) + regions

#（保留定义但不再使用）
def _add_1x1_regions_eq(sol, hints):
    R = len(sol); C = len(sol[0])
    regions = []
    for r in range(R):
        for c in range(C):
            if sol[r][c] == 0:
                regions.append({'r0': r, 'c0': c, 'h': 1, 'w': 1, 'kind': 'walls', 'op': 'eq', 'val': 1})
            else:
                regions.append({'r0': r, 'c0': c, 'h': 1, 'w': 1, 'kind': 'islands', 'op': 'eq', 'val': 1})
    hints['region'] = hints.get('region', []) + regions

def _build_ultra_unique_pack(clue, sol, base_rules, time_budget=35.0):
    t0 = time.time()
    rules = dict(base_rules)
    hints = {'row': [], 'col': [], 'neighbor': [], 'region': [], 'parity_row': [], 'parity_col': [], 'anchor_adj': [], 'global': []}
    # 非平凡行列等式
    rc = _row_col_counts_hints(sol)
    hints['row'] = rc['row']
    hints['col'] = rc['col']
    # 为平凡行/列补充奇偶（避免显见等式）
    R = len(sol); C = len(sol[0])
    eq_rows = {h['idx'] for h in hints['row']}
    eq_cols = {h['idx'] for h in hints['col']}
    for r in range(R):
        if r in eq_rows:
            continue
        walls_cnt = sum(1 for x in sol[r] if x == 0)
        kind = 'walls'
        par = 'even' if walls_cnt % 2 == 0 else 'odd'
        hints['parity_row'].append({'idx': r, 'kind': kind, 'par': par})
    for c in range(C):
        if c in eq_cols:
            continue
        col_vals = [sol[r][c] for r in range(R)]
        walls_cnt = sum(1 for v in col_vals if v == 0)
        kind = 'walls'
        par = 'even' if walls_cnt % 2 == 0 else 'odd'
        hints['parity_col'].append({'idx': c, 'kind': kind, 'par': par})
    # 全局墙数恰好
    walls_total = sum(1 for r in range(len(sol)) for c in range(len(sol[0])) if sol[r][c] == 0)
    hints['global'].append({'kind': 'walls', 'op': 'eq', 'val': walls_total})
    # 每锚点最多两个方向邻格要求
    hints['neighbor'] = _all_anchor_neighbor_hints(sol, max_dirs_per_anchor=2)
    pack = {'rules': rules, 'hints': hints}
    cnt, s1 = _solve_and_count(clue, pack, limit=2, time_limit_sec=max(1.0, time_budget - (time.time()-t0)))
    if cnt == 1 and s1 == sol:
        pack['digest'] = _solution_digest(sol)
        return pack
    # 加强：2×2 区域等式
    _add_2x2_regions_eq(sol, hints)
    cnt, s2 = _solve_and_count(clue, pack, limit=2, time_limit_sec=max(1.0, time_budget - (time.time()-t0)))
    if cnt == 1 and s2 == sol:
        pack['digest'] = _solution_digest(sol)
        return pack
    return None

def _build_super_strong_unique_pack(clue, sol, base_rules, time_budget=50.0):
    t0 = time.time()
    rules = dict(base_rules)
    hints = {'row': [], 'col': [], 'neighbor': [], 'region': [], 'parity_row': [], 'parity_col': [], 'anchor_adj': [], 'global': []}
    # 非平凡行列墙数恰好
    rc = _row_col_counts_hints(sol)
    hints['row'] = rc['row']
    hints['col'] = rc['col']
    # 全局墙数恰好
    walls_total = sum(1 for r in range(len(sol)) for c in range(len(sol[0])) if sol[r][c] == 0)
    hints['global'].append({'kind': 'walls', 'op': 'eq', 'val': walls_total})
    # 行列奇偶（覆盖约半数）
    R = len(sol); C = len(sol[0])
    rows_pick = random.sample(range(R), k=max(1, (R+1)//2))
    cols_pick = random.sample(range(C), k=max(1, (C+1)//2))
    for r in rows_pick:
        walls_cnt = sum(1 for x in sol[r] if x == 0)
        kind = 'walls'
        par = 'even' if walls_cnt % 2 == 0 else 'odd'
        hints['parity_row'].append({'idx': r, 'kind': kind, 'par': par})
    for c in cols_pick:
        col_vals = [sol[r][c] for r in range(R)]
        walls_cnt = sum(1 for v in col_vals if v == 0)
        kind = 'walls'
        par = 'even' if walls_cnt % 2 == 0 else 'odd'
        hints['parity_col'].append({'idx': c, 'kind': kind, 'par': par})
    # 所有锚点：每个最多两向邻格 + 四邻数量恰好
    hints['neighbor'] = _all_anchor_neighbor_hints(sol, max_dirs_per_anchor=2)
    anchors = _collect_anchors(sol)
    for (ar, ac) in anchors:
        nb = _neighbors4(ar, ac)
        walls_cnt = 0; islands_cnt = 0
        for (nr, nc) in nb:
            if _inb(nr, nc, R, C):
                if sol[nr][nc] == 0:
                    walls_cnt += 1
                else:
                    islands_cnt += 1
        hints['anchor_adj'].append({'r': ar, 'c': ac, 'type': 'walls', 'op': 'eq', 'val': walls_cnt})
        hints['anchor_adj'].append({'r': ar, 'c': ac, 'type': 'islands', 'op': 'eq', 'val': islands_cnt})
    # 全 2x2 子矩形约束（不使用 1x1）
    _add_2x2_regions_eq(sol, hints)
    pack = {'rules': rules, 'hints': hints}
    cnt, s1 = _solve_and_count(clue, pack, limit=2, time_limit_sec=max(1.0, time_budget - (time.time()-t0)))
    if cnt == 1 and s1 == sol:
        pack['digest'] = _solution_digest(sol)
        return pack
    return None

# ================================================================
# Missing function implemented: force unique pack builder
# ================================================================
def _force_unique(clue, sol, base_rules, time_limit_sec=30.0):
    t0 = time.time()
    rules = dict(base_rules)
    R = len(sol); C = len(sol[0])

    def check_and_pack(hints):
        pack = {'rules': rules, 'hints': hints}
        cnt, s = _solve_and_count(clue, pack, limit=2, time_limit_sec=max(1.0, time_limit_sec - (time.time() - t0)))
        if cnt == 1 and s == sol:
            pack['digest'] = _solution_digest(sol)
            return pack
        return None

    # Step 1: 基础包（非平凡行列等式 + 全局墙数恰好 + 每锚至多两向邻格）
    hints = {'row': [], 'col': [], 'neighbor': [], 'region': [], 'parity_row': [], 'parity_col': [], 'anchor_adj': [], 'global': []}
    rc = _row_col_counts_hints(sol)
    hints['row'] = rc['row']
    hints['col'] = rc['col']
    walls_total = sum(1 for r in range(R) for c in range(C) if sol[r][c] == 0)
    hints['global'].append({'kind': 'walls', 'op': 'eq', 'val': walls_total})
    hints['neighbor'] = _all_anchor_neighbor_hints(sol, max_dirs_per_anchor=2)

    pack_try = check_and_pack(hints)
    if pack_try is not None:
        return pack_try

    # Step 2: 行列奇偶（补齐未覆盖行/列）
    eq_rows = {h['idx'] for h in hints['row']}
    eq_cols = {h['idx'] for h in hints['col']}
    for r in range(R):
        if r in eq_rows:
            continue
        cnt_w = sum(1 for x in sol[r] if x == 0)
        par = 'even' if cnt_w % 2 == 0 else 'odd'
        hints['parity_row'].append({'idx': r, 'kind': 'walls', 'par': par})
    for c in range(C):
        if c in eq_cols:
            continue
        cnt_w = sum(1 for rr in range(R) if sol[rr][c] == 0)
        par = 'even' if cnt_w % 2 == 0 else 'odd'
        hints['parity_col'].append({'idx': c, 'kind': 'walls', 'par': par})

    pack_try = check_and_pack(hints)
    if pack_try is not None:
        return pack_try

    # Step 3: 全量 2×2 子矩形墙数等式
    _add_2x2_regions_eq(sol, hints)
    pack_try = check_and_pack(hints)
    if pack_try is not None:
        return pack_try

    # Step 4: 候选池增量加入（避免显见线索组合）
    pools = _gen_candidate_hints(sol, max_per_type=3)
    pool_names = ['row', 'col', 'neighbor', 'region', 'parity_row', 'parity_col', 'anchor_adj', 'global']
    pools_dict = {name: list(pools[i]) for i, name in enumerate(pool_names)}
    for name in pool_names:
        random.shuffle(pools_dict[name])

    for _round in range(80):
        if time.time() - t0 > time_limit_sec:
            break
        candidates = []
        for name in pool_names:
            if pools_dict[name]:
                candidates.append(name)
        if not candidates:
            break
        name = random.choice(candidates)
        cand = pools_dict[name].pop()
        hints[name].append(cand)
        if _has_apparent_combo(hints, R, C):
            hints[name].pop()
            continue
        pack_try = check_and_pack(hints)
        if pack_try is not None:
            return pack_try

    return None

# ================================================================
# Public operators for YAML
# ================================================================
def make_puzzle(rows, cols):
    attempts = 120
    global_time_limit = 60.0
    t0 = time.time()
    for _ in range(attempts):
        if time.time() - t0 > global_time_limit:
            break
        sizes = _random_island_sizes(rows, cols)
        sol = _place_islands(rows, cols, sizes, max_tries=160)
        if sol is None:
            continue
        clue = _make_clue_from_solution(sol)
        rules = {
            'require_wall_connected': True,
            'forbid_island_2x2': True,
            'forbid_wall_2x2': True
        }

        # 优先用强唯一化链快速返回
        rules_strong = {'require_wall_connected': True, 'forbid_island_2x2': True, 'forbid_wall_2x2': True}
        pack_ultra = _build_ultra_unique_pack(clue, sol, rules_strong, time_budget=max(10.0, global_time_limit - (time.time()-t0)))
        if pack_ultra is not None:
            cnt_chk, sol_chk = _solve_and_count(clue, pack_ultra, limit=2, time_limit_sec=max(8.0, global_time_limit - (time.time()-t0)))
            if cnt_chk == 1 and sol_chk == sol:
                return {'clue': clue, 'solution': sol, 'rules_pack': pack_ultra}

        pack_uni = _force_unique(clue, sol, base_rules=rules_strong, time_limit_sec=max(12.0, global_time_limit - (time.time()-t0)))
        if pack_uni is not None:
            cnt_chk, sol_chk = _solve_and_count(clue, pack_uni, limit=2, time_limit_sec=max(8.0, global_time_limit - (time.time()-t0)))
            if cnt_chk == 1 and sol_chk == sol:
                return {'clue': clue, 'solution': sol, 'rules_pack': pack_uni}

        # 随机提示组合（受限次数与强度）
        pool_row, pool_col, pool_nei, pool_region, pool_parity_row, pool_parity_col, pool_anchor_adj, pool_global = _gen_candidate_hints(sol, max_per_type=3)
        for p in (pool_row, pool_col, pool_nei, pool_region, pool_parity_row, pool_parity_col, pool_anchor_adj, pool_global):
            random.shuffle(p)

        def try_build_and_check():
            for _inner in range(60):
                r_take = random.randint(0, min(1, len(pool_row))) if pool_row else 0
                c_take = random.randint(0, min(1, len(pool_col))) if pool_col else 0
                reg_take = random.randint(0, min(2, len(pool_region))) if pool_region else 0
                nei_take = random.randint(0, min(2, len(pool_nei))) if pool_nei else 0
                adj_take = random.randint(0, min(1, len(pool_anchor_adj))) if pool_anchor_adj else 0
                pr_take = 1 if (pool_parity_row and random.random() < 0.6) else 0
                pc_take = 1 if (pool_parity_col and random.random() < 0.6) else 0
                take_global = 1 if (pool_global and random.random() < 0.25) else 0

                kinds_used = sum(1 for k in [r_take>0, c_take>0, reg_take>0, nei_take>0, adj_take>0, pr_take>0, pc_take>0, take_global>0] if k)
                if kinds_used < 2:
                    continue

                hints = {
                    'row': pool_row[:r_take],
                    'col': pool_col[:c_take],
                    'neighbor': pool_nei[:nei_take],
                    'region': pool_region[:reg_take],
                    'parity_row': pool_parity_row[:pr_take] if pr_take else [],
                    'parity_col': pool_parity_col[:pc_take] if pc_take else [],
                    'anchor_adj': pool_anchor_adj[:adj_take],
                    'global': pool_global[:take_global]
                }
                if _has_apparent_combo(hints, len(sol), len(sol[0])):
                    continue

                rules_pack = {'rules': rules, 'hints': hints}
                remaining = max(1.0, global_time_limit - (time.time()-t0))
                count, solved = _solve_and_count(clue, rules_pack, limit=2, time_limit_sec=remaining)
                if count == 1 and solved == sol:
                    rules_pack['digest'] = _solution_digest(sol)
                    return {'clue': clue, 'solution': sol, 'rules_pack': rules_pack}
            return None

        pack_try = try_build_and_check()
        if pack_try is not None:
            return pack_try

        # 超强兜底链（不使用 1×1 等式）
        super_pack = _build_super_strong_unique_pack(clue, sol, rules_strong, time_budget=max(15.0, global_time_limit - (time.time()-t0)))
        if super_pack is not None:
            cnt_chk, sol_chk = _solve_and_count(clue, super_pack, limit=2, time_limit_sec=max(8.0, global_time_limit - (time.time()-t0)))
            if cnt_chk == 1 and sol_chk == sol:
                return {'clue': clue, 'solution': sol, 'rules_pack': super_pack}

    # ============================================================
    # 最终兜底：优先使用请求尺寸 rows×cols 程序化生成 + 强唯一化包
    # 如仍失败，才退化到 5×5
    # ============================================================
    def final_attempt_with_size(R_fb, C_fb, time_budget_solve=30.0, time_budget_pack=35.0):
        t_begin = time.time()
        last_sol = None
        last_clue = None
        while (time.time() - t0) < (global_time_limit - 2.0) and (time.time() - t_begin) < time_budget_solve:
            sizes_fb = _random_island_sizes(R_fb, C_fb)
            sol_fb = _place_islands(R_fb, C_fb, sizes_fb, max_tries=220)
            if sol_fb is None:
                continue
            if not _check_no_2x2_walls_by_solution(sol_fb):
                continue
            if not _check_no_2x2_islands(sol_fb):
                continue
            if not _check_walls_connected(sol_fb):
                continue
            last_sol = sol_fb
            last_clue = _make_clue_from_solution(sol_fb)
            rules_fb = {'require_wall_connected': True, 'forbid_island_2x2': True, 'forbid_wall_2x2': True}

            pack_fb = _force_unique(last_clue, last_sol, base_rules=rules_fb, time_limit_sec=min(20.0, max(3.0, time_budget_pack - (time.time()-t_begin))))
            if pack_fb is not None:
                cnt_final, sol_final = _solve_and_count(last_clue, pack_fb, limit=2, time_limit_sec=min(18.0, max(3.0, time_budget_pack - (time.time()-t_begin))))
                if cnt_final == 1 and sol_final == last_sol:
                    return {'clue': last_clue, 'solution': last_sol, 'rules_pack': pack_fb}

            ultra_pack = _build_ultra_unique_pack(last_clue, last_sol, rules_fb, time_budget=min(25.0, max(3.0, time_budget_pack - (time.time()-t_begin))))
            if ultra_pack is not None:
                cnt_final, sol_final = _solve_and_count(last_clue, ultra_pack, limit=2, time_limit_sec=min(22.0, max(3.0, time_budget_pack - (time.time()-t_begin))))
                if cnt_final == 1 and sol_final == last_sol:
                    return {'clue': last_clue, 'solution': last_sol, 'rules_pack': ultra_pack}

            super_pack = _build_super_strong_unique_pack(last_clue, last_sol, rules_fb, time_budget=min(35.0, max(3.0, time_budget_pack - (time.time()-t_begin))))
            if super_pack is not None:
                cnt_final, sol_final = _solve_and_count(last_clue, super_pack, limit=2, time_limit_sec=min(30.0, max(3.0, time_budget_pack - (time.time()-t_begin))))
                if cnt_final == 1 and sol_final == last_sol:
                    return {'clue': last_clue, 'solution': last_sol, 'rules_pack': super_pack}
            # 否则继续尝试新的终局
        if last_sol is None:
            return None
        # 如果仍未返回：基于最后一个可用终局构造较强描述包（不含 1×1）
        rules_last = {'require_wall_connected': True, 'forbid_island_2x2': True, 'forbid_wall_2x2': True}
        hints_last = {'row': [], 'col': [], 'neighbor': [], 'region': [], 'parity_row': [], 'parity_col': [], 'anchor_adj': [], 'global': []}
        rc = _row_col_counts_hints(last_sol)
        hints_last['row'] = rc['row']
        hints_last['col'] = rc['col']
        walls_total = sum(1 for r in range(len(last_sol)) for c in range(len(last_sol[0])) if last_sol[r][c] == 0)
        hints_last['global'].append({'kind': 'walls', 'op': 'eq', 'val': walls_total})
        hints_last['neighbor'] = _all_anchor_neighbor_hints(last_sol, max_dirs_per_anchor=2)
        _add_2x2_regions_eq(last_sol, hints_last)
        pack_last = {'rules': rules_last, 'hints': hints_last}
        # 加固：仅当唯一且一致时返回
        cnt_chk, sol_chk = _solve_and_count(last_clue, pack_last, limit=2, time_limit_sec=28.0)
        if cnt_chk == 1 and sol_chk == last_sol:
            pack_last['digest'] = _solution_digest(last_sol)
            return {'clue': last_clue, 'solution': last_sol, 'rules_pack': pack_last}
        # 再试一次强唯一化
        pack_retry = _force_unique(last_clue, last_sol, base_rules=rules_last, time_limit_sec=10.0)
        if pack_retry is not None:
            cnt_retry, sol_retry = _solve_and_count(last_clue, pack_retry, limit=2, time_limit_sec=10.0)
            if cnt_retry == 1 and sol_retry == last_sol:
                return {'clue': last_clue, 'solution': last_sol, 'rules_pack': pack_retry}
        return None

    # 先用请求尺寸兜底
    attempt_req = final_attempt_with_size(rows, cols, time_budget_solve=20.0, time_budget_pack=25.0)
    if attempt_req is not None:
        return attempt_req
    # 再退化到 5×5 最终兜底
    attempt_5x5 = final_attempt_with_size(5, 5, time_budget_solve=22.0, time_budget_pack=28.0)
    if attempt_5x5 is not None:
        return attempt_5x5

    # 极端情况下，进行多次快速尝试，确保规则一致再返回
    rows_fb, cols_fb = 5, 5
    for _ in range(6):
        sol_tmp = _place_islands(rows_fb, cols_fb, [3,3,2,2], max_tries=300)
        if sol_tmp is None:
            continue
        if not (_check_no_2x2_walls_by_solution(sol_tmp) and _check_no_2x2_islands(sol_tmp) and _check_walls_connected(sol_tmp)):
            continue
        last_sol = sol_tmp
        last_clue = _make_clue_from_solution(last_sol)
        rules_last = {'require_wall_connected': True, 'forbid_island_2x2': True, 'forbid_wall_2x2': True}
        hints_last = {'row': [], 'col': [], 'neighbor': [], 'region': [], 'parity_row': [], 'parity_col': [], 'anchor_adj': [], 'global': []}
        rc = _row_col_counts_hints(last_sol)
        hints_last['row'] = rc['row']
        hints_last['col'] = rc['col']
        walls_total = sum(1 for r in range(len(last_sol)) for c in range(len(last_sol[0])) if last_sol[r][c] == 0)
        hints_last['global'].append({'kind': 'walls', 'op': 'eq', 'val': walls_total})
        hints_last['neighbor'] = _all_anchor_neighbor_hints(last_sol, max_dirs_per_anchor=2)
        _add_2x2_regions_eq(last_sol, hints_last)
        pack_last = {'rules': rules_last, 'hints': hints_last}
        cnt_last, sol_last = _solve_and_count(last_clue, pack_last, limit=2, time_limit_sec=18.0)
        if cnt_last == 1 and sol_last == last_sol:
            pack_last['digest'] = _solution_digest(last_sol)
            return {'clue': last_clue, 'solution': last_sol, 'rules_pack': pack_last}
        pack_retry = _force_unique(last_clue, last_sol, base_rules=rules_last, time_limit_sec=10.0)
        if pack_retry is not None:
            cnt_retry, sol_retry = _solve_and_count(last_clue, pack_retry, limit=2, time_limit_sec=10.0)
            if cnt_retry == 1 and sol_retry == last_sol:
                return {'clue': last_clue, 'solution': last_sol, 'rules_pack': pack_retry}
    # 如仍失败，返回 None，由上层重试
    return None

def solve_from_clue(clue, rules_pack):
    for t in (40.0, 70.0):
        count, sol = _solve_and_count(clue, rules_pack, limit=2, time_limit_sec=t)
        if count == 1 and sol is not None:
            return sol
    return None

def render_rules(rows, cols, rules_pack):
    return _render_hint_text(rows, cols, rules_pack)

# ================================================================
# Strong answer validator for YAML
# ================================================================
def _anchors_fixed_ok(candidate, clue):
    R = len(clue); C = len(clue[0])
    for r in range(R):
        for c in range(C):
            if clue[r][c] >= 2:
                if candidate[r][c] != clue[r][c]:
                    return False
            else:
                # 未知格不得出现新锚点（>=2）
                if candidate[r][c] >= 2:
                    return False
    return True

# 基于四连通的岛结构校验
def _islands_structure_ok(candidate, clue):
    R = len(candidate); C = len(candidate[0])
    visited = [[False]*C for _ in range(R)]
    anchors = [(r, c, clue[r][c]) for r in range(R) for c in range(C) if clue[r][c] >= 2]
    covered = [[False]*C for _ in range(R)]
    for (sr, sc, size) in anchors:
        if candidate[sr][sc] < 2:
            return False
        dq = deque()
        dq.append((sr, sc))
        visited[sr][sc] = True
        cells = [(sr, sc)]
        extra_anchor = 0
        while dq:
            r, c = dq.popleft()
            for nr, nc in _neighbors4(r, c):
                if not _inb(nr, nc, R, C):
                    continue
                if visited[nr][nc]:
                    continue
                if candidate[nr][nc] == 0:
                    continue
                visited[nr][nc] = True
                cells.append((nr, nc))
                dq.append((nr, nc))
                if clue[nr][nc] >= 2 and not (nr == sr and nc == sc):
                    extra_anchor += 1
        if extra_anchor != 0:
            return False
        if len(cells) != size:
            return False
        for (r, c) in cells:
            covered[r][c] = True
    for r in range(R):
        for c in range(C):
            if candidate[r][c] != 0 and not covered[r][c]:
                return False
    return True

def check_answer(candidate, clue, rules_pack):
    # candidate must be a list of lists of ints with proper shape
    if not isinstance(candidate, list) or not candidate:
        return False
    R = len(clue); C = len(clue[0])
    if len(candidate) != R:
        return False
    for row in candidate:
        if not isinstance(row, list) or len(row) != C:
            return False
        for v in row:
            if not isinstance(v, int):
                return False
    # 锚点固定与禁止新增锚点
    if not _anchors_fixed_ok(candidate, clue):
        return False
    # 岛结构硬校验：每岛恰一锚点且大小等于锚点、岛四连通、不同岛隔墙
    if not _islands_structure_ok(candidate, clue):
        return False
    # Fast path: digest match if provided
    dig = rules_pack.get('digest')
    if dig is not None:
        cand_dig = _solution_digest(candidate)
        if cand_dig != dig:
            return False
        if not _apply_hints_ok(candidate, rules_pack):
            return False
        if not _check_no_2x2_walls_by_solution(candidate):
            return False
        return True

    # Fallback: re-solve; only accept if unique and equal
    sol = solve_from_clue(clue, rules_pack)
    if sol is None:
        return False
    if sol != candidate:
        return False
    if not _apply_hints_ok(candidate, rules_pack):
        return False
    if not _check_no_2x2_walls_by_solution(candidate):
        return False
    return True

# ================================================================
# Extra operators for YAML: get actual grid size after generation
# ================================================================
def get_rows(grid):
    return len(grid)

def get_cols(grid):
    return len(grid[0])