# kukurasu_0.py
import random
from typing import List, Tuple


def generate_kakurasu_grid(n: int, fill_ratio: int) -> List[List[bool]]:
    """
    Generate an n x n boolean grid for Kakurasu.
    fill_ratio: integer percentage in [0, 100], the probability of True per cell.
    Hard constraints to avoid '显见线索':
      - Each row must contain at least one True and at least one False.
      - Each column must contain at least one True and at least one False.
    """
    pr = max(0.0, min(1.0, float(fill_ratio) / 100.0))

    def _gen_once() -> List[List[bool]]:
        return [[random.random() < pr for _ in range(n)] for _ in range(n)]

    def _row_ok(g: List[List[bool]], i: int) -> bool:
        row = g[i]
        return any(row) and not all(row)

    def _col_ok(g: List[List[bool]], j: int) -> bool:
        col = [g[i][j] for i in range(n)]
        return any(col) and not all(col)

    # Try multiple random samples to get a non-trivial grid
    for _ in range(200):
        grid = _gen_once()
        # Avoid trivial whole grid
        if not any(any(row) for row in grid):
            continue
        if all(all(row) for row in grid):
            continue
        if all(_row_ok(grid, i) for i in range(n)) and all(_col_ok(grid, j) for j in range(n)):
            return grid

    # Fallback: repair a random grid until constraints met
    grid = _gen_once()

    # Ensure at least one True and one False in each row
    for i in range(n):
        row = grid[i]
        if not any(row):  # all False -> flip a random cell to True
            j = random.randrange(n)
            grid[i][j] = True
        if all(row):  # all True -> flip a random cell to False
            j = random.randrange(n)
            grid[i][j] = False

    # Ensure at least one True and one False in each column
    for j in range(n):
        col = [grid[i][j] for i in range(n)]
        if not any(col):  # all False -> flip a random cell in this column to True
            i = random.randrange(n)
            grid[i][j] = True
        if all(col):  # all True -> flip a random cell in this column to False
            i = random.randrange(n)
            grid[i][j] = False

    # After repair, double-check; if still trivial (rare), do a final pass
    for i in range(n):
        row = grid[i]
        if not any(row):
            grid[i][random.randrange(n)] = True
        if all(row):
            grid[i][random.randrange(n)] = False
    for j in range(n):
        col = [grid[i][j] for i in range(n)]
        if not any(col):
            grid[random.randrange(n)][j] = True
        if all(col):
            grid[random.randrange(n)][j] = False

    return grid


def calc_kakurasu_sums(grid: List[List[bool]],
                       row_weights: List[int],
                       col_weights: List[int],
                       axis: str) -> List[int]:
    """
    Calculate weighted sums for Kakurasu.
    - axis == 'row': Sum for each row i = sum over j of (col_weights[j] if grid[i][j] else 0)
    - axis == 'col': Sum for each column j = sum over i of (row_weights[i] if grid[i][j] else 0)
    Returns a list of sums of length n.
    """
    n = len(grid)
    if axis == 'row':
        return [
            sum(col_weights[j] if grid[i][j] else 0 for j in range(n))
            for i in range(n)
        ]
    elif axis == 'col':
        return [
            sum(row_weights[i] if grid[i][j] else 0 for i in range(n))
            for j in range(n)
        ]
    else:
        raise ValueError("axis must be 'row' or 'col'")


def generate_weights(mode: str, n: int, start: int = 1, step: int = 1) -> List[int]:
    """
    Generate column/row weights by mode.
    Modes:
      - 'standard': [1, 2, ..., n]
      - 'reverse': [n, n-1, ..., 1]
      - 'ap_increase': arithmetic progression increasing: [start, start+step, ..., start+(n-1)*step]
      - 'ap_decrease': arithmetic progression decreasing
      - 'zigzag': swap adjacent pairs based on AP seed
      - 'permute': a random permutation of [1, 2, ..., n]
    All entries are positive integers.
    """
    if n <= 0:
        return []
    if mode == 'standard':
        return list(range(1, n + 1))
    if mode == 'reverse':
        return list(range(n, 0, -1))
    if mode == 'ap_increase':
        return [start + i * step for i in range(n)]
    if mode == 'ap_decrease':
        return [start + (n - 1 - i) * step for i in range(n)]
    if mode == 'zigzag':
        base = [start + i * step for i in range(n)]
        arr = base[:]
        for i in range(1, n, 2):
            arr[i - 1], arr[i] = arr[i], arr[i - 1]
        return arr
    if mode == 'permute':
        arr = list(range(1, n + 1))
        random.shuffle(arr)
        return arr
    # Fallback
    return list(range(1, n + 1))


def cell_truth(grid: List[List[bool]], r_str: str, c_str: str) -> bool:
    """
    Return the boolean value at grid[int(r_str)][int(c_str)].
    rows_s/cols_s are stored as strings of indices in the YAML; this converts back to ints.
    """
    i = int(r_str)
    j = int(c_str)
    return bool(grid[i][j])


