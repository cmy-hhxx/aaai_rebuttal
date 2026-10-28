# boolean_expressions_0.py
# 升级版：混合算术、给定事实与自指元陈述，内置唯一解验证；标签与文本全面中文化；随机一致性修复
from typing import List, Dict, Tuple, Callable
import random
import time

# -------------------------
# 自定义：生成标签 A,B,C,...
# -------------------------
def make_labels(count: int) -> List[str]:
    """
    生成 ['A','B','C', ...]，长度为 count，count 不超过 26 为宜
    """
    return [chr(ord('A') + i) for i in range(count)]

# -------------------------
# 工具：事实名与真值生成
# -------------------------
def _gen_facts(rng: random.Random) -> Tuple[List[str], Dict[str, bool]]:
    """
    随机生成事实名称与真值：
    - 事实数量：2 或 3
    - 名称风格：命题甲/断言甲 等
    返回：fact_names, fact_truths
    """
    fact_count = rng.choice([2, 3])
    style = rng.choice(["命题", "断言"])
    base = ["甲", "乙", "丙"]
    fact_names = [f"{style}{base[i]}" for i in range(fact_count)]
    fact_truths = {name: rng.choice([True, False]) for name in fact_names}
    return fact_names, fact_truths

def _facts_text(fact_names: List[str], fact_truths: Dict[str, bool]) -> str:
    """
    生成事实文本：已知 命题甲为真，命题乙为假，命题丙为真。
    """
    parts = []
    for name in fact_names:
        parts.append(f"{name}为{'真' if fact_truths[name] else '假'}")
    return "已知 " + "，".join(parts) + "。"

# -------------------------
# 工具：规则说明文本（加入真数限制公开条款）
# -------------------------
def _rule_text(rng: random.Random) -> str:
    """
    随机生成规则说明文本（纯中文表达，不含唯一性等内部信息），包含自洽语义、真数限制与答案格式。
    """
    variants = [
        "规则说明：与表示逻辑与，或表示逻辑或，非表示逻辑非；等于与不等于表示数值相等与不相等；使用大于与小于进行比较；零为假，非零为真；括号中的算式先计算再判断真值。若选项之间出现相互引用，则以整体自洽为准，即所有选项的陈述与其自身真假需同时成立。另行约定：真选项数量至少为1且不是全部选项。答案需按标签升序并以逗号分隔，示例 A,B；若仅有一个则输出 A。",
        "题目环境：采用与、或、非三种逻辑操作；数值关系使用等于、不等于、大于、小于；非零视为真，零视为假；遇到括号先计算再判断。若选项之间互相约束，请寻找使所有陈述与各自真假一致的自洽配置。另有规定：真选项数量至少为1且不是全部选项。答案格式为按标签升序输出所有为真的选项，逗号分隔，示例 A,B；若只有一个则输出 A。",
        "约定：与表示逻辑与，或表示逻辑或，非表示逻辑非；比较运算包括等于、不等于、大于、小于；当数值不等于零时视为真，等于零视为假；括号内先算术后判断。若出现自指或互指语句，以所有选项同时自洽为准。并规定：真选项数量至少为1且不是全部选项。答案按标签升序并用逗号分隔，示例 A,B；若仅一项为真则直接输出该标签，例如 A。"
    ]
    rng.shuffle(variants)
    return variants[0]

# -------------------------
# 表达式模板实现（基础选项）：返回 (文本, 真值)
# -------------------------

def _tpl_double_neg_or_eq_neq(rng: random.Random) -> Tuple[str, bool]:
    u = rng.randint(2, 9)
    v = rng.randint(2, 5)
    w = rng.randint(2, 5)
    t = rng.randint(2, 7)
    rhs_neg = (-2) * (-v) * (-w) * t  # 负数
    left_neg = -(rng.randint(2, 9) * 10 + rng.randint(1, 9))
    n = rng.randint(2, 9)
    m = rng.randint(1, n - 1)
    h = rng.randint(8, 30)
    right_pos = h - (m / n)  # 正数
    text = f"非 非 (((1 - (-{u} / -{u})) 等于 ({rhs_neg})) 或 (({left_neg}) 不等于 ({right_pos})))"
    eq_part = (1 - ((-u) / (-u))) == rhs_neg  # 0 == 负数 -> False
    neq_part = (left_neg != right_pos)        # True
    value = True if (eq_part or neq_part) else False
    return text, value

