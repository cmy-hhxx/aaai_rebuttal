import sys, json, random, math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional, Set

# We will generate problems about the custom operation:
# A ￡ B = (A ∪ B) − (A ∩ B)  (symmetric difference)
#
# Domain is typically subsets of integers described by simple predicates
# (parity, sign, modular class, intervals, divisibility, membership in a small set, etc.)
# To keep problems self-contained and solvable without ambiguity, every set is defined as
# a subset of a specified finite universe U.
#
# The answer is always a set, wrapped as [[{...}]] (double square brackets).
#
# We also provide short, checkable explanations and do internal verification.

def eprint(*args):
    print(*args, file=sys.stderr)

def format_set_elems(elems: List[int]) -> str:
    # Render as {a,b,c} with ascending order; empty set as {}
    if not elems:
        return "{}"
    return "{" + ",".join(str(x) for x in elems) + "}"

def wrap_double_square(s: str) -> str:
    return "[[" + s + "]]"

# ----- Predicate system over integers -----

@dataclass(frozen=True)
class Pred:
    kind: str
    params: Tuple[Any, ...]

    def holds(self, x: int) -> bool:
        k = self.kind
        p = self.params
        if k == "even":
            return x % 2 == 0
        if k == "odd":
            return x % 2 != 0
        if k == "positive":
            return x > 0
        if k == "negative":
            return x < 0
        if k == "nonnegative":
            return x >= 0
        if k == "nonpositive":
            return x <= 0
        if k == "multiple_of":
            d = p[0]
            return d != 0 and x % d == 0
        if k == "not_multiple_of":
            d = p[0]
            return d != 0 and x % d != 0
        if k == "congruent":
            r, m = p
            return m > 0 and ((x - r) % m == 0)
        if k == "in_interval":
            lo, hi = p
            return lo <= x <= hi
        if k == "in_set":
            S = p[0]
            return x in S
        if k == "not_in_set":
            S = p[0]
            return x not in S
        if k == "prime":
            if x < 2:
                return False
            if x == 2:
                return True
            if x % 2 == 0:
                return False
            r = int(math.isqrt(x))
            for t in range(3, r + 1, 2):
                if x % t == 0:
                    return False
            return True
        if k == "composite":
            if x < 4:
                return False
            if x % 2 == 0:
                return x != 2
            r = int(math.isqrt(x))
            for t in range(3, r + 1, 2):
                if x % t == 0:
                    return True
            return False
        raise ValueError(f"Unknown predicate kind: {k}")

    def describe(self) -> str:
        k = self.kind
        p = self.params
        if k == "even":
            return "x 是偶数"
        if k == "odd":
            return "x 是奇数"
        if k == "positive":
            return "x 是正整数"
        if k == "negative":
            return "x 是负整数"
        if k == "nonnegative":
            return "x 是非负整数"
        if k == "nonpositive":
            return "x 是非正整数"
        if k == "multiple_of":
            return f"x 是 {p[0]} 的倍数"
        if k == "not_multiple_of":
            return f"x 不是 {p[0]} 的倍数"
        if k == "congruent":
            r, m = p
            return f"x ≡ {r} (mod {m})"
        if k == "in_interval":
            lo, hi = p
            return f"{lo} ≤ x ≤ {hi}"
        if k == "in_set":
            S = sorted(p[0])
            return "x 属于集合 " + format_set_elems(S)
        if k == "not_in_set":
            S = sorted(p[0])
            return "x 不属于集合 " + format_set_elems(S)
        if k == "prime":
            return "x 是质数"
        if k == "composite":
            return "x 是合数"
        raise ValueError(f"Unknown predicate kind: {k}")

@dataclass
class SetDef:
    name: str
    universe: List[int]
    pred: Pred

    def materialize(self) -> Set[int]:
        return {x for x in self.universe if self.pred.holds(x)}

    def render(self) -> str:
        Umin, Umax = min(self.universe), max(self.universe)
        # Universe shown explicitly to avoid ambiguity
        return f"{self.name} = {{x ∈ U | {self.pred.describe()} }}"

def symmetric_difference(A: Set[int], B: Set[int]) -> Set[int]:
    return (A | B) - (A & B)

# ----- Generation families -----

def gen_universe(rng: random.Random) -> List[int]:
    # Choose a manageable finite universe U = {L, L+1, ..., R}
    # Ensure it includes 0 often, but allow ranges not centered.
    L = rng.randint(-12, -2)
    R = rng.randint(8, 18)
    if L >= R:
        L, R = -10, 10
    U = list(range(L, R + 1))
    return U

