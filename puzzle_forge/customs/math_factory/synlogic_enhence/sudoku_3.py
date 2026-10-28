# sudoku_7.py
# Helper functions for dynamic Jigsaw/Classic Sudoku generation, clue selection, encoding, formatting, and consistency checks.

from typing import List, Tuple, Optional
import random
from z3 import And, Or, Not, Sum, If, BoolVal

def random_choice(seq):
    """Return a random element from a non-empty sequence."""
    return random.choice(seq)

def random_perm(n: int) -> List[int]:
    """Return a random permutation of digits 1..n as a list mapping: new_digit = perm[old_digit-1]."""
    lst = list(range(1, n + 1))
    random.shuffle(lst)
    return lst

def has_items(lst) -> bool:
    """Return True if the list is non-empty."""
    return bool(lst)

def make_regions(n: int, k: int, t: int) -> List[List[int]]:
    """
    Legacy affine region scheme:
      region_id(r, c) = (k*(c - r) + t) mod n
    For odd n and any unit k modulo n, each region has exactly n cells (one per row and column).
    """
    reg = [[0] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            reg[r][c] = (k * (c - r) + t) % n
    return reg

def make_regions_dynamic(n: int, scheme: str, k: Optional[int] = None, t: Optional[int] = None) -> List[List[int]]:
    """
    Generate region id grid by scheme:
      - 'affine': region_id = (k*(c - r) + t) mod n
      - 'blocks3': classic 3x3 boxes: id = (r//3)*3 + (c//3) for n=9
    """
    if scheme == 'affine':
        if k is None:
            k = 1
        if t is None:
            t = 0
        return make_regions(n, k, t)
    elif scheme == 'blocks3':
        box = 3
        reg = [[0] * n for _ in range(n)]
        for r in range(n):
            for c in range(n):
                reg[r][c] = (r // box) * box + (c // box)
        return reg
    else:
        return make_regions(n, 1, 0)

def build_solution(n: int, offset: int, perm: List[int]) -> List[List[int]]:
    """Legacy cyclic Latin solution; kept for compatibility."""
    grid = [[0] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            base = (r + c + offset) % n + 1
            grid[r][c] = perm[base - 1]
    return grid

def build_solution2(n: int, scheme: str, offset: int, perm: List[int]) -> List[List[int]]:
    """
    Build a valid solution tailored to region scheme:
      - blocks3: classic Sudoku base pattern for n=9
      - otherwise: cyclic Latin base
    Then apply digit permutation 'perm'.
    """
    grid = [[0] * n for _ in range(n)]
    if scheme == 'blocks3':
        for r in range(n):
            for c in range(n):
                base = ((r * 3 + r // 3 + c + offset) % n) + 1
                grid[r][c] = perm[base - 1]
    else:
        for r in range(n):
            for c in range(n):
                base = (r + c + offset) % n + 1
                grid[r][c] = perm[base - 1]
    return grid

def _pairs_for_symmetry(n: int, symmetry: str):
    """Yield unique cell-pairs (or self-pairs) according to symmetry."""
    seen = set()
    def mate(rc):
        r, c = rc
        if symmetry == 'rot180':
            return (n - 1 - r, n - 1 - c)
        elif symmetry == 'mirror_h':
            return (n - 1 - r, c)
        elif symmetry == 'mirror_v':
            return (r, n - 1 - c)
        else:
            return rc

    for r in range(n):
        for c in range(n):
            a = (r, c)
            b = mate(a)
            key = tuple(sorted([a, b]))
            if key in seen:
                continue
            seen.add(key)
            yield a, b

def pick_givens(sol_grid: List[List[int]], clue_num: int, symmetry: str) -> List[List[int]]:
    """
    Pick 'givens' from the solved grid. Return list of [r, c, val].
    symmetry in {'none','rot180','mirror_h','mirror_v'}.
    """
    n = len(sol_grid)
    if symmetry == 'none':
        cells = [(r, c) for r in range(n) for c in range(n)]
        random.shuffle(cells)
        givens = []
        used = set()
        for r, c in cells:
            if len(givens) >= clue_num:
                break
            if (r, c) in used:
                continue
            used.add((r, c))
            givens.append([r, c, sol_grid[r][c]])
        return givens

    pairs = list(_pairs_for_symmetry(n, symmetry))
    random.shuffle(pairs)
    givens = []
    used = set()
    needed = clue_num

    if needed % 2 == 1:
        axis_candidates = []
        if symmetry == 'rot180':
            axis_candidates = [(n // 2, n // 2)]
        elif symmetry == 'mirror_h':
            axis_candidates = [(n // 2, c) for c in range(n)]
        elif symmetry == 'mirror_v':
            axis_candidates = [(r, n // 2) for r in range(n)]
        random.shuffle(axis_candidates)
        for r, c in axis_candidates:
            if (r, c) not in used:
                givens.append([r, c, sol_grid[r][c]])
                used.add((r, c))
                needed -= 1
                break

    for (r1, c1), (r2, c2) in pairs:
        if needed <= 0:
            break
        if (r1, c1) in used or (r2, c2) in used:
            continue
        givens.append([r1, c1, sol_grid[r1][c1]])
        used.add((r1, c1))
        if (r1, c1) != (r2, c2):
            givens.append([r2, c2, sol_grid[r2][c2]])
            used.add((r2, c2))
            needed -= 2
        else:
            needed -= 1

    return givens[:clue_num]

def pick_target_cell(givens: List[List[int]], n: int) -> List[int]:
    """Pick a non-given cell [r, c] uniformly at random for a targeted query."""
    given_set = {(r, c) for r, c, _ in givens}
    candidates = [(r, c) for r in range(n) for c in range(n) if (r, c) not in given_set]
    return list(random_choice(candidates))

def build_puzzle(n: int, sol_grid: List[List[int]], givens: List[List[int]]) -> List[List[int]]:
    """Build a puzzle grid with givens placed and zeros elsewhere."""
    puzzle = [[0] * n for _ in range(n)]
    for r, c, v in givens:
        puzzle[r][c] = v
    return puzzle

def format_grid(grid: List[List[int]]) -> str:
    """Format an n x n grid of integers as a multi-line string; rows space-separated."""
    return "\n".join(" ".join(str(v) for v in row) for row in grid)

# ---------- Encoders: exactly-one constraints (sum/pairwise) ----------

def _exactly_one_sum(bools):
    return Sum([If(b, 1, 0) for b in bools]) == 1

def _exactly_one_pairwise(bools):
    if not bools:
        return BoolVal(False)
    if len(bools) == 1:
        return bools[0]
    at_least_one = Or(bools)
    at_most_one = And([Or(Not(bools[i]), Not(bools[j]))
                       for i in range(len(bools)) for j in range(i + 1, len(bools))])
    return And(at_least_one, at_most_one)

def _exactly_one(bools, style: str):
    if style == 'pairwise':
        return _exactly_one_pairwise(bools)
    return _exactly_one_sum(bools)

def enc_cell_uniqueness(x, row_keys, col_keys, digit_keys, style: str):
    """Each cell has exactly one digit."""
    clauses = []
    for rk in row_keys:
        for ck in col_keys:
            literals = [x[(rk, ck, dk)] for dk in digit_keys]
            clauses.append(_exactly_one(literals, style))
    return And(clauses) if clauses else BoolVal(True)

def enc_row_constraints(x, row_keys, col_keys, digit_keys, style: str):
    """Each row has each digit exactly once."""
    clauses = []
    for rk in row_keys:
        for dk in digit_keys:
            literals = [x[(rk, ck, dk)] for ck in col_keys]
            clauses.append(_exactly_one(literals, style))
    return And(clauses) if clauses else BoolVal(True)

def enc_col_constraints(x, row_keys, col_keys, digit_keys, style: str):
    """Each column has each digit exactly once."""
    clauses = []
    for ck in col_keys:
        for dk in digit_keys:
            literals = [x[(rk, ck, dk)] for rk in row_keys]
            clauses.append(_exactly_one(literals, style))
    return And(clauses) if clauses else BoolVal(True)

def enc_region_constraints(x, row_keys, col_keys, digit_keys, regions: List[List[int]], region_ids: List[int], style: str):
    """Each region has each digit exactly once."""
    clauses = []
    n = len(regions)
    key_by_index = {}
    for ri, rk in enumerate(row_keys):
        for ci, ck in enumerate(col_keys):
            key_by_index[(ri, ci)] = (rk, ck)
    for reg_id in region_ids:
        cells = [(ri, ci) for ri in range(n) for ci in range(n) if regions[ri][ci] == reg_id]
        for dk in digit_keys:
            literals = [x[(key_by_index[(ri, ci)][0], key_by_index[(ri, ci)][1], dk)] for (ri, ci) in cells]
            clauses.append(_exactly_one(literals, style))
    return And(clauses) if clauses else BoolVal(True)

def global_digit_count(x, row_keys, col_keys, digit_keys, n: int):
    """Optional redundancy: each digit appears exactly n times overall."""
    clauses = []
    for dk in digit_keys:
        literals = [x[(rk, ck, dk)] for rk in row_keys for ck in col_keys]
        clauses.append(Sum([If(b, 1, 0) for b in literals]) == n)
    return And(clauses) if clauses else BoolVal(True)

def maybe_enforce(flag: bool, expr):
    """If flag is False, relax to True; else return expr."""
    return expr if flag else BoolVal(True)

# ---------- Advanced features: pairs, diagonals, thermometers, killer, parity ----------

def gen_knight_pairs(n: int) -> List[Tuple[Tuple[int,int], Tuple[int,int]]]:
    """All unique knight-move pairs."""
    deltas = [(1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)]
    seen = set()
    pairs = []
    for r in range(n):
        for c in range(n):
            for dr, dc in deltas:
                r2, c2 = r+dr, c+dc
                if 0 <= r2 < n and 0 <= c2 < n:
                    a = (r, c); b = (r2, c2)
                    key = tuple(sorted([a, b]))
                    if key in seen: 
                        continue
                    seen.add(key)
                    pairs.append((a, b))
    return pairs

def gen_king_pairs(n: int) -> List[Tuple[Tuple[int,int], Tuple[int,int]]]:
    """All unique diagonal-adjacent pairs ('king' moves)."""
    deltas = [(-1,-1),(-1,1),(1,-1),(1,1)]
    seen = set()
    pairs = []
    for r in range(n):
        for c in range(n):
            for dr, dc in deltas:
                r2, c2 = r+dr, c+dc
                if 0 <= r2 < n and 0 <= c2 < n:
                    a = (r, c); b = (r2, c2)
                    key = tuple(sorted([a, b]))
                    if key in seen:
                        continue
                    seen.add(key)
                    pairs.append((a, b))
    return pairs

def gen_adjacent_pairs(n: int) -> List[Tuple[Tuple[int,int], Tuple[int,int]]]:
    """All unique orthogonally adjacent cell pairs."""
    seen = set()
    pairs = []
    for r in range(n):
        for c in range(n):
            for dr, dc in [(0,1),(1,0),(0,-1),(-1,0)]:
                r2, c2 = r+dr, c+dc
                if 0 <= r2 < n and 0 <= c2 < n:
                    a = (r, c); b = (r2, c2)
                    key = tuple(sorted([a, b]))
                    if key in seen:
                        continue
                    seen.add(key)
                    pairs.append((a, b))
    return pairs

def enc_anti_knight(x, row_keys, col_keys, digit_keys, pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]]):
    """Forbid equal digits on knight pairs (global)."""
    kb = _key_by_index(row_keys, col_keys)
    clauses = []
    for (r1,c1),(r2,c2) in pairs:
        a = kb[(r1,c1)]
        b = kb[(r2,c2)]
        for dk in digit_keys:
            clauses.append(Or(Not(x[(a[0], a[1], dk)]), Not(x[(b[0], b[1], dk)])))
    return And(clauses) if clauses else BoolVal(True)

def enc_anti_king(x, row_keys, col_keys, digit_keys, pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]]):
    """Forbid equal digits on diagonal-adjacent pairs (global)."""
    kb = _key_by_index(row_keys, col_keys)
    clauses = []
    for (r1,c1),(r2,c2) in pairs:
        a = kb[(r1,c1)]
        b = kb[(r2,c2)]
        for dk in digit_keys:
            clauses.append(Or(Not(x[(a[0], a[1], dk)]), Not(x[(b[0], b[1], dk)])))
    return And(clauses) if clauses else BoolVal(True)

def enc_non_consecutive(x, row_keys, col_keys, digit_keys, pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]]):
    """Forbid consecutive values on adjacent orth pairs (global)."""
    kb = _key_by_index(row_keys, col_keys)
    clauses = []
    n = len(digit_keys)
    dict_int_to_key = {int(dk[1:]): dk for dk in digit_keys}
    for (r1,c1),(r2,c2) in pairs:
        a = kb[(r1,c1)]
        b = kb[(r2,c2)]
        for k in range(1, n):  # k and k+1
            d_k = dict_int_to_key[k]
            d_k1 = dict_int_to_key[k+1]
            clauses.append(Or(Not(x[(a[0], a[1], d_k)]), Not(x[(b[0], b[1], d_k1)])))
            clauses.append(Or(Not(x[(a[0], a[1], d_k1)]), Not(x[(b[0], b[1], d_k)])))
    return And(clauses) if clauses else BoolVal(True)

def enc_diagonals(x, row_keys, col_keys, digit_keys, diag_type: str):
    """Sudoku-X: each digit appears exactly once on specified diagonal(s). diag_type in {'none','main','anti','both'}."""
    n = len(row_keys)
    kb = _key_by_index(row_keys, col_keys)
    clauses = []
    def diag_cells(kind):
        if kind == 'main':
            return [(i, i) for i in range(n)]
        elif kind == 'anti':
            return [(i, n-1-i) for i in range(n)]
        return []
    kinds = []
    if diag_type == 'main':
        kinds = ['main']
    elif diag_type == 'anti':
        kinds = ['anti']
    elif diag_type == 'both':
        kinds = ['main','anti']
    for kind in kinds:
        cells = diag_cells(kind)
        for dk in digit_keys:
            literals = [x[(kb[(ri, ci)][0], kb[(ri, ci)][1], dk)] for (ri, ci) in cells]
            clauses.append(_exactly_one(literals, 'sum'))
    return And(clauses) if clauses else BoolVal(True)

def create_thermometers_from_solution(sol_grid: List[List[int]], thermo_num: int, min_len: int, max_len: int) -> List[List[Tuple[int,int]]]:
    """Create thermometers that strictly increase along path according to solution."""
    n = len(sol_grid)
    thermos = []
    attempts = 0
    max_attempts = 1000
    dirs = [(1,0),(-1,0),(0,1),(0,-1)]
    while len(thermos) < thermo_num and attempts < max_attempts:
        attempts += 1
        r = random.randrange(n)
        c = random.randrange(n)
        path = [(r,c)]
        while len(path) < max_len:
            rr, cc = path[-1]
            random.shuffle(dirs)
            moved = False
            for dr, dc in dirs:
                r2, c2 = rr+dr, cc+dc
                if 0 <= r2 < n and 0 <= c2 < n and (r2,c2) not in path:
                    if sol_grid[r2][c2] > sol_grid[rr][cc]:
                        path.append((r2,c2))
                        moved = True
                        break
            if not moved:
                break
        if len(path) >= min_len:
            thermos.append(path)
    return thermos

def enc_thermo_constraints(x, row_keys, col_keys, digit_keys, thermometers: List[List[Tuple[int,int]]]):
    """Strictly increasing along thermometer: for each consecutive pair u->v, val(v) > val(u)."""
    kb = _key_by_index(row_keys, col_keys)
    clauses = []
    n = len(digit_keys)
    dict_int_to_key = {int(dk[1:]): dk for dk in digit_keys}
    for path in thermometers:
        for i in range(len(path)-1):
            (r1,c1) = path[i]
            (r2,c2) = path[i+1]
            a = kb[(r1,c1)]
            b = kb[(r2,c2)]
            for k in range(1, n+1):
                allowed = [dict_int_to_key[m] for m in range(k+1, n+1)]
                if allowed:
                    clauses.append(Or(Not(x[(a[0], a[1], dict_int_to_key[k])]), Or([x[(b[0], b[1], dk)] for dk in allowed])))
                else:
                    clauses.append(Not(x[(a[0], a[1], dict_int_to_key[k])]))
    return And(clauses) if clauses else BoolVal(True)

def make_killer_cages_cells(sol_grid: List[List[int]], cage_num: int, min_size: int, max_size: int) -> List[List[Tuple[int,int]]]:
    """Create disjoint cages (list of cell coords)."""
    n = len(sol_grid)
    all_cells = [(r,c) for r in range(n) for c in range(n)]
    random.shuffle(all_cells)
    used = set()
    cages = []
    for _ in range(cage_num):
        size = random.randint(min_size, max_size)
        cage = []
        tries = 0
        while len(cage) < size and tries < 2000:
            tries += 1
            rc = random_choice(all_cells)
            if rc in used:
                continue
            cage.append(rc)
            used.add(rc)
        if len(cage) >= min_size:
            cages.append(cage)
    return cages

def make_killer_cages_sums(sol_grid: List[List[int]], cages: List[List[Tuple[int,int]]]) -> List[int]:
    """Compute sums for each cage from solution grid."""
    sums = []
    for cage in cages:
        s = 0
        for (r,c) in cage:
            s += sol_grid[r][c]
        sums.append(s)
    return sums

def enc_killer_cages(x, row_keys, col_keys, digit_keys, cages: List[List[Tuple[int,int]]], sums: List[int]):
    """Sum of digits in each cage equals target."""
    kb = _key_by_index(row_keys, col_keys)
    dict_int_to_key = {int(dk[1:]): dk for dk in digit_keys}
    clauses = []
    for idx, cage in enumerate(cages):
        target = sums[idx]
        cell_terms = []
        for (r,c) in cage:
            rk, ck = kb[(r,c)]
            cell_terms.extend([If(x[(rk, ck, dict_int_to_key[k])], k, 0) for k in dict_int_to_key.keys()])
        clauses.append(Sum(cell_terms) == target)
    return And(clauses) if clauses else BoolVal(True)

def choose_parity_even(sol_grid: List[List[int]], max_count: int) -> List[Tuple[int,int]]:
    """Pick cells that are even in the solution."""
    n = len(sol_grid)
    cells = [(r,c) for r in range(n) for c in range(n) if sol_grid[r][c] % 2 == 0]
    random.shuffle(cells)
    return cells[:max_count]

def choose_parity_odd(sol_grid: List[List[int]], max_count: int) -> List[Tuple[int,int]]:
    """Pick cells that are odd in the solution."""
    n = len(sol_grid)
    cells = [(r,c) for r in range(n) for c in range(n) if sol_grid[r][c] % 2 == 1]
    random.shuffle(cells)
    return cells[:max_count]

def enc_parity(x, row_keys, col_keys, digit_keys, even_cells: List[Tuple[int,int]], odd_cells: List[Tuple[int,int]]):
    """Restrict some cells to even digits and some to odd digits."""
    kb = _key_by_index(row_keys, col_keys)
    even_digits = [dk for dk in digit_keys if int(dk[1:]) % 2 == 0]
    odd_digits = [dk for dk in digit_keys if int(dk[1:]) % 2 == 1]
    clauses = []
    for (r,c) in even_cells:
        rk, ck = kb[(r,c)]
        clauses.append(Or([x[(rk, ck, dk)] for dk in even_digits]) if even_digits else BoolVal(True))
    for (r,c) in odd_cells:
        rk, ck = kb[(r,c)]
        clauses.append(Or([x[(rk, ck, dk)] for dk in odd_digits]) if odd_digits else BoolVal(True))
    return And(clauses) if clauses else BoolVal(True)

def _format_coords_list(coords: List[Tuple[int,int]]) -> str:
    """Format list of coordinates as [(r,c), ...] string."""
    return "[" + ", ".join("(" + str(r) + "," + str(c) + ")" for (r,c) in coords) + "]"

def _format_paths_list(paths: List[List[Tuple[int,int]]]) -> str:
    """Format list of paths: [[(r,c),...]; [(r,c),...]]"""
    parts = []
    for path in paths:
        parts.append(_format_coords_list(path))
    return "[" + "; ".join(parts) + "]"

def _format_cages_with_sums(cages: List[List[Tuple[int,int]]], sums: List[int]) -> str:
    """Format cages with sums: Cage 1: [(r,c),...] sum=S; Cage 2: ..."""
    items = []
    for i, cage in enumerate(cages):
        items.append("Cage " + str(i+1) + ": " + _format_coords_list(cage) + " sum=" + str(sums[i]))
    return "; ".join(items)

def make_constraints_desc(n: int,
                          region_scheme: str,
                          enable_anti_knight: bool, knight_pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]],
                          enable_anti_king: bool, king_pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]],
                          enable_non_consecutive: bool, adj_pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]],
                          diag_type: str,
                          enable_thermo: bool, thermometers: List[List[Tuple[int,int]]],
                          enable_killer: bool, cages: List[List[Tuple[int,int]]], sums: List[int],
                          enable_parity: bool, even_cells: List[Tuple[int,int]], odd_cells: List[Tuple[int,int]]) -> str:
    """
    Build a human-readable constraints description for the puzzle text.
    Includes enabled features and their concrete details so the puzzle is solvable by players.
    Coordinates use 0-based indexing.
    """
    anti_knight_pairs_count = len(knight_pairs)
    anti_king_pairs_count = len(king_pairs)
    noncon_pairs_count = len(adj_pairs)

    parts = []
    parts.append("Regions: region layout is indicated by the ID map above. Coordinates use 0-based indexing (rows 0..8, cols 0..8).")
    if enable_anti_knight:
        parts.append("Anti-knight: identical digits are forbidden at chess knight distance (applied to all such pairs; total pairs=" + str(anti_knight_pairs_count) + ").")
    if enable_anti_king:
        parts.append("Anti-king: identical digits are forbidden on diagonal adjacency (applied to all such pairs; total pairs=" + str(anti_king_pairs_count) + ").")
    if enable_non_consecutive:
        parts.append("Non-consecutive adjacency: for all orthogonally adjacent cell pairs, the two digits cannot be consecutive (total pairs=" + str(noncon_pairs_count) + ").")
    if diag_type != 'none':
        parts.append("Sudoku-X: on the " + ("main and anti-diagonals" if diag_type == "both" else diag_type + " diagonal") + ", digits 1..9 each appear exactly once.")
    if enable_thermo and len(thermometers) > 0:
        parts.append("Thermometers: paths=" + _format_paths_list(thermometers) + " (digits strictly increase along each path).")
    if enable_killer and len(cages) > 0:
        parts.append("Killer cages: " + _format_cages_with_sums(cages, sums) + ".")
    if enable_parity and (len(even_cells) > 0 or len(odd_cells) > 0):
        parts.append("Parity hints: Even cells=" + _format_coords_list(even_cells) + "; Odd cells=" + _format_coords_list(odd_cells) + ".")
    return " ".join(parts)

