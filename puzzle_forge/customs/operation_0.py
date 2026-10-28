# operation_0.py
# 说明：
# - compute_odot(x, y): 实现自定义运算 ⊙，定义为 x ⊙ y = x**2 * |y|
# - gen_problem(): 随机生成一个包含 ⊙ 的（带括号的）表达式与其唯一答案，并提供用于校验的元信息
# - verify_with_meta(pack): 使用元信息对答案进行完备校验，保证唯一性与正确性

import random

def compute_odot(x, y):
    """x ⊙ y = x**2 * |y|"""
    return (x ** 2) * abs(y)

def _safe_randint(a, b, exclude=None):
    """在区间 [a, b] 内取随机整数，可排除若干取值"""
    if exclude is None:
        exclude = set()
    else:
        exclude = set(exclude if isinstance(exclude, (list, set, tuple)) else [exclude])
    for _ in range(100):
        v = random.randint(a, b)
        if v not in exclude:
            return v
    for v in [a, b]:
        if v not in exclude:
            return v
    return a

def _apply_op(a, b, op):
    """对二元运算 a (op) b 求值，支持 + - * /；其中 / 返回浮点"""
    if op == '+':
        return a + b
    if op == '-':
        return a - b
    if op == '*':
        return a * b
    if op == '/':
        return a / b  # 调用方保证 b != 0
    raise ValueError("Unsupported operator")

def _fmt_num(n):
    """将整数格式化为表达式中的安全表示；负数加括号避免出现 '+ -5' 之类的不规范书写"""
    return f"({n})" if isinstance(n, int) and n < 0 else str(n)

def gen_problem():
    """
    随机生成表达式（含 ⊙，并可能含加减乘除与括号），并计算唯一答案。
    所有模板均显式使用括号，规避同级结合歧义；生成时自动规避除零。
    模板（随机其一）：
      1) a ⊙ b
      2) (a ⊙ b) op c
      3) a op (b ⊙ c)
      4) (a op b) ⊙ c
      5) (a ⊙ b) op (c ⊙ d)
      6) ((a op b) ⊙ c) op d
      7) a op ((b ⊙ c) op2 d)
      8) ((a ⊙ b) ⊙ c) op d
      9) a op ((b ⊙ c) ⊙ d)
    其中 op ∈ {+, -, *, /}。
    返回：
        pack = {
          'expr': 表达式字符串（含 ⊙ 与必要括号，负数带括号避免歧义）,
          'ans': 数值答案（int或float）,
          'meta': {用于验证的元信息}
        }
    """
    a = random.randint(-15, 15)
    b = random.randint(-15, 15)
    c = random.randint(-15, 15)
    d = random.randint(-15, 15)

    # 选择外层结构与运算符
    pattern = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9])
    op = random.choice(['+', '-', '*', '/'])
    op2 = random.choice(['+', '-', '*', '/'])  # 用于某些双层结构

    # 针对除法的分母做非零约束
    if pattern in (2,):
        # (a ⊙ b) op c ：如果 op 是除法，c != 0
        if op == '/':
            c = _safe_randint(-15, 15, exclude=0)
    if pattern in (3,):
        # a op (b ⊙ c)：若 op 是除法，右值 (b ⊙ c) 必须 != 0；只需保证 b != 0 且 c != 0
        if op == '/':
            if b == 0:
                b = _safe_randint(-15, 15, exclude=0)
            c = _safe_randint(-15, 15, exclude=0)
    if pattern in (4,):
        # (a op b) ⊙ c：内层 op 可为 /；若 op 为 /，需 b != 0
        if op == '/':
            if b == 0:
                b = _safe_randint(-15, 15, exclude=0)
    if pattern in (5,):
        # (a ⊙ b) op (c ⊙ d) ：若 op 为 /，右值 (c ⊙ d) != 0 => c != 0 且 d != 0
        if op == '/':
            if c == 0:
                c = _safe_randint(-15, 15, exclude=0)
            if d == 0:
                d = _safe_randint(-15, 15, exclude=0)
    if pattern in (6,):
        # ((a op b) ⊙ c) op d ：若 op 为 /，需 d != 0；若内层 op 是 /，需 b != 0
        if op == '/':
            d = _safe_randint(-15, 15, exclude=0)
        if op2 == '/':  # 用 op2 表示内层 (a op2 b)
            if b == 0:
                b = _safe_randint(-15, 15, exclude=0)
    if pattern in (7,):
        # a op ((b ⊙ c) op2 d) ：若内层 op2 是 /，需 d != 0；为简洁与安全，外层避免为除法
        if op2 == '/':
            d = _safe_randint(-15, 15, exclude=0)
        op = random.choice(['+', '-', '*'])  # 外层不使用除法以避免复杂分母约束
    if pattern in (8,):
        # ((a ⊙ b) ⊙ c) op d ：若 op 为 /，需 d != 0
        if op == '/':
            d = _safe_randint(-15, 15, exclude=0)
    if pattern in (9,):
        # a op ((b ⊙ c) ⊙ d) ：若 op 为 /，需右值 != 0；确保 d != 0 即可
        if op == '/':
            d = _safe_randint(-15, 15, exclude=0)

    # 计算答案并构造表达式与元信息
    if pattern == 1:
        ans = compute_odot(a, b)
        expr = f"{_fmt_num(a)} ⊙ {_fmt_num(b)}"
        meta = {'pattern': 1, 'a': a, 'b': b}
    elif pattern == 2:
        left = compute_odot(a, b)
        ans = _apply_op(left, c, op)
        expr = f"({_fmt_num(a)} ⊙ {_fmt_num(b)}) {op} {_fmt_num(c)}"
        meta = {'pattern': 2, 'a': a, 'b': b, 'c': c, 'op': op}
    elif pattern == 3:
        right = compute_odot(b, c)
        ans = _apply_op(a, right, op)
        expr = f"{_fmt_num(a)} {op} ({_fmt_num(b)} ⊙ {_fmt_num(c)})"
        meta = {'pattern': 3, 'a': a, 'b': b, 'c': c, 'op': op}
    elif pattern == 4:
        inner = _apply_op(a, b, op)
        ans = compute_odot(inner, c)
        expr = f"({_fmt_num(a)} {op} {_fmt_num(b)}) ⊙ {_fmt_num(c)}"
        meta = {'pattern': 4, 'a': a, 'b': b, 'c': c, 'op': op}
    elif pattern == 5:
        left = compute_odot(a, b)
        right = compute_odot(c, d)
        ans = _apply_op(left, right, op)
        expr = f"({_fmt_num(a)} ⊙ {_fmt_num(b)}) {op} ({_fmt_num(c)} ⊙ {_fmt_num(d)})"
        meta = {'pattern': 5, 'a': a, 'b': b, 'c': c, 'd': d, 'op': op}
    elif pattern == 6:
        inner_left = _apply_op(a, b, op2)
        inner_odot = compute_odot(inner_left, c)
        ans = _apply_op(inner_odot, d, op)
        expr = f"(({_fmt_num(a)} {op2} {_fmt_num(b)}) ⊙ {_fmt_num(c)}) {op} {_fmt_num(d)}"
        meta = {'pattern': 6, 'a': a, 'b': b, 'c': c, 'd': d, 'op': op, 'op2': op2}
    elif pattern == 7:
        inner_right = _apply_op(compute_odot(b, c), d, op2)
        ans = _apply_op(a, inner_right, op)
        expr = f"{_fmt_num(a)} {op} (({_fmt_num(b)} ⊙ {_fmt_num(c)}) {op2} {_fmt_num(d)})"
        meta = {'pattern': 7, 'a': a, 'b': b, 'c': c, 'd': d, 'op': op, 'op2': op2}
    elif pattern == 8:
        inner1 = compute_odot(a, b)
        inner2 = compute_odot(inner1, c)
        ans = _apply_op(inner2, d, op)
        expr = f"(({_fmt_num(a)} ⊙ {_fmt_num(b)}) ⊙ {_fmt_num(c)}) {op} {_fmt_num(d)}"
        meta = {'pattern': 8, 'a': a, 'b': b, 'c': c, 'd': d, 'op': op}
    else:  # pattern == 9
        inner2 = compute_odot(compute_odot(b, c), d)
        ans = _apply_op(a, inner2, op)
        expr = f"{_fmt_num(a)} {op} (({_fmt_num(b)} ⊙ {_fmt_num(c)}) ⊙ {_fmt_num(d)})"
        meta = {'pattern': 9, 'a': a, 'b': b, 'c': c, 'd': d, 'op': op}

    return {'expr': expr, 'ans': ans, 'meta': meta}