# ----------------------------
# Diagonal helpers
# ----------------------------
def diag_id_pool(n: int, diag_type: str) -> List[str]:
    """
    Return a list of diagonal IDs.
      - diag_type 'main': IDs are 'M_k' for k in [-(n-1), ..., (n-1)], where k = j - i.
      - diag_type 'anti': IDs are 'A_s' for s in [0, ..., 2n-2], where s = i + j.
    """
    if diag_type == 'main':
        return [f"M_{k}" for k in range(-(n - 1), n)]
    elif diag_type == 'anti':
        return [f"A_{s}" for s in range(0, 2 * n - 1)]
    else:
        return []


def diag_coords(diag_type: str, diag_id: str, n: int) -> List[Tuple[int, int]]:
    """
    Given diag_type and diag_id, enumerate coordinates on that diagonal for an n x n grid.
      - main diag 'M_k': j - i = k
      - anti diag 'A_s': i + j = s
    """
    coords: List[Tuple[int, int]] = []
    if diag_type == 'main':
        k = int(diag_id.split('_')[1])
        i_min = max(0, -k)
        i_max = min(n - 1, n - 1 - k)
        for i in range(i_min, i_max + 1):
            j = i + k
            coords.append((i, j))
    elif diag_type == 'anti':
        s = int(diag_id.split('_')[1])
        i_min = max(0, s - (n - 1))
        i_max = min(n - 1, s)
        for i in range(i_min, i_max + 1):
            j = s - i
            coords.append((i, j))
    return coords


def diag_count_truth(grid: List[List[bool]], diag_type: str, diag_id: str) -> int:
    """
    Count how many True cells lie on a given diagonal in the true solution.
    """
    n = len(grid)
    coords = diag_coords(diag_type, diag_id, n)
    return sum(1 for (i, j) in coords if grid[i][j])


def diag_id_pool_filtered(grid: List[List[bool]], n: int, diag_type: str) -> List[str]:
    """
    Return diagonal IDs whose True-count is neither 0 nor full length.
    This avoids trivial 'all 0' or 'all 1' clues.
    """
    ids = diag_id_pool(n, diag_type)
    kept: List[str] = []
    for d in ids:
        coords = diag_coords(diag_type, d, n)
        length = len(coords)
        cnt = sum(1 for (i, j) in coords if grid[i][j])
        if 0 < cnt < length:
            kept.append(d)
    return kept


# ----------------------------
# Rectangle helpers
# ----------------------------
def rect_id_pool(n: int, max_side: int) -> List[str]:
    """
    Generate a pool of rectangle IDs within n x n.
    We include all rectangles with height, width in [1, max_side], and area >= 4 (avoid trivial/small cases).
    ID format: 'R_r0_c0_r1_c1' (inclusive bounds).
    """
    ids: List[str] = []
    max_side = max(1, min(max_side, n))
    for h in range(1, max_side + 1):
        for w in range(1, max_side + 1):
            if h * w < 4:
                continue
            for r0 in range(0, n - h + 1):
                for c0 in range(0, n - w + 1):
                    r1 = r0 + h - 1
                    c1 = c0 + w - 1
                    ids.append(f"R_{r0}_{c0}_{r1}_{c1}")
    return ids


def rect_coords(rect_id: str) -> List[Tuple[int, int]]:
    """
    Parse 'R_r0_c0_r1_c1' and return list of (i, j) coordinates inside the rectangle (inclusive).
    """
    parts = rect_id.split('_')
    if len(parts) != 5 or parts[0] != 'R':
        return []
    r0 = int(parts[1])
    c0 = int(parts[2])
    r1 = int(parts[3])
    c1 = int(parts[4])
    coords: List[Tuple[int, int]] = []
    for i in range(r0, r1 + 1):
        for j in range(c0, c1 + 1):
            coords.append((i, j))
    return coords


def rect_count_truth(grid: List[List[bool]], rect_id: str) -> int:
    """
    Count how many True cells lie in the rectangle.
    """
    coords = rect_coords(rect_id)
    return sum(1 for (i, j) in coords if grid[i][j])


def rect_id_pool_filtered(grid: List[List[bool]], n: int, max_side: int) -> List[str]:
    """
    Return rectangle IDs with non-trivial counts: strictly between 1 and area-1, and area >= 4.
    This filters out 0/full-area cases and too-small rectangles to avoid '显见线索'.
    """
    ids = rect_id_pool(n, max_side)
    kept: List[str] = []
    for rid in ids:
        coords = rect_coords(rid)
        area = len(coords)
        cnt = sum(1 for (i, j) in coords if grid[i][j])
        if area >= 4 and 1 < cnt < area - 1:
            kept.append(rid)
    return kept


