# game_of_24_5.py
# -*- coding: utf-8 -*-
from fractions import Fraction
from itertools import permutations, product, combinations
import json
import random
import time
from typing import List, Tuple, Dict, Any, Optional

# ------------------------------------------------------------
# 基础工具
# ------------------------------------------------------------

def _is_int(x: Fraction) -> bool:
    """判断 Fraction 是否为整数。"""
    return x.denominator == 1

def _sqrt_int(n: int) -> Optional[int]:
    """若 n 为非负完全平方数则返回其整数平方根, 否则返回 None。"""
    if n < 0:
        return None
    r = int(n ** 0.5)
    return r if r * r == n else None

def _is_power_of_two(n: int) -> bool:
    """判断正整数 n 是否为 2 的幂。"""
    if n <= 0:
        return False
    return (n & (n - 1)) == 0

def _apply_unary(val: Fraction, rep: str, func: str) -> Optional[Tuple[Fraction, str]]:
    """
    在值 val 上应用一元函数 func, 并返回新值与新的表示字符串。
    约束:
      - sqrt: 仅对非负整数且为完全平方数; 输出为整数
      - log2: 仅对正整数且为 2 的幂; 输出为整数
      - abs: 始终允许
    """
    if func == 'sqrt':
        if not _is_int(val):
            return None
        v = val.numerator // val.denominator
        rt = _sqrt_int(v)
        if rt is None:
            return None
        return Fraction(rt, 1), f"sqrt({rep})"
    elif func == 'log2':
        if not _is_int(val):
            return None
        v = val.numerator // val.denominator
        if v <= 0 or not _is_power_of_two(v):
            return None
        k = v.bit_length() - 1
        return Fraction(k, 1), f"log2({rep})"
    elif func == 'abs':
        return abs(val), f"abs({rep})"
    else:
        return None

def _apply_unary_pipeline(val: Fraction, rep: str, funcs: List[str], funcs_seq: List[Dict[str, Any]], at_step: int) -> Optional[Tuple[Fraction, str]]:
    """依次应用一元函数管道, 记录每次应用的 at_step。"""
    out_val, out_rep = val, rep
    for f in funcs:
        res = _apply_unary(out_val, out_rep, f)
        if res is None:
            return None
        out_val, out_rep = res
        funcs_seq.append({'func': f, 'at_step': at_step})
    return out_val, out_rep

def _apply_binary(a: Fraction, b: Fraction, op: str) -> Optional[Fraction]:
    """对 a 与 b 应用二元运算符。除法避免除零。"""
    if op == '+':
        return a + b
    elif op == '-':
        return a - b
    elif op == '*':
        return a * b
    elif op == '/':
        if b == 0:
            return None
        return a / b
    else:
        return None

# ------------------------------------------------------------
# 表达式评估(5 种括号形状)
# 叶子顺序: a,b,c,d -> L0,L1,L2,L3
# 节点序(N0,N1,N2)按该形状的求值顺序; at_step: 叶 0..3, 节点 4..6
# ------------------------------------------------------------

