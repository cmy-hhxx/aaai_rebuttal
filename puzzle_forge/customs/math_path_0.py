import random
import math

def _eval_block(c, d, e, f, K, M, g, h):
    """
    计算链式块 ((((c % d) * f) % e) * K % M) % g % h 的值；
    要求 d,e,g,h,M 均不小于 2，否则返回 None。
    """
    if d < 2 or e < 2 or g < 2 or h < 2 or M < 2:
        return None
    t1 = c % d
    t2 = t1 * f
    t3 = t2 % e
    t4 = t3 * K
    t5 = t4 % M
    t6 = t5 % g
    t7 = t6 % h
    return t7

def _make_expr(a, b, c, d, e, f, K, M, g, h, target):
    """
    统一括号与空格风格（与题面一致）：
    a - b + ((((c % d) * f) % e) * K % M) % g % h = target
    """
    return f"{a} - {b} + (((( {c} % {d}) * {f}) % {e}) * {K} % {M}) % {g} % {h} = {target}"

def _ranges_by_difficulty(diff_level: int):
    """
    难度控制：
      - 调节 K、M、target 范围；
      - 控制 a,b 是否允许为 0；
      - 防退化：d,e,g,h,M 均从 {2..9} 取值；
      - t8 需避开过小值（提升信息量）。
    """
    if diff_level == 1:  # easy
        return dict(K_range=(3, 9), M_range=(3, 9), target_range=(6, 20), forbid_zero_ab=False, t8_forbidden={0})
    if diff_level == 2:  # medium
        return dict(K_range=(4, 12), M_range=(4, 12), target_range=(7, 24), forbid_zero_ab=False, t8_forbidden={0, 1})
    # hard
    return dict(K_range=(5, 19), M_range=(5, 19), target_range=(8, 28), forbid_zero_ab=True, t8_forbidden={0, 1, 2})

def _unique_pairs_for_D(D: int, used: set, forbid_zero_ab: bool):
    """
    枚举满足 a-b=D 的 (a,b)，要求：
      - a,b ∈ {0..9}；
      - a != b；
      - a,b 均不在 used；
      - 若 forbid_zero_ab 为 True，则 a,b 不得为 0。
    返回列表 pairs。
    """
    pairs = []
    for b in range(10):
        a = b + D
        if 0 <= a <= 9 and a != b and a not in used and b not in used:
            if forbid_zero_ab and (a == 0 or b == 0):
                continue
            pairs.append((a, b))
    return pairs

def count_ab(K, M, c, d, e, f, g, h, target):
    """
    独立重算 (a,b) 解的数量（用于 YAML 层冗余校验）。
    """
    t8 = _eval_block(c, d, e, f, K, M, g, h)
    if t8 is None:
        return 0
    used = {c, d, e, f, g, h}
    cnt = 0
    for b in range(10):
        for a in range(10):
            if a == b: 
                continue
            if a in used or b in used:
                continue
            if a - b + t8 == target:
                cnt += 1
                if cnt > 1:
                    return cnt
    return cnt

