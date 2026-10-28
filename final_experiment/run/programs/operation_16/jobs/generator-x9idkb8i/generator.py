import sys, json, random, math
from typing import List, Dict, Any, Tuple, Optional

import sympy as sp


# ------------------------- Utilities -------------------------

def _latex_wrap(expr) -> str:
    """Return LaTeX string wrapped in [[...]] as required by seed style."""
    return f"[[{sp.latex(sp.simplify(expr))}]]"


def _safe_int(rng: random.Random, a: int, b: int, exclude: Optional[set] = None) -> int:
    exclude = exclude or set()
    for _ in range(200):
        v = rng.randint(a, b)
        if v not in exclude:
            return v
    # fallback deterministic
    for v in range(a, b + 1):
        if v not in exclude:
            return v
    raise RuntimeError("No integer available for sampling.")


def _choose(rng: random.Random, seq):
    return seq[rng.randrange(len(seq))]


def _sym_simplify(expr):
    return sp.simplify(sp.together(sp.cancel(expr)))


# ------------------------- Expression factories -------------------------

x = sp.Symbol('x')

def poly_expr(rng: random.Random, deg_min=1, deg_max=5, coeff_min=-5, coeff_max=6, must_nonzero=True) -> sp.Expr:
    deg = rng.randint(deg_min, deg_max)
    coeffs = []
    # ensure leading coefficient nonzero
    lead = _safe_int(rng, coeff_min, coeff_max, exclude={0}) if must_nonzero else rng.randint(coeff_min, coeff_max)
    coeffs.append(lead)
    for _ in range(deg):
        coeffs.append(rng.randint(coeff_min, coeff_max))
    # build a_deg x^deg + ... + a0
    expr = 0
    for i, a in enumerate(coeffs):
        power = deg - i
        expr += a * x**power
    return sp.expand(expr)

def monomial_expr(rng: random.Random) -> sp.Expr:
    a = _safe_int(rng, -6, 6, exclude={0})
    n = rng.randint(0, 6)
    return a * x**n

def exp_expr(rng: random.Random) -> sp.Expr:
    # e^{k x} or e^{k x + b}
    k = _safe_int(rng, -4, 4, exclude={0})
    b = rng.randint(-3, 3)
    if b == 0:
        return sp.exp(k*x)
    return sp.exp(k*x + b)

def trig_expr(rng: random.Random) -> sp.Expr:
    # sin(kx+b), cos(kx+b)
    k = _safe_int(rng, -5, 5, exclude={0})
    b = rng.choice([0, 0, 0, rng.randint(-3, 3)])  # bias to 0
    inner = k*x + b
    if rng.random() < 0.5:
        return sp.sin(inner)
    else:
        return sp.cos(inner)

def log_expr(rng: random.Random) -> sp.Expr:
    # ln(ax + b), ensure a !=0
    a = _safe_int(rng, -5, 5, exclude={0})
    b = rng.randint(-5, 5)
    return sp.log(a*x + b)

def rational_expr(rng: random.Random) -> sp.Expr:
    # (ax+b)/(cx+d), ensure denominator not identically 0
    a = _safe_int(rng, -6, 6, exclude={0})
    b = rng.randint(-6, 6)
    c = _safe_int(rng, -6, 6, exclude={0})
    d = rng.randint(-6, 6)
    return (a*x + b)/(c*x + d)

def power_expr(rng: random.Random) -> sp.Expr:
    # (ax+b)^n with n>=2
    a = _safe_int(rng, -4, 4, exclude={0})
    b = rng.randint(-4, 4)
    n = rng.randint(2, 5)
    return (a*x + b)**n

def mixed_expr(rng: random.Random) -> sp.Expr:
    """Create a moderately varied expression with manageable derivative."""
    # pick a base type, sometimes sum of two terms
    factories = [poly_expr, monomial_expr, exp_expr, trig_expr, rational_expr, power_expr, log_expr]
    f1 = _choose(rng, factories)
    expr1 = f1(rng)
    if rng.random() < 0.40:
        f2 = _choose(rng, factories)
        expr2 = f2(rng)
        op = rng.choice([1, -1])
        expr = expr1 + op*expr2
    else:
        expr = expr1
    return sp.simplify(expr)


