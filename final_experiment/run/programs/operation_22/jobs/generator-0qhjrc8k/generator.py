import sys, json, random
import sympy as sp

x, y = sp.symbols("x y")

# ---------- formatting helpers ----------

def s(expr):
    return sp.simplify(expr)

def latex(expr):
    # keep it simple and fast
    return sp.latex(s(expr))

def wrap(latex_str):
    return f"[[{latex_str}]]"

def rand_int(rng, lo, hi, nonzero=False):
    for _ in range(200):
        v = rng.randint(lo, hi)
        if nonzero and v == 0:
            continue
        return v
    raise RuntimeError("rand_int failed")

def choice(rng, seq):
    return seq[rng.randrange(len(seq))]

def build_problem_text(f_expr, g_expr, lang="zh"):
    f_ltx = latex(f_expr)
    g_ltx = latex(g_expr)
    if lang == "zh":
        return (
            "使用如下自定义运算：\n\n"
            "定义：\n"
            "\\[\n"
            "f\\,\u25a0\\,g=\\frac{\\partial f}{\\partial x}+\\frac{\\partial g}{\\partial x}.\n"
            "\\]\n\n"
            "已知：\n"
            f"\\[\n f(x,y)={f_ltx},\\quad g(x,y)={g_ltx}.\n\\]\n\n"
            "求：\\(f\\,\u25a0\\,g\\)。请用 LaTeX 作答，并用双中括号包裹：[[...]]。"
        )
    else:
        return (
            "Custom operation:\n"
            "\\[\n"
            "f\\,\u25a0\\,g=\\frac{\\partial f}{\\partial x}+\\frac{\\partial g}{\\partial x}.\n"
            "\\]\n\n"
            f"Given \\(f(x,y)={f_ltx}\\), \\(g(x,y)={g_ltx}\\). Compute \\(f\\,\u25a0\\,g\\). "
            "Answer in LaTeX wrapped as [[...]]."
        )

def compute(f_expr, g_expr):
    # single pass derivatives; simplify at the end
    return s(sp.diff(f_expr, x) + sp.diff(g_expr, x))

def explain(f_expr, g_expr, res, lang="zh"):
    dfx = sp.diff(f_expr, x)
    dgx = sp.diff(g_expr, x)
    if lang == "zh":
        return (
            "按定义：\\(f\\,\u25a0\\,g=\\frac{\\partial f}{\\partial x}+\\frac{\\partial g}{\\partial x}\\)。\n\n"
            f"\\(\\frac{{\\partial f}}{{\\partial x}}={latex(dfx)}\\)，"
            f"\\(\\frac{{\\partial g}}{{\\partial x}}={latex(dgx)}\\)。\n\n"
            f"相加并化简得：\\(f\\,\u25a0\\,g={latex(res)}\\)。"
        )
    else:
        return (
            "By definition: \\(f\\,\u25a0\\,g=\\frac{\\partial f}{\\partial x}+\\frac{\\partial g}{\\partial x}\\).\n\n"
            f"\\(\\frac{{\\partial f}}{{\\partial x}}={latex(dfx)}\\), "
            f"\\(\\frac{{\\partial g}}{{\\partial g}}{{\\partial x}}={latex(dgx)}\\).\n\n"
            f"Sum and simplify: \\(f\\,\u25a0\\,g={latex(res)}\\)."
        )

# ---------- fast numeric cross-check (very limited) ----------

def numeric_check(f_expr, g_expr, res_expr, rng):
    # 2 trials only, no heavy N(), and skip if substitution fails
    for _ in range(2):
        xv = rand_int(rng, -2, 2, nonzero=False)
        yv = rand_int(rng, -2, 2, nonzero=True)
        subs = {x: sp.Rational(xv), y: sp.Rational(yv)}
        try:
            exact = s(res_expr.subs(subs))
        except Exception:
            continue

        h = sp.Rational(1, 200)  # coarse but fine for sanity
        subs_p = {x: subs[x] + h, y: subs[y]}
        subs_m = {x: subs[x] - h, y: subs[y]}
        try:
            fd = s((f_expr.subs(subs_p) - f_expr.subs(subs_m)) / (2 * h))
            gd = s((g_expr.subs(subs_p) - g_expr.subs(subs_m)) / (2 * h))
            approx = s(fd + gd)
        except Exception:
            continue

        # compare as rationals if possible; else compare floats quickly
        if exact.is_rational and approx.is_rational:
            if exact != approx:
                raise AssertionError("numeric_check failed (rational mismatch)")
        else:
            ev = float(sp.N(exact, 20))
            av = float(sp.N(approx, 20))
            if abs(ev - av) > 1e-4:
                raise AssertionError("numeric_check failed (float mismatch)")

