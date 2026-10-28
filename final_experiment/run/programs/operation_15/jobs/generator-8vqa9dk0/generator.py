import sys, json, random, math
from typing import List, Dict, Any, Tuple, Optional

import sympy as sp


# ----------------------------
# Utilities
# ----------------------------

def sgn_str(n: int) -> str:
    return "+" if n >= 0 else "-"

def fmt_rational(q: sp.Rational) -> str:
    if q.q == 1:
        return str(int(q.p))
    return f"{int(q.p)}/{int(q.q)}"

def expr_to_zh(expr: sp.Expr) -> str:
    # Sympy pretty in plain text, keep it compact
    return str(sp.simplify(expr))

def safe_int(x: sp.Expr) -> Optional[int]:
    x_s = sp.simplify(x)
    if x_s.is_integer:
        return int(x_s)
    return None

def safe_rational_or_real_to_json(x: sp.Expr) -> Any:
    x_s = sp.simplify(x)
    if x_s.is_Rational:
        return int(x_s) if x_s.q == 1 else f"{int(x_s.p)}/{int(x_s.q)}"
    # If it is a special constant (pi, E, sqrt), output as string
    if x_s.has(sp.pi) or x_s.has(sp.E) or x_s.has(sp.sqrt):
        return str(x_s)
    # If it is numeric but not rational, try float with stable rounding
    if x_s.is_number:
        try:
            val = float(x_s.evalf(30))
            # stable representation
            return float(f"{val:.12g}")
        except Exception:
            return str(x_s)
    return str(x_s)

def wrap_double_brackets(ans: Any) -> str:
    # Requirement from seed: wrap a single number in [[...]].
    # Our generator always asks for single value.
    return f"[[{ans}]]"

def pick_nonzero_int(rng: random.Random, lo: int, hi: int) -> int:
    while True:
        v = rng.randint(lo, hi)
        if v != 0:
            return v