# ------------------------- Custom operations -------------------------

def op_plusprime(f: sp.Expr, g: sp.Expr, point) -> sp.Expr:
    """f □ g = f'(x) + g'(x), evaluate at x=point."""
    fp = sp.diff(f, x)
    gp = sp.diff(g, x)
    val = sp.simplify(fp.subs(x, point) + gp.subs(x, point))
    return val

def op_minusprime(f: sp.Expr, g: sp.Expr, point) -> sp.Expr:
    """f △ g = f'(x) - g'(x), evaluate at x=point."""
    fp = sp.diff(f, x)
    gp = sp.diff(g, x)
    val = sp.simplify(fp.subs(x, point) - gp.subs(x, point))
    return val

def op_weighted(f: sp.Expr, g: sp.Expr, point, a: int, b: int) -> sp.Expr:
    """f ⊠ g = a f'(x) + b g'(x) at x=point."""
    fp = sp.diff(f, x)
    gp = sp.diff(g, x)
    val = sp.simplify(a*fp.subs(x, point) + b*gp.subs(x, point))
    return val

def op_at_diffpoints(f: sp.Expr, g: sp.Expr, p, q) -> sp.Expr:
    """f ★ g = f'(p) + g'(q) (derivatives evaluated at different points)."""
    fp = sp.diff(f, x)
    gp = sp.diff(g, x)
    return sp.simplify(fp.subs(x, p) + gp.subs(x, q))


# ------------------------- Validation helpers -------------------------

def is_defined_real_at(expr: sp.Expr, point) -> bool:
    """Heuristic domain check by asking SymPy if expression evaluates without complex/NaN/zoo."""
    try:
        v = sp.simplify(expr.subs(x, point))
        if v.has(sp.zoo) or v.has(sp.nan) or v.has(sp.oo) or v.has(-sp.oo):
            return False
        # avoid complex from log or fractional powers
        if sp.im(v).equals(0) is False:
            # if im(v) not provably 0, attempt numerical
            vn = complex(sp.N(v))
            if abs(vn.imag) > 1e-9:
                return False
        return True
    except Exception:
        return False

def is_derivative_defined(expr: sp.Expr, point) -> bool:
    try:
        d = sp.diff(expr, x)
        return is_defined_real_at(d, point)
    except Exception:
        return False

def independent_numeric_check(f: sp.Expr, g: sp.Expr, point, op_kind: str, extra=None) -> bool:
    """Cross-check by numerical evaluation separate from symbolic simplify."""
    try:
        fp = sp.diff(f, x)
        gp = sp.diff(g, x)
        if op_kind == "plus":
            sym = _sym_simplify(fp.subs(x, point) + gp.subs(x, point))
            num = sp.N(fp.subs(x, point)) + sp.N(gp.subs(x, point))
        elif op_kind == "minus":
            sym = _sym_simplify(fp.subs(x, point) - gp.subs(x, point))
            num = sp.N(fp.subs(x, point)) - sp.N(gp.subs(x, point))
        elif op_kind == "weighted":
            a, b = extra
            sym = _sym_simplify(a*fp.subs(x, point) + b*gp.subs(x, point))
            num = a*sp.N(fp.subs(x, point)) + b*sp.N(gp.subs(x, point))
        elif op_kind == "diffpoints":
            p, q = extra
            sym = _sym_simplify(fp.subs(x, p) + gp.subs(x, q))
            num = sp.N(fp.subs(x, p)) + sp.N(gp.subs(x, q))
        else:
            return False
        # compare numerically with tolerance
        sym_n = complex(sp.N(sym))
        num_n = complex(num)
        return (abs(sym_n.real - num_n.real) < 1e-7) and (abs(sym_n.imag - num_n.imag) < 1e-7)
    except Exception:
        return False


