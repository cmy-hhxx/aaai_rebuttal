# einsteins_riddle_12.py
import random
from typing import List, Dict, Any, Tuple

# ------------------------------
# 通用随机数函数（供 YAML variables 使用）
# ------------------------------
def rand_int(a: int, b: int) -> int:
    """返回区间[a,b]的随机整数。"""
    return random.randint(a, b)

# ------------------------------
# 通用抽样与组合生成函数（供 YAML variables 使用）
# ------------------------------
def pick_one(pool: List[str]) -> str:
    """从列表中随机选择一个元素。"""
    if not pool:
        raise ValueError("pool is empty")
    return random.choice(pool)

def pick_one_except(pool: List[str], exclude: str) -> str:
    """从列表中选择一个与exclude不同的元素。若exclude不在pool则等价于随机选择。"""
    if not pool:
        raise ValueError("pool is empty")
    candidates = [x for x in pool if x != exclude]
    if not candidates:
        raise ValueError("no candidate available different from exclude")
    return random.choice(candidates)

def pick_k(pool: List[str], k: int) -> List[str]:
    """从列表中无重复随机选择k个元素。"""
    if k > len(pool):
        raise ValueError("k larger than pool size")
    return random.sample(pool, k)

def pick_k_with_must(pool: List[str], k: int, must_include: str) -> List[str]:
    """从列表中无重复随机选择k个元素，且必须包含指定元素。"""
    if must_include not in pool:
        raise ValueError("must_include not in pool")
    if k > len(pool):
        raise ValueError("k larger than pool size")
    base = [must_include]
    candidates = [x for x in pool if x != must_include]
    need = k - 1
    if need > len(candidates):
        raise ValueError("not enough candidates for pick_k_with_must")
    base.extend(random.sample(candidates, need))
    random.shuffle(base)
    return base

def pick_distinct_pair(items: List[str]) -> List[str]:
    """从列表中随机选择两个不同元素并返回[elem1, elem2]。"""
    if len(items) < 2:
        raise ValueError("items too small for a pair")
    a, b = random.sample(items, 2)
    return [a, b]

def gen_partial_bijection(a_list: List[str], b_list: List[str], m: int) -> List[List[str]]:
    """
    在a_list与b_list之间生成m对一一对应的配对，输出为[[a1,b1], [a2,b2], ...]。
    """
    if m < 1 or m > min(len(a_list), len(b_list)):
        raise ValueError("invalid m for partial bijection")
    a_sel = random.sample(a_list, m)
    b_sel = random.sample(b_list, m)
    random.shuffle(b_sel)
    pairs = []
    for i in range(m):
        pairs.append([a_sel[i], b_sel[i]])
    return pairs

def gen_partial_bijection_with_pair(a_list: List[str], b_list: List[str], m: int,
                                    must_a: str, must_b: str) -> List[List[str]]:
    """
    生成m对一一对应，且必须包含[must_a, must_b]这一对，其他对在剩余元素中随机生成。
    """
    if m < 1 or m > min(len(a_list), len(b_list)):
        raise ValueError("invalid m for partial bijection")
    if must_a not in a_list or must_b not in b_list:
        raise ValueError("must pair elements not in lists")
    pairs = [[must_a, must_b]]
    remaining_m = m - 1
    a_candidates = [x for x in a_list if x != must_a]
    b_candidates = [y for y in b_list if y != must_b]
    if remaining_m > min(len(a_candidates), len(b_candidates)):
        raise ValueError("not enough candidates to complete pairs")
    a_sel = random.sample(a_candidates, remaining_m)
    b_sel = random.sample(b_candidates, remaining_m)
    random.shuffle(b_sel)
    for i in range(remaining_m):
        pairs.append([a_sel[i], b_sel[i]])
    random.shuffle(pairs)
    return pairs

