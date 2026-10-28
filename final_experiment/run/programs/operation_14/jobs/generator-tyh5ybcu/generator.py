import sys, json, random, math
from typing import List, Tuple, Dict, Any, Optional

# We may use sympy and z3 if needed, but this generator stays in stdlib and exact integer arithmetic.


def cadd(a, b):
    return (a[0] + b[0], a[1] + b[1])

def csub(a, b):
    return (a[0] - b[0], a[1] - b[1])

def cmul(a, b):
    # (x1+y1 i)(x2+y2 i) = (x1x2 - y1y2) + (x1y2 + y1x2)i
    return (a[0]*b[0] - a[1]*b[1], a[0]*b[1] + a[1]*b[0])

def cscale(a, k: int):
    return (a[0]*k, a[1]*k)

def csq(a):
    return cmul(a, a)

def fmt_complex(z: Tuple[int, int]) -> str:
    x, y = z
    if y == 0:
        return str(x)
    if x == 0:
        if y == 1:
            return "i"
        if y == -1:
            return "-i"
        return f"{y}i"
    sign = "+" if y > 0 else "-"
    ay = abs(y)
    if ay == 1:
        return f"{x}{sign}i"
    return f"{x}{sign}{ay}i"

def op(a: int, b: int) -> Tuple[int, int]:
    # a◎b = (a + b i)^2 = (a^2 - b^2) + (2ab)i
    return (a*a - b*b, 2*a*b)

def op_variant(a: int, b: int, variant: int) -> Tuple[int, int]:
    # Provide L2 variation while staying in same domain (custom complex-like operation from (a + b i)^2)
    # variant 0: (a + b i)^2
    # variant 1: (a - b i)^2
    # variant 2: (-a + b i)^2
    # variant 3: (a + b i)^2 but "i" replaced by "j" symbol in statement (still same arithmetic)
    if variant == 0 or variant == 3:
        return op(a, b)
    elif variant == 1:
        # (a - bi)^2 = (a^2 - b^2) - (2ab)i
        return (a*a - b*b, -2*a*b)
    elif variant == 2:
        # (-a + bi)^2 = (a^2 - b^2) - (2ab)i  (since -a flips imaginary part sign)
        return (a*a - b*b, -2*a*b)
    else:
        raise ValueError("bad variant")

def symbol_for_i(variant: int) -> str:
    return "j" if variant == 3 else "i"

def check_unique_X(target: Tuple[int,int], a: int, b: int, variant: int) -> Optional[int]:
    # Solve (X◎a) + (something) = target ; Here operation yields:
    # X◎a = (X^2 - a^2) + s*(2Xa)i where s is +/-1 depending on variant
    # Imag part gives linear equation in X; use it for uniqueness.
    s = 1
    if variant in (1,2):
        s = -1
    tx, ty = target
    # ty = s*2*X*a  => X = ty / (s*2a) must be integer
    denom = s * 2 * a
    if denom == 0:
        return None
    if ty % denom != 0:
        return None
    X = ty // denom
    # real part check: tx == X^2 - a^2
    if tx != X*X - a*a:
        return None
    return X

