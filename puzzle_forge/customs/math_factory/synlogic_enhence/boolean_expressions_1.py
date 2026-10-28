# boolean_expressions_5.py
import random
from math import gcd
from typing import List, Dict, Any, Tuple

# -----------------------
# 基础工具（供YAML调用）
# -----------------------
def randbool() -> bool:
    return bool(random.getrandbits(1))

def randint(a: int, b: int) -> int:
    return random.randint(a, b)

def list_len(seq) -> int:
    try:
        return len(list(seq))
    except Exception:
        return 0

def make_universe(n: int):
    # 生成从1到n的自然数集合列表
    if n is None or n <= 0:
        return []
    return list(range(1, n + 1))

def is_prime(n: int) -> bool:
    if n is None:
        return False
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True

def random_prime_between(a: int, b: int) -> int:
    if a > b:
        a, b = b, a
    candidates = [x for x in range(max(2, a), b + 1) if is_prime(x)]
    if candidates:
        return random.choice(candidates)
    return random_composite_between(a, b)

def random_composite_between(a: int, b: int) -> int:
    if a > b:
        a, b = b, a
    candidates = [x for x in range(max(4, a), b + 1) if not is_prime(x)]
    if candidates:
        return random.choice(candidates)
    return random.randint(a, b)

def random_y_given_z(z: int, small_flag: bool) -> int:
    base = z * z
    if small_flag:
        if base <= 1:
            return 0
        val = random.randint(0, max(0, base - 1))
        sign = random.choice([-1, 1])
        return sign * val
    else:
        val = random.randint(base, base + 20)
        sign = random.choice([-1, 1])
        return sign * val

def choose_subset(universe, k: int):
    if k <= 0:
        return []
    if k >= len(universe):
        return list(universe)
    return random.sample(list(universe), k)

def choose_superset_or_random(A, universe, m: int, subset_flag: bool):
    A_set = set(A)
    U = list(universe)
    if m <= 0:
        return []
    if subset_flag:
        need = max(0, m - len(A_set))
        remainder = [x for x in U if x not in A_set]
        if need > len(remainder):
            extra = remainder
        else:
            extra = random.sample(remainder, need)
        res = list(A_set) + extra
        if len(res) < m:
            pad_pool = [x for x in U if x not in set(res)]
            add_num = m - len(res)
            if add_num > len(pad_pool):
                res = list(set(res))
            else:
                res += random.sample(pad_pool, add_num)
        return res[:m]
    else:
        exclude_pool = list(A_set) if A_set else []
        if exclude_pool:
            excluded = random.choice(exclude_pool)
            candidates = [x for x in U if x != excluded]
        else:
            candidates = U[:]
        if m > len(candidates):
            return choose_subset(U, min(m, len(U)))
        return random.sample(candidates, m)

def is_proper_subset(A, B) -> bool:
    try:
        return set(A) < set(B)
    except Exception:
        return False

def is_subset(X, Y) -> bool:
    try:
        return set(X) <= set(Y)
    except Exception:
        return False

def has_intersection(A, B) -> bool:
    try:
        return len(set(A).intersection(set(B))) > 0
    except Exception:
        return False

# -----------------------
# 算术与集合类模板（1..8）
# -----------------------
def tmpl_conj_xy5z_and_proper(A, B, x, y, z, rng) -> Tuple[str, bool, str]:
    # ((x*y + k*z == t) and (A proper subset of B))
    k = rng.choice([3, 4, 5, 6])
    base = x * y + k * z
    t = base + rng.choice([-2, -1, 0, 1, 2, -3, 3])
    text = f"合取判断 左式为 x 乘以 y 加上 {k} 乘以 z 等于 {t} 且 右式为 A 是 B 的真子集"
    truth = (x * y + k * z == t) and is_proper_subset(A, B)
    return text, truth, 'mixed'

def tmpl_not_prime_and_small_y(x, y, z) -> Tuple[str, bool, str]:
    # not ((x is prime) and (|y| < z*z))
    text = "非 判断 x 是质数 且 y 的绝对值小于 z 的平方"
    truth = not (is_prime(x) and (abs(y) < z * z))
    return text, truth, 'arith'