def choose_pred(rng: random.Random, U: List[int], allow_set_membership: bool = True) -> Pred:
    # Weighted choices for variety
    kinds = [
        ("even", 2),
        ("odd", 2),
        ("positive", 2),
        ("negative", 2),
        ("nonnegative", 2),
        ("nonpositive", 2),
        ("multiple_of", 3),
        ("not_multiple_of", 2),
        ("congruent", 3),
        ("in_interval", 2),
        ("prime", 1),
        ("composite", 1),
    ]
    if allow_set_membership:
        kinds += [("in_set", 2), ("not_in_set", 2)]
    pool = []
    for k, w in kinds:
        pool.extend([k] * w)
    kind = rng.choice(pool)

    if kind in ("even", "odd", "positive", "negative", "nonnegative", "nonpositive", "prime", "composite"):
        return Pred(kind, ())
    if kind in ("multiple_of", "not_multiple_of"):
        d = rng.randint(2, 7)
        return Pred(kind, (d,))
    if kind == "congruent":
        m = rng.randint(3, 8)
        r = rng.randint(0, m - 1)
        # sometimes use negative remainder representative for variety
        if rng.random() < 0.25:
            r = r - m
        return Pred(kind, (r, m))
    if kind == "in_interval":
        lo = rng.randint(min(U), max(U) - 2)
        hi = rng.randint(lo + 1, max(U))
        return Pred(kind, (lo, hi))
    if kind in ("in_set", "not_in_set"):
        # choose a small subset of U
        size = rng.randint(2, min(6, len(U)))
        S = set(rng.sample(U, size))
        return Pred(kind, (frozenset(S),))
    raise ValueError("unreachable")

def gen_problem_family_basic(rng: random.Random) -> Dict[str, Any]:
    # Two predicate-defined subsets over same finite universe.
    U = gen_universe(rng)
    predA = choose_pred(rng, U, allow_set_membership=True)
    predB = choose_pred(rng, U, allow_set_membership=True)

    # Ensure A and B are not identical too often, and produce nontrivial symmetric diff.
    Adef = SetDef("A", U, predA)
    Bdef = SetDef("B", U, predB)
    A = Adef.materialize()
    B = Bdef.materialize()
    SD = symmetric_difference(A, B)

    return {
        "U": U, "Adef": Adef, "Bdef": Bdef,
        "A": A, "B": B, "SD": SD,
        "family": "basic"
    }

def gen_problem_family_three_sets(rng: random.Random) -> Dict[str, Any]:
    # Combine operation nested: (A ￡ B) ￡ C or A ￡ (B ￡ C)
    U = gen_universe(rng)
    predA = choose_pred(rng, U, allow_set_membership=True)
    predB = choose_pred(rng, U, allow_set_membership=True)
    predC = choose_pred(rng, U, allow_set_membership=True)
    Adef = SetDef("A", U, predA)
    Bdef = SetDef("B", U, predB)
    Cdef = SetDef("C", U, predC)
    A = Adef.materialize()
    B = Bdef.materialize()
    C = Cdef.materialize()

    form = rng.choice(["left", "right"])
    if form == "left":
        # (A ￡ B) ￡ C
        SD1 = symmetric_difference(A, B)
        SD = symmetric_difference(SD1, C)
        query = "(A ￡ B) ￡ C"
    else:
        SD1 = symmetric_difference(B, C)
        SD = symmetric_difference(A, SD1)
        query = "A ￡ (B ￡ C)"

    return {
        "U": U, "Adef": Adef, "Bdef": Bdef, "Cdef": Cdef,
        "A": A, "B": B, "C": C,
        "SD": SD, "query": query,
        "family": "three"
    }

def gen_problem_family_complement(rng: random.Random) -> Dict[str, Any]:
    # Define B as complement-like relative to U (explicit rule), still self-contained.
    U = gen_universe(rng)
    predA = choose_pred(rng, U, allow_set_membership=True)
    Adef = SetDef("A", U, predA)
    A = Adef.materialize()

    # Define B with a different predicate; also define D = U \\ B or similar
    predB = choose_pred(rng, U, allow_set_membership=True)
    Bdef = SetDef("B", U, predB)
    B = Bdef.materialize()

    # Ask for A ￡ (U\\B) or (U\\A) ￡ B
    form = rng.choice(["A_xor_compB", "compA_xor_B"])
    Uset = set(U)
    if form == "A_xor_compB":
        compB = Uset - B
        SD = symmetric_difference(A, compB)
        query = "A ￡ (U \\ B)"
    else:
        compA = Uset - A
        SD = symmetric_difference(compA, B)
        query = "(U \\ A) ￡ B"

    return {
        "U": U, "Adef": Adef, "Bdef": Bdef,
        "A": A, "B": B, "SD": SD, "query": query,
        "family": "comp", "form": form
    }

# ----- Rendering -----

def render_universe(U: List[int]) -> str:
    return "U = " + format_set_elems(sorted(U))

