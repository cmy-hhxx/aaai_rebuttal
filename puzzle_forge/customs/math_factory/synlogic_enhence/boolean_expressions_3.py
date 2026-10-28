# boolean_expressions_7.py
import random
from typing import List, Dict, Any, Tuple


def is_prime(n: int) -> bool:
    """Return True if n is prime."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def gcd(a: int, b: int) -> int:
    """Greatest common divisor."""
    a, b = abs(a), abs(b)
    while b != 0:
        a, b = b, a % b
    return a


def gen_unique_list(size: int, low: int, high: int) -> List[int]:
    """
    Generate a sorted list of unique integers of given size in [low, high].
    If the requested size exceeds the available range, it will cap at the range size.
    """
    if low > high:
        low, high = high, low
    pool = list(range(low, high + 1))
    if size <= 0:
        return []
    k = min(size, len(pool))
    return sorted(random.sample(pool, k))


# -----------------------------
# 原始模板（返回 (text, truth, category, complexity, params, kind)）
# -----------------------------
def tmpl_pyth_and_in(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： （（a*a 加 b*b 等于 c*c）且（x 属于 E。））
    """
    if random.random() < 0.5 and len(E) > 0:
        x = random.choice(E)
    else:
        low = min(E) - 5 if E else 0
        high = max(E) + 5 if E else 10
        candidates = [v for v in range(low, high + 1) if v not in E]
        x = random.choice(candidates) if candidates else (low - 1)
    truth = (a * a + b * b == c * c) and (x in E)
    text = f"（（a*a 加 b*b 等于 c*c）且（{x} 属于 E。））"
    return text, truth, "arith_set", 2, {"x": x}, "pyth_and_in"


