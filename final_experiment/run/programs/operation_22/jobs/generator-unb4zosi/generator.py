import sys, json, random
from dataclasses import dataclass
import sympy as sp

# ----------------------------
# Utilities
# ----------------------------

def to_latex(expr):
    return sp.latex(sp.simplify(expr))

def wrap_answer_latex(latex_str):
    return f"[[{latex_str}]]"

def pick_nonzero_int(rng, lo, hi, forbid=None):
    if forbid is None:
        forbid = set()
    for _ in range(200):
        v = rng.randint(lo, hi)
        if v != 0 and v not in forbid:
            return v
    raise RuntimeError("Failed to sample nonzero int")

def pick_int(rng, lo, hi, forbid=None):
    if forbid is None:
        forbid = set()
    for _ in range(200):
        v = rng.randint(lo, hi)
        if v not in forbid:
            return v
    raise RuntimeError("Failed to sample int")

def rand_choice(rng, seq):
    return seq[rng.randrange(len(seq))]

def json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False)

# ----------------------------
# Problem model: custom operation f■g = df/dx + dg/dx
# Generate multiple families with real structural variety.
# ----------------------------

x, y = sp.symbols('x y')

@dataclass(frozen=True)
class Instance:
    f_expr: sp.Expr
    g_expr: sp.Expr
    problem_text: str
    answer_value: str
    explanation: str
    signature: str

def build_problem_text(f_expr, g_expr, language="zh"):
    # Render expressions into LaTeX
    f_ltx = to_latex(f_expr)
    g_ltx = to_latex(g_expr)

    if language == "zh":
        return (
            "你将使用如下自定义运算规则计算：\n\n"
            "定义运算：\n"
            "\\[\n"
            "f\\,\u25a0\\,g=\\frac{\\partial f}{\\partial x}+\\frac{\\partial g}{\\partial x}.\n"
            "\\]\n\n"
            "已知：\n"
            f"\\[\n f(x,y)={f_ltx},\\quad g(x,y)={g_ltx}.\n\\]\n\n"
            "求：\\(f\\,\u25a0\\,g\\)。\n"
            "请用 LaTeX 作答，并将最终结果用双中括号包裹，例如：[[...]]。"
        )
    else:
        return (
            "Using the custom operation:\n"
            "\\[\n"
            "f\\,\u25a0\\,g=\\frac{\\partial f}{\\partial x}+\\frac{\\partial g}{\\partial x}.\n"
            "\\]\n\n"
            f"Given \\(f(x,y)={f_ltx}\\), \\(g(x,y)={g_ltx}\\). Compute \\(f\\,\u25a0\\,g\\).\n"
            "Answer in LaTeX, wrapped like [[...]]."
        )

def compute_answer_and_explain(f_expr, g_expr, language="zh"):
    dfx = sp.diff(f_expr, x)
    dgx = sp.diff(g_expr, x)
    res = sp.simplify(dfx + dgx)

    if language == "zh":
        explanation = (
            "按定义：\\(f\\,\u25a0\\,g=\\frac{\\partial f}{\\partial x}+\\frac{\\partial g}{\\partial x}\\)。\n\n"
            f"先求偏导：\\(\\frac{{\\partial f}}{{\\partial x}}={to_latex(dfx)}\\)。\n"
            f"再求偏导：\\(\\frac{{\\partial g}}{{\\partial x}}={to_latex(dgx)}\\)。\n\n"
            f"相加得：\\(f\\,\u25a0\\,g={to_latex(res)}\\)。"
        )
    else:
        explanation = (
            "By definition: \\(f\\,\u25a0\\,g=\\frac{\\partial f}{\\partial x}+\\frac{\\partial g}{\\partial x}\\).\n\n"
            f"\\(\\frac{{\\partial f}}{{\\partial x}}={to_latex(dfx)}\\), "
            f"\\(\\frac{{\\partial g}}{{\\partial x}}={to_latex(dgx)}\\).\n\n"
            f"Thus \\(f\\,\u25a0\\,g={to_latex(res)}\\)."
        )

    return res, explanation

def cross_check_numeric(f_expr, g_expr, res_expr, rng):
    # independent validation by finite differences at random points (avoid singularities)
    # Compare d/dx via central difference vs sympy value for several points.
    for _ in range(5):
        xv = pick_int(rng, -3, 3)
        yv = pick_nonzero_int(rng, -3, 3)
        subs = {x: sp.Rational(xv), y: sp.Rational(yv)}
        # avoid domain issues: check denominators not zero
        try:
            fval = sp.simplify(f_expr.subs(subs))
            gval = sp.simplify(g_expr.subs(subs))
        except Exception:
            continue

        # central difference for each function in x
        h = sp.Rational(1, 1000)
        subs_p = {x: subs[x] + h, y: subs[y]}
        subs_m = {x: subs[x] - h, y: subs[y]}
        try:
            fd = sp.simplify((f_expr.subs(subs_p) - f_expr.subs(subs_m)) / (2*h))
            gd = sp.simplify((g_expr.subs(subs_p) - g_expr.subs(subs_m)) / (2*h))
            approx = sp.N(fd + gd, 30)
            exact = sp.N(res_expr.subs(subs), 30)
        except Exception:
            continue

        # allow small tolerance
        if abs(complex(approx) - complex(exact)) > 1e-7:
            raise AssertionError("Numeric cross-check failed")

