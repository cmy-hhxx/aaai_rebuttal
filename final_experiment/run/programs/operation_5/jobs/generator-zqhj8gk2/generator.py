import sys, json, random, math
from typing import List, Dict, Any, Tuple

# We generate problems about custom operation(s), primarily based on:
# a ∞ b = a^2 + b^2 (positive integers).
# To add diversity while staying in-domain (custom operation evaluation / inverse),
# we sometimes introduce one extra operation with explicit definition, but always
# keep the core task as evaluating / solving equations under the custom rule(s).

def is_square(n: int) -> bool:
    if n < 0:
        return False
    r = int(math.isqrt(n))
    return r * r == n

def fmt_op(sym: str) -> str:
    # render operator symbol as plain text; keep consistent
    return sym

def solve_in_positive_integers_for_infty_eq(n: int, b: int) -> List[int]:
    # Solve x^2 + b^2 = n, x positive integer
    rem = n - b*b
    if rem <= 0:
        return []
    if is_square(rem):
        x = int(math.isqrt(rem))
        if x > 0:
            return [x]
    return []

def solve_pair_sum_squares(n: int, require_distinct: bool = False, limit: int = 1000) -> List[Tuple[int,int]]:
    # Find all positive integer (a,b) such that a^2 + b^2 = n
    sols = []
    # a and b can be up to sqrt(n-1)
    m = int(math.isqrt(n-1))
    for a in range(1, m+1):
        rem = n - a*a
        if rem <= 0:
            continue
        if is_square(rem):
            b = int(math.isqrt(rem))
            if b <= 0:
                continue
            if require_distinct and a == b:
                continue
            sols.append((a,b))
    return sols

def make_problem_type1(rng: random.Random) -> Tuple[str, Any, str]:
    # Compute a∞b = a^2 + b^2
    a = rng.randint(2, 30)
    b = rng.randint(2, 30)
    ans = a*a + b*b
    problem = (
        "定义自定义运算：\n"
        f"{a} {fmt_op('∞')} {b} 表示 {a}^2 + {b}^2（a、b 为正整数）。\n\n"
        f"计算：{a}{fmt_op('∞')}{b} 的值。\n"
        "请只输出一个数字。"
    )
    explanation = f"按定义：{a}∞{b} = {a}^2 + {b}^2 = {a*a} + {b*b} = {ans}。"
    return problem, ans, explanation

def make_problem_type2(rng: random.Random) -> Tuple[str, Any, str]:
    # Solve X∞b = n (unique)
    x = rng.randint(2, 40)
    b = rng.randint(2, 30)
    n = x*x + b*b
    # ask for X given X∞b = n
    problem = (
        "定义自定义运算：x∞y = x^2 + y^2（x、y 为正整数）。\n\n"
        f"若 X∞{b} = {n}，求 X。\n"
        "请只输出 X 的值。"
    )
    explanation = (
        f"由定义：X∞{b} = X^2 + {b}^2 = {n}。\n"
        f"因此 X^2 = {n} - {b*b} = {x*x}，所以 X = {x}（正整数）。"
    )
    return problem, x, explanation

def make_problem_type3(rng: random.Random) -> Tuple[str, Any, str]:
    # Two-step: compute (a∞b) - (c∞d) or compare
    a = rng.randint(2, 25)
    b = rng.randint(2, 25)
    c = rng.randint(2, 25)
    d = rng.randint(2, 25)
    val1 = a*a + b*b
    val2 = c*c + d*d
    op_choice = rng.choice(["+", "-", "×"])
    if op_choice == "+":
        ans = val1 + val2
        expr = f"({a}∞{b}) + ({c}∞{d})"
        expl = f"({a}∞{b})={val1}，({c}∞{d})={val2}，相加得 {ans}。"
    elif op_choice == "-":
        # ensure nonnegative by ordering
        if val1 < val2:
            a,b,c,d,val1,val2 = c,d,a,b,val2,val1
        ans = val1 - val2
        expr = f"({a}∞{b}) - ({c}∞{d})"
        expl = f"({a}∞{b})={val1}，({c}∞{d})={val2}，相减得 {ans}。"
    else:
        # multiplication, keep numbers moderate
        ans = val1 * val2
        expr = f"({a}∞{b}) × ({c}∞{d})"
        expl = f"({a}∞{b})={val1}，({c}∞{d})={val2}，相乘得 {ans}。"
    problem = (
        "定义自定义运算：x∞y = x^2 + y^2（x、y 为正整数）。\n\n"
        f"计算表达式：{expr}。\n"
        "请只输出一个数字。"
    )
    explanation = expl
    return problem, ans, explanation

