# math_path_3.py
# 高阶泛化实例生成与唯一解验证（<=3分钟）
# - gen_deep_instance(): 随机生成候选解与多模板复合规则，并通过带剪枝的回溯验证唯一解；非唯一或超时则重试。
# - format_assign(order, digits): 输出 'm=..., n=..., ...' 格式字符串。

import random
import time
from typing import List, Dict, Tuple, Optional, Set

ORDER = ['m','n','o','p','q','r','s','t','u','v']

# ------------------------ 工具函数 ------------------------
def format_assign(order: List[str], digits: List[int]) -> str:
    if len(order) != 10 or len(digits) != 10:
        raise ValueError("变量名或数字列表长度不为 10。")
    if len(set(digits)) != 10:
        raise ValueError("十个数字不互不相同。")
    return ", ".join(f"{name}={val}" for name, val in zip(order, digits))

def _name_to_val(digits: List[int]) -> Dict[str, int]:
    return {name: digits[i] for i, name in enumerate(ORDER)}

def _subset_sum_bounds(remaining_digits: List[int], need_k: int) -> Tuple[int, int]:
    rd_sorted = sorted(remaining_digits)
    if need_k <= 0:
        return 0, 0
    if len(rd_sorted) < need_k:
        return 10**9, -10**9
    min_sum = sum(rd_sorted[:need_k])
    max_sum = sum(rd_sorted[-need_k:])
    return min_sum, max_sum

# ------------------------ 规则生成 ------------------------
def _gen_weights(n: int) -> List[int]:
    return [random.randint(1, 7) for _ in range(n)]

def _build_rule_text(expr: str, rhs: int) -> str:
    return f"{expr} = {rhs}"

def _rule_checksum(name_to_val: Dict[str, int]) -> Tuple[Dict, str]:
    weights = _gen_weights(10)
    M = random.randint(5, 9)
    rhs = sum(weights[i] * name_to_val[ORDER[i]] for i in range(10)) % M
    pairs_text = "[" + ", ".join(f"{ORDER[i]}:{weights[i]}" for i in range(10)) + "]"
    text = f"加权模校验: (Σ w_i*Xi) % {M} = {rhs}，变量与权重映射 {pairs_text}"
    params = {'type': 'checksum', 'weights': weights, 'mod': M, 'rhs': rhs}
    return params, text

def _rule_two_digit(name_to_val: Dict[str, int]) -> Tuple[Dict, str, Set[str]]:
    # 分母 T、V 必非零；若 interpret_two_digit=True，则 R 也必非零
    nonzero_pool = [x for x in ORDER if name_to_val[x] != 0]
    T = random.choice(nonzero_pool)
    remaining1 = [x for x in ORDER if x != T]
    V_candidates = [x for x in remaining1 if name_to_val[x] != 0]
    V = random.choice(V_candidates)
    remaining2 = [x for x in remaining1 if x != V]

    interpret_two_digit = random.choice([True, False])
    if interpret_two_digit:
        R_candidates = [x for x in remaining2 if name_to_val[x] != 0]
    else:
        R_candidates = remaining2[:]
    R = random.choice(R_candidates)
    remaining3 = [x for x in remaining2 if x != R]
    S = random.choice(remaining3)
    remaining4 = [x for x in remaining3 if x != S]
    U = random.choice(remaining4)

    place = random.randint(8, 12)
    k2 = random.randint(2, 9)
    nonzero = {T, V}
    if interpret_two_digit:
        nonzero.add(R)

    rhs = ((place * name_to_val[R] + name_to_val[S]) % name_to_val[T]) + ((name_to_val[U] * k2) % name_to_val[V])
    text = _build_rule_text(f"组合约束: ({place}*{R} + {S}) % {T} + ({U} * {k2}) % {V}", rhs)
    params = {
        'type': 'two_digit',
        'R': R, 'S': S, 'T': T, 'U': U, 'V': V,
        'place': place, 'k2': k2, 'rhs': rhs
    }
    return params, text, nonzero

