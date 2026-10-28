import sys, json, math, random, re
from fractions import Fraction
import sympy as sp

# ---------------------------
# Utility: formatting and validation
# ---------------------------

def is_pos_int(x: int) -> bool:
    return isinstance(x, int) and x > 0

def fmt_sqrt_int(n: int) -> str:
    return f"\\sqrt{{{n}}}"

def fmt_sympy_expr(expr: sp.Expr) -> str:
    """Format sympy expression to required LaTeX-like string:
       - powers as a^b
       - sqrt as \sqrt{...}
       - keep as simplified as possible but do NOT expand into decimals
    """
    expr = sp.simplify(expr)

    # Convert to a string with sqrt
    # sympy's sstr prints sqrt(n) as sqrt(n); we need \sqrt{n}
    s = sp.sstr(expr)

    # Replace sqrt(...)
    def repl_sqrt(m):
        inside = m.group(1)
        return f"\\sqrt{{{inside}}}"
    s = re.sub(r"sqrt\(([^()]+)\)", repl_sqrt, s)

    # Replace ** with ^
    s = s.replace("**", "^")

    # sympy prints Rational as e.g. 3/2; that's ok.
    return s

def op_expr(a: int, b: int) -> sp.Expr:
    """a % b = a^b + sqrt(a*b), with a,b positive integers."""
    assert is_pos_int(a) and is_pos_int(b)
    return sp.Integer(a) ** sp.Integer(b) + sp.sqrt(sp.Integer(a) * sp.Integer(b))

def op_value_as_string(a: int, b: int) -> str:
    return fmt_sympy_expr(op_expr(a, b))

def unique_solution_check_integer(eq_expr: sp.Eq, var: sp.Symbol, domain_min=1, domain_max=200):
    """Check integer solutions in a bounded positive range. Return list of solutions."""
    sols = []
    for x in range(domain_min, domain_max + 1):
        if sp.simplify(eq_expr.lhs.subs(var, x) - eq_expr.rhs) == 0:
            sols.append(x)
    return sols

# ---------------------------
# Problem families
# ---------------------------

def gen_family_compute(rng: random.Random):
    """
    Family A: compute a%b directly.
    """
    a = rng.randint(2, 20)
    b = rng.randint(2, 7)
    # avoid too trivial duplicates
    expr = op_expr(a, b)
    ans = f"[[{fmt_sympy_expr(expr)}]]"

    problem = (
        "定义新的运算：\n"
        "对正整数 a,b，规定 a%b = a^b + \\sqrt{ab}。\n\n"
        f"计算：{a}%{b}。\n"
        "若答案含根号，请写成 \\sqrt{x} 的形式（x 为根号内的数）。\n"
        "请将答案用双中括号包裹，如 [[你的答案]]。"
    )
    explanation = (
        f"按定义：{a}%{b} = {a}^{b} + \\sqrt{{{a}·{b}}}。\n"
        f"其中 {a}^{b} = {a**b}，且 \\sqrt{{{a}·{b}}} = \\sqrt{{{a*b}}}。\n"
        f"所以答案为 [[{fmt_sympy_expr(expr)}]]。"
    )
    return problem, ans, explanation

def gen_family_solve_x_percent_1(rng: random.Random):
    """
    Family B: given X%1 = N, solve X (unique positive integer).
    Since X%1 = X^1 + sqrt(X*1) = X + sqrt(X).
    We construct N by choosing t so that X=t^2 gives N=t^2 + t.
    """
    t = rng.randint(2, 25)
    x = t * t
    n = x + t  # t^2 + t
    var = sp.Symbol('X', integer=True, positive=True)
    eq = sp.Eq(var + sp.sqrt(var), n)

    # Verify uniqueness in reasonable range
    sols = unique_solution_check_integer(eq, var, 1, 2000)
    if sols != [x]:
        # Fallback: enforce by resampling upstream; here raise to trigger retry
        raise ValueError(f"Non-unique or missing solution for X%1={n}, sols={sols}")

    problem = (
        "定义新的运算：\n"
        "对正整数 a,b，规定 a%b = a^b + \\sqrt{ab}。\n\n"
        f"若 X%1 = {n}，求正整数 X。\n"
        "答案只需给出数字，并用双中括号包裹，如 [[你的答案]]。"
    )
    ans = f"[[{x}]]"
    explanation = (
        "由定义：X%1 = X^1 + \\sqrt{X·1} = X + \\sqrt{X}。\n"
        f"因此方程为 X + \\sqrt{{X}} = {n}。\n"
        f"注意到 {n} = {t}^2 + {t}，令 \\sqrt{{X}} = {t} 可得 X = {t}^2 = {x}，代回：{x}+\\sqrt{{{x}}}={x}+{t}={n} 成立。\n"
        f"且在正整数范围内该解唯一，所以 X = {x}。"
    )
    return problem, ans, explanation

