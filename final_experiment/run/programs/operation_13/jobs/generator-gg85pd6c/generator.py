import sys, json, random, math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

# Custom operation: a ⊕ b = a + b i  (complex number)
# Generate problems about evaluating expressions and solving for X in complex equations.

I = 1j

def c(a: int, b: int) -> complex:
    return complex(a, b)

def fmt_int(n: int) -> str:
    return str(n)

def fmt_complex(z: complex) -> str:
    a = int(round(z.real))
    b = int(round(z.imag))
    # Ensure integer formatting; generation guarantees ints.
    if b == 0:
        return f"{a}"
    if a == 0:
        if b == 1:
            return "i"
        if b == -1:
            return "-i"
        return f"{b}i"
    # a != 0 and b != 0
    sign = "+" if b > 0 else "-"
    bb = abs(b)
    if bb == 1:
        return f"{a}{sign}i"
    return f"{a}{sign}{bb}i"

def parseable_pair(a: int, b: int) -> str:
    return f"({a}⊕{b})"

def compute_q1(k: int, a: int, b: int, c1: int, d: int) -> complex:
    # k*(a⊕b) - (c1⊕d)
    return k * c(a, b) - c(c1, d)

def compute_q1_alt(k: int, a: int, b: int, c1: int, d: int) -> complex:
    # Independent route: separate real/imag parts
    real = k * a - c1
    imag = k * b - d
    return complex(real, imag)

def solve_q2_linear(A: Tuple[int, int], B: Tuple[int, int], m: int, target: Tuple[int, int]) -> int:
    # (A) + m*(X⊕B_im)?? Actually pattern: (p⊕q) + (X⊕r)*m = target
    # Here A=(p,q), B=(?, r) with unknown X and fixed imag r. So (X⊕r)=X+ri.
    # Solve for X integer.
    (p, q) = A
    (t_re, t_im) = target
    r = B[1]
    # Equation: (p+q i) + m*(X + r i) = t_re + t_im i
    # => real: p + mX = t_re ; imag: q + m r = t_im
    # X = (t_re - p)/m must be integer
    if (t_im - q) != m * r:
        raise ValueError("Inconsistent imaginary part, no solution.")
    num = t_re - p
    if num % m != 0:
        raise ValueError("X not integer.")
    return num // m

def solve_q2_check(A: Tuple[int, int], r: int, m: int, target: Tuple[int, int], X: int) -> bool:
    left = c(A[0], A[1]) + m * c(X, r)
    return int(round(left.real)) == target[0] and int(round(left.imag)) == target[1]

def rand_nonzero_int(rng: random.Random, lo: int, hi: int) -> int:
    while True:
        x = rng.randint(lo, hi)
        if x != 0:
            return x

@dataclass(frozen=True)
class Item:
    problem: str
    answer: Any
    explanation: str

