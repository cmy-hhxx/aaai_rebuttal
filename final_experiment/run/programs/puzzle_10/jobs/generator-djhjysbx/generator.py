import sys, json, math, random, itertools
from fractions import Fraction

# ----------------------------
# 24点（四数一次）数据生成器
# - 支持重复数字
# - 运算：+ - * /
# - 允许括号（通过二叉树组合体现）
# - 输出中文题面与解释
# ----------------------------

OPS = [
    ("+", lambda a, b: a + b),
    ("-", lambda a, b: a - b),
    ("*", lambda a, b: a * b),
    ("/", lambda a, b: a / b if b != 0 else None),
]

# 为了显示更直观：把 * / 显示成 × ÷
DISP_OP = {"+": "+", "-": "-", "*": "×", "/": "÷"}

def frac_from_int(x: int) -> Fraction:
    return Fraction(x, 1)

def safe_apply(op_sym, a: Fraction, b: Fraction):
    if op_sym == "/":
        if b == 0:
            return None
        return a / b
    elif op_sym == "+":
        return a + b
    elif op_sym == "-":
        return a - b
    elif op_sym == "*":
        return a * b
    else:
        raise ValueError("unknown op")

def precedence(op_sym: str) -> int:
    if op_sym in ("*", "/"):
        return 2
    return 1

def format_expr(node):
    """
    node: (op, left, right) 或者 Fraction/int 叶子
    返回 (expr_str, prec)
    """
    if isinstance(node, tuple):
        op, L, R = node
        ls, lp = format_expr(L)
        rs, rp = format_expr(R)
        p = precedence(op)

        # 左右子表达式是否需要括号：当子优先级更低时需要
        # 对于减法/除法：右侧同优先级也需要括号以保持结构
        if isinstance(L, tuple):
            if lp < p:
                ls = f"({ls})"
        if isinstance(R, tuple):
            if rp < p or (op in ("-", "/") and rp == p):
                rs = f"({rs})"
        return f"{ls}{DISP_OP[op]}{rs}", p
    else:
        # 叶子：Fraction（来自整数）
        if isinstance(node, Fraction):
            if node.denominator == 1:
                return str(node.numerator), 3
            else:
                # 题面允许除法，所以用 a/b 形式
                return f"{node.numerator}/{node.denominator}", 3
        return str(node), 3

def eval_node(node) -> Fraction:
    if isinstance(node, tuple):
        op, L, R = node
        a = eval_node(L)
        b = eval_node(R)
        if op == "/":
            if b == 0:
                raise ZeroDivisionError
            return a / b
        elif op == "+":
            return a + b
        elif op == "-":
            return a - b
        elif op == "*":
            return a * b
        else:
            raise ValueError
    else:
        return node if isinstance(node, Fraction) else Fraction(node, 1)

def all_solutions_for_numbers(nums, target=Fraction(24, 1), limit=2000):
    """
    精确枚举所有能得到 target 的表达式树（数量可能很多，做上限 limit）。
    nums: list[int] 长度4，可重复
    返回：set[str] 规范化后的表达式字符串（不含外层 [[ ]]）
    """
    # 初始节点列表：每个数都是一个叶子节点
    leaves = [frac_from_int(x) for x in nums]

    sols = set()

    # 用 multiset 的组合递归：对当前节点列表，选两项合并
    def rec(nodes):
        nonlocal sols
        if len(sols) >= limit:
            return
        if len(nodes) == 1:
            try:
                val = eval_node(nodes[0])
            except ZeroDivisionError:
                return
            if val == target:
                s, _ = format_expr(nodes[0])
                sols.add(s)
            return

        n = len(nodes)
        # 选 i<j
        for i in range(n):
            for j in range(i + 1, n):
                A = nodes[i]
                B = nodes[j]
                rest = [nodes[k] for k in range(n) if k != i and k != j]

                # 对于 + 和 * 交换无关，为减少重复可固定顺序；
                # 但表达式字符串格式化后仍可能不同，这里进一步用规则减少探索。
                for op_sym, _ in OPS:
                    # 生成结果节点
                    # 注意：- 和 / 需要考虑 A op B 与 B op A 两种
                    if op_sym in ("+", "*"):
                        # 只做一个方向，避免重复
                        try:
                            val = safe_apply(op_sym, eval_node(A), eval_node(B))
                        except ZeroDivisionError:
                            continue
                        if val is None:
                            continue
                        new = (op_sym, A, B)
                        rec(rest + [new])
                    else:
                        # 两个方向
                        for left, right in ((A, B), (B, A)):
                            try:
                                lv = eval_node(left)
                                rv = eval_node(right)
                            except ZeroDivisionError:
                                continue
                            val = safe_apply(op_sym, lv, rv)
                            if val is None:
                                continue
                            new = (op_sym, left, right)
                            rec(rest + [new])

    rec(leaves)
    return sols

