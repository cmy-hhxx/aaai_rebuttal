import sys, json, random, itertools
from dataclasses import dataclass
from typing import List, Tuple, Set, Dict, Optional, FrozenSet

# -----------------------------
# CNF resolution problem generator (ZH)
# -----------------------------

VAR_POOL = list("pqrstuvwxyzabcdefghijklmno")  # enough atoms

def lit_str(lit: Tuple[str, bool]) -> str:
    v, pos = lit
    return v if pos else f"¬{v}"

def clause_str(clause: FrozenSet[Tuple[str, bool]]) -> str:
    if len(clause) == 0:
        return "0"
    # stable order: by var then neg first? follow seed-like: ¬p before p
    def key(l):
        v, pos = l
        return (v, 0 if not pos else 1)
    return "∨".join(lit_str(l) for l in sorted(clause, key=key))

def cnf_str(clauses: List[FrozenSet[Tuple[str, bool]]]) -> str:
    return "∧".join(f"({clause_str(c)})" for c in clauses)

def complement(lit: Tuple[str, bool]) -> Tuple[str, bool]:
    v, pos = lit
    return (v, not pos)

def is_tautology(clause: FrozenSet[Tuple[str, bool]]) -> bool:
    s = set(clause)
    for l in clause:
        if complement(l) in s:
            return True
    return False

def resolvents(c1: FrozenSet[Tuple[str, bool]], c2: FrozenSet[Tuple[str, bool]]) -> Set[FrozenSet[Tuple[str, bool]]]:
    """All possible resolvents produced by resolving on any complementary literal pair.
       We do NOT simplify tautologies away here; keep them because dispel just concatenates.
       Empty resolvent => empty frozenset.
    """
    res = set()
    s2 = set(c2)
    for l in c1:
        lc = complement(l)
        if lc in s2:
            new = (set(c1) - {l}) | (set(c2) - {lc})
            res.add(frozenset(new))
    return res

def can_resolve(c1, c2) -> bool:
    s2 = set(c2)
    return any(complement(l) in s2 for l in c1)

def resolution_algorithm_cycles(clauses: List[FrozenSet[Tuple[str, bool]]]) -> Tuple[str, int, Dict]:
    """
    Implement the described algorithm:
    - S0, S2 empty; S1 = set(clauses)
    - loop:
        b) resolve S0 vs S1 -> add new to S2; if empty resolvent -> Implausible
        c) resolve pairs within S1 similarly
        d) if S2 empty -> Plausible else S0 |= S1; S1 = S2; S2=empty; continue
    Return (output, cycles, trace)
    cycles counts how many times step d is executed (i.e., number of loop iterations performed).
    """
    S0: Set[FrozenSet[Tuple[str, bool]]] = set()
    S1: Set[FrozenSet[Tuple[str, bool]]] = set(clauses)
    S2: Set[FrozenSet[Tuple[str, bool]]] = set()
    cycles = 0

    # trace of first iteration (for Q4-like explanation)
    trace = {
        "init": {"S0": set(), "S1": set(S1), "S2": set()},
        "first_iter": {"from_S0_S1": set(), "from_S1_S1": set(), "S2_end": None, "empty_found": False},
    }

    def add_resolvent(r: FrozenSet[Tuple[str, bool]]):
        nonlocal S2
        if len(r) == 0:
            return "EMPTY"
        if (r not in S0) and (r not in S1) and (r not in S2):
            S2.add(r)
        return "OK"

    while True:
        cycles += 1
        # b) S0 vs S1
        new_b = set()
        for c0 in list(S0):
            for c1 in list(S1):
                for r in resolvents(c0, c1):
                    if len(r) == 0:
                        if cycles == 1:
                            trace["first_iter"]["empty_found"] = True
                            trace["first_iter"]["from_S0_S1"] = set(new_b)
                            trace["first_iter"]["S2_end"] = set(S2)
                        return "Implausible", cycles, trace
                    if (r not in S0) and (r not in S1) and (r not in S2):
                        S2.add(r)
                        new_b.add(r)

        # c) S1 pairs
        new_c = set()
        S1_list = list(S1)
        for i in range(len(S1_list)):
            for j in range(i + 1, len(S1_list)):
                for r in resolvents(S1_list[i], S1_list[j]):
                    if len(r) == 0:
                        if cycles == 1:
                            trace["first_iter"]["from_S0_S1"] = set(new_b)
                            trace["first_iter"]["from_S1_S1"] = set(new_c)
                            trace["first_iter"]["empty_found"] = True
                            trace["first_iter"]["S2_end"] = set(S2)
                        return "Implausible", cycles, trace
                    if (r not in S0) and (r not in S1) and (r not in S2):
                        S2.add(r)
                        new_c.add(r)

        if cycles == 1:
            trace["first_iter"]["from_S0_S1"] = set(new_b)
            trace["first_iter"]["from_S1_S1"] = set(new_c)
            trace["first_iter"]["S2_end"] = set(S2)

        # d) check S2
        if len(S2) == 0:
            return "Plausible", cycles, trace
        S0 |= S1
        S1 = set(S2)
        S2.clear()

