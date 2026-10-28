import sys, json, random, math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

import sympy as sp


# ----------------------------
# Utilities
# ----------------------------

def wrap_double_brackets(s: str) -> str:
    return f"[[{s}]]"

def fmt_int(n: int) -> str:
    return str(n)

def fmt_sympy_expr(expr: sp.Expr) -> str:
    """Format expression with sqrt as \\sqrt{x} and no spaces.
    Keep exact forms; handle rationals and simple sums/products.
    """
    expr = sp.simplify(expr)
    # sympy's latex is good but uses \sqrt{} and \left; we want plain.
    # We'll implement a small custom mapper for common forms.
    # Fallback to sympy.sstr then adapt sqrt.
    s = sp.sstr(expr)
    # sympy prints sqrt(x) -> sqrt(x)
    s = s.replace("sqrt(", r"\sqrt{")
    # replace matching ')' for sqrt with '}'
    # naive but works if sqrt arguments are simple (we ensure so).
    out = []
    i = 0
    while i < len(s):
        if s.startswith(r"\sqrt{", i):
            out.append(r"\sqrt{")
            i += len(r"\sqrt{")
            depth = 1
            # original had "sqrt(" replaced; now we need to read until matching ')'
            # But we already replaced '(' with '{', so we should find the original ')'
            # Actually s still contains ')' because we only replaced "sqrt(" token.
            # Let's parse until first ')' at depth 1 for function argument.
            # This is safe for our constructed radicals.
            start = i
            while i < len(s) and s[i] != ')':
                i += 1
            out.append(s[start:i])
            out.append("}")
            if i < len(s) and s[i] == ')':
                i += 1
        else:
            out.append(s[i])
            i += 1
    s2 = "".join(out)
    s2 = s2.replace(" ", "")
    return s2

def choose_nonzero_int(rng: random.Random, lo: int, hi: int) -> int:
    while True:
        v = rng.randint(lo, hi)
        if v != 0:
            return v

def safe_sample(rng: random.Random, seq):
    return seq[rng.randrange(len(seq))]


# ----------------------------
# Core operation families
# ----------------------------

@dataclass
class OpRule:
    """Binary operation of the form (A + kB) * (pA + qB) or (A + kB) * (A + B) etc."""
    k: int
    p: int
    q: int
    # if p=q=0 and use_sum_ab=True then second factor is (A+B)
    use_sum_ab: bool = False

    def apply(self, A: int, B: int) -> int:
        if self.use_sum_ab:
            return (A + self.k * B) * (A + B)
        return (A + self.k * B) * (self.p * A + self.q * B)

    def render(self) -> str:
        if self.use_sum_ab:
            return f"A○B=(A+{self.k}B)×(A+B)"
        # handle signs for nice rendering
        def term(coeff, var):
            if coeff == 0:
                return "0"
            if coeff == 1:
                return var
            if coeff == -1:
                return f"-{var}"
            return f"{coeff}{var}"
        second = f"({term(self.p,'A')}+{term(self.q,'B')})"
        # simplify +-
        second = second.replace("+-", "-")
        return f"A○B=(A+{self.k}B)×{second}"

@dataclass
class ProblemItem:
    problem: str
    answer: Any
    explanation: str


# ----------------------------
# Solvers / generators for 3 sub-questions
# ----------------------------

def gen_q1_chain(rng: random.Random) -> Tuple[str, int, str]:
    """Compute chain like a○b○c with given operation; specify left-to-right explicitly."""
    # Use seed-like operation: (A+kB)*(A+B)
    k = rng.randint(2, 6)
    rule = OpRule(k=k, p=0, q=0, use_sum_ab=True)

    # choose small integers to keep numbers reasonable but nontrivial
    a = rng.randint(2, 12)
    b = rng.randint(1, 10)
    c = rng.randint(1, 10)
    # force some variety: sometimes negative
    if rng.random() < 0.25:
        b = -b
    if rng.random() < 0.15:
        c = -c

    first = rule.apply(a, b)
    final = rule.apply(first, c)

    problem = (
        "已定义自定义运算：\n"
        f"{rule.render()}，其中A、B为整数。\n\n"
        f"题1：按从左到右的顺序计算 ({a}○{b})○{c}。\n"
        "请把最终结果用双重方括号括起来，例如 [[123]]。"
    )
    answer = wrap_double_brackets(str(final))
    explanation = (
        f"先算：{a}○{b}=( {a}+{k}×{b})×({a}+{b})={a + k*b}×{a + b}={first}。\n"
        f"再算：{first}○{c}=( {first}+{k}×{c})×({first}+{c})={first + k*c}×{first + c}={final}。\n"
        f"所以答案为 {answer}。"
    )
    return problem, answer, explanation

