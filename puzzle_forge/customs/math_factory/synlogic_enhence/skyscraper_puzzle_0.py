# skyscraper_puzzle_0.py
# High-complexity randomized-rule Skyscraper puzzle generation and text rendering.

import random

def function_1(*args, **kwargs):
    return None

def function_2(*args, **kwargs):
    return None

def make_index_labels(n, prefix='r'):
    return [f"{prefix}{i}" for i in range(n)]

def _base_latin(n):
    return [[((i + j) % n) + 1 for j in range(n)] for i in range(n)]

def _permute_rows(grid, perm):
    return [grid[i] for i in perm]

def _permute_cols(grid, perm):
    return [[row[j] for j in perm] for row in grid]

def _permute_symbols(grid, sym_map):
    return [[sym_map[v] for v in row] for row in grid]

def random_latin_grid(n):
    grid = _base_latin(n)
    row_perm = list(range(n)); random.shuffle(row_perm)
    grid = _permute_rows(grid, row_perm)
    col_perm = list(range(n)); random.shuffle(col_perm)
    grid = _permute_cols(grid, col_perm)
    sym_values = list(range(1, n + 1))
    sym_perm = sym_values[:]; random.shuffle(sym_perm)
    sym_map = {old: new for old, new in zip(sym_values, sym_perm)}
    grid = _permute_symbols(grid, sym_map)
    return grid

def _visible_count(seq):
    max_h = 0; cnt = 0
    for h in seq:
        if h > max_h:
            cnt += 1; max_h = h
    return cnt

def compute_clues(grid):
    n = len(grid)
    left = [_visible_count(row) for row in grid]
    right = [_visible_count(list(reversed(row))) for row in grid]
    top = []; bottom = []
    for c in range(n):
        col = [grid[r][c] for r in range(n)]
        top.append(_visible_count(col))
        bottom.append(_visible_count(list(reversed(col))))
    return {'top': top, 'bottom': bottom, 'left': left, 'right': right}

def _sample_unique_indices(n, k):
    k = max(0, min(k, n))
    return random.sample(range(n), k) if k > 0 else []

def _row_sum_targets(grid, rows_sel):
    return [sum(grid[i]) for i in rows_sel]

def _col_sum_targets(grid, cols_sel):
    n = len(grid)
    return [sum(grid[i][j] for i in range(n)) for j in cols_sel]

def _sample_reveals(grid, reveal_num):
    n = len(grid)
    reveal_num = max(0, min(reveal_num, n))
    if reveal_num == 0:
        return []
    all_positions = [(i, j) for i in range(n) for j in range(n)]
    sel = random.sample(all_positions, reveal_num)
    return [(i, j, grid[i][j]) for (i, j) in sel]

def _sample_row_rel_lt(grid, row_rel_num):
    n = len(grid)
    row_rel_num = max(0, min(row_rel_num, n))
    choices = []
    if row_rel_num == 0:
        return choices
    rows = list(range(n)); random.shuffle(rows)
    for i in rows:
        cols = list(range(n)); random.shuffle(cols)
        found = False
        for j1 in cols:
            for j2 in cols:
                if j1 == j2: continue
                if grid[i][j1] < grid[i][j2]:
                    choices.append((i, j1, j2)); found = True; break
            if found: break
        if len(choices) >= row_rel_num: break
    return choices[:row_rel_num]

def _sample_col_rel_lt(grid, col_rel_num):
    n = len(grid)
    col_rel_num = max(0, min(col_rel_num, n))
    choices = []
    if col_rel_num == 0:
        return choices
    cols = list(range(n)); random.shuffle(cols)
    for j in cols:
        rows = list(range(n)); random.shuffle(rows)
        found = False
        for i1 in rows:
            for i2 in rows:
                if i1 == i2: continue
                if grid[i1][j] < grid[i2][j]:
                    choices.append((i1, i2, j)); found = True; break
            if found: break
        if len(choices) >= col_rel_num: break
    return choices[:col_rel_num]

def _make_regions(n, max_regions):
    max_regions = max(0, min(max_regions, n))
    cells = [(i, j) for i in range(n) for j in range(n)]
    random.shuffle(cells)
    used = set(); regions = []; attempts = 0
    while len(regions) < max_regions and attempts < n * n:
        attempts += 1
        seed = None
        for (i, j) in cells:
            if (i, j) not in used:
                seed = (i, j); break
        if seed is None: break
        size = random.randint(2, min(4, n))
        region = [seed]; used.add(seed)
        si, sj = seed
        neighbors = []
        for di, dj in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            ni, nj = si+di, sj+dj
            if 0 <= ni < n and 0 <= nj < n and (ni, nj) not in used:
                neighbors.append((ni, nj))
        random.shuffle(neighbors)
        for nb in neighbors:
            if len(region) >= size: break
            region.append(nb); used.add(nb)
        if len(region) >= 2:
            regions.append(region)
    return regions

