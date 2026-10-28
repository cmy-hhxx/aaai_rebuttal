# operation_0.py
import random
from math import gcd
from itertools import combinations
from typing import List, Tuple

# ========== 基础随机 ==========
def rand_choice(lst: List):
    return random.choice(lst)

def rand_int(a: int, b: int) -> int:
    return random.randint(a, b)

def rand_nonzero_int(a: int, b: int) -> int:
    while True:
        v = random.randint(a, b)
        if v != 0:
            return v

# ========== 自定义运算 ==========
def op_calc(mode: str, power: int, x: int, y: int) -> int:
    if mode == 'xpow_yabs':
        return (x ** power) * abs(y)
    if mode == 'xpabs_ypow':
        return abs(x) * (y ** power)
    raise ValueError(f'Unsupported mode: {mode}')

# ========== 附加条件相关 ==========
def _candidate_conditions(a: int, b: int) -> List[Tuple[str, str]]:
    """返回 (代码, 描述) 列表，至少含 non_equal。"""
    cand = [('non_equal', 'a ≠ b')] if a != b else []
    if (a + b) % 2 == 0:
        cand.append(('sum_even', 'a+b 为偶数'))
    if a > b:
        cand.append(('a_gt_b', 'a > b'))
    if (a > 0 and b > 0) or (a < 0 and b < 0):
        cand.append(('same_sign', 'a 与 b 同号'))
    d = abs(gcd(a, b))
    if d not in (0, 1):
        cand.append((f'gcd_{d}', f'gcd(a,b) = {d}'))
    if (a - b) != 0 and (a + b) % (a - b) == 0:
        cand.append(('diff_div_sum', 'a−b 能整除 a+b'))
    return cand

def _satisfy_extra(codes: List[str], A: int, B: int) -> bool:
    for c in codes:
        if c == 'non_equal' and A == B:
            return False
        if c == 'sum_even' and (A + B) % 2 != 0:
            return False
        if c == 'a_gt_b' and not (A > B):
            return False
        if c == 'same_sign' and not ((A > 0 and B > 0) or (A < 0 and B < 0)):
            return False
        if c.startswith('gcd_') and abs(gcd(A, B)) != int(c.split('_')[1]):
            return False
        if c == 'diff_div_sum' and ((A - B) == 0 or (A + B) % (A - B) != 0):
            return False
    return True

def _unique_given(mode: str, power: int, r1: int, r2: int, r3: int,
                  codes: List[str], bound: int) -> bool:
    cnt = 0
    for A in range(-bound, bound + 1):
        if A == 0:
            continue
        for B in range(-bound, bound + 1):
            if B == 0:
                continue
            if op_calc(mode, power, A, B) == r1 and \
               op_calc(mode, power, B, A) == r2 and \
               op_calc(mode, power, A + B, A - B) == r3 and \
               _satisfy_extra(codes, A, B):
                cnt += 1
                if cnt > 1:
                    return False
    return cnt == 1

def choose_extra_conds(a: int, b: int,
                       mode: str, power: int,
                       r1: int, r2: int, r3: int,
                       bound: int,
                       min_k: int = 2) -> Tuple[List[str], str]:
    """
    选取最小组合(不少于 min_k, 若候选不足则自动降低要求)以保证唯一解。
    """
    pool = _candidate_conditions(a, b)
    codes = [c[0] for c in pool]
    desc_map = {c[0]: c[1] for c in pool}

    # 如果候选数量不足 min_k，允许降低要求到可用数量
    effective_min = min(min_k, len(codes)) if codes else 1

    random.shuffle(codes)
    for k in range(effective_min, len(codes) + 1):
        for combo in combinations(codes, k):
            if _unique_given(mode, power, r1, r2, r3, list(combo), bound):
                desc = '且 '.join(desc_map[c] for c in combo)
                return list(combo), desc

    # 理论兜底（全部条件）
    desc = '且 '.join(desc_map[c] for c in codes) if codes else '无额外条件'
    return codes if codes else ['non_equal'], desc