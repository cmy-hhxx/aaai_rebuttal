import sys, json, math, random
from fractions import Fraction

# We generate problems about a custom operation defined via an integral.
# Use exact rational arithmetic (Fraction) to avoid floating issues.
#
# Families:
# A) polynomial integrand: f(x)=k*x^n, operation a★b = ∫_a^b f(x) dx
#    Questions: compute a★b; solve for a given a★c = T (unique when monotone).
# B) affine integrand: f(x)=m*x+p, operation a★b = ∫_a^b f(x) dx
#    Questions: compute; solve for a given a★c = T (quadratic -> 0/1/2 solutions).
#
# Ensure statement self-contained, sufficient, and answer verifiable.
# Provide explanation with key algebra steps and substitution check.

def frac_to_str(fr: Fraction) -> str:
    if fr.denominator == 1:
        return str(fr.numerator)
    else:
        return f"{fr.numerator}/{fr.denominator}"

def num_to_json(fr: Fraction):
    # For answers, keep as int if integral, else as string fraction.
    if fr.denominator == 1:
        return fr.numerator
    return frac_to_str(fr)

def wrap_double_brackets(s: str) -> str:
    return f"[[{s}]]"

def integral_kxn(k: int, n: int, a: int, b: int) -> Fraction:
    # ∫_a^b k x^n dx = k/(n+1) * (b^{n+1}-a^{n+1})
    return Fraction(k, n + 1) * (Fraction(b) ** (n + 1) - Fraction(a) ** (n + 1))

def integral_mx_p(m: int, p: int, a: int, b: int) -> Fraction:
    # ∫_a^b (m x + p) dx = m/2 (b^2 - a^2) + p (b-a)
    return Fraction(m, 2) * (Fraction(b) ** 2 - Fraction(a) ** 2) + Fraction(p) * (Fraction(b - a))

def is_perfect_square_int(x: int) -> bool:
    if x < 0:
        return False
    r = int(math.isqrt(x))
    return r * r == x

def solve_quadratic_int_roots(A: int, B: int, C: int):
    # Solve A a^2 + B a + C = 0 over rationals, but we will construct
    # instances where roots are integers (or a single integer root).
    if A == 0:
        if B == 0:
            return []
        # linear
        if (-C) % B == 0:
            return [Fraction(-C, B)]
        return [Fraction(-C, B)]
    D = B * B - 4 * A * C
    if D < 0:
        return []
    if not is_perfect_square_int(D):
        # allow rational sqrt? We avoid in generation; but keep fallback empty.
        return []
    s = int(math.isqrt(D))
    r1 = Fraction(-B + s, 2 * A)
    r2 = Fraction(-B - s, 2 * A)
    # unique roots
    if r1 == r2:
        return [r1]
    return sorted([r1, r2])

def unique_int_solution_for_kxn(k, n, c, T):
    # Solve for integer a in ∫_a^c k x^n dx = T
    # k/(n+1) * (c^{n+1} - a^{n+1}) = T
    # a^{n+1} = c^{n+1} - (n+1)/k * T
    # We'll only call this when k divides (n+1)*T cleanly and rhs is perfect power.
    rhs = Fraction(c) ** (n + 1) - Fraction(n + 1, k) * T
    # rhs must be integer and be perfect (n+1)-th power for integer a.
    if rhs.denominator != 1:
        return None
    val = rhs.numerator
    # handle odd/even powers
    power = n + 1
    # integer root
    if val == 0:
        return 0
    sign = 1
    if val < 0:
        if power % 2 == 0:
            return None
        sign = -1
        val = -val
    root = int(round(val ** (1.0 / power)))
    # correct by checking near values
    candidates = set([max(0, root - 2), max(0, root - 1), root, root + 1, root + 2])
    # also allow negative for odd power
    allcands = set()
    for r in candidates:
        allcands.add(r)
        if power % 2 == 1:
            allcands.add(-r)
    for r in sorted(allcands):
        if r ** power == (rhs.numerator):
            return r
    return None

def format_or_list(values):
    # values: list of Fractions or ints; want "aorb" without spaces
    strs = []
    for v in values:
        if isinstance(v, Fraction):
            strs.append(frac_to_str(v))
        else:
            strs.append(str(v))
    return "or".join(strs)

