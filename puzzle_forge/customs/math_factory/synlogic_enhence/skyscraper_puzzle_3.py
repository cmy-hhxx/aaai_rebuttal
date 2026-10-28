# skyscraper_puzzle_3.py
# -----------------------------------------------------------------------------
# Generalized & high-complexity custom operators for Skyscraper-like puzzle generation.
# Inverse generation pipeline with uniqueness pinning and multi-layer constraints.
# -----------------------------------------------------------------------------

from typing import List, Dict, Tuple, Any
import random
from z3 import And, Distinct, Sum, If, BoolVal, Solver, Int, sat

# -------------------------- Random choice helpers ----------------------------

def choose_diagonal_type() -> str:
    # Avoid contradictory diagonal patterns; keep either none or strictly increasing main diagonal
    return random.choice(['none', 'main_inc'])

def choose_sides() -> List[str]:
    """
    Randomly choose a non-empty subset of sides from ['left', 'right', 'top', 'bottom'].
    Bias towards including more sides to increase reasoning density.
    """
    sides = ['left', 'right', 'top', 'bottom']
    while True:
        pick = [s for s in sides if random.random() < 0.6]
        if pick:
            return pick

def choose_sides_mask(sides_to_use: List[str], n: int) -> Dict[str, List[bool]]:
    """
    For each selected side, create a boolean mask (length n) indicating which indices are revealed.
    Density sampled in [0.5, 1.0]. For unselected sides, return all False.
    Ensure each selected side reveals at least one index.
    """
    masks = {'left': [False]*n, 'right': [False]*n, 'top': [False]*n, 'bottom': [False]*n}
    for side in masks.keys():
        if side in (sides_to_use or []):
            density = random.uniform(0.5, 1.0)
            m = [random.random() < density for _ in range(n)]
            if not any(m):
                m[random.randrange(n)] = True
            masks[side] = m
    return masks

def choose_fixed_count(n: int) -> int:
    return random.randint(0, min(4, n))

def choose_rule_budget(n: int) -> int:
    # More rules for larger grids, but keep bounded for performance
    return random.randint(max(2, n), 2 * n)

def choose_pin_num(n: int) -> int:
    # Uniqueness pins between n and 2n give a good balance of strength and non-triviality
    return random.randint(n, 2 * n)

def select_pin_positions(n: int, k: int) -> List[Tuple[int, int]]:
    """
    Select k (1-based) distinct positions, spread across rows/cols to maximize information.
    """
    all_cells = [(r, c) for r in range(1, n+1) for c in range(1, n+1)]
    random.shuffle(all_cells)
    chosen = []
    used_r = set(); used_c = set()
    for (r, c) in all_cells:
        if r not in used_r and c not in used_c:
            chosen.append((r, c))
            used_r.add(r); used_c.add(c)
            if len(chosen) >= k:
                return chosen[:k]
    # If not enough, fill remaining arbitrarily
    for rc in all_cells:
        if rc not in chosen:
            chosen.append(rc)
            if len(chosen) >= k:
                break
    return chosen[:k]

# -------------------------- Latin and diagonal construction -------------------