def tmpl_disj_sum_eq_or_coprime(x, y, z, rng) -> Tuple[str, bool, str]:
    # ((x + y) * z == m) or (gcd(|x|, |y|) == 1)
    m = (x + y) * z + rng.choice([-2, -1, 0, 1, 2, -3, 3])
    text = f"析取判断 左式为 x 加 y 再乘以 z 等于 {m} 或 右式为 x 与 y 互质"
    truth = ((x + y) * z == m) or (gcd(abs(x), abs(y)) == 1)
    return text, truth, 'arith'

def tmpl_double_neg_subset_and_sum_nonzero(A, B, x, y, z) -> Tuple[str, bool, str]:
    # not not ((B subset A) and ((x + y + z) != 0))
    text = "非 非 判断 B 是 A 的子集 且 x 加 y 加 z 不等于 0"
    inner = is_subset(B, A) and ((x + y + z) != 0)
    return text, bool(inner), 'mixed'

def tmpl_imp_subset_then_mod(A, B, x, z, rng) -> Tuple[str, bool, str]:
    # If A subset B then x % z == r
    r = rng.randrange(0, z) if z > 0 else 0
    text = f"蕴含判断 如果 A 是 B 的子集 则 x 模 z 等于 {r}"
    truth = (not is_subset(A, B)) or ((x % z) == r if z != 0 else False)
    return text, truth, 'mixed'

def tmpl_iff_evenness(x, y) -> Tuple[str, bool, str]:
    # x even iff y even
    text = "双条件判断 x 是偶数 当且仅当 y 是偶数"
    truth = (x % 2 == 0) == (y % 2 == 0)
    return text, truth, 'arith'

def tmpl_xor_intersect_vs_proper(B, A) -> Tuple[str, bool, str]:
    # XOR between (A∩B≠∅) and (B proper subset A)
    text = "异或判断 A 与 B 的交集非空 与 B 是 A 的真子集 恰有一件成立"
    truth = (has_intersection(A, B)) ^ (is_proper_subset(B, A))
    return text, truth, 'set'

def tmpl_minA_plus_maxB_eq_xy(A, B, x, y) -> Tuple[str, bool, str]:
    # min(A) + max(B) == x + y
    text = "判断 A 的最小元素与 B 的最大元素之和 等于 x 加 y"
    try:
        truth = (min(A) + max(B) == x + y)
    except ValueError:
        truth = False
    return text, truth, 'arith'

# -----------------------
# 模板工厂 —— 算术与集合
# -----------------------
def _make_template(tid: int, rng, x, y, z, A, B):
    if tid == 1:
        return tmpl_conj_xy5z_and_proper(A, B, x, y, z, rng)
    if tid == 2:
        return tmpl_not_prime_and_small_y(x, y, z)
    if tid == 3:
        return tmpl_disj_sum_eq_or_coprime(x, y, z, rng)
    if tid == 4:
        return tmpl_double_neg_subset_and_sum_nonzero(A, B, x, y, z)
    if tid == 5:
        return tmpl_imp_subset_then_mod(A, B, x, z, rng)
    if tid == 6:
        return tmpl_iff_evenness(x, y)
    if tid == 7:
        return tmpl_xor_intersect_vs_proper(B, A)
    if tid == 8:
        return tmpl_minA_plus_maxB_eq_xy(A, B, x, y)
    # 默认回退到算术模板，避免空池时报错
    return tmpl_iff_evenness(x, y)

# -----------------------
# 元模板（9..12）及其规格，用于唯一性与耦合
# -----------------------
def _label(idx: int) -> str:
    """从 0 开始的索引到字母编号 A,B,C,... 超过 26 用 S<编号>"""
    if idx < 26:
        return chr(ord('A') + idx)
    return f"S{idx + 1}"

def meta_count_first_k_equals_spec(k: int, r: int) -> Dict[str, Any]:
    return {"type": "count_eq", "k": k, "r": r}

def meta_parity_first_k_even_spec(k: int) -> Dict[str, Any]:
    return {"type": "parity_k_even", "k": k}

def meta_imp_ab_then_not_c_spec(a: int, b: int, c: int) -> Dict[str, Any]:
    return {"type": "imp_then_not", "a": a, "b": b, "c": c}

def meta_xor_p_q_spec(p: int, q: int) -> Dict[str, Any]:
    return {"type": "xor_pair", "p": p, "q": q}