def gen_instance(seed=None, diff_level=1):
    """
    生成满足题面且“唯一 (a,b)”的实例：
      表达式：a - b + ((((c % d) * f) % e) * K % M) % g % h = target
    约束：
      - a,b,c,d,e,f,g,h ∈ {0..9}，互不相同；
      - d,e,g,h,M ∈ {2..9}；
      - 统一括号风格与计算顺序；
      - 在固定 (c,d,e,f,g,h,K,M) 的前提下，(a,b) 唯一。
    难度控制：
      - diff_level ∈ {1,2,3} 对 K、M、target 与 a,b 是否允许为 0 做不同设定。
    返回 dict:
      {a,b,c,d,e,f,g,h,K,M,target,ab_count,expr}
    """
    if seed is not None:
        random.seed(seed)
    else:
        random.seed()

    cfg = _ranges_by_difficulty(diff_level)
    K_lo, K_hi = cfg["K_range"]
    M_lo, M_hi = cfg["M_range"]
    T_lo, T_hi = cfg["target_range"]
    forbid_zero_ab = cfg["forbid_zero_ab"]
    t8_forbidden = cfg["t8_forbidden"]

    def sample_digits():
        # 所有取模右操作数从 {2..9} 抽取，避免退化与非法
        d = random.randint(2, 9)
        e = random.randint(3, 9)  # 提升信息量，避免 e=2 太弱
        g = random.randint(4, 9)  # 提升信息量，避免 g 过小
        h = random.randint(5, 9)  # 提升信息量，避免 h 过小
        # 其余位 c、f 从 {0..9} 抽取，但确保互异且与 d,e,g,h 不冲突；f 避免 0
        used = {d, e, g, h}
        f_candidates = [x for x in range(1, 10) if x not in used]  # f != 0
        if not f_candidates:
            return None
        f = random.choice(f_candidates)
        used.add(f)
        c_candidates = [x for x in range(1, 10) if x not in used]  # c 优先非零
        if not c_candidates:
            # 退一步允许 c=0
            c_candidates = [x for x in range(0, 10) if x not in used]
            if not c_candidates:
                return None
        c = random.choice(c_candidates)
        return c, d, e, f, g, h

    MAX_TRY = 10000
    for _ in range(MAX_TRY):
        # 结构参数 K、M：避免退化，确保 gcd(K,M)=1 且 K % M != 0
        K = random.randint(K_lo, K_hi)
        M = random.randint(M_lo, M_hi)
        if M < 2 or K % M == 0 or math.gcd(K, M) != 1:
            continue

        # 抽取 c,d,e,f,g,h（互异、非零且不小于2），并尽量减少退化
        sampled = sample_digits()
        if sampled is None:
            continue
        c, d, e, f, g, h = sampled
        if len({c, d, e, f, g, h}) != 6:
            continue

        # 计算链式块值 t8，避开过小的集合（提升信息量与难度）
        t8 = _eval_block(c, d, e, f, K, M, g, h)
        if t8 is None or t8 in t8_forbidden:
            continue

        # 穷举 D ∈ [-9..9]，确保唯一 (a,b) 且 target 落在范围内
        used = {c, d, e, f, g, h}
        unique_candidates = []
        for D in range(-9, 9 + 1):
            pairs = _unique_pairs_for_D(D, used, forbid_zero_ab)
            if len(pairs) == 1:
                tgt = t8 + D
                if T_lo <= tgt <= T_hi:
                    unique_candidates.append((D, tgt, pairs[0]))
        if not unique_candidates:
            continue

        # 随机挑选唯一候选
        D, target, (a, b) = random.choice(unique_candidates)

        # 最终一致性校验
        if len({a, b, c, d, e, f, g, h}) != 8:
            continue
        if forbid_zero_ab and (a == 0 or b == 0):
            continue
        val_full = a - b + t8
        if val_full != target:
            continue

        # 再次独立枚举，真实计算 ab_count
        ab_count = count_ab(K, M, c, d, e, f, g, h, target)
        if ab_count != 1:
            continue

        expr = _make_expr(a, b, c, d, e, f, K, M, g, h, target)
        return {
            'a': a, 'b': b, 'c': c, 'd': d, 'e': e, 'f': f, 'g': g, 'h': h,
            'K': K, 'M': M, 'target': target,
            'ab_count': ab_count,
            'expr': expr
        }

    # 自适应策略：若在当前难度失败，降级难度并重试一次
    if diff_level > 1:
        return gen_instance(seed, diff_level - 1)

    # 再次放宽：允许 t8_forbidden 为空（但仍保证唯一）
    t8_forbidden = set()
    for _ in range(MAX_TRY):
        K = random.randint(3, 15)
        M = random.randint(3, 15)
        if M < 2 or K % M == 0 or math.gcd(K, M) != 1:
            continue
        sampled = sample_digits()
        if sampled is None:
            continue
        c, d, e, f, g, h = sampled
        if len({c, d, e, f, g, h}) != 6:
            continue
        t8 = _eval_block(c, d, e, f, K, M, g, h)
        if t8 is None or t8 in t8_forbidden:
            continue
        used = {c, d, e, f, g, h}
        unique_candidates = []
        for D in range(-9, 10):
            pairs = _unique_pairs_for_D(D, used, forbid_zero_ab=False)
            if len(pairs) == 1:
                tgt = t8 + D
                if 5 <= tgt <= 30:
                    unique_candidates.append((D, tgt, pairs[0]))
        if not unique_candidates:
            continue
        D, target, (a, b) = random.choice(unique_candidates)
        if len({a, b, c, d, e, f, g, h}) != 8:
            continue
        if a - b + t8 != target:
            continue
        ab_count = count_ab(K, M, c, d, e, f, g, h, target)
        if ab_count != 1:
            continue
        expr = _make_expr(a, b, c, d, e, f, K, M, g, h, target)
        return {
            'a': a, 'b': b, 'c': c, 'd': d, 'e': e, 'f': f, 'g': g, 'h': h,
            'K': K, 'M': M, 'target': target,
            'ab_count': ab_count,
            'expr': expr
        }

    # 若仍失败，抛异常提示调参
    raise RuntimeError("Failed to generate a unique-instance; consider adjusting difficulty or ranges.")