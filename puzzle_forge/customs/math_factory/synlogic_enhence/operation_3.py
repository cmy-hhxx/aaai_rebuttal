# =============================================
# operation_4.py — final compatibility version
# =============================================
import random
from fractions import Fraction
from typing import Tuple
from z3 import Int, Solver, And, Or, sat

# ---------- 占位兼容函数 ----------
def function_1(*args, **kwargs):
    """Placeholder for backward compatibility."""
    return ''

def function_2(*args, **kwargs):
    """Placeholder for backward compatibility."""
    return ('', '')

# ---------- Helper functions ----------
def _frac_to_str(fr: Fraction) -> str:
    """Convert Fraction to simplified string."""
    return str(fr.numerator) if fr.denominator == 1 else f"{fr.numerator}/{fr.denominator}"

def format_poly(A: int, B: int, C: int) -> str:
    """Return polynomial string in k^2 + Bk + C format."""
    parts = []
    parts.append('k^2' if A == 1 else ('-k^2' if A == -1 else f'{A}k^2'))
    if B:
        sign = '+' if B > 0 else '-'
        coef = '' if abs(B) == 1 else str(abs(B))
        parts.append(f' {sign} {coef}k')
    if C:
        sign = '+' if C > 0 else '-'
        parts.append(f' {sign} {abs(C)}')
    return ''.join(parts)

def compute_min_info(A: int, B: int, C: int) -> Tuple[str, str]:
    """Compute vertex (k_min, f_min) for quadratic."""
    k_min = Fraction(-B, 2 * A)
    f_min = Fraction(4 * A * C - B * B, 4 * A)
    return _frac_to_str(k_min), _frac_to_str(f_min)

# ---------- Coefficient & clue generator with uniqueness check ----------
def gen_coeff_and_clues() -> Tuple[int, int, int, int, int, int, int]:
    """
    Generate (A,B,C) with integer constraints and their clues (S,D,P,F1)
    while ensuring uniqueness using Z3.
    """
    while True:
        A = random.randint(1, 5)
        B = random.randint(-10, 10)
        C = random.randint(-10, 10)
        if B == 0 and C == 0:
            continue
        S = B + C
        D = A - B
        P = B * C
        F1 = A + B + C

        a_z, b_z, c_z = Int('a'), Int('b'), Int('c')
        solver = Solver()
        solver.add(
            And(a_z >= 1, a_z <= 5),
            And(b_z >= -10, b_z <= 10),
            And(c_z >= -10, c_z <= 10),
            b_z + c_z == S,
            a_z - b_z == D,
            b_z * c_z == P,
            a_z + b_z + c_z == F1
        )
        if solver.check() != sat:
            continue
        model = solver.model()
        # check uniqueness
        solver.add(Or(a_z != model[a_z], b_z != model[b_z], c_z != model[c_z]))
        if solver.check() == sat:
            continue  # multiple solutions, resample
        return (A, B, C, S, D, P, F1)