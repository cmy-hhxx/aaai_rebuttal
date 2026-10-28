# math_path_5.py
# -*- coding: utf-8 -*-
"""
辅助函数库：用于PuzzleClone YAML中的custom_operator
文件名需与YAML中引用一致：math_path_5.py
"""

import random

def calc_rhs(a, b, c, d, e, f, g, base_const, sign1, sign2, coeff2):
    """
    计算右端常数：
    rhs = a*b + sign1 * (c % d) * e + coeff2 * sign2 * (f % g) + base_const
    参数:
      a,b,c,d,e,f,g: 0..9 的整数（由第一阶段求解得到）
      base_const: 题面给定常数
      sign1, sign2 ∈ {-1, +1}
      coeff2 ∈ {0, 1}；为0时第二个模项不计入
    """
    r_cd = c % d
    r_fg = f % g if coeff2 == 1 else 0
    return a * b + sign1 * r_cd * e + coeff2 * sign2 * r_fg + base_const


def calc_checksum(a, b, c, d, e, f, g, chk_base):
    """
    计算加权校验余数：
    chk_rem = (a + 2*b + 3*c + 4*d + 5*e + 6*f + 7*g) % chk_base
    """
    s = a + 2*b + 3*c + 4*d + 5*e + 6*f + 7*g
    return s % chk_base


def calc_tau(a, b, c, d, e, f, g, alpha, beta, coeff2):
    """
    计算余数加权校验值：
    tau = (alpha*(c % d) + coeff2*beta*(f % g)) % (5 + alpha)
    当 coeff2 == 0 时第二项自动为0（不出现第二个模项）
    """
    r_cd = c % d
    r_fg = (f % g) if coeff2 == 1 else 0
    base2 = 5 + alpha
    return (alpha * r_cd + coeff2 * beta * r_fg) % base2


def build_desc(style_id, base_const, rhs, sign1, sign2, coeff2, chk_base, chk_rem, alpha, beta, tau, sum_all, r_sum_v):
    """
    构造题面描述文本，依据不同风格和符号设置生成自然语言。
    返回单行字符串，内部使用 '\\n' 显式换行。
    额外公开两条强约束：
      - 数位总和约束：a+b+...+g = sum_all
      - 余数之和提示： (c % d) + (f % g 或者 0) = r_sum_v
    """
    op1 = '加' if sign1 == 1 else '减'
    op2 = '加' if sign2 == 1 else '减'
    if coeff2 == 1:
        expr_txt = f"表达式为 a*b {op1} (c % d)*e {op2} (f % g) + {base_const} = {rhs}"
        rem2_txt = f"余数加权校验：令 α={alpha}、β={beta}，则 (α*(c % d) + β*(f % g)) 对 (5+α) 取模的结果为 {tau}"
        rsum_txt = f"余数之和提示： (c % d) + (f % g) = {r_sum_v}"
    else:
        expr_txt = f"表达式为 a*b {op1} (c % d)*e + {base_const} = {rhs}"
        rem2_txt = f"余数加权校验：令 α={alpha}、β={beta}，由于不出现第二个模项，按约定 (f % g)=0，此时 (α*(c % d)) 对 (5+α) 取模的结果为 {tau}"
        rsum_txt = f"余数之和提示： (c % d) = {r_sum_v}"

    if style_id == 0:
        title = "财务对账抽查（扩展版）："
        guide = "请结合所有给出的规则进行推理求解。"
    elif style_id == 1:
        title = "数据填空-算式一致性校验："
        guide = "请严格按照提示逐步推演，得出唯一的一组数字。"
    else:
        title = "数字谜题-多运算混合："
        guide = "请谨慎处理模运算与比较关系，最终给出唯一答案。"

    mod_semantics = "说明：模运算的余数定义为非负且严格小于除数（余数 ∈ [0, 除数)）。若未出现第二个模项，则视 (f % g)=0。"
    chk_txt = f"加权和模校验：将 (a + 2*b + 3*c + 4*d + 5*e + 6*f + 7*g) 对基数 {chk_base} 取模，所得余数为 {chk_rem}。"
    sum_txt = f"数位总和约束：a + b + c + d + e + f + g = {sum_all}。"
    fmt = "答案格式说明：请按(a,b,c,d,e,f,g)的顺序输出一个7元组，例如：(1,2,3,4,5,6,7)"

    return f"{title}{expr_txt}\\n{sum_txt}\\n{rsum_txt}\\n{mod_semantics}\\n{chk_txt}\\n{rem2_txt}\\n{guide}\\n{fmt}"