def make_problem_type4(rng: random.Random) -> Tuple[str, Any, str]:
    # Find all positive integer pairs (a,b) such that a∞b = N, with controlled small number of solutions.
    # We'll craft N as sum of squares that yields exactly 2 ordered solutions (a,b) in positive ints.
    # Example: 25 = 3^2+4^2 and 4^2+3^2 => 2 ordered solutions.
    # We ensure N has exactly 2 ordered solutions by choosing a!=b and N not having other representations.
    # We'll search with bound.
    for _ in range(2000):
        a = rng.randint(2, 25)
        b = rng.randint(2, 25)
        if a == b:
            continue
        N = a*a + b*b
        sols = solve_pair_sum_squares(N, require_distinct=False)
        # Count ordered solutions; solve_pair_sum_squares returns (a,b) by scanning a
        # It will include both (a,b) and (b,a) if both appear during scan.
        # We want exactly 2 solutions (a,b) and (b,a), meaning exactly one unordered pair with a!=b.
        if len(sols) == 2:
            # ensure they are swaps
            sset = set(sols)
            if (a,b) in sset and (b,a) in sset:
                # ask for number of solutions, or list them sorted
                ask = rng.choice(["count", "list"])
                if ask == "count":
                    ans = 2
                    problem = (
                        "定义自定义运算：x∞y = x^2 + y^2（x、y 为正整数）。\n\n"
                        f"方程 x∞y = {N} 有多少组正整数有序解 (x,y)？\n"
                        "请只输出解的组数。"
                    )
                    explanation = (
                        f"x∞y={N} 等价于 x^2+y^2={N}。\n"
                        f"可验证 {a}^2+{b}^2={N}，且交换仍成立：{b}^2+{a}^2={N}。\n"
                        "并且该 N 只有这一对不同的平方和表示，因此有序解恰为 2 组。"
                    )
                    return problem, ans, explanation
                else:
                    # list ordered pairs in lexicographic order
                    sols_sorted = sorted(sols)
                    ans = sols_sorted
                    problem = (
                        "定义自定义运算：x∞y = x^2 + y^2（x、y 为正整数）。\n\n"
                        f"求所有满足 x∞y = {N} 的正整数有序对 (x,y)，并按字典序从小到大列出。\n"
                        "答案用 JSON 数组表示，例如 [[1,2],[2,1]]。"
                    )
                    explanation = (
                        f"x∞y={N} 等价于 x^2+y^2={N}。\n"
                        f"可得两组解：({a},{b}) 与 ({b},{a})。按字典序排序为 {sols_sorted}。"
                    )
                    return problem, ans, explanation
    raise RuntimeError("Failed to generate type4 problem with desired uniqueness of representations.")

def make_problem_type5(rng: random.Random) -> Tuple[str, Any, str]:
    # Introduce a second operation explicitly, still in same skill: evaluate custom op and solve.
    # Define: a ⊙ b = a∞b + a + b, where ∞ is as defined. Then compute or invert.
    a = rng.randint(2, 20)
    b = rng.randint(2, 20)
    base = a*a + b*b
    val = base + a + b
    mode = rng.choice(["compute", "solve"])
    if mode == "compute":
        problem = (
            "给定正整数 a,b，定义运算：\n"
            "1) a∞b = a^2 + b^2；\n"
            "2) a⊙b = (a∞b) + a + b。\n\n"
            f"计算：{a}⊙{b} 的值。\n"
            "请只输出一个数字。"
        )
        explanation = f"{a}∞{b}={a*a}+{b*b}={base}；所以 {a}⊙{b}={base}+{a}+{b}={val}。"
        return problem, val, explanation
    else:
        # Solve X⊙b = val for X (unique by construction)
        x = rng.randint(2, 25)
        b = rng.randint(2, 20)
        base = x*x + b*b
        val = base + x + b
        # equation: X^2 + b^2 + X + b = val => X^2 + X + (b^2+b-val)=0
        # but we keep constructed so solution is X=x.
        problem = (
            "给定正整数 x,y，定义运算：\n"
            "1) x∞y = x^2 + y^2；\n"
            "2) x⊙y = (x∞y) + x + y。\n\n"
            f"若 X⊙{b} = {val}，求 X。\n"
            "请只输出 X 的值。"
        )
        explanation = (
            f"由定义：X⊙{b} = (X^2+{b}^2)+X+{b} = {val}。\n"
            f"移项得：X^2+X + ({b*b}+{b}-{val})=0。\n"
            f"代入构造可知 X={x} 满足：{x*x}+{x}+({b*b}+{b}-{val})=0，因此 X={x}。"
        )
        return problem, x, explanation

def canonical_signature(problem: str, answer: Any) -> str:
    # prevent duplicates across generated set
    return problem.strip() + "\nANS=" + json.dumps(answer, ensure_ascii=False, sort_keys=True)

def generate_one(rng: random.Random) -> Dict[str, Any]:
    makers = [make_problem_type1, make_problem_type2, make_problem_type3, make_problem_type4, make_problem_type5]
    # weights encourage variety
    weights = [3, 3, 3, 2, 3]
    maker = rng.choices(makers, weights=weights, k=1)[0]
    p, a, e = maker(rng)
    if not isinstance(p, str) or not p.strip():
        raise AssertionError("Empty problem.")
    if not isinstance(e, str):
        raise AssertionError("Explanation must be a string.")
    return {"problem": p, "answer": a, "explanation": e}

def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data)
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count must be positive")
    except Exception as ex:
        sys.stderr.write(f"Invalid input JSON. Expect {{'seed': int, 'count': int}}. Error: {ex}\n")
        sys.exit(1)

    rng = random.Random(seed)
    out: List[Dict[str, Any]] = []
    seen = set()

    max_attempts = 20000
    attempts = 0
    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng)
            sig = canonical_signature(item["problem"], item["answer"])
            if sig in seen:
                continue
            # basic self-check: if answer is list of pairs, ensure matches equation when relevant
            # For type4 list-mode: answer is list of [x,y]
            if isinstance(item["answer"], list) and item["answer"] and isinstance(item["answer"][0], list):
                # try to parse N from problem string "... = N"
                # lightweight validation: compute x^2+y^2 consistent across all pairs
                pairs = item["answer"]
                Ns = set()
                for xy in pairs:
                    x, y = int(xy[0]), int(xy[1])
                    if x <= 0 or y <= 0:
                        raise AssertionError("Non-positive pair in answer.")
                    Ns.add(x*x + y*y)
                if len(Ns) != 1:
                    raise AssertionError("Inconsistent pairs for sum of squares.")
            seen.add(sig)
            out.append(item)
        except Exception as ex:
            # resample on generation failure
            continue

    if len(out) < count:
        sys.stderr.write(f"Generation failed: produced {len(out)}/{count} after {attempts} attempts.\n")
        sys.exit(2)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()