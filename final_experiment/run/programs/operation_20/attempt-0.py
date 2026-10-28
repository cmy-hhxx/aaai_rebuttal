import sys, json, math, random
from fractions import Fraction

# We generate problems about a custom operation:
# a ● b = ∫_a^b f(x) dx + C
# f(x) is an odd polynomial chosen so that ∫_a^b f(x) dx becomes an even polynomial in a when b is fixed at 1,
# making it natural to have symmetric solutions ±a (like the seed).
#
# We enforce that the asked equation is: a●1 = K, solve for a, and require more than one answer (typically 2).
#
# No network, deterministic by seed, bounded resampling.

def frac_to_str(fr: Fraction) -> str:
    if fr.denominator == 1:
        return str(fr.numerator)
    # keep as reduced fraction
    return f"{fr.numerator}/{fr.denominator}"

def format_answers(ans_list):
    # ans_list: list of Fraction, already unique
    # sort numerically
    ans_list = sorted(ans_list, key=lambda x: (x.numerator / x.denominator))
    s = "or".join(frac_to_str(a) for a in ans_list)
    return f"[[{s}]]"

def poly_text_zh(terms):
    # terms: list of (coeff:int, power:int), like [(1,3),(2,1)] => x^3+2x
    # assume coeff != 0
    parts = []
    for c, p in sorted(terms, key=lambda t: -t[1]):
        if p == 0:
            term = str(abs(c))
        elif p == 1:
            term = "x" if abs(c) == 1 else f"{abs(c)}x"
        else:
            term = f"x^{p}" if abs(c) == 1 else f"{abs(c)}x^{p}"
        sign = "+" if c > 0 else "-"
        parts.append((sign, term))
    # first term sign handling
    if not parts:
        return "0"
    sign0, term0 = parts[0]
    out = (term0 if sign0 == "+" else f"-{term0}")
    for sign, term in parts[1:]:
        out += sign + term
    return out