# ------------------------- Problem generation -------------------------

def render_expr(expr: sp.Expr) -> str:
    return sp.latex(expr)

def make_problem_text(lang: str, op_symbol: str, op_def_latex: str,
                      f_expr: sp.Expr, g_expr: sp.Expr, query: str) -> str:
    # Currently only zh required by user; keep extensible.
    if lang != "zh":
        lang = "zh"
    f_ltx = render_expr(f_expr)
    g_ltx = render_expr(g_expr)
    return (
        "你需要根据下面给出的“自定义运算”规则计算结果。\n\n"
        "### 运算规则\n"
        f"{op_def_latex}\n\n"
        "### 已知函数\n"
        f"1）$f(x)={f_ltx}$\n"
        f"2）$g(x)={g_ltx}$\n\n"
        f"### 问题\n"
        f"{query}\n\n"
        "请将最终答案用 LaTeX 表示，并用双层方括号包裹：[[...]]。"
    )

def generate_one(rng: random.Random, lang: str) -> Dict[str, Any]:
    # choose a family/variant (L2/L4 changes)
    variant = rng.choices(
        population=["plus_same_point", "minus_same_point", "weighted_same_point", "diff_points"],
        weights=[0.45, 0.20, 0.20, 0.15],
        k=1
    )[0]

    # sample expressions with constraints to keep solvable and defined
    for _ in range(400):
        f_expr = mixed_expr(rng)
        g_expr = mixed_expr(rng)

        # sample points
        point = rng.choice([-2, -1, 0, 1, 2, 3])
        p = rng.choice([-2, -1, 0, 1, 2])
        q = rng.choice([-1, 0, 1, 2, 3])

        # ensure derivatives defined
        if variant in ("plus_same_point", "minus_same_point", "weighted_same_point"):
            if not (is_derivative_defined(f_expr, point) and is_derivative_defined(g_expr, point)):
                continue
        else:
            if not (is_derivative_defined(f_expr, p) and is_derivative_defined(g_expr, q)):
                continue

        # define operation and compute answer
        if variant == "plus_same_point":
            op_symbol = "□"
            op_def = r"定义 $f\;□\;g = f'(x)+g'(x)$。"
            ans_expr = op_plusprime(f_expr, g_expr, point)
            if not independent_numeric_check(f_expr, g_expr, point, "plus"):
                continue
            query = f"计算 $f□g$ 在 $x={point}$ 时的值。"

            # explanation
            fp = sp.diff(f_expr, x)
            gp = sp.diff(g_expr, x)
            expl = (
                f"先求导：$f'(x)={sp.latex(fp)}$，$g'(x)={sp.latex(gp)}$。\n"
                f"按定义 $f□g=f'(x)+g'(x)$，代入 $x={point}$：\n"
                f"$f'( {point})+g'({point})={sp.latex(fp.subs(x, point))}+{sp.latex(gp.subs(x, point))}"
                f"={sp.latex(_sym_simplify(ans_expr))}$。"
            )

        elif variant == "minus_same_point":
            op_symbol = "△"
            op_def = r"定义 $f\;△\;g = f'(x)-g'(x)$。"
            ans_expr = op_minusprime(f_expr, g_expr, point)
            if not independent_numeric_check(f_expr, g_expr, point, "minus"):
                continue
            query = f"计算 $f△g$ 在 $x={point}$ 时的值。"
            fp = sp.diff(f_expr, x)
            gp = sp.diff(g_expr, x)
            expl = (
                f"求导得：$f'(x)={sp.latex(fp)}$，$g'(x)={sp.latex(gp)}$。\n"
                f"按定义 $f△g=f'(x)-g'(x)$，代入 $x={point}$：\n"
                f"$f'({point})-g'({point})={sp.latex(fp.subs(x, point))}-{sp.latex(gp.subs(x, point))}"
                f"={sp.latex(_sym_simplify(ans_expr))}$。"
            )

        elif variant == "weighted_same_point":
            op_symbol = "⊠"
            a = _safe_int(rng, -4, 4, exclude={0})
            b = _safe_int(rng, -4, 4, exclude={0})
            # avoid trivial scaling both same sign huge? keep manageable
            if abs(a) + abs(b) > 7:
                continue
            op_def = rf"定义 $f\;\,⊠\;\,g = {a}\,f'(x)+{b}\,g'(x)$。"
            ans_expr = op_weighted(f_expr, g_expr, point, a, b)
            if not independent_numeric_check(f_expr, g_expr, point, "weighted", extra=(a, b)):
                continue
            query = f"计算 $f⊠g$ 在 $x={point}$ 时的值。"
            fp = sp.diff(f_expr, x)
            gp = sp.diff(g_expr, x)
            expl = (
                f"先求导：$f'(x)={sp.latex(fp)}$，$g'(x)={sp.latex(gp)}$。\n"
                f"按定义 $f⊠g={a}f'(x)+{b}g'(x)$，代入 $x={point}$：\n"
                f"${a}f'({point})+{b}g'({point})="
                f"{a}\\cdot({sp.latex(fp.subs(x, point))})+{b}\\cdot({sp.latex(gp.subs(x, point))})"
                f"={sp.latex(_sym_simplify(ans_expr))}$。"
            )

        else:  # diff_points
            op_symbol = "★"
            op_def = r"定义 $f\;★\;g = f'(p)+g'(q)$（其中 $p,q$ 为题目给定常数）。"
            ans_expr = op_at_diffpoints(f_expr, g_expr, p, q)
            if not independent_numeric_check(f_expr, g_expr, None, "diffpoints", extra=(p, q)):
                continue
            query = f"已知本题取 $p={p}, q={q}$，计算 $f★g$ 的值。"
            fp = sp.diff(f_expr, x)
            gp = sp.diff(g_expr, x)
            expl = (
                f"求导：$f'(x)={sp.latex(fp)}$，$g'(x)={sp.latex(gp)}$。\n"
                f"按定义 $f★g=f'(p)+g'(q)$，代入 $p={p},q={q}$：\n"
                f"$f'({p})+g'({q})={sp.latex(fp.subs(x, p))}+{sp.latex(gp.subs(x, q))}"
                f"={sp.latex(_sym_simplify(ans_expr))}$。"
            )

        # ensure answer is not NaN/Inf/complex
        if not is_defined_real_at(ans_expr, 0):  # heuristic check on expr itself
            # (substituting x=0 doesn't matter; is_defined_real_at checks expression value directly if numeric,
            # but ans_expr is numeric already; subs won't change)
            pass
        try:
            z = sp.simplify(ans_expr)
            if z.has(sp.zoo) or z.has(sp.nan) or z.has(sp.oo) or z.has(-sp.oo):
                continue
            # keep answer reasonably sized in latex
            if len(sp.latex(z)) > 120:
                continue
        except Exception:
            continue

        problem = make_problem_text(lang, op_symbol, op_def, f_expr, g_expr, query)
        answer = _latex_wrap(ans_expr)
        return {"problem": problem, "answer": answer, "explanation": expl}

    raise RuntimeError("Failed to generate a valid problem after many attempts.")


def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count must be positive")
    except Exception as e:
        print(f"Invalid input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # user provided output_language in a separate JSON in conversation;
    # runtime input spec only includes seed/count, so fix to zh as requested.
    lang = "zh"

    rng = random.Random(seed)

    results: List[Dict[str, Any]] = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng, lang)
        except Exception as e:
            print(f"Generation attempt failed: {e}", file=sys.stderr)
            continue

        # deduplicate by problem text (strong enough)
        key = item["problem"]
        if key in seen:
            continue
        # basic sanity
        if not item["problem"].strip() or not str(item["answer"]).strip():
            continue

        seen.add(key)
        results.append(item)

    if len(results) < count:
        print(f"Could not generate enough unique problems. Generated {len(results)}/{count}.", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()