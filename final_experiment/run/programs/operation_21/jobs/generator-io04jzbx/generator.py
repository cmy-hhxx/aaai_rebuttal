import sys, json, math, random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

import sympy as sp


# ----------------------------
# Core generator: double integral with custom operator
# ----------------------------

@dataclass(frozen=True)
class IntegralProblem:
    problem: str
    answer: Any
    explanation: str


def _to_pretty_pi_rational(r: sp.Rational) -> str:
    """Render a rational multiple of pi, e.g., 3*pi/4."""
    num = int(r.p)
    den = int(r.q)
    if num == 0:
        return "0"
    if den == 1:
        if num == 1:
            return "π"
        elif num == -1:
            return "-π"
        else:
            return f"{num}π"
    else:
        # num*pi/den
        if num == 1:
            return f"π/{den}"
        elif num == -1:
            return f"-π/{den}"
        else:
            return f"{num}π/{den}"


def _fmt_bound(v: sp.Expr) -> str:
    """Format bound in Chinese statement; use π."""
    v = sp.simplify(v)
    if v == sp.pi:
        return "π"
    if v.is_Rational:
        return str(v)
    # Rational * pi
    if v.is_Mul and sp.pi in v.free_symbols.union({sp.pi}):
        # try get v/pi
        coeff = sp.simplify(v / sp.pi)
        if coeff.is_Rational:
            return _to_pretty_pi_rational(coeff)
    # handle pi/2 etc
    if v.is_Pow:
        return str(v)
    # general fallback with π symbol
    s = str(v).replace("pi", "π")
    return s


def _sympy_to_text(expr: sp.Expr) -> str:
    s = sp.sstr(expr)
    s = s.replace("pi", "π")
    # Make * a bit more readable in Chinese text
    s = s.replace("*", "·")
    return s


def _pick_nonzero_int(rng: random.Random, lo: int, hi: int) -> int:
    while True:
        k = rng.randint(lo, hi)
        if k != 0:
            return k


def _sample_rect_bounds(rng: random.Random) -> Tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]:
    """
    Sample rectangle bounds:
      x in [ax, bx], y in [ay, by]
    Choose from rational multiples of pi or small integers, ensuring proper order.
    """
    def sample_endpoint():
        kind = rng.choice(["pi", "int"])
        if kind == "int":
            return sp.Integer(rng.randint(0, 4))
        else:
            den = rng.choice([2, 3, 4, 6])
            num = rng.randint(0, den)  # 0..den => 0..pi
            return sp.Rational(num, den) * sp.pi

    # Ensure non-degenerate ranges
    for _ in range(200):
        ax = sample_endpoint()
        bx = sample_endpoint()
        ay = sample_endpoint()
        by = sample_endpoint()
        if sp.simplify(bx - ax) == 0 or sp.simplify(by - ay) == 0:
            continue
        # order
        if sp.N(bx) < sp.N(ax):
            ax, bx = bx, ax
        if sp.N(by) < sp.N(ay):
            ay, by = by, ay
        # avoid extreme huge symbolic complexity
        return ax, bx, ay, by
    raise RuntimeError("Failed to sample rectangle bounds.")


def _build_family_A(rng: random.Random) -> Dict[str, Any]:
    """
    Separable trig product:
      f(x,y) = A*sin(m x + p)*cos(n y + q) or A*cos(...)*sin(...)
    Rectangle bounds.
    """
    x, y = sp.symbols('x y', real=True)

    A = _pick_nonzero_int(rng, -5, 5)
    m = rng.randint(1, 4)
    n = rng.randint(1, 4)

    # phase shifts: multiples of pi/2 or 0
    phase_choices = [sp.Integer(0), sp.pi/2, sp.pi, 3*sp.pi/2]
    p = rng.choice(phase_choices)
    q = rng.choice(phase_choices)

    # choose form
    form = rng.choice(["sin_cos", "cos_sin", "sin_sin", "cos_cos"])
    if form == "sin_cos":
        fx = sp.sin(m*x + p)
        fy = sp.cos(n*y + q)
    elif form == "cos_sin":
        fx = sp.cos(m*x + p)
        fy = sp.sin(n*y + q)
    elif form == "sin_sin":
        fx = sp.sin(m*x + p)
        fy = sp.sin(n*y + q)
    else:
        fx = sp.cos(m*x + p)
        fy = sp.cos(n*y + q)

    f = sp.Integer(A) * fx * fy
    ax, bx, ay, by = _sample_rect_bounds(rng)

    return dict(x=x, y=y, f=f, ax=ax, bx=bx, ay=ay, by=by, family="A")