def construct_seed_grid(n: int, diagonal_type: str) -> List[List[int]]:
    """
    Construct an n×n Latin grid using Z3. Optionally enforce main diagonal strictly increasing.
    Fallback: randomized backtracking that respects constraints when Z3 fails (rare for n in [4..7]).
    """
    z = [[Int(f"sg_{i+1}_{j+1}") for j in range(n)] for i in range(n)]
    s = Solver()

    # Domain constraints: 1..n
    for i in range(n):
        for j in range(n):
            s.add(z[i][j] >= 1, z[i][j] <= n)

    # Row Distinct and Column Distinct
    for i in range(n):
        s.add(Distinct(z[i]))
    for j in range(n):
        s.add(Distinct([z[i][j] for i in range(n)]))

    # Optional main diagonal strictly increasing
    if diagonal_type == 'main_inc':
        for i in range(n - 1):
            s.add(z[i][i] < z[i + 1][i + 1])

    if s.check() == sat:
        m = s.model()
        return [[m[z[i][j]].as_long() for j in range(n)] for i in range(n)]

    # Fallback: backtracking Latin with optional diagonal
    values = list(range(1, n + 1))
    grid = [[0] * n for _ in range(n)]
    col_used = [set() for _ in range(n)]

    def place_row(r: int) -> bool:
        if r == n:
            return True
        cand_vals = values[:]
        random.shuffle(cand_vals)

        chosen = [0] * n
        used_row = set()

        def dfs_c(c: int) -> bool:
            if c == n:
                if diagonal_type == 'main_inc' and r > 0:
                    if not (grid[r - 1][r - 1] < chosen[r]):
                        return False
                grid[r] = chosen[:]
                for j in range(n):
                    col_used[j].add(grid[r][j])
                ok = place_row(r + 1)
                if ok:
                    return True
                for j in range(n):
                    col_used[j].remove(grid[r][j])
                grid[r] = [0] * n
                return False

            random.shuffle(cand_vals)
            for v in cand_vals:
                if v in used_row:
                    continue
                if v in col_used[c]:
                    continue
                if diagonal_type == 'main_inc' and c == r and r > 0 and grid[r - 1][r - 1] >= v:
                    continue
                chosen[c] = v
                used_row.add(v)
                if dfs_c(c + 1):
                    return True
                used_row.remove(v)
            return False

        return dfs_c(0)

    if place_row(0):
        return grid

    # Last resort: cyclic Latin; if diagonal required, try random symbol permutations
    base = [[((i + j) % n) + 1 for j in range(n)] for i in range(n)]
    if diagonal_type == 'main_inc':
        for _ in range(50):
            perm = list(range(1, n + 1))
            random.shuffle(perm)
            mp = {v: perm[v - 1] for v in range(1, n + 1)}
            g2 = [[mp[base[i][j]] for j in range(n)] for i in range(n)]
            if all(g2[i][i] < g2[i + 1][i + 1] for i in range(n - 1)):
                return g2
    return base

# -------------------------- SMT constraints builders --------------------------

def function_1(grid, rows: List[str], cols: List[str], n: int):
    """
    Domain + Latin constraints:
    - Each cell in [1..n].
    - Each row Distinct.
    - Each column Distinct.
    """
    cons = []
    for r in rows:
        for c in cols:
            cons.append(And(grid[(r, c)] >= 1, grid[(r, c)] <= n))
    for r in rows:
        cons.append(Distinct([grid[(r, c)] for c in cols]))
    for c in cols:
        cons.append(Distinct([grid[(r, c)] for r in rows]))
    return And(cons)

def build_diag_constraint(grid, rows: List[str], cols: List[str], n: int, diagonal_type: str):
    """
    Conditionally apply diagonal constraints:
    - 'main_inc': grid[(rows[i], cols[i])] < grid[(rows[i+1], cols[i+1])] for all i
    - 'none': no constraint (returns True).
    """
    if diagonal_type == 'main_inc':
        return And([grid[(rows[i], cols[i])] < grid[(rows[i + 1], cols[i + 1])] for i in range(n - 1)])
    return BoolVal(True)

def _visible_count_expr(line: List):
    """
    SMT visibility counter: counts buildings visible from one end.
    First element visible; j-th visible iff strictly higher than all previous.
    """
    terms = []
    for j in range(len(line)):
        cond = BoolVal(True) if j == 0 else And([line[j] > line[k] for k in range(j)])
        terms.append(If(cond, 1, 0))
    return Sum(terms)