def _region_sum_targets(grid, regions):
    return [sum(grid[i][j] for (i, j) in reg) for reg in regions]

def _region_max_pairs(grid, regions, max_hint_ratio=0.5):
    pairs = []
    for ri, reg in enumerate(regions):
        if len(reg) == 0: continue
        if random.random() < max_hint_ratio:
            i_max, j_max = max(reg, key=lambda ij: grid[ij[0]][ij[1]])
            pairs.append((ri, (i_max, j_max)))
    return pairs

def _rank_row_hints(grid, max_hints):
    n = len(grid)
    max_hints = max(0, min(max_hints, n))
    hints = []
    rows = list(range(n)); random.shuffle(rows)
    for i in rows:
        cols = list(range(n)); random.shuffle(cols)
        j = cols[0]
        val = grid[i][j]
        r = 1 + sum(1 for t in range(n) if grid[i][t] < val)
        hints.append((i, j, r))
        if len(hints) >= max_hints: break
    return hints

def _rank_col_hints(grid, max_hints):
    n = len(grid)
    max_hints = max(0, min(max_hints, n))
    hints = []
    cols = list(range(n)); random.shuffle(cols)
    for j in cols:
        rows = list(range(n)); random.shuffle(rows)
        i = rows[0]
        val = grid[i][j]
        r = 1 + sum(1 for t in range(n) if grid[t][j] < val)
        hints.append((i, j, r))
        if len(hints) >= max_hints: break
    return hints

def _adj_row_diffs(grid, max_num):
    n = len(grid)
    max_num = max(0, min(max_num, n))
    diffs = []
    if max_num == 0: return diffs
    for i in random.sample(range(n), n):
        j1 = random.randint(0, n - 2)
        j2 = j1 + 1
        d = abs(grid[i][j1] - grid[i][j2])
        diffs.append((i, j1, j2, d))
        if len(diffs) >= max_num: break
    return diffs

def _adj_col_diffs(grid, max_num):
    n = len(grid)
    max_num = max(0, min(max_num, n))
    diffs = []
    if max_num == 0: return diffs
    for j in random.sample(range(n), n):
        i1 = random.randint(0, n - 2)
        i2 = i1 + 1
        d = abs(grid[i1][j] - grid[i2][j])
        diffs.append((i1, i2, j, d))
        if len(diffs) >= max_num: break
    return diffs

def _row_weight_constraints(grid, max_num):
    n = len(grid)
    max_num = max(0, min(max_num, n))
    if max_num == 0: return [], [], []
    rows_sel = random.sample(range(n), max_num)
    weights = []; targets = []
    for i in rows_sel:
        w_row = [random.randint(1, 2) for _ in range(n)]
        weights.append(w_row)
        targ = sum(w_row[j] * grid[i][j] for j in range(n))
        targets.append(targ)
    return rows_sel, weights, targets