def gen_family_solve_x_percent_b(rng: random.Random):
    """
    Family C: given X%b = N, solve X (unique positive integer) by construction.
    For b=1 or 2 only, we can ensure uniqueness by choosing X to make sqrt term integer
    and keep search range small.
    We'll use b=2: X%2 = X^2 + sqrt(2X). Choose X=2t^2 => sqrt(2X)=sqrt(4t^2)=2t.
    Then N = (2t^2)^2 + 2t = 4t^4 + 2t.
    """
    b = 2
    t = rng.randint(2, 12)
    x = 2 * t * t
    n = x * x + 2 * t

    var = sp.Symbol('X', integer=True, positive=True)
    eq = sp.Eq(var**2 + sp.sqrt(2*var), n)
    sols = unique_solution_check_integer(eq, var, 1, 5000)
    if sols != [x]:
        raise ValueError(f"Non-unique or missing solution for X%2={n}, sols={sols}")

    problem = (
        "定义新的运算：\n"
        "对正整数 a,b，规定 a%b = a^b + \\sqrt{ab}。\n\n"
        f"若 X%2 = {n}，求正整数 X。\n"
        "答案只需给出数字，并用双中括号包裹，如 [[你的答案]]。"
    )
    ans = f"[[{x}]]"
    explanation = (
        "由定义：X%2 = X^2 + \\sqrt{2X}。\n"
        f"方程为 X^2 + \\sqrt{{2X}} = {n}。\n"
        f"构造验证：取 X={x} 时，X^2={x}^2={x*x}，且 2X=2·{x}={2*x}，\\sqrt{{2X}}=\\sqrt{{{2*x}}}={2*t}。\n"
        f"因此左边 = {x*x} + {2*t} = {n}，成立。\n"
        "再在正整数范围内枚举核验仅此一解，所以 X 为该值。"
    )
    return problem, ans, explanation

def gen_family_compare(rng: random.Random):
    """
    Family D: compare two custom-operation results.
    Ask which is larger, output one of: "A", "B", or "=" wrapped.
    """
    a1 = rng.randint(2, 12)
    b1 = rng.randint(2, 6)
    a2 = rng.randint(2, 12)
    b2 = rng.randint(2, 6)

    e1 = sp.N(op_expr(a1, b1), 30)
    e2 = sp.N(op_expr(a2, b2), 30)
    if abs(float(e1 - e2)) < 1e-12:
        comp = "="
    elif e1 > e2:
        comp = "A"
    else:
        comp = "B"

    problem = (
        "定义新的运算：\n"
        "对正整数 a,b，规定 a%b = a^b + \\sqrt{ab}。\n\n"
        f"比较下列两式大小：\n"
        f"A = {a1}%{b1}，B = {a2}%{b2}。\n"
        "若 A>B 输出 A；若 A<B 输出 B；若相等输出 =。\n"
        "请将输出用双中括号包裹，如 [[A]]。"
    )

    ans = f"[[{comp}]]"
    explanation = (
        f"A = {a1}^{b1} + \\sqrt{{{a1*b1}}} = {a1**b1} + {fmt_sqrt_int(a1*b1)}。\n"
        f"B = {a2}^{b2} + \\sqrt{{{a2*b2}}} = {a2**b2} + {fmt_sqrt_int(a2*b2)}。\n"
        "比较两者数值大小可得结论（幂项增长很快，必要时再比较根号项），因此输出为 "
        f"[[{comp}]]。"
    )
    return problem, ans, explanation

# ---------------------------
# Main generator with retries, dedup, self-check
# ---------------------------

def generate_one(rng: random.Random):
    families = [
        gen_family_compute,
        gen_family_solve_x_percent_1,
        gen_family_solve_x_percent_b,
        gen_family_compare,
    ]
    # Weighted choice
    weights = [0.45, 0.25, 0.20, 0.10]
    r = rng.random() * sum(weights)
    acc = 0.0
    for f, w in zip(families, weights):
        acc += w
        if r <= acc:
            return f(rng)
    return families[-1](rng)

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    out = []
    seen = set()
    max_attempts = 2000
    attempts = 0

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            problem, answer, explanation = generate_one(rng)
        except Exception as e:
            print(f"[stderr] generation attempt failed: {e}", file=sys.stderr)
            continue

        if not problem or not isinstance(problem, str):
            continue
        if not explanation or not isinstance(explanation, str):
            continue
        if not answer or not isinstance(answer, str):
            continue
        # basic answer format check: must be [[...]]
        if not (answer.startswith("[[") and answer.endswith("]]")):
            continue

        key = problem.strip()
        if key in seen:
            continue
        seen.add(key)

        out.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    if len(out) < count:
        print(f"[stderr] Could only generate {len(out)}/{count} items after {attempts} attempts.", file=sys.stderr)
        # Fail hard to avoid returning insufficient count
        raise SystemExit(1)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()