def gen_q2_equation(rng: random.Random) -> Tuple[str, str, str]:
    """Solve equation like m ○ (X ○ n) = T under rule (A+kB)*(A+B)."""
    k = rng.randint(2, 7)
    rule = OpRule(k=k, p=0, q=0, use_sum_ab=True)

    # pick constants
    m = rng.randint(2, 10)
    n = rng.randint(1, 8)
    if rng.random() < 0.25:
        n = -n

    X = sp.Symbol('X', integer=True)  # but solutions may not be integer; allow symbolic
    inner = (X + k*n) * (X + n)  # X○n
    outer = (m + k*inner) * (m + inner)  # m○(X○n)

    # Choose a target by picking a nice X0 (possibly integer) then compute T
    X0 = rng.randint(-8, 8)
    if X0 == 0 and rng.random() < 0.5:
        X0 = 1
    inner0 = int(rule.apply(X0, n))
    T = int(rule.apply(m, inner0))

    # Now solve equation for X; might yield 0,1,2 solutions in integers; we allow all real solutions.
    eq = sp.Eq(outer, T)
    sols = sp.solve(eq, X, domain=sp.S.Complexes)  # exact
    # Filter to real
    real_sols = []
    for s in sols:
        s_simpl = sp.simplify(s)
        if s_simpl.is_real is True:
            real_sols.append(s_simpl)
        elif s_simpl.is_real is None:
            # attempt numeric test
            if abs(complex(sp.N(s_simpl)).imag) < 1e-10:
                real_sols.append(sp.nsimplify(sp.re(s_simpl)))
    # Make unique
    uniq = []
    for s in real_sols:
        if all(sp.simplify(s - t) != 0 for t in uniq):
            uniq.append(s)
    uniq = sorted(uniq, key=lambda e: float(sp.N(e)))

    # Ensure at least one solution and that X0 is included (for consistency)
    if not any(sp.simplify(s - X0) == 0 for s in uniq):
        # fallback: include X0 by construction; but if solver missed due to assumptions, recompute over rationals
        uniq.append(sp.Integer(X0))
        uniq = sorted(uniq, key=lambda e: float(sp.N(e)))

    ans_parts = [fmt_sympy_expr(s) for s in uniq]
    ans_str = "or".join(ans_parts)
    answer = wrap_double_brackets(ans_str)

    problem = (
        "已定义自定义运算：\n"
        f"{rule.render()}，其中A、B为整数。\n\n"
        f"题2：若 {m}○(X○{n})={T}，求X。\n"
        "若有多个解，用 'or' 连接；含根号写作 \\sqrt{{x}} 形式。\n"
        "请把最终答案用双重方括号括起来，例如 [[1or2]]。"
    )

    # Explanation: reduce to quadratic in X
    inner_expr = sp.expand(inner)
    outer_expr = sp.expand((m + k*inner) * (m + inner))
    poly = sp.expand(outer_expr - T)
    poly_s = sp.Poly(poly, X)

    explanation = (
        f"先表示内层：X○{n}=(X+{k}×{n})×(X+{n})={fmt_sympy_expr(inner_expr)}。\n"
        f"代入外层：{m}○(X○{n})=( {m}+{k}(X○{n}) )×( {m}+(X○{n}) )。\n"
        f"令其等于 {T}，得到关于X的方程：{fmt_sympy_expr(poly)}=0。\n"
        f"解得 X={ans_str}，因此答案为 {answer}。"
    )
    return problem, answer, explanation