# -----------------------------
# Instance construction helpers
# -----------------------------

def pick_vars(rng: random.Random, kmin=4, kmax=7) -> List[str]:
    k = rng.randint(kmin, kmax)
    return rng.sample(VAR_POOL, k)

def rand_lit(rng: random.Random, vars_: List[str]) -> Tuple[str, bool]:
    v = rng.choice(vars_)
    pos = rng.choice([True, False])
    return (v, pos)

def rand_clause(rng: random.Random, vars_: List[str], size_min=2, size_max=4, allow_tautology=True) -> FrozenSet[Tuple[str, bool]]:
    size = rng.randint(size_min, size_max)
    lits = []
    while len(lits) < size:
        l = rand_lit(rng, vars_)
        if l not in lits:
            lits.append(l)
    clause = frozenset(lits)
    if not allow_tautology:
        # resample if tautology
        tries = 0
        while is_tautology(clause) and tries < 30:
            clause = frozenset({rand_lit(rng, vars_) for _ in range(size)})
            tries += 1
    return clause

def ensure_can_resolve_no(rng: random.Random, vars_: List[str]) -> Tuple[FrozenSet[Tuple[str, bool]], FrozenSet[Tuple[str, bool]]]:
    """Return two clauses that cannot be resolved (no complementary pair)."""
    vset = rng.sample(vars_, rng.randint(2, min(4, len(vars_))))
    # Fix polarity assignment for each variable, both clauses use same polarity if they share var
    pol = {v: rng.choice([True, False]) for v in vset}
    # Build each clause from subset with same polarities
    a = set()
    b = set()
    for v in vset:
        if rng.random() < 0.8:
            a.add((v, pol[v]))
        if rng.random() < 0.8:
            b.add((v, pol[v]))
    # Ensure non-empty
    if len(a) < 2:
        a.add((vset[0], pol[vset[0]]))
        a.add((vset[1], pol[vset[1]]))
    if len(b) < 2:
        b.add((vset[-1], pol[vset[-1]]))
        b.add((vset[0], pol[vset[0]]))
    return frozenset(a), frozenset(b)

def ensure_can_resolve_yes(rng: random.Random, vars_: List[str]) -> Tuple[FrozenSet[Tuple[str, bool]], FrozenSet[Tuple[str, bool]], Tuple[str,bool]]:
    """Return two clauses that can be resolved; also return one chosen pivot literal L in C1 and L' in C2."""
    pivot_var = rng.choice(vars_)
    pivot_pos = rng.choice([True, False])
    L = (pivot_var, pivot_pos)
    Lc = complement(L)
    c1 = set(rand_clause(rng, vars_, 2, 4, allow_tautology=True))
    c2 = set(rand_clause(rng, vars_, 2, 4, allow_tautology=True))
    # force include L in c1, L' in c2
    c1.add(L)
    c2.add(Lc)
    return frozenset(c1), frozenset(c2), L

def one_dispel(c1: FrozenSet[Tuple[str, bool]], c2: FrozenSet[Tuple[str, bool]], pivot: Tuple[str,bool]) -> FrozenSet[Tuple[str,bool]]:
    """Compute resolvent using a specified pivot literal in c1."""
    L = pivot
    Lc = complement(L)
    if L not in c1 or Lc not in c2:
        raise ValueError("pivot not applicable")
    new = (set(c1) - {L}) | (set(c2) - {Lc})
    return frozenset(new)

def all_dispels(c1: FrozenSet[Tuple[str, bool]], c2: FrozenSet[Tuple[str, bool]]) -> List[FrozenSet[Tuple[str, bool]]]:
    res = sorted(resolvents(c1, c2), key=lambda cl: clause_str(cl))
    return res