def _rule_nested_mod(name_to_val: Dict[str, int]) -> Tuple[Dict, str, Set[str]]:
    # 分母 C、D 必非零
    nonzero_pool = [x for x in ORDER if name_to_val[x] != 0]
    C = random.choice(nonzero_pool)
    remaining1 = [x for x in ORDER if x != C]
    D_candidates = [x for x in remaining1 if name_to_val[x] != 0]
    D = random.choice(D_candidates)
    remaining2 = [x for x in remaining1 if x != D]
    A = random.choice(remaining2)
    remaining3 = [x for x in remaining2 if x != A]
    B = random.choice(remaining3)

    k1 = random.randint(2, 9)
    nonzero = {C, D}
    rhs = (name_to_val[A] + (name_to_val[B] % name_to_val[C]) * k1) % name_to_val[D]
    text = _build_rule_text(f"嵌套取模: (({A} + ({B} % {C}) * {k1}) % {D})", rhs)
    params = {'type': 'nested_mod', 'A': A, 'B': B, 'C': C, 'D': D, 'k1': k1, 'rhs': rhs}
    return params, text, nonzero

def _rule_subset_sum_disjoint(name_to_val: Dict[str, int], used_vars: Set[str], size_range=(3,5)) -> Tuple[Dict, str, Set[str]]:
    # 第二条子集和尽量与第一条弱交叉（交集<=1）
    for _ in range(50):
        sz = random.randint(*size_range)
        vars_ = random.sample(ORDER, sz)
        if len(set(vars_) & used_vars) <= 1:
            rhs = sum(name_to_val[v] for v in vars_)
            text = _build_rule_text("子集和值: " + " + ".join(vars_), rhs)
            return {'type': 'subset_sum', 'vars': vars_, 'rhs': rhs}, text, set(vars_)
    # 回退
    sz = random.randint(*size_range)
    vars_ = random.sample(ORDER, sz)
    rhs = sum(name_to_val[v] for v in vars_)
    text = _build_rule_text("子集和值: " + " + ".join(vars_), rhs)
    return {'type': 'subset_sum', 'vars': vars_, 'rhs': rhs}, text, set(vars_)

def _rule_linear_congruence(name_to_val: Dict[str, int]) -> Tuple[Dict, str]:
    X, Y, Z = random.sample(ORDER, 3)
    alpha, beta, gamma = random.randint(1,3), random.randint(1,3), random.randint(1,3)
    M3 = random.randint(4,9)
    rhs = (alpha*name_to_val[X] + beta*name_to_val[Y] + gamma*name_to_val[Z]) % M3
    text = _build_rule_text(f"线性同余: ({alpha}*{X} + {beta}*{Y} + {gamma}*{Z}) % {M3}", rhs)
    params = {'type': 'lin_cong', 'X': X, 'Y': Y, 'Z': Z, 'alpha': alpha, 'beta': beta, 'gamma': gamma, 'mod': M3, 'rhs': rhs}
    return params, text

def _rule_parity2(name_to_val: Dict[str, int]) -> Tuple[Dict, str]:
    sz = random.randint(3, 5)
    vars_ = random.sample(ORDER, sz)
    bias = random.randint(0, 3)
    rhs = (sum(name_to_val[v] for v in vars_) + bias) % 2
    text = _build_rule_text(f"奇偶约束: (" + " + ".join(vars_) + f" + {bias}) % 2", rhs)
    params = {'type': 'parity2', 'vars': vars_, 'bias': bias, 'rhs': rhs}
    return params, text

def _rule_inequalities(name_to_val: Dict[str, int], num=2) -> Tuple[List[Dict], str]:
    pairs = random.sample(ORDER, 2*num)
    pieces = []
    out_params = []
    used = set()
    for i in range(num):
        a, b = pairs[2*i], pairs[2*i+1]
        if a in used or b in used:
            continue
        used.add(a); used.add(b)
        if name_to_val[a] > name_to_val[b]:
            pieces.append(f"{a} > {b}")
            out_params.append({'type': 'ineq', 'a': a, 'b': b, 'op': '>'})
        else:
            pieces.append(f"{a} < {b}")
            out_params.append({'type': 'ineq', 'a': a, 'b': b, 'op': '<'})
    if not pieces:
        a, b = random.sample(ORDER, 2)
        if name_to_val[a] > name_to_val[b]:
            pieces.append(f"{a} > {b}")
            out_params.append({'type': 'ineq', 'a': a, 'b': b, 'op': '>'})
        else:
            pieces.append(f"{a} < {b}")
            out_params.append({'type': 'ineq', 'a': a, 'b': b, 'op': '<'})
    text = "相对大小: " + "; ".join(pieces)
    return out_params, text