def _pick_one_fact(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    name = rng.choice(fact_names)
    return name, fact_truths[name]

def _pick_two_distinct_facts(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[Tuple[str, bool], Tuple[str, bool]]:
    names = fact_names
    if len(names) == 1:
        n = names[0]
        return (n, fact_truths[n]), (n, fact_truths[n])
    a, b = rng.sample(names, 2)
    return (a, fact_truths[a]), (b, fact_truths[b])

def _tpl_and_numeric_nonzero_and_fact(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    x = rng.randint(2, 12)
    y = rng.randint(3, 15)
    u = rng.randint(2, 12)
    v = rng.randint(3, 15)
    left_num = (x * y + 0 * 0) * (-(u) * v)  # 非零
    fname, fval = _pick_one_fact(rng, fact_names, fact_truths)
    text = f"((( {x} * {y} + 0 * 0) 与 (-{u} * {v})) 与 {fname})"
    left_bool = (left_num != 0)
    value = (left_bool and fval)
    return text, value

def _tpl_not_or_eq_not_fact(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    p = rng.randint(2, 40)
    q = rng.randint(1, 9)
    fname, fval = _pick_one_fact(rng, fact_names, fact_truths)
    text = f"非 (({p} + {q} 等于 {p}) 或 非 {fname})"
    left_eq = ((p + q) == p)  # False
    inner = (left_eq or (not fval))
    value = (not inner)
    return text, value

def _tpl_true_via_order_and_zero(rng: random.Random) -> Tuple[str, bool]:
    a = rng.randint(2, 12)
    b = rng.randint(2, 12)
    r = rng.randint(1, 9)
    s = rng.randint(5, 20)
    text = f"(({a} * {b} 小于 {a} * {b} + {r}) 与 ({s} - {s} 等于 0))"
    value = ((a * b) < (a * b + r)) and ((s - s) == 0)
    return text, value

def _tpl_not_and_eqs_diff(rng: random.Random) -> Tuple[str, bool]:
    a = rng.randint(2, 30)
    b = rng.randint(5, 50)
    c = b + rng.randint(1, 7)
    text = f"非 (({a} - {a} 等于 0) 与 ({b} - {c} 等于 0))"
    value = not ((a - a == 0) and (b - c == 0))
    return text, value

def _tpl_double_neg_true(rng: random.Random) -> Tuple[str, bool]:
    text = "非 非 ((1 不等于 0) 或 (2 不等于 0))"
    value = True
    return text, value

def _tpl_fact_and_not_fact(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    if len(fact_names) >= 2:
        (n1, v1), (n2, v2) = _pick_two_distinct_facts(rng, fact_names, fact_truths)
        text = f"({n1} 与 非 {n2})"
        value = v1 and (not v2)
        return text, value
    else:
        n1, v1 = _pick_one_fact(rng, fact_names, fact_truths)
        text = f"({n1} 与 (1 不等于 0))"
        value = v1 and True
        return text, value

def _tpl_not_fact_and_zero_eq(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    s = rng.randint(5, 20)
    n1, v1 = _pick_one_fact(rng, fact_names, fact_truths)
    text = f"非 ({n1} 与 ({s} - {s} 等于 0))"
    value = not (v1 and ((s - s) == 0))
    return text, value

def _tpl_nums_and_fact_or(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    u = rng.randint(2, 12)
    v = rng.randint(2, 12)
    if len(fact_names) >= 2:
        (n1, v1), (n2, v2) = _pick_two_distinct_facts(rng, fact_names, fact_truths)
        text = f"((( {u} 不等于 0) 与 ({v} 不等于 0)) 与 ({n1} 或 {n2}))"
        left = (u != 0) and (v != 0)
        value = left and (v1 or v2)
    else:
        n1, v1 = _pick_one_fact(rng, fact_names, fact_truths)
        text = f"((( {u} 不等于 0) 与 ({v} 不等于 0)) 与 {n1})"
        value = ((u != 0) and (v != 0)) and v1
    return text, value

def _tpl_order_or_lt_and_fact(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    a = rng.randint(2, 12)
    b = rng.randint(2, 12)
    r = rng.randint(1, 9)
    k = rng.randint(3, 30)
    n1, v1 = _pick_one_fact(rng, fact_names, fact_truths)
    text = f"((({a} * {b} 大于 {a} * {b} - {r}) 或 ({k} 小于 {k} + 1)) 与 {n1})"
    num_part = ((a * b) > (a * b - r)) or (k < k + 1)
    value = num_part and v1
    return text, value

def _tpl_not_or_false_false(rng: random.Random) -> Tuple[str, bool]:
    a = rng.randint(2, 30)
    b = rng.randint(2, 30)
    text = f"非 ((({a} - {a} 等于 1)) 或 (({b} - {b} 等于 2)))"
    value = not (((a - a) == 1) or ((b - b) == 2))
    return text, value

def _tpl_eq_and_double_not_fact(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    p = rng.randint(2, 40)
    n1, v1 = _pick_one_fact(rng, fact_names, fact_truths)
    text = f"(({p} - {p} 等于 0) 与 非 非 {n1})"
    value = ((p - p) == 0) and (not (not v1))
    return text, value

def _tpl_not_and_notfacts(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    if len(fact_names) >= 2:
        (n1, v1), (n2, v2) = _pick_two_distinct_facts(rng, fact_names, fact_truths)
        text = f"非 ((非 {n1}) 与 (非 {n2}))"
        value = not ((not v1) and (not v2))
        return text, value
    else:
        n1, v1 = _pick_one_fact(rng, fact_names, fact_truths)
        text = f"非 (非 {n1})"
        value = not (not v1)
        return text, value

def _tpl_three_facts_mix(rng: random.Random, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[str, bool]:
    if len(fact_names) >= 3:
        a, b, c = rng.sample(fact_names, 3)
        va, vb, vc = fact_truths[a], fact_truths[b], fact_truths[c]
        text = f"(({a} 与 {b}) 或 非 {c})"
        value = (va and vb) or (not vc)
    elif len(fact_names) == 2:
        a, b = fact_names
        va, vb = fact_truths[a], fact_truths[b]
        text = f"({a} 或 非 {b})"
        value = va or (not vb)
    else:
        n1, v1 = _pick_one_fact(rng, fact_names, fact_truths)
        text = f"({n1} 或 (1 不等于 0))"
        value = v1 or True
    return text, value

def _pick_templates(rng: random.Random, k: int, fact_names: List[str], fact_truths: Dict[str, bool]) -> Tuple[List[str], List[bool]]:
    pool = []
    pool.append(lambda: _tpl_double_neg_or_eq_neq(rng))
    pool.append(lambda: _tpl_and_numeric_nonzero_and_fact(rng, fact_names, fact_truths))
    pool.append(lambda: _tpl_not_or_eq_not_fact(rng, fact_names, fact_truths))
    pool.append(lambda: _tpl_true_via_order_and_zero(rng))
    pool.append(lambda: _tpl_not_and_eqs_diff(rng))
    pool.append(lambda: _tpl_double_neg_true(rng))
    pool.append(lambda: _tpl_fact_and_not_fact(rng, fact_names, fact_truths))
    pool.append(lambda: _tpl_not_fact_and_zero_eq(rng, fact_names, fact_truths))
    pool.append(lambda: _tpl_nums_and_fact_or(rng, fact_names, fact_truths))
    pool.append(lambda: _tpl_order_or_lt_and_fact(rng, fact_names, fact_truths))
    pool.append(lambda: _tpl_not_or_false_false(rng))
    pool.append(lambda: _tpl_eq_and_double_not_fact(rng, fact_names, fact_truths))
    pool.append(lambda: _tpl_not_and_notfacts(rng, fact_names, fact_truths))
    pool.append(lambda: _tpl_three_facts_mix(rng, fact_names, fact_truths))
    rng.shuffle(pool)
    chosen = pool[:k]
    texts, vals = [], []
    for gen in chosen:
        t, v = gen()
        texts.append(t)
        vals.append(v)
    return texts, vals

# -------------------------
# 元陈述模板（基于选项间关系）
# 返回 (文本, evaluator)，evaluator: Callable[[List[bool]], bool]
# -------------------------
def _meta_count_eq(k: int) -> Tuple[str, Callable[[List[bool]], bool]]:
    text = f"恰有 {k} 个选项为真"
    return text, lambda B: sum(1 for x in B if x) == k

def _meta_parity(parity: str) -> Tuple[str, Callable[[List[bool]], bool]]:
    if parity == "odd":
        text = "真选项数量为奇数"
        return text, lambda B: (sum(1 for x in B if x) % 2) == 1
    else:
        text = "真选项数量为偶数"
        return text, lambda B: (sum(1 for x in B if x) % 2) == 0

def _meta_same(labels: List[str], i: int, j: int) -> Tuple[str, Callable[[List[bool]], bool]]:
    text = f"选项 {labels[i]} 与 选项 {labels[j]} 的真假相同"
    return text, lambda B: B[i] == B[j]

def _meta_subset_exact(labels: List[str], idxs: List[int], t: int) -> Tuple[str, Callable[[List[bool]], bool]]:
    subset_names = ",".join(labels[i] for i in idxs)
    text = f"在 {subset_names} 中恰有 {t} 项为真"
    return text, lambda B: sum(1 for i in idxs if B[i]) == t

def _meta_subset_atmost_one(labels: List[str], idxs: List[int]) -> Tuple[str, Callable[[List[bool]], bool]]:
    subset_names = ",".join(labels[i] for i in idxs)
    text = f"在 {subset_names} 中至多一项为真"
    return text, lambda B: sum(1 for i in idxs if B[i]) <= 1

def _meta_implies(labels: List[str], p: int, q: int) -> Tuple[str, Callable[[List[bool]], bool]]:
    text = f"若选项 {labels[p]} 为真则选项 {labels[q]} 为假"
    return text, lambda B: (not B[p]) or (not B[q])

def _meta_iff_not(labels: List[str], i: int, z: int) -> Tuple[str, Callable[[List[bool]], bool]]:
    # 本项为真 当且仅当 Z 为假（含自指）
    text = f"本选项为真当且仅当 选项 {labels[z]} 为假"
    return text, lambda B: B[i] == (not B[z])

def _meta_only_if_all(labels: List[str], i: int, idxs: List[int]) -> Tuple[str, Callable[[List[bool]], bool]]:
    # 只有当 子集全真 时 本选项才为真：B[i] => all(B[idxs])
    subset_names = ",".join(labels[j] for j in idxs)
    text = f"只有当 {subset_names} 同时为真时本选项才为真"
    return text, lambda B: (not B[i]) or all(B[j] for j in idxs)

# -------------------------
# 主函数：构建实例（带唯一性验证）
# -------------------------
def function_2(labels: List[str], seed: int) -> Dict[str, object]:
    """
    构建一个题目实例：
    - 随机生成事实与基础算术陈述
    - 随机组合若干元陈述（选项之间的关系）
    - 穷举所有真假配置，寻找固定点（自洽）且满足 1 <= 真数 < n
    - 保证唯一解，失败则重采样
    返回：
      {
        'rule_text': str,
        'options_block': 'A. 文本\\nB. 文本\\n...',
        'answer': 'A,B',
        'answer_labels': ['A','B'],
        'true_count': 2,
        'facts_text': str,
        'truths_map': {'A': True, 'B': False, ...},
        'unique': True
      }
    """
    t_start = time.time()
    rng = random.Random(seed)
    n = len(labels)
    # 生成事实与规则说明
    fact_names, fact_truths = _gen_facts(rng)
    facts_text = _facts_text(fact_names, fact_truths)
    rule_text = _rule_text(rng)

    # 多次尝试，直至获得唯一固定点
    max_attempts = 120
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        # 基础选项数：至少2个
        base_count = rng.randint(2, max(2, min(3, n - 2)))
        meta_count = n - base_count

        # 准备基础表达式池并抽取
        base_texts_pool, base_vals_pool = _pick_templates(rng, max(n, 8), fact_names, fact_truths)
        # 从池中抽 base_count 个
        idx_pool = list(range(len(base_texts_pool)))
        rng.shuffle(idx_pool)
        chosen_idx = idx_pool[:base_count]
        base_texts = [base_texts_pool[i] for i in chosen_idx]
        base_vals = [base_vals_pool[i] for i in chosen_idx]

        # 选项骨架：先放基础，再放元陈述（随后洗牌）
        option_texts: List[str] = []
        evaluators: List[Callable[[List[bool]], bool]] = []

        # 基础选项：断言即固定真值
        for i in range(base_count):
            t = base_texts[i]
            v = base_vals[i]
            option_texts.append(t)
            evaluators.append(lambda B, vv=v: vv)

        # 元陈述构造
        meta_specs: List[Tuple[str, Callable[[List[bool]], bool]]] = []
        # 候选模板若干
        # 1. 恰有k项为真
        if meta_count > 0:
            k = rng.randint(1, max(1, n - 1))
            meta_specs.append(_meta_count_eq(k))
        # 2. 奇偶性
        if meta_count > 0:
            parity = rng.choice(["odd", "even"])
            meta_specs.append(_meta_parity(parity))
        # 3. 两两相同
        if meta_count > 0 and n >= 4:
            i1, i2 = rng.sample(range(n), 2)
            meta_specs.append(_meta_same(labels, i1, i2))
        # 4. 子集恰有t项为真
        if meta_count > 0:
            msize = rng.randint(2, max(2, min(4, n)))
            idxs = rng.sample(range(n), msize)
            tval = rng.randint(0, msize)
            meta_specs.append(_meta_subset_exact(labels, idxs, tval))
        # 5. 子集中至多一真
        if meta_count > 0:
            msize2 = rng.randint(2, max(2, min(4, n)))
            idxs2 = rng.sample(range(n), msize2)
            meta_specs.append(_meta_subset_atmost_one(labels, idxs2))
        # 6. 蕴含
        if meta_count > 0:
            p, q = rng.sample(range(n), 2)
            meta_specs.append(_meta_implies(labels, p, q))
        # 7. 本项 iff Z 为假（自指）
        if meta_count > 0:
            z = rng.randrange(n)
            meta_specs.append(("__IFF_NOT__", z))  # 占位，后续绑定索引
        # 8. 只有当 子集全真 时 本项才为真（自指）
        if meta_count > 0:
            msize3 = rng.randint(2, max(2, min(3, n)))
            idxs3 = rng.sample(range(n), msize3)
            meta_specs.append(("__ONLY_IF_ALL__", idxs3))  # 占位

        rng.shuffle(meta_specs)
        meta_specs = meta_specs[:meta_count]

        # 先放元文本与评估器的占位
        for spec in meta_specs:
            if isinstance(spec, tuple) and isinstance(spec[0], str) and spec[0] == "__IFF_NOT__":
                z = spec[1]
                option_texts.append(f"本选项为真当且仅当 选项 {labels[z]} 为假")
                evaluators.append(None)  # 稍后回填
            elif isinstance(spec, tuple) and isinstance(spec[0], str) and spec[0] == "__ONLY_IF_ALL__":
                idxs3 = spec[1]
                subset_names = ",".join(labels[j] for j in idxs3)
                option_texts.append(f"只有当 {subset_names} 同时为真时本选项才为真")
                evaluators.append(None)  # 稍后回填
            else:
                text, ev = spec  # 普通元陈述
                option_texts.append(text)
                evaluators.append(ev)

        # 如果基础与元陈述的顺序太集中，整体洗牌以提升迷惑度
        paired = list(zip(option_texts, evaluators))
        rng.shuffle(paired)
        option_texts = [t for t, _ in paired]
        evaluators = [e for _, e in paired]

        # 回填自指类评估器：需要当前索引
        for i in range(n):
            if evaluators[i] is None:
                # 检测是哪种自指
                t = option_texts[i]
                if t.startswith("本选项为真当且仅当 选项 "):
                    # 提取 Z
                    zlab = t.split("当且仅当 选项 ")[1].split(" 为假")[0].strip()
                    z = labels.index(zlab)
                    evaluators[i] = (lambda ii, zz: (lambda B: B[ii] == (not B[zz])))(i, z)
                elif t.startswith("只有当 "):
                    # 提取集合
                    inside = t[len("只有当 "):].split(" 同时为真时本选项才为真")[0]
                    parts = [p.strip() for p in inside.split(",")]
                    idxs3 = [labels.index(p) for p in parts]
                    evaluators[i] = (lambda ii, lst: (lambda B: (not B[ii]) or all(B[j] for j in lst)))(i, idxs3)
                else:
                    evaluators[i] = lambda B: True

        # 穷举固定点：
        solutions = []
        for mask in range(1 << n):
            B = [(mask >> i) & 1 == 1 for i in range(n)]
            tc = sum(1 for x in B if x)
            if not (1 <= tc < n):
                continue
            try_vals = [ev(B) for ev in evaluators]
            if all(B[i] == try_vals[i] for i in range(n)):
                solutions.append(B)
                if len(solutions) > 1:
                    break
        if len(solutions) == 1:
            B = solutions[0]
            truths_map: Dict[str, bool] = {lab: B[i] for i, lab in enumerate(labels)}
            lines: List[str] = [f"{lab}. {option_texts[i]}" for i, lab in enumerate(labels)]
            options_block = "\n".join(lines)
            answer_labels = [lab for lab in labels if truths_map.get(lab, False)]
            answer = ",".join(answer_labels)
            true_count = len(answer_labels)
            return {
                "rule_text": rule_text,
                "options_block": options_block,
                "answer": answer,
                "answer_labels": answer_labels,
                "true_count": true_count,
                "facts_text": facts_text,
                "truths_map": truths_map,
                "unique": True
            }
        if time.time() - t_start > 150.0:
            break

    # 若失败，抛出异常以便上层框架丢弃并重试
    raise ValueError("未能在限定尝试内构造唯一自洽题目，请重试")

def function_1(instance: Dict[str, object]) -> str:
    """
    返回标准答案字符串（按标签升序、逗号分隔）
    """
    return instance.get("answer", "")