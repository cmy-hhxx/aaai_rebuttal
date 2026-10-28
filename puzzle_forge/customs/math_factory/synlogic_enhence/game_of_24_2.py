# ------------------------------------------------------------------
# File: game_of_24_0.py
#   Complex helpers for multi-rule 24-point puzzle generation
# ------------------------------------------------------------------
import random, itertools, time
from typing import List, Sequence, Dict, Tuple

# ---------------------  Expression evaluation ------------------- #
def compute_value(nums: Sequence[float], ops: Sequence[str]) -> float:
    """Left-to-right evaluation of the expression."""
    if len(nums) != len(ops) + 1:
        raise ValueError("Mismatch between numbers and operators.")
    def apply(a, op, b):
        if op == '+': return a + b
        if op == '-': return a - b
        if op == '*': return a * b
        if op == '/':
            if b == 0:
                raise ZeroDivisionError
            return a / b
        raise ValueError(f'Unknown operator {op}')
    res = nums[0]
    for op, nxt in zip(ops, nums[1:]):
        res = apply(res, op, nxt)
    return res

def compute_steps(nums: Sequence[float], ops: Sequence[str]) -> List[float]:
    """Return list of intermediate results for a given expression."""
    steps = []
    res = nums[0]
    for op, nxt in zip(ops, nums[1:]):
        res = compute_value([res, nxt], [op])
        steps.append(res)
    return steps

# ---------------------  Rule definitions ------------------------ #
_RULES_DESC = {
    0: '必须至少使用一次加法',
    1: '必须至少使用一次减法',
    2: '必须至少使用一次乘法',
    3: '必须至少使用一次除法',
    4: '第一个运算符必须是乘号',
    5: '最后一个运算符必须是加号',
    6: '不能出现除以 1 的情况',
    7: '第一次运算结果必须能被第二个数字整除',
    8: '第二次运算结果必须是偶数',
    9: '三次运算得到的中间结果必须严格递增'
}

def gen_rules(num_rules: int) -> List[int]:
    pool = list(_RULES_DESC.keys())
    return random.sample(pool, num_rules)

def get_rule_desc(rule_ids: Sequence[int]) -> List[str]:
    return [_RULES_DESC[rid] for rid in rule_ids]

def check_rules(nums: Sequence[int], ops: Sequence[str], rule_ids: Sequence[int]) -> bool:
    """Check if (nums, ops) satisfy all rules."""
    try:
        # Pre-compute intermediates
        steps = compute_steps(nums, ops)
    except ZeroDivisionError:
        return False
    for rid in rule_ids:
        if rid == 0 and '+' not in ops:
            return False
        if rid == 1 and '-' not in ops:
            return False
        if rid == 2 and '*' not in ops:
            return False
        if rid == 3 and '/' not in ops:
            return False
        if rid == 4 and ops[0] != '*':
            return False
        if rid == 5 and ops[-1] != '+':
            return False
        if rid == 6 and any(op == '/' and nums[i + 1] == 1 for i, op in enumerate(ops)):
            return False
        if rid == 7 and (steps[0] % nums[1] != 0):
            return False
        if rid == 8 and (len(steps) < 2 or steps[1] % 2 != 0):
            return False
        if rid == 9 and any(a >= b for a, b in zip(steps, steps[1:])):
            return False
    return True

# ------------------  Unique-solution verifier ------------------- #
def unique_solution(
    original_nums: Sequence[int],
    ops_pool: Sequence[str],
    target: float,
    rule_ids: Sequence[int],
    time_limit: float = 170.0
) -> bool:
    """
    Verify uniqueness among all permutations and operator combinations.
    Cease search on discovery of a second solution.
    """
    start = time.time()
    num_count = len(original_nums)
    solutions_found = 0
    nums_set = list(set(itertools.permutations(original_nums)))

    for nums in nums_set:
        for ops in itertools.product(ops_pool, repeat=num_count - 1):
            if time.time() - start > time_limit:
                raise RuntimeError("Unique-solution verification timed out.")
            try:
                if abs(compute_value(nums, ops) - target) < 1e-6 and check_rules(nums, ops, rule_ids):
                    solutions_found += 1
                    if solutions_found > 1:
                        return False
            except ZeroDivisionError:
                continue
    return solutions_found == 1

# ------------------------  Normalizer --------------------------- #
def _normalize_order(
    nums: List[int],
    ops: List[str],
    target: float,
    rule_ids: Sequence[int]
) -> Tuple[List[int], List[str]]:
    improved = True
    while improved:
        improved = False
        for i in range(len(nums) - 1):
            if nums[i] > nums[i + 1]:
                cand_nums = nums.copy()
                cand_nums[i], cand_nums[i + 1] = cand_nums[i + 1], cand_nums[i]
                try:
                    if abs(compute_value(cand_nums, ops) - target) < 1e-6 \
                       and check_rules(cand_nums, ops, rule_ids):
                        nums = cand_nums
                        improved = True
                except ZeroDivisionError:
                    pass
    return nums, ops

# ---------------------  Instance generator ---------------------- #
def gen_instance(
    num_pool_min: int,
    num_pool_max: int,
    num_count: int,
    ops_pool: Sequence[str],
    target: int,
    rule_ids: Sequence[int],
    max_retry: int = 120_000
) -> Dict[str, List]:
    attempts = 0
    while attempts < max_retry:
        attempts += 1
        nums = [random.randint(num_pool_min, num_pool_max) for _ in range(num_count)]
        ops  = [random.choice(ops_pool) for _ in range(num_count - 1)]

        # quick rule & target pre-check
        try:
            if abs(compute_value(nums, ops) - target) > 1e-6:
                continue
        except ZeroDivisionError:
            continue
        if not check_rules(nums, ops, rule_ids):
            continue
        # uniqueness check
        try:
            if unique_solution(nums, ops_pool, target, rule_ids):
                nums, ops = _normalize_order(nums, ops, target, rule_ids)
                steps = compute_steps(nums, ops)
                return {'nums': list(nums), 'ops': list(ops)}
        except RuntimeError:
            # timeout: abandon current candidate
            continue
    raise RuntimeError("Exceeded retry limit; could not build a valid unique puzzle.")