# ------------------------ 验证器（唯一解，<= 180s） ------------------------
def _eval_rule_if_ready(assign: Dict[str,int], rule: Dict) -> Tuple[bool, bool]:
    """规则变量齐备时局部验证；否则不触发。返回(ready, holds)。"""
    t = rule['type']
    def has(*vars_): return all(v in assign for v in vars_)
    if t == 'checksum':
        ready = all(v in assign for v in ORDER)
        if not ready: return False, True
        lhs = sum(rule['weights'][i] * assign[ORDER[i]] for i in range(10)) % rule['mod']
        return True, lhs == rule['rhs']
    elif t == 'two_digit':
        ready = has(rule['R'], rule['S'], rule['T'], rule['U'], rule['V'])
        if not ready: return False, True
        lhs = ((rule['place'] * assign[rule['R']] + assign[rule['S']]) % assign[rule['T']]) + ((assign[rule['U']] * rule['k2']) % assign[rule['V']])
        return True, lhs == rule['rhs']
    elif t == 'nested_mod':
        ready = has(rule['A'], rule['B'], rule['C'], rule['D'])
        if not ready: return False, True
        lhs = (assign[rule['A']] + (assign[rule['B']] % assign[rule['C']]) * rule['k1']) % assign[rule['D']]
        return True, lhs == rule['rhs']
    elif t == 'subset_sum':
        vars_ = rule['vars']
        ready = all(v in assign for v in vars_)
        if not ready: return False, True
        lhs = sum(assign[v] for v in vars_)
        return True, lhs == rule['rhs']
    elif t == 'lin_cong':
        ready = has(rule['X'], rule['Y'], rule['Z'])
        if not ready: return False, True
        lhs = (rule['alpha']*assign[rule['X']] + rule['beta']*assign[rule['Y']] + rule['gamma']*assign[rule['Z']]) % rule['mod']
        return True, lhs == rule['rhs']
    elif t == 'parity2':
        vars_ = rule['vars']
        ready = all(v in assign for v in vars_)
        if not ready: return False, True
        lhs = (sum(assign[v] for v in vars_) + rule['bias']) % 2
        return True, lhs == rule['rhs']
    elif t == 'ineq':
        ready = has(rule['a'], rule['b'])
        if not ready: return False, True
        if rule['op'] == '>':
            return True, assign[rule['a']] > assign[rule['b']]
        else:
            return True, assign[rule['a']] < assign[rule['b']]
    else:
        return False, True

def _count_solutions(params: Dict, nonzero_vars: Set[str], time_limit: float = 180.0) -> Tuple[int, Optional[List[int]]]:
    start = time.time()
    rules = params['rules']

    strong_vars: List[str] = []
    for r in rules:
        if r['type'] in ('two_digit', 'nested_mod', 'parity2'):
            for k in r.keys():
                if k in ORDER:
                    strong_vars.append(k)

    var_order = []
    seen = set()
    for x in list(nonzero_vars):
        if x not in seen:
            var_order.append(x); seen.add(x)
    for x in strong_vars:
        if x not in seen:
            var_order.append(x); seen.add(x)
    for x in ORDER:
        if x not in seen:
            var_order.append(x); seen.add(x)

    subset_rules = [r for r in rules if r['type'] == 'subset_sum']
    ineq_rules = [r for r in rules if r['type'] == 'ineq']

    best_solution = None
    solution_count = 0
    must_nonzero = set(nonzero_vars)

    def feasible_partial(assign: Dict[str,int], remaining_digits: Set[int]) -> bool:
        # 子集和剪枝
        rd_list = list(remaining_digits)
        for r in subset_rules:
            vars_ = r['vars']
            target = r['rhs']
            assigned_sum = sum(assign[x] for x in vars_ if x in assign)
            left_vars = [x for x in vars_ if x not in assign]
            need_k = len(left_vars)
            min_possible, max_possible = _subset_sum_bounds(rd_list, need_k)
            if not (assigned_sum + min_possible <= target <= assigned_sum + max_possible):
                return False
        # 不等式
        for r in ineq_rules:
            a, b, op = r['a'], r['b'], r['op']
            if a in assign and b in assign:
                if op == '>' and not (assign[a] > assign[b]): return False
                if op == '<' and not (assign[a] < assign[b]): return False
        # 就绪即检
        for r in rules:
            if r['type'] in ('subset_sum','ineq'):
                continue
            ready, holds = _eval_rule_if_ready(assign, r)
            if ready and not holds:
                return False
        # 时限
        if time.time() - start > time_limit:
            return False
        return True

    def check_full(assign: Dict[str,int]) -> bool:
        for r in rules:
            ready, holds = _eval_rule_if_ready(assign, r)
            if not ready or not holds:
                return False
        return True

    def dfs(idx: int, assign: Dict[str,int], remaining_digits: Set[int]) -> None:
        nonlocal solution_count, best_solution
        if solution_count >= 2:
            return
        if time.time() - start > time_limit:
            return
        if idx == len(var_order):
            if check_full(assign):
                solution_count += 1
                if best_solution is None:
                    best_solution = [assign[name] for name in ORDER]
            return
        var = var_order[idx]
        candidates = list(remaining_digits)
        if var in must_nonzero and 0 in candidates:
            candidates.remove(0)
        candidates.sort()
        for d in candidates:
            assign[var] = d
            rem = remaining_digits.copy()
            rem.remove(d)
            if feasible_partial(assign, rem):
                dfs(idx+1, assign, rem)
            del assign[var]
            if solution_count >= 2 or (time.time() - start > time_limit):
                return

    dfs(0, {}, set(range(10)))
    return solution_count, best_solution