def unique_list(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ----------------------------
# Operation model
# ----------------------------

x = sp.Symbol('x', real=True)

def compute_custom_operation(op: str, f: sp.Expr, g: sp.Expr) -> sp.Expr:
    """
    Supported:
    - "triangle": f△g = (f(g(x)))'
    - "nabla":    f▽g = (g(f(x)))'
    - "star":     f★g = (f(x)*g(x))'
    - "circle":   f∘g = f(g(x))  (not derivative)
    - "box":      f□g = (f(g(x)))'' (second derivative)
    """
    if op == "triangle":
        expr = sp.diff(f.subs(x, g), x)
    elif op == "nabla":
        expr = sp.diff(g.subs(x, f), x)
    elif op == "star":
        expr = sp.diff(f * g, x)
    elif op == "circle":
        expr = f.subs(x, g)
    elif op == "box":
        expr = sp.diff(f.subs(x, g), x, 2)
    else:
        raise ValueError("unknown op")
    return sp.simplify(expr)

def eval_at(expr: sp.Expr, x0: sp.Expr) -> sp.Expr:
    return sp.simplify(expr.subs(x, x0))


# ----------------------------
# Function families
# ----------------------------

def make_poly(rng: random.Random, deg: int, coeff_range: Tuple[int,int]=(-4,4), ensure_nonlinear=True) -> sp.Expr:
    lo, hi = coeff_range
    # ensure leading coefficient nonzero
    a = pick_nonzero_int(rng, lo, hi)
    expr = a * x**deg
    # add lower terms
    for p in range(deg-1, -1, -1):
        c = rng.randint(lo, hi)
        if c != 0:
            expr += c * x**p
    if ensure_nonlinear and deg <= 1:
        # force at least quadratic
        return make_poly(rng, 2, coeff_range, True)
    return sp.simplify(expr)

def make_exp_affine(rng: random.Random, coeff_range=(-3,3)) -> sp.Expr:
    a = pick_nonzero_int(rng, coeff_range[0], coeff_range[1])
    b = rng.randint(coeff_range[0], coeff_range[1])
    return sp.exp(a*x + b)

def make_log_affine(rng: random.Random, coeff_range=(1,4)) -> sp.Expr:
    # ln(kx + c), ensure argument positive at chosen evaluation points later
    k = pick_nonzero_int(rng, 1, coeff_range[1])
    c = rng.randint(1, coeff_range[1]*2)
    return sp.log(k*x + c)

def make_trig_affine(rng: random.Random) -> sp.Expr:
    a = pick_nonzero_int(rng, -4, 4)
    b = rng.randint(-3, 3)
    func = rng.choice([sp.sin, sp.cos])
    return func(a*x + b)

def make_rational_simple(rng: random.Random) -> sp.Expr:
    # (ax+b)/(cx+d), avoid c=0
    a = pick_nonzero_int(rng, -5, 5)
    b = rng.randint(-5, 5)
    c = pick_nonzero_int(rng, -5, 5)
    d = rng.randint(-5, 5)
    return sp.simplify((a*x + b)/(c*x + d))

def choose_x0_for_domain(rng: random.Random, f: sp.Expr, g: sp.Expr, op: str) -> sp.Expr:
    """
    Choose an x0 from a small candidate set so that operation expression is defined.
    We handle log domains and rational denominator nonzero at needed points.
    """
    candidates = [
        sp.Integer(0),
        sp.Integer(1),
        sp.Integer(-1),
        sp.Rational(1, 2),
        sp.Rational(-1, 2),
        sp.Integer(2),
        sp.Integer(-2),
    ]
    rng.shuffle(candidates)

    op_expr = compute_custom_operation(op, f, g)

    for x0 in candidates:
        try:
            v = eval_at(op_expr, x0)
            # Ensure no zoo/NaN
            if v.has(sp.zoo) or v.has(sp.nan) or v is sp.zoo:
                continue
            # Ensure denominators not zero in evaluation
            if not sp.simplify(sp.denom(v)).subs({}, {}) == 0:
                # Check it is finite numeric
                if v.is_real is False:
                    # allow symbolic constants but real
                    # attempt numeric check
                    vv = sp.N(v, 30)
                    if not (vv.is_real and vv.is_finite):
                        continue
                else:
                    vv = sp.N(v, 30)
                    if hasattr(vv, "is_finite") and not vv.is_finite:
                        continue
            # Also ensure no undefined log at x0 by numerical finiteness
            vv = sp.N(v, 30)
            if (hasattr(vv, "is_finite") and vv.is_finite) or isinstance(vv, (sp.Float, sp.Integer, sp.Rational)):
                return x0
        except Exception:
            continue

    # fallback: try random integers
    for _ in range(50):
        x0 = sp.Integer(rng.randint(-3, 3))
        try:
            v = eval_at(op_expr, x0)
            vv = sp.N(v, 30)
            if hasattr(vv, "is_finite") and vv.is_finite and vv.is_real:
                return x0
        except Exception:
            pass
    raise RuntimeError("无法为该函数组合找到合适的取值点 x0 以保证定义良好。")


# ----------------------------
# Problem templates (Chinese)
# ----------------------------

def render_problem(op_symbol: str, op_def: str, f_expr: sp.Expr, g_expr: sp.Expr, x0: sp.Expr) -> str:
    return (
        "你是一名擅长计算自定义运算的助手。下面给出一种自定义二元运算的规则，请严格按规则计算。\n\n"
        "### 运算规则：\n"
        f"{op_symbol}：{op_def}\n\n"
        "### 题目：\n"
        f"已知 f(x)={expr_to_zh(f_expr)}，g(x)={expr_to_zh(g_expr)}，求 (f {op_symbol} g) 在 x={expr_to_zh(x0)} 时的值。\n"
        "请把答案写成单个数，并用双层方括号包裹，例如：[[3]]。\n"
    )

def render_explanation(op_symbol: str, op_name: str, f_expr: sp.Expr, g_expr: sp.Expr, op_expr: sp.Expr, x0: sp.Expr, value: sp.Expr) -> str:
    # Keep it brief but checkable
    composed = sp.simplify(f_expr.subs(x, g_expr)) if op_name in ("triangle", "box") else (
        sp.simplify(g_expr.subs(x, f_expr)) if op_name == "nabla" else None
    )
    parts = []
    parts.append(f"按定义，(f {op_symbol} g) 需要先按规则构造表达式再求导/代入。")
    if op_name == "triangle":
        parts.append(f"先复合：f(g(x)) = {expr_to_zh(composed)}。")
        parts.append(f"再求导：(f(g(x)))' = {expr_to_zh(op_expr)}。")
    elif op_name == "box":
        parts.append(f"先复合：f(g(x)) = {expr_to_zh(composed)}。")
        parts.append(f"再二阶导：(f(g(x)))'' = {expr_to_zh(op_expr)}。")
    elif op_name == "nabla":
        parts.append(f"先复合：g(f(x)) = {expr_to_zh(composed)}。")
        parts.append(f"再求导：(g(f(x)))' = {expr_to_zh(op_expr)}。")
    elif op_name == "star":
        parts.append(f"先相乘：f(x)g(x) = {expr_to_zh(sp.simplify(f_expr*g_expr))}。")
        parts.append(f"再求导：(f(x)g(x))' = {expr_to_zh(op_expr)}。")
    elif op_name == "circle":
        parts.append(f"直接复合：f(g(x)) = {expr_to_zh(op_expr)}。")
    parts.append(f"代入 x={expr_to_zh(x0)}，得到值 {expr_to_zh(value)}。")
    return "\n".join(parts)


# ----------------------------
# Generator core
# ----------------------------

OPS = [
    ("△", "f△g = (f(g(x)))′", "triangle"),
    ("▽", "f▽g = (g(f(x)))′", "nabla"),
    ("★", "f★g = (f(x)·g(x))′", "star"),
    ("∘", "f∘g = f(g(x))", "circle"),
    ("□", "f□g = (f(g(x)))″", "box"),
]

def sample_function_pair(rng: random.Random) -> Tuple[sp.Expr, sp.Expr]:
    # choose families with variety
    families = ["poly", "exp", "trig", "rat", "log"]
    f_type = rng.choice(families)
    g_type = rng.choice(families)

    def make_one(t: str) -> sp.Expr:
        if t == "poly":
            deg = rng.choice([2, 3, 4])
            return make_poly(rng, deg)
        if t == "exp":
            # allow exp(affine) or exp(poly small)
            if rng.random() < 0.7:
                return make_exp_affine(rng)
            else:
                p = make_poly(rng, rng.choice([2, 3]), coeff_range=(-2, 2))
                return sp.exp(p)
        if t == "trig":
            return make_trig_affine(rng)
        if t == "rat":
            return make_rational_simple(rng)
        if t == "log":
            return make_log_affine(rng)
        raise ValueError

    f_expr = make_one(f_type)
    g_expr = make_one(g_type)

    return sp.simplify(f_expr), sp.simplify(g_expr)

def make_item(rng: random.Random, used_signatures: set) -> Dict[str, Any]:
    # bounded resampling
    for _ in range(200):
        op_symbol, op_def, op_name = rng.choice(OPS)
        f_expr, g_expr = sample_function_pair(rng)

        # Avoid trivial / overly pathological cases for derivative at chosen points:
        # - prevent constant functions
        if sp.simplify(sp.diff(f_expr, x)) == 0 and op_name in ("triangle", "box", "star", "nabla"):
            continue
        if sp.simplify(sp.diff(g_expr, x)) == 0 and op_name in ("triangle", "box", "star", "nabla"):
            continue

        try:
            x0 = choose_x0_for_domain(rng, f_expr, g_expr, op_name)
        except Exception:
            continue

        try:
            op_expr = compute_custom_operation(op_name, f_expr, g_expr)
            val = eval_at(op_expr, x0)
            # ensure it's a determinate value
            vv = sp.N(val, 50)
            if hasattr(vv, "is_finite") and not vv.is_finite:
                continue
            if hasattr(vv, "is_real") and not vv.is_real:
                continue
        except Exception:
            continue

        # signature to avoid duplicates
        sig = (op_name, str(sp.simplify(f_expr)), str(sp.simplify(g_expr)), str(x0))
        if sig in used_signatures:
            continue

        # cross-check: numerical differentiation when op involves derivative
        if op_name in ("triangle", "nabla", "star"):
            try:
                # numeric check using lambdify and central difference on the composed/product function (not on already-derived expr)
                h = 1e-6
                xf = float(sp.N(x0, 20))
                if op_name == "triangle":
                    base = sp.simplify(f_expr.subs(x, g_expr))
                elif op_name == "nabla":
                    base = sp.simplify(g_expr.subs(x, f_expr))
                else:
                    base = sp.simplify(f_expr * g_expr)
                f_num = sp.lambdify(x, base, "math")
                num_der = (f_num(xf + h) - f_num(xf - h)) / (2*h)
                sym_der = float(sp.N(val, 20))
                # allow moderate tolerance
                if not (math.isfinite(num_der) and math.isfinite(sym_der)):
                    continue
                if abs(num_der - sym_der) > 1e-4 * (1.0 + abs(sym_der)):
                    continue
            except Exception:
                # if lambdify fails (e.g., due to complex logs), skip
                continue
        elif op_name == "box":
            # check second derivative numerically
            try:
                h = 1e-4
                xf = float(sp.N(x0, 20))
                base = sp.simplify(f_expr.subs(x, g_expr))
                f_num = sp.lambdify(x, base, "math")
                num_dd = (f_num(xf + h) - 2*f_num(xf) + f_num(xf - h)) / (h*h)
                sym_dd = float(sp.N(val, 20))
                if not (math.isfinite(num_dd) and math.isfinite(sym_dd)):
                    continue
                if abs(num_dd - sym_dd) > 5e-3 * (1.0 + abs(sym_dd)):
                    continue
            except Exception:
                continue

        problem = render_problem(op_symbol, op_def, f_expr, g_expr, x0)
        ans_json = safe_rational_or_real_to_json(val)
        answer = wrap_double_brackets(ans_json)
        explanation = render_explanation(op_symbol, op_name, f_expr, g_expr, op_expr, x0, val)

        used_signatures.add(sig)
        return {"problem": problem, "answer": answer, "explanation": explanation}

    raise RuntimeError("在采样上限内未能生成合格题目。")


def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
        seed = int(req["seed"])
        count = int(req["count"])
    except Exception as e:
        print(f"输入 JSON 解析失败：{e}", file=sys.stderr)
        sys.exit(1)

    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    used = set()
    items: List[Dict[str, Any]] = []
    for _ in range(count):
        item = make_item(rng, used)
        # basic non-empty check
        if not item["problem"] or not item["answer"]:
            raise RuntimeError("生成了空题面或空答案")
        items.append(item)

    sys.stdout.write(json.dumps(items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()