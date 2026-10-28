# sudoku_0.py

# Helper functions for the YAML specification with advanced rule bundle
from typing import List, Tuple, Set, Dict, Optional
import random
import time


def choose_one(options: List[str]):
    """Return a random element from a list of options."""
    if not options:
        raise ValueError("choose_one requires a non-empty list")
    return random.choice(list(options))


def make_index_list(n: int) -> List[str]:
    """Return ['0', '1', ..., str(n-1)] as string indices for rows/cols."""
    return [str(i) for i in range(n)]


def make_blocks(n: int) -> List[List[Tuple[str, str]]]:
    """Build 3x3 block coordinate sets for standard 9x9 Sudoku as string indices."""
    if n != 9:
        raise ValueError("This helper assumes n=9 for standard Sudoku blocks.")
    blocks = []
    for br in range(3):
        for bc in range(3):
            block = []
            r0 = br * 3
            c0 = bc * 3
            for dr in range(3):
                for dc in range(3):
                    block.append((str(r0 + dr), str(c0 + dc)))
            blocks.append(block)
    return blocks


def format_answer_tuple(answer_matrix: List[List[int]]) -> str:
    """
    Convert a 9x9 list of lists into a nested tuple string:
    ((r1c1, ..., r1c9), (r2c1, ..., r2c9), ..., (r9c1, ..., r9c9))
    """
    tuples = tuple(tuple(int(x) for x in row) for row in answer_matrix)
    return str(tuples)


# ------------------------ Constructive full Sudoku generator ------------------------