def render_problem_basic(data: Dict[str, Any], lang: str) -> Tuple[str, Any, str]:
    U = data["U"]
    Adef: SetDef = data["Adef"]
    Bdef: SetDef = data["Bdef"]
    A = data["A"]
    B = data["B"]
    SD = data["SD"]

    problem = (
        "你需要根据自定义运算规则计算集合结果。\n\n"
        "### 运算规则\n"
        "A ￡ B = (A ∪ B) − (A ∩ B)。\n\n"
        "### 已知\n"
        f"{render_universe(U)}。\n"
        f"{Adef.render()}。\n"
        f"{Bdef.render()}。\n\n"
        "### 问题\n"
        "计算 A ￡ B。\n"
        "请将答案用双层方括号包裹，并以集合形式给出，例如 [[{1,2,3}]]。\n"
    )

    ans_elems = sorted(SD)
    answer = wrap_double_square(format_set_elems(ans_elems))

    # Explanation with explicit union/intersection for verification
    union = sorted(A | B)
    inter = sorted(A & B)
    expl = (
        f"先由定义在 U 中列出：A = {format_set_elems(sorted(A))}，B = {format_set_elems(sorted(B))}。\n"
        f"A ∪ B = {format_set_elems(union)}，A ∩ B = {format_set_elems(inter)}。\n"
        f"A ￡ B = (A ∪ B) − (A ∩ B) = {format_set_elems(ans_elems)}。"
    )
    return problem, answer, expl

def render_problem_three(data: Dict[str, Any]) -> Tuple[str, Any, str]:
    U = data["U"]
    Adef: SetDef = data["Adef"]
    Bdef: SetDef = data["Bdef"]
    Cdef: SetDef = data["Cdef"]
    A, B, C = data["A"], data["B"], data["C"]
    SD = data["SD"]
    query = data["query"]

    problem = (
        "你需要根据自定义运算规则计算集合结果。\n\n"
        "### 运算规则\n"
        "A ￡ B = (A ∪ B) − (A ∩ B)。\n\n"
        "### 已知\n"
        f"{render_universe(U)}。\n"
        f"{Adef.render()}。\n"
        f"{Bdef.render()}。\n"
        f"{Cdef.render()}。\n\n"
        "### 问题\n"
        f"计算 {query}。\n"
        "请将答案用双层方括号包裹，并以集合形式给出，例如 [[{1,2,3}]]。\n"
    )

    ans_elems = sorted(SD)
    answer = wrap_double_square(format_set_elems(ans_elems))

    # Provide step-by-step with one intermediate symmetric difference
    if query == "(A ￡ B) ￡ C":
        SD1 = symmetric_difference(A, B)
        expl = (
            f"先在 U 中得到：A = {format_set_elems(sorted(A))}，B = {format_set_elems(sorted(B))}，C = {format_set_elems(sorted(C))}。\n"
            f"A ￡ B = {format_set_elems(sorted(SD1))}。\n"
            f"(A ￡ B) ￡ C = {format_set_elems(ans_elems)}。"
        )
    else:
        SD1 = symmetric_difference(B, C)
        expl = (
            f"先在 U 中得到：A = {format_set_elems(sorted(A))}，B = {format_set_elems(sorted(B))}，C = {format_set_elems(sorted(C))}。\n"
            f"B ￡ C = {format_set_elems(sorted(SD1))}。\n"
            f"A ￡ (B ￡ C) = {format_set_elems(ans_elems)}。"
        )
    return problem, answer, expl

def render_problem_comp(data: Dict[str, Any]) -> Tuple[str, Any, str]:
    U = data["U"]
    Uset = set(U)
    Adef: SetDef = data["Adef"]
    Bdef: SetDef = data["Bdef"]
    A, B = data["A"], data["B"]
    SD = data["SD"]
    query = data["query"]

    problem = (
        "你需要根据自定义运算规则计算集合结果。\n\n"
        "### 运算规则\n"
        "A ￡ B = (A ∪ B) − (A ∩ B)。\n\n"
        "### 已知\n"
        f"{render_universe(U)}。\n"
        f"{Adef.render()}。\n"
        f"{Bdef.render()}。\n"
        "并且补集（相对 U）定义为：U \\ S = {x ∈ U | x 不属于 S}。\n\n"
        "### 问题\n"
        f"计算 {query}。\n"
        "请将答案用双层方括号包裹，并以集合形式给出，例如 [[{1,2,3}]]。\n"
    )

    ans_elems = sorted(SD)
    answer = wrap_double_square(format_set_elems(ans_elems))

    if query == "A ￡ (U \\ B)":
        compB = Uset - B
        expl = (
            f"在 U 中列出：A = {format_set_elems(sorted(A))}，B = {format_set_elems(sorted(B))}。\n"
            f"U \\ B = {format_set_elems(sorted(compB))}。\n"
            f"A ￡ (U \\ B) = {format_set_elems(ans_elems)}。"
        )
    else:
        compA = Uset - A
        expl = (
            f"在 U 中列出：A = {format_set_elems(sorted(A))}，B = {format_set_elems(sorted(B))}。\n"
            f"U \\ A = {format_set_elems(sorted(compA))}。\n"
            f"(U \\ A) ￡ B = {format_set_elems(ans_elems)}。"
        )
    return problem, answer, expl