def build_instance(rng: random.Random):
    # Choose family:
    # f(x) = sum c_i x^{p_i} with odd p_i (1,3,5) and small integer coefficients.
    # Then ∫_a^1 f(x) dx = const - sum c_i/(p_i+1)*a^{p_i+1}
    # which depends on even powers of a: (p_i+1) even.
    # If we target equation to become a^2 = t or A a^2 + B a^4 = t with t>0 etc.
    #
    # We'll use one-term or two-term cases.
    # To keep solutions simple and usually two-valued, often reduce to a^2 = t (rational).
    family = rng.choice(["one_term", "two_term_quadratic_in_a2"])

    C = rng.randint(2, 9)  # constant added outside integral
    b = 1  # fixed upper limit in question, mirrors seed

    if family == "one_term":
        # f(x) = k x^{p} with p in {1,3,5}; choose k so that equation leads to a^2 = t or a^4 = t etc.
        p = rng.choice([1, 3, 5])
        k = rng.choice([-6, -4, -3, -2, -1, 1, 2, 3, 4, 6])
        # Integral from a to 1: k/(p+1)*(1 - a^{p+1})
        # So a●1 = k/(p+1)*(1 - a^{p+1}) + C
        # Let K be chosen so that a^{p+1} = T is positive rational giving two real solutions if p+1 even.
        # Here p is odd => p+1 even. Great: solutions are ±(T)^{1/(p+1)}.
        # For simplicity, we make T a perfect power so that root is rational/integer.
        # Choose base q (rational) and set a = ±q, then compute K.
        q_num = rng.choice([1, 2, 3, 4, 5, 6])
        q_den = rng.choice([1, 1, 1, 2, 3])  # bias to integers
        q = Fraction(q_num, q_den)
        # Compute K from chosen a=q (one of solutions), but since even power, ±q both satisfy.
        # a●1 = k/(p+1)*(1 - q^{p+1}) + C
        K = Fraction(k, p + 1) * (Fraction(1, 1) - q ** (p + 1)) + Fraction(C, 1)

        # Validate that k != 0 and that yields two distinct solutions (q != 0).
        if q == 0:
            return None
        # Now solve for a from equation:
        # k/(p+1)*(1 - a^{p+1}) + C = K  => 1 - a^{p+1} = (K - C)*(p+1)/k
        # a^{p+1} = 1 - (K - C)*(p+1)/k
        rhs = Fraction(1, 1) - (K - C) * Fraction(p + 1, k)
        # We need rhs = q^(p+1). This should hold by construction.
        if rhs != q ** (p + 1):
            return None
        # Two real solutions: a = ±q (since p+1 even)
        ans = [q, -q]
        # Ensure distinct (q != 0)
        if ans[0] == ans[1]:
            return None

        f_terms = [(k, p)]
        return {
            "C": C,
            "b": b,
            "f_terms": f_terms,
            "K": K,
            "answers": sorted(set(ans), key=lambda x: (x.numerator / x.denominator)),
            "family": family,
            "extra": {"p": p, "k": k, "q": q, "rhs": rhs}
        }

    else:
        # family == "two_term_quadratic_in_a2"
        # Choose f(x) = k1 x + k3 x^3 (odd terms) so that the equation becomes:
        # a●1 = (k1/2)(1-a^2) + (k3/4)(1-a^4) + C = K
        # Rearranged in t=a^2:
        # (k3/4) t^2 + (k1/2) t + (K - C - k1/2 - k3/4) = 0
        # We want exactly two solutions for a: ±sqrt(t0) with a single positive rational t0 root
        # AND the other root in t is negative (discarded), or root t0 positive and distinct, but still only ± for a.
        k1 = rng.choice([-6, -4, -2, -1, 1, 2, 4, 6])
        k3 = rng.choice([-6, -4, -2, -1, 1, 2, 4, 6])
        # avoid k3=0 (we want quadratic in t sometimes), but it can be linear; keep quadratic:
        if k3 == 0:
            return None

        # Choose t0 as positive rational perfect square to keep sqrt rational: t0 = (m/n)^2
        m = rng.choice([1, 2, 3, 4, 5, 6])
        n = rng.choice([1, 1, 2, 3])
        s = Fraction(m, n)
        t0 = s * s  # a^2
        a_vals = [s, -s]

        # Choose another root t1 negative rational to ensure only ±sqrt(t0) are real solutions.
        # We'll set the quadratic in t to have roots t0 and t1.
        # For quadratic A t^2 + B t + D = 0, with A = k3/4, B = k1/2, D = (K - C - k1/2 - k3/4)
        # Root sum: -(B/A) = t0 + t1 => t1 = -(B/A) - t0
        A = Fraction(k3, 4)
        B = Fraction(k1, 2)
        t1 = -B / A - t0

        # Require t1 < 0
        if t1 >= 0:
            return None

        # Now determine D from product: D/A = t0*t1 => D = A*t0*t1
        D = A * t0 * t1
        # Then K computed from: D = K - C - k1/2 - k3/4  => K = D + C + k1/2 + k3/4
        K = D + Fraction(C, 1) + Fraction(k1, 2) + Fraction(k3, 4)

        # sanity check: plug back for a=s
        # integral: (k1/2)(1-a^2) + (k3/4)(1-a^4)
        integral = Fraction(k1, 2) * (1 - t0) + Fraction(k3, 4) * (1 - t0 * t0)
        lhs = integral + C
        if lhs != K:
            return None

        f_terms = [(k3, 3), (k1, 1)]
        return {
            "C": C,
            "b": b,
            "f_terms": f_terms,
            "K": K,
            "answers": sorted(set(a_vals), key=lambda x: (x.numerator / x.denominator)),
            "family": family,
            "extra": {"k1": k1, "k3": k3, "s": s, "t0": t0, "t1": t1}
        }