def gen_partial_bijection_with_pair_anchor(a_list: List[str], b_list: List[str], m: int,
                                           must_a: str, must_b: str,
                                           anchor_b: str, anchor_a: str) -> List[List[str]]:
    """
    生成m对一一对应，必须包含[must_a, must_b]这一对；
    同时若出现anchor_b（如middle_color），则必须与anchor_a（如middle_payment）配对，
    从源头避免将非中位支付映射到中位颜色导致的Distinct冲突。
    """
    if m < 1 or m > min(len(a_list), len(b_list)):
        raise ValueError("invalid m for partial bijection")
    if must_a not in a_list or must_b not in b_list:
        raise ValueError("must pair elements not in lists")

    pairs: List[List[str]] = [[must_a, must_b]]
    remaining_m = m - 1

    a_can = [x for x in a_list if x != must_a]
    b_can = [y for y in b_list if y != must_b]

    if remaining_m > min(len(a_can), len(b_can)):
        raise ValueError("not enough candidates to complete pairs")

    # 若还有容量，优先加入锚点对（anchor_a, anchor_b），确保中位-中位一致。
    if remaining_m >= 1 and (anchor_a in a_can) and (anchor_b in b_can):
        pairs.append([anchor_a, anchor_b])
        remaining_m -= 1
        a_can = [x for x in a_can if x != anchor_a]
        b_can = [y for y in b_can if y != anchor_b]

    # 剩余对随机生成，避免产生anchor_b与非anchor_a的配对
    attempts = 0
    while remaining_m > 0 and attempts < 1000:
        a_sel = random.sample(a_can, remaining_m)
        b_sel = random.sample(b_can, remaining_m)
        ok = True
        for bb in b_sel:
            if bb == anchor_b and (anchor_a not in a_sel):
                ok = False
                break
        if ok:
            # 打乱并配对
            random.shuffle(b_sel)
            for i in range(remaining_m):
                pairs.append([a_sel[i], b_sel[i]])
            remaining_m = 0
            break
        attempts += 1

    if remaining_m != 0:
        # 保底：强制避开anchor_b与非anchor_a的组合
        # 构造所有候选对并贪心挑选
        candidates = [(a, b) for a in a_can for b in b_can if not (b == anchor_b and a != anchor_a)]
        if len(candidates) < remaining_m:
            raise ValueError("unable to construct anchored bijection")
        random.shuffle(candidates)
        used_a, used_b = set(), set()
        for a, b in candidates:
            if a in used_a or b in used_b:
                continue
            pairs.append([a, b])
            used_a.add(a)
            used_b.add(b)
            remaining_m -= 1
            if remaining_m == 0:
                break
        if remaining_m != 0:
            raise ValueError("failed to finalize anchored bijection")

    random.shuffle(pairs)
    return pairs

def pick_pairs_distinct(a_list: List[str], b_list: List[str], count: int) -> List[List[str]]:
    """
    从a_list与b_list生成若干对[a,b]，保证a各不相同且b各不相同。
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    if count > min(len(a_list), len(b_list)):
        raise ValueError("count too large for distinct pairing")
    a_sel = random.sample(a_list, count)
    b_sel = random.sample(b_list, count)
    random.shuffle(b_sel)
    return [[a_sel[i], b_sel[i]] for i in range(count)]

def pick_pairs_distinct_avoid_pairs(a_list: List[str], b_list: List[str], count: int,
                                    avoid_pairs: List[List[str]]) -> List[List[str]]:
    """
    生成若干对[a,b]，保证两侧元素互异，且避开avoid_pairs中的组合。
    适用于避开必然矛盾（如[leftmost_product, middle_color]或[leftmost_product, middle_payment]）。
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    avoid = {(p[0], p[1]) for p in (avoid_pairs or []) if isinstance(p, list) and len(p) == 2}

    attempts = 0
    while attempts < 1000:
        candidates = [(a, b) for a in a_list for b in b_list if (a, b) not in avoid]
        random.shuffle(candidates)
        picked: List[Tuple[str, str]] = []
        used_a, used_b = set(), set()
        for a, b in candidates:
            if a in used_a or b in used_b:
                continue
            picked.append((a, b))
            used_a.add(a)
            used_b.add(b)
            if len(picked) == count:
                break
        if len(picked) == count:
            return [[a, b] for a, b in picked]
        attempts += 1

    raise ValueError("unable to pick distinct pairs avoiding conflicts")