def format_set_of_clauses(clauses: Set[FrozenSet[Tuple[str,bool]]]) -> str:
    if len(clauses) == 0:
        return "∅"
    # render as {c1,c2,...}
    items = sorted([clause_str(c) for c in clauses], key=lambda s: s)
    return "{" + ",".join(items) + "}"

def ans_block(parts: List[str]) -> str:
    # Each question answer requested in [[...]] form; multiple blocks separated by ==== like seed
    return "====".join(f"[[{p}]]" for p in parts)

# -----------------------------
# Build one full 5-part problem
# -----------------------------

def build_one(rng: random.Random, lang: str = "zh") -> Dict:
    vars_ = pick_vars(rng)

    # Q1: resolvable?
    if rng.random() < 0.5:
        c1, c2 = ensure_can_resolve_no(rng, vars_)
        q1_opt = "B"
    else:
        c1, c2, _ = ensure_can_resolve_yes(rng, vars_)
        q1_opt = "A"

    # Q2: single dispel with unique pivot; ensure exactly one complementary pair
    tries = 0
    while True:
        tries += 1
        if tries > 200:
            raise RuntimeError("Failed to construct Q2 with unique pivot")
        pivot_var = rng.choice(vars_)
        pivot_pos = rng.choice([True, False])
        L = (pivot_var, pivot_pos)
        Lc = complement(L)
        # Build C1 containing L but avoid any other complements with C2
        other_vars = rng.sample([v for v in vars_ if v != pivot_var], rng.randint(2, min(4, len(vars_)-1)))
        c1_set = {L}
        for v in other_vars:
            c1_set.add((v, rng.choice([True, False])))
        # Build C2 containing Lc; for vars in c1_set (excluding pivot), use same polarity to avoid complements
        c2_set = {Lc}
        # add some from c1 (same polarity)
        for (v, pos) in c1_set:
            if v == pivot_var:
                continue
            if rng.random() < 0.7:
                c2_set.add((v, pos))
        # add new vars not in c1 with random polarity
        remain = [v for v in vars_ if v not in {x for x,_ in c1_set} and v != pivot_var]
        rng.shuffle(remain)
        for v in remain[:rng.randint(0, 2)]:
            c2_set.add((v, rng.choice([True, False])))
        C1_q2 = frozenset(c1_set)
        C2_q2 = frozenset(c2_set)
        # check exactly one complementary pair
        res = resolvents(C1_q2, C2_q2)
        if len(res) == 1:
            R2 = next(iter(res))
            break

    # Q3: multiple dispels possible (>=2) with multiple complementary pairs
    tries = 0
    while True:
        tries += 1
        if tries > 300:
            raise RuntimeError("Failed to construct Q3 with multiple resolvents")
        # choose two pivot vars different
        if len(vars_) < 4:
            continue
        pv = rng.sample(vars_, 2)
        L1 = (pv[0], rng.choice([True, False]))
        L2 = (pv[1], rng.choice([True, False]))
        c1_set = {L1, L2}
        # add one more literal
        c1_set.add((rng.choice([v for v in vars_ if v not in pv]), rng.choice([True, False])))
        c2_set = {complement(L1), complement(L2)}
        c2_set.add((rng.choice([v for v in vars_ if v not in pv]), rng.choice([True, False])))
        C1_q3 = frozenset(c1_set)
        C2_q3 = frozenset(c2_set)
        R3s = all_dispels(C1_q3, C2_q3)
        if len(R3s) >= 2:
            break

    # Q4 & Q5: CNF for algorithm, ensure small size and non-trivial, compute output & cycles
    # We will sample 3~5 clauses, each 1~3 literals, avoid tautology for clarity
    tries = 0
    while True:
        tries += 1
        if tries > 400:
            raise RuntimeError("Failed to construct CNF for Q4/Q5")
        m = rng.randint(3, 5)
        clauses = []
        for _ in range(m):
            size = rng.randint(1, 3)
            cl = rand_clause(rng, vars_, size, size, allow_tautology=False)
            clauses.append(cl)
        # ensure no duplicates
        clauses = list(dict.fromkeys(clauses))
        if len(clauses) < 3:
            continue
        out, cyc, trace = resolution_algorithm_cycles(clauses)
        # prefer instances that terminate within 1~4 cycles (readable) and have some action in first iter
        if 1 <= cyc <= 4 and (len(trace["first_iter"]["from_S1_S1"]) > 0 or out == "Implausible"):
            cnf = clauses
            output_q5 = out
            cycles_q5 = cyc
            trace_q4 = trace
            break

    # Render problem in Chinese
    prob = []
    prob.append("下面给出一套命题逻辑中的归结（Resolution）规则。请按题面定义作答。\n")
    prob.append("定义：文字（literal）指命题变元及其否定；互补文字：L 的互补记为 L’（p 的互补是 ¬p，¬p 的互补是 p）。\n")
    prob.append("归结：若 C1 = C3 ∨ L，C2 = C4 ∨ L’，则可归结，dispel(C1,C2)=C3 ∨ C4；若结果为空子句，则记为 0。\n")
    prob.append("归结算法：S0、S2 初始为空集，S1 为 CNF 中所有子句集合；循环：先归结 S0 与 S1，再归结 S1 内两两；若得到 0 则输出 Implausible；若本轮新得到集合 S2 为空则输出 Plausible；否则令 S0←S0∪S1，S1←S2，S2 清空继续。\n")

    prob.append(f"\n1：子句 C1 = {clause_str(c1)} 与 C2 = {clause_str(c2)} 是否可归结？\nA. 是\nB. 否\n答案格式：[[选项]]。\n")

    prob.append(f"2：若 C1 = {clause_str(C1_q2)}，C2 = {clause_str(C2_q2)}，求 dispel(C1,C2)。\n答案格式：[[]]。\n")

    prob.append(f"3：若 C1 = {clause_str(C1_q3)}，C2 = {clause_str(C2_q3)}，则 dispel(C1,C2)=？\n若有多个可能结果，用 [[];[];…] 给出。\n")

    cnf_text = cnf_str(cnf)
    prob.append(f"4：对 CNF：{cnf_text}，在开始归结算法前 S0、S1、S2 分别是什么？并说明第一次循环结束时的 S2 是什么。\n答案格式：[[S0];[S1];[S2];[第一次循环后S2]]，集合用{{}}表示，空集用 ∅ 表示。\n")

    prob.append(f"5：对 CNF：{cnf_text}，归结算法最终输出是什么？总共会进行多少轮循环？\n答案格式：[[输出];[轮数]]。\n")

    problem_text = "".join(prob)

    # Build answers
    a1 = q1_opt

    a2 = clause_str(R2)

    a3_list = [clause_str(r) for r in R3s]
    a3 = ";".join(a3_list)

    S0_init = trace_q4["init"]["S0"]
    S1_init = trace_q4["init"]["S1"]
    S2_init = trace_q4["init"]["S2"]
    S2_after_first = trace_q4["first_iter"]["S2_end"] if trace_q4["first_iter"]["S2_end"] is not None else set()

    a4 = ";".join([
        format_set_of_clauses(S0_init),
        format_set_of_clauses(S1_init),
        format_set_of_clauses(S2_init),
        format_set_of_clauses(S2_after_first),
    ])

    a5 = f"{output_q5};{cycles_q5}"

    answer = ans_block([a1, a2, a3, a4, a5])

    # Explanation (short, checkable)
    exp = []
    exp.append("要点核对：\n")
    exp.append(f"(1) 第1问：两子句可归结当且仅当存在某个文字 L 使得另一子句包含 L’。\n")
    exp.append(f"  C1={clause_str(c1)}，C2={clause_str(c2)}，因此选择 {a1}。\n")
    exp.append(f"(2) 第2问：题目构造保证只有一对互补文字可归结，因此 dispel 就是删去该互补对后把剩余文字并起来：{a2}。\n")
    exp.append(f"(3) 第3问：存在至少两对互补文字，因此会产生多个可能的 resolvent；逐个按 dispel 定义合并得到：{a3}。\n")
    exp.append(f"(4) 第4问：初始化 S0=∅，S2=∅，S1 为 CNF 的全部子句集合；第一次循环后 S2 为本轮新归结得到且不在 S0/S1 中的子句集合：{format_set_of_clauses(S2_after_first)}。\n")
    exp.append(f"(5) 第5问：按算法迭代直至出现空子句(输出 Implausible)或本轮无新子句(输出 Plausible)。本题输出 {output_q5}，共 {cycles_q5} 轮。\n")
    explanation = "".join(exp)

    return {"problem": problem_text, "answer": answer, "explanation": explanation}

# -----------------------------
# Main
# -----------------------------

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count must be positive")
    except Exception as e:
        print(f"Invalid input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    results = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = build_one(rng, "zh")
        except Exception as e:
            # resample
            continue
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    if len(results) < count:
        print(f"Generation failed: only produced {len(results)}/{count} after {attempts} attempts", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()