def build_problem_1(rng: random.Random) -> Dict[str, Any]:
    # Type A: compute linear combination of 2-4 operation terms, maybe with integer multipliers.
    variant = rng.choice([0,0,0,1,2,3])  # bias to canonical but allow variants
    sym = symbol_for_i(variant)

    term_count = rng.choice([2,3,3,4])
    terms = []
    expr_val = (0,0)

    for _ in range(term_count):
        a = rng.randint(-6, 7)
        b = rng.randint(-6, 7)
        while a == 0 and b == 0:
            a = rng.randint(-6, 7)
            b = rng.randint(-6, 7)
        k = rng.choice([1,1,1,2, -1, 3])
        z = op_variant(a, b, variant)
        expr_val = cadd(expr_val, cscale(z, k))
        # render term
        if k == 1:
            t = f"({a}◎{b})"
        elif k == -1:
            t = f"-({a}◎{b})"
        else:
            t = f"{k}×({a}◎{b})"
        terms.append(t)

    # combine with + between terms (already include unary - where needed)
    expr = terms[0]
    for t in terms[1:]:
        if t.startswith("-"):
            expr += f" {t}"
        else:
            expr += f" + {t}"

    problem = (
        "定义一种自定义运算：\n\n"
        f"a◎b = (a + b{sym})^2，其中 {sym}^2 = -1，且按复数运算规则展开。\n\n"
        f"计算：{expr}。\n"
        "若结果是复数，请写成 x + yi 的形式（例如 3-2i）；若为实数直接写整数。"
    )
    answer = fmt_complex(expr_val)

    # explanation: show rule and compute each term briefly
    lines = []
    lines.append(f"运算展开：a◎b = (a + b{sym})^2 = (a^2 - b^2) + ({'2ab' if variant in (0,3) else '-2ab'}){sym}。")
    lines.append("逐项计算并线性相加：")
    # recompute with details
    expr_val2 = (0,0)
    for t in terms:
        # parse back by regenerating? We'll store details now by re-walking generation is hard.
        pass
    # Instead: provide a compact correctness check by plugging final into sum components listing from stored data
    # So we store data in generation:
    return_obj = {"problem": problem, "answer": answer}
    return_obj["_variant"] = variant
    return_obj["_sym"] = sym
    return_obj["_expr_val"] = expr_val
    return_obj["_terms_raw"] = []  # fill properly with a,b,k and value
    # regenerate properly with stored data:
    expr_val = (0,0)
    terms = []
    raw = []
    for _ in range(term_count):
        a = rng.randint(-6, 7)
        b = rng.randint(-6, 7)
        while a == 0 and b == 0:
            a = rng.randint(-6, 7)
            b = rng.randint(-6, 7)
        k = rng.choice([1,1,1,2, -1, 3])
        z = op_variant(a, b, variant)
        expr_val = cadd(expr_val, cscale(z, k))
        if k == 1:
            t = f"({a}◎{b})"
        elif k == -1:
            t = f"-({a}◎{b})"
        else:
            t = f"{k}×({a}◎{b})"
        terms.append(t)
        raw.append((a,b,k,z))
    # build expression again
    expr = terms[0]
    for t in terms[1:]:
        if t.startswith("-"):
            expr += f" {t}"
        else:
            expr += f" + {t}"
    problem = (
        "定义一种自定义运算：\n\n"
        f"a◎b = (a + b{sym})^2，其中 {sym}^2 = -1，且按复数运算规则展开。\n\n"
        f"计算：{expr}。\n"
        "若结果是复数，请写成 x + yi 的形式（例如 3-2i）；若为实数直接写整数。"
    )
    answer = fmt_complex(expr_val)

    lines = []
    if variant in (0,3):
        lines.append(f"展开：a◎b=(a+b{sym})^2=(a^2-b^2)+2ab{sym}。")
    else:
        lines.append(f"展开：a◎b=(a-b{sym})^2=(a^2-b^2)-2ab{sym}。")
    lines.append("逐项：")
    acc = (0,0)
    for (a,b,k,z) in raw:
        kz = cscale(z,k)
        acc = cadd(acc, kz)
        lines.append(f"{k}×({a}◎{b}) = {k}×({fmt_complex(z)}) = {fmt_complex(kz)}")
    lines.append(f"相加得到：{fmt_complex(acc)}。")
    explanation = "\n".join(lines)

    return {"problem": problem, "answer": answer, "explanation": explanation}