def render_problem_zh(inst, rng):
    # Different phrasings
    styles = rng.choice([1, 2, 3])
    f_expr = poly_text_zh(inst["f_terms"])
    C = inst["C"]
    K = inst["K"]
    # K as string: if fraction, show as a/b
    K_str = frac_to_str(K if isinstance(K, Fraction) else Fraction(K, 1))

    op_symbol = rng.choice(["●", "★", "⊙"])
    # operation definition
    rule = f"a{op_symbol}b=∫_a^b f(x) dx + {C}。"

    if styles == 1:
        problem = (
            "你需要按如下自定义运算规则计算未知数。\n\n"
            "【运算规则】\n"
            f"{rule}\n\n"
            "【已知】\n"
            f"f(x)={f_expr}。\n\n"
            "【问题】\n"
            f"若 a{op_symbol}1 = {K_str}，求 a。\n"
            "答案可能为负数；若有多个答案，用“or”连接。请将最终答案写成 [[...]] 的形式。"
        )
    elif styles == 2:
        problem = (
            "定义一种新运算（与普通乘法无关）：\n"
            f"{rule}\n"
            f"其中 f(x)={f_expr}。\n"
            f"现在给出等式 a{op_symbol}1={K_str}，求满足条件的 a。\n"
            "若有多解，请用 or 分隔，并用双中括号包裹，例如 [[1or2]]。"
        )
    else:
        problem = (
            "设自定义运算满足：\n"
            f"{rule}\n"
            f"并给定函数 f(x)={f_expr}。\n"
            f"求解方程 a{op_symbol}1={K_str} 中的 a（可能为负）。\n"
            "多解用 or 连接，最后答案写作 [[你的答案]]。"
        )
    return problem, op_symbol

def render_explanation_zh(inst, op_symbol):
    f_expr = poly_text_zh(inst["f_terms"])
    C = inst["C"]
    K = inst["K"]
    K_str = frac_to_str(K)
    # Provide a checkable derivation with the concrete antiderivative.
    # Build antiderivative text.
    anti_parts = []
    for c, p in sorted(inst["f_terms"], key=lambda t: -t[1]):
        anti_c = Fraction(c, p + 1)
        pow2 = p + 1
        coef_str = frac_to_str(abs(anti_c))
        if pow2 == 1:
            core = "x"
        else:
            core = f"x^{pow2}"
        if abs(anti_c) == 1:
            term = core
        else:
            term = f"{coef_str}{core}"
        sign = "+" if anti_c > 0 else "-"
        anti_parts.append((sign, term))
    sign0, term0 = anti_parts[0]
    F = term0 if sign0 == "+" else f"-{term0}"
    for sgn, trm in anti_parts[1:]:
        F += sgn + trm

    ans_str = format_answers(inst["answers"])
    # show key equation leading to even power
    explanation = (
        f"由定义：a{op_symbol}1=∫_a^1 f(x)dx+{C}。\n"
        f"已知 f(x)={f_expr}，其一个原函数可取 F(x)={F}。\n"
        f"因此 ∫_a^1 f(x)dx = F(1)-F(a)。\n"
        f"把它代入 a{op_symbol}1={K_str} 得到关于 a 的方程，解得 a 的取值为 {ans_str}。\n"
        "（可将解代回 ∫_a^1 f(x)dx+常数 进行核对。）"
    )
    return explanation

def canonical_key(problem: str, answer):
    return (problem.strip(), json.dumps(answer, ensure_ascii=False, sort_keys=True))

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = 4000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        inst = build_instance(rng)
        if inst is None:
            continue
        # Require multiple answers
        if len(inst["answers"]) < 2:
            continue

        problem, op_symbol = render_problem_zh(inst, rng)
        answer = format_answers(inst["answers"])
        explanation = render_explanation_zh(inst, op_symbol)

        key = canonical_key(problem, answer)
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    if len(results) < count:
        print(f"Failed to generate enough unique problems: got {len(results)}/{count} after {attempts} attempts",
              file=sys.stderr)
        # Still output what we have to keep JSON valid; but spec wants exactly count.
        # Raise to signal failure.
        raise SystemExit(1)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()