# ------------------------ 生成器（带唯一解验证） ------------------------
def gen_deep_instance() -> Dict[str, object]:
    deadline = time.time() + 180.0
    while time.time() < deadline:
        base_digits = list(range(10))
        random.shuffle(base_digits)
        name_to_val = _name_to_val(base_digits)

        rules_params: List[Dict] = []
        rules_texts: List[str] = []
        nonzero_vars: Set[str] = set()

        # 强约束：加权模、两位数组合、嵌套取模、第一条子集和
        p_checksum, t_checksum = _rule_checksum(name_to_val)
        rules_params.append(p_checksum); rules_texts.append(t_checksum)

        p_two, t_two, nz_two = _rule_two_digit(name_to_val)
        rules_params.append(p_two); rules_texts.append(t_two); nonzero_vars |= nz_two

        p_nested, t_nested, nz_nested = _rule_nested_mod(name_to_val)
        rules_params.append(p_nested); rules_texts.append(t_nested); nonzero_vars |= nz_nested

        p_ss1, t_ss1, ss1_vars = _rule_subset_sum_disjoint(name_to_val, used_vars=set(), size_range=(3,5))
        rules_params.append(p_ss1); rules_texts.append(t_ss1)

        # 可选补强：第二个子集和（弱交叉）或线性同余
        if random.choice([True, False]):
            p_ss2, t_ss2, _ = _rule_subset_sum_disjoint(name_to_val, used_vars=ss1_vars, size_range=(3,5))
            rules_params.append(p_ss2); rules_texts.append(t_ss2)
        else:
            p_lin, t_lin = _rule_linear_congruence(name_to_val)
            rules_params.append(p_lin); rules_texts.append(t_lin)

        # 可选奇偶约束
        if random.choice([True, False]):
            p_par, t_par = _rule_parity2(name_to_val)
            rules_params.append(p_par); rules_texts.append(t_par)

        # 不等式链：2~3 条，分散变量覆盖
        ineq_num = random.randint(2, 3)
        ineq_params, ineq_text = _rule_inequalities(name_to_val, num=ineq_num)
        rules_params.extend(ineq_params); rules_texts.append(ineq_text)

        # 唯一解验证
        verify_params = {'rules': rules_params}
        remaining_time = max(1.0, deadline - time.time())
        cnt, witness = _count_solutions(verify_params, nonzero_vars, time_limit=remaining_time)
        if cnt == 1 and witness is not None:
            nonzero_sorted = sorted(list(nonzero_vars))
            nonzero_desc = ("以下变量必须非零: " + ", ".join(nonzero_sorted)) if nonzero_sorted else "无额外非零约束"
            rules_numbered = [f"{i+1}) {txt}" for i, txt in enumerate(rules_texts)]
            explain_text = "符号 % 表示取模，a % b 为 a 除以 b 的余数；加权项 place*x + y 为以 place 为系数的线性组合；变量与权重以 [(变量:权重)] 显示；奇偶约束 (和 + 偏置) % 2 = 常数；所有规则的右端常数均由同一组变量赋值计算得到"
            notes_text = "答题格式为模板，不含数值提示；请严格使用'===='连接和值与赋值序列，不要添加额外空格或字符"

            return {
                'order': ORDER,
                'digits': witness,
                'rules_texts': rules_texts,
                'rules_numbered': rules_numbered,
                'nonzero_desc': nonzero_desc,
                'explain_text': explain_text,
                'notes_text': notes_text,
            }
    raise RuntimeError("生成唯一解实例超时，请重试。")