def generate_rule_spec(n, sol_grid,
                       top_full, bottom_full, left_full, right_full,
                       max_top_num, max_bottom_num, max_left_num, max_right_num,
                       row_sum_num, col_sum_num, reveal_num, row_rel_num, col_rel_num,
                       difficulty_level):
    """
    Randomize internal composite rules using upper bounds and difficulty level.
    Avoid '显见线索' by not simultaneously covering all rows and all columns with sum constraints,
    scaling reveals and advanced constraints with difficulty, and de-duplicating overly strong combos.
    """
    # Difficulty scaling
    # Level 1 (易): fewer clues, more reveals; Level 3 (难): more structure, fewer reveals
    rev_cap = {1: max(1, n // 2), 2: max(1, n // 3), 3: max(1, n // 4)}[difficulty_level]
    reg_cap = {1: max(0, n // 3), 2: max(0, n // 2), 3: n}[difficulty_level]
    rank_cap = {1: 1, 2: n // 2, 3: n}[difficulty_level]
    weight_cap = {1: n // 2, 2: n // 2, 3: n}[difficulty_level]

    # Decide actual counts from upper bounds
    top_k = random.randint(0, max(0, min(max_top_num, n)))
    bottom_k = random.randint(0, max(0, min(max_bottom_num, n)))
    left_k = random.randint(0, max(0, min(max_left_num, n)))
    right_k = random.randint(0, max(0, min(max_right_num, n)))

    # Choose indices for clues
    top_idx = _sample_unique_indices(n, top_k)
    bottom_idx = _sample_unique_indices(n, bottom_k)
    left_idx = _sample_unique_indices(n, left_k)
    right_idx = _sample_unique_indices(n, right_k)

    # Row sums and Column sums
    rs_k = max(0, min(row_sum_num, n))
    cs_k = max(0, min(col_sum_num, n))
    # Avoid simultaneous full coverage on both rows and cols (显见线索)
    if rs_k >= n and cs_k >= n:
        cs_k = n // 2
    row_sum_rows = _sample_unique_indices(n, rs_k)
    col_sum_cols = _sample_unique_indices(n, cs_k)
    row_sum_targets = _row_sum_targets(sol_grid, row_sum_rows)
    col_sum_targets = _col_sum_targets(sol_grid, col_sum_cols)

    # Reveals (cap by difficulty)
    reveal_num = min(reveal_num, rev_cap)
    reveals = _sample_reveals(sol_grid, reveal_num)

    # Pairwise relations
    row_rel_lt = _sample_row_rel_lt(sol_grid, min(row_rel_num, n))
    col_rel_lt = _sample_col_rel_lt(sol_grid, min(col_rel_num, n))

    # Advanced constraints: rank hints, regions, adjacency diffs, weighted sums
    rank_row_hints = _rank_row_hints(sol_grid, random.randint(0, rank_cap))
    rank_col_hints = _rank_col_hints(sol_grid, random.randint(0, rank_cap))

    # Regions
    max_regions = random.randint(0, reg_cap)
    regions = _make_regions(n, max_regions)
    region_sum_targets = _region_sum_targets(sol_grid, regions)
    region_max_pairs = _region_max_pairs(sol_grid, regions, max_hint_ratio=0.5)

    # Adjacency diffs
    adj_row_diffs = _adj_row_diffs(sol_grid, random.randint(0, n))
    adj_col_diffs = _adj_col_diffs(sol_grid, random.randint(0, n))

    # Weighted row sums (reduce if row sums already heavy)
    max_weight_rows = weight_cap if rs_k <= n // 2 else 0
    rws_rows, rws_weights, rws_targets = _row_weight_constraints(sol_grid, random.randint(0, max_weight_rows))

    # Minimal constraint strength heuristic
    strength = (
        len(top_idx) + len(bottom_idx) + len(left_idx) + len(right_idx) +
        len(row_sum_rows) + len(col_sum_cols) + len(reveals) +
        len(row_rel_lt) + len(col_rel_lt) + len(rank_row_hints) + len(rank_col_hints) +
        len(regions) + len(region_max_pairs) + len(adj_row_diffs) + len(adj_col_diffs) +
        len(rws_rows)
    )
    target_strength = max(5, n + 4)
    if strength < target_strength:
        # Add more reveals within cap
        extra_rev = max(0, min(target_strength - strength, rev_cap - len(reveals)))
        if extra_rev > 0:
            reveals += _sample_reveals(sol_grid, extra_rev)
        # Add more row sums if possible
        extra_rows = [i for i in range(n) if i not in row_sum_rows]
        random.shuffle(extra_rows)
        needed = max(0, min(target_strength - strength - extra_rev, n - len(row_sum_rows)))
        for i in extra_rows[:needed]:
            row_sum_rows.append(i)
            row_sum_targets.append(sum(sol_grid[i]))

    return {
        'top_idx': top_idx,
        'bottom_idx': bottom_idx,
        'left_idx': left_idx,
        'right_idx': right_idx,
        'row_sum_rows': row_sum_rows,
        'row_sum_targets': row_sum_targets,
        'col_sum_cols': col_sum_cols,
        'col_sum_targets': col_sum_targets,
        'reveals': reveals,
        'row_rel_lt': row_rel_lt,
        'col_rel_lt': col_rel_lt,
        'rank_row_hints': rank_row_hints,
        'rank_col_hints': rank_col_hints,
        'region_cells_list': regions,
        'region_sum_targets': region_sum_targets,
        'region_max_pairs': region_max_pairs,
        'adj_row_diffs': adj_row_diffs,
        'adj_col_diffs': adj_col_diffs,
        'row_weight_rows': rws_rows,
        'row_weight_weights': rws_weights,
        'row_weight_targets': rws_targets,
    }

def _pairs_to_text(pairs):
    return "[" + ", ".join([f"({a}, {b})" for (a, b) in pairs]) + "]"

def render_rule_text(n, rule_spec, top_full, bottom_full, left_full, right_full):
    """
    Human-readable multi-line string describing the exact rules (indices 0-based).
    Avoid double quotes; use brackets and parentheses; join with explicit \n.
    """
    lines = []
    lines.append(f"尺寸: n={n}，索引从 0 开始")

    # Visibility subsets with values
    top_idx = rule_spec.get('top_idx', [])
    if top_idx:
        top_pairs = [(c, top_full[c]) for c in top_idx]
        lines.append(f"顶部线索: " + _pairs_to_text(top_pairs))
    bottom_idx = rule_spec.get('bottom_idx', [])
    if bottom_idx:
        bottom_pairs = [(c, bottom_full[c]) for c in bottom_idx]
        lines.append(f"底部线索: " + _pairs_to_text(bottom_pairs))
    left_idx = rule_spec.get('left_idx', [])
    if left_idx:
        left_pairs = [(i, left_full[i]) for i in left_idx]
        lines.append(f"行左侧线索: " + _pairs_to_text(left_pairs))
    right_idx = rule_spec.get('right_idx', [])
    if right_idx:
        right_pairs = [(i, right_full[i]) for i in right_idx]
        lines.append(f"行右侧线索: " + _pairs_to_text(right_pairs))

    # Row/Col sums
    rows_sel = rule_spec.get('row_sum_rows', [])
    row_targets = rule_spec.get('row_sum_targets', [])
    if rows_sel:
        pairs = [(i, row_targets[idx]) for idx, i in enumerate(rows_sel)]
        lines.append(f"行总和约束: " + _pairs_to_text(pairs))
    cols_sel = rule_spec.get('col_sum_cols', [])
    col_targets = rule_spec.get('col_sum_targets', [])
    if cols_sel:
        pairs = [(j, col_targets[idx]) for idx, j in enumerate(cols_sel)]
        lines.append(f"列总和约束: " + _pairs_to_text(pairs))

    # Reveals
    reveals = rule_spec.get('reveals', [])
    if reveals:
        text = "[" + ", ".join([f"({i}, {j}) = {v}" for (i, j, v) in reveals]) + "]"
        lines.append(f"已知格子: " + text)

    # Row/Col < relations
    row_rel_lt = rule_spec.get('row_rel_lt', [])
    if row_rel_lt:
        text = "[" + ", ".join([f"({i}, {j1}) < ({i}, {j2})" for (i, j1, j2) in row_rel_lt]) + "]"
        lines.append(f"行内相对大小: " + text)
    col_rel_lt = rule_spec.get('col_rel_lt', [])
    if col_rel_lt:
        text = "[" + ", ".join([f"({i1}, {j}) < ({i2}, {j})" for (i1, i2, j) in col_rel_lt]) + "]"
        lines.append(f"列内相对大小: " + text)

    # Rank hints
    rrh = rule_spec.get('rank_row_hints', [])
    if rrh:
        text = "[" + ", ".join([f"({i}, {j}) 为第 {r} 小" for (i, j, r) in rrh]) + "]"
        lines.append(f"行排名提示: " + text)
    rch = rule_spec.get('rank_col_hints', [])
    if rch:
        text = "[" + ", ".join([f"({i}, {j}) 为第 {r} 小" for (i, j, r) in rch]) + "]"
        lines.append(f"列排名提示: " + text)

    # Regions
    regions = rule_spec.get('region_cells_list', [])
    region_sums = rule_spec.get('region_sum_targets', [])
    region_max_pairs = rule_spec.get('region_max_pairs', [])
    if regions:
        reg_lines = []
        for idx, cells in enumerate(regions):
            cells_text = _pairs_to_text(cells)
            part = f"R{idx}: cells={cells_text}, sum={region_sums[idx] if idx < len(region_sums) else '?'}"
            reg_lines.append(part)
        if reg_lines:
            lines.append("区域信息: [" + "; ".join(reg_lines) + "]")
    if region_max_pairs:
        text = "[" + ", ".join([f"R{ri} max=({i_max}, {j_max})" for (ri, (i_max, j_max)) in region_max_pairs]) + "]"
        lines.append(f"区域最大值提示: " + text)

    # Adjacency diffs
    adr = rule_spec.get('adj_row_diffs', [])
    if adr:
        text = "[" + ", ".join([f"|({i}, {j1}) - ({i}, {j2})| = {d}" for (i, j1, j2, d) in adr]) + "]"
        lines.append(f"行内差值: " + text)
    adc = rule_spec.get('adj_col_diffs', [])
    if adc:
        text = "[" + ", ".join([f"|({i1}, {j}) - ({i2}, {j})| = {d}" for (i1, i2, j, d) in adc]) + "]"
        lines.append(f"列内差值: " + text)

    # Weighted row sums
    rws_rows = rule_spec.get('row_weight_rows', [])
    rws_weights = rule_spec.get('row_weight_weights', [])
    rws_targets = rule_spec.get('row_weight_targets', [])
    if rws_rows:
        parts = []
        for idx, i in enumerate(rws_rows):
            w = rws_weights[idx] if idx < len(rws_weights) else []
            t = rws_targets[idx] if idx < len(rws_targets) else "?"
            parts.append(f"行{i}: weights={w}, target={t}")
        lines.append("加权行和: [" + "; ".join(parts) + "]")

    return "\\n".join(lines)