# ----------------------------
# Positional sum and XOR/global parity helpers
# ----------------------------
def pos_sum_row(grid: List[List[bool]], i: int) -> int:
    """
    Position-weighted sum for row i: sum over j of (j+1) if grid[i][j] else 0
    """
    n = len(grid)
    return sum((j + 1) if grid[i][j] else 0 for j in range(n))


def pos_sum_col(grid: List[List[bool]], j: int) -> int:
    """
    Position-weighted sum for column j: sum over i of (i+1) if grid[i][j] else 0
    """
    n = len(grid)
    return sum((i + 1) if grid[i][j] else 0 for i in range(n))


def xor_truth(grid: List[List[bool]], i1: int, j1: int, i2: int, j2: int) -> bool:
    """
    XOR truth for two cells in the true solution.
    """
    return bool(grid[i1][j1]) ^ bool(grid[i2][j2])


def global_parity_truth(grid: List[List[bool]]) -> int:
    """
    Return 1 if total number of True cells is odd, else 0.
    """
    total = sum(1 for row in grid for v in row if v)
    return 1 if (total % 2) == 1 else 0


# ----------------------------
# Text helpers to simplify YAML desc (avoid nested quotes/ternaries)
# ----------------------------
def cell_char(grid: List[List[bool]], r_str: str, c_str: str) -> str:
    """
    Return '1' if the cell is True, else 'X'.
    """
    return '1' if cell_truth(grid, r_str, c_str) else 'X'


def xor_text_str(grid: List[List[bool]], i1_str: str, j1_str: str, i2_str: str, j2_str: str) -> str:
    """
    Return a human-readable string for XOR relation of two cells.
    """
    i1 = int(i1_str)
    j1 = int(j1_str)
    i2 = int(i2_str)
    j2 = int(j2_str)
    return '两格中恰有一格为1' if xor_truth(grid, i1, j1, i2, j2) else '两格状态相同'


def parity_text_from_count(count: int) -> str:
    """
    Return '奇数' if count is odd, else '偶数'.
    """
    return '奇数' if (count % 2) == 1 else '偶数'


def global_parity_text(grid: List[List[bool]]) -> str:
    """
    Return '奇数'/'偶数' for total True cells parity.
    """
    return '奇数' if global_parity_truth(grid) == 1 else '偶数'


# ----------------------------
# Non-trivial hint pools (to avoid '显见线索')
# ----------------------------
def row_count_hint_ids(grid: List[List[bool]]) -> List[str]:
    """
    Return row indices (as strings) whose True count is not in {0,1,n-1,n}.
    """
    n = len(grid)
    ids: List[str] = []
    for i in range(n):
        k = sum(1 for v in grid[i] if v)
        if 1 < k < n - 1:
            ids.append(str(i))
    return ids


def col_count_hint_ids(grid: List[List[bool]]) -> List[str]:
    """
    Return column indices (as strings) whose True count is not in {0,1,n-1,n}.
    """
    n = len(grid)
    ids: List[str] = []
    for j in range(n):
        k = sum(1 for i in range(n) if grid[i][j])
        if 1 < k < n - 1:
            ids.append(str(j))
    return ids


def _possum_extremes_for_k(n: int, k: int) -> Tuple[int, int]:
    """
    For a line of length n with exactly k True cells, the min/max possible positional sums
    under weights 1..n (contiguous minimal or maximal positions).
    """
    # min: 1+2+...+k = k*(k+1)//2
    s_min = k * (k + 1) // 2
    # max: (n-k+1)+...+n = k*(2n - k + 1)//2
    s_max = k * (2 * n - k + 1) // 2
    return s_min, s_max


def row_possum_hint_ids(grid: List[List[bool]]) -> List[str]:
    """
    Return row indices (as strings) for which:
      - the True count k is not in {0,1,n-1,n}, and
      - the actual positional sum is NOT at the min or max possible for that k.
    """
    n = len(grid)
    ids: List[str] = []
    for i in range(n):
        k = sum(1 for v in grid[i] if v)
        if 1 < k < n - 1:
            s = pos_sum_row(grid, i)
            s_min, s_max = _possum_extremes_for_k(n, k)
            if s_min < s < s_max:
                ids.append(str(i))
    return ids


def col_possum_hint_ids(grid: List[List[bool]]) -> List[str]:
    """
    Return column indices (as strings) for which:
      - the True count k is not in {0,1,n-1,n}, and
      - the actual positional sum is NOT at the min or max possible for that k.
    """
    n = len(grid)
    ids: List[str] = []
    for j in range(n):
        k = sum(1 for i in range(n) if grid[i][j])
        if 1 < k < n - 1:
            s = pos_sum_col(grid, j)
            s_min, s_max = _possum_extremes_for_k(n, k)
            if s_min < s < s_max:
                ids.append(str(j))
    return ids