def build_visibility_constraints_masked(grid, rows: List[str], cols: List[str],
                                        left: List[int], right: List[int],
                                        top: List[int], bottom: List[int],
                                        sides_to_use: List[str],
                                        left_mask: List[bool], right_mask: List[bool],
                                        top_mask: List[bool], bottom_mask: List[bool]):
    """
    Build SMT visibility constraints only for selected sides and masked indices.
    """
    use = set(sides_to_use or [])
    cons = []

    if 'left' in use and left_mask:
        for r_idx, r in enumerate(rows):
            if left_mask[r_idx]:
                row_line = [grid[(r, c)] for c in cols]
                cons.append(_visible_count_expr(row_line) == left[r_idx])

    if 'right' in use and right_mask:
        for r_idx, r in enumerate(rows):
            if right_mask[r_idx]:
                row_line_rev = [grid[(r, c)] for c in reversed(cols)]
                cons.append(_visible_count_expr(row_line_rev) == right[r_idx])

    if 'top' in use and top_mask:
        for c_idx, c in enumerate(cols):
            if top_mask[c_idx]:
                col_line = [grid[(r, c)] for r in rows]
                cons.append(_visible_count_expr(col_line) == top[c_idx])

    if 'bottom' in use and bottom_mask:
        for c_idx, c in enumerate(cols):
            if bottom_mask[c_idx]:
                col_line_rev = [grid[(r, c)] for r in reversed(rows)]
                cons.append(_visible_count_expr(col_line_rev) == bottom[c_idx])

    if not cons:
        return BoolVal(True)
    return And(cons)

# -------------------------- Pure-Python visibility helpers --------------------

def _visible_count_py(line_vals: List[int]) -> int:
    count = 0
    max_so_far = -10**9
    for v in line_vals:
        if v > max_so_far:
            count += 1
            max_so_far = v
    return count

def compute_sides(grid_vals: List[List[int]]) -> Dict[str, List[int]]:
    """
    Compute visibility arrays for all four sides from the concrete grid values.
    """
    n = len(grid_vals)
    left = [_visible_count_py(row) for row in grid_vals]
    right = [_visible_count_py(list(reversed(row))) for row in grid_vals]
    top = []
    bottom = []
    for c in range(n):
        col = [grid_vals[r][c] for r in range(n)]
        top.append(_visible_count_py(col))
        bottom.append(_visible_count_py(list(reversed(col))))
    return {'left': left, 'right': right, 'top': top, 'bottom': bottom}

# -------------------------- Random subset and fixed sampling ------------------

def choose_fixed_from_seed(seed_grid: List[List[int]], k: int) -> Dict[Tuple[int, int], int]:
    """
    Sample k distinct cells (1-based indices) from seed_grid as fixed clues.
    Returns dict {(r, c): value}.
    """
    n = len(seed_grid)
    coords = [(r + 1, c + 1) for r in range(n) for c in range(n)]
    random.shuffle(coords)
    chosen = coords[:max(0, min(k, n * n))]
    return { (r, c): seed_grid[r - 1][c - 1] for (r, c) in chosen }

# -------------------------- Randomized internal rules -------------------------