def eval_meta_truth(spec: Dict[str, Any], base_truths: List[bool]) -> bool:
    t = spec.get("type")
    if t == "count_eq":
        k = spec["k"]
        r = spec["r"]
        k = max(0, min(k, len(base_truths)))
        cnt = sum(1 for i in range(k) if base_truths[i])
        return cnt == r
    if t == "parity_k_even":
        k = spec["k"]
        k = max(0, min(k, len(base_truths)))
        cnt = sum(1 for i in range(k) if base_truths[i])
        return (cnt % 2) == 0
    if t == "imp_then_not":
        a = spec["a"]; b = spec["b"]; c = spec["c"]
        if any(idx < 0 or idx >= len(base_truths) for idx in [a, b, c]):
            return False
        return (not (base_truths[a] and base_truths[b])) or (not base_truths[c])
    if t == "xor_pair":
        p = spec["p"]; q = spec["q"]
        if any(idx < 0 or idx >= len(base_truths) for idx in [p, q]):
            return False
        return (base_truths[p]) ^ (base_truths[q])
    return False

def meta_text_from_spec(spec: Dict[str, Any]) -> str:
    t = spec.get("type")
    if t == "count_eq":
        k = spec["k"]; r = spec["r"]
        return f"元判断 在前 {k} 条陈述中 恰好有 {r} 条为真"
    if t == "parity_k_even":
        k = spec["k"]
        return f"元判断 在前 {k} 条陈述中 真陈述的数量为偶数"
    if t == "imp_then_not":
        a = spec["a"]; b = spec["b"]; c = spec["c"]
        return f"元判断 若第 {_label(a)} 条与第 {_label(b)} 条都为真 则第 {_label(c)} 条为假"
    if t == "xor_pair":
        p = spec["p"]; q = spec["q"]
        return f"元判断 第 {_label(p)} 条与第 {_label(q)} 条 恰有一条为真"
    return "元判断 占位符"