def _key_by_index(row_keys, col_keys):
    """Build reverse maps from indices to (row_key, col_key)."""
    key_by_index = {}
    for ri, rk in enumerate(row_keys):
        for ci, ck in enumerate(col_keys):
            key_by_index[(ri, ci)] = (rk, ck)
    return key_by_index

def enc_givens_lock(x, row_keys, col_keys, digit_keys, givens: List[List[int]]):
    """Lock given values: for each (r,c,v) assert x[(row_keys[r], col_keys[c], 'd'+str(v))]."""
    dict_int_to_key = {int(dk[1:]): dk for dk in digit_keys}
    clauses = []
    for r, c, v in givens:
        rk = row_keys[r]
        ck = col_keys[c]
        dk = dict_int_to_key[v]
        clauses.append(x[(rk, ck, dk)])
    return And(clauses) if clauses else BoolVal(True)

def check_diagonals_valid(sol_grid: List[List[int]]) -> bool:
    """
    Check whether both main and anti diagonals of the solution grid contain digits 1..n each exactly once.
    This ensures enabling diagonal rules will remain consistent with the constructed solution/givens.
    """
    n = len(sol_grid)
    req = set(range(1, n+1))
    main = [sol_grid[i][i] for i in range(n)]
    anti = [sol_grid[i][n-1-i] for i in range(n)]
    return set(main) == req and set(anti) == req

