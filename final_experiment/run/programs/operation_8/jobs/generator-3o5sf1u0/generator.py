import sys, json, math, random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

import sympy as sp

# ----------------------------
# Custom operations definition
# ----------------------------
# a①b = sqrt(a) + b^2
# a②b = sqrt(a) * b
def op1(a, b):
    return sp.sqrt(a) + b**2

def op2(a, b):
    return sp.sqrt(a) * b

# ----------------------------
# Utilities
# ----------------------------
def to_latex_expr(expr) -> str:
    """Return LaTeX for a sympy expression, with \sqrt{} and \frac{}."""
    expr_s = sp.simplify(expr)
    return sp.latex(expr_s)

def wrap(ans: str) -> str:
    return f"[[{ans}]]"

def is_perfect_square_int(n: int) -> bool:
    if n < 0:
        return False
    r = int(math.isqrt(n))
    return r * r == n

def rational_int_value(expr) -> Optional[int]:
    """If expr simplifies to an integer, return it; else None."""
    expr_s = sp.simplify(expr)
    if expr_s.is_integer:
        return int(expr_s)
    return None

def ensure_unique_solutions(sol_list) -> List[sp.Expr]:
    uniq = []
    seen = set()
    for s in sol_list:
        ss = sp.simplify(s)
        key = sp.srepr(ss)
        if key not in seen:
            seen.add(key)
            uniq.append(ss)
    return uniq

# ----------------------------
# Problem families
# ----------------------------
@dataclass
class Generated:
    problem: str
    answer: Any
    explanation: str

def gen_part1_expression(rng: random.Random) -> Tuple[str, str, str]:
    """
    Generate a question of the form:
      计算 (A ① b) ② c
      or 计算 (A ② b) ① c
      or 计算 (A ① b) ① c
      or 计算 (A ② b) ② c
    Keep values small and ensure expression is well-defined.
    """
    A = rng.choice([0, 1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144])
    b = rng.randint(1, 9)
    c = rng.randint(1, 9)

    form = rng.choice(["(A①b)②c", "(A②b)①c", "(A①b)①c", "(A②b)②c"])

    if form == "(A①b)②c":
        expr1 = op1(A, b)
        expr = op2(expr1, c)
        steps = [
            f"先算 {A}①{b} = \\sqrt{{{A}}} + {b}^2 = {to_latex_expr(sp.sqrt(A))} + {b*b} = {to_latex_expr(expr1)}。",
            f"再算 ({to_latex_expr(expr1)})②{c} = \\sqrt{{{to_latex_expr(expr1)}}}\\times {c} = {to_latex_expr(expr)}。"
        ]
        problem_expr = f"( {A}①{b} )②{c}"
    elif form == "(A②b)①c":
        expr1 = op2(A, b)
        expr = op1(expr1, c)
        steps = [
            f"先算 {A}②{b} = \\sqrt{{{A}}}\\times {b} = {to_latex_expr(expr1)}。",
            f"再算 ({to_latex_expr(expr1)})①{c} = \\sqrt{{{to_latex_expr(expr1)}}} + {c}^2 = {to_latex_expr(expr)}。"
        ]
        problem_expr = f"( {A}②{b} )①{c}"
    elif form == "(A①b)①c":
        expr1 = op1(A, b)
        expr = op1(expr1, c)
        steps = [
            f"先算 {A}①{b} = \\sqrt{{{A}}} + {b}^2 = {to_latex_expr(expr1)}。",
            f"再算 ({to_latex_expr(expr1)})①{c} = \\sqrt{{{to_latex_expr(expr1)}}} + {c}^2 = {to_latex_expr(expr)}。"
        ]
        problem_expr = f"( {A}①{b} )①{c}"
    else:  # "(A②b)②c"
        expr1 = op2(A, b)
        expr = op2(expr1, c)
        steps = [
            f"先算 {A}②{b} = \\sqrt{{{A}}}\\times {b} = {to_latex_expr(expr1)}。",
            f"再算 ({to_latex_expr(expr1)})②{c} = \\sqrt{{{to_latex_expr(expr1)}}}\\times {c} = {to_latex_expr(expr)}。"
        ]
        problem_expr = f"( {A}②{b} )②{c}"

    ans_latex = wrap(to_latex_expr(expr))
    expl = "；".join(steps)
    return problem_expr, ans_latex, expl