# ------------------------------
# 多对排除与严格不共享支付维度（已在YAML使用）
# ------------------------------
def pick_pair_avoid_pairs_as_list(a_list: List[str], b_list: List[str], exclude_pairs: List[List[str]]) -> List[List[str]]:
    """
    从a_list与b_list选取一对[a,b]并返回[[a,b]]，要求该对不属于exclude_pairs集合。
    """
    excludes = { (p[0], p[1]) for p in exclude_pairs or [] if isinstance(p, list) and len(p) == 2 }
    attempts = 0
    while attempts < 1000:
        a = random.choice(a_list)
        b = random.choice(b_list)
        if (a, b) not in excludes:
            return [[a, b]]
        attempts += 1
    # 保底：尽量避开已用元素
    a_choices = [x for x in a_list if all(x != ep[0] for ep in exclude_pairs)] or a_list
    b_choices = [y for y in b_list if all(y != ep[1] for ep in exclude_pairs)] or b_list
    a = random.choice(a_choices)
    b = random.choice(b_choices)
    return [[a, b]]

def pick_pair_distinct_from(a_list: List[str], b_list: List[str], exclude_pair: List[str]) -> List[str]:
    """
    从a_list与b_list选取一对[a,b]，要求不等于exclude_pair（即不同时满足a==exclude_pair[0]且b==exclude_pair[1]）。
    """
    if len(a_list) == 0 or len(b_list) == 0:
        raise ValueError("empty source lists")
    attempts = 0
    while attempts < 1000:
        a = random.choice(a_list)
        b = random.choice(b_list)
        if not (exclude_pair and len(exclude_pair) == 2 and a == exclude_pair[0] and b == exclude_pair[1]):
            return [a, b]
        attempts += 1
    # 保底策略：若循环未找到，强制更换其中一个维度
    a_choices = [x for x in a_list if x != (exclude_pair[0] if exclude_pair else None)] or a_list
    b_choices = [y for y in b_list if y != (exclude_pair[1] if exclude_pair else None)] or b_list
    a = random.choice(a_choices)
    b = random.choice(b_choices)
    return [a, b]

def pick_pair_disjoint_from_pair(a_list: List[str], b_list: List[str], exclude_pair: List[str]) -> List[str]:
    """
    从a_list与b_list选取一对[a,b]，要求 a != exclude_pair[0] 且 b != exclude_pair[1]。
    用于避免两个商品绑定到同一个支付方式，降低位置冲突风险。
    """
    if not exclude_pair or len(exclude_pair) != 2:
        return pick_pair_distinct_from(a_list, b_list, exclude_pair or [])
    attempts = 0
    while attempts < 1000:
        a = random.choice(a_list)
        b = random.choice(b_list)
        if a != exclude_pair[0] and b != exclude_pair[1]:
            return [a, b]
        attempts += 1
    # 保底：强制替换
    a_choices = [x for x in a_list if x != exclude_pair[0]] or a_list
    b_choices = [y for y in b_list if y != exclude_pair[1]] or b_list
    a = random.choice(a_choices)
    b = random.choice(b_choices)
    return [a, b]

# ------------------------------
# 解读模型用函数（供查询与一致性检查用）
# ------------------------------
def _eval_pos(model, expr):
    """将Z3 Int表达式求值为Python int。"""
    v = model.evaluate(expr, model_completion=True)
    try:
        return int(v.as_long())
    except Exception:
        try:
            return int(str(v))
        except Exception as e:
            raise RuntimeError(f"Failed to evaluate position: {v}") from e

def who_has_gufa(products: List[str],
                 slogans: List[str],
                 pos_product: Dict[str, Any],
                 pos_slogan: Dict[str, Any],
                 _model,
                 target_slogan: str) -> str:
    """
    根据模型与目标口号，返回该口号所在摊位对应的商品名称。
    """
    if target_slogan not in slogans:
        raise ValueError("target_slogan not in slogans")
    gufa_pos = _eval_pos(_model, pos_slogan[target_slogan])
    for p in products:
        if _eval_pos(_model, pos_product[p]) == gufa_pos:
            return p
    raise ValueError("No product found at target slogan position")

def unique_gufa_consistent(products: List[str],
                           slogans: List[str],
                           pos_product: Dict[str, Any],
                           pos_slogan: Dict[str, Any],
                           _solutions: List[Any],
                           target_slogan: str) -> bool:
    """
    检查所有解中目标口号对应的商品是否一致。
    """
    found = None
    for m in _solutions:
        ans = who_has_gufa(products, slogans, pos_product, pos_slogan, m, target_slogan)
        if found is None:
            found = ans
        elif ans != found:
            return False
    return True