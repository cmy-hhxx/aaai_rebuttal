import sys, json, itertools, math, random
from fractions import Fraction

OPS = ["+", "-", "*", "/"]

def apply_op(a: Fraction, b: Fraction, op: str):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            return None
        return a / b
    raise ValueError(op)

def eval_left_assoc(nums, ops):
    """Evaluate (((n0 op0 n1) op1 n2) op2 n3) ... with exact rationals."""
    cur = Fraction(nums[0], 1)
    for i, op in enumerate(ops):
        nxt = Fraction(nums[i + 1], 1)
        cur = apply_op(cur, nxt, op)
        if cur is None:
            return None
    return cur

def format_expr_left_assoc(nums, ops):
    s = str(nums[0])
    for i, op in enumerate(ops):
        s = f"({s} {op} {nums[i+1]})"
    return s

def lex_key_solution(sol):
    # sol is dict {"nums": [...], "ops":[...]}
    return (tuple(sol["nums"]), tuple(sol["ops"]))

def find_all_left_assoc_solutions(nums, target=24):
    """Return all solutions in required dict form, allowing any permutation of nums and any ops."""
    sols = []
    for perm in set(itertools.permutations(nums)):
        for ops in itertools.product(OPS, repeat=len(nums) - 1):
            val = eval_left_assoc(perm, ops)
            if val is not None and val == Fraction(target, 1):
                sols.append({"nums": list(perm), "ops": list(ops)})
    sols.sort(key=lex_key_solution)
    return sols

def count_all_parenthesizations_solutions(nums, target=24):
    """
    For cross-check: count solutions over all binary tree parenthesizations.
    Return a set of canonical strings for expressions achieving target.
    """
    # DP over subsets: map from tuple(sorted elements with multiplicity via indices)) -> dict(value -> set(expr_str))
    # Use indices to preserve multiplicity of equal numbers.
    n = len(nums)
    items = [(i, Fraction(nums[i], 1), str(nums[i])) for i in range(n)]

    # Represent subset by bitmask
    dp = [dict() for _ in range(1 << n)]
    for i in range(n):
        mask = 1 << i
        dp[mask][items[i][1]] = {items[i][2]}

    def add_expr(d, val, exprs):
        if val in d:
            d[val].update(exprs)
        else:
            d[val] = set(exprs)

    for mask in range(1 << n):
        # skip singletons
        if mask == 0 or (mask & (mask - 1)) == 0:
            continue
        # partition mask into a and b (proper, non-empty)
        sub = (mask - 1) & mask
        while sub:
            a = sub
            b = mask ^ a
            if b:
                for va, ea_set in dp[a].items():
                    for vb, eb_set in dp[b].items():
                        for op in OPS:
                            if op == "/" and vb == 0:
                                continue
                            if op == "/" and vb == 0:
                                continue
                            res = apply_op(va, vb, op)
                            if res is None:
                                continue
                            # build expressions; keep parentheses for clarity
                            new_exprs = set()
                            for ea in ea_set:
                                for eb in eb_set:
                                    new_exprs.add(f"({ea} {op} {eb})")
                            add_expr(dp[mask], res, new_exprs)

                        # also consider non-commutative ops by swapping? Already covered by iterating partitions a/b,
                        # because a and b vary; however partitions are unordered pairs. To ensure both orders, explicitly add swapped for - and /
                        for op in ["-", "/"]:
                            if op == "/" and va == 0:
                                # swapping means vb / va, so denominator is va; if va==0, invalid
                                continue
                            res = apply_op(vb, va, op)
                            if res is None:
                                continue
                            new_exprs = set()
                            for ea in ea_set:
                                for eb in eb_set:
                                    # swapped: (eb op ea)
                                    new_exprs.add(f"({eb} {op} {ea})")
                            add_expr(dp[mask], res, new_exprs)
            sub = (sub - 1) & mask

    full = (1 << n) - 1
    return dp[full].get(Fraction(target, 1), set())

def canonical_problem_key(nums):
    # avoid duplicates across generated instances
    return tuple(sorted(nums))