def gen_part2_equation(rng: random.Random) -> Tuple[str, Any, str]:
    """
    Generate an equation involving X and operations, solvable with a unique real solution.
    Output answer as a plain number (can be integer or simplified rational/surd expression).
    We'll keep it usually integer by construction.

    Example patterns (choose one):
      1) k ② (X ① m) = T
      2) k ① (X ② m) = T
      3) (X ① m) ② k = T
      4) (X ② m) ① k = T

    We will construct by choosing an integer X, then computing T, then asking to solve.
    Need ensure square roots are defined: for op1, sqrt(a) requires a>=0.
    We'll pick X>=0 integer.
    """
    X_val = rng.randint(0, 80)
    m = rng.randint(1, 8)
    k = rng.randint(1, 9)
    pattern = rng.choice([1, 2, 3, 4])

    X = sp.Symbol('X', real=True)

    if pattern == 1:
        # k ② (X ① m) = sqrt(k) * (sqrt(X) + m^2)
        T = sp.simplify(op2(k, op1(X_val, m)))
        eq = sp.Eq(op2(k, op1(X, m)), T)
        # Solve; should be unique for X>=0 due to monotonic sqrt(X)
        sols = sp.solve(eq, X)
        sols = ensure_unique_solutions(sols)
        # keep real and >=0
        sols_real = [s for s in sols if sp.simplify(sp.im(s)) == 0]
        # filter by domain
        sols_good = []
        for s in sols_real:
            # quick numeric check
            try:
                sv = float(sp.N(s))
                if sv >= -1e-9:
                    sols_good.append(sp.simplify(s))
            except Exception:
                pass
        sols_good = ensure_unique_solutions(sols_good)
        # ensure our constructed X is among solutions
        if sp.Integer(X_val) not in [sp.simplify(s) for s in sols_good]:
            # fallback, but this should be rare; we can just set answer to X_val directly as constructed
            pass
        # uniqueness: prefer cases yielding exactly one admissible solution
        if len(sols_good) != 1:
            # Force a unique-solution by re-encoding: make it directly linear in sqrt(X)
            # Choose T to make sqrt(X) isolated:
            # sqrt(k)*(sqrt(X)+m^2)=sqrt(k)*(sqrt(X_val)+m^2)
            # This should yield X = X_val uniquely for X>=0.
            T = sp.simplify(sp.sqrt(k) * (sp.sqrt(X_val) + m**2))
            eq = sp.Eq(sp.sqrt(k) * (sp.sqrt(X) + m**2), T)
            sols_good = [sp.Integer(X_val)]
        answer = sols_good[0]
        problem = f"若 {k}②(X①{m}) = {to_latex_expr(T)}，求 X。"
        expl = (
            f"由定义：{k}②(Y)=\\sqrt{{{k}}}\\times Y，且 X①{m}=\\sqrt{{X}}+{m}^2。"
            f"所以方程为 \\sqrt{{{k}}}(\\sqrt{{X}}+{m*m}) = {to_latex_expr(T)}。"
            f"两边同除以 \\sqrt{{{k}}} 得 \\sqrt{{X}}+{m*m} = {to_latex_expr(sp.simplify(T/sp.sqrt(k)))}，"
            f"从而 \\sqrt{{X}} = {to_latex_expr(sp.simplify(T/sp.sqrt(k) - m*m))}，"
            f"故 X = {to_latex_expr(answer)}。"
        )
        return problem, wrap(to_latex_expr(answer)), expl

    if pattern == 2:
        # k ① (X ② m) = sqrt(k) + (sqrt(X)*m)^2 = sqrt(k) + X*m^2
        T = sp.simplify(op1(k, op2(X_val, m)))
        eq = sp.Eq(op1(k, op2(X, m)), T)
        sols = sp.solve(eq, X)
        sols = ensure_unique_solutions(sols)
        # should be unique linear in X
        sols_real = [s for s in sols if sp.simplify(sp.im(s)) == 0]
        if len(sols_real) != 1:
            # enforce by construction
            sols_real = [sp.Integer(X_val)]
        answer = sp.simplify(sols_real[0])
        problem = f"若 {k}①(X②{m}) = {to_latex_expr(T)}，求 X。"
        expl = (
            f"先化简：X②{m}=\\sqrt{{X}}\\times {m}。"
            f"因此 {k}①(X②{m})=\\sqrt{{{k}}}+(\\sqrt{{X}}\\times {m})^2"
            f"=\\sqrt{{{k}}}+{m*m}X。"
            f"令其等于 {to_latex_expr(T)}，得 {m*m}X={to_latex_expr(sp.simplify(T-sp.sqrt(k)))}，"
            f"所以 X={to_latex_expr(answer)}。"
        )
        return problem, wrap(to_latex_expr(answer)), expl

    if pattern == 3:
        # (X ① m) ② k = sqrt( sqrt(X) + m^2 ) * k
        T = sp.simplify(op2(op1(X_val, m), k))
        eq = sp.Eq(op2(op1(X, m), k), T)
        sols = sp.solve(eq, X)
        sols = ensure_unique_solutions(sols)
        sols_real = [s for s in sols if sp.simplify(sp.im(s)) == 0]
        sols_good = []
        for s in sols_real:
            try:
                sv = float(sp.N(s))
                if sv >= -1e-9:
                    sols_good.append(sp.simplify(s))
            except Exception:
                pass
        sols_good = ensure_unique_solutions(sols_good)
        if len(sols_good) != 1:
            # pick guaranteed-unique by setting k=1 to avoid extraneous? still monotone; but for safety:
            sols_good = [sp.Integer(X_val)]
        answer = sp.simplify(sols_good[0])
        problem = f"若 (X①{m})②{k} = {to_latex_expr(T)}，求 X。"
        expl = (
            f"(X①{m})=\\sqrt{{X}}+{m*m}，再代入②： (X①{m})②{k}=\\sqrt{{\\sqrt{{X}}+{m*m}}}\\times {k}。"
            f"令其等于 {to_latex_expr(T)}，两边同除以 {k} 得 "
            f"\\sqrt{{\\sqrt{{X}}+{m*m}}} = {to_latex_expr(sp.simplify(T/k))}。"
            f"两边平方：\\sqrt{{X}}+{m*m}={to_latex_expr(sp.simplify((T/k)**2))}，"
            f"故 \\sqrt{{X}}={to_latex_expr(sp.simplify((T/k)**2 - m*m))}，"
            f"再平方得 X={to_latex_expr(answer)}。"
        )
        return problem, wrap(to_latex_expr(answer)), expl

    # pattern == 4:
    # (X ② m) ① k = sqrt( sqrt(X)*m ) + k^2  -> involves 4th root, may give more complex solutions
    # We'll instead construct to keep integer by choosing X such that sqrt(X)*m is a perfect square.
    # Let sqrt(X)=t^2, X=t^4. Then sqrt(sqrt(X)*m)=sqrt(t^2*m)=t*sqrt(m). Not integer unless m square.
    # To keep simple, choose m as perfect square.
    m = rng.choice([1, 4, 9])
    t = rng.randint(0, 6)
    X_val = t**4
    k = rng.randint(1, 9)
    T = sp.simplify(op1(op2(X_val, m), k))
    # Now solve: sqrt( sqrt(X)*m ) + k^2 = T
    answer = sp.Integer(X_val)
    problem = f"若 (X②{m})①{k} = {to_latex_expr(T)}，求 X。"
    expl = (
        f"由定义：(X②{m})①{k}=\\sqrt{{X②{m}}}+{k}^2。且 X②{m}=\\sqrt{{X}}\\times {m}。"
        f"因此方程为 \\sqrt{{{m}\\sqrt{{X}}}}+{k*k} = {to_latex_expr(T)}。"
        f"移项得 \\sqrt{{{m}\\sqrt{{X}}}} = {to_latex_expr(sp.simplify(T-k*k))}。"
        f"两边平方：{m}\\sqrt{{X}} = {to_latex_expr(sp.simplify((T-k*k)**2))}，"
        f"再除以 {m} 得 \\sqrt{{X}} = {to_latex_expr(sp.simplify((T-k*k)**2/m))}，"
        f"两边再平方得到 X = {to_latex_expr(answer)}。"
    )
    return problem, wrap(to_latex_expr(answer)), expl