def build_problem_2(rng: random.Random) -> Dict[str, Any]:
    # Type B: solve for X from equation involving one unknown operation term and some known complex constant.
    variant = rng.choice([0,0,0,1,2,3])
    sym = symbol_for_i(variant)
    s = 1 if variant in (0,3) else -1

    # Choose parameter a for X◎a to make X solvable from imaginary part: ty = s*2*X*a * m
    a = rng.randint(1,6)
    m = rng.choice([1,2,3])  # multiplier on (X◎a)
    # Choose X
    X = rng.randint(-8,8)
    while X == 0:
        X = rng.randint(-8,8)

    # Build other known terms: (p◎q) plus maybe scaled one more term, and a constant shift.
    p = rng.randint(-7,7); q = rng.randint(-7,7)
    while p == 0 and q == 0:
        p = rng.randint(-7,7); q = rng.randint(-7,7)
    k2 = rng.choice([1,2,-1,3])
    t_known = cscale(op_variant(p,q,variant), k2)

    # Optional second known term
    if rng.random() < 0.55:
        r = rng.randint(-6,6); u = rng.randint(-6,6)
        while r == 0 and u == 0:
            r = rng.randint(-6,6); u = rng.randint(-6,6)
        k3 = rng.choice([1, -1, 2])
        t_known2 = cscale(op_variant(r,u,variant), k3)
        known_sum = cadd(t_known, t_known2)
        known_render = f"{k2}×({p}◎{q}) + {k3}×({r}◎{u})"
        known_explain = [(p,q,k2),(r,u,k3)]
    else:
        known_sum = t_known
        known_render = f"{k2}×({p}◎{q})"
        known_explain = [(p,q,k2)]

    # Constant complex shift C
    cx = rng.randint(-30,30)
    cy = rng.randint(-30,30)
    C = (cx, cy)

    # Compute target: known_sum + m*(X◎a) + C
    termX = cscale(op_variant(X, a, variant), m)
    target = cadd(cadd(known_sum, termX), C)

    # Now prepare equation: known_render + m×(X◎a) + (cx+cy i) = target
    # Ensure uniqueness: it should be unique from imaginary part, and real part must match.
    # Additionally avoid degenerate denom:
    denom = s*2*a*m
    if denom == 0:
        return build_problem_2(rng)

    # Verify solver can recover X uniquely
    # Move known to right: m*(X◎a) = target - known_sum - C
    rhs_for_X = csub(csub(target, known_sum), C)
    # rhs_for_X should equal m*(X◎a)
    # Divide by m: get (X◎a)
    if rhs_for_X[0] % m != 0 or rhs_for_X[1] % m != 0:
        return build_problem_2(rng)
    opX_target = (rhs_for_X[0]//m, rhs_for_X[1]//m)
    X_check = check_unique_X(opX_target, a=a, b=0, variant=variant)  # wrong signature usage
    # implement directly:
    tx, ty = opX_target
    denom2 = s*2*a
    if denom2 == 0 or ty % denom2 != 0:
        return build_problem_2(rng)
    X_rec = ty // denom2
    if tx != X_rec*X_rec - a*a:
        return build_problem_2(rng)
    if X_rec != X:
        return build_problem_2(rng)

    # Render constant
    C_str = fmt_complex(C)
    target_str = fmt_complex(target)

    # Render m*(X◎a)
    if m == 1:
        xterm_render = f"(X◎{a})"
    else:
        xterm_render = f"{m}×(X◎{a})"

    problem = (
        "定义一种自定义运算：\n\n"
        f"a◎b = (a + b{sym})^2，其中 {sym}^2 = -1。\n\n"
        f"已知方程：{known_render} + {xterm_render} + ({C_str}) = {target_str}。\n"
        "求整数 X。"
    )

    # Explanation: isolate X◎a, use imaginary part then verify real part.
    lines = []
    if variant in (0,3):
        lines.append(f"有：X◎{a}=(X+{a}{sym})^2=(X^2-{a*a})+2X·{a}{sym}。")
    else:
        lines.append(f"有：X◎{a}=(X-{a}{sym})^2=(X^2-{a*a})-2X·{a}{sym}。")
    lines.append(f"将已知项移到右边：{xterm_render} = {target_str} - ({known_render}) - ({C_str})。")
    lines.append("对比虚部可得 X：")
    lines.append(f"{m}×({s}·2·X·{a}) = 目标虚部差值。于是 X = {X}。")
    lines.append(f"代回检验实部：X^2-{a*a} = {X*X - a*a}，与右侧对应一致。")
    explanation = "\n".join(lines)

    return {"problem": problem, "answer": X, "explanation": explanation}

def normalize_problem_text(s: str) -> str:
    return " ".join(s.split())

def generate(seed: int, count: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    out = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        builder = build_problem_2 if rng.random() < 0.5 else build_problem_1
        try:
            item = builder(rng)
        except RecursionError:
            continue
        key = normalize_problem_text(item["problem"])
        if key in seen:
            continue
        seen.add(key)
        # basic sanity
        if not item["problem"].strip():
            continue
        if item["explanation"] is None:
            continue
        out.append({"problem": item["problem"], "answer": item["answer"], "explanation": item["explanation"]})

    if len(out) < count:
        print(f"生成失败：仅生成 {len(out)}/{count} 道题（尝试 {attempts} 次）。", file=sys.stderr)
        # still output what we have? Spec requires exactly count; so raise.
        raise RuntimeError("Could not generate enough unique problems within attempt limit.")
    return out

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    res = generate(seed, count)
    sys.stdout.write(json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    main()