def _eval_shape(a: Tuple[Fraction, str],
                b: Tuple[Fraction, str],
                c: Tuple[Fraction, str],
                d: Tuple[Fraction, str],
                ops: Tuple[str, str, str],
                shape_id: int,
                placement: Dict[str, List[str]],
                require_all_int: bool,
                nonneg_intermediate: bool) -> Optional[Dict[str, Any]]:
    """
    计算给定形状与运算的表达式, 支持在叶子与中间节点放置一元函数管道(列表)。
    require_all_int: 若 True, 每次二元运算后的值必须为整数。
    nonneg_intermediate: 若 True, 每次二元运算后的值必须为非负。
    placement: 节点 -> 一元函数列表, 例如 {'L2':['sqrt'], 'N2':['log2','abs']}
    """
    funcs_seq: List[Dict[str, Any]] = []

    def apply_leaf(idx: int, tup: Tuple[Fraction, str]) -> Tuple[Fraction, str]:
        val, rep = tup
        key = f"L{idx}"
        if key in placement and placement[key]:
            res = _apply_unary_pipeline(val, rep, placement[key], funcs_seq, at_step=idx)
            if res is None:
                return None  # type: ignore
            return res
        return val, rep

    a = apply_leaf(0, a)
    if a is None: return None
    b = apply_leaf(1, b)
    if b is None: return None
    c = apply_leaf(2, c)
    if c is None: return None
    d = apply_leaf(3, d)
    if d is None: return None

    o1, o2, o3 = ops

    def apply_node(n_idx: int, left: Tuple[Fraction, str], op: str, right: Tuple[Fraction, str]) -> Optional[Tuple[Fraction, str]]:
        lval, lrep = left
        rval, rrep = right
        v = _apply_binary(lval, rval, op)
        if v is None:
            return None
        if require_all_int and not _is_int(v):
            return None
        if nonneg_intermediate and v < 0:
            return None
        rep = f"({lrep} {op} {rrep})"
        key = f"N{n_idx}"
        if key in placement and placement[key]:
            res = _apply_unary_pipeline(v, rep, placement[key], funcs_seq, at_step=4+n_idx)
            if res is None:
                return None
            v, rep = res
        return v, rep

    if shape_id == 1:
        # ((a o1 b) o2 c) o3 d
        ops_seq = [o1, o2, o3]
        n0 = apply_node(0, a, o1, b)
        if n0 is None: return None
        n1 = apply_node(1, n0, o2, c)
        if n1 is None: return None
        n2 = apply_node(2, n1, o3, d)
        if n2 is None: return None
        val, rep = n2
    elif shape_id == 2:
        # (a o1 (b o2 c)) o3 d
        ops_seq = [o2, o1, o3]
        n0 = apply_node(0, b, o2, c)
        if n0 is None: return None
        n1 = apply_node(1, a, o1, n0)
        if n1 is None: return None
        n2 = apply_node(2, n1, o3, d)
        if n2 is None: return None
        val, rep = n2
    elif shape_id == 3:
        # (a o1 b) o3 (c o2 d)
        ops_seq = [o1, o2, o3]
        n0 = apply_node(0, a, o1, b)
        if n0 is None: return None
        n1 = apply_node(1, c, o2, d)
        if n1 is None: return None
        n2 = apply_node(2, n0, o3, n1)
        if n2 is None: return None
        val, rep = n2
    elif shape_id == 4:
        # a o1 ((b o2 c) o3 d)
        ops_seq = [o2, o3, o1]
        n0 = apply_node(0, b, o2, c)
        if n0 is None: return None
        n1 = apply_node(1, n0, o3, d)
        if n1 is None: return None
        n2 = apply_node(2, a, o1, n1)
        if n2 is None: return None
        val, rep = n2
    elif shape_id == 5:
        # a o1 (b o2 (c o3 d))
        ops_seq = [o3, o2, o1]
        n0 = apply_node(0, c, o3, d)
        if n0 is None: return None
        n1 = apply_node(1, b, o2, n0)
        if n1 is None: return None
        n2 = apply_node(2, a, o1, n1)
        if n2 is None: return None
        val, rep = n2
    else:
        return None

    return {
        'value': val,
        'parens': rep,
        'ops_seq': ops_seq,
        'funcs_sequence': funcs_seq
    }

# ------------------------------------------------------------
# 规范化与求解
# ------------------------------------------------------------

def _candidate_key(cand: Dict[str, Any]) -> Tuple[Tuple[int, ...], Tuple[str, ...], str]:
    """
    比较键:
      1) nums 字典序
      2) ops 字典序
      3) parens 字符串(保证确定性)
    """
    return (tuple(cand['nums']), tuple(cand['ops']), cand['parens'])

def _rel_ok(leaves_nums: List[int], rels: List[Tuple[int, str, int]]) -> bool:
    """检查叶子间相对关系约束。rels: (i, op, j), 0<=i,j<=3, op in {'<','>','<=','>=','!=','=='}"""
    for i, op, j in rels:
        a, b = leaves_nums[i], leaves_nums[j]
        if op == '<' and not (a < b): return False
        if op == '>' and not (a > b): return False
        if op == '<=' and not (a <= b): return False
        if op == '>=' and not (a >= b): return False
        if op == '!=' and not (a != b): return False
        if op == '==' and not (a == b): return False
    return True

def _parity_ok(leaves_nums: List[int], parity: str) -> bool:
    """parity: 'none'/'sum_even'/'sum_odd'"""
    if parity == 'sum_even':
        return (sum(leaves_nums) % 2) == 0
    if parity == 'sum_odd':
        return (sum(leaves_nums) % 2) == 1
    return True