# -----------------------
# 核心接口：生成陈述与校验（强化版，保证类型覆盖与文本去重）
# -----------------------
def gen_statements(x: int, y: int, z: int, A, B, seed: int,
                   stmt_min: int, stmt_max: int, templates_pool: List[int]) -> Dict[str, Any]:
    """
    生成陈述块与真值列表：
    返回 {'block': 文本块, 'truths': [bool, ...], 'kinds': [...], 'meta_specs': [...], 'texts': [...]}
    - 文本不含引号和花括号；
    - 至少生成 6 条基础陈述（受输入范围约束），并保证算术/集合/混合三类覆盖（在可用模板范围内）；
    - 文本严格去重：同一题面内的每条陈述文本不重复；
    - 至少加入 1 条元判断，若空间允许尽量加入 2 条，第一条固定为奇偶性元判断（当模板 10 可用时）。
    """
    # 归一化与兜底
    if stmt_min is None or stmt_max is None or stmt_min <= 0 or stmt_max < stmt_min:
        stmt_min, stmt_max = 6, 8
    pool = [t for t in templates_pool if t in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}]
    if not pool:
        pool = [1, 2, 3, 4, 5, 6, 7, 8]

    rng = random.Random(seed)
    n = rng.randint(stmt_min, stmt_max)

    # 划分基础模板与元模板池
    base_pool = [t for t in pool if t in {1, 2, 3, 4, 5, 6, 7, 8}]
    meta_pool = [t for t in pool if t in {9, 10, 11, 12}]

    # 至少生成 6 条基础陈述；若存在元模板池，预留至少 1 条元判断位
    base_target = max(6, min(n, rng.randint(max(6, n - 2), n)))
    if meta_pool and base_target == n:
        base_target = max(6, n - 1)  # 预留 1 条位给元判断

    labels: List[str] = []
    truths: List[bool] = []
    kinds: List[str] = []
    lines: List[str] = []
    texts: List[str] = []
    text_set = set()

    # 可用类型判断，用于前几条的类型覆盖
    set_available = 7 in base_pool
    mixed_available = any(t in base_pool for t in [1, 4, 5])
    arith_available = any(t in base_pool for t in [2, 3, 6, 8])

    # 前三条强制类型覆盖（仅在该类型可用时强制）
    forced_tids = []
    if set_available:
        forced_tids.append(7)  # set
    elif mixed_available:
        forced_tids.append(rng.choice([t for t in base_pool if t in {1, 4, 5}]))

    if mixed_available:
        forced_tids.append(5)  # mixed（优先使用 5）
    elif set_available or arith_available:
        cand = [t for t in base_pool if t in ({1, 4} if set_available else {2, 3, 8, 6})]
        if cand:
            forced_tids.append(rng.choice(cand))

    if arith_available:
        forced_tids.append(6)  # arith
    else:
        cand = [t for t in base_pool if t in {1, 4, 5, 7}]
        if cand:
            forced_tids.append(rng.choice(cand))

    # 生成基础陈述（前几条为强制覆盖，其余随机但去重）
    for i in range(base_target):
        # 选择模板
        if i < len(forced_tids):
            tid = forced_tids[i]
        else:
            tid = rng.choice(base_pool)

        # 去重尝试
        tries = 0
        while True:
            text, truth, kind = _make_template(tid, rng, x, y, z, A, B)
            if text not in text_set:
                break
            tries += 1
            # 重抽不同模板以避免重复
            alt_pool = [t for t in base_pool if t != tid]
            if not alt_pool:
                break
            tid = rng.choice(alt_pool)
            if tries > 10:
                break

        label = _label(i)
        labels.append(label)
        truths.append(bool(truth))
        kinds.append(kind)
        lines.append(f"- {label}. {text}")
        texts.append(text)
        text_set.add(text)

    # 生成元判断：至少 1 条，若空间允许尽量加入 2 条；第一条固定奇偶性（当 10 可用时）
    meta_specs: List[Dict[str, Any]] = []
    max_meta = max(0, n - base_target)
    meta_cnt = 0
    if meta_pool and max_meta > 0:
        meta_cnt = min(2, max_meta) if max_meta >= 2 else 1
        for j in range(meta_cnt):
            base_truths = truths[:]
            base_n = len(base_truths)
            if base_n < 3:
                break

            if j == 0 and (10 in meta_pool):
                # 第一条为奇偶性（模板 10 可用时）
                k = rng.randint(min(3, base_n), base_n)
                spec = meta_parity_first_k_even_spec(k)
            else:
                # 第二条在计数等式/蕴含/异或中选一条
                candidates = [t for t in meta_pool if t in {9, 11, 12}]
                if not candidates:
                    candidates = meta_pool[:]
                tid = rng.choice(candidates)
                if tid == 9:
                    k = rng.randint(min(3, base_n), base_n)
                    actual = sum(1 for i in range(k) if base_truths[i])
                    r = actual + rng.choice([-1, 0, 1])
                    r = max(0, min(r, k))
                    spec = meta_count_first_k_equals_spec(k, r)
                elif tid == 11:
                    if base_n >= 3:
                        a, b, c = rng.sample(range(base_n), 3)
                        spec = meta_imp_ab_then_not_c_spec(a, b, c)
                    else:
                        k = rng.randint(min(3, base_n), base_n)
                        spec = meta_parity_first_k_even_spec(k)
                elif tid == 12:
                    if base_n >= 2:
                        p, q = rng.sample(range(base_n), 2)
                        spec = meta_xor_p_q_spec(p, q)
                    else:
                        k = rng.randint(min(3, base_n), base_n)
                        spec = meta_parity_first_k_even_spec(k)
                else:
                    k = rng.randint(min(3, base_n), base_n)
                    spec = meta_parity_first_k_even_spec(k)

            meta_truth = eval_meta_truth(spec, base_truths)
            meta_text = meta_text_from_spec(spec)

            idx = base_target + len(meta_specs)
            label = _label(idx)
            labels.append(label)
            truths.append(bool(meta_truth))
            kinds.append('meta')
            # 元判断文本也参与去重
            if meta_text not in text_set:
                lines.append(f"- {label}. {meta_text}")
                texts.append(meta_text)
                text_set.add(meta_text)
            else:
                # 极少数情况下重复（如多次选择同类元判断），附加轻微变体避免重复
                lines.append(f"- {label}. {meta_text} 条件校验")
                texts.append(meta_text + " 条件校验")
                text_set.add(meta_text + " 条件校验")
            meta_specs.append(spec)

    block = "\n".join(lines)
    return {"block": block, "truths": truths, "kinds": kinds, "meta_specs": meta_specs, "texts": texts}

