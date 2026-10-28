# numbrix_5.py
# Helper functions for generating torus Numbrix instances with unique solutions
# and building randomized internal rule packs aligned with a solved grid, with
# strict uniqueness verification (unknown is NOT accepted as unique).

from z3 import Int, Solver, And, Or, sat, unsat, IntVal
import random

def pick_difficulty():
    """
    Randomly pick a difficulty level from ['easy', 'medium', 'hard'].
    This is used in YAML variables via formula since 'str' type is not supported.
    """
    return random.choice(['easy', 'medium', 'hard'])

def _adjacent_torus(r1, c1, r2, c2, n):
    same_row = And(r2 == r1,
                   Or(c2 == c1 + 1,
                      And(c1 == n, c2 == 1),
                      c2 == c1 - 1,
                      And(c1 == 1, c2 == n)))
    same_col = And(c2 == c1,
                   Or(r2 == r1 + 1,
                      And(r1 == n, r2 == 1),
                      r2 == r1 - 1,
                      And(r1 == 1, r2 == n)))
    return Or(same_row, same_col)

def _serpentine_grid(n):
    # Build base Hamiltonian path grid: consecutive numbers are orthogonally adjacent
    grid = [[0 for _ in range(n)] for _ in range(n)]
    val = 1
    for r in range(n):
        if r % 2 == 0:  # left to right
            for c in range(n):
                grid[r][c] = val
                val += 1
        else:  # right to left
            for c in range(n-1, -1, -1):
                grid[r][c] = val
                val += 1
    return grid

def _rotate_grid(grid, k):
    # Rotate 90*k degrees clockwise
    g = [row[:] for row in grid]
    for _ in range(k % 4):
        g = [list(row) for row in zip(*g[::-1])]
    return g

def _flip_h(grid):
    # Mirror horizontally (reverse columns)
    return [list(reversed(row)) for row in grid]

def _flip_v(grid):
    # Mirror vertically (reverse rows)
    return grid[::-1]