def _build_family_B(rng: random.Random) -> Dict[str, Any]:
    """
    Polynomial-exponential/separable:
      f(x,y) = (a*x + b)*(c*y + d)  or  (a*x^2 + b)*exp(k y) etc.
    Rectangle bounds.
    """
    x, y = sp.symbols('x y', real=True)
    kind = rng.choice(["bilinear", "polyexp", "polytrig"])

    ax, bx, ay, by = _sample_rect_bounds(rng)

    if kind == "bilinear":
        a = _pick_nonzero_int(rng, -4, 4)
        b = rng.randint(-3, 3)
        c = _pick_nonzero_int(rng, -4, 4)
        d = rng.randint(-3, 3)
        f = (a*x + b) * (c*y + d)
    elif kind == "polyexp":
        a = _pick_nonzero_int(rng, -3, 3)
        b = rng.randint(-3, 3)
        k = _pick_nonzero_int(rng, -3, 3)
        f = (a*x**2 + b*x + rng.randint(-2, 2)) * sp.exp(k*y)
    else:  # polytrig
        a = _pick_nonzero_int(rng, -3, 3)
        m = rng.randint(1, 4)
        f = (a*x + rng.randint(-2, 2)) * sp.sin(m*y)

    return dict(x=x, y=y, f=f, ax=ax, bx=bx, ay=ay, by=by, family="B", kind=kind)


def _build_family_C(rng: random.Random) -> Dict[str, Any]:
    """
    Non-separable but still exactly integrable:
      f(x,y)=sin(m x + n y) or cos(m x - n y) or exp(a x + b y).
    """
    x, y = sp.symbols('x y', real=True)
    choice = rng.choice(["sin_linear", "cos_linear", "exp_linear"])
    ax, bx, ay, by = _sample_rect_bounds(rng)

    if choice == "sin_linear":
        m = _pick_nonzero_int(rng, -4, 4)
        n = _pick_nonzero_int(rng, -4, 4)
        p = rng.choice([0, sp.pi/2, sp.pi])
        f = sp.sin(m*x + n*y + p)
    elif choice == "cos_linear":
        m = _pick_nonzero_int(rng, -4, 4)
        n = _pick_nonzero_int(rng, -4, 4)
        p = rng.choice([0, sp.pi/2, sp.pi])
        f = sp.cos(m*x - n*y + p)
    else:
        a = _pick_nonzero_int(rng, -3, 3)
        b = _pick_nonzero_int(rng, -3, 3)
        f = sp.exp(a*x + b*y)

    # Scale optionally
    scale = rng.choice([1, 1, 2, -1, 3, -2])
    f = sp.Integer(scale) * f
    return dict(x=x, y=y, f=f, ax=ax, bx=bx, ay=ay, by=by, family="C", kind=choice)


def _compute_integral(data: Dict[str, Any]) -> sp.Expr:
    x, y, f = data["x"], data["y"], data["f"]
    ax, bx, ay, by = data["ax"], data["bx"], data["ay"], data["by"]
    # integrate dy then dx
    inner = sp.integrate(f, (y, ay, by))
    res = sp.integrate(inner, (x, ax, bx))
    res_s = sp.simplify(res)
    return res_s


def _cross_check_numeric(data: Dict[str, Any], exact: sp.Expr) -> None:
    """Independent-ish check: numeric quadrature by sampling grid (Riemann sum) vs exact."""
    x, y, f = data["x"], data["y"], data["f"]
    ax, bx, ay, by = data["ax"], data["bx"], data["ay"], data["by"]

    axf = float(sp.N(ax))
    bxf = float(sp.N(bx))
    ayf = float(sp.N(ay))
    byf = float(sp.N(by))
    # If bounds are too large/small, still handle.
    nx = 40
    ny = 40
    dx = (bxf - axf) / nx
    dy = (byf - ayf) / ny

    f_lam = sp.lambdify((x, y), f, "math")

    s = 0.0
    # midpoint rule
    for i in range(nx):
        xm = axf + (i + 0.5) * dx
        for j in range(ny):
            ym = ayf + (j + 0.5) * dy
            s += f_lam(xm, ym)
    approx = s * dx * dy
    exact_f = float(sp.N(exact))
    # tolerance scaled
    tol = 1e-3 * (1.0 + abs(exact_f))
    if not (math.isfinite(approx) and math.isfinite(exact_f)):
        raise RuntimeError("Non-finite numeric check.")
    if abs(approx - exact_f) > 50 * tol:
        # Not necessarily wrong (oscillatory functions), but flag for resampling by raising
        raise RuntimeError(f"Numeric cross-check failed: approx={approx}, exact={exact_f}")