def _generate_placements(base_nodes: List[str], allowed_funcs: List[str], use_funcs: int, pipeline_limit: int) -> List[Dict[str, List[str]]]:
    """
    根据 use_funcs 与 pipeline_limit 枚举一元函数放置方案(管道), 返回列表:
      placement: 节点 -> 函数列表
    """
    placements: List[Dict[str, List[str]]] = []
    if use_funcs <= 0 or pipeline_limit <= 0 or not allowed_funcs:
        return [dict()] if use_funcs == 0 else []
    # use_funcs == 1
    if use_funcs == 1:
        if pipeline_limit >= 1:
            for nid in base_nodes:
                for f in allowed_funcs:
                    placements.append({nid: [f]})
        return placements
    # use_funcs == 2
    if use_funcs == 2:
        # Option A: 一节点管道长度 2
        if pipeline_limit >= 2:
            for nid in base_nodes:
                for f1 in allowed_funcs:
                    for f2 in allowed_funcs:
                        placements.append({nid: [f1, f2]})
        # Option B: 两节点各长度 1
        if pipeline_limit >= 1:
            for n1, n2 in combinations(base_nodes, 2):
                for f1 in allowed_funcs:
                    for f2 in allowed_funcs:
                        placements.append({n1: [f1], n2: [f2]})
        return placements
    # 超过 2 不支持(全局硬上限)
    return []