# ---------- instance families (kept algebraic to stay fast) ----------

def family_A(rng):
    # f = (a*x + b*y + c)/(d*y + e), g = p*x^n + q*x*y + r*y^2
    a = rand_int(rng, -4, 4, nonzero=True)
    b = rand_int(rng, -4, 4)
    c = rand_int(rng, -4, 4)
    d = rand_int(rng, -3, 3, nonzero=True)
    e = rand_int(rng, -3, 3)
    denom = d * y + e
    f_expr = (a * x + b * y + c) / denom

    p = rand_int(rng, -3, 3, nonzero=True)
    q = rand_int(rng, -3, 3)
    r = rand_int(rng, -3, 3)
    n = choice(rng, [2, 3, 4])
    g_expr = p * x**n + q * x * y + r * y**2
    return f_expr, g_expr

def family_B(rng):
    # f = (x^m)*(alpha*y+beta)/(gamma*y^k) + delta, g = polynomial in x and y
    m = choice(rng, [1, 2, 3])
    k = choice(rng, [1, 2])
    alpha = rand_int(rng, -4, 4, nonzero=True)
    beta = rand_int(rng, -4, 4)
    gamma = rand_int(rng, -4, 4, nonzero=True)
    delta = rand_int(rng, -3, 3)
    f_expr = (x**m) * (alpha * y + beta) / (gamma * y**k) + delta

    A = rand_int(rng, -4, 4, nonzero=True)
    B = rand_int(rng, -3, 3)
    C = rand_int(rng, -3, 3)
    n = choice(rng, [2, 3, 4, 5])
    g_expr = A * (x + B)**n + C * x * y
    return f_expr, g_expr

def family_C(rng):
    # f = (a*x^2 + b)/(c*y + d) + e*x, g = u*(x + s*y + t)^n + v*x
    a = rand_int(rng, -4, 4, nonzero=True)
    b = rand_int(rng, -5, 5)
    c = rand_int(rng, -4, 4, nonzero=True)
    d = rand_int(rng, -4, 4)
    e = rand_int(rng, -3, 3)
    f_expr = (a * x**2 + b) / (c * y + d) + e * x

    u = rand_int(rng, -3, 3, nonzero=True)
    s_ = rand_int(rng, -3, 3)
    t = rand_int(rng, -3, 3)
    n = choice(rng, [2, 3, 4])
    v = rand_int(rng, -3, 3)
    g_expr = u * (x + s_ * y + t) ** n + v * x
    return f_expr, g_expr

def generate_one(rng):
    fam = choice(rng, [family_A, family_B, family_C])
    return fam(rng)

# ---------- main generator ----------

def main():
    inp = json.load(sys.stdin)
    seed = int(inp["seed"])
    count = int(inp["count"])
    rng = random.Random(seed)

    lang = "zh"

    out = []
    seen = set()

    # cap attempts to avoid runaway time; these are easy to generate uniquely
    max_attempts = 20 * count + 50
    attempts = 0

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            f_expr, g_expr = generate_one(rng)
            res = compute(f_expr, g_expr)

            # quick sanity check
            numeric_check(f_expr, g_expr, res, rng)

            sig = (sp.srepr(s(f_expr)), sp.srepr(s(g_expr)))
            if sig in seen:
                continue
            seen.add(sig)

            prob = build_problem_text(f_expr, g_expr, lang)
            ans = wrap(latex(res))
            exp = explain(f_expr, g_expr, res, lang)

            out.append({"problem": prob, "answer": ans, "explanation": exp})
        except Exception as e:
            print(f"[warn] skipped instance due to: {e}", file=sys.stderr)
            continue

    if len(out) != count:
        raise RuntimeError(f"生成失败：仅生成 {len(out)}/{count} 道题（已尝试 {attempts} 次）")

    sys.stdout.write(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()