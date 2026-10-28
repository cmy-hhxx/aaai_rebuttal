# math_path_6.py
# 逆向生成与校验工具：随机生成一致的题目参数与隐藏解；并提供基本计算/校验函数（强化随机规则版）

import random
import math

def compute_expr(a, b, c, d, e, f, g):
    """
    计算表达式：(a + b * c) % d + (e // f) * g
    要求：d > 0, f > 0（正整数）
    """
    if d <= 0 or f <= 0:
        raise ZeroDivisionError("模/整除的除数需为正整数")
    return (a + b * c) % d + (e // f) * g


def is_valid_solution(a, b, c, d, e, f, g,
                      target=42, lo=-20, hi=20,
                      b_lo=None, b_hi=None, c_lo=None, c_hi=None,
                      d_lo=None, d_hi=None, f_lo=None, f_hi=None,
                      g_lo=None, g_hi=None,
                      use_b_range=True, use_c_range=True,
                      use_d_range=True, use_f_range=True, use_g_range=True,
                      qt_min=0, qt_max=7,
                      main_a1=1, main_a2=0, main_a3=0, main_a4=0,
                      parity_idx=None, parity_val=None,
                      positivity_idx=None,
                      # 新增约束参数
                      pairsum_bf=None, pairsum_cg=None,
                      ad_sum=None, qt_sum=None,
                      mod_M=None, mod_V=None,
                      l1_bound=None, nonneg_target=None):
    """
    验证 (a,b,c,d,e,f,g) 是否满足（在启用的）约束：
    - 全局范围 [lo, hi]
    - 可选：b,c,d,f,g 的狭窄区间
    - d,f 为正整数
    - e 能被 f 整除，q=e//f，q,t ∈ [qt_min, qt_max]
    - 存在 t,r 使 a + b*c = d*t + r 且 0 < r < d
    - 目标式：r + main_a1*q*g + main_a2*q + main_a3*g + main_a4 = target
    - 可选：若 parity_idx/parity_val 非空，对应变量必须为偶数/奇数
    - 可选：positivity_idx 中变量为正
    - 新增复合约束：
      * b + f = pairsum_bf
      * c + g = pairsum_cg
      * a + d = ad_sum
      * q + t = qt_sum
      * (a + 2*b + 3*c + 4*d) % mod_M = mod_V
      * |b| + |c| + |g| = l1_bound
      * [b,c,f,g] 中非负个数计数等于 nonneg_target
    """
    vals = (a, b, c, d, e, f, g)
    if any(v < lo or v > hi for v in vals):
        return False

    # 范围约束
    if use_b_range:
        if b_lo is not None and b < b_lo:
            return False
        if b_hi is not None and b > b_hi:
            return False
    if use_c_range:
        if c_lo is not None and c < c_lo:
            return False
        if c_hi is not None and c > c_hi:
            return False
    if use_d_range:
        if d_lo is not None and d < d_lo:
            return False
        if d_hi is not None and d > d_hi:
            return False
    if use_f_range:
        if f_lo is not None and f < f_lo:
            return False
        if f_hi is not None and f > f_hi:
            return False
    if use_g_range:
        if g_lo is not None and g < g_lo:
            return False
        if g_hi is not None and g > g_hi:
            return False

    # 正除数
    if d <= 0 or f <= 0:
        return False

    # 整除与 q,t,r
    if f == 0:
        return False
    if e % f != 0:
        return False
    q = e // f
    if q < qt_min or q > qt_max:
        return False

    try:
        r = (a + b * c) % d
        if r <= 0 or r >= d:
            return False
    except ZeroDivisionError:
        return False

    # t 的存在性与范围
    t_raw = (a + b * c - r)
    if d == 0:
        return False
    if t_raw % d != 0:
        return False
    t = t_raw // d
    if t < qt_min or t > qt_max:
        return False

    # 主等式
    if r + main_a1 * q * g + main_a2 * q + main_a3 * g + main_a4 != target:
        return False

    # 偶奇规则
    if parity_idx and parity_val:
        for idx, pv in zip(parity_idx, parity_val):
            v = (a, b, c, d, e, f, g)[idx]
            if pv == 0 and (v % 2 != 0):
                return False
            if pv == 1 and (v % 2 == 0):
                return False

    # 正性规则
    if positivity_idx:
        for idx in positivity_idx:
            if (a, b, c, d, e, f, g)[idx] <= 0:
                return False

    # 新增复合约束验证
    if pairsum_bf is not None and (b + f != pairsum_bf):
        return False
    if pairsum_cg is not None and (c + g != pairsum_cg):
        return False
    if ad_sum is not None and (a + d != ad_sum):
        return False
    if qt_sum is not None and (q + t != qt_sum):
        return False
    if mod_M is not None and mod_V is not None:
        if mod_M <= 0:
            return False
        lin = a + 2 * b + 3 * c + 4 * d
        if lin % mod_M != mod_V:
            return False
    if l1_bound is not None:
        if (abs(b) + abs(c) + abs(g)) != l1_bound:
            return False
    if nonneg_target is not None:
        cnt = sum(1 for v in (b, c, f, g) if v >= 0)
        if cnt != nonneg_target:
            return False

    return True


def _gen_coprime_weights(n):
    """
    生成长度为 n 的互素小整数权重向量（乱序）。
    """
    pool = [1, 2, 3, 5, 7, 11, 13, 17, 19, 23]
    for _ in range(100):
        cand = random.sample(pool, n)
        ok = True
        for i in range(n):
            for j in range(i + 1, n):
                if math.gcd(cand[i], cand[j]) != 1:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            random.shuffle(cand)
            return cand
    base = [1, 2, 3, 5, 7, 11, 13]
    random.shuffle(base)
    return base[:n]


def _make_main_template():
    """
    随机选择主等式模板的系数 (a1, a2, a3, a4) 及其文本生成器
    模板候选：
      1) r + q*g
      2) r + q + g
      3) r + q*g + g
      4) r + q*g + delta（delta ∈ [-5..5]）
      5) r + 2*q + g
    """
    choice = random.randint(1, 5)
    if choice == 1:
        return 1, 0, 0, 0, lambda tgt: f"r + q * g = {tgt}"
    if choice == 2:
        return 0, 1, 1, 0, lambda tgt: f"r + q + g = {tgt}"
    if choice == 3:
        return 1, 0, 1, 0, lambda tgt: f"r + q * g + g = {tgt}"
    if choice == 4:
        delta = random.randint(-5, 5)
        return 1, 0, 0, delta, lambda tgt: f"r + q * g + ({delta}) = {tgt}"
    # choice == 5
    return 0, 2, 1, 0, lambda tgt: f"r + 2 * q + g = {tgt}"


def gen_sensor_instance():
    """
    逆向随机生成一组一致的题目参数与隐藏解（不直接暴露解，只返回用于描述题目的参数）：
    返回字典键（新增随机规则相关字段）：
    - vmin, vmax: 全局范围
    - b_lo, b_hi; c_lo, c_hi; d_lo, d_hi; f_lo, f_hi; g_lo, g_hi
    - use_b_range...use_g_range: 各区间是否启用（布尔）
    - qt_min, qt_max: q 与 t 的范围（含下界随机 0/1）
    - main_a1..main_a4: 主等式系数
    - target: 目标值
    - parity_idx, parity_val, parity_rule_num: 偶奇规则（索引与 0/1 为偶/奇）
    - positivity_idx, pos_count: 正性规则（索引列表与数量）
    - weights: 权重向量（长度 7）
    - sum_total, checksum_total: 总和与加权和
    - 新增：pairsum_bf, pairsum_cg, ad_sum, qt_sum, mod_M, mod_V, l1_bound, nonneg_target
    - 文本片段：desc_parity, desc_ranges, desc_positivity, desc_main, desc_pairsum, desc_ad, desc_qtsum, desc_modlin, desc_l1, desc_nonneg, desc_denom
    """
    var_letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g']

    for _ in range(1000):
        # 基础区间与上下界
        d_lo = random.randint(3, 6)
        d_hi = random.randint(max(d_lo + 1, 7), 12)
        f_lo = random.randint(2, 5)
        f_hi = random.randint(max(f_lo + 1, 6), 9)
        g_lo = random.randint(1, 3)
        g_hi = random.randint(max(g_lo + 2, 6), 10)
        qt_max = random.randint(6, 9)
        qt_min = random.choice([0, 1])

        # q, f, g, e
        q = random.randint(qt_min, qt_max)
        f = random.randint(f_lo, f_hi)
        g = random.randint(g_lo, g_hi)
        e = f * q

        # d, r, t
        d = random.randint(d_lo, d_hi)
        if d <= 0:
            continue
        r = random.randint(1, max(1, d - 1))
        t = random.randint(qt_min, qt_max)

        # 生成 b, c
        b_lo = -10
        b_hi = 10
        b = random.randint(b_lo, b_hi)

        c_lo = -11
        c_hi = 11
        c = random.randint(c_lo, c_hi)

        # 根据 r 反推 a（非负，且不超过 vmax）
        bc = b * c
        a0 = (r - (bc % d)) % d  # 最小非负解
        vmax_seed = max(abs(e), abs(b), abs(c), d, f, g, 20)
        vmax = vmax_seed + random.randint(3, 12)
        vmin = -vmax
        if a0 > vmax:
            continue
        max_k = (vmax - a0) // d
        if max_k < 0:
            continue
        k = random.randint(0, max_k)
        a = a0 + k * d

        # 主等式模板（系数与文本生成器）
        main_a1, main_a2, main_a3, main_a4, main_text_fn = _make_main_template()
        target = r + main_a1 * q * g + main_a2 * q + main_a3 * g + main_a4

        # 权重与两类和
        weights = _gen_coprime_weights(7)
        vec = [a, b, c, d, e, f, g]
        sum_total = sum(vec)
        checksum_total = sum(weights[i] * vec[i] for i in range(7))

        # 随机启用的区间约束（至少启用 3 个）
        flags = {
            "use_b_range": random.random() < 0.7,
            "use_c_range": random.random() < 0.7,
            "use_d_range": random.random() < 0.7,
            "use_f_range": random.random() < 0.7,
            "use_g_range": random.random() < 0.7
        }
        if sum(1 for v in flags.values() if v) < 3:
            need = 3 - sum(1 for v in flags.values() if v)
            for key in ["use_d_range", "use_f_range", "use_g_range", "use_b_range", "use_c_range"]:
                if need <= 0:
                    break
                if not flags[key]:
                    flags[key] = True
                    need -= 1

        # 偶奇规则（从实际解中抽样 1~3 个变量）
        m = random.randint(1, 3)
        all_idx = list(range(7))
        random.shuffle(all_idx)
        pick_idx = all_idx[:m]
        parity_idx = []
        parity_val = []
        for idx in pick_idx:
            val = vec[idx]
            parity_idx.append(idx)
            parity_val.append(0 if (val % 2 == 0) else 1)
        parity_rule_num = len(parity_idx)

        # 正性规则（选 0~2 个正数变量）
        positive_candidates = [i for i, v in enumerate(vec) if v > 0]
        random.shuffle(positive_candidates)
        pos_take = random.randint(0, min(2, len(positive_candidates)))
        positivity_idx = positive_candidates[:pos_take]
        pos_count = len(positivity_idx)

        # 新增复合约束常数
        pairsum_bf = b + f
        pairsum_cg = c + g
        ad_sum = a + d
        qt_sum = q + t
        mod_M = random.randint(5, 9)
        mod_V = (a + 2 * b + 3 * c + 4 * d) % mod_M
        l1_bound = abs(b) + abs(c) + abs(g)
        nonneg_target = sum(1 for v in (b, c, f, g) if v >= 0)

        # 文本片段渲染
        def _parity_word(pv):
            return "偶数" if pv == 0 else "奇数"
        desc_parity = "；".join([f"{var_letters[i]} 为{_parity_word(pv)}" for i, pv in zip(parity_idx, parity_val)]) or "无偶奇限制"
        segs = []
        if flags["use_b_range"]:
            segs.append(f"b ∈ [{b_lo}, {b_hi}]")
        if flags["use_c_range"]:
            segs.append(f"c ∈ [{c_lo}, {c_hi}]")
        if flags["use_d_range"]:
            segs.append(f"d ∈ [{d_lo}, {d_hi}]")
        if flags["use_f_range"]:
            segs.append(f"f ∈ [{f_lo}, {f_hi}]")
        if flags["use_g_range"]:
            segs.append(f"g ∈ [{g_lo}, {g_hi}]")
        desc_ranges = "；".join(segs) if segs else "无额外区间限制"
        if pos_count > 0:
            desc_pos = "、".join([var_letters[i] for i in positivity_idx])
            desc_positivity = f"以下变量为正：{desc_pos}"
        else:
            desc_positivity = "无额外正性要求"
        desc_main = main_text_fn(target)
        desc_pairsum = f"b + f = {pairsum_bf}；c + g = {pairsum_cg}"
        desc_ad = f"a + d = {ad_sum}"
        desc_qtsum = f"q + t = {qt_sum}"
        desc_modlin = f"(a + 2*b + 3*c + 4*d) % {mod_M} = {mod_V}"
        desc_l1 = f"|b| + |c| + |g| = {l1_bound}"
        desc_nonneg = f"在 [b,c,f,g] 中，非负个数恰为 {nonneg_target}"
        desc_denom = "d 与 f 为正整数"

        # 校验一致性（防御式）
        if not is_valid_solution(
            a, b, c, d, e, f, g,
            target=target, lo=vmin, hi=vmax,
            b_lo=b_lo, b_hi=b_hi, c_lo=c_lo, c_hi=c_hi,
            d_lo=d_lo, d_hi=d_hi, f_lo=f_lo, f_hi=f_hi,
            g_lo=g_lo, g_hi=g_hi,
            use_b_range=flags["use_b_range"], use_c_range=flags["use_c_range"],
            use_d_range=flags["use_d_range"], use_f_range=flags["use_f_range"], use_g_range=flags["use_g_range"],
            qt_min=qt_min, qt_max=qt_max,
            main_a1=main_a1, main_a2=main_a2, main_a3=main_a3, main_a4=main_a4,
            parity_idx=parity_idx, parity_val=parity_val,
            positivity_idx=positivity_idx,
            pairsum_bf=pairsum_bf, pairsum_cg=pairsum_cg,
            ad_sum=ad_sum, qt_sum=qt_sum,
            mod_M=mod_M, mod_V=mod_V,
            l1_bound=l1_bound, nonneg_target=nonneg_target
        ):
            continue

        return {
            "vmin": vmin, "vmax": vmax,
            "b_lo": b_lo, "b_hi": b_hi,
            "c_lo": c_lo, "c_hi": c_hi,
            "d_lo": d_lo, "d_hi": d_hi,
            "f_lo": f_lo, "f_hi": f_hi,
            "g_lo": g_lo, "g_hi": g_hi,
            "use_b_range": flags["use_b_range"],
            "use_c_range": flags["use_c_range"],
            "use_d_range": flags["use_d_range"],
            "use_f_range": flags["use_f_range"],
            "use_g_range": flags["use_g_range"],
            "qt_min": qt_min, "qt_max": qt_max,
            "main_a1": main_a1, "main_a2": main_a2, "main_a3": main_a3, "main_a4": main_a4,
            "target": target,
            "parity_idx": parity_idx, "parity_val": parity_val, "parity_rule_num": parity_rule_num,
            "positivity_idx": positivity_idx, "pos_count": pos_count,
            "weights": weights,
            "sum_total": sum_total,
            "checksum_total": checksum_total,
            # 新增常数
            "pairsum_bf": pairsum_bf,
            "pairsum_cg": pairsum_cg,
            "ad_sum": ad_sum,
            "qt_sum": qt_sum,
            "mod_M": mod_M,
            "mod_V": mod_V,
            "l1_bound": l1_bound,
            "nonneg_target": nonneg_target,
            # 文本片段
            "desc_parity": desc_parity,
            "desc_ranges": desc_ranges,
            "desc_positivity": desc_positivity,
            "desc_main": desc_main,
            "desc_pairsum": desc_pairsum,
            "desc_ad": desc_ad,
            "desc_qtsum": desc_qtsum,
            "desc_modlin": desc_modlin,
            "desc_l1": desc_l1,
            "desc_nonneg": desc_nonneg,
            "desc_denom": desc_denom
        }

    # 回退（极少触发）：给出一组保守参数，允许上层丢弃
    # 注意：回退不保证唯一解，仅为占位。生成器可选择丢弃该实例。
    return {
        "vmin": -20, "vmax": 30,
        "b_lo": -10, "b_hi": 10,
        "c_lo": -11, "c_hi": 11,
        "d_lo": 3, "d_hi": 9,
        "f_lo": 2, "f_hi": 8,
        "g_lo": 1, "g_hi": 10,
        "use_b_range": True, "use_c_range": True, "use_d_range": True, "use_f_range": True, "use_g_range": True,
        "qt_min": 0, "qt_max": 7,
        "main_a1": 1, "main_a2": 0, "main_a3": 0, "main_a4": 0,
        "target": 42,
        "parity_idx": [1, 2], "parity_val": [0, 1], "parity_rule_num": 2,
        "positivity_idx": [], "pos_count": 0,
        "weights": [1, 2, 3, 5, 7, 11, 13],
        "sum_total": 0,
        "checksum_total": 0,
        "pairsum_bf": 10,
        "pairsum_cg": 9,
        "ad_sum": 8,
        "qt_sum": 7,
        "mod_M": 7,
        "mod_V": 3,
        "l1_bound": 12,
        "nonneg_target": 3,
        "desc_parity": "b 为偶数；c 为奇数",
        "desc_ranges": "b ∈ [-10, 10]；c ∈ [-11, 11]；d ∈ [3, 9]；f ∈ [2, 8]；g ∈ [1, 10]",
        "desc_positivity": "无额外正性要求",
        "desc_main": "r + q * g = 42",
        "desc_pairsum": "b + f = 10；c + g = 9",
        "desc_ad": "a + d = 8",
        "desc_qtsum": "q + t = 7",
        "desc_modlin": "(a + 2*b + 3*c + 4*d) % 7 = 3",
        "desc_l1": "|b| + |c| + |g| = 12",
        "desc_nonneg": "在 [b,c,f,g] 中，非负个数恰为 3",
        "desc_denom": "d 与 f 为正整数"
    }