def pick_unique_instance(rng: random.Random, max_attempts=5000):
    """
    采样一个四数组合（1..13 可重复），并确保：
    - 存在解
    - 题目给出的答案唯一（只输出一种标准答案）
    """
    for _ in range(max_attempts):
        nums = [rng.randint(1, 13) for _ in range(4)]
        sols = all_solutions_for_numbers(nums, limit=4000)
        if len(sols) == 1:
            expr = next(iter(sols))
            # 再做一次回代校验：表达式确实==24（独立于枚举过程的字符串->解析太重）
            # 这里用保存的树不方便；改为：再次枚举一次但限制 1 个即可（不同路径：打乱操作顺序）
            # 简化：用枚举结果本身已经是精确分数计算，仍做额外检查：重新计算所有解并确认仍唯一。
            sols2 = all_solutions_for_numbers(nums, limit=4000)
            if sols2 == sols:
                return nums, expr
    raise RuntimeError("在给定尝试次数内未能生成具有唯一解的四数组合。")

def build_problem_text(nums, language="zh"):
    a, b, c, d = nums
    if language == "zh":
        return (
            "你正在玩一个“24点”规则的算式谜题。\n\n"
            "规则：\n"
            "1）从 1 到 13 中给出 4 个数（允许重复）。\n"
            "2）只能使用加（+）、减（-）、乘（×）、除（÷）四则运算以及括号改变运算顺序。\n"
            "3）4 个数必须全部使用且每个数只能使用一次。\n"
            "4）目标是把结果算成 24。\n\n"
            f"本题给出的四个数是：{a} {b} {c} {d}\n"
            "请给出一个满足规则且结果为 24 的算式表达式。\n"
            "要求：把最终算式用双重方括号包起来，例如 [[a+b/c-d]]（只需给出一种即可）。"
        )
    else:
        # 备用：若未来扩展其他语言
        return (
            "24 game.\n"
            f"Numbers: {a} {b} {c} {d}\n"
        )

def build_explanation(nums, expr, language="zh"):
    # 将显示用符号转为 python 可 eval 的形式进行数值验证（用 Fraction）
    # 仅支持整数与 /，不支持 a/b 形式中的负号括号复杂解析；这里用安全方式：
    # 直接把 × ÷ 替换，并用 Fraction 进行 eval。
    py_expr = expr.replace("×", "*").replace("÷", "/")
    # 为了让 eval 使用 Fraction，对数字进行包装：
    # 简易 tokenizer：把连续数字替换成 Fraction(n,1)
    out = []
    i = 0
    while i < len(py_expr):
        ch = py_expr[i]
        if ch.isdigit():
            j = i
            while j < len(py_expr) and py_expr[j].isdigit():
                j += 1
            num = py_expr[i:j]
            out.append(f"Fraction({num},1)")
            i = j
        else:
            out.append(ch)
            i += 1
    safe = "".join(out)
    try:
        val = eval(safe, {"Fraction": Fraction})
    except Exception as e:
        # 理论上不应发生；若发生给出降级说明
        val = None
        err = str(e)

    if language == "zh":
        if val == Fraction(24, 1):
            return (
                "一种可行构造如下：\n"
                f"算式：{expr}\n"
                "校验：将算式逐步按括号与四则运算计算，最终结果为 24。\n"
                f"（精确分数校验结果：{val}）"
            )
        else:
            return (
                "给出的标准答案算式如下，并应当满足结果为 24：\n"
                f"{expr}\n"
                f"（内部校验遇到异常/不一致：val={val}, err={err if val is None else ''}）"
            )
    else:
        return f"Expression: {expr}, value={val}"

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    seen = set()
    items = []
    attempts = 0
    max_total_attempts = 20000

    while len(items) < count:
        if attempts > max_total_attempts:
            raise RuntimeError("生成失败：总体尝试次数超限，可能是唯一解实例过难采样。")
        attempts += 1

        nums, expr = pick_unique_instance(rng)
        key = tuple(nums)
        if key in seen:
            continue
        seen.add(key)

        problem = build_problem_text(nums, language="zh")
        answer = f"[[{expr}]]"
        explanation = build_explanation(nums, expr, language="zh")

        # 最终一致性自检：答案表达式必须使用四个数且各一次（按多重集计数）
        # 从 expr 中抽取所有整数 token（因为我们只用原始整数叶子），检查频次。
        tokens = []
        s = expr
        i = 0
        while i < len(s):
            if s[i].isdigit():
                j = i
                while j < len(s) and s[j].isdigit():
                    j += 1
                tokens.append(int(s[i:j]))
                i = j
            else:
                i += 1
        if sorted(tokens) != sorted(nums):
            # 若格式化导致分数叶子出现（理论不会，因为叶子全是整数），则丢弃重采样
            sys.stderr.write(f"丢弃：答案用数不匹配 nums={nums}, tokens={tokens}, expr={expr}\n")
            seen.remove(key)
            continue

        # 计算确认值为 24
        py_expr = expr.replace("×", "*").replace("÷", "/")
        out = []
        i = 0
        while i < len(py_expr):
            ch = py_expr[i]
            if ch.isdigit():
                j = i
                while j < len(py_expr) and py_expr[j].isdigit():
                    j += 1
                num = py_expr[i:j]
                out.append(f"Fraction({num},1)")
                i = j
            else:
                out.append(ch)
                i += 1
        safe = "".join(out)
        val = eval(safe, {"Fraction": Fraction})
        if val != Fraction(24, 1):
            sys.stderr.write(f"丢弃：数值不为24 nums={nums}, expr={expr}, val={val}\n")
            seen.remove(key)
            continue

        items.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    json.dump(items, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()