# ----- Validation -----

def validate_instance(data: Dict[str, Any]) -> bool:
    # Check that the displayed constraints suffice: because U is finite and sets are defined in terms of U,
    # the result is uniquely determined.
    # Also ensure not too trivial too often (e.g., SD equals empty) by rejecting sometimes.
    SD = data["SD"]
    # accept empty sometimes, but not too frequently; handled in sampling logic
    return True

def cross_check(data: Dict[str, Any]) -> None:
    # Independent verification by elementwise definition:
    U = data["U"]
    if data["family"] == "basic":
        Adef: SetDef = data["Adef"]
        Bdef: SetDef = data["Bdef"]
        for x in U:
            a = Adef.pred.holds(x)
            b = Bdef.pred.holds(x)
            sd_expected = (a and not b) or (b and not a)
            sd_in = x in data["SD"]
            if sd_expected != sd_in:
                raise AssertionError("cross-check failed for basic")
    elif data["family"] == "three":
        # compute by membership parity in A,B,C depending on expression
        Adef: SetDef = data["Adef"]
        Bdef: SetDef = data["Bdef"]
        Cdef: SetDef = data["Cdef"]
        query = data["query"]
        for x in U:
            a = Adef.pred.holds(x)
            b = Bdef.pred.holds(x)
            c = Cdef.pred.holds(x)
            if query == "(A ￡ B) ￡ C":
                # XOR XOR
                sd_expected = (a ^ b) ^ c
            else:
                sd_expected = a ^ (b ^ c)
            sd_in = x in data["SD"]
            if sd_expected != sd_in:
                raise AssertionError("cross-check failed for three")
    elif data["family"] == "comp":
        Adef: SetDef = data["Adef"]
        Bdef: SetDef = data["Bdef"]
        query = data["query"]
        for x in U:
            a = Adef.pred.holds(x)
            b = Bdef.pred.holds(x)
            if query == "A ￡ (U \\ B)":
                # compB means not b within U; since x in U always, just use not b
                sd_expected = a ^ (not b)
            else:
                sd_expected = (not a) ^ b
            sd_in = x in data["SD"]
            if sd_expected != sd_in:
                raise AssertionError("cross-check failed for comp")
    else:
        raise AssertionError("unknown family")

def make_one(rng: random.Random, lang: str, attempt_limit: int = 200) -> Dict[str, Any]:
    # Rejection sampling to ensure diversity and avoid too many empty/huge sets.
    for _ in range(attempt_limit):
        family = rng.choices(["basic", "three", "comp"], weights=[6, 3, 3], k=1)[0]
        if family == "basic":
            data = gen_problem_family_basic(rng)
        elif family == "three":
            data = gen_problem_family_three_sets(rng)
        else:
            data = gen_problem_family_complement(rng)

        # Nontriviality heuristics
        U = data["U"]
        SD = data["SD"]
        if len(SD) == 0 and rng.random() < 0.75:
            continue
        if len(SD) == len(U) and rng.random() < 0.6:
            continue

        # Ensure A and B are not both extremely tiny too often in basic
        if data["family"] == "basic":
            if len(data["A"]) <= 1 and len(data["B"]) <= 1 and rng.random() < 0.7:
                continue

        if not validate_instance(data):
            continue
        cross_check(data)

        # Render
        if data["family"] == "basic":
            prob, ans, expl = render_problem_basic(data, lang)
        elif data["family"] == "three":
            prob, ans, expl = render_problem_three(data)
        else:
            prob, ans, expl = render_problem_comp(data)

        return {"problem": prob, "answer": ans, "explanation": expl}

    raise RuntimeError("生成失败：在给定尝试次数内未能构造出合格题目。")

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        eprint("输入不是合法 JSON：", e)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))
    lang = req.get("output_language", "zh")  # retained though currently only zh rendering is implemented

    if count <= 0:
        print("[]")
        return

    rng = random.Random(seed)

    out = []
    seen = set()
    # limit overall attempts to avoid infinite loops
    total_attempts = 0
    while len(out) < count:
        total_attempts += 1
        if total_attempts > 5000:
            raise RuntimeError("生成失败：重试次数过多，可能约束过强或重复过滤过严。")

        item = make_one(rng, lang)

        # Deduplicate by problem text
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()