def gen_family_A(rng: random.Random):
    # polynomial integrand
    # choose n, k
    n = rng.choice([1, 2, 3])  # degree
    # pick k ensuring not too large
    k = rng.choice([1, 2, 3, 4, 5, 6, 8, 10, 12])
    # choose a,b integers, distinct, smallish
    a = rng.randint(-5, 6)
    b = rng.randint(-5, 6)
    while b == a:
        b = rng.randint(-5, 6)
    # question 2: choose c and integer solution a0, build T
    c = rng.randint(-5, 7)
    a0 = rng.randint(-5, 7)
    while a0 == c:
        a0 = rng.randint(-5, 7)
    T = integral_kxn(k, n, a0, c)

    # Render
    problem = []
    problem.append("你是一个擅长计算自定义运算的智能助手。下面给出一个用定积分定义的新运算，请按规则作答。")
    problem.append("")
    problem.append("### 运算规则")
    problem.append(f"定义运算 a★b = \\int_{{a}}^{{b}} {k}x^{n} \\, dx")
    problem.append("")
    problem.append("### 问题")
    problem.append(f"1) 计算 {a}★{b} 。答案用双中括号包裹，例如 [[33]]。")
    problem.append(f"2) 若 a★{c} = {frac_to_str(T)}，求 a。若有多个解用 'or' 连接，例如 [[1or2]]。同样用双中括号包裹。")

    # Solve Q1
    val1 = integral_kxn(k, n, a, b)

    # Solve Q2 (should be unique for constructed a0)
    # We still compute via formula and verify.
    # a^{n+1} = c^{n+1} - (n+1)/k * T
    sol = unique_int_solution_for_kxn(k, n, c, T)
    if sol is None:
        raise ValueError("Failed to produce integer-solvable instance for family A.")
    # verify
    if integral_kxn(k, n, sol, c) != T:
        raise ValueError("Verification failed for family A.")

    answer = wrap_double_brackets(frac_to_str(val1)) + "====" + wrap_double_brackets(str(sol))

    expl = []
    expl.append("第1问：")
    expl.append(f"a★b=∫_a^b {k}x^{n}dx = {k}/({n+1})·(b^{n+1}-a^{n+1})。")
    expl.append(f"代入 a={a}, b={b} 得 {k}/({n+1})·(({b})^{n+1}-({a})^{n+1}) = {frac_to_str(val1)}。")
    expl.append("第2问：")
    expl.append(f"由 a★{c} = {frac_to_str(T)}：")
    expl.append(f"{k}/({n+1})·(({c})^{n+1}-a^{n+1}) = {frac_to_str(T)}，")
    expl.append(f"所以 a^{n+1} = ({c})^{n+1} - ({n+1})/{k}·{frac_to_str(T)}。")
    expl.append(f"计算可得整数解 a={sol}，回代验证 ∫_{sol}^{c} {k}x^{n}dx = {frac_to_str(T)} 成立。")

    return "\n".join(problem), answer, "\n".join(expl)

