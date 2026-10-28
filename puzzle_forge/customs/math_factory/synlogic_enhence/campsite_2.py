# campsite_0.py
# -*- coding: utf-8 -*-
"""
Complex generator for Tents & Trees puzzles with multiple layered constraints.
Ensures unique solution within 3 minutes and provides a string formatter.
"""

import random
import time
from typing import List, Tuple, Dict, Set
from z3 import Solver, Bool, Or, Not, Sum, If, Implies, sat

TIME_LIMIT = 180  # seconds


def generate_complex_tents_puzzle() -> Dict:
    """Generate a high-complexity tents puzzle with a unique solution."""
    start_time = time.time()
    attempt = 0
    while time.time() - start_time < TIME_LIMIT:
        attempt += 1
        n_rows = random.randint(4, 7)
        n_cols = random.randint(4, 7)
        cells = [(r, c) for r in range(n_rows) for c in range(n_cols)]

        # Trees
        min_trees = max(3, (n_rows + n_cols) // 2)
        max_trees = max(min_trees, (n_rows * n_cols) // 2)
        tree_num = random.randint(min_trees, max_trees)
        tree_positions: Set[Tuple[int, int]] = set(random.sample(cells, tree_num))

        # Random rule toggles
        rule_exact = random.choice([True, False])
        diag_prohibit = random.choice([True, False])
        wind_dir = random.choice(['N', 'S', 'E', 'W'])

        # Regions (contiguous row bands)
        num_regions = random.choice([2, 3])
        split_pts = sorted(random.sample(range(1, n_rows), num_regions - 1))
        bands = [0] + split_pts + [n_rows]
        regions = [[bands[i], bands[i + 1] - 1] for i in range(len(bands) - 1)]

        # Z3 model
        tent = [[Bool(f't_{r}_{c}') for c in range(n_cols)] for r in range(n_rows)]
        s = Solver()

        # Helper functions
        def orth(rc):
            r, c = rc
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < n_rows and 0 <= nc < n_cols:
                    yield nr, nc

        def all_nei(rc):
            r, c = rc
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n_rows and 0 <= nc < n_cols:
                        yield nr, nc

        # tents cannot occupy trees
        for r, c in tree_positions:
            s.add(Not(tent[r][c]))

        # tent must be adjacent to exactly one tree
        for r, c in cells:
            adj_tree = [(nr, nc) in tree_positions for nr, nc in orth((r, c))]
            s.add(Implies(tent[r][c], Sum([If(b, 1, 0) for b in adj_tree]) == 1))

        # per-tree constraint
        for r, c in tree_positions:
            adj_tents = [tent[nr][nc] for nr, nc in orth((r, c))]
            expr = Sum([If(t, 1, 0) for t in adj_tents])
            s.add(expr == 1 if rule_exact else expr <= 1)

        # tents cannot touch per diag_prohibit
        for r, c in cells:
            nei_iter = all_nei if diag_prohibit else orth
            for nr, nc in nei_iter((r, c)):
                if (nr, nc) > (r, c):
                    s.add(Or(Not(tent[r][c]), Not(tent[nr][nc])))

        # wind rule (no tent windward of any tree)
        for r, c in tree_positions:
            if wind_dir == 'N' and r > 0:
                s.add(Not(tent[r - 1][c]))
            elif wind_dir == 'S' and r < n_rows - 1:
                s.add(Not(tent[r + 1][c]))
            elif wind_dir == 'W' and c > 0:
                s.add(Not(tent[r][c - 1]))
            elif wind_dir == 'E' and c < n_cols - 1:
                s.add(Not(tent[r][c + 1]))

        # total tents = trees
        s.add(Sum([If(tent[r][c], 1, 0) for r, c in cells]) == tree_num)

        if s.check() != sat:
            continue
        m = s.model()
        tents = {(r, c) for r, c in cells if m.eval(tent[r][c], model_completion=True)}

        # Row/Col constraints
        row_cons = [sum(1 for c in range(n_cols) if (r, c) in tents) for r in range(n_rows)]
        col_cons = [sum(1 for r in range(n_rows) if (r, c) in tents) for c in range(n_cols)]

        # Region constraints - ensure each >0
        region_cons = []
        valid_region = True
        for r0, r1 in regions:
            cnt = sum(1 for rr in range(r0, r1 + 1) for cc in range(n_cols) if (rr, cc) in tents)
            if cnt == 0:
                valid_region = False
                break
            region_cons.append(cnt)
        if not valid_region:
            continue

        # Lock constraints for uniqueness
        for r in range(n_rows):
            s.add(Sum([If(tent[r][c], 1, 0) for c in range(n_cols)]) == row_cons[r])
        for c in range(n_cols):
            s.add(Sum([If(tent[r][c], 1, 0) for r in range(n_rows)]) == col_cons[c])
        for idx, (r0, r1) in enumerate(regions):
            s.add(Sum([If(tent[rr][cc], 1, 0)
                       for rr in range(r0, r1 + 1)
                       for cc in range(n_cols)]) == region_cons[idx])

        if s.check() != sat:
            continue
        unique_m = s.model()
        s.add(Or([tent[r][c] != unique_m[tent[r][c]] for r, c in cells]))
        if s.check() == sat:
            continue  # not unique

        # Build grids
        solution_grid = [[('T' if (r, c) in tree_positions else
                           ('C' if (r, c) in tents else 'X'))
                          for c in range(n_cols)] for r in range(n_rows)]
        init_grid = [['T' if (r, c) in tree_positions else 'X'
                      for c in range(n_cols)] for r in range(n_rows)]

        return {
            'n_rows': n_rows,
            'n_cols': n_cols,
            'initial_grid': init_grid,
            'row_constraints': row_cons,
            'col_constraints': col_cons,
            'solution_grid': solution_grid,
            'rule_exact': rule_exact,
            'diag_prohibit': diag_prohibit,
            'wind_dir': wind_dir,
            'regions': regions,
            'region_cons': region_cons
        }

    raise RuntimeError(f'Generation failed after {attempt} attempts within {TIME_LIMIT}s')


# ---------- Utility ---------------------------------------------------------
def grid_to_str(grid: List[List[str]]) -> str:
    """Convert grid (list of lists) into string like [[T,C,X],[X,X,T],...] (no quotes)."""
    row_strs = [','.join(row) for row in grid]
    return '[' + ','.join(['[' + r + ']' for r in row_strs]) + ']'