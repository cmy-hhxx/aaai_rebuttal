import sys, json, math, itertools, random
from fractions import Fraction
from typing import List, Tuple, Optional, Dict, Any

# =========================
# Core math for custom op
# =========================

def even_numbers_between(a: int, b: int) -> List[int]:
    lo, hi = (a, b) if a <= b else (b, a)
    start = lo if lo % 2 == 0 else lo + 1
    if start > hi:
        return []
    return list(range(start, hi + 1, 2))

def avg_evens(a: int, b: int) -> Optional[Fraction]:
    evs = even_numbers_between(a, b)
    if not evs:
        return None
    return Fraction(sum(evs), len(evs))

def avg_evens_via_formula(a: int, b: int) -> Optional[Fraction]:
    lo, hi = (a, b) if a <= b else (b, a)
    first = lo if lo % 2 == 0 else lo + 1
    last = hi if hi % 2 == 0 else hi - 1
    if first > last:
        return None
    n = ((last - first) // 2) + 1
    # average of arithmetic progression = (first+last)/2
    return Fraction(first + last, 2)

def fmt_fraction(fr: Fraction) -> str:
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"{fr.numerator}/{fr.denominator}"

def wrap_answer(value: str) -> str:
    return f"[[{value}]]"

def parse_op(a: int, b: int) -> Fraction:
    v = avg_evens(a, b)
    if v is None:
        raise ValueError("区间内没有偶数，运算未定义")
    return v

# =========================
# Problem families
# =========================

def make_problem_family_A(rng: random.Random) -> Dict[str, Any]:
    """
    Two-part problem:
    (1) compute a#b
    (2) solve a#X = t for integer X in a bounded range, possibly multiple solutions.
    Ensure at least one solution exists; allow multiple solutions by design sometimes.
    """
    # Choose a fixed a and b for part (1)
    a = rng.randint(-9, 15)
    b = rng.randint(a + 2, a + 26) if rng.random() < 0.7 else rng.randint(-15, 25)
    if rng.random() < 0.25:
        # occasionally swap to test "between" meaning irrespective of order
        a1, b1 = b, a
    else:
        a1, b1 = a, b

    v1 = avg_evens(a1, b1)
    # ensure defined
    if v1 is None:
        # adjust b to include an even
        b1 = a1 + (1 if a1 % 2 == 0 else 2)
        v1 = avg_evens(a1, b1)
    assert v1 is not None

    # Part (2): pick a2 and a solution X0, build t = a2#X0
    a2 = rng.randint(-8, 12)
    # choose X0 not too close; allow both sides
    X0 = rng.randint(a2 - 2, a2 + 24)
    # ensure there is at least one even in [a2, X0]
    if not even_numbers_between(a2, X0):
        X0 += 1
    t = avg_evens(a2, X0)
    if t is None:
        raise RuntimeError("构造失败：t 未定义")
    # We will ask for all integer X in [L,U] such that a2#X == t
    L = min(a2, X0) - rng.randint(0, 6)
    U = max(a2, X0) + rng.randint(3, 10)
    # Keep range reasonable
    L = max(L, -20)
    U = min(U, 40)
    if L > U:
        L, U = U, L

    sols = []
    for X in range(L, U + 1):
        val = avg_evens(a2, X)
        if val is not None and val == t:
            sols.append(X)

    # ensure at least one solution, and not too many
    if not sols or len(sols) > 12:
        raise RuntimeError("构造失败：解的数量不合适")

    # prepare outputs
    ans1 = fmt_fraction(v1)
    ans2 = "or".join(str(s) for s in sols)

    # Cross-check with formula path
    v1_f = avg_evens_via_formula(a1, b1)
    t_f = avg_evens_via_formula(a2, X0)
    if v1_f != v1 or t_f != t:
        raise RuntimeError("交叉核验失败：公式法与枚举法不一致")

    # Explanation: show evens list for part (1), and show t and a couple checks for part (2)
    evs1 = even_numbers_between(a1, b1)
    exp_lines = []
    exp_lines.append("定义：a#b 等于 a 到 b（含端点）之间所有偶数的平均数。")
    exp_lines.append(f"(1) {a1}#{b1}：区间内偶数为 {evs1}，平均数 = {sum(evs1)}/{len(evs1)} = {fmt_fraction(v1)}。")
    exp_lines.append(f"(2) 解 {a2}#X = {fmt_fraction(t)}，并限定 X 为整数且 X∈[{L},{U}]。")
    # show derivation of t via endpoints first/last even for the constructed solution X0
    lo, hi = (a2, X0) if a2 <= X0 else (X0, a2)
    first = lo if lo % 2 == 0 else lo + 1
    last = hi if hi % 2 == 0 else hi - 1
    if first <= last:
        exp_lines.append(f"例如取构造用的一个满足值：X={X0} 时，区间偶数首项={first}、末项={last}，平均数=(首项+末项)/2={(first+last)}/2={fmt_fraction(t)}。")
    # show check for first two solutions
    show_s = sols[:2]
    for s in show_s:
        evs = even_numbers_between(a2, s)
        exp_lines.append(f"检验：X={s} 时偶数为 {evs}，其平均数为 {fmt_fraction(avg_evens(a2, s))}。")
    exp_lines.append(f"因此满足条件的 X 为：{ans2}。")

    problem = (
        "给定自定义运算：a#b 表示 a 与 b（含端点）之间所有偶数的平均数。\n"
        f"1）计算 {a1}#{b1}。答案用双中括号表示，例如 [[6]]。\n"
        f"2）在 X 为整数且 X∈[{L},{U}] 的条件下，解方程 {a2}#X = {fmt_fraction(t)}。\n"
        "若有多个解，用 or 连接，并用双中括号表示，例如 [[1or2]]。"
    )

    answer = wrap_answer(ans1) + "====" + wrap_answer(ans2)
    return {"problem": problem, "answer": answer, "explanation": "\n".join(exp_lines)}

def make_problem_family_B(rng: random.Random) -> Dict[str, Any]:
    """
    Three-part variant (still same core skill: apply custom operation + solve equation):
    (1) compute a#b
    (2) compute (a#b) + (c#d) or difference
    (3) solve for X such that p#X equals a given rational; restrict X range
    """
    a, b = rng.randint(-10, 20), rng.randint(-10, 20)
    if a == b:
        b += 3
    # ensure defined
    if not even_numbers_between(a, b):
        b += 1
    c, d = rng.randint(-12, 18), rng.randint(-12, 18)
    if c == d:
        d -= 4
    if not even_numbers_between(c, d):
        d -= 1

    v_ab = avg_evens(a, b)
    v_cd = avg_evens(c, d)
    if v_ab is None or v_cd is None:
        raise RuntimeError("构造失败：未定义")

    op = rng.choice(["+", "-"])
    if op == "+":
        v2 = v_ab + v_cd
        op_text = "相加"
        expr_text = f"({a}#{b}) + ({c}#{d})"
    else:
        v2 = v_ab - v_cd
        op_text = "相减"
        expr_text = f"({a}#{b}) - ({c}#{d})"

    # Part (3): choose p and an X0 to create target
    p = rng.randint(-6, 10)
    X0 = rng.randint(p - 1, p + 18)
    if not even_numbers_between(p, X0):
        X0 += 1
    tgt = avg_evens(p, X0)
    if tgt is None:
        raise RuntimeError("构造失败：tgt 未定义")

    L = min(p, X0) - rng.randint(0, 5)
    U = max(p, X0) + rng.randint(2, 9)
    L = max(L, -20)
    U = min(U, 40)

    sols = []
    for X in range(L, U + 1):
        val = avg_evens(p, X)
        if val is not None and val == tgt:
            sols.append(X)
    if not sols or len(sols) > 14:
        raise RuntimeError("构造失败：解的数量不合适")

    # cross-check numeric via formula
    if avg_evens_via_formula(a, b) != v_ab or avg_evens_via_formula(c, d) != v_cd:
        raise RuntimeError("交叉核验失败")

    ans1 = fmt_fraction(v_ab)
    ans2 = fmt_fraction(v2)
    ans3 = "or".join(str(s) for s in sols)

    ev_ab = even_numbers_between(a, b)
    ev_cd = even_numbers_between(c, d)

    exp = []
    exp.append("定义：a#b 为 a 到 b（含端点）之间所有偶数的平均数。")
    exp.append(f"(1) {a}#{b}：偶数为 {ev_ab}，平均数 = {fmt_fraction(v_ab)}。")
    exp.append(f"(2) {expr_text}（{op_text}）：{fmt_fraction(v_ab)} {op} {fmt_fraction(v_cd)} = {fmt_fraction(v2)}，其中 {c}#{d} 的偶数为 {ev_cd}。")
    exp.append(f"(3) 解 {p}#X = {fmt_fraction(tgt)}，限制 X 为整数且 X∈[{L},{U}]。满足条件的 X 为：{ans3}。")

    problem = (
        "给定自定义运算：a#b 表示 a 与 b（含端点）之间所有偶数的平均数。\n"
        f"1）计算 {a}#{b}。\n"
        f"2）计算 {expr_text}。\n"
        f"3）在 X 为整数且 X∈[{L},{U}] 的条件下，解 {p}#X = {fmt_fraction(tgt)}。\n"
        "每问答案都用双中括号表示；第 3 问若多解用 or 连接。"
    )
    answer = "====".join([wrap_answer(ans1), wrap_answer(ans2), wrap_answer(ans3)])
    return {"problem": problem, "answer": answer, "explanation": "\n".join(exp)}

# =========================
# Generator orchestration
# =========================

def generate_one(rng: random.Random) -> Dict[str, Any]:
    # Choose a family with probability
    family = rng.choices(["A", "B"], weights=[0.7, 0.3], k=1)[0]
    if family == "A":
        return make_problem_family_A(rng)
    else:
        return make_problem_family_B(rng)

def signature(item: Dict[str, Any]) -> str:
    # lightweight dedup signature
    return item["problem"]

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results = []
    seen = set()

    max_attempts = 2000
    attempts = 0
    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng)
            sig = signature(item)
            if sig in seen:
                continue
            # basic sanity checks
            if not isinstance(item.get("problem"), str) or not item["problem"].strip():
                raise RuntimeError("空题面")
            if "answer" not in item:
                raise RuntimeError("缺少答案")
            if not isinstance(item.get("explanation"), str) or not item["explanation"].strip():
                raise RuntimeError("缺少解析")
            seen.add(sig)
            results.append(item)
        except Exception as e:
            # resample
            print(f"[warn] 生成失败：{e}", file=sys.stderr)
            continue

    if len(results) != count:
        raise SystemExit(f"无法生成足够数量的题目：需要 {count}，实际 {len(results)}。请更换 seed 或降低 count。")

    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()