def generate_rules(seed_grid: List[List[int]], rule_budget: int) -> List[Dict[str, Any]]:
    """
    Generate a list of randomized, seed-consistent rules.
    Rule types:
    - pair_cmp: compare two cells with op in {<, >, <=, >=, ==, !=}
    - row_peak: the maximum in a row is at a specific column
    - col_peak: the maximum in a column is at a specific row
    - edge_rel: compare row first/last or col first/last
    - pair_sum_eq: sum of two cells equals target
    """
    n = len(seed_grid)
    rules: List[Dict[str, Any]] = []
    cells = [(r, c) for r in range(1, n+1) for c in range(1, n+1)]
    def val(rc): return seed_grid[rc[0]-1][rc[1]-1]

    def pick_op(a: int, b: int) -> str:
        ops = []
        if a < b: ops += ['<', '<=', '!=']
        if a > b: ops += ['>', '>=', '!=']
        if a == b: ops += ['==', '<=', '>=']
        return random.choice(ops or ['=='])

    # pair_cmp rules
    pair_cnt = max(1, rule_budget // 3)
    for _ in range(pair_cnt):
        rc1, rc2 = random.sample(cells, 2)
        a, b = val(rc1), val(rc2)
        op = pick_op(a, b)
        rules.append({'type': 'pair_cmp', 'rc1': rc1, 'rc2': rc2, 'op': op})

    # row_peak and col_peak
    rp_cnt = random.randint(0, max(1, rule_budget // 4))
    for _ in range(rp_cnt):
        r = random.randint(1, n)
        row_vals = seed_grid[r-1]
        k = 1 + row_vals.index(max(row_vals))
        rules.append({'type': 'row_peak', 'r': r, 'c': k})
    cp_cnt = random.randint(0, max(1, rule_budget // 4))
    for _ in range(cp_cnt):
        c = random.randint(1, n)
        col_vals = [seed_grid[r-1][c-1] for r in range(1, n+1)]
        k = 1 + col_vals.index(max(col_vals))
        rules.append({'type': 'col_peak', 'r': k, 'c': c})

    # edge_rel
    er_cnt = random.randint(0, max(1, rule_budget // 4))
    for _ in range(er_cnt):
        if random.random() < 0.5:
            r = random.randint(1, n)
            a = seed_grid[r-1][0]; b = seed_grid[r-1][n-1]
            op = pick_op(a, b)
            rules.append({'type': 'edge_rel', 'axis': 'row', 'r': r, 'c1': 1, 'c2': n, 'op': op})
        else:
            c = random.randint(1, n)
            a = seed_grid[0][c-1]; b = seed_grid[n-1][c-1]
            op = pick_op(a, b)
            rules.append({'type': 'edge_rel', 'axis': 'col', 'c': c, 'r1': 1, 'r2': n, 'op': op})

    # pair_sum_eq
    ps_cnt = random.randint(0, max(1, rule_budget // 5))
    for _ in range(ps_cnt):
        r1, c1 = random.randint(1, n), random.randint(1, n)
        r2, c2 = random.randint(1, n), random.randint(1, n)
        while (r2, c2) == (r1, c1):
            r2, c2 = random.randint(1, n), random.randint(1, n)
        target = seed_grid[r1-1][c1-1] + seed_grid[r2-1][c2-1]
        rules.append({'type': 'pair_sum_eq', 'rc1': (r1, c1), 'rc2': (r2, c2), 'target': target})

    random.shuffle(rules)
    return rules[:max(1, rule_budget)]

def build_dynamic_rules(grid, rows: List[str], cols: List[str], rules: List[Dict[str, Any]]):
    """
    Encode the randomized rule set as an SMT And(...) constraint.
    """
    cons = []
    for rule in (rules or []):
        t = rule.get('type')
        if t == 'pair_cmp':
            r1, c1 = rule['rc1']
            r2, c2 = rule['rc2']
            a = grid[(f'R{r1}', f'C{c1}')]
            b = grid[(f'R{r2}', f'C{c2}')]
            op = rule['op']
            if op == '<':
                cons.append(a < b)
            elif op == '>':
                cons.append(a > b)
            elif op == '<=':
                cons.append(a <= b)
            elif op == '>=':
                cons.append(a >= b)
            elif op == '==':
                cons.append(a == b)
            elif op == '!=':
                cons.append(a != b)
        elif t == 'row_peak':
            r, c = rule['r'], rule['c']
            peak = grid[(f'R{r}', f'C{c}')]
            others = [grid[(f'R{r}', f'C{j}')] for j in range(1, len(cols)+1) if j != c]
            cons.append(And([peak > x for x in others]) if others else BoolVal(True))
        elif t == 'col_peak':
            r, c = rule['r'], rule['c']
            peak = grid[(f'R{r}', f'C{c}')]
            others = [grid[(f'R{i}', f'C{c}')] for i in range(1, len(rows)+1) if i != r]
            cons.append(And([peak > x for x in others]) if others else BoolVal(True))
        elif t == 'edge_rel':
            op = rule['op']
            if rule['axis'] == 'row':
                r = rule['r']; c1 = rule['c1']; c2 = rule['c2']
                a = grid[(f'R{r}', f'C{c1}')]
                b = grid[(f'R{r}', f'C{c2}')]
            else:
                c = rule['c']; r1 = rule['r1']; r2 = rule['r2']
                a = grid[(f'R{r1}', f'C{c}')]
                b = grid[(f'R{r2}', f'C{c}')]
            if op == '<':
                cons.append(a < b)
            elif op == '>':
                cons.append(a > b)
            elif op == '<=':
                cons.append(a <= b)
            elif op == '>=':
                cons.append(a >= b)
            elif op == '==':
                cons.append(a == b)
            elif op == '!=':
                cons.append(a != b)
        elif t == 'pair_sum_eq':
            r1, c1 = rule['rc1']; r2, c2 = rule['rc2']; target = rule['target']
            a = grid[(f'R{r1}', f'C{c1}')]
            b = grid[(f'R{r2}', f'C{c2}')]
            cons.append(a + b == target)
        else:
            cons.append(BoolVal(True))
    return And(cons) if cons else BoolVal(True)

# -------------------------- Composite high-level constraints ------------------

def _snake_path(n: int) -> List[Tuple[int, int]]:
    """
    Build snake path: row1 left->right, row2 right->left, row3 left->right, ...
    1-based coordinates.
    """
    path = []
    for r in range(1, n+1):
        cols = range(1, n+1) if r % 2 == 1 else range(n, 0, -1)
        for c in cols:
            path.append((r, c))
    return path

def generate_composite_spec(seed_grid: List[List[int]]) -> Dict[str, Any]:
    """
    Build composite constraints specification derived from seed_grid.
    Includes:
    - checker (black/white sum relation)
    - diag_sum_rel (main vs anti diagonal sums)
    - snake_pairs (subset of adjacent relations along snake path)
    - rowcol_sum_targets (sum(row r)+sum(col c)=target)
    - block_targets (2x2 block sums equals target)
    """
    n = len(seed_grid)
    spec: Dict[str, Any] = {}

    # Checker sums
    black = []; white = []
    for r in range(1, n+1):
        for c in range(1, n+1):
            if (r + c) % 2 == 0:
                black.append(seed_grid[r-1][c-1])
            else:
                white.append(seed_grid[r-1][c-1])
    sb = sum(black); sw = sum(white)
    rel = random.choice(['==', '>=', '<='])
    delta = sb - sw if rel == '==' else max(0, sb - sw) if rel == '>=' else max(0, sw - sb)
    spec['checker'] = {'rel': rel, 'delta': delta}

    # Diagonal sums
    main = sum(seed_grid[i][i] for i in range(n))
    anti = sum(seed_grid[i][n-1-i] for i in range(n))
    rel2 = random.choice(['==', '>=', '<='])
    delta2 = main - anti if rel2 == '==' else max(0, main - anti) if rel2 == '>=' else max(0, anti - main)
    spec['diag_sum_rel'] = {'rel': rel2, 'delta': delta2}

    # Snake pairs (mask subset)
    path = _snake_path(n)
    pairs = []
    density = random.uniform(0.3, 0.7)
    for i in range(len(path)-1):
        if random.random() < density:
            (r1, c1) = path[i]; (r2, c2) = path[i+1]
            a = seed_grid[r1-1][c1-1]; b = seed_grid[r2-1][c2-1]
            if a < b: op = '<'
            elif a > b: op = '>'
            else: op = '=='
            pairs.append({'rc1': (r1, c1), 'rc2': (r2, c2), 'op': op})
    spec['snake_pairs'] = pairs

    # Row+Col sum targets (few)
    rct = []
    for _ in range(random.randint(1, max(1, n//2))):
        r = random.randint(1, n); c = random.randint(1, n)
        target = sum(seed_grid[r-1]) + sum(seed_grid[i][c-1] for i in range(n))
        rct.append({'r': r, 'c': c, 'target': target})
    spec['rowcol_sum_targets'] = rct

    # 2x2 block sum targets (if n>=4)
    blks = []
    if n >= 4:
        cnt = random.randint(1, max(1, n-3))
        for _ in range(cnt):
            r = random.randint(1, n-1)
            c = random.randint(1, n-1)
            target = seed_grid[r-1][c-1] + seed_grid[r-1][c] + seed_grid[r][c-1] + seed_grid[r][c]
            blks.append({'r': r, 'c': c, 'target': target})
    spec['block_targets'] = blks

    return spec

def build_composite_constraints(grid, rows: List[str], cols: List[str], spec: Dict[str, Any]):
    """
    Build Z3 constraints for composite spec:
    - checker: sum(black) rel sum(white)+delta
    - diag_sum_rel: sum(main) rel sum(anti)+delta
    - snake_pairs: pairwise comparisons along snake path (subset)
    - rowcol_sum_targets: sum(row r)+sum(col c) == target
    - block_targets: 2x2 block sums == target
    """
    cons = []
    n = len(rows)

    # Checker
    chk = spec.get('checker')
    if chk:
        black = []; white = []
        for r in range(1, n+1):
            for c in range(1, n+1):
                v = grid[(f'R{r}', f'C{c}')]
                if (r + c) % 2 == 0:
                    black.append(v)
                else:
                    white.append(v)
        s_black = Sum(black) if black else 0
        s_white = Sum(white) if white else 0
        rel = chk.get('rel'); delta = chk.get('delta', 0)
        if rel == '==':
            cons.append(s_black == s_white + delta)
        elif rel == '>=':
            cons.append(s_black >= s_white + delta)
        elif rel == '<=':
            cons.append(s_black <= s_white + delta)

    # Diagonal sums
    dsr = spec.get('diag_sum_rel')
    if dsr:
        main = Sum([grid[(rows[i], cols[i])] for i in range(n)])
        anti = Sum([grid[(rows[i], cols[n-1-i])] for i in range(n)])
        rel = dsr.get('rel'); delta = dsr.get('delta', 0)
        if rel == '==':
            cons.append(main == anti + delta)
        elif rel == '>=':
            cons.append(main >= anti + delta)
        elif rel == '<=':
            cons.append(main <= anti + delta)

    # Snake pairs
    for pr in spec.get('snake_pairs', []):
        r1, c1 = pr['rc1']; r2, c2 = pr['rc2']; op = pr['op']
        a = grid[(f'R{r1}', f'C{c1}')]; b = grid[(f'R{r2}', f'C{c2}')]
        if op == '<':
            cons.append(a < b)
        elif op == '>':
            cons.append(a > b)
        else:
            cons.append(a == b)

    # Row+Col sum targets
    for it in spec.get('rowcol_sum_targets', []):
        r = it['r']; c = it['c']; target = it['target']
        s_row = Sum([grid[(f'R{r}', f'C{j}')] for j in range(1, n+1)])
        s_col = Sum([grid[(f'R{i}', f'C{c}')] for i in range(1, n+1)])
        cons.append(s_row + s_col == target)

    # 2x2 block targets
    for it in spec.get('block_targets', []):
        r = it['r']; c = it['c']; target = it['target']
        cells = [
            grid[(f'R{r}', f'C{c}')],
            grid[(f'R{r}', f'C{c+1}')],
            grid[(f'R{r+1}', f'C{c}')],
            grid[(f'R{r+1}', f'C{c+1}')]
        ]
        cons.append(Sum(cells) == target)

    return And(cons) if cons else BoolVal(True)

# -------------------------- Description formatting helpers -------------------

def _mask_apply(arr: List[int], mask: List[bool]) -> List[Any]:
    return [arr[i] if (i < len(mask) and mask[i]) else '_' for i in range(len(arr))]

def format_sides_desc_masked(sides_to_use: List[str],
                             left: List[int], right: List[int],
                             top: List[int], bottom: List[int],
                             left_mask: List[bool], right_mask: List[bool],
                             top_mask: List[bool], bottom_mask: List[bool]) -> str:
    """
    Build a concise one-line description with masked arrays where unrevealed entries are '_'.
    Only include sides present in sides_to_use.
    """
    parts = []
    use = set(sides_to_use or [])
    if 'left' in use:
        parts.append(f"[left={_mask_apply(left, left_mask)}]")
    if 'right' in use:
        parts.append(f"[right={_mask_apply(right, right_mask)}]")
    if 'top' in use:
        parts.append(f"[top={_mask_apply(top, top_mask)}]")
    if 'bottom' in use:
        parts.append(f"[bottom={_mask_apply(bottom, bottom_mask)}]")
    return " ".join(parts) if parts else "[no visibility clues]"

def format_fixed_desc(fixed: Dict[Tuple[int, int], int]) -> str:
    if not fixed:
        return "[]"
    items = [f"({r}, {c}) -> {v}" for (r, c), v in fixed.items()]
    return "[" + ", ".join(items) + "]"

def format_rules_desc(rules: List[Dict[str, Any]], n: int) -> str:
    """
    Human-friendly rules description. Also explain uncommon rule types briefly.
    """
    if not rules:
        return "无额外规则"
    out = []
    for idx, rule in enumerate(rules, 1):
        t = rule.get('type')
        if t == 'pair_cmp':
            r1, c1 = rule['rc1']; r2, c2 = rule['rc2']; op = rule['op']
            out.append(f"{idx}. 位置({r1},{c1}) {op} 位置({r2},{c2})")
        elif t == 'row_peak':
            r, c = rule['r'], rule['c']
            out.append(f"{idx}. 行 {r} 的最高楼在列 {c}（row_peak：该行此列的数字严格大于该行其它列）")
        elif t == 'col_peak':
            r, c = rule['r'], rule['c']
            out.append(f"{idx}. 列 {c} 的最高楼在行 {r}（col_peak：该列此行的数字严格大于该列其它行）")
        elif t == 'edge_rel':
            op = rule['op']
            if rule['axis'] == 'row':
                r = rule['r']; c1 = rule['c1']; c2 = rule['c2']
                out.append(f"{idx}. 行 {r} 的第 {c1} 列 {op} 第 {c2} 列（同一行两端相对大小）")
            else:
                c = rule['c']; r1 = rule['r1']; r2 = rule['r2']
                out.append(f"{idx}. 列 {c} 的第 {r1} 行 {op} 第 {r2} 行（同一列首尾相对大小）")
        elif t == 'pair_sum_eq':
            r1, c1 = rule['rc1']; r2, c2 = rule['rc2']; target = rule['target']
            out.append(f"{idx}. 位置({r1},{c1}) 与 位置({r2},{c2}) 之和等于 {target}")
        else:
            out.append(f"{idx}. 其他规则")
    return "; ".join(out)

def format_composite_desc(spec: Dict[str, Any]) -> str:
    """
    Summarize composite constraints in plain language.
    """
    parts = []
    chk = spec.get('checker')
    if chk:
        parts.append(f"棋盘黑白格和之关系：sum_black {chk.get('rel')} sum_white + {chk.get('delta')}")
    dsr = spec.get('diag_sum_rel')
    if dsr:
        parts.append(f"对角线和关系：sum_main {dsr.get('rel')} sum_anti + {dsr.get('delta')}")
    sp = spec.get('snake_pairs', [])
    if sp:
        parts.append(f"蛇形路径相邻比较条目数 {len(sp)}（蛇形：第1行从左到右，第2行从右到左，依次往复）")
    rct = spec.get('rowcol_sum_targets', [])
    if rct:
        parts.append(f"行列和目标共 {len(rct)} 条（sum(row r)+sum(col c) 等于给定值）")
    blks = spec.get('block_targets', [])
    if blks:
        parts.append(f"2×2 成块和目标共 {len(blks)} 条")
    return "; ".join(parts) if parts else "无复合约束"