def _render_problem_zh(data: Dict[str, Any]) -> str:
    f = data["f"]
    ax, bx, ay, by = data["ax"], data["bx"], data["ay"], data["by"]

    fx_txt = _sympy_to_text(f)
    ax_t, bx_t, ay_t, by_t = map(_fmt_bound, [ax, bx, ay, by])

    # Operator definition and ask
    return (
        "你将使用如下自定义运算符来计算二重积分：\n\n"
        "定义：f◆D = ∬_D f(x, y) dx dy。\n\n"
        f"已知 f(x,y) = {fx_txt}，积分区域 D 为矩形：{ax_t} ≤ x ≤ {bx_t}，{ay_t} ≤ y ≤ {by_t}。\n"
        "计算 f◆D 的值。"
    )


def _render_explanation_zh(data: Dict[str, Any], exact: sp.Expr) -> str:
    x, y, f = data["x"], data["y"], data["f"]
    ax, bx, ay, by = data["ax"], data["bx"], data["ay"], data["by"]

    # show two-step integration
    inner = sp.integrate(f, (y, ay, by))
    outer = sp.integrate(inner, (x, ax, bx))
    inner_s = sp.simplify(inner)
    outer_s = sp.simplify(outer)

    ax_t, bx_t, ay_t, by_t = map(_fmt_bound, [ax, bx, ay, by])

    return (
        "按定义计算二重积分：\n"
        f"f◆D = ∬_D f(x,y) dx dy = ∫_{ax_t}^{bx_t} ∫_{ay_t}^{by_t} f(x,y) dy dx。\n\n"
        f"先对 y 积分：\n"
        f"∫_{ay_t}^{by_t} f(x,y) dy = { _sympy_to_text(inner_s) }。\n\n"
        f"再对 x 积分：\n"
        f"∫_{ax_t}^{bx_t} ({ _sympy_to_text(inner_s) }) dx = { _sympy_to_text(outer_s) }。\n\n"
        f"因此 f◆D = { _sympy_to_text(sp.simplify(exact)) }。"
    )


def _make_one(rng: random.Random) -> IntegralProblem:
    builders = [_build_family_A, _build_family_B, _build_family_C]
    # try multiple times to avoid overly nasty numeric cross-check failures
    for _ in range(80):
        data = rng.choice(builders)(rng)
        try:
            exact = _compute_integral(data)
            # avoid unevaluated Integral
            if isinstance(exact, sp.Integral) or exact.has(sp.Integral):
                continue
            exact_s = sp.simplify(exact)

            # numeric cross-check (raises if fails)
            _cross_check_numeric(data, exact_s)

            prob = _render_problem_zh(data)
            expl = _render_explanation_zh(data, exact_s)

            # answer as JSON value: if sympy Rational/Integer -> int/float? keep exact string for pi etc.
            # Prefer exact symbolic string to avoid precision loss.
            ans = _sympy_to_text(exact_s)

            return IntegralProblem(problem=prob, answer=ans, explanation=expl)
        except Exception:
            continue
    raise RuntimeError("Failed to generate a valid integral problem after many attempts.")


def generate(seed: int, count: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    out: List[Dict[str, Any]] = []
    seen = set()

    attempts = 0
    while len(out) < count:
        attempts += 1
        if attempts > 5000:
            raise RuntimeError(f"Generation stalled: produced {len(out)}/{count}.")
        item = _make_one(rng)
        key = (item.problem, str(item.answer))
        if key in seen:
            continue
        seen.add(key)
        out.append({"problem": item.problem, "answer": item.answer, "explanation": item.explanation})
    return out


def main():
    try:
        raw = sys.stdin.read()
        obj = json.loads(raw if raw.strip() else "{}")
        seed = int(obj["seed"])
        count = int(obj["count"])
        if count <= 0:
            raise ValueError("count must be a positive integer.")
        res = generate(seed, count)
        sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()