def gen_q3_parameter_solve(rng: random.Random) -> Tuple[str, str, str]:
    """Given A○B=(A+kB)*(xA+yB), with fixed k, solve x,y from two equations."""
    k = rng.randint(2, 6)

    # Choose integer x,y then sample two (A,B) pairs such that system is solvable uniquely.
    x_true = choose_nonzero_int(rng, -3, 4)
    y_true = choose_nonzero_int(rng, -3, 4)

    # Ensure not both small in a degenerate way: avoid proportional equations
    # We'll pick two distinct (A,B) and solve linear system on (x,y) after dividing by (A+kB).
    def pick_pair():
        A = rng.randint(1, 9)
        B = rng.randint(1, 9)
        if rng.random() < 0.2:
            B = -B
        if rng.random() < 0.15:
            A = -A
        # avoid A+kB=0
        if A + k*B == 0:
            return None
        return A, B

    # sample pairs ensuring determinant nonzero for unique x,y
    for _ in range(200):
        p1 = pick_pair()
        p2 = pick_pair()
        if not p1 or not p2:
            continue
        A1,B1 = p1
        A2,B2 = p2
        if (A1,B1)==(A2,B2):
            continue
        det = A1*B2 - A2*B1
        if det == 0:
            continue
        # compute results
        R1 = (A1 + k*B1) * (x_true*A1 + y_true*B1)
        R2 = (A2 + k*B2) * (x_true*A2 + y_true*B2)
        # avoid too large
        if max(abs(R1), abs(R2)) > 2000:
            continue

        # Solve back to verify uniqueness
        x,y = sp.symbols('x y', integer=True)
        eq1 = sp.Eq((A1 + k*B1)*(x*A1 + y*B1), R1)
        eq2 = sp.Eq((A2 + k*B2)*(x*A2 + y*B2), R2)
        sol = sp.solve([eq1, eq2], [x, y], dict=True)
        if len(sol) != 1:
            continue
        sol0 = sol[0]
        if sp.simplify(sol0[x] - x_true)!=0 or sp.simplify(sol0[y]-y_true)!=0:
            continue

        answer = wrap_double_brackets(f"x={int(x_true)},y={int(y_true)}")
        problem = (
            "题3：现在修改运算规则。\n"
            f"定义 A○B=(A+{k}B)×(xA+yB)，其中x、y为参数，A、B为整数。\n"
            f"已知 {A1}○{B1}={R1}，且 {A2}○{B2}={R2}，求x与y（均为整数）。\n"
            "请按 [[x=整数,y=整数]] 的格式作答。"
        )

        # Explanation: turn into linear system
        C1 = A1 + k*B1
        C2 = A2 + k*B2
        # Since C1,C2 != 0, divide both equations
        rhs1 = sp.Rational(R1, C1)
        rhs2 = sp.Rational(R2, C2)
        explanation = (
            f"由定义：{A1}○{B1}=( {A1}+{k}×{B1})×(x·{A1}+y·{B1})={R1}。\n"
            f"因 {A1}+{k}×{B1}={C1}≠0，两边同除以{C1}：得到 {A1}x+{B1}y={fmt_sympy_expr(rhs1)}。\n"
            f"同理 {A2}+{k}×{B2}={C2}≠0，得到 {A2}x+{B2}y={fmt_sympy_expr(rhs2)}。\n"
            f"解该二元一次方程组，得 x={x_true}, y={y_true}，故答案为 {answer}。"
        )
        return problem, answer, explanation

    raise RuntimeError("Failed to generate a valid parameter-solve instance for Q3.")


# ----------------------------
# Whole problem (3 parts) generator
# ----------------------------

def generate_one(rng: random.Random, idx: int, lang: str) -> ProblemItem:
    # We only implement zh as requested; keep structure modular.
    p1, a1, e1 = gen_q1_chain(rng)
    p2, a2, e2 = gen_q2_equation(rng)
    p3, a3, e3 = gen_q3_parameter_solve(rng)

    problem = (
        f"以下为三道互相独立的小题（均为自定义运算○）。\n\n"
        f"{p1}\n\n"
        f"{p2}\n\n"
        f"{p3}"
    )
    answer = f"{a1}===={a2}===={a3}"
    explanation = (
        "题1解析：\n" + e1 + "\n\n"
        "题2解析：\n" + e2 + "\n\n"
        "题3解析：\n" + e3
    )
    return ProblemItem(problem=problem, answer=answer, explanation=explanation)


# ----------------------------
# Dedup / validation
# ----------------------------

def normalize_problem_text(s: str) -> str:
    return " ".join(s.split())

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])

    rng = random.Random(seed)

    items: List[ProblemItem] = []
    seen = set()

    attempts = 0
    max_attempts = max(200, count * 50)

    while len(items) < count and attempts < max_attempts:
        attempts += 1
        try:
            it = generate_one(rng, len(items), "zh")
        except Exception as ex:
            print(f"[gen_error] {ex}", file=sys.stderr)
            continue

        key = normalize_problem_text(it.problem)
        if key in seen:
            continue
        seen.add(key)

        # basic non-empty checks
        if not it.problem.strip() or it.answer is None or not str(it.answer).strip():
            print("[validation_error] empty fields", file=sys.stderr)
            continue

        items.append(it)

    if len(items) < count:
        raise RuntimeError(f"Only generated {len(items)} items out of requested {count} after {attempts} attempts.")

    out = [{"problem": it.problem, "answer": it.answer, "explanation": it.explanation} for it in items]
    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()