def is_valid_instance_v2(x: int, y: int, z: int, A, B, seed: int,
                         stmt_min: int, stmt_max: int, templates_pool: List[int],
                         truths: List[bool]) -> bool:
    """
    基础一致性校验：
    - 基本数据与集合合理；
    - 重算并与 truths 完全一致；
    - 至少一个真与一个假；
    - 类型多样性（含算术或集合或混合）。
    """
    if z is None or z <= 0:
        return False
    if not isinstance(A, list) or not isinstance(B, list):
        return False
    if len(A) < 2 or len(B) < 2:
        return False
    if set(A) == set(B):
        return False
    if abs(x) > 10**9 or abs(y) > 10**9 or abs(z) > 10**6:
        return False

    recomputed = gen_statements(x, y, z, A, B, seed, stmt_min, stmt_max, templates_pool)
    rt = recomputed.get("truths", [])
    if truths != rt:
        return False
    if len(truths) < 3:
        return False
    if all(truths) or not any(truths):
        return False

    kinds = recomputed.get("kinds", [])
    has_arith = any(k == 'arith' for k in kinds)
    has_set = any(k == 'set' for k in kinds)
    has_mixed = any(k == 'mixed' for k in kinds)
    if not (has_arith or has_set or has_mixed):
        return False
    type_count = len({k for k in kinds})
    if type_count == 1 and not has_mixed:
        return False

    return True

def is_valid_instance_v3(x: int, y: int, z: int, A, B, seed: int,
                         stmt_min: int, stmt_max: int, templates_pool: List[int],
                         truths: List[bool]) -> bool:
    """
    强化版唯一性与复杂度校验（与模板可用性联动）：
    - 继承 v2 的全部检查；
    - 基础段长度 >= 4；
    - 至少包含 1 条元判断；
    - 若模板 10 可用（奇偶性元判断），则必须包含奇偶性元判断；
    - 文本不重复；
    - 类型覆盖：对可用的基础类型（set/mixed/arith）分别要求在基础段中至少出现一次；
    - 敏感性：翻转任一基础真值，至少存在一条元判断真值发生变化。
    """
    if not is_valid_instance_v2(x, y, z, A, B, seed, stmt_min, stmt_max, templates_pool, truths):
        return False

    recomputed = gen_statements(x, y, z, A, B, seed, stmt_min, stmt_max, templates_pool)
    kinds = recomputed.get("kinds", [])
    meta_specs = recomputed.get("meta_specs", [])
    texts = recomputed.get("texts", [])
    if not kinds or not texts:
        return False

    # 文本去重
    if len(set(texts)) != len(texts):
        return False

    # 基础段长度
    base_len = 0
    for k in kinds:
        if k == 'meta':
            break
        base_len += 1
    if base_len < 4:
        return False

    # 至少包含一条元判断
    has_meta = any(k == 'meta' for k in kinds)
    if not has_meta:
        return False
    # 若模板 10 可用则必须包含奇偶性元判断
    must_have_parity = 10 in templates_pool
    if must_have_parity:
        if not any(spec.get("type") == "parity_k_even" for spec in meta_specs):
            return False

    # 类型覆盖：仅对可用类型施加约束
    base_kinds = kinds[:base_len]
    base_pool = [t for t in templates_pool if t in {1, 2, 3, 4, 5, 6, 7, 8}]
    set_available = 7 in base_pool
    mixed_available = any(t in base_pool for t in [1, 4, 5])
    arith_available = any(t in base_pool for t in [2, 3, 6, 8])

    if set_available and not any(k == 'set' for k in base_kinds):
        return False
    if mixed_available and not any(k == 'mixed' for k in base_kinds):
        return False
    if arith_available and not any(k == 'arith' for k in base_kinds):
        return False

    # 敏感性：翻转任一基础真值，检查元判断是否变化
    base_truths = truths[:base_len]
    original_meta = [eval_meta_truth(spec, base_truths) for spec in meta_specs]
    sensitive = False
    for i in range(base_len):
        flipped = base_truths[:]
        flipped[i] = not flipped[i]
        mutated_meta = [eval_meta_truth(spec, flipped) for spec in meta_specs]
        if mutated_meta != original_meta:
            sensitive = True
            break

    return sensitive