def check_main_diagonal_valid(sol_grid: List[List[int]]) -> bool:
    """Check whether the main diagonal contains digits 1..n each exactly once."""
    n = len(sol_grid)
    req = set(range(1, n+1))
    main = [sol_grid[i][i] for i in range(n)]
    return set(main) == req

def check_anti_diagonal_valid(sol_grid: List[List[int]]) -> bool:
    """Check whether the anti diagonal contains digits 1..n each exactly once."""
    n = len(sol_grid)
    req = set(range(1, n+1))
    anti = [sol_grid[i][n-1-i] for i in range(n)]
    return set(anti) == req

def pick_diag_type(sol_grid: List[List[int]]) -> str:
    """
    Pick a diagonal type among {'none','main','anti','both'} consistent with the solution.
    """
    options = ['none']
    main_ok = check_main_diagonal_valid(sol_grid)
    anti_ok = check_anti_diagonal_valid(sol_grid)
    if main_ok:
        options.append('main')
    if anti_ok:
        options.append('anti')
    if main_ok and anti_ok:
        options.append('both')
    return random_choice(options)

def solution_satisfies_anti_knight(sol_grid: List[List[int]], pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]]) -> bool:
    """Return True if sol_grid has no equal digits on any knight pair."""
    for (r1,c1),(r2,c2) in pairs:
        if sol_grid[r1][c1] == sol_grid[r2][c2]:
            return False
    return True

def solution_satisfies_anti_king(sol_grid: List[List[int]], pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]]) -> bool:
    """Return True if sol_grid has no equal digits on any diagonal-adjacent pair."""
    for (r1,c1),(r2,c2) in pairs:
        if sol_grid[r1][c1] == sol_grid[r2][c2]:
            return False
    return True

def solution_satisfies_non_consecutive(sol_grid: List[List[int]], pairs: List[Tuple[Tuple[int,int], Tuple[int,int]]]) -> bool:
    """Return True if sol_grid has no orthogonally adjacent consecutive digits."""
    for (r1,c1),(r2,c2) in pairs:
        if abs(sol_grid[r1][c1] - sol_grid[r2][c2]) == 1:
            return False
    return True