def gen_family_B(rng: random.Random):
    # affine integrand
    m = rng.choice([1, 2, 3, 4, 5, 6, 8, 10])
    p = rng.choice([-6, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 7])
    a = rng.randint(-6, 6)
    b = rng.randint(-6, 6)
    while b == a:
        b = rng.randint(-6, 6)

    # For Q2 construct to have integer solutions:
    # a★c = m/2 (c^2-a^2) + p(c-a) = T
    # Rearranged: (-m/2)a^2 - p a + (m/2)c^2 + pc - T = 0
    # Multiply by 2: -m a^2 - 2p a + m c^2 + 2pc - 2T = 0
    # => m a^2 + 2p a + (2T - m c^2 - 2pc) = 0
    c = rng.randint(-5, 7)
    # choose two integer roots r1,r2 possibly equal
    r1 = rng.randint(-6, 6)
    r2 = rng.randint(-6, 6)
    # allow equal for single root
    # Build T so that equation has roots r1,r2
    # We want polynomial: m(a-r1)(a-r2)= m a^2 - m(r1+r2)a + m r1 r2
    # Our polynomial is: m a^2 + 2p a + C = 0
    # Therefore need 2p = -m(r1+r2) => choose r1,r2 consistent with p
    # We'll resample a few times to match.
    for _ in range(200):
        r1 = rng.randint(-6, 6)
        r2 = rng.randint(-6, 6)
        if 2 * p == -m * (r1 + r2):
            break
    else:
        # fallback: force r2 from r1
        r1 = rng.randint(-6, 6)
        # r2 = -(2p/m) - r1, require integer and m divides 2p
        if (2 * p) % m != 0:
            # adjust p to ensure divisibility
            p = rng.choice([0, m, -m, 2*m, -2*m]) // 1
        r2 = - (2 * p) // m - r1

    # Now choose T so that C = m r1 r2
    # C = 2T - m c^2 - 2 p c
    # => 2T = m r1 r2 + m c^2 + 2 p c
    twoT = m * r1 * r2 + m * c * c + 2 * p * c
    # Ensure T is integer or half-integer; we will present as fraction if needed
    T = Fraction(twoT, 2)

    # ensure equation actually yields these roots
    A = m
    B = 2 * p
    C = int(twoT - (m * c * c + 2 * p * c))  # equals m*r1*r2
    roots = solve_quadratic_int_roots(A, B, C)
    if not roots:
        raise ValueError("Failed to generate solvable quadratic in family B.")
    # verify roots by integral
    for rr in roots:
        if rr.denominator != 1:
            raise ValueError("Non-integer root unexpectedly generated.")
        if integral_mx_p(m, p, int(rr), c) != T:
            raise ValueError("Verification failed for family B root.")

    val1 = integral_mx_p(m, p, a, b)

    problem = []
    problem.append("你是一个擅长计算自定义运算的智能助手。下面给出一个用定积分定义的新运算，请按规则作答。")
    problem.append("")
    problem.append("### 运算规则")
    problem.append(f"定义运算 a★b = \\int_{{a}}^{{b}} ({m}x {('+' if p>=0 else '-') } {abs(p)}) \\, dx")
    problem.append("")
    problem.append("### 问题")
    problem.append(f"1) 计算 {a}★{b} 。答案用双中括号包裹，例如 [[33]]。")
    problem.append(f"2) 若 a★{c} = {frac_to_str(T)}，求 a。若有多个解用 'or' 连接，例如 [[1or2]]。同样用双中括号包裹。")

    # format answers
    ans1 = frac_to_str(val1)
    # roots are integers sorted
    int_roots = [str(r.numerator) for r in roots]
    ans2 = "or".join(int_roots)
    answer = wrap_double_brackets(ans1) + "====" + wrap_double_brackets(ans2)

    expl = []
    expl.append("第1问：")
    expl.append(f"a★b=∫_a^b ({m}x{('+' if p>=0 else '-')}{abs(p)})dx")
    expl.append(f"= {m}/2·(b^2-a^2) + {p}·(b-a)。")
    expl.append(f"代入 a={a}, b={b} 得 {frac_to_str(val1)}。")
    expl.append("第2问：")
    expl.append(f"由 a★{c} = {frac_to_str(T)}：")
    expl.append(f"{m}/2·(({c})^2-a^2)+{p}·({c}-a)={frac_to_str(T)}。")
    expl.append("整理成关于 a 的二次方程，可得到整数解：")
    expl.append("a=" + " 或 ".join(int_roots) + "。")
    expl.append("将解分别回代到定积分表达式中，均可得到右侧的数值。")

    return "\n".join(problem), answer, "\n".join(expl)

def make_one(rng: random.Random):
    # Choose family with balance
    if rng.random() < 0.5:
        return gen_family_A(rng)
    else:
        return gen_family_B(rng)

def main():
    raw = sys.stdin.read()
    try:
        inp = json.loads(raw)
    except Exception as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    seed = int(inp.get("seed", 0))
    count = int(inp.get("count", 1))
    rng = random.Random(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = 50 * count + 200

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            problem, answer, explanation = make_one(rng)
        except Exception as e:
            print(f"Generation attempt failed: {e}", file=sys.stderr)
            continue
        key = (problem, answer)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    if len(results) < count:
        print(f"Failed to generate enough unique problems. Got {len(results)} of {count}.", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()