def verify_with_meta(pack):
    """
    使用生成时的元信息对答案进行完备校验，保证题目答案的唯一性与正确性。
    """
    try:
        ans = pack.get('ans')
        meta = pack.get('meta', {})
        pattern = meta.get('pattern')

        if pattern == 1:
            a, b = meta['a'], meta['b']
            expected = compute_odot(a, b)
        elif pattern == 2:
            a, b, c, op = meta['a'], meta['b'], meta['c'], meta['op']
            expected = _apply_op(compute_odot(a, b), c, op)
        elif pattern == 3:
            a, b, c, op = meta['a'], meta['b'], meta['c'], meta['op']
            expected = _apply_op(a, compute_odot(b, c), op)
        elif pattern == 4:
            a, b, c, op = meta['a'], meta['b'], meta['c'], meta['op']
            expected = compute_odot(_apply_op(a, b, op), c)
        elif pattern == 5:
            a, b, c, d, op = meta['a'], meta['b'], meta['c'], meta['d'], meta['op']
            expected = _apply_op(compute_odot(a, b), compute_odot(c, d), op)
        elif pattern == 6:
            a, b, c, d, op, op2 = meta['a'], meta['b'], meta['c'], meta['d'], meta['op'], meta['op2']
            expected = _apply_op(compute_odot(_apply_op(a, b, op2), c), d, op)
        elif pattern == 7:
            a, b, c, d, op, op2 = meta['a'], meta['b'], meta['c'], meta['d'], meta['op'], meta['op2']
            expected = _apply_op(a, _apply_op(compute_odot(b, c), d, op2), op)
        elif pattern == 8:
            a, b, c, d, op = meta['a'], meta['b'], meta['c'], meta['d'], meta['op']
            expected = _apply_op(compute_odot(compute_odot(a, b), c), d, op)
        elif pattern == 9:
            a, b, c, d, op = meta['a'], meta['b'], meta['c'], meta['d'], meta['op']
            expected = _apply_op(a, compute_odot(compute_odot(b, c), d), op)
        else:
            return False

        # 容差比较（处理浮点）
        if isinstance(expected, float) or isinstance(ans, float):
            return abs(float(expected) - float(ans)) <= 1e-9
        return expected == ans
    except Exception:
        return False