def _torus_shift(grid, dr, dc):
    n = len(grid)
    dr %= n
    dc %= n
    shifted = [[0]*n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            shifted[(r+dr) % n][(c+dc) % n] = grid[r][c]
    return shifted

def _reverse_numbers(grid):
    n2 = len(grid) * len(grid)
    return [[n2 + 1 - v for v in row] for row in grid]

def _random_transformed_grid(n, rng):
    g = _serpentine_grid(n)
    # Apply random transforms that preserve adjacency
    if rng.random() < 0.5:
        g = _flip_h(g)
    if rng.random() < 0.5:
        g = _flip_v(g)
    g = _rotate_grid(g, rng.choice([0, 1, 2, 3]))
    g = _torus_shift(g, rng.randrange(0, n), rng.randrange(0, n))
    if rng.random() < 0.5:
        g = _reverse_numbers(g)
    return g

def _build_uniqueness_solver(n, clues, timeout_ms=120000):
    numbers = list(range(1, n*n + 1))
    pos_r = {v: Int(f"r_{v}") for v in numbers}
    pos_c = {v: Int(f"c_{v}") for v in numbers}
    s = Solver()
    s.set("timeout", timeout_ms)
    # Bounds
    for v in numbers:
        s.add(And(pos_r[v] >= 1, pos_r[v] <= n,
                  pos_c[v] >= 1, pos_c[v] <= n))
    # Distinct positions (pairwise)
    for i in range(len(numbers)):
        vi = numbers[i]
        for j in range(i+1, len(numbers)):
            vj = numbers[j]
            s.add(Or(pos_r[vi] != pos_r[vj], pos_c[vi] != pos_c[vj]))
    # Adjacency for consecutive numbers (torus)
    for k in range(1, n*n):
        s.add(_adjacent_torus(pos_r[k], pos_c[k], pos_r[k+1], pos_c[k+1], n))
    # Fix clues
    for (r, c, v) in clues:
        s.add(pos_r[v] == r)
        s.add(pos_c[v] == c)
    return s, pos_r, pos_c, numbers

def _is_unique(n, clues, timeout_ms=120000):
    """
    Strict uniqueness: return True only if second model check == unsat.
    unknown is treated as non-unique (False).
    """
    s, pos_r, pos_c, nums = _build_uniqueness_solver(n, clues, timeout_ms=timeout_ms)
    res = s.check()
    if res != sat:
        return False
    m = s.model()
    # Block this model and check for another
    block_terms = []
    for v in nums:
        rv = m[pos_r[v]].as_long()
        cv = m[pos_c[v]].as_long()
        block_terms.append(Or(pos_r[v] != IntVal(rv), pos_c[v] != IntVal(cv)))
    s.add(Or(block_terms))
    res2 = s.check()
    return res2 == unsat

def _grid_positions(grid):
    n = len(grid)
    pos = {}
    for r in range(n):
        for c in range(n):
            pos[grid[r][c]] = (r+1, c+1)  # 1-based
    return pos

def _choose_clue_count(n, difficulty, rng):
    total = n*n
    # Clue density bands by difficulty
    if difficulty == 'easy':
        low, high = 0.38, 0.5
    elif difficulty == 'hard':
        low, high = 0.2, 0.28
    else:
        low, high = 0.28, 0.38
    lo = max(2, int(low * total))
    hi = max(lo+1, int(high * total))
    return rng.randint(lo, hi)

def gen_torus_clues_unique(n, difficulty):
    """
    Generate a list of (row, col, value) clues for an n x n torus Numbrix such that:
    - There exists exactly one solution (verified by Z3).
    - Clues include endpoints 1 and n^2.
    - The hidden solution grid is randomized by transforms.
    - Uniqueness check uses solver timeout to bound runtime.
    """
    rng = random.Random()
    grid = _random_transformed_grid(n, rng)
    pos = _grid_positions(grid)

    # Start with endpoints; grow until unique is achieved.
    total = n*n
    base = {1, total}
    max_tries = 160
    target = _choose_clue_count(n, difficulty, rng)

    # candidate pool of values to reveal
    pool = [v for v in range(1, total+1) if v not in base]
    rng.shuffle(pool)

    for _ in range(max_tries):
        # build initial set of values
        clue_vals = set(base)
        # fill up to 'target'
        for v in pool:
            if len(clue_vals) >= target:
                break
            clue_vals.add(v)

        # Attempt strict uniqueness; if not unique, grow clues up to ~60% if needed
        grow_pool = [v for v in range(1, total+1) if v not in clue_vals]
        rng.shuffle(grow_pool)
        clues = [(pos[v][0], pos[v][1], v) for v in sorted(clue_vals)]
        if _is_unique(n, clues, timeout_ms=120000):
            return clues

        for v in grow_pool:
            clue_vals.add(v)
            clues = [(pos[vv][0], pos[vv][1], vv) for vv in sorted(clue_vals)]
            if _is_unique(n, clues, timeout_ms=120000):
                return clues
            # cap growth at ~60%
            if len(clue_vals) >= int(0.6 * total):
                break

        # Shuffle and try again with a different subset size around target
        rng.shuffle(pool)
        target = _choose_clue_count(n, difficulty, rng)

    # Fallback: reveal ~60% and ensure uniqueness, else raise
    clue_vals = set(base)
    for v in pool:
        if len(clue_vals) >= int(0.6 * total):
            break
        clue_vals.add(v)
    clues = [(pos[v][0], pos[v][1], v) for v in sorted(clue_vals)]
    if _is_unique(n, clues, timeout_ms=150000):
        return clues
    raise RuntimeError("Failed to generate unique clues within limits.")

def verify_unique_with_rules(n, clues, rule_pack, timeout_ms=60000):
    """
    Verify uniqueness under final rules + clues + torus adjacency.
    Returns True if unique (strict: second model unsat), False otherwise (including unknown).
    """
    s, pos_r, pos_c, nums = _build_uniqueness_solver(n, clues, timeout_ms=timeout_ms)

    def add_same_row_pairs(pairs):
        for (a, b) in pairs:
            s.add(pos_r[a] == pos_r[b])

    def add_same_col_pairs(pairs):
        for (a, b) in pairs:
            s.add(pos_c[a] == pos_c[b])

    def add_adj_pairs(pairs):
        for (a, b) in pairs:
            s.add(_adjacent_torus(pos_r[a], pos_c[a], pos_r[b], pos_c[b], n))

    def add_left_k_rel(rels):
        for (x, y, k) in rels:
            s.add(And(pos_r[x] == pos_r[y],
                      Or(pos_c[x] == pos_c[y] + k,
                         And(pos_c[y] + k > n, pos_c[x] == pos_c[y] + k - n))))

    def add_border_values(vals):
        for v in vals:
            s.add(Or(pos_r[v] == 1, pos_r[v] == n, pos_c[v] == 1, pos_c[v] == n))

    def add_corner_values(vals):
        for v in vals:
            s.add(Or(And(pos_r[v] == 1, pos_c[v] == 1),
                     And(pos_r[v] == 1, pos_c[v] == n),
                     And(pos_r[v] == n, pos_c[v] == 1),
                     And(pos_r[v] == n, pos_c[v] == n)))

    def add_mirror_h_pairs(pairs):
        for (a, b) in pairs:
            s.add(And(pos_r[a] == pos_r[b], pos_c[a] + pos_c[b] == n + 1))

    def add_mirror_v_pairs(pairs):
        for (a, b) in pairs:
            s.add(And(pos_c[a] == pos_c[b], pos_r[a] + pos_r[b] == n + 1))

    def add_diag_eq_pairs(pairs):
        for (a, b) in pairs:
            s.add(pos_r[a] - pos_c[a] == pos_r[b] - pos_c[b])

    def add_antidiag_eq_pairs(pairs):
        for (a, b) in pairs:
            s.add(pos_r[a] + pos_c[a] == pos_r[b] + pos_c[b])

    def add_rectangle_quads(quads):
        for (p, q, r, s2) in quads:
            s.add(And(pos_r[p] == pos_r[q],
                      pos_r[r] == pos_r[s2],
                      pos_c[p] == pos_c[r],
                      pos_c[q] == pos_c[s2]))

    def add_band_rows(rows, vals):
        if rows and len(rows) == 2:
            rA, rB = rows
            for v in vals:
                s.add(Or(pos_r[v] == rA, pos_r[v] == rB))

    def add_band_cols(cols, vals):
        if cols and len(cols) == 2:
            cA, cB = cols
            for v in vals:
                s.add(Or(pos_c[v] == cA, pos_c[v] == cB))

    # Inject all rules found in rule_pack
    add_same_row_pairs(rule_pack.get('same_row_pairs', []))
    add_same_col_pairs(rule_pack.get('same_col_pairs', []))
    add_adj_pairs(rule_pack.get('adj_pairs', []))
    add_left_k_rel(rule_pack.get('left_k_rel', []))
    add_border_values(rule_pack.get('border_values', []))
    add_corner_values(rule_pack.get('corner_values', []))
    add_mirror_h_pairs(rule_pack.get('mirror_h_pairs', []))
    add_mirror_v_pairs(rule_pack.get('mirror_v_pairs', []))
    add_diag_eq_pairs(rule_pack.get('diag_eq_pairs', []))
    add_antidiag_eq_pairs(rule_pack.get('antidiag_eq_pairs', []))
    add_rectangle_quads(rule_pack.get('rectangle_quads', []))
    add_band_rows(rule_pack.get('band_rows', []), rule_pack.get('band_values', []))
    add_band_cols(rule_pack.get('band_cols', []), rule_pack.get('bandc_values', []))

    res = s.check()
    if res != sat:
        return False
    m = s.model()
    # Block this model and check for another
    block_terms = []
    for v in nums:
        rv = m[pos_r[v]].as_long()
        cv = m[pos_c[v]].as_long()
        block_terms.append(Or(pos_r[v] != IntVal(rv), pos_c[v] != IntVal(cv)))
    s.add(Or(block_terms))
    res2 = s.check()
    return res2 == unsat

def build_rule_pack(n, row_of, col_of, difficulty, clues):
    """
    Build randomized internal rule lists aligned with a solved grid.
    Inputs:
      - n: grid size
      - row_of: list of rows for values 1..n^2 (index v-1)
      - col_of: list of cols for values 1..n^2 (index v-1)
      - difficulty: 'easy' | 'medium' | 'hard' controls rule density
      - clues: list of (r, c, v) used both in text and uniqueness verification
    Returns a dict with keys:
      'same_row_pairs', 'same_col_pairs', 'adj_pairs', 'left_k_rel',
      'border_values', 'corner_values',
      'mirror_h_pairs', 'mirror_v_pairs',
      'diag_eq_pairs', 'antidiag_eq_pairs',
      'rectangle_quads',
      'band_rows', 'band_values',
      'band_cols', 'bandc_values',
      'texts' (list of human-readable rules)
    Ensures uniqueness via verify_unique_with_rules, else raises.
    """
    rng = random.Random()
    total = n*n

    def pos(v):
        return row_of[v-1], col_of[v-1]

    # Pools
    same_row_candidates = []
    same_col_candidates = []
    left_k_candidates = []  # (x, y, k) where x is k steps right of y on same row (wrap)
    adj_candidates = []     # (a, b) adjacent in torus, excluding consecutives
    border_vals = []
    corner_vals = []
    mirror_h_candidates = []   # (a, b): same row & c(a)+c(b)=n+1
    mirror_v_candidates = []   # (a, b): same col & r(a)+r(b)=n+1
    diag_eq_candidates = []    # (a, b): r(a)-c(a)=r(b)-c(b)
    antidiag_eq_candidates = []# (a, b): r(a)+c(a)=r(b)+c(b)
    rectangle_quads_candidates = [] # (p,q,r,s): rectangle corners
    band_rows = []  # two distinct rows
    band_cols = []  # two distinct cols
    band_values_candidates = []
    bandc_values_candidates = []

    # Border and corner
    for v in range(1, total+1):
        r, c = pos(v)
        if r == 1 or r == n or c == 1 or c == n:
            border_vals.append(v)
        if (r, c) in [(1,1), (1,n), (n,1), (n,n)]:
            corner_vals.append(v)

    # Pairwise scanning to fill pools
    for a in range(1, total+1):
        ra, ca = pos(a)
        for b in range(a+1, total+1):
            rb, cb = pos(b)
            if ra == rb:
                same_row_candidates.append((a, b))
            if ca == cb:
                same_col_candidates.append((a, b))

            # Adjacent torus (exclude consecutives)
            if abs(a - b) != 1:
                same_row = (rb == ra) and (cb in {((ca + 1 - 1) % n) + 1, ((ca - 1 - 1) % n) + 1})
                same_col = (cb == ca) and (rb in {((ra + 1 - 1) % n) + 1, ((ra - 1 - 1) % n) + 1})
                if same_row or same_col:
                    adj_candidates.append((a, b))

            # Right-offset (wrap) from b to a on same row
            if ra == rb:
                diff = (ca - cb) % n
                if 1 <= diff <= n-1:
                    left_k_candidates.append((a, b, diff))

            # Mirror constraints
            if ra == rb and (ca + cb == n + 1):
                mirror_h_candidates.append((a, b))
            if ca == cb and (ra + rb == n + 1):
                mirror_v_candidates.append((a, b))

            # Diagonal equalities
            if (ra - ca) == (rb - cb):
                diag_eq_candidates.append((a, b))
            if (ra + ca) == (rb + cb):
                antidiag_eq_candidates.append((a, b))

    # Rectangle corner quads
    rows = list(range(1, n+1))
    cols = list(range(1, n+1))
    for i in range(n):
        for j in range(i+1, n):
            r1, r2 = rows[i], rows[j]
            for u in range(n):
                for v in range(u+1, n):
                    c1, c2 = cols[u], cols[v]
                    p = q = r_ = s_ = None
                    for val in range(1, total+1):
                        rv, cv = pos(val)
                        if rv == r1 and cv == c1: p = val
                        elif rv == r1 and cv == c2: q = val
                        elif rv == r2 and cv == c1: r_ = val
                        elif rv == r2 and cv == c2: s_ = val
                    if p and q and r_ and s_:
                        rectangle_quads_candidates.append((p, q, r_, s_))

    # Two-row/two-col bands
    rng_rows = rows[:]
    rng_cols = cols[:]
    random.shuffle(rng_rows)
    random.shuffle(rng_cols)
    if len(rng_rows) >= 2:
        band_rows = rng_rows[:2]
    if len(rng_cols) >= 2:
        band_cols = rng_cols[:2]
    for v in range(1, total+1):
        r, c = pos(v)
        if band_rows and r in band_rows:
            band_values_candidates.append(v)
        if band_cols and c in band_cols:
            bandc_values_candidates.append(v)

    # Shuffle pools for sampling
    rng.shuffle(same_row_candidates)
    rng.shuffle(same_col_candidates)
    rng.shuffle(adj_candidates)
    rng.shuffle(left_k_candidates)
    rng.shuffle(border_vals)
    rng.shuffle(corner_vals)
    rng.shuffle(mirror_h_candidates)
    rng.shuffle(mirror_v_candidates)
    rng.shuffle(diag_eq_candidates)
    rng.shuffle(antidiag_eq_candidates)
    rng.shuffle(rectangle_quads_candidates)
    rng.shuffle(band_values_candidates)
    rng.shuffle(bandc_values_candidates)

    # Rule counts per difficulty（更克制，逐步增强）
    if difficulty == 'easy':
        counts = dict(sr=3, sc=3, adj=3, left=2, border=min(4, len(border_vals)),
                      corner=min(1, len(corner_vals)), mh=2, mv=2, d=2, ad=2,
                      rect=min(2, len(rectangle_quads_candidates)),
                      band_vals=min(5, len(band_values_candidates)),
                      bandc_vals=min(5, len(bandc_values_candidates)))
    elif difficulty == 'hard':
        counts = dict(sr=1, sc=1, adj=1, left=1, border=min(2, len(border_vals)),
                      corner=min(1, len(corner_vals)), mh=1, mv=1, d=1, ad=1,
                      rect=min(1, len(rectangle_quads_candidates)),
                      band_vals=min(3, len(band_values_candidates)),
                      bandc_vals=min(3, len(bandc_values_candidates)))
    else:  # medium
        counts = dict(sr=2, sc=2, adj=2, left=1, border=min(3, len(border_vals)),
                      corner=min(1, len(corner_vals)), mh=2, mv=2, d=2, ad=2,
                      rect=min(1, len(rectangle_quads_candidates)),
                      band_vals=min(4, len(band_values_candidates)),
                      bandc_vals=min(4, len(bandc_values_candidates)))

    def _pluralize(prefix_single, prefix_multi, items):
        if not items:
            return ""
        if len(items) == 1:
            return f"{prefix_single} {items[0]}"
        return f"{prefix_multi} " + ", ".join(str(x) for x in items)

    def pick_pack(cnts):
        same_row_pairs = same_row_candidates[:cnts['sr']]
        same_col_pairs = same_col_candidates[:cnts['sc']]
        adj_pairs = adj_candidates[:cnts['adj']]
        left_k_rel = left_k_candidates[:cnts['left']]
        border_values = border_vals[:cnts['border']]
        corner_values = corner_vals[:cnts['corner']]
        mirror_h_pairs = mirror_h_candidates[:cnts['mh']]
        mirror_v_pairs = mirror_v_candidates[:cnts['mv']]
        diag_eq_pairs = diag_eq_candidates[:cnts['d']]
        antidiag_eq_pairs = antidiag_eq_candidates[:cnts['ad']]
        rectangle_quads = rectangle_quads_candidates[:cnts['rect']]
        band_values = band_values_candidates[:cnts['band_vals']]
        bandc_values = bandc_values_candidates[:cnts['bandc_vals']]

        # Build human-readable texts (single-line safe, no double quotes)
        texts = []
        for (a, b) in same_row_pairs:
            texts.append(f"Numbers {a} and {b} are in the same row")
        for (a, b) in same_col_pairs:
            texts.append(f"Numbers {a} and {b} are in the same column")
        for (a, b) in adj_pairs:
            texts.append(f"Numbers {a} and {b} are adjacent horizontally or vertically (wrapping allowed)")
        for (x, y, k) in left_k_rel:
            texts.append(f"Number {x} is {k} step{'s' if k != 1 else ''} to the right of number {y} on the same row (wrapping allowed)")
        if border_values:
            if len(border_values) == 1:
                texts.append(_pluralize("Number", "Numbers", border_values) + " is on the outer border of the grid")
            else:
                texts.append(_pluralize("Number", "Numbers", border_values) + " are on the outer border of the grid")
        if corner_values:
            if len(corner_values) == 1:
                texts.append(_pluralize("Number", "Numbers", corner_values) + " is in a corner")
            else:
                texts.append(_pluralize("Number", "Numbers", corner_values) + " are in corners")
        for (a, b) in mirror_h_pairs:
            texts.append(f"Numbers {a} and {b} are mirror-symmetric across the vertical midline in their row (their column indices sum to {n+1})")
        for (a, b) in mirror_v_pairs:
            texts.append(f"Numbers {a} and {b} are mirror-symmetric across the horizontal midline in their column (their row indices sum to {n+1})")
        for (a, b) in diag_eq_pairs:
            texts.append(f"Numbers {a} and {b} lie on the same NW-SE diagonal (row minus column is equal)")
        for (a, b) in antidiag_eq_pairs:
            texts.append(f"Numbers {a} and {b} lie on the same NE-SW diagonal (row plus column is equal)")
        for (p, q, r, s2) in rectangle_quads:
            texts.append(f"Numbers {p}, {q}, {r}, {s2} form the four corners of a rectangle (two rows and two columns)")
        if band_rows and band_values:
            if len(band_values) == 1:
                texts.append("Number " + ", ".join(str(v) for v in band_values) + f" lies only in rows {band_rows[0]} or {band_rows[1]}")
            else:
                texts.append("Numbers " + ", ".join(str(v) for v in band_values) + f" lie only in rows {band_rows[0]} or {band_rows[1]}")
        if band_cols and bandc_values:
            if len(bandc_values) == 1:
                texts.append("Number " + ", ".join(str(v) for v in bandc_values) + f" lies only in columns {band_cols[0]} or {band_cols[1]}")
            else:
                texts.append("Numbers " + ", ".join(str(v) for v in bandc_values) + f" lie only in columns {band_cols[0]} or {band_cols[1]}")

        return {
            'same_row_pairs': same_row_pairs,
            'same_col_pairs': same_col_pairs,
            'adj_pairs': adj_pairs,
            'left_k_rel': left_k_rel,
            'border_values': border_values,
            'corner_values': corner_values,
            'mirror_h_pairs': mirror_h_pairs,
            'mirror_v_pairs': mirror_v_pairs,
            'diag_eq_pairs': diag_eq_pairs,
            'antidiag_eq_pairs': antidiag_eq_pairs,
            'rectangle_quads': rectangle_quads,
            'band_rows': band_rows,
            'band_values': band_values,
            'band_cols': band_cols,
            'bandc_values': bandc_values,
            'texts': texts
        }

    pack = pick_pack(counts)
    # Incremental uniqueness verification and strengthening
    max_increments = 8
    increment_order = ['sr', 'sc', 'adj', 'left', 'mh', 'mv', 'd', 'ad', 'rect', 'band_vals', 'bandc_vals', 'border', 'corner']
    inc_step = 1
    tried = 0
    while not verify_unique_with_rules(n, clues, pack, timeout_ms=60000) and tried < max_increments:
        # increment some counts if possible
        for key in increment_order:
            if key == 'sr':
                counts['sr'] = min(counts['sr'] + inc_step, len(same_row_candidates))
            elif key == 'sc':
                counts['sc'] = min(counts['sc'] + inc_step, len(same_col_candidates))
            elif key == 'adj':
                counts['adj'] = min(counts['adj'] + inc_step, len(adj_candidates))
            elif key == 'left':
                counts['left'] = min(counts['left'] + inc_step, len(left_k_candidates))
            elif key == 'mh':
                counts['mh'] = min(counts['mh'] + inc_step, len(mirror_h_candidates))
            elif key == 'mv':
                counts['mv'] = min(counts['mv'] + inc_step, len(mirror_v_candidates))
            elif key == 'd':
                counts['d'] = min(counts['d'] + inc_step, len(diag_eq_candidates))
            elif key == 'ad':
                counts['ad'] = min(counts['ad'] + inc_step, len(antidiag_eq_candidates))
            elif key == 'rect':
                counts['rect'] = min(counts['rect'] + inc_step, len(rectangle_quads_candidates))
            elif key == 'band_vals':
                counts['band_vals'] = min(counts['band_vals'] + inc_step, len(band_values_candidates))
            elif key == 'bandc_vals':
                counts['bandc_vals'] = min(counts['bandc_vals'] + inc_step, len(bandc_values_candidates))
            elif key == 'border':
                counts['border'] = min(counts['border'] + inc_step, len(border_vals))
            elif key == 'corner':
                counts['corner'] = min(counts['corner'] + inc_step, len(corner_vals))
        pack = pick_pack(counts)
        tried += 1

    # Final check; if still not unique, try a strict fallback raising counts to maxima once
    if not verify_unique_with_rules(n, clues, pack, timeout_ms=60000):
        counts['sr'] = len(same_row_candidates)
        counts['sc'] = len(same_col_candidates)
        counts['adj'] = len(adj_candidates)
        counts['left'] = len(left_k_candidates)
        counts['mh'] = len(mirror_h_candidates)
        counts['mv'] = len(mirror_v_candidates)
        counts['d'] = len(diag_eq_candidates)
        counts['ad'] = len(antidiag_eq_candidates)
        counts['rect'] = min(len(rectangle_quads_candidates), counts.get('rect', 0) + 2)  # avoid explosion
        counts['band_vals'] = len(band_values_candidates)
        counts['bandc_vals'] = len(bandc_values_candidates)
        counts['border'] = len(border_vals)
        counts['corner'] = len(corner_vals)
        pack = pick_pack(counts)
        if not verify_unique_with_rules(n, clues, pack, timeout_ms=60000):
            raise RuntimeError("Failed to build a unique rule pack under given clues.")

    return pack

def render_rules_text(rule_pack):
    """
    Render a single-line text from the rule pack 'texts' list.
    Output contains no double quotes and no braces; items separated by '; '.
    """
    return "; ".join(rule_pack.get('texts', []))