def parity_word(flag):
    """
    根据布尔标记返回'偶'或'奇'：
    True -> '偶'；False -> '奇'
    """
    return '偶' if bool(flag) else '奇'


def compare_word(flag):
    """
    根据布尔标记返回'大于'或'小于'：
    True -> '大于'；False -> '小于'
    """
    return '大于' if bool(flag) else '小于'


def list_len(l):
    """返回列表长度（用于避免在YAML公式中直接调用内置len）。"""
    return len(l)


def gen_hints_all(slots, values):
    """
    基于已求得的唯一解生成三类提示，改进为解驱动的确定性与适度难度：
    - 奇偶提示：固定1条，每条 ('slot', is_even)
    - 大小关系提示：固定2条（若可行），尽量覆盖4个不同的占位符，每条 ('slot1', 'slot2', is_greater)
    - 差值提示：最多1条，且差值在{2,3}，尽量选用未在大小关系中出现过的占位符，每条 ('slot1','slot2', delta)
    返回: (parity_hints, ordering_hints, difference_hints)
    """
    # 以解为种子，构造局部随机器，保证同一解生成相同提示
    try:
        seed = int(''.join(str(x) for x in values))
    except Exception:
        seed = sum(values) * 131 + len(values)
    rng = random.Random(seed)

    mapping = dict(zip(slots, values))

    # 奇偶提示：固定1条
    s_par = rng.choice(slots)
    parity_hints = [(s_par, (mapping[s_par] % 2 == 0))]

    # 大小关系提示：固定2条（若可行），尽量覆盖4个不同占位符
    all_pairs = []
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            s1, s2 = slots[i], slots[j]
            is_greater = mapping[s1] > mapping[s2]
            # 随机左右，但保持语义正确（使用局部rng）
            if rng.random() < 0.5:
                all_pairs.append((s1, s2, is_greater))
            else:
                all_pairs.append((s2, s1, mapping[s2] > mapping[s1]))

    ordering_hints = []
    if all_pairs:
        rng.shuffle(all_pairs)
        used = set()
        for p in all_pairs:
            s1, s2, _ = p
            if s1 in used or s2 in used:
                continue
            ordering_hints.append(p)
            used.add(s1); used.add(s2)
            if len(ordering_hints) >= 2:
                break
        if len(ordering_hints) < 2 and len(all_pairs) >= 2:
            # 兜底补足到2条
            for p in all_pairs:
                if p not in ordering_hints:
                    ordering_hints.append(p)
                    if len(ordering_hints) >= 2:
                        break

    # 差值提示：差值限定为{2,3}，尽量不复用 ordering 的占位符
    diff_candidates = []
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            delta = abs(mapping[slots[i]] - mapping[slots[j]])
            if delta in (2, 3):
                diff_candidates.append((slots[i], slots[j], delta))
    difference_hints = []
    if diff_candidates:
        used_in_order = set()
        for s1, s2, _ in ordering_hints:
            used_in_order.add(s1); used_in_order.add(s2)
        rng.shuffle(diff_candidates)
        chosen = None
        for cand in diff_candidates:
            s1, s2, _ = cand
            if s1 not in used_in_order and s2 not in used_in_order:
                chosen = cand
                break
        if chosen is None:
            chosen = diff_candidates[0]
        difference_hints = [chosen]

    return parity_hints, ordering_hints, difference_hints


def hints_text(slots, parity_hints, ordering_hints, difference_hints):
    """
    将三类提示渲染为多行文本（以 \\n 分隔）。
    """
    lines = []
    for s, is_even in parity_hints:
        lines.append(f"提示：占位符 {s} 为{parity_word(is_even)}数")
    for s1, s2, is_greater in ordering_hints:
        lines.append(f"提示：占位符 {s1} 的值{compare_word(is_greater)}占位符 {s2} 的值")
    for s1, s2, delta in difference_hints:
        lines.append(f"提示：占位符 {s1} 与占位符 {s2} 的数值相差为 {delta}")
    return "\\n".join(lines)