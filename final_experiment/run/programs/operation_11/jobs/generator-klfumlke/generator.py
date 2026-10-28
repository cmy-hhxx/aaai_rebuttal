import sys, json, math, random
from typing import List, Dict, Any, Tuple, Optional

# We use sympy for exact integer arithmetic & equation solving when needed
import sympy as sp


def op_yen(a: int, b: int) -> int:
    """Custom operation: a¥b = a^b - b^a, for positive integers a,b."""
    return pow(a, b) - pow(b, a)


def render_op_symbol() -> str:
    return "¥"


def safe_int(x) -> int:
    if isinstance(x, bool):
        raise ValueError("bool is not int")
    if isinstance(x, int):
        return x
    if isinstance(x, sp.Integer):
        return int(x)
    raise ValueError(f"not an int: {x!r}")


def check_positive_int(n: int) -> None:
    if not (isinstance(n, int) and n > 0):
        raise ValueError(f"expected positive integer, got {n!r}")


# -------------------- Family A: Direct compute a¥b --------------------
def gen_direct_compute(rng: random.Random) -> Tuple[str, Any, str]:
    # Choose small enough to keep numbers manageable yet nontrivial.
    # a,b in [2..9], but allow equal sometimes.
    a = rng.randint(2, 9)
    b = rng.randint(2, 9)
    # Ensure not always trivial symmetric; allow all.
    val = op_yen(a, b)

    op = render_op_symbol()
    problem = (
        "定义一种新运算：对正整数 a,b，规定\n"
        f"a{op}b = a^b - b^a。\n\n"
        f"计算：{a}{op}{b}。\n"
        "答案只写一个整数。"
    )
    answer = val
    explanation = (
        f"按定义：{a}{op}{b} = {a}^{b} - {b}^{a} = {pow(a,b)} - {pow(b,a)} = {val}。"
    )

    # Internal consistency check
    assert answer == pow(a, b) - pow(b, a)
    return problem, answer, explanation


# -------------------- Family B: Solve equation a¥x = k for positive integer x --------------------
def solve_a_yen_x_equals_k(a: int, k: int, x_min: int, x_max: int) -> List[int]:
    """Find all positive integer x in [x_min, x_max] s.t. a¥x = k."""
    sols = []
    for x in range(x_min, x_max + 1):
        if op_yen(a, x) == k:
            sols.append(x)
    return sols


def gen_solve_left(rng: random.Random) -> Tuple[str, Any, str]:
    # Construct by choosing a and x, then computing k to guarantee solvable.
    a = rng.randint(2, 8)
    x_true = rng.randint(2, 9)
    k = op_yen(a, x_true)

    # Add uniqueness requirement by verifying within a range
    x_min, x_max = 1, 12
    sols = solve_a_yen_x_equals_k(a, k, x_min, x_max)

    # Resample if not unique
    tries = 0
    while len(sols) != 1 and tries < 50:
        a = rng.randint(2, 8)
        x_true = rng.randint(2, 9)
        k = op_yen(a, x_true)
        sols = solve_a_yen_x_equals_k(a, k, x_min, x_max)
        tries += 1
    if len(sols) != 1:
        raise RuntimeError("Failed to generate unique-solution instance for a¥x=k")

    op = render_op_symbol()
    problem = (
        "定义一种新运算：对正整数 a,b，规定\n"
        f"a{op}b = a^b - b^a。\n\n"
        f"已知 {a}{op}X = {k}，且 X 为正整数。\n"
        f"在 1 到 {x_max} 的范围内，求 X。"
    )
    answer = sols[0]
    explanation = (
        f"由定义，{a}{op}X = {a}^X - X^{a}。\n"
        f"在 X=1..{x_max} 逐一代入检查：只有 X={answer} 满足 "
        f"{a}^{answer} - {answer}^{a} = {pow(a,answer)} - {pow(answer,a)} = {k}。"
    )

    assert answer == x_true  # by construction + uniqueness
    assert op_yen(a, answer) == k
    return problem, answer, explanation


# -------------------- Family C: Solve chain a¥X¥b = t with explicit evaluation order (left-associative) --------------------
def chain_left(a: int, x: int, b: int) -> int:
    return op_yen(op_yen(a, x), b)


