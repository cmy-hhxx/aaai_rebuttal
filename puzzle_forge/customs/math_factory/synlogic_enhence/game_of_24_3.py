# ================================================================
#  game_of_24_5.py  –  cleaned & stable (no null bytes)
# ================================================================
import itertools
import json
import operator
import random
from fractions import Fraction
from typing import Dict, List, Tuple

# ---------- operator mapping ----------
FUNC = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': lambda a, b: Fraction(a, b),   # keep exactness
    '%': operator.mod
}
OPS = list(FUNC.keys())

# ---------- safe apply ---------------
def safe_apply(op: str, a, b):
    if op in {'/', '%'} and b == 0:
        return False, None
    if op == '%' and (not isinstance(a, int) or not isinstance(b, int)):
        return False, None
    res = FUNC[op](a, b)
    if op == '/':
        if res.denominator != 1:
            return False, None
        res = int(res)
    return True, res

# ---------- two bracket patterns -----
def eval_pattern(nums: Tuple[int, int, int, int],
                 ops: Tuple[str, str, str],
                 bracket_id: int):
    a, b, c, d = nums
    op1, op2, op3 = ops

    if bracket_id == 0:  # ((a op1 b) op2 (c op3 d))
        ok, v_left = safe_apply(op1, a, b)
        if not ok:
            return None
        ok, v_right = safe_apply(op3, c, d)
        if not ok:
            return None
        ok, final = safe_apply(op2, v_left, v_right)
        if not ok:
            return None
        return v_left, v_right, final

    else:  # a op1 (b op2 (c op3 d))
        ok, t1 = safe_apply(op3, c, d)
        if not ok:
            return None
        ok, v_left = safe_apply(op2, b, t1)
        if not ok:
            return None
        ok, final = safe_apply(op1, a, v_left)
        if not ok:
            return None
        v_right = t1
        return v_left, v_right, final

# ---------- enumeration -------------
def enumerate_expr(nums: Tuple[int, int, int, int],
                   mod_cnt: int, div_limit: int,
                   k1: int, k2: int, r2: int, sum_min: int,
                   bracket_id: int):
    bucket: Dict[int, List[Tuple[Tuple[int, ...], Tuple[str, ...]]]] = {}
    for perm in set(itertools.permutations(nums)):
        for ops in itertools.product(OPS, repeat=3):
            if ops.count('%') != mod_cnt or ops.count('/') > div_limit:
                continue
            res = eval_pattern(perm, ops, bracket_id)
            if res is None:
                continue
            v1, v2, val = res
            if v1 % k1 or v2 % k2 != r2 or v1 + v2 <= sum_min:
                continue
            bucket.setdefault(val, []).append((perm, ops))
    return bucket

# ---------- instance generator -------
def generate_instance(max_trials: int = 10000) -> Dict:
    for _ in range(max_trials):
        nums = random.sample(range(2, 40), 4)
        mod_cnt = random.randint(0, 3)
        div_limit = random.randint(0, 3 - mod_cnt)
        k1 = random.randint(2, 5)
        k2 = random.randint(2, 5)
        r2 = random.randint(0, k2 - 1)
        sum_min = random.randint(10, 60)
        bracket_id = random.randint(0, 1)

        bucket = enumerate_expr(tuple(nums), mod_cnt, div_limit,
                                k1, k2, r2, sum_min, bracket_id)

        viable = [v for v, lst in bucket.items() if 20 <= v <= 300 and len(lst) == 1]
        if not viable:
            continue
        tgt = random.choice(viable)
        perm, ops = bucket[tgt][0]
        return dict(nums=list(nums), target=tgt, mod_cnt=mod_cnt,
                    div_limit=div_limit, k1=k1, k2=k2, r2=r2,
                    sum_min=sum_min, bracket_id=bracket_id,
                    solution_perm=perm, solution_ops=ops)
    raise RuntimeError('generation failed')

# ---------- solver for framework -----
def search_expression(nums: list, target: int,
                      mod_cnt: int, div_limit: int,
                      k1: int, k2: int, r2: int, sum_min: int,
                      bracket_id: int) -> str:
    bucket = enumerate_expr(tuple(nums), mod_cnt, div_limit,
                            k1, k2, r2, sum_min, bracket_id)
    sols = bucket.get(target, [])
    if len(sols) != 1:
        return 'IMPOSSIBLE'
    perm, ops = sols[0]
    return json.dumps({"nums": list(perm), "ops": list(ops)}, ensure_ascii=False)

# quick test
if __name__ == '__main__':
    inst = generate_instance()
    print(inst)
    print(search_expression(inst['nums'], inst['target'], inst['mod_cnt'],
          inst['div_limit'], inst['k1'], inst['k2'], inst['r2'],
          inst['sum_min'], inst['bracket_id']))