def _base_pattern(r: int, c: int, base: int, side: int) -> int:
    """Sudoku Latin base pattern: returns 0..8"""
    return (base * (r % base) + r // base + c) % side


def gen_full_sudoku(n: int) -> List[List[int]]:
    """
    Construct a full valid 9x9 Sudoku solution by:
    1) Using the Latin base pattern
    2) Randomly permuting rows within bands, columns within stacks
    3) Randomly permuting bands and stacks
    4) Randomly permuting digits 1..9
    """
    if n != 9:
        raise ValueError("Only 9x9 supported in this generator")

    base = 3
    side = base * base

    # Step 1: initial Latin base grid (values 1..9)
    grid = [[[_base_pattern(r, c, base, side) + 1][0] for c in range(side)] for r in range(side)]

    # Helpers for random permutations
    def shuffled(seq):
        seq = list(seq)
        random.shuffle(seq)
        return seq

    # Step 2: shuffle rows within bands and bands themselves
    rows = []
    band_order = shuffled(range(base))
    for b in band_order:
        band_rows = [b * base + r for r in shuffled(range(base))]
        rows.extend(band_rows)

    # Step 3: shuffle cols within stacks and stacks themselves
    cols = []
    stack_order = shuffled(range(base))
    for s in stack_order:
        stack_cols = [s * base + c for c in shuffled(range(base))]
        cols.extend(stack_cols)

    grid = [[grid[r][c] for c in cols] for r in rows]

    # Step 4: permute digits 1..9
    digits = list(range(1, 10))
    digit_perm = shuffled(digits)
    mapping = {d: digit_perm[d - 1] for d in digits}
    for i in range(side):
        for j in range(side):
            grid[i][j] = mapping[grid[i][j]]

    return grid


# ------------------------ Generic puzzle text rendering ------------------------

def build_givens_from_mask(sol_grid: List[List[int]],
                           mask_positions: List[Tuple[int, int]]) -> List[Tuple[str, str, int]]:
    """Return givens as (r_str, c_str, v)."""
    out = []
    for (i, j) in mask_positions:
        out.append((str(i), str(j), int(sol_grid[i][j])))
    return out


def grid_to_lines(sol_grid: List[List[int]],
                  mask_positions: List[Tuple[int, int]],
                  blank_symbol: str = "X") -> List[str]:
    """
    Render masked grid to 9 text lines, filling blanks with blank_symbol.
    Add '|' separators between 3x3 blocks to improve readability: 'abc|def|ghi'
    """
    keep = set(mask_positions)
    lines = []
    n = len(sol_grid)
    for i in range(n):
        row_chars = []
        for j in range(n):
            ch = str(sol_grid[i][j]) if (i, j) in keep else blank_symbol
            row_chars.append(ch)
            if j in (2, 5) and j + 1 < n:
                row_chars.append("|")
        lines.append("".join(row_chars))
    return lines


# ------------------------ Uniqueness check helpers ------------------------

def _unique_check_with_z3(sol_grid: List[List[int]],
                          keep_cells: Set[Tuple[int, int]],
                          n: int) -> bool:
    """Check uniqueness under standard Sudoku constraints with givens keep_cells."""
    try:
        from z3 import Solver, Int, Distinct, And, Or, sat
    except Exception:
        return False

    x = [[Int(f"x_{i}_{j}") for j in range(n)] for i in range(n)]
    s = Solver()

    for i in range(n):
        for j in range(n):
            s.add(And(x[i][j] >= 1, x[i][j] <= 9))

    for i in range(n):
        s.add(Distinct(x[i]))
    for j in range(n):
        s.add(Distinct([x[i][j] for i in range(n)]))

    for br in range(0, n, 3):
        for bc in range(0, n, 3):
            cells = [x[br + di][bc + dj] for di in range(3) for dj in range(3)]
            s.add(Distinct(cells))

    for (i, j) in keep_cells:
        s.add(x[i][j] == sol_grid[i][j])

    if s.check() != sat:
        return False
    m = s.model()

    diff_list = []
    for i in range(n):
        for j in range(n):
            v = m.eval(x[i][j]).as_long()
            diff_list.append(x[i][j] != v)

    s.push()
    s.add(Or(diff_list))
    res = s.check()
    s.pop()
    return res != sat


def has_unique_solution_std(sol_grid: List[List[int]],
                            keep: List[Tuple[int, int]],
                            n: int) -> bool:
    """Expose standard uniqueness check as a reusable helper."""
    return _unique_check_with_z3(sol_grid, set(keep), n)


# ------------------------ Symmetry pairing ------------------------

def _gen_symmetric_pairs(n: int, symmetry: str) -> List[List[Tuple[int, int]]]:
    """
    Create disjoint groups of coordinates to remove together for a given symmetry.
    Each group is either a singleton [(r,c)] or a pair [(r1,c1),(r2,c2)].
    """
    pairs = []
    seen = set()

    def rot180(r, c): return (n - 1 - r, n - 1 - c)
    def mirror_h(r, c): return (n - 1 - r, c)
    def mirror_v(r, c): return (r, n - 1 - c)

    for r in range(n):
        for c in range(n):
            if (r, c) in seen:
                continue
            if symmetry == 'none':
                pairs.append([(r, c)])
                seen.add((r, c))
            elif symmetry == 'rot180':
                rr, cc = rot180(r, c)
                if (rr, cc) == (r, c):
                    pairs.append([(r, c)])
                    seen.add((r, c))
                else:
                    group = sorted([(r, c), (rr, cc)])
                    a, b = group[0], group[1]
                    if a not in seen and b not in seen:
                        pairs.append(group)
                        seen.add(a); seen.add(b)
            elif symmetry == 'mirror_h':
                rr, cc = mirror_h(r, c)
                if (rr, cc) == (r, c):
                    pairs.append([(r, c)])
                    seen.add((r, c))
                else:
                    group = sorted([(r, c), (rr, cc)])
                    a, b = group[0], group[1]
                    if a not in seen and b not in seen:
                        pairs.append(group)
                        seen.add(a); seen.add(b)
            elif symmetry == 'mirror_v':
                rr, cc = mirror_v(r, c)
                if (rr, cc) == (r, c):
                    pairs.append([(r, c)])
                    seen.add((r, c))
                else:
                    group = sorted([(r, c), (rr, cc)])
                    a, b = group[0], group[1]
                    if a not in seen and b not in seen:
                        pairs.append(group)
                        seen.add(a); seen.add(b)
            else:
                pairs.append([(r, c)])
                seen.add((r, c))

    random.shuffle(pairs)
    return pairs


# ------------------------ Unique puzzle mask generation ------------------------

def _block_index_9(i: int, j: int) -> int:
    """Return 0..8 block index for 9x9."""
    return (i // 3) * 3 + (j // 3)


def make_unique_puzzle_mask(sol_grid: List[List[int]],
                            n: int,
                            symmetry: str,
                            givens_min: int,
                            givens_max: int,
                            min_row: int,
                            min_col: int,
                            min_block: int) -> List[Tuple[int, int]]:
    """
    Produce a set of coordinates to KEEP (givens), ensuring a unique solution and
    attempting to keep the number of givens within [givens_min, givens_max],
    while enforcing row/col/block minimum givens.
    """
    keep: Set[Tuple[int, int]] = {(i, j) for i in range(n) for j in range(n)}
    groups = _gen_symmetric_pairs(n, symmetry)

    def respects_distribution(after_keep: Set[Tuple[int, int]]) -> bool:
        row_counts = [0] * n
        col_counts = [0] * n
        block_counts = [0] * 9
        for (i, j) in after_keep:
            row_counts[i] += 1
            col_counts[j] += 1
            block_counts[_block_index_9(i, j)] += 1
        return (all(rc >= min_row for rc in row_counts)
                and all(cc >= min_col for cc in col_counts)
                and all(bc >= min_block for bc in block_counts))

    for grp in groups:
        if len(keep) <= givens_max:
            break
        if len(keep) - len(grp) < givens_min:
            continue
        new_keep = keep.difference(grp)
        if not respects_distribution(new_keep):
            continue
        if _unique_check_with_z3(sol_grid, new_keep, n):
            keep = new_keep

    if len(keep) > givens_max:
        for grp in groups:
            if len(keep) <= givens_max:
                break
            if any(cell not in keep for cell in grp):
                continue
            if len(keep) - len(grp) < givens_min:
                continue
            new_keep = keep.difference(grp)
            if not respects_distribution(new_keep):
                continue
            if _unique_check_with_z3(sol_grid, new_keep, n):
                keep = new_keep

    while len(keep) < givens_min:
        all_cells = [(i, j) for i in range(n) for j in range(n)]
        random.shuffle(all_cells)
        for cand in all_cells:
            if cand in keep:
                continue
            new_keep = set(keep)
            new_keep.add(cand)
            if respects_distribution(new_keep):
                keep = new_keep
                break
        else:
            break

    if not _unique_check_with_z3(sol_grid, keep, n):
        keep = {(i, j) for i in range(n) for j in range(n)
                if i == n // 2 or j == n // 2 or i == j or i + j == n - 1}
        all_cells = [(i, j) for i in range(n) for j in range(n)]
        random.shuffle(all_cells)
        for cand in all_cells:
            if (cand in keep):
                continue
            new_keep = set(keep); new_keep.add(cand)
            if _unique_check_with_z3(sol_grid, new_keep, n):
                keep = new_keep
                break
        if not _unique_check_with_z3(sol_grid, keep, n):
            keep = {(i, j) for i in range(n) for j in range(n)}

    return sorted(list(keep))


def make_puzzle_mask_interplay(sol_grid: List[List[int]],
                               n: int,
                               symmetry: str,
                               givens_min: int,
                               givens_max: int,
                               min_row: int,
                               min_col: int,
                               min_block: int) -> List[Tuple[int, int]]:
    """
    Build a givens mask that tends to require additional rules:
    1) Start from a standard-unique mask (as before).
    2) Then try to remove some givens to make the puzzle NON-UNIQUE under standard Sudoku,
       while still respecting givens_min/givens_max and distribution constraints (row/col/block).
       This encourages the final uniqueness to rely on extra rules.
    """
    base_keep = set(make_unique_puzzle_mask(sol_grid, n, symmetry, givens_min, givens_max,
                                            min_row, min_col, min_block))

    def respects_distribution(after_keep: Set[Tuple[int, int]]) -> bool:
        row_counts = [0] * n
        col_counts = [0] * n
        block_counts = [0] * 9
        for (i, j) in after_keep:
            row_counts[i] += 1
            col_counts[j] += 1
            block_counts[_block_index_9(i, j)] += 1
        return (all(rc >= min_row for rc in row_counts)
                and all(cc >= min_col for cc in col_counts)
                and all(bc >= min_block for bc in block_counts))

    # If already non-unique under standard (unlikely), return directly
    if not _unique_check_with_z3(sol_grid, base_keep, n):
        return sorted(list(base_keep))

    # Try to remove a small number of givens (group-wise) to break standard uniqueness
    groups = _gen_symmetric_pairs(n, symmetry)
    random.shuffle(groups)
    keep = set(base_keep)
    attempts = 0
    max_attempts = 300
    while attempts < max_attempts and _unique_check_with_z3(sol_grid, keep, n):
        attempts += 1
        candidate_groups = [grp for grp in groups if all(cell in keep for cell in grp)]
        if not candidate_groups:
            break
        grp = random.choice(candidate_groups)
        new_keep = keep.difference(grp)
        if len(new_keep) < givens_min:
            continue
        if not respects_distribution(new_keep):
            continue
        if not _unique_check_with_z3(sol_grid, new_keep, n):
            keep = new_keep
            break
        else:
            # Occasionally accept neutral removal to explore (low probability)
            if random.random() < 0.2:
                keep = new_keep

    return sorted(list(keep))


# ------------------------ Rule bundle generation for variability ------------------------

def _adjacent_pairs(n: int) -> List[Tuple[int, int, int, int]]:
    """List all right and down adjacent cell pairs (i,j)-(i,j+1) and (i,j)-(i+1,j)."""
    pairs = []
    for i in range(n):
        for j in range(n):
            if j + 1 < n:
                pairs.append((i, j, i, j + 1))
            if i + 1 < n:
                pairs.append((i, j, i + 1, j))
    return pairs


def _knight_pairs(n: int) -> List[Tuple[int, int, int, int]]:
    """List all knight-move pairs (L-shape by chess knight)."""
    deltas = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
    pairs = set()
    for i in range(n):
        for j in range(n):
            for di, dj in deltas:
                ii = i + di
                jj = j + dj
                if 0 <= ii < n and 0 <= jj < n:
                    a = (i, j, ii, jj)
                    b = (ii, jj, i, j)
                    if b not in pairs:
                        pairs.add(a)
    return list(pairs)


def _neighbors(n: int, cell: Tuple[int, int]) -> List[Tuple[int, int]]:
    """Return up/down/left/right neighbors inside the grid."""
    i, j = cell
    out = []
    for di, dj in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        ii = i + di
        jj = j + dj
        if 0 <= ii < n and 0 <= jj < n:
            out.append((ii, jj))
    return out


def _random_arrow_paths(n: int, count: int) -> List[Dict[str, object]]:
    """
    Generate arrow constraints with contiguous Manhattan paths:
    Each arrow has:
      - 'circle': a single cell
      - 'path': a contiguous sequence of 2..4 distinct cells (neighbors chain)
    Prefer length >= 3; if not feasible fall back to 2..4.
    """
    arrows = []
    all_cells = [(i, j) for i in range(n) for j in range(n)]
    for _ in range(count):
        circle = random.choice(all_cells)
        # Build path by random walk starting from a neighbor of the circle
        start_neighbors = _neighbors(n, circle)
        if not start_neighbors:
            continue
        # Prefer length >=3
        preferred_lengths = [3, 4, 2]
        path = []
        chosen_len = None
        for L in preferred_lengths:
            path_candidate = []
            if not start_neighbors:
                break
            current = random.choice(start_neighbors)
            path_candidate.append(current)
            attempt_guard = 0
            while len(path_candidate) < L and attempt_guard < 40:
                attempt_guard += 1
                nbrs = _neighbors(n, current)
                nbrs = [p for p in nbrs if p != circle and p not in path_candidate]
                if not nbrs:
                    break
                current = random.choice(nbrs)
                path_candidate.append(current)
            if len(path_candidate) == L:
                path = path_candidate
                chosen_len = L
                break
        if chosen_len is None:
            continue
        arrows.append({"circle": circle, "path": path})
    return arrows


def _random_thermometers(n: int, count: int) -> List[List[Tuple[int, int]]]:
    """
    Generate thermometer paths as contiguous Manhattan chains.
    Prefer length >= 3; fall back to 2..5 if needed.
    """
    thermos: List[List[Tuple[int, int]]] = []
    all_cells = [(i, j) for i in range(n) for j in range(n)]
    for _ in range(count):
        # Prefer longer thermos
        preferred_lengths = [3, 4, 5, 2]
        path = None
        for L in preferred_lengths:
            start = random.choice(all_cells)
            path_candidate = [start]
            attempt_guard = 0
            while len(path_candidate) < L and attempt_guard < 60:
                attempt_guard += 1
                nbrs = _neighbors(n, path_candidate[-1])
                nbrs = [p for p in nbrs if p not in path_candidate]
                if not nbrs:
                    break
                nxt = random.choice(nbrs)
                path_candidate.append(nxt)
            if len(path_candidate) == L:
                path = path_candidate
                break
        if path and len(path) >= 2:
            thermos.append(path)
    return thermos


def _active_rule_type_count(bundle: Dict[str, object]) -> int:
    """Count how many different rule categories are active (>0 or True)."""
    cnt = 0
    if bundle.get("parity"): cnt += 1
    if bundle.get("ineq"): cnt += 1
    if bundle.get("cages"): cnt += 1
    if bundle.get("kropki"): cnt += 1
    if bundle.get("thermos"): cnt += 1
    if bundle.get("arrows"): cnt += 1
    if bundle.get("anti_knight_global", False): cnt += 1
    if bundle.get("diagX", False): cnt += 1
    return cnt


def _complexity_score(bundle: Dict[str, object]) -> int:
    """A simple score to ensure rule density/depth."""
    score = 0
    score += len(bundle.get("parity", []))
    score += len(bundle.get("ineq", []))
    score += len(bundle.get("kropki", []))
    score += len(bundle.get("thermos", []))
    score += len(bundle.get("arrows", []))
    score += len(bundle.get("cages", []))
    # Weight for global constraints:
    if bundle.get("diagX", False): score += 2
    if bundle.get("anti_knight_global", False): score += 2
    return score


def make_random_rule_bundle_ext(sol_grid: List[List[int]],
                                n: int,
                                parity_min: int, parity_max: int,
                                ineq_min: int, ineq_max: int,
                                cage_min: int, cage_max: int,
                                kropki_min: int, kropki_max: int,
                                thermo_min: int, thermo_max: int,
                                arrow_min: int, arrow_max: int,
                                diagX_toggle: str,
                                anti_knight_toggle: str) -> Dict[str, object]:
    """
    Build a randomized set of constraints based on the solved grid.
    Returns a dict with keys:
      "parity", "ineq", "cages", "kropki", "thermos", "arrows", "diagX", "anti_knight_global"
    Enforce at least two different rule categories are active and a minimum complexity score.
    """
    for _ in range(100):
        p_count = random.randint(parity_min, max(parity_min, parity_max))
        i_count = random.randint(ineq_min, max(ineq_min, ineq_max))
        g_count = random.randint(cage_min, max(cage_min, cage_max))
        k_count = random.randint(kropki_min, max(kropki_min, kropki_max))
        t_count = random.randint(thermo_min, max(thermo_min, thermo_max))
        a_count = random.randint(arrow_min, max(arrow_min, arrow_max))
        diag_on = (diagX_toggle == 'on')
        ak_global = (anti_knight_toggle == 'on')

        if all(c == 0 for c in [p_count, i_count, g_count, k_count, t_count, a_count]) and not (diag_on or ak_global):
            i_count = max(i_count, 2)
            p_count = max(p_count, 1)

        all_cells = [(i, j) for i in range(n) for j in range(n)]

        # Parity
        parity: List[Tuple[str, str, str]] = []
        if p_count > 0:
            random.shuffle(all_cells)
            for (i, j) in all_cells[:p_count]:
                v = sol_grid[i][j]
                tag = "even" if (v % 2 == 0) else "odd"
                parity.append((str(i), str(j), tag))

        # Inequality (adjacent)
        apairs = _adjacent_pairs(n)
        random.shuffle(apairs)
        ineq: List[Tuple[str, str, str, str, str]] = []
        if i_count > 0:
            for (i1, j1, i2, j2) in apairs[:i_count]:
                v1 = sol_grid[i1][j1]
                v2 = sol_grid[i2][j2]
                op = "lt" if v1 < v2 else "gt"
                ineq.append((str(i1), str(j1), str(i2), str(j2), op))

        # Cages
        cages: List[Dict[str, object]] = []
        if g_count > 0:
            for _ in range(g_count):
                size = random.randint(2, 4)
                cells = random.sample(all_cells, size)
                total = sum(sol_grid[i][j] for (i, j) in cells)
                cages.append({
                    "cells": [(str(i), str(j)) for (i, j) in cells],
                    "total": int(total)
                })

        # Kropki (adjacent)
        random.shuffle(apairs)
        kropki: List[Tuple[str, str, str, str, str]] = []
        if k_count > 0:
            for (i1, j1, i2, j2) in apairs[:k_count]:
                v1 = sol_grid[i1][j1]
                v2 = sol_grid[i2][j2]
                if abs(v1 - v2) == 1:
                    kropki.append((str(i1), str(j1), str(i2), str(j2), "white"))
                elif v1 == 2 * v2 or v2 == 2 * v1:
                    kropki.append((str(i1), str(j1), str(i2), str(j2), "black"))
                else:
                    continue

        # Thermometers (contiguous, prefer length >=3)
        thermos: List[List[Tuple[str, str]]] = []
        if t_count > 0:
            thermos_cells = _random_thermometers(n, t_count)
            thermos = [[(str(i), str(j)) for (i, j) in path] for path in thermos_cells]

        # Arrows (contiguous path, prefer length >=3)
        arrows: List[Dict[str, object]] = []
        if a_count > 0:
            arrows_spec = _random_arrow_paths(n, a_count)
            for spec in arrows_spec:
                circle = (str(spec["circle"][0]), str(spec["circle"][1]))
                path = [(str(i), str(j)) for (i, j) in spec["path"]]
                arrows.append({"circle": circle, "path": path})

        bundle = {
            "parity": parity,
            "ineq": ineq,
            "cages": cages,
            "kropki": kropki,
            "thermos": thermos,
            "arrows": arrows,
            "anti_knight_global": bool(ak_global),
            "diagX": bool(diag_on)
        }

        if _active_rule_type_count(bundle) >= 2 and _complexity_score(bundle) >= 6:
            return bundle

    # Fallback: ensure at least reasonable depth (parity≥4, ineq≥3)
    all_cells = [(i, j) for i in range(n) for j in range(n)]
    random.shuffle(all_cells)
    parity = []
    for (i, j) in all_cells[:4]:
        v = sol_grid[i][j]
        tag = "even" if (v % 2 == 0) else "odd"
        parity.append((str(i), str(j), tag))

    apairs = _adjacent_pairs(n)
    random.shuffle(apairs)
    ineq = []
    for (i1, j1, i2, j2) in apairs[:3]:
        v1 = sol_grid[i1][j1]; v2 = sol_grid[i2][j2]
        op = "lt" if v1 < v2 else "gt"
        ineq.append((str(i1), str(j1), str(i2), str(j2), op))

    return {
        "parity": parity,
        "ineq": ineq,
        "cages": [],
        "kropki": [],
        "thermos": [],
        "arrows": [],
        "anti_knight_global": False,
        "diagX": False
    }


def _check_full_uniqueness_with_rules(sol_grid: List[List[int]],
                                      keep: List[Tuple[int, int]],
                                      n: int,
                                      bundle: Dict[str, object],
                                      timeout_ms: int) -> bool:
    """Check uniqueness with full set of rules using Z3 within timeout."""
    try:
        from z3 import Solver, Int, And, Or, Distinct, Sum, sat
    except Exception:
        return False

    x = [[Int(f"x_{i}_{j}") for j in range(n)] for i in range(n)]
    s = Solver()
    s.set("timeout", timeout_ms)

    # Domains
    for i in range(n):
        for j in range(n):
            s.add(And(x[i][j] >= 1, x[i][j] <= 9))

    # Row/Col Distinct
    for i in range(n):
        s.add(Distinct(x[i]))
    for j in range(n):
        s.add(Distinct([x[i][j] for i in range(n)]))

    # Blocks Distinct
    for br in range(0, n, 3):
        for bc in range(0, n, 3):
            s.add(Distinct([x[br+di][bc+dj] for di in range(3) for dj in range(3)]))

    # Givens
    keep_set = set(keep)
    for (i, j) in keep_set:
        s.add(x[i][j] == sol_grid[i][j])

    # Parity
    for (r_str, c_str, tag) in bundle.get("parity", []):
        i = int(r_str); j = int(c_str)
        if tag == "even":
            s.add(x[i][j] % 2 == 0)
        else:
            s.add(x[i][j] % 2 == 1)

    # Inequality
    for (r1, c1, r2, c2, op) in bundle.get("ineq", []):
        i1 = int(r1); j1 = int(c1); i2 = int(r2); j2 = int(c2)
        if op == "lt":
            s.add(x[i1][j1] < x[i2][j2])
        else:
            s.add(x[i1][j1] > x[i2][j2])

    # Killer cages (sum AND distinct inside cage)
    for cg in bundle.get("cages", []):
        cells = [(int(r), int(c)) for (r, c) in cg["cells"]]
        total = int(cg["total"])
        s.add(Sum([x[i][j] for (i, j) in cells]) == total)
        s.add(Distinct([x[i][j] for (i, j) in cells]))

    # Kropki dots
    for (r1, c1, r2, c2, typ) in bundle.get("kropki", []):
        i1 = int(r1); j1 = int(c1); i2 = int(r2); j2 = int(c2)
        if typ == "white":
            s.add(Or(x[i1][j1] - x[i2][j2] == 1, x[i2][j2] - x[i1][j1] == 1))
        else:
            s.add(Or(x[i1][j1] == 2 * x[i2][j2], x[i2][j2] == 2 * x[i1][j1]))

    # Thermometers: strictly increasing (contiguous paths, order as listed)
    for path in bundle.get("thermos", []):
        cells = [(int(r), int(c)) for (r, c) in path]
        for k in range(len(cells) - 1):
            i1, j1 = cells[k]
            i2, j2 = cells[k + 1]
            s.add(x[i1][j1] < x[i2][j2])

    # Arrows: sum equals circle (contiguous path)
    for ar in bundle.get("arrows", []):
        circle = (int(ar["circle"][0]), int(ar["circle"][1]))
        path = [(int(r), int(c)) for (r, c) in ar["path"]]
        s.add(x[circle[0]][circle[1]] == Sum([x[i][j] for (i, j) in path]))

    # Global Anti-knight
    if bundle.get("anti_knight_global", False):
        for (i1, j1, i2, j2) in _knight_pairs(n):
            s.add(x[i1][j1] != x[i2][j2])

    # Diagonal X
    if bundle.get("diagX", False):
        s.add(Distinct([x[i][i] for i in range(n)]))
        s.add(Distinct([x[i][n - 1 - i] for i in range(n)]))

    if s.check() != sat:
        return False

    # Exclude the solved grid to search for a second solution
    diff_clause = []
    for i in range(n):
        for j in range(n):
            diff_clause.append(x[i][j] != sol_grid[i][j])

    s.push()
    s.add(Or(diff_clause))
    res = s.check()
    s.pop()
    return res != sat


def ensure_unique_rule_bundle(sol_grid: List[List[int]],
                              n: int,
                              mask_positions: List[Tuple[int, int]],
                              parity_min: int, parity_max: int,
                              ineq_min: int, ineq_max: int,
                              cage_min: int, cage_max: int,
                              kropki_min: int, kropki_max: int,
                              thermo_min: int, thermo_max: int,
                              arrow_min: int, arrow_max: int,
                              diagX_toggle: str,
                              anti_knight_toggle: str,
                              timeout_ms: int) -> Dict[str, object]:
    """
    Iteratively sample rule bundles and verify uniqueness under all rules within timeout_ms.
    Prefer non-unique under standard; require decent complexity and multiple categories.
    """
    start = time.time()
    keep = sorted(list(set(mask_positions)))
    attempts = 0
    prefer_interplay = True
    std_unique = has_unique_solution_std(sol_grid, keep, n)

    min_complexity = 6

    while True:
        attempts += 1
        bundle = make_random_rule_bundle_ext(
            sol_grid, n,
            parity_min, parity_max,
            ineq_min, ineq_max,
            cage_min, cage_max,
            kropki_min, kropki_max,
            thermo_min, thermo_max,
            arrow_min, arrow_max,
            diagX_toggle,
            anti_knight_toggle
        )

        if _complexity_score(bundle) < min_complexity or _active_rule_type_count(bundle) < 2:
            continue

        ok = _check_full_uniqueness_with_rules(sol_grid, keep, n, bundle, timeout_ms)
        if ok:
            # Prefer cases where standard Sudoku is NOT unique (multi-rule interplay)
            if not std_unique and (time.time() - start) < 170:
                return bundle
            elif not prefer_interplay:
                return bundle
            else:
                # If standard is unique, still ensure depth threshold before accepting
                if _complexity_score(bundle) >= min_complexity:
                    if attempts > 10:
                        return bundle

        # Gradually reduce complexity caps and retry; also relax interplay preference near timeout
        parity_max = max(parity_min, parity_max - 1)
        ineq_max = max(ineq_min, ineq_max - 1)
        cage_max = max(cage_min, cage_max - 1)
        kropki_max = max(kropki_min, kropki_max - 1)
        thermo_max = max(thermo_min, thermo_max - 1)
        arrow_max = max(arrow_min, arrow_max - 1)
        if attempts % 4 == 0:
            diagX_toggle = 'off'
        if attempts % 5 == 0:
            anti_knight_toggle = 'off'

        if (time.time() - start) > 150:
            prefer_interplay = False

        # Strong fallback near timeout
        if (time.time() - start) > 170:
            # Step 1: small parity + inequality
            apairs = _adjacent_pairs(n)
            random.shuffle(apairs)
            ineq = []
            for (i1, j1, i2, j2) in apairs[:3]:
                v1 = sol_grid[i1][j1]; v2 = sol_grid[i2][j2]
                op = "lt" if v1 < v2 else "gt"
                ineq.append((str(i1), str(j1), str(i2), str(j2), op))

            all_cells = [(i, j) for i in range(n) for j in range(n)]
            random.shuffle(all_cells)
            parity = []
            for (i, j) in all_cells[:4]:
                v = sol_grid[i][j]
                tag = "even" if (v % 2 == 0) else "odd"
                parity.append((str(i), str(j), tag))

            bundle_fb = {
                "parity": parity,
                "ineq": ineq,
                "cages": [],
                "kropki": [],
                "thermos": [],
                "arrows": [],
                "anti_knight_global": False,
                "diagX": False
            }
            if _check_full_uniqueness_with_rules(sol_grid, keep, n, bundle_fb, timeout_ms):
                return bundle_fb

            # Step 2: enable diagX
            bundle_fb["diagX"] = True
            if _check_full_uniqueness_with_rules(sol_grid, keep, n, bundle_fb, timeout_ms):
                return bundle_fb

            # Step 3: enable global anti-knight
            bundle_fb["anti_knight_global"] = True
            if _check_full_uniqueness_with_rules(sol_grid, keep, n, bundle_fb, timeout_ms):
                return bundle_fb

            # Step 4: slightly increase parity hints
            while len(parity) < 8 and all_cells:
                (i, j) = all_cells.pop()
                v = sol_grid[i][j]
                tag = "even" if (v % 2 == 0) else "odd"
                parity.append((str(i), str(j), tag))
            bundle_fb["parity"] = parity
            if _check_full_uniqueness_with_rules(sol_grid, keep, n, bundle_fb, timeout_ms):
                return bundle_fb

            return bundle_fb


# ------------------------ Human-readable rules text ------------------------

def format_rules_text(bundle: Dict[str, object]) -> str:
    """
    Convert the rule bundle into human-readable Chinese lines.
    Every line starts with '- ' and ends with '。', separated by '\n'.
    Coordinates are 1-based (rXcY).
    """
    lines: List[str] = []

    # Unified legend line (clarified semantics)
    lines.append(
        "- 额外规则说明：不等与黑/白点仅作用于上下或左右相邻格，未标注的相邻对不受影响；"
        "温度计按下列顺序（第一个格为球端）沿相邻路径严格递增；"
        "箭头：圆圈格等于其后所列路径格之和（路径相邻连通）；"
        "和杀：每个笼内数字互不相同，且其和等于给定值。"
    )

    # Parity
    for (r_str, c_str, tag) in bundle.get("parity", []):
        i = int(r_str) + 1
        j = int(c_str) + 1
        zh = "偶数" if tag == "even" else "奇数"
        lines.append(f"- 额外规则·奇偶：r{i}c{j} 为{zh}。")

    # Inequality (adjacent)
    for (r1, c1, r2, c2, op) in bundle.get("ineq", []):
        i1 = int(r1) + 1; j1 = int(c1) + 1
        i2 = int(r2) + 1; j2 = int(c2) + 1
        sym = "＜" if op == "lt" else "＞"
        lines.append(f"- 额外规则·不等：r{i1}c{j1} {sym} r{i2}c{j2}。")

    # Killer cages (now explicitly distinct)
    for cg in bundle.get("cages", []):
        cells = [(int(r) + 1, int(c) + 1) for (r, c) in cg["cells"]]
        total = int(cg["total"])
        cell_str = ",".join([f"r{ri}c{ci}" for (ri, ci) in cells])
        lines.append(f"- 额外规则·和杀：单元格[{cell_str}]之和 = {total}（笼内数字各不相同）。")

    # Kropki dots (adjacent)
    for (r1, c1, r2, c2, typ) in bundle.get("kropki", []):
        i1 = int(r1) + 1; j1 = int(c1) + 1
        i2 = int(r2) + 1; j2 = int(c2) + 1
        if typ == "white":
            lines.append(f"- 额外规则·白点：r{i1}c{j1} 与 r{i2}c{j2} 相差 1。")
        else:
            lines.append(f"- 额外规则·黑点：r{i1}c{j1} 与 r{i2}c{j2} 存在 2 倍关系。")

    # Thermometers (contiguous path)
    for path in bundle.get("thermos", []):
        seq = [f"r{int(r)+1}c{int(c)+1}" for (r, c) in path]
        lines.append(f"- 额外规则·温度计：{' → '.join(seq)} 严格递增。")

    # Arrows (contiguous path)
    for ar in bundle.get("arrows", []):
        circle = (int(ar["circle"][0]) + 1, int(ar["circle"][1]) + 1)
        seq = [f"r{int(r)+1}c{int(c)+1}" for (r, c) in ar["path"]]
        lines.append(f"- 额外规则·箭头：r{circle[0]}c{circle[1]} = 路径[{' → '.join(seq)}]之和。")

    # Global Anti-knight
    if bundle.get("anti_knight_global", False):
        lines.append("- 额外规则·反马步（全局）：任何相隔一个棋马步的两格数字不得相同。")

    # Diagonal X
    if bundle.get("diagX", False):
        lines.append("- 额外规则·对角线：两条主对角线数字 1-9 各不相同。")

    return "\n".join(lines) if lines else "- 无额外规则。"