def gen_chain_left_equation(rng: random.Random) -> Tuple[str, Any, str]:
    # Build from a chosen (a, x, b), compute t, then ask to solve for x.
    a = rng.randint(2, 6)
    b = rng.randint(2, 6)
    x_true = rng.randint(2, 7)

    # Ensure intermediate stays integer (it will) but could be large negative; that's fine.
    t = chain_left(a, x_true, b)

    # Uniqueness check within small range
    x_min, x_max = 1, 10
    sols = []
    for x in range(x_min, x_max + 1):
        if chain_left(a, x, b) == t:
            sols.append(x)
    tries = 0
    while len(sols) != 1 and tries < 80:
        a = rng.randint(2, 6)
        b = rng.randint(2, 6)
        x_true = rng.randint(2, 7)
        t = chain_left(a, x_true, b)
        sols = [x for x in range(x_min, x_max + 1) if chain_left(a, x, b) == t]
        tries += 1
    if len(sols) != 1:
        raise RuntimeError("Failed to generate unique-solution instance for a¥X¥b=t")

    op = render_op_symbol()
    problem = (
        "定义一种新运算：对正整数 a,b，规定\n"
        f"a{op}b = a^b - b^a。\n\n"
        f"注意：连续运算按从左到右计算，即 a{op}b{op}c 表示 (a{op}b){op}c。\n\n"
        f"已知 {a}{op}X{op}{b} = {t}，且 X 为正整数。\n"
        f"在 1 到 {x_max} 的范围内，求 X。"
    )
    answer = sols[0]

    # Provide a concrete verification trail for the found X
    mid = op_yen(a, answer)
    final = op_yen(mid, b)
    explanation = (
        f"按从左到右：({a}{op}X){op}{b}。\n"
        f"枚举 X=1..{x_max}，只有 X={answer} 满足等式。\n"
        f"核算：先算 {a}{op}{answer} = {a}^{answer} - {answer}^{a} = "
        f"{pow(a,answer)} - {pow(answer,a)} = {mid}；\n"
        f"再算 {mid}{op}{b} = {mid}^{b} - {b}^{mid} = {final}，恰为 {t}。"
    )

    assert answer == x_true
    assert chain_left(a, answer, b) == t
    return problem, answer, explanation


# -------------------- Family D: Ask for sign / comparison based on a¥b --------------------
def gen_sign_or_compare(rng: random.Random) -> Tuple[str, Any, str]:
    # Choose a!=b to reduce trivial zero
    a = rng.randint(2, 9)
    b = rng.randint(2, 9)
    while b == a:
        b = rng.randint(2, 9)

    val = op_yen(a, b)
    # Ask: determine sign: -1 / 0 / 1
    problem = (
        "定义一种新运算：对正整数 a,b，规定 a¥b = a^b - b^a。\n\n"
        f"判断 {a}¥{b} 的符号：\n"
        "若为正数输出 1，若为 0 输出 0，若为负数输出 -1。"
    )
    if val > 0:
        ans = 1
    elif val == 0:
        ans = 0
    else:
        ans = -1

    explanation = (
        f"先计算 {a}¥{b} = {a}^{b} - {b}^{a} = {pow(a,b)} - {pow(b,a)} = {val}。\n"
        f"因此其符号对应输出 {ans}。"
    )
    assert (ans == 1 and val > 0) or (ans == 0 and val == 0) or (ans == -1 and val < 0)
    return problem, ans, explanation


# -------------------- Orchestration --------------------
def make_generator(rng: random.Random):
    # Weighted selection among families for diversity
    families = [
        ("direct", gen_direct_compute, 0.35),
        ("solve_left", gen_solve_left, 0.25),
        ("chain_left", gen_chain_left_equation, 0.25),
        ("sign", gen_sign_or_compare, 0.15),
    ]
    # Build cumulative
    cum = []
    s = 0.0
    for name, fn, w in families:
        s += w
        cum.append((s, name, fn))
    # normalize
    for i in range(len(cum)):
        cum[i] = (cum[i][0] / s, cum[i][1], cum[i][2])

    def pick():
        r = rng.random()
        for c, name, fn in cum:
            if r <= c:
                return name, fn
        return cum[-1][1], cum[-1][2]

    return pick


def dedup_key(problem: str) -> str:
    # Simple dedup by exact problem text
    return problem.strip()


def generate(seed: int, count: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    pick = make_generator(rng)

    out = []
    seen = set()
    attempts = 0
    max_attempts = max(200, count * 40)

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            _, fn = pick()
            problem, answer, explanation = fn(rng)
            if not isinstance(problem, str) or not problem.strip():
                continue
            if not isinstance(explanation, str):
                continue
            key = dedup_key(problem)
            if key in seen:
                continue
            seen.add(key)
            out.append({"problem": problem, "answer": answer, "explanation": explanation})
        except Exception as e:
            # real failure; continue sampling but keep bounded
            print(f"[gen warning] {type(e).__name__}: {e}", file=sys.stderr)
            continue

    if len(out) != count:
        raise RuntimeError(f"Only generated {len(out)}/{count} problems after {attempts} attempts.")
    return out


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    if count <= 0:
        raise ValueError("count must be positive")
    res = generate(seed, count)
    json.dump(res, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()