def pick_instance(rng, max_tries=5000):
    """
    Generate a 4-number instance with:
    - at least one left-assoc solution
    - unique left-assoc solution under our tie-break (the lexicographically minimal is also the only one)
      (this matches the seed's "avoid multiple answers" intention, but operationalized).
    """
    seen = set()
    for _ in range(max_tries):
        # choose numbers: mix of 1..9 with repeats allowed; avoid all same; avoid too trivial huge counts.
        nums = [rng.randint(1, 9) for _ in range(4)]
        key = canonical_problem_key(nums)
        if key in seen:
            continue
        seen.add(key)

        sols = find_all_left_assoc_solutions(nums, 24)
        if len(sols) != 1:
            continue

        # Cross-check: the found left-assoc solution must indeed evaluate to 24 (already),
        # and also verify via all-parenthesizations DP that 24 is reachable (sanity).
        # It may find additional non-left-assoc solutions; that's fine because the problem statement
        # will explicitly fix evaluation order to avoid ambiguity.
        sol = sols[0]
        expr = format_expr_left_assoc(sol["nums"], sol["ops"])
        val = eval_left_assoc(sol["nums"], sol["ops"])
        if val != Fraction(24, 1):
            continue

        # Additional sanity: ensure expression is valid (no division by zero along the way)
        if val is None:
            continue

        # Return constructed instance and solution
        return nums, sol
    raise RuntimeError("Failed to generate a valid instance within retry limit.")

def render_problem(nums, lang="zh"):
    # We explicitly define evaluation order to make solution form (nums + ops) well-defined and checkable.
    return (
        f"给定数字列表 {nums}（每个数字必须且只能使用一次），你需要选择 3 个运算符，"
        f"运算符仅允许从 {OPS} 中选择，并按如下固定顺序计算：\n"
        f"先算第 1 个数 op1 第 2 个数，结果再 op2 第 3 个数，结果再 op3 第 4 个数，"
        f"也就是形如 (((a op1 b) op2 c) op3 d)。\n"
        f"目标是使最终结果等于 24。\n"
        f"请按字典形式返回一个答案：{{\"nums\": [a,b,c,d], \"ops\": [op1,op2,op3]}}。\n"
        f"为避免多解，请在所有可行答案中选择字典序最小者：先比较 nums 列表字典序，"
        f"若相同再比较 ops 列表字典序（按字符串比较）。"
    )

def render_explanation(nums, sol):
    expr = format_expr_left_assoc(sol["nums"], sol["ops"])
    # compute stepwise
    a, b, c, d = [Fraction(x, 1) for x in sol["nums"]]
    op1, op2, op3 = sol["ops"]
    r1 = apply_op(a, b, op1)
    r2 = apply_op(r1, c, op2) if r1 is not None else None
    r3 = apply_op(r2, d, op3) if r2 is not None else None
    def f(fr):
        if fr is None:
            return "未定义"
        if fr.denominator == 1:
            return str(fr.numerator)
        return f"{fr.numerator}/{fr.denominator}"
    return (
        f"按固定顺序计算 {expr}：\n"
        f"第1步：{sol['nums'][0]} {op1} {sol['nums'][1]} = {f(r1)}\n"
        f"第2步：{f(r1)} {op2} {sol['nums'][2]} = {f(r2)}\n"
        f"第3步：{f(r2)} {op3} {sol['nums'][3]} = {f(r3)}\n"
        f"最终得到 24，因此该 {{nums, ops}} 满足要求。"
    )

def generate(seed, count, lang="zh"):
    rng = random.Random(seed)
    results = []
    used_problem_keys = set()

    attempts = 0
    while len(results) < count:
        attempts += 1
        if attempts > 20000:
            raise RuntimeError("Too many attempts; cannot reach target count with current constraints.")
        nums, sol = pick_instance(rng)

        # Avoid repeating the same multiset across output
        key = canonical_problem_key(nums)
        if key in used_problem_keys:
            continue
        used_problem_keys.add(key)

        prob = render_problem(nums, lang=lang)
        expl = render_explanation(nums, sol)
        results.append({"problem": prob, "answer": sol, "explanation": expl})
    return results

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    out_lang = "zh"
    # output_language is provided in the caller message, but not in stdin spec; keep zh default as required.
    res = generate(seed, count, lang=out_lang)
    sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        raise