def make_family_A(rng, language):
    # Rational / polynomial mix: (a*x + b*y + c)/(d*y + e) + polynomial in x,y
    a = pick_nonzero_int(rng, -4, 4)
    b = pick_int(rng, -4, 4)
    c = pick_int(rng, -4, 4)
    d = pick_nonzero_int(rng, -3, 3)
    e = pick_int(rng, -3, 3)
    # ensure denominator not identically 0
    denom = d*y + e
    f_expr = (a*x + b*y + c) / denom

    p = pick_nonzero_int(rng, -3, 3)
    q = pick_int(rng, -3, 3)
    r = pick_int(rng, -3, 3)
    n = rand_choice(rng, [2, 3, 4])
    g_expr = p*x**n + q*x*y + r*y**2

    problem_text = build_problem_text(f_expr, g_expr, language)
    res, expl = compute_answer_and_explain(f_expr, g_expr, language)
    cross_check_numeric(f_expr, g_expr, res, rng)

    sig = f"A|{sp.srepr(sp.simplify(f_expr))}|{sp.srepr(sp.simplify(g_expr))}"
    return Instance(
        f_expr=f_expr,
        g_expr=g_expr,
        problem_text=problem_text,
        answer_value=wrap_answer_latex(to_latex(res)),
        explanation=expl,
        signature=sig
    )

def make_family_B(rng, language):
    # Product/quotient with y in denominator: f = (x^m)*(alpha*y+beta)/(gamma*y^k) + delta
    m = rand_choice(rng, [1, 2, 3])
    k = rand_choice(rng, [1, 2])
    alpha = pick_nonzero_int(rng, -4, 4)
    beta = pick_int(rng, -4, 4)
    gamma = pick_nonzero_int(rng, -4, 4)
    delta = pick_int(rng, -3, 3)

    f_expr = (x**m) * (alpha*y + beta) / (gamma * y**k) + delta

    # g includes trig/exp/log combo but still differentiable wrt x
    choice = rand_choice(rng, ["trig", "exp", "log", "mix"])
    A = pick_nonzero_int(rng, -3, 3)
    B = pick_nonzero_int(rng, -3, 3)
    C = pick_int(rng, -3, 3)

    if choice == "trig":
        g_expr = A*sp.sin(B*x + C) + (pick_int(rng, -3, 3))*y
    elif choice == "exp":
        g_expr = A*sp.exp(B*x) + (pick_int(rng, -3, 3))*x*y
    elif choice == "log":
        # ensure argument > 0 is not required symbolically; use log(x^2+...) to be safe
        t = pick_nonzero_int(rng, 1, 4)
        g_expr = A*sp.log(x**2 + t) + (pick_int(rng, -3, 3))*y**2
    else:
        g_expr = A*sp.exp(B*x) + pick_nonzero_int(rng, -3, 3)*sp.cos(x + C) + pick_int(rng, -3, 3)*y

    problem_text = build_problem_text(f_expr, g_expr, language)
    res, expl = compute_answer_and_explain(f_expr, g_expr, language)
    cross_check_numeric(f_expr, g_expr, res, rng)

    sig = f"B|{sp.srepr(sp.simplify(f_expr))}|{sp.srepr(sp.simplify(g_expr))}"
    return Instance(
        f_expr=f_expr,
        g_expr=g_expr,
        problem_text=problem_text,
        answer_value=wrap_answer_latex(to_latex(res)),
        explanation=expl,
        signature=sig
    )

def make_family_C(rng, language):
    # Piecewise-free but with sqrt/power in x: f = (a*x^2 + b)/(c*y + d) + e*x
    a = pick_nonzero_int(rng, -4, 4)
    b = pick_int(rng, -5, 5)
    c = pick_nonzero_int(rng, -4, 4)
    d = pick_int(rng, -4, 4)
    e = pick_int(rng, -3, 3)
    f_expr = (a*x**2 + b) / (c*y + d) + e*x

    # g uses power of (x + s*y + t) with n>=2
    s = pick_int(rng, -3, 3)
    t = pick_int(rng, -3, 3)
    n = rand_choice(rng, [2, 3, 4, 5])
    u = pick_nonzero_int(rng, -3, 3)
    v = pick_int(rng, -3, 3)
    g_expr = u*(x + s*y + t)**n + v*y

    problem_text = build_problem_text(f_expr, g_expr, language)
    res, expl = compute_answer_and_explain(f_expr, g_expr, language)
    cross_check_numeric(f_expr, g_expr, res, rng)

    sig = f"C|{sp.srepr(sp.simplify(f_expr))}|{sp.srepr(sp.simplify(g_expr))}"
    return Instance(
        f_expr=f_expr,
        g_expr=g_expr,
        problem_text=problem_text,
        answer_value=wrap_answer_latex(to_latex(res)),
        explanation=expl,
        signature=sig
    )

def generate_one(rng, language):
    makers = [make_family_A, make_family_B, make_family_C]
    maker = rand_choice(rng, makers)
    return maker(rng, language)

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    # user-specified config
    # (provided to the generator program via the chat prompt; we set it here as constant)
    output_language = "zh"

    results = []
    seen = set()
    attempts = 0
    max_attempts = 50 * count + 200

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            inst = generate_one(rng, output_language)
        except Exception as e:
            print(f"[warn] generation failed: {e}", file=sys.stderr)
            continue

        if inst.signature in seen:
            continue
        seen.add(inst.signature)

        results.append({
            "problem": inst.problem_text,
            "answer": inst.answer_value,
            "explanation": inst.explanation
        })

    if len(results) != count:
        raise RuntimeError(f"Unable to generate enough unique problems: {len(results)}/{count}")

    sys.stdout.write(json_dumps(results))

if __name__ == "__main__":
    main()