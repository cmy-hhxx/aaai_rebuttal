# math_path_0.py
# -*- coding: utf-8 -*-
import random

def pick_k_distinct(low=2, high=9, k=4, exclude=None):
    """
    从 [low, high]（含）中选取 k 个互异整数，排除 exclude 中的数
    """
    if exclude is None:
        exclude = []
    pool = [x for x in range(low, high + 1) if x not in exclude]
    if k > len(pool):
        raise ValueError('Not enough distinct numbers available for selection.')
    return random.sample(pool, k)

def choose_two_coeffs(low=2, high=9, exclude_list=None):
    """
    在 [low, high] 中选2个互异系数，且不在 exclude_list 中
    """
    if exclude_list is None:
        exclude_list = []
    pool = [x for x in range(low, high + 1) if x not in exclude_list]
    if len(pool) < 2:
        raise ValueError('Not enough candidates for coefficients.')
    return random.sample(pool, 2)

def choose_template():
    """
    选择一个表达式模板 id ∈ {1,2,3}
    """
    return random.choice([1, 2, 3])

def pick_clues(k=3):
    """
    从线索池中选取 k 条互异线索，避免显见组合。
    线索池：
      基础：'sum12','sum23','sum36','diff12','diff23','par1','par3'
      拓展：'even2','par16','linmod'
    规则：
      - (p1,p2) 的和与差不可同时出现（sum12 与 diff12 互斥）
      - (p2,p3) 的和与差不可同时出现（sum23 与 diff23 互斥）
    """
    k = max(0, min(k, 10))
    selected = set()
    used12 = False
    used23 = False
    used36 = False

    categories = ['12', '23', '36', 'par1', 'par3', 'par16', 'even2', 'linmod']
    random.shuffle(categories)

    attempts = 0
    while len(selected) < k and attempts < 100:
        attempts += 1
        cat = random.choice(categories)

        if cat == '12':
            if not used12:
                selected.add(random.choice(['sum12', 'diff12']))
                used12 = True
        elif cat == '23':
            if not used23:
                selected.add(random.choice(['sum23', 'diff23']))
                used23 = True
        elif cat == '36':
            if not used36:
                selected.add('sum36')
                used36 = True
        else:
            selected.add(cat)

    return list(selected)

def order_chain_text(var_list, is_desc):
    """
    var_list: ['p1','p2','p3','p6']
    is_desc: True -> '>'，False -> '<'
    """
    if not var_list:
        return ''
    sep = '>' if is_desc else '<'
    return sep.join(var_list)

def build_pattern_string(template_id, d, e, g, h, m1, m2):
    """
    生成题面展示的“问号版”表达式模板（统一括号与空格）。
      T1: ? - ? + (((((? % d) * m1) % e + ? * m2) % g) % h)
      T2: ? - ? + ((((? * m1 + ? * m2) % e) % g) % h)
      T3: ? + ? - (((( (? * m1) % d + (? * m2) % g) % h)))
    说明：问号自左至右依次代表 p1、p2、p3、p6
    """
    if template_id == 1:
        return f'? - ? + (((((? % {d}) * {m1}) % {e} + ? * {m2}) % {g}) % {h})'
    elif template_id == 2:
        return f'? - ? + ((((? * {m1} + ? * {m2}) % {e}) % {g}) % {h})'
    else:
        return f'? + ? - (((((? * {m1}) % {d} + (? * {m2}) % {g}) % {h})))'

def build_expr_string(template_id, a, b, c, d, e, f, g, h, m1, m2, target):
    """
    将解填入最终答案字符串，格式与模式统一，便于精确比对。
    统一去除多余空格，保持括号结构与 pattern 一致。
    """
    if template_id == 1:
        # a - b + (((((c % d) * m1) % e + f * m2) % g) % h)
        return f'{a} - {b} + ((((({c} % {d}) * {m1}) % {e} + {f} * {m2}) % {g}) % {h}) = {target}'
    elif template_id == 2:
        # a - b + ((((c * m1 + f * m2) % e) % g) % h)
        return f'{a} - {b} + (((( {c} * {m1} + {f} * {m2}) % {e}) % {g}) % {h}) = {target}'
    else:
        # a + b - (((((a3 * m1) % d + (f * m2) % g) % h)))
        return f'{a} + {b} - ((((({c} * {m1}) % {d} + ({f} * {m2}) % {g}) % {h}))) = {target}'

def eval_expr_value(template_id, a, b, c, d, e, f, g, h, m1, m2):
    """
    按线性化模板计算目标值，严格与 build_expr_string 的算式一致。
    """
    if template_id == 1:
        t = (((c % d) * m1) % e + f * m2) % g
        return a - b + (t % h)
    elif template_id == 2:
        t = ((c * m1 + f * m2) % e) % g
        return a - b + (t % h)
    else:
        t = (((c * m1) % d) + ((f * m2) % g)) % h
        return a + b - t

def choose_mod_base(d, e, g, h):
    """
    在线性同余线索中，随机选择一个底数（来自 d,e,g,h）并给出系数序列的一个排列
    返回: base, coeffs[4]  (coeffs 为 1..4 的一个随机排列)
    """
    base = random.choice([d, e, g, h])
    coeffs = random.sample([1, 2, 3, 4], 4)
    return base, coeffs

def compute_linmod_value(coeffs, a, b, c, f, base):
    """
    计算 c1*a + c2*b + c3*c + c4*f 在模 base 下的同余值
    coeffs: [c1,c2,c3,c4]
    """
    c1, c2, c3, c4 = coeffs
    return (c1 * a + c2 * b + c3 * c + c4 * f) % base

def build_linmod_text(coeffs, base, value):
    """
    构建线性同余文本：c1*p1 + c2*p2 + c3*p3 + c4*p6 ≡ value (mod base)
    """
    c1, c2, c3, c4 = coeffs
    return f'{c1}*p1 + {c2}*p2 + {c3}*p3 + {c4}*p6 ≡ {value} (mod {base})'

def build_clues_text(clue_set, sum12, sum23, sum36, diff12, diff23,
                     p1, p2, p3, p6, par1_even, par3_even,
                     par16_same, linmod_text):
    """
    根据选中的线索集合，生成单行中文线索文本。
    """
    parts = []
    if 'sum12' in clue_set:
        parts.append(f'p1+p2={sum12}')
    if 'sum23' in clue_set:
        parts.append(f'p2+p3={sum23}')
    if 'sum36' in clue_set:
        parts.append(f'p3+p6={sum36}')
    if 'diff12' in clue_set:
        parts.append(f'p1-p2={diff12}')
    if 'diff23' in clue_set:
        parts.append(f'p2-p3={diff23}')
    if 'par1' in clue_set:
        parts.append('p1为偶数' if par1_even else 'p1为奇数')
    if 'par3' in clue_set:
        parts.append('p3为偶数' if par3_even else 'p3为奇数')
    if 'par16' in clue_set:
        parts.append('p1与p6同奇偶' if par16_same else 'p1与p6不同奇偶')
    if 'even2' in clue_set:
        parts.append('p1,p2,p3,p6中恰有2个偶数')
    if 'linmod' in clue_set:
        parts.append(linmod_text)
    return '，'.join(parts)

def build_sample_answer(template_id, d, e, g, h, m1, m2, target):
    """
    示例答案字符串（样例用 a=1,b=2,c=3,f=4），与 build_expr_string 保持完全一致。
    """
    a, b, c, f = 1, 2, 3, 4
    return build_expr_string(template_id, a, b, c, d, e, f, g, h, m1, m2, target)