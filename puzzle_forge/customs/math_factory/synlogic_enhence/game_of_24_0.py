# game_of_24_3.py
# 改进要点：
# - 去平凡化计数约束：丢弃 at_least 0、丢弃 at_most >= 3，保留 exact k 与非平凡边界的 at_least/at_most；
# - 仅展示有效运算集合的成本 effective_costs_str；
# - 规则文本自然语言呈现并与内部 tie_break_order 完全一致；
# - 唯一性验证：最优排序键下 (nums, ops, expr) 去重计数=1；生成与验证限时控制，确保≤3分钟。

from typing import List, Tuple, Dict, Optional, Any
from itertools import permutations, product
import random
import time


# ===== 基础运算与括号形状 =====

def _apply_op(x: int, y: int, op: str) -> Optional[int]:
    if op == '+':
        return x + y
    if op == '-':
        return x - y
    if op == '*':
        return x * y
    if op == '/':
        if y == 0:
            return None
        if x % y != 0:
            return None
        return x // y
    return None


_SHAPE_DEPTH_SCORE = {
    1: 3,  # ((a o b) o c) o d
    2: 2,  # (a o (b o c)) o d
    3: 3,  # a o ((b o c) o d)
    4: 3,  # a o (b o (c o d))
    5: 2,  # (a o b) o (c o d)
}