def gen_item(rng: random.Random) -> Item:
    # Mix of two formats:
    # Type A: two-part question (evaluate expression; solve X)
    # Type B: only one of them, with different structure (to increase diversity)
    typ = rng.choices(["A", "B1", "B2"], weights=[0.55, 0.25, 0.20])[0]

    if typ == "A":
        # Part 1: k*(a⊕b) ± (c⊕d)
        k = rng.randint(2, 6)
        a = rng.randint(-6, 8)
        b = rng.randint(-6, 8)
        c1 = rng.randint(-6, 8)
        d = rng.randint(-6, 8)
        op = rng.choice(["-", "+"])
        if op == "-":
            z = k * c(a, b) - c(c1, d)
            z_alt = compute_q1_alt(k, a, b, c1, d)
            expr = f"{k}×{parseable_pair(a,b)}−{parseable_pair(c1,d)}"
            exp_line = f"{k}×({a}+{b}i)−({c1}+{d}i)=({k*a}-{c1})+({k*b}-{d})i={fmt_complex(z)}"
        else:
            z = k * c(a, b) + c(c1, d)
            z_alt = complex(k*a + c1, k*b + d)
            expr = f"{k}×{parseable_pair(a,b)}+{parseable_pair(c1,d)}"
            exp_line = f"{k}×({a}+{b}i)+({c1}+{d}i)=({k*a}+{c1})+({k*b}+{d})i={fmt_complex(z)}"
        if z != z_alt:
            raise AssertionError("Cross-check failed for Q1")

        # Part 2: (p⊕q) + m*(X⊕r) = target, choose X first to ensure integer
        m = rng.randint(2, 5)
        p = rng.randint(-8, 10)
        q = rng.randint(-8, 10)
        r = rng.randint(-8, 10)
        X = rng.randint(-10, 12)
        target_re = p + m * X
        target_im = q + m * r
        # verify
        if not solve_q2_check((p, q), r, m, (target_re, target_im), X):
            raise AssertionError("Construction check failed for Q2")

        # compute via solver and cross-check
        X_solved = solve_q2_linear((p, q), (0, r), m, (target_re, target_im))
        if X_solved != X:
            raise AssertionError("Solver cross-check failed for Q2")

        problem = (
            "你需要按如下自定义运算规则计算/求解：\n\n"
            "运算定义：a⊕b = a + b i（其中 i 为虚数单位）。\n\n"
            f"1）计算：{expr}。\n"
            "请将答案写成复数标准形式 a+bi（若虚部为 0 则写整数），并用 [[...]] 包裹。\n\n"
            f"2）若 {parseable_pair(p,q)} + {parseable_pair('X',r)}×{m} = {fmt_int(target_re)}+{fmt_int(target_im)}i，求 X（X 为整数）。\n"
            "请仅给出 X，并用 [[...]] 包裹。"
        )
        # For part 2, render (X⊕r) carefully:
        problem = problem.replace(parseable_pair('X', r), f"(X⊕{r})")

        answer = f"[[{fmt_complex(z)}]]====[[{X}]]"
        explanation = (
            "第1问：由 a⊕b=a+bi，先把 ⊕ 改写为复数，再做数乘与加减。\n"
            f"{exp_line}\n\n"
            "第2问：\n"
            f"(p⊕q)=({p}+{q}i)，(X⊕{r})=(X+{r}i)。\n"
            f"方程为：({p}+{q}i)+{m}(X+{r}i)=({p}+{m}X)+({q}+{m*r})i。\n"
            f"与 {target_re}+{target_im}i 对应比较实部：{p}+{m}X={target_re}，得 X=({target_re}-{p})/{m}={X}。"
        )
        return Item(problem=problem, answer=answer, explanation=explanation)

    elif typ == "B1":
        # Single evaluation with nested structure: (a⊕b)×n − (c⊕d)×m + (e⊕f)
        n = rng.randint(2, 5)
        m = rng.randint(2, 5)
        a, b = rng.randint(-7, 9), rng.randint(-7, 9)
        c1, d = rng.randint(-7, 9), rng.randint(-7, 9)
        e, f = rng.randint(-7, 9), rng.randint(-7, 9)
        z = n * c(a, b) - m * c(c1, d) + c(e, f)
        # independent compute
        z_alt = complex(n*a - m*c1 + e, n*b - m*d + f)
        if z != z_alt:
            raise AssertionError("Cross-check failed for B1")

        expr = f"{parseable_pair(a,b)}×{n}−{parseable_pair(c1,d)}×{m}+{parseable_pair(e,f)}"
        problem = (
            "按如下规则定义运算：a⊕b = a + b i（i 为虚数单位）。\n\n"
            f"计算：{expr}。\n"
            "请将答案写成复数标准形式 a+bi（若虚部为 0 则写整数），并用 [[...]] 包裹。"
        )
        answer = f"[[{fmt_complex(z)}]]"
        explanation = (
            "把每个 a⊕b 看成复数 a+bi：\n"
            f"({a}+{b}i)×{n}−({c1}+{d}i)×{m}+({e}+{f}i)\n"
            f"=({n*a}-{m*c1}+{e})+({n*b}-{m*d}+{f})i\n"
            f"={fmt_complex(z)}。"
        )
        return Item(problem=problem, answer=answer, explanation=explanation)

    else:  # B2
        # Solve X in: (u⊕v)×k + (X⊕r) = target  OR (u⊕v) + (X⊕r)×k = target
        form = rng.choice(["left_mul", "right_mul"])
        k = rng.randint(2, 6)
        u, v = rng.randint(-9, 9), rng.randint(-9, 9)
        r = rng.randint(-9, 9)
        X = rng.randint(-12, 12)

        if form == "left_mul":
            # (u⊕v)×k + (X⊕r) = target
            target = k * c(u, v) + c(X, r)
            target_re, target_im = int(target.real), int(target.imag)
            # Solve: X = target_re - k*u ; imag check: r = target_im - k*v
            X_s = target_re - k * u
            if (target_im - k * v) != r or X_s != X:
                # If mismatch due to rounding (shouldn't) or construction, fix by redefining X to computed
                X = X_s
                target = k * c(u, v) + c(X, r)
                target_re, target_im = int(target.real), int(target.imag)
            # Cross-check by substitution
            lhs = k * c(u, v) + c(X, r)
            if int(lhs.real) != target_re or int(lhs.imag) != target_im:
                raise AssertionError("B2 left_mul check failed")

            problem = (
                "已知自定义运算：a⊕b = a + b i（i 为虚数单位）。\n\n"
                f"若 {parseable_pair(u,v)}×{k} + (X⊕{r}) = {target_re}+{target_im}i，且 X 为整数，求 X。\n"
                "请用 [[...]] 包裹答案。"
            )
            answer = f"[[{X}]]"
            explanation = (
                f"({u}⊕{v})=({u}+{v}i)，所以左边为 {k}({u}+{v}i)+(X+{r}i)\n"
                f"=({k*u}+X)+({k*v}+{r})i。\n"
                f"与 {target_re}+{target_im}i 比较实部：{k*u}+X={target_re}，故 X={target_re}-{k*u}={X}。"
            )
            return Item(problem=problem, answer=answer, explanation=explanation)

        else:
            # (u⊕v) + (X⊕r)×k = target, enforce integer X
            target_re = u + k * X
            target_im = v + k * r
            # Solve with linear solver
            X_solved = solve_q2_linear((u, v), (0, r), k, (target_re, target_im))
            if X_solved != X:
                raise AssertionError("B2 right_mul solver mismatch")
            if not solve_q2_check((u, v), r, k, (target_re, target_im), X):
                raise AssertionError("B2 right_mul substitution failed")

            problem = (
                "已知自定义运算：a⊕b = a + b i（i 为虚数单位）。\n\n"
                f"若 {parseable_pair(u,v)} + (X⊕{r})×{k} = {target_re}+{target_im}i，且 X 为整数，求 X。\n"
                "请用 [[...]] 包裹答案。"
            )
            answer = f"[[{X}]]"
            explanation = (
                f"({u}⊕{v})=({u}+{v}i)，(X⊕{r})=(X+{r}i)。\n"
                f"左边：({u}+{v}i)+{k}(X+{r}i)=({u}+{k}X)+({v}+{k*r})i。\n"
                f"对比实部：{u}+{k}X={target_re} ⇒ X=({target_re}-{u})/{k}={X}。"
            )
            return Item(problem=problem, answer=answer, explanation=explanation)

def canonical_signature(problem: str, answer: Any) -> str:
    return f"{problem}||{json.dumps(answer, ensure_ascii=False, sort_keys=True)}"

def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    items: List[Item] = []
    seen = set()
    attempts = 0
    max_attempts = 20000

    while len(items) < count and attempts < max_attempts:
        attempts += 1
        try:
            it = gen_item(rng)
        except Exception as e:
            print(f"generation error: {e}", file=sys.stderr)
            continue
        sig = canonical_signature(it.problem, it.answer)
        if sig in seen:
            continue
        seen.add(sig)
        items.append(it)

    if len(items) < count:
        raise RuntimeError(f"Failed to generate enough unique items: {len(items)}/{count} after {attempts} attempts")

    out = [{"problem": it.problem, "answer": it.answer, "explanation": it.explanation} for it in items]
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=None))

if __name__ == "__main__":
    main()