def tmpl_triangle_chain(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： （（a 加 b 大于 c）且（a 小于 b 且 b 小于 c。））
    """
    truth = ((a + b) > c) and (a < b < c)
    text = "（（a 加 b 大于 c）且（a 小于 b 且 b 小于 c。））"
    return text, truth, "ordering", 1, {}, "triangle_chain"


def tmpl_neg_or_membership(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 非 （（（c 减 b 减 a 等于 t）或（y 属于 E。）））
    """
    t = c - b - a
    if random.random() < 0.5:
        t = t + random.choice([-2, -1, 1, 2])
    if random.random() < 0.5 and len(E) > 0:
        y = random.choice(E)
    else:
        low = min(E) - 5 if E else 0
        high = max(E) + 5 if E else 10
        candidates = [v for v in range(low, high + 1) if v not in E]
        y = random.choice(candidates) if candidates else (low - 1)
    truth = not (((c - b - a) == t) or (y in E))
    text = f"非 （（（c 减 b 减 a 等于 {t}）或（{y} 属于 E。）））"
    return text, truth, "neg_or_set", 2, {"t": t, "y": y}, "neg_or_membership"


def _hard_prime_candidate() -> int:
    """
    返回一个不太显然的奇数，用于质数判定，降低显见线索。
    从 21 到 99 的奇数中随机选择。
    """
    odds = [x for x in range(21, 100) if x % 2 == 1]
    return random.choice(odds)


def tmpl_double_neg_or_prime(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 非 非 （（（a*b*c 等于 p）或（z 不是质数。）））
    提升难度：z 选取 21..99 的奇数，减少显见合数；并标记是否被第二子句单独决定。
    """
    abc = a * b * c
    # p 随机接近 abc，避免过于显见
    p = abc if random.random() < 0.5 else abc + random.choice([-2, -1, 1, 2])
    # z 选取不太显然的奇数
    z = _hard_prime_candidate()
    inner_left = (abc == p)
    inner_right = (not is_prime(z))
    inner = inner_left or inner_right
    truth = bool(inner)
    # 若左子句为假且右子句为真，则该条由第二子句单独决定
    decided_by_z = (not inner_left) and inner_right
    text = f"非 非 （（（a*b*c 等于 {p}）或（{z} 不是质数。）））"
    return text, truth, "double_neg_or_prime", 2, {"p": p, "z": z, "decided_by_z": decided_by_z}, "double_neg_or_prime"


def tmpl_xor_membership_prime(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 恰有一个为真： （u 属于 E） 与 （v 为质数）
    """
    if random.random() < 0.5 and len(E) > 0:
        u = random.choice(E)
    else:
        low = min(E) - 5 if E else 0
        high = max(E) + 5 if E else 10
        candidates = [val for val in range(low, high + 1) if val not in E]
        u = random.choice(candidates) if candidates else (low - 1)
    # v 选择非显然的奇数
    v = _hard_prime_candidate()
    truth = ((u in E) != is_prime(v))
    text = f"恰有一个为真： （{u} 属于 E） 与 （{v} 为质数）"
    return text, truth, "xor_set_prime", 2, {"u": u, "v": v}, "xor_membership_prime"


def tmpl_implication(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 如果 （a 加 d 大于 c），则 （r 属于 E）
    """
    d = random.randint(-10, 10)
    if random.random() < 0.5 and len(E) > 0:
        r = random.choice(E)
    else:
        low = min(E) - 5 if E else 0
        high = max(E) + 5 if E else 10
        candidates = [val for val in range(low, high + 1) if val not in E]
        r = random.choice(candidates) if candidates else (low - 1)
    premise = (a + d) > c
    conclusion = (r in E)
    truth = (not premise) or conclusion
    text = f"如果 （a 加 {d} 大于 c），则 （{r} 属于 E）"
    return text, truth, "implication_set", 2, {"d": d, "r": r}, "implication"


def tmpl_not_divisible_or_notin(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 非 （（a 对 d 取余等于 r）或（u 不属于 E。））
    """
    d = random.randint(2, 12)
    real_r = a % d
    if random.random() < 0.5:
        r = real_r
    else:
        choices = [x for x in range(d) if x != real_r]
        r = random.choice(choices) if choices else real_r
    if random.random() < 0.5 and len(E) > 0:
        u = random.choice(E)
    else:
        low = min(E) - 5 if E else 0
        high = max(E) + 5 if E else 10
        candidates = [val for val in range(low, high + 1) if val not in E]
        u = random.choice(candidates) if candidates else (low - 1)
    truth = not (((a % d) == r) or (u not in E))
    text = f"非 （（a 对 {d} 取余等于 {r}）或（{u} 不属于 E。））"
    return text, truth, "mod_notin_neg", 2, {"d": d, "r": r, "u": u}, "not_divisible_or_notin"


# -----------------------------
# 新增高阶复合模板
# -----------------------------
def tmpl_abs_gcd_parity(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 设 d 等于 a 与 b 的差的绝对值，g 为 a 与 c 的最大公因数，则 （d 为偶数且 g 大于 1）或（b 小于 c 且 g 等于 1）
    """
    d = abs(a - b)
    g = gcd(a, c)
    truth = ((d % 2 == 0) and (g > 1)) or ((b < c) and (g == 1))
    text = f"设 d 等于 a 与 b 的差的绝对值，g 为 a 与 c 的最大公因数，则 （d 为偶数且 g 大于 1）或（b 小于 c 且 g 等于 1）"
    return text, truth, "number_theory", 3, {"d": d, "g": g}, "abs_gcd_parity"


def tmpl_max_min_sum_not(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 设 M 为 E 的最大值，m 为 E 的最小值，s 为 E 的元素之和，则 非 （M 加 m 大于 s）
    """
    M = max(E) if E else 0
    m = min(E) if E else 0
    s = sum(E)
    truth = not ((M + m) > s)
    text = "设 M 为 E 的最大值，m 为 E 的最小值，s 为 E 的元素之和，则 非 （M 加 m 大于 s）"
    return text, truth, "set_aggregate", 3, {"M": M, "m": m, "s": s}, "max_min_sum_not"


def tmpl_transform_membership_xor(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 设 T 为由 E 中每个元素加 a 得到的集合，则 恰有一个为真：（c 属于 T） 与 （b 属于 T）
    """
    truth = ((c - a) in E) != ((b - a) in E)
    text = "设 T 为由 E 中每个元素加 a 得到的集合，则 恰有一个为真：（c 属于 T） 与 （b 属于 T）"
    return text, truth, "set_transform", 3, {}, "transform_membership_xor"


def tmpl_mod_mix(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 设 k 为 E 的最大值减最小值，d 为 a 对 k 取余，则 非 （（d 等于 b 对 k 取余）或（c 对 k 取余等于 0））
    """
    M = max(E) if E else 1
    m = min(E) if E else 0
    k = max(1, M - m)
    d = a % k
    truth = not ((d == (b % k)) or ((c % k) == 0))
    text = f"设 k 为 E 的最大值减最小值，d 为 a 对 k 取余，则 非 （（d 等于 b 对 k 取余）或（c 对 k 取余等于 0））"
    return text, truth, "mod_mix", 3, {"k": k, "d": d}, "mod_mix"


def tmpl_biconditional_parity(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 当且仅当： （a 与 b 的奇偶性相同） 与 （E 中偶数的个数为偶数）
    """
    parity_equal = (a % 2 == b % 2)
    even_cnt_even = (sum(1 for x in E if x % 2 == 0) % 2 == 0)
    truth = (parity_equal == even_cnt_even)
    text = "当且仅当： （a 与 b 的奇偶性相同） 与 （E 中偶数的个数为偶数）"
    return text, truth, "biconditional", 3, {}, "biconditional_parity"


def tmpl_prime_count_implication(a: int, b: int, c: int, E: List[int]) -> Tuple[str, bool, str, int, Dict[str, Any], str]:
    """
    模板： 设 q 为 E 中质数的数量，若 q 不少于 t 则 a 加 b 小于等于 c 加 t
    """
    q = sum(1 for x in E if is_prime(x))
    t = random.randint(1, max(1, len(E)))
    premise = q >= t
    conclusion = (a + b) <= (c + t)
    truth = (not premise) or conclusion
    text = f"设 q 为 E 中质数的数量，若 q 不少于 {t} 则 a 加 b 小于等于 c 加 {t}"
    return text, truth, "prime_count_imp", 3, {"q": q, "t": t}, "prime_count_implication"


# -----------------------------
# 统一真值再评估器（用于唯一性和一致性校验）
# -----------------------------
def evaluate_truth(kind: str, params: Dict[str, Any], a: int, b: int, c: int, E: List[int]) -> bool:
    """独立根据 kind 与 params 重新计算陈述真值，确保一致性与唯一性。"""
    if kind == "pyth_and_in":
        x = params["x"]
        return (a * a + b * b == c * c) and (x in E)
    if kind == "triangle_chain":
        return ((a + b) > c) and (a < b < c)
    if kind == "neg_or_membership":
        t = params["t"]; y = params["y"]
        return not (((c - b - a) == t) or (y in E))
    if kind == "double_neg_or_prime":
        p = params["p"]; z = params["z"]
        abc = a * b * c
        return bool(((abc == p) or (not is_prime(z))))
    if kind == "xor_membership_prime":
        u = params["u"]; v = params["v"]
        return ((u in E) != is_prime(v))
    if kind == "implication":
        d = params["d"]; r = params["r"]
        return (not ((a + d) > c)) or (r in E)
    if kind == "not_divisible_or_notin":
        d = params["d"]; r = params["r"]; u = params["u"]
        return not (((a % d) == r) or (u not in E))
    if kind == "abs_gcd_parity":
        d = abs(a - b)
        g = gcd(a, c)
        return ((d % 2 == 0) and (g > 1)) or ((b < c) and (g == 1))
    if kind == "max_min_sum_not":
        M = max(E) if E else 0
        m = min(E) if E else 0
        s = sum(E)
        return not ((M + m) > s)
    if kind == "transform_membership_xor":
        return ((c - a) in E) != ((b - a) in E)
    if kind == "mod_mix":
        M = max(E) if E else 1
        m = min(E) if E else 0
        k = max(1, M - m)
        d = a % k
        return not ((d == (b % k)) or ((c % k) == 0))
    if kind == "biconditional_parity":
        parity_equal = (a % 2 == b % 2)
        even_cnt_even = (sum(1 for x in E if x % 2 == 0) % 2 == 0)
        return (parity_equal == even_cnt_even)
    if kind == "prime_count_implication":
        q = sum(1 for x in E if is_prime(x))
        t = params["t"]
        premise = q >= t
        conclusion = (a + b) <= (c + t)
        return (not premise) or conclusion
    return False


def _pick_templates(k: int) -> List:
    """从模板池中随机选择 k 个模板函数引用。允许重复以扩大组合空间。"""
    pool = [
        tmpl_pyth_and_in,
        tmpl_triangle_chain,
        tmpl_neg_or_membership,
        tmpl_double_neg_or_prime,
        tmpl_xor_membership_prime,
        tmpl_implication,
        tmpl_not_divisible_or_notin,
        tmpl_abs_gcd_parity,
        tmpl_max_min_sum_not,
        tmpl_transform_membership_xor,
        tmpl_mod_mix,
        tmpl_biconditional_parity,
        tmpl_prime_count_implication,
    ]
    return [random.choice(pool) for _ in range(k)]


def _build_abc_e() -> Tuple[int, int, int, List[int]]:
    """随机生成 (a, b, c, E) 并确保 a,b,c 两两不同，E 合理。"""
    a = random.randint(3, 30)
    b = random.randint(4, 35)
    c = random.randint(5, 40)
    tries = 0
    while len({a, b, c}) != 3 and tries < 50:
        a = random.randint(3, 30)
        b = random.randint(4, 35)
        c = random.randint(5, 40)
        tries += 1
    E_size = random.randint(3, 7)
    E_low = random.randint(2, 20)
    E_high = random.randint(E_low + 7, E_low + 25)
    E = gen_unique_list(E_size, E_low, E_high)
    return a, b, c, E


def build_instance(target_count: int = None) -> Dict[str, Any]:
    """
    构造完整题目实例：
    - 随机生成 a,b,c,E
    - 随机选择若干模板生成陈述与真值
    - 验证通过后返回包含展示文本、答案等的字典
    增强：限制“由单子句显见决定”的陈述最多 1 条，提升整体均衡性。
    """
    max_tries = 400
    for _ in range(max_tries):
        a, b, c, E = _build_abc_e()
        if target_count is None:
            opt_num = random.randint(4, 7)
        else:
            opt_num = max(4, min(7, int(target_count)))
        stmts: List[Dict[str, Any]] = []
        tmpl_funcs = _pick_templates(opt_num)

        for f in tmpl_funcs:
            text, truth, cat, comp, params, kind = f(a, b, c, E)
            stmts.append({
                "text": text,
                "truth": bool(truth),
                "category": cat,
                "complexity": comp,
                "params": params,
                "kind": kind
            })

        truths = [s["truth"] for s in stmts]
        true_count = sum(truths)
        cats = {s.get("category", "") for s in stmts}
        complex_cnt = sum(1 for s in stmts if int(s.get("complexity", 1)) >= 2)
        texts = [s["text"] for s in stmts]
        # 显见线索统计：双重否定或质数 模板由第二子句单独决定的计数
        easy_or_cnt = sum(
            1 for s in stmts
            if s.get("kind") == "double_neg_or_prime" and s.get("params", {}).get("decided_by_z", False)
        )

        # 验证一致性：独立重算真值
        consistent = all(
            evaluate_truth(s["kind"], s.get("params", {}), a, b, c, E) == bool(s["truth"]) for s in stmts
        )

        # 通过校验：真值数量，至少两条复杂，类别≥3，文本不重复，a,b,c不同，E唯一，一致性通过，且显见线索上限
        if (1 <= true_count <= opt_num - 1 and
            complex_cnt >= 2 and
            len(cats) >= 3 and
            len(set(texts)) == len(texts) and
            len({a, b, c}) == 3 and
            len(E) == len(set(E)) and
            consistent and
            easy_or_cnt <= 1):

            lines = [f"- {i + 1}. {stmts[i]['text']}" for i in range(opt_num)]
            stmts_block = "\n".join(lines)
            instance = {
                "a": a,
                "b": b,
                "c": c,
                "E": E,
                "opt_num": opt_num,
                "statements": stmts,
                "stmts_block": stmts_block
            }
            return instance

    # 退而求其次的回退实例：保障有效与多样性
    a, b, c, E = _build_abc_e()
    fallback_templates = [
        tmpl_triangle_chain,
        tmpl_abs_gcd_parity,
        tmpl_max_min_sum_not,
        tmpl_transform_membership_xor,
        tmpl_mod_mix,
        tmpl_prime_count_implication,
    ]
    stmts = []
    for f in fallback_templates:
        text, truth, cat, comp, params, kind = f(a, b, c, E)
        stmts.append({"text": text, "truth": bool(truth), "category": cat, "complexity": comp, "params": params, "kind": kind})
    lines = [f"- {i + 1}. {stmts[i]['text']}" for i in range(len(stmts))]
    return {
        "a": a, "b": b, "c": c, "E": E,
        "opt_num": len(stmts),
        "statements": stmts,
        "stmts_block": "\n".join(lines)
    }


def get_answer_codes_from_instance(instance: Dict[str, Any]) -> List[int]:
    """给定实例，返回为真陈述的编号列表（从1开始，升序）。"""
    codes = [i + 1 for i, s in enumerate(instance.get("statements", [])) if bool(s.get("truth", False))]
    return sorted(codes)


def validate_instance(instance: Dict[str, Any]) -> bool:
    """
    验证题目实例：
    - a,b,c 两两不同
    - E 去重
    - 真陈述数量在 [1, n-1]
    - 至少包含两条复杂模板，且模板类别数量>=3
    - 文本不重复
    - 独立评估器重算真值一致
    - 显见线索上限：由双重否定或质数模板的第二子句单独决定的陈述最多 1 条
    该验证为线性复杂度，确保生成过程在限定时间内完成。
    """
    try:
        a = instance["a"]
        b = instance["b"]
        c = instance["c"]
        E = instance["E"]
        stmts = instance["statements"]
        n = instance["opt_num"]
    except Exception:
        return False

    if len({a, b, c}) != 3:
        return False
    if len(E) != len(set(E)):
        return False

    truths = [bool(s.get("truth", False)) for s in stmts]
    true_cnt = sum(truths)
    if not (1 <= true_cnt <= n - 1):
        return False

    complex_cnt = sum(1 for s in stmts if int(s.get("complexity", 1)) >= 2)
    if complex_cnt < 2:
        return False

    cats = {s.get("category", "") for s in stmts}
    if len(cats) < 3:
        return False

    texts = [s.get("text", "") for s in stmts]
    if len(set(texts)) != len(texts):
        return False

    # 独立重算真值一致性校验
    consistent = all(
        evaluate_truth(s.get("kind", ""), s.get("params", {}), a, b, c, E) == bool(s.get("truth", False))
        for s in stmts
    )
    if not consistent:
        return False

    # 显见线索计数限制
    easy_or_cnt = sum(
        1 for s in stmts
        if s.get("kind") == "double_neg_or_prime" and s.get("params", {}).get("decided_by_z", False)
    )
    if easy_or_cnt > 1:
        return False

    return True