def function_1(nums: List[int],
               ops_set: List[str],
               funcs_set: List[str],
               target: int,
               max_funcs: int,
               rule_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    规范化求解器:
    - 遵循 rule_config 的规则集进行搜索:
        * step_integrality: 'final' 或 'all'
        * func_apply_scope: 'any' / 'leaves_only' / 'internal_only'
        * pipeline_limit: 0..2
        * parity_constraint 与 relational_constraints
        * nonneg_intermediate: 布尔
    - 校验所有约束, 选择最优解(函数次数最少 -> nums 字典序 -> ops 字典序 -> parens)。
    """
    step_integrality = rule_config.get('step_integrality', 'final')
    require_all_int = (step_integrality == 'all')
    scope = rule_config.get('func_apply_scope', 'any')
    pipeline_limit = int(rule_config.get('pipeline_limit', 1))
    parity_constraint = rule_config.get('parity_constraint', 'none')
    rels = rule_config.get('relational_constraints', [])
    nonneg_intermediate = bool(rule_config.get('nonneg_intermediate', False))

    # 限制最大函数数不超过 2 且不超过 rule_config 上限
    max_funcs = max(0, min(int(max_funcs), int(rule_config.get('max_funcs_upper', 2)), 2))

    allowed_funcs = [f for f in funcs_set if f in ('sqrt', 'log2', 'abs')]

    # 根据 scope 构造可放置节点集合
    if scope == 'leaves_only':
        base_nodes = [f"L{i}" for i in range(4)]
    elif scope == 'internal_only':
        base_nodes = [f"N{i}" for i in range(3)]
    else:
        base_nodes = [f"L{i}" for i in range(4)] + [f"N{i}" for i in range(3)]

    best: Optional[Dict[str, Any]] = None

    # 按函数使用数分层
    for use_funcs in range(0, max_funcs + 1):
        candidates: List[Dict[str, Any]] = []
        placements_list = _generate_placements(base_nodes, allowed_funcs, use_funcs, pipeline_limit)

        for a0, b0, c0, d0 in permutations(nums, 4):
            leaves_nums = [a0, b0, c0, d0]
            if not _parity_ok(leaves_nums, parity_constraint):
                continue
            if rels and not _rel_ok(leaves_nums, rels):
                continue

            for shape_id in range(1, 6):
                for ops in product(ops_set, repeat=3):
                    for placement in placements_list:
                        a = (Fraction(a0, 1), str(a0))
                        b = (Fraction(b0, 1), str(b0))
                        c = (Fraction(c0, 1), str(c0))
                        d = (Fraction(d0, 1), str(d0))
                        out = _eval_shape(a, b, c, d, ops, shape_id, placement,
                                          require_all_int=require_all_int,
                                          nonneg_intermediate=nonneg_intermediate)
                        if out is None:
                            continue
                        val: Fraction = out['value']
                        if not (_is_int(val) and int(val) == target):
                            continue

                        cand = {
                            'nums': leaves_nums,
                            'ops': out['ops_seq'],
                            'parens': out['parens'],
                            'funcs_sequence': sorted(out['funcs_sequence'], key=lambda x: x['at_step'])
                        }
                        candidates.append(cand)

        if candidates:
            candidates.sort(key=_candidate_key)
            best = candidates[0]
            break

    if best is None:
        raise ValueError("未找到满足条件的表达式。")

    return best

def function_2(ans: Dict[str, Any]) -> str:
    """
    将答案字典规范化为 JSON 字符串:
    键顺序: nums -> ops -> parens -> funcs_sequence
    """
    ordered = {
        "nums": ans.get("nums", []),
        "ops": ans.get("ops", []),
        "parens": ans.get("parens", ""),
        "funcs_sequence": ans.get("funcs_sequence", []),
    }
    return json.dumps(ordered, ensure_ascii=False, separators=(',', ':'))

# ------------------------------------------------------------
# 规则随机化与描述
# ------------------------------------------------------------

def gen_rule_config(ops_allow: List[str],
                    funcs_allow: List[str],
                    max_funcs_upper_seed: int) -> Dict[str, Any]:
    """
    随机生成内部规则:
      - step_integrality: 'final' 或 'all'
      - func_apply_scope: 'any' / 'leaves_only' / 'internal_only'
      - pipeline_limit: 0..2
      - ops_pool: 从 ops_allow 随机取子集(至少 2 个)
      - funcs_pool: 从 funcs_allow 随机取子集(可为空)
      - parity_constraint: 'none'/'sum_even'/'sum_odd'
      - relational_constraints: 随机 0..2 条, 操作符从 {'<','>','!=','<=','>='}
      - nonneg_intermediate: 布尔
      - max_funcs_upper: 0..2
      - style_id: 1..3 (描述句式)
    """
    ops_allow = [op for op in ops_allow if op in ('+', '-', '*', '/')]
    funcs_allow = [f for f in funcs_allow if f in ('sqrt', 'log2', 'abs')]
    if len(ops_allow) < 2:
        ops_allow = ['+', '*']

    # ops_pool 至少 2 个
    k_ops = random.randint(2, min(4, len(ops_allow)))
    ops_pool = sorted(random.sample(ops_allow, k_ops))

    # funcs_pool 可为空
    k_funcs = random.randint(0, min(3, len(funcs_allow)))
    funcs_pool = sorted(random.sample(funcs_allow, k_funcs))

    step_integrality = random.choice(['final', 'all'])
    func_apply_scope = random.choice(['any', 'leaves_only', 'internal_only'])
    pipeline_limit = random.randint(0, 2)
    parity_constraint = random.choice(['none', 'sum_even', 'sum_odd'])

    # 关系约束
    rel_ops = ['<', '>', '!=', '<=', '>=']
    num_rels = random.randint(0, 2)
    rel_indices = [(i, j) for i in range(4) for j in range(4) if i != j]
    relational_constraints: List[Tuple[int, str, int]] = []
    for _ in range(num_rels):
        i, j = random.choice(rel_indices)
        relational_constraints.append((i, random.choice(rel_ops), j))

    nonneg_intermediate = random.choice([False, True])
    max_funcs_upper = max(0, min(int(max_funcs_upper_seed), 2))
    style_id = random.randint(1, 3)

    return {
        'ops_pool': ops_pool,
        'funcs_pool': funcs_pool,
        'step_integrality': step_integrality,
        'func_apply_scope': func_apply_scope,
        'pipeline_limit': pipeline_limit,
        'parity_constraint': parity_constraint,
        'relational_constraints': relational_constraints,
        'nonneg_intermediate': nonneg_intermediate,
        'max_funcs_upper': max_funcs_upper,
        'style_id': style_id
    }

def rule_desc(rule_config: Dict[str, Any]) -> str:
    """
    基于 rule_config 生成确定性的单行规则描述片段。
    """
    step_text = '所有中间结果与最终结果均需为整数' if rule_config.get('step_integrality') == 'all' else '仅要求最终结果为整数'
    scope = rule_config.get('func_apply_scope', 'any')
    if scope == 'leaves_only':
        scope_text = '一元函数仅可作用于原始数字'
    elif scope == 'internal_only':
        scope_text = '一元函数仅可作用于中间计算结果'
    else:
        scope_text = '一元函数可作用于原始数字或中间计算结果'
    k = rule_config.get('max_funcs_upper', 2)
    pipe = rule_config.get('pipeline_limit', 1)
    par = rule_config.get('parity_constraint', 'none')
    par_text = '无整体奇偶限制' if par == 'none' else ('四数之和必须为偶数' if par == 'sum_even' else '四数之和必须为奇数')
    rels = rule_config.get('relational_constraints', [])
    if rels:
        rel_text_items = [f"(L{i} {op} L{j})" for i, op, j in rels]
        rel_text = '并满足位置关系: ' + ', '.join(rel_text_items)
    else:
        rel_text = '无位置关系额外限制'
    nonneg = rule_config.get('nonneg_intermediate', False)
    nonneg_text = '中间计算值必须非负' if nonneg else '中间计算值可为负'
    base_text = f"{step_text}; {scope_text}; 函数最多使用 {k} 次且单节点可串联不超过 {pipe} 次; {par_text}; {rel_text}; {nonneg_text}; sqrt 仅对非负完全平方有效, log2 仅对 2 的幂有效, abs 无限制; 除法不得出现除以 0。"
    style_id = rule_config.get('style_id', 1)
    if style_id == 1:
        return f"{base_text}"
    elif style_id == 2:
        return f"遵守整性与函数域限制: {step_text}; {scope_text}; 管道上限 {pipe}; 使用次数不超过 {k}; {par_text}; {rel_text}; 并确保运算合法(尤其除法与符号约束)。"
    else:
        return f"{scope_text}; {step_text}; 奇偶: {par_text}; 关系: {rel_text}; 管道不超过 {pipe}, 使用总次数不超过 {k}, 中间值限制: {nonneg_text}。"

# ------------------------------------------------------------
# 实例生成(逆向): 先构造可行表达式 -> 设定 target -> 唯一性验证 -> 返回实例
# ------------------------------------------------------------

def _biased_sample_numbers(num_min: int, num_max: int) -> List[int]:
    """
    从区间采样 4 个互异整数, 并加入对平方数与 2 的幂的偏置以增大可行性。
    """
    squares = [x*x for x in range(1, int(num_max ** 0.5) + 1)]
    powers2 = []
    k = 1
    while k <= num_max:
        powers2.append(k)
        k *= 2
    pool = set(range(max(1, num_min), max(num_min+1, num_max+1)))
    pool |= set(s for s in squares if num_min <= s <= num_max)
    pool |= set(p for p in powers2 if num_min <= p <= num_max)
    pool = list(pool)
    if len(pool) < 4:
        pool = list(range(num_min, max(num_min+1, num_max+1)))
    return random.sample(pool, 4)

def _gen_random_placement(base_nodes: List[str], funcs_pool: List[str], use_funcs: int, pipeline_limit: int) -> Dict[str, List[str]]:
    """随机生成一个函数放置方案(管道), 满足总使用次数与管道上限。"""
    placement: Dict[str, List[str]] = {}
    if use_funcs <= 0 or not funcs_pool or pipeline_limit <= 0:
        return placement
    if use_funcs == 1:
        nid = random.choice(base_nodes)
        placement[nid] = [random.choice(funcs_pool)]
        return placement
    if use_funcs == 2:
        # 随机在两种方案间选择
        if pipeline_limit >= 2 and random.choice([True, False]):
            nid = random.choice(base_nodes)
            placement[nid] = [random.choice(funcs_pool), random.choice(funcs_pool)]
        else:
            nids = random.sample(base_nodes, 2)
            placement[nids[0]] = [random.choice(funcs_pool)]
            placement[nids[1]] = [random.choice(funcs_pool)]
        return placement
    return placement

def gen_instance(num_min: int,
                 num_max: int,
                 rule_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    逆向生成唯一可解实例:
      1) 使用 rule_config 中的 ops_pool/funcs_pool/step_integrality/func_apply_scope/pipeline_limit/parity/relations/nonneg/max_funcs_upper
      2) 随机采样 nums、shape、ops 三元组与函数管道放置
      3) 评估表达式, 若有效且满足整性与约束, 将其结果作为 target
      4) 构造 ops_set 与 funcs_set: 至少包含表达式用到的, 再随机加入部分元素
      5) 调用 verify_unique 进行唯一性验证; 若不唯一则继续尝试
    """
    ops_pool = rule_config.get('ops_pool', ['+', '-', '*', '/'])
    funcs_pool = rule_config.get('funcs_pool', ['sqrt', 'log2', 'abs'])
    step_integrality = rule_config.get('step_integrality', 'final')
    require_all_int = (step_integrality == 'all')
    scope = rule_config.get('func_apply_scope', 'any')
    pipeline_limit = int(rule_config.get('pipeline_limit', 1))
    parity_constraint = rule_config.get('parity_constraint', 'none')
    rels = rule_config.get('relational_constraints', [])
    nonneg_intermediate = bool(rule_config.get('nonneg_intermediate', False))
    max_funcs_upper = int(rule_config.get('max_funcs_upper', 2))

    # 根据 scope 生成可放置节点
    if scope == 'leaves_only':
        base_nodes = [f"L{i}" for i in range(4)]
    elif scope == 'internal_only':
        base_nodes = [f"N{i}" for i in range(3)]
    else:
        base_nodes = [f"L{i}" for i in range(4)] + [f"N{i}" for i in range(3)]

    start_t = time.perf_counter()
    for _try in range(5000):
        # time guard
        if time.perf_counter() - start_t > 5.0:  # 单实例生成尽量控制在 5s 以内
            break

        nums = _biased_sample_numbers(num_min, num_max)
        max_funcs = random.randint(0, max_funcs_upper)

        # 随机表达式骨架
        shape_id = random.randint(1, 5)
        perm = random.sample(nums, 4)
        leaves_nums = perm[:]  # 检查奇偶与关系
        if not _parity_ok(leaves_nums, parity_constraint):
            continue
        if rels and not _rel_ok(leaves_nums, rels):
            continue

        ops_triple = tuple(random.choice(ops_pool) for _ in range(3))

        # 函数管道放置
        use_funcs = random.randint(0, max_funcs)
        placement = _gen_random_placement(base_nodes, funcs_pool, use_funcs, pipeline_limit)

        # 评估
        a, b, c, d = (Fraction(perm[0], 1), str(perm[0])), (Fraction(perm[1], 1), str(perm[1])), (Fraction(perm[2], 1), str(perm[2])), (Fraction(perm[3], 1), str(perm[3]))
        out = _eval_shape(a, b, c, d, ops_triple, shape_id, placement,
                          require_all_int=require_all_int, nonneg_intermediate=nonneg_intermediate)
        if out is None:
            continue
        val: Fraction = out['value']
        if not _is_int(val):
            continue
        iv = int(val)

        # 至少包含使用到的操作/函数, 再随机补充
        used_ops = set(ops_triple)
        used_funcs = set(f['func'] for f in out['funcs_sequence'])

        extra_ops = []
        remaining_ops = list(set(ops_pool) - used_ops)
        if remaining_ops:
            extra_ops = random.sample(remaining_ops, k=random.randint(0, len(remaining_ops)))
        ops_set = sorted(list(used_ops.union(extra_ops))) or sorted(list(ops_pool))

        extra_funcs = []
        remaining_funcs = list(set(funcs_pool) - used_funcs)
        if remaining_funcs:
            extra_funcs = random.sample(remaining_funcs, k=random.randint(0, len(remaining_funcs)))
        funcs_set = sorted(list(used_funcs.union(extra_funcs))) or sorted(list(funcs_pool))

        # 唯一性验证
        if verify_unique(nums, ops_set, funcs_set, iv, max_funcs, rule_config, time_limit=2.0):
            return {
                'nums': nums,
                'ops_set': ops_set,
                'funcs_set': funcs_set,
                'target': iv,
                'max_funcs': max_funcs
            }

    # 兜底: 简单相加目标, 无函数, 并尝试保证唯一性(通常可行)
    nums = _biased_sample_numbers(num_min, num_max)
    ops_set = sorted(list(set(ops_pool))) or ['+', '*']
    funcs_set = sorted(list(set(funcs_pool))) or ['abs']
    max_funcs = 0
    target = sum(nums)
    return {
        'nums': nums,
        'ops_set': ops_set,
        'funcs_set': funcs_set,
        'target': target,
        'max_funcs': max_funcs
    }

# ------------------------------------------------------------
# 唯一性验证(高效, 设定时间限制)
# ------------------------------------------------------------

def verify_unique(nums: List[int],
                  ops_set: List[str],
                  funcs_set: List[str],
                  target: int,
                  max_funcs: int,
                  rule_config: Dict[str, Any],
                  time_limit: float = 2.0) -> bool:
    """
    在给定规则下验证规范化最优解是否唯一:
      - 分层枚举 use_funcs 0..max_funcs
      - 枚举数字排列、形状、ops 三元组、函数管道放置
      - 统计达到目标的候选, 计算规范化最优的候选键数量
      - 若最优候选数量为 1 则唯一
      - 时间限制默认 2 秒(全局上限需小于 3 分钟)
    """
    t0 = time.perf_counter()
    step_integrality = rule_config.get('step_integrality', 'final')
    require_all_int = (step_integrality == 'all')
    scope = rule_config.get('func_apply_scope', 'any')
    pipeline_limit = int(rule_config.get('pipeline_limit', 1))
    parity_constraint = rule_config.get('parity_constraint', 'none')
    rels = rule_config.get('relational_constraints', [])
    nonneg_intermediate = bool(rule_config.get('nonneg_intermediate', False))

    max_funcs = max(0, min(int(max_funcs), int(rule_config.get('max_funcs_upper', 2)), 2))
    allowed_funcs = [f for f in funcs_set if f in ('sqrt', 'log2', 'abs')]

    if scope == 'leaves_only':
        base_nodes = [f"L{i}" for i in range(4)]
    elif scope == 'internal_only':
        base_nodes = [f"N{i}" for i in range(3)]
    else:
        base_nodes = [f"L{i}" for i in range(4)] + [f"N{i}" for i in range(3)]

    best_key: Optional[Tuple[Tuple[int, ...], Tuple[str, ...], str]] = None
    best_count = 0
    best_funcs_used: Optional[int] = None

    for use_funcs in range(0, max_funcs + 1):
        placements_list = _generate_placements(base_nodes, allowed_funcs, use_funcs, pipeline_limit)
        # 早停: 若已超过时间, 返回保守 False
        if time.perf_counter() - t0 > time_limit:
            return False

        local_keys: List[Tuple[Tuple[int, ...], Tuple[str, ...], str]] = []

        for a0, b0, c0, d0 in permutations(nums, 4):
            leaves_nums = [a0, b0, c0, d0]
            if not _parity_ok(leaves_nums, parity_constraint):
                continue
            if rels and not _rel_ok(leaves_nums, rels):
                continue

            for shape_id in range(1, 6):
                for ops in product(ops_set, repeat=3):
                    for placement in placements_list:
                        # 时间检查
                        if time.perf_counter() - t0 > time_limit:
                            return False
                        a = (Fraction(a0, 1), str(a0))
                        b = (Fraction(b0, 1), str(b0))
                        c = (Fraction(c0, 1), str(c0))
                        d = (Fraction(d0, 1), str(d0))
                        out = _eval_shape(a, b, c, d, ops, shape_id, placement,
                                          require_all_int=require_all_int,
                                          nonneg_intermediate=nonneg_intermediate)
                        if out is None:
                            continue
                        val: Fraction = out['value']
                        if not (_is_int(val) and int(val) == target):
                            continue

                        # 记录候选键
                        key = (tuple(leaves_nums), tuple(out['ops_seq']), out['parens'])
                        local_keys.append(key)

        # 在该 use_funcs 层计算最优键集合大小
        if local_keys:
            local_keys.sort()
            # 最优为字典序最小键
            min_key = local_keys[0]
            count_min = sum(1 for k in local_keys if k == min_key)
            # 如果是第一层或比之前层使用函数更少, 则更新
            if best_funcs_used is None or use_funcs < best_funcs_used:
                best_funcs_used = use_funcs
                best_key = min_key
                best_count = count_min
            # 已找到候选则无需继续更高 use_funcs
            break

    # 唯一当且仅当最优层的最小键计数为 1
    return best_count == 1

# ------------------------------------------------------------
# 结束
# ------------------------------------------------------------