def _shape_eval(a: int, b: int, c: int, d: int, o1: str, o2: str, o3: str,
                shape_id: int, forbid_negative_intermediate: bool) -> Optional[Tuple[int, str]]:
    def chk(v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if forbid_negative_intermediate and v < 0:
            return None
        return v

    if shape_id == 1:
        t1 = chk(_apply_op(a, b, o1))
        if t1 is None: return None
        t2 = chk(_apply_op(t1, c, o2))
        if t2 is None: return None
        t3 = chk(_apply_op(t2, d, o3))
        if t3 is None: return None
        expr = f'(({a}{o1}{b}){o2}{c}){o3}{d}'
        return t3, expr
    if shape_id == 2:
        t1 = chk(_apply_op(b, c, o2))
        if t1 is None: return None
        t2 = chk(_apply_op(a, t1, o1))
        if t2 is None: return None
        t3 = chk(_apply_op(t2, d, o3))
        if t3 is None: return None
        expr = f'({a}{o1}({b}{o2}{c})){o3}{d}'
        return t3, expr
    if shape_id == 3:
        t1 = chk(_apply_op(b, c, o2))
        if t1 is None: return None
        t2 = chk(_apply_op(t1, d, o3))
        if t2 is None: return None
        t3 = chk(_apply_op(a, t2, o1))
        if t3 is None: return None
        expr = f'{a}{o1}(({b}{o2}{c}){o3}{d})'
        return t3, expr
    if shape_id == 4:
        t1 = chk(_apply_op(c, d, o3))
        if t1 is None: return None
        t2 = chk(_apply_op(b, t1, o2))
        if t2 is None: return None
        t3 = chk(_apply_op(a, t2, o1))
        if t3 is None: return None
        expr = f'{a}{o1}({b}{o2}({c}{o3}{d}))'
        return t3, expr
    if shape_id == 5:
        t1 = chk(_apply_op(a, b, o1))
        if t1 is None: return None
        t2 = chk(_apply_op(c, d, o3))
        if t2 is None: return None
        t3 = chk(_apply_op(t1, t2, o2))
        if t3 is None: return None
        expr = f'({a}{o1}{b}){o2}({c}{o3}{d})'
        return t3, expr
    return None


# ===== 随机工具与规则生成 =====

def _rand_ops_subset(ops_universe: List[str]) -> List[str]:
    k = random.randint(1, len(ops_universe))
    return random.sample(ops_universe, k)


def _rand_costs(ops_set: List[str], low: int = 1, high: int = 6) -> Dict[str, int]:
    return {op: random.randint(low, high) for op in ops_set}


def _gen_random_nums(n: int, lo: int, hi: int) -> List[int]:
    lo2, hi2 = min(lo, hi), max(lo, hi)
    return [random.randint(lo2, hi2) for _ in range(n)]


def _rand_shapes_policy() -> Tuple[str, List[int]]:
    policy = random.choice(['all', 'left', 'right', 'balanced'])
    if policy == 'all':
        return policy, [1, 2, 3, 4, 5]
    if policy == 'left':
        return policy, [1]
    if policy == 'right':
        return policy, [4]
    return policy, random.choice([[2], [5], [2, 5]])


def _rand_relation() -> str:
    return random.choice(['eq', 'ge', 'le', 'closest'])


def _is_trivial_count_constraint(ctype: str, k: int) -> bool:
    if ctype == 'at_least' and k <= 0:
        return True
    if ctype == 'at_most' and k >= 3:
        return True
    return False


def _rand_op_count_constraints(eff_ops: List[str]) -> List[Dict[str, Any]]:
    """仅在有效运算集合上生成0~2条非平凡计数约束。"""
    if not eff_ops:
        return []
    k = random.randint(0, 2)
    if k == 0:
        return []
    chosen_ops = random.sample(eff_ops, min(k, len(eff_ops)))
    constraints = []
    for op in chosen_ops:
        ctype = random.choice(['at_least', 'at_most', 'exact'])
        if ctype == 'exact':
            kval = random.randint(0, 3)
        elif ctype == 'at_least':
            kval = random.randint(1, 3)  # 避免0
        else:
            kval = random.randint(0, 2)  # 避免≥3
        if not _is_trivial_count_constraint(ctype, kval):
            constraints.append({'op': op, 'type': ctype, 'k': kval})
    return constraints


# ===== 文本构造 =====

def _tie_break_desc(order: List[str]) -> str:
    mapping = {'parens': '表达式字符串', 'nums': '数字序列', 'ops': '运算序列'}
    return '→'.join(mapping[k] for k in order)


def _build_rules_desc(rules: Dict[str, Any], costs: Dict[str, int], eff_ops: List[str]) -> str:
    parts = []
    parts.append('四个数字各用且仅用一次')
    parts.append('必须使用标准完全括号化表达式(五种形之一)')
    rel = rules['relation']
    if rel == 'eq':
        parts.append('优先级1: 结果必须等于目标值')
    elif rel == 'ge':
        parts.append('优先级1: 结果必须不小于目标值(越接近目标越好)')
    elif rel == 'le':
        parts.append('优先级1: 结果必须不大于目标值(越接近目标越好)')
    else:
        parts.append('优先级1: 结果需最接近目标值(先最小化差值)')
    if '/' in eff_ops:
        parts.append('若出现除法则必须整除且每一步中间值为整数')
    else:
        parts.append('除法不可用')
    if rules['negative_intermediate_allowed']:
        parts.append('中间结果允许为负')
    else:
        parts.append('中间结果不得为负')
    pol = rules['shapes_policy']
    if pol == 'all':
        parts.append('括号形状不限(标准完全括号化的5种形)')
    elif pol == 'left':
        parts.append('仅允许左结合括号形((a o b) o c) o d(五种形之一)')
    elif pol == 'right':
        parts.append('仅允许右结合括号形 a o (b o (c o d))(五种形之一)')
    else:
        parts.append('允许平衡括号形(如(a o (b o c)) o d或(a o b) o (c o d))')
    parts.append(f"优先级2: 超出软预算{rules['budget']}的方案更劣(超额越小越优；预算与成本单位一致)")
    parts.append(f"优先级3: 总运算成本越低越优(按成本表计算)")
    parts.append(f"优先级4: 运算切换惩罚(相邻两个运算符不同记一次切换)权重为{rules['switch_weight']}，惩罚越小越优")
    parts.append(f"优先级5: 括号深度惩罚权重为{rules['depth_weight']}，惩罚越小越优(深度评分越大表示结构越深)")
    if rules.get('op_count_constraints'):
        cs = []
        for c in rules['op_count_constraints']:
            if c['type'] == 'at_least':
                cs.append(f"{c['op']}至少{c['k']}次")
            elif c['type'] == 'at_most':
                cs.append(f"{c['op']}至多{c['k']}次")
            else:
                cs.append(f"{c['op']}恰好{c['k']}次")
        parts.append('运算符次数约束: ' + '；'.join(cs))
    else:
        parts.append('暂无运算符次数约束')
    parts.append('如仍并列，则依次按' + _tie_break_desc(rules['tie_break_order']) + '的字典序比较')
    return '；'.join(parts)


# ===== 关系与排序 =====

def _ops_counts_ok(ops_seq: Tuple[str, str, str], constraints: List[Dict[str, Any]]) -> bool:
    if not constraints:
        return True
    from collections import Counter
    cnt = Counter(ops_seq)
    for c in constraints:
        op, k, tp = c['op'], c['k'], c['type']
        v = cnt.get(op, 0)
        if tp == 'at_least' and v < k:
            return False
        if tp == 'at_most' and v > k:
            return False
        if tp == 'exact' and v != k:
            return False
    return True


def _switches(ops_seq: Tuple[str, str, str]) -> int:
    return int(ops_seq[0] != ops_seq[1]) + int(ops_seq[1] != ops_seq[2])


def _primary_and_feasible(val: int, target: int, relation: str) -> Optional[int]:
    if relation == 'eq':
        return 0 if val == target else None
    if relation == 'ge':
        return (val - target) if val >= target else None
    if relation == 'le':
        return (target - val) if val <= target else None
    return abs(val - target)  # closest


def _enumerate_all_candidates(nums: List[int],
                              ops_set: List[str],
                              costs: Dict[str, int],
                              target: int,
                              rules: Dict[str, Any]) -> List[Tuple]:
    allowed_shapes = rules['allowed_shapes']
    forbid_neg = not rules['negative_intermediate_allowed']
    div_allowed = rules['division_allowed']
    relation = rules['relation']
    tbo = rules['tie_break_order']
    cnt_constraints = rules.get('op_count_constraints', [])
    budget = rules['budget']
    switch_weight = rules['switch_weight']
    depth_weight = rules['depth_weight']

    eff_ops = [op for op in ops_set if (op != '/' or div_allowed)]
    if not eff_ops:
        return []

    seen_perms = set(permutations(nums, 4))
    out = []

    for a, b, c, d in seen_perms:
        for o1, o2, o3 in product(eff_ops, repeat=3):
            ops_seq = (o1, o2, o3)
            if not _ops_counts_ok(ops_seq, cnt_constraints):
                continue
            base_cost = costs[o1] + costs[o2] + costs[o3]
            sw_cnt = _switches(ops_seq)
            sw_pen = switch_weight * sw_cnt
            for shape in allowed_shapes:
                res = _shape_eval(a, b, c, d, o1, o2, o3, shape, forbid_neg)
                if res is None:
                    continue
                val, expr = res
                primary = _primary_and_feasible(val, target, relation)
                if primary is None:
                    continue
                over_budget = max(0, base_cost - budget)
                depth_pen = depth_weight * _SHAPE_DEPTH_SCORE[shape]
                tie_keys = []
                nums_seq = (a, b, c, d)
                for k in tbo:
                    if k == 'nums':
                        tie_keys.append(nums_seq)
                    elif k == 'ops':
                        tie_keys.append(ops_seq)
                    else:
                        tie_keys.append(expr)
                key = (primary, over_budget, base_cost, sw_pen, depth_pen, *tie_keys)
                out.append((key, nums_seq, ops_seq, expr, base_cost, val))

    return out


def _pick_best_and_unique(cands: List[Tuple]) -> Optional[Tuple[Dict, int]]:
    if not cands:
        return None
    cands.sort(key=lambda x: x[0])
    best_key = cands[0][0]
    seen = set()
    for k, nums_seq, ops_seq, expr, cost, val in cands:
        if k != best_key:
            break
        seen.add((nums_seq, ops_seq, expr))
    _, nums_seq, ops_seq, expr, cost, _ = cands[0]
    best_dict = {
        'nums': list(nums_seq),
        'ops': list(ops_seq),
        'parens': expr,
        'total_cost': int(cost),
    }
    return best_dict, len(seen)


# ===== 逆向采样(兜底) =====

def _random_valid_expression_with_rules(nums: List[int],
                                        eff_ops: List[str],
                                        rules: Dict[str, Any],
                                        max_trials: int = 1500) -> Optional[Tuple[List[int], List[str], str, int]]:
    allowed_shapes = rules['allowed_shapes']
    forbid_neg = not rules['negative_intermediate_allowed']
    cnt_constraints = rules.get('op_count_constraints', [])
    if not eff_ops:
        return None
    perms = list(set(permutations(nums, 4)))
    for _ in range(max_trials):
        a, b, c, d = random.choice(perms)
        o1, o2, o3 = random.choice(eff_ops), random.choice(eff_ops), random.choice(eff_ops)
        if not _ops_counts_ok((o1, o2, o3), cnt_constraints):
            continue
        shape = random.choice(allowed_shapes)
        res = _shape_eval(a, b, c, d, o1, o2, o3, shape, forbid_neg)
        if res is None:
            continue
        val, expr = res
        return [a, b, c, d], [o1, o2, o3], expr, val
    return None


# ===== 主生成器与验证器 =====

def function_1(n_num: int,
               num_min: int,
               num_max: int,
               ops_universe: List[str],
               target_low: int,
               target_high: int,
               max_attempts: int,
               budget_low: int,
               budget_high: int,
               switch_weight_low: int,
               switch_weight_high: int,
               depth_weight_low: int,
               depth_weight_high: int,
               time_limit_sec: int) -> Dict:
    t0 = time.time()
    lo_n, hi_n = min(num_min, num_max), max(num_min, num_max)
    t_lo, t_hi = min(target_low, target_high), max(target_low, target_high)
    if n_num != 4:
        n_num = 4

    def random_rules(ops_set: List[str]) -> Dict[str, Any]:
        division_allowed = random.choice([True, False])
        shapes_policy, allowed_shapes = _rand_shapes_policy()
        negative_intermediate_allowed = random.choice([True, False])
        tie_break_order = random.sample(['nums', 'ops', 'parens'], 3)
        relation = _rand_relation()
        budget = random.randint(min(budget_low, budget_high), max(budget_low, budget_high))
        switch_weight = random.randint(min(switch_weight_low, switch_weight_high), max(switch_weight_low, switch_weight_high))
        depth_weight = random.randint(min(depth_weight_low, depth_weight_high), max(depth_weight_low, depth_weight_high))
        eff_ops = [op for op in ops_set if (op != '/' or division_allowed)]
        return {
            'division_allowed': division_allowed,
            'shapes_policy': shapes_policy,
            'allowed_shapes': allowed_shapes,
            'negative_intermediate_allowed': negative_intermediate_allowed,
            'tie_break_order': tie_break_order,
            'relation': relation,
            'budget': budget,
            'switch_weight': switch_weight,
            'depth_weight': depth_weight,
            'eff_ops': eff_ops,
        }

    # 正向阶段
    for _ in range(max_attempts):
        if time.time() - t0 > time_limit_sec:
            break
        ops_set = _rand_ops_subset(ops_universe)
        costs = _rand_costs(ops_set, low=1, high=6)
        nums = _gen_random_nums(n_num, lo_n, hi_n)
        target = random.randint(t_lo, t_hi)
        rules = random_rules(ops_set)
        rules['op_count_constraints'] = _rand_op_count_constraints(rules['eff_ops'])

        cands = _enumerate_all_candidates(nums, ops_set, costs, target, rules)
        if not cands:
            continue
        pick = _pick_best_and_unique(cands)
        if pick is None:
            continue
        best, uniq = pick
        if uniq != 1:
            continue
        ops_list_str = ', '.join(ops_set)
        effective_ops_str = ', '.join(rules['eff_ops'])
        costs_str = ', '.join([f"{op}:{costs[op]}" for op in ops_set])
        effective_costs_str = ', '.join([f"{op}:{costs[op]}" for op in rules['eff_ops']])
        rules_desc = _build_rules_desc(rules, costs, rules['eff_ops'])
        return {
            'nums': nums,
            'ops_set': ops_set,
            'effective_ops_str': effective_ops_str,
            'costs': costs,
            'target': target,
            'best': best,
            'rules': rules,
            'rules_desc': rules_desc,
            'ops_list_str': ops_list_str,
            'costs_str': costs_str,
            'effective_costs_str': effective_costs_str
        }

    # 逆向兜底阶段
    while time.time() - t0 <= time_limit_sec:
        ops_set = _rand_ops_subset(ops_universe)
        costs = _rand_costs(ops_set, low=1, high=6)
        nums = _gen_random_nums(n_num, lo_n, hi_n)
        rules = random_rules(ops_set)
        rules['op_count_constraints'] = _rand_op_count_constraints(rules['eff_ops'])

        sample = _random_valid_expression_with_rules(nums, rules['eff_ops'], rules, max_trials=1500)
        if sample is None:
            continue
        _, _, _, val = sample

        rel = rules['relation']
        if rel == 'eq':
            target = val
        elif rel == 'ge':
            target = val - random.randint(0, 5)
        elif rel == 'le':
            target = val + random.randint(0, 5)
        else:
            target = val + random.randint(-8, 8)
        target = min(max(target, t_lo), t_hi)

        cands = _enumerate_all_candidates(nums, ops_set, costs, target, rules)
        if not cands:
            continue
        pick = _pick_best_and_unique(cands)
        if pick is None:
            continue
        best, uniq = pick
        if uniq != 1:
            continue
        ops_list_str = ', '.join(ops_set)
        effective_ops_str = ', '.join(rules['eff_ops'])
        costs_str = ', '.join([f"{op}:{costs[op]}" for op in ops_set])
        effective_costs_str = ', '.join([f"{op}:{costs[op]}" for op in rules['eff_ops']])
        rules_desc = _build_rules_desc(rules, costs, rules['eff_ops'])
        return {
            'nums': nums,
            'ops_set': ops_set,
            'effective_ops_str': effective_ops_str,
            'costs': costs,
            'target': target,
            'best': best,
            'rules': rules,
            'rules_desc': rules_desc,
            'ops_list_str': ops_list_str,
            'costs_str': costs_str,
            'effective_costs_str': effective_costs_str
        }

    raise TimeoutError("Generation exceeded time limit without finding a unique optimal instance.")


def function_2(instance: Dict, time_limit_sec: int) -> bool:
    t0 = time.time()
    try:
        for k in ['nums', 'ops_set', 'effective_ops_str', 'costs', 'target', 'best', 'rules', 'effective_costs_str']:
            if k not in instance:
                return False
        nums = instance['nums']
        ops_set = instance['ops_set']
        costs = instance['costs']
        target = instance['target']
        best = instance['best']
        rules = instance['rules']
        for k in ['nums', 'ops', 'parens', 'total_cost']:
            if k not in best:
                return False
        if not (isinstance(nums, list) and len(nums) == 4 and all(isinstance(x, int) for x in nums)):
            return False
        if not (isinstance(ops_set, list) and 1 <= len(ops_set) <= 4 and all(op in ['+', '-', '*', '/'] for op in ops_set)):
            return False
        if not (isinstance(costs, dict) and all(op in ops_set for op in costs.keys()) and all(isinstance(v, int) and v >= 1 for v in costs.values())):
            return False
        if not isinstance(target, int):
            return False

        cands = _enumerate_all_candidates(nums, ops_set, costs, target, rules)
        if not cands:
            return False
        pick = _pick_best_and_unique(cands)
        if pick is None:
            return False
        if time.time() - t0 > time_limit_sec:
            return False
        recomputed, uniq = pick
        if uniq != 1:
            return False

        for key in ['nums', 'ops', 'parens', 'total_cost']:
            if recomputed[key] != best[key]:
                return False

        expr = best['parens']
        safe_expr = expr.replace('/', '//')
        allowed_chars = set('0123456789+-*/() ')
        if any(ch not in allowed_chars for ch in safe_expr):
            return False
        val = eval(safe_expr, {"__builtins__": None}, {})
        if not isinstance(val, int):
            return False
        if _primary_and_feasible(val, target, rules['relation']) is None:
            return False

        base_cost = sum(costs[o] for o in best['ops'])
        if base_cost != best['total_cost']:
            return False
        if not rules['division_allowed'] and any(o == '/' for o in best['ops']):
            return False
        if not _ops_counts_ok(tuple(best['ops']), rules.get('op_count_constraints', [])):
            return False

        return True
    except Exception:
        return False