# object_counting_1.py
import random
from fractions import Fraction
from typing import List

def abs_diff(a: int, b: int) -> int:
    """
    Return the absolute difference between two integers.
    """
    return abs(a - b)

def rand_list(n: int, low: int, high: int) -> List[int]:
    """
    Generate a list of n random integers in [low, high].
    """
    return [random.randint(low, high) for _ in range(n)]

def rand_int(low: int, high: int) -> int:
    """
    Generate a random integer in [low, high] inclusive.
    """
    if low > high:
        low, high = high, low
    return random.randint(low, high)

def _determinant_int_matrix(mat: List[List[int]]) -> int:
    """
    Compute the determinant of a square integer matrix exactly using Fraction-based Gaussian elimination.
    """
    n = len(mat)
    A = [[Fraction(x) for x in row] for row in mat]
    det = Fraction(1)
    sign = 1
    for i in range(n):
        pivot = i
        while pivot < n and A[pivot][i] == 0:
            pivot += 1
        if pivot == n:
            return 0
        if pivot != i:
            A[i], A[pivot] = A[pivot], A[i]
            sign *= -1
        pivot_val = A[i][i]
        det *= pivot_val
        for r in range(i + 1, n):
            if A[r][i] != 0:
                factor = A[r][i] / pivot_val
                for c in range(i, n):
                    A[r][c] -= factor * A[i][c]
    det = det * sign
    return int(det) if det.denominator == 1 else 0

def gen_invertible_matrix(n: int, low: int, high: int) -> List[List[int]]:
    """
    Generate a random n x n integer matrix with entries in [low, high] that is invertible (determinant != 0).
    Fallback to identity if repeated attempts fail.
    """
    attempts = 0
    if high < low:
        low, high = high, low
    while attempts < 200:
        M = [[random.randint(low, high) for _ in range(n)] for _ in range(n)]
        if any(all(v == 0 for v in row) for row in M):
            attempts += 1
            continue
        det = _determinant_int_matrix(M)
        if det != 0:
            return M
        attempts += 1
    I = [[0] * n for _ in range(n)]
    for i in range(n):
        I[i][i] = 1
    return I

def gen_random_matrix(rows: int, cols: int, low: int, high: int) -> List[List[int]]:
    """
    Generate a random rows x cols integer matrix with entries in [low, high].
    Ensures no row is all zero to avoid trivial mixed constraints.
    """
    if rows <= 0 or cols <= 0:
        return [[0 for _ in range(cols)] for _ in range(max(1, rows))]
    if high < low:
        low, high = high, low
    M = []
    for _ in range(rows):
        r = [random.randint(low, high) for _ in range(cols)]
        attempts = 0
        while all(v == 0 for v in r) and attempts < 50:
            r = [random.randint(low, high) for _ in range(cols)]
            attempts += 1
        if all(v == 0 for v in r):
            idx = random.randint(0, cols - 1)
            r[idx] = 1
        M.append(r)
    return M

def matmul(A: List[List[int]], x: List[int]) -> List[int]:
    """
    Compute b = A * x for integer matrix A and integer vector x.
    """
    return [sum(aij * xj for aij, xj in zip(row, x)) for row in A]

def sum_int_list(lst: List[int]) -> int:
    """
    Sum a list of integers, provided to avoid using Python built-in sum in YAML formulas directly.
    """
    return sum(lst)

def concat_two_lists(a: List[int], b: List[int]) -> List[int]:
    """
    Concatenate two lists.
    """
    return a + b

def argmax_index(lst: List[int]) -> int:
    """
    Return the index of the first maximum element in the list.
    """
    if not lst:
        return 0
    max_val = lst[0]
    idx = 0
    for i in range(1, len(lst)):
        if lst[i] > max_val:
            max_val = lst[i]
            idx = i
    return idx

def select_random_indices(n: int, k: int) -> List[int]:
    """
    Select k unique indices from range(n) uniformly at random.
    """
    if n <= 0:
        return []
    k = max(1, min(k, n))
    return random.sample(list(range(n)), k)

# ---------- Readability helpers for equation rendering ----------

def _format_linear_combination(coefs: List[int], names: List[str]) -> str:
    """
    Build a human-readable linear combination string like:
    3×衣物1 - 2×衣物2 + 4×衣物3
    Skips zero coefficients and handles signs properly.
    """
    terms = []
    for c, name in zip(coefs, names):
        if c == 0:
            continue
        sign = '+' if c > 0 else '-'
        abs_c = abs(c)
        if not terms:
            # first term: no leading '+'; if negative, start with '- '
            if c < 0:
                terms.append(f'- {abs_c}×{name}')
            else:
                terms.append(f'{abs_c}×{name}')
        else:
            if c < 0:
                terms.append(f'- {abs_c}×{name}')
            else:
                terms.append(f'+ {abs_c}×{name}')
    return ' '.join(terms) if terms else '0'

def format_equations(A: List[List[int]], names: List[str], b: List[int]) -> str:
    """
    Format square system A * x = b into numbered lines without zero terms and with proper signs.
    """
    lines = []
    for i, row in enumerate(A):
        left = _format_linear_combination(row, names)
        lines.append(f'第{i + 1}条 {left} = {b[i]}')
    return '\n'.join(lines)

def format_mixed_equations(M: List[List[int]], clothes_names: List[str], cars_names: List[str], b: List[int]) -> str:
    """
    Format mixed system M * [clothes, cars]^T = b into numbered lines, skipping zero terms and handling signs.
    """
    lines = []
    split = len(clothes_names)
    for r, row in enumerate(M):
        left_clothes = _format_linear_combination(row[:split], clothes_names)
        left_cars = _format_linear_combination(row[split:split + len(cars_names)], cars_names)
        if left_clothes == '0' and left_cars == '0':
            left = '0'
        elif left_clothes == '0':
            left = left_cars
        elif left_cars == '0':
            left = left_clothes
        else:
            # merge with a middle ' + ' if second starts with positive, or ' ' if it already has a leading '-'
            if left_cars.startswith('-'):
                left = f'{left_clothes} {left_cars}'
            else:
                left = f'{left_clothes} + {left_cars}'
        lines.append(f'第{r + 1}条 {left} = {b[r]}')
    return '\n'.join(lines)