def compute_check_part1(expr_str: str) -> sp.Expr:
    """Parse our limited expression string and compute using op1/op2 to cross-check."""
    # expr_str format like "( A①b )②c" etc
    s = expr_str.replace(" ", "")
    # extract numbers and ops by simple parsing since structure is fixed with parentheses
    # pattern: (XopY)opZ where op in {①,②}
    if not (s.startswith("(") and ")" in s):
        raise ValueError("bad expr")
    inside, tail = s[1:].split(")", 1)
    # inside: A①b or A②b
    if "①" in inside:
        left, right = inside.split("①")
        first = ("①", int(left), int(right))
    elif "②" in inside:
        left, right = inside.split("②")
        first = ("②", int(left), int(right))
    else:
        raise ValueError("bad inside")

    if len(tail) < 2:
        raise ValueError("bad tail")
    op = tail[0]
    z = int(tail[1:])

    if first[0] == "①":
        v = op1(first[1], first[2])
    else:
        v = op2(first[1], first[2])

    if op == "①":
        return op1(v, z)
    elif op == "②":
        return op2(v, z)
    else:
        raise ValueError("bad op")

# ----------------------------
# Rendering
# ----------------------------
def make_problem(rng: random.Random, lang: str) -> Generated:
    # Two-part question like the seed, but values/forms vary.
    expr_str, ans1, expl1 = gen_part1_expression(rng)
    eq_str, ans2, expl2 = gen_part2_equation(rng)

    # Cross-check part1 by independent parser
    expr_sym = compute_check_part1(expr_str)
    if wrap(to_latex_expr(expr_sym)) != ans1:
        # If mismatch, use computed as source of truth (should not happen)
        ans1 = wrap(to_latex_expr(expr_sym))

    # Ensure part2 answer is consistent by substitution check
    # Extract numeric value if possible; else keep sympy exact
    X = sp.Symbol('X', real=True)
    # We'll numerically verify using the displayed equation string not easy; instead verify by regenerating
    # via explanation-equation patterns isn't robust. So we check by plugging into a recomputed equation
    # based on the equation text pattern recognition.
    # Minimal safe approach: parse based on known formats we created.
    def verify_equation(eq_text: str, x_val_expr: sp.Expr) -> bool:
        s = eq_text.replace(" ", "")
        # patterns:
        # 若 k②(X①m)=T
        # 若 k①(X②m)=T
        # 若 (X①m)②k=T
        # 若 (X②m)①k=T
        try:
            if "②(X①" in s:
                k = int(s.split("若")[1].split("②")[0])
                m = int(s.split("X①")[1].split(")")[0])
                T_ltx = s.split("=")[1].split("，")[0]
                T = sp.sympify(T_ltx.replace("\\sqrt", "sqrt").replace("{", "(").replace("}", ")"))
                lhs = op2(k, op1(x_val_expr, m))
                return sp.simplify(lhs - T) == 0
            if "①(X②" in s:
                k = int(s.split("若")[1].split("①")[0])
                m = int(s.split("X②")[1].split(")")[0])
                T_ltx = s.split("=")[1].split("，")[0]
                T = sp.sympify(T_ltx.replace("\\sqrt", "sqrt").replace("{", "(").replace("}", ")"))
                lhs = op1(k, op2(x_val_expr, m))
                return sp.simplify(lhs - T) == 0
            if "若(X①" in s and ")②" in s:
                m = int(s.split("若(X①")[1].split(")")[0])
                k = int(s.split(")②")[1].split("=")[0])
                T_ltx = s.split("=")[1].split("，")[0]
                T = sp.sympify(T_ltx.replace("\\sqrt", "sqrt").replace("{", "(").replace("}", ")"))
                lhs = op2(op1(x_val_expr, m), k)
                return sp.simplify(lhs - T) == 0
            if "若(X②" in s and ")①" in s:
                m = int(s.split("若(X②")[1].split(")")[0])
                k = int(s.split(")①")[1].split("=")[0])
                T_ltx = s.split("=")[1].split("，")[0]
                T = sp.sympify(T_ltx.replace("\\sqrt", "sqrt").replace("{", "(").replace("}", ")"))
                lhs = op1(op2(x_val_expr, m), k)
                return sp.simplify(lhs - T) == 0
        except Exception:
            return False
        return False

    ans2_expr = sp.sympify(ans2.strip()[2:-2].replace("\\sqrt", "sqrt").replace("{", "(").replace("}", ")"))
    if not verify_equation(eq_str, ans2_expr):
        # If verification fails due to sympify of LaTeX nuances, fall back to numeric check:
        try:
            # Extract numeric via sympy N and verify approximately using same parsing
            if not verify_equation(eq_str, sp.N(ans2_expr)):
                raise ValueError("equation verification failed")
        except Exception:
            # As last resort: keep answer but mark; however requirement disallows fake claims.
            # We'll regenerate at a higher level by raising to retry.
            raise RuntimeError("Failed to verify generated equation instance.")

    if lang == "zh":
        problem = (
            "定义两种新运算：\n"
            "a①b = \\sqrt{a} + b^2；\n"
            "a②b = \\sqrt{a}\\times b。\n\n"
            "1）计算 " + expr_str + " 。请用 LaTeX 表示答案，并用双中括号包裹，如 [[...]]。\n"
            "2）" + eq_str + " 只需给出 X 的值，并用双中括号包裹，如 [[...]]。"
        )
        explanation = (
            "第1问：" + expl1 + "\n"
            "第2问：" + expl2
        )
        answer = ans1 + "====" + ans2
    else:
        # Default to Chinese as per requirements (shouldn't happen)
        problem = (
            "定义两种新运算：a①b = \\sqrt{a} + b^2，a②b = \\sqrt{a}\\times b。\n"
            f"1) 计算 {expr_str}。\n2) {eq_str}"
        )
        explanation = f"1) {expl1}\n2) {expl2}"
        answer = ans1 + "====" + ans2

    return Generated(problem=problem, answer=answer, explanation=explanation)

# ----------------------------
# Main generation loop
# ----------------------------
def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))
    rng = random.Random(seed)

    # output_language is provided by caller in meta; but our runtime input only has seed/count.
    # As per instruction, language choice is preserved in program (fixed at build time).
    output_language = "zh"

    results: List[Dict[str, Any]] = []
    seen = set()
    attempts = 0
    max_attempts = max(200, count * 40)

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            g = make_problem(rng, output_language)
        except Exception as e:
            # retry on generation/verification failure
            continue

        key = (g.problem, str(g.answer))
        if key in seen:
            continue
        seen.add(key)
        results.append({"problem": g.problem, "answer": g.answer, "explanation": g.explanation})

    if len(results) < count:
        print(f"Failed to generate enough unique problems: got {len(results)}/{count}", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()