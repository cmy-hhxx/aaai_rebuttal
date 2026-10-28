import sys, json, random, itertools, math, re
from typing import List, Tuple, Dict, Any, Optional

# ---------- Utilities: formatting, parsing, logic evaluation ----------

HEX_DIGITS = "0123456789ABCDEF"

def to_hex(i: int) -> str:
    if i < 0:
        raise ValueError("negative index")
    if i < 16:
        return HEX_DIGITS[i]
    return format(i, "X")

def lit_str(var: str, is_pos: bool, lang_and: str = "∧", lang_not: str = "¬") -> str:
    return (var if is_pos else f"{lang_not}{var}")

def conj_term(vars_: List[str], bits: List[int], lang_and: str = "∧", lang_not: str = "¬") -> str:
    # bits: 1 means var True -> positive literal; 0 means var False -> negated literal
    lits = [lit_str(v, b == 1, lang_and, lang_not) for v, b in zip(vars_, bits)]
    return lang_and.join(lits)

def disj_term(vars_: List[str], bits: List[int], lang_or: str = "∨", lang_not: str = "¬") -> str:
    # Paired disjunctive term: each variable or its negation appears once.
    # Its false assignment corresponds to bits:
    # For clause (l1 ∨ l2 ∨ ...), the unique falsifying assignment sets each literal to False:
    #   literal v is False when v=0; literal ¬v is False when v=1.
    # So if falsifying bit for variable is 0 -> use v; if bit is 1 -> use ¬v.
    lits = []
    for v, b in zip(vars_, bits):
        if b == 0:
            lits.append(v)
        else:
            lits.append(f"{lang_not}{v}")
    return lang_or.join(lits)

def bits_to_index(bits: List[int]) -> int:
    # bits are ordered as vars_ listed (ascending subscript / lexicographic)
    # binary number with first var as MSB
    i = 0
    for b in bits:
        i = (i << 1) | (1 if b else 0)
    return i

def index_to_bits(i: int, n: int) -> List[int]:
    return [(i >> (n - 1 - k)) & 1 for k in range(n)]

def even_set(indices: List[int]) -> bool:
    return all(i % 2 == 0 for i in indices)

def odd_set(indices: List[int]) -> bool:
    return all(i % 2 == 1 for i in indices)

def is_power_of_two(x: int) -> bool:
    return x > 0 and (x & (x - 1) == 0)

# ---------- Logic modeling via truth tables (no external solvers needed) ----------

def eval_formula(ast, env: Dict[str, int]) -> int:
    t = ast[0]
    if t == "var":
        return env[ast[1]]
    if t == "not":
        return 1 - eval_formula(ast[1], env)
    if t == "and":
        return eval_formula(ast[1], env) & eval_formula(ast[2], env)
    if t == "or":
        return eval_formula(ast[1], env) | eval_formula(ast[2], env)
    if t == "imp":
        a = eval_formula(ast[1], env)
        b = eval_formula(ast[2], env)
        return (1 - a) | b
    if t == "iff":
        a = eval_formula(ast[1], env)
        b = eval_formula(ast[2], env)
        return 1 if a == b else 0
    raise ValueError(f"Unknown AST node: {t}")

# ---------- Simple expression parser (supports ¬, ∧, ∨, →, ↔, parentheses) ----------

TOKEN_RE = re.compile(
    r"\s*("
    r"↔|→|¬|∧|∨|\^|v|V|\(|\)|"
    r"[A-Za-z][A-Za-z0-9_]*"
    r")\s*"
)

def tokenize(s: str) -> List[str]:
    tokens = TOKEN_RE.findall(s)
    if not tokens:
        return []
    joined = "".join(tokens)
    stripped = re.sub(r"\s+", "", s)
    if joined != stripped:
        # There are unknown characters
        # Try a looser validation: remove recognized tokens progressively
        pos = 0
        for m in TOKEN_RE.finditer(s):
            pos = m.end()
        # If parser cannot cover all, still proceed but may error later
    # normalize
    norm = []
    for t in tokens:
        if t == "^":
            norm.append("∧")
        elif t in ("v", "V"):
            norm.append("∨")
        else:
            norm.append(t)
    return norm

class Parser:
    def __init__(self, tokens: List[str]):
        self.toks = tokens
        self.i = 0

    def peek(self) -> Optional[str]:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def eat(self, t: str) -> None:
        if self.peek() != t:
            raise ValueError(f"Expected {t}, got {self.peek()}")
        self.i += 1

    def parse(self):
        node = self.parse_iff()
        if self.peek() is not None:
            raise ValueError(f"Unexpected token: {self.peek()}")
        return node

    def parse_iff(self):
        node = self.parse_imp()
        while self.peek() == "↔":
            self.eat("↔")
            rhs = self.parse_imp()
            node = ("iff", node, rhs)
        return node

    def parse_imp(self):
        node = self.parse_or()
        while self.peek() == "→":
            self.eat("→")
            rhs = self.parse_or()
            node = ("imp", node, rhs)
        return node

    def parse_or(self):
        node = self.parse_and()
        while self.peek() == "∨":
            self.eat("∨")
            rhs = self.parse_and()
            node = ("or", node, rhs)
        return node

    def parse_and(self):
        node = self.parse_not()
        while self.peek() == "∧":
            self.eat("∧")
            rhs = self.parse_not()
            node = ("and", node, rhs)
        return node

    def parse_not(self):
        if self.peek() == "¬":
            self.eat("¬")
            return ("not", self.parse_not())
        return self.parse_atom()

    def parse_atom(self):
        t = self.peek()
        if t is None:
            raise ValueError("Unexpected end")
        if t == "(":
            self.eat("(")
            node = self.parse_iff()
            self.eat(")")
            return node
        if re.match(r"^[A-Za-z][A-Za-z0-9_]*$", t):
            self.eat(t)
            return ("var", t)
        raise ValueError(f"Bad atom: {t}")

def parse_expr(s: str):
    p = Parser(tokenize(s))
    return p.parse()

def vars_in_ast(ast) -> List[str]:
    t = ast[0]
    if t == "var":
        return [ast[1]]
    if t == "not":
        return vars_in_ast(ast[1])
    if t in ("and", "or", "imp", "iff"):
        return sorted(set(vars_in_ast(ast[1]) + vars_in_ast(ast[2])))
    return []

def truth_indices(ast, vars_: List[str]) -> List[int]:
    res = []
    n = len(vars_)
    for i in range(2**n):
        bits = index_to_bits(i, n)
        env = {v: bits[j] for j, v in enumerate(vars_)}
        if eval_formula(ast, env) == 1:
            res.append(i)
    return res

def principal_dnf_m_indices(indices: List[int], n: int) -> List[str]:
    # Return list like ["m0","mA",...]
    return [f"m{to_hex(i)}" for i in indices]

# ---------- Generation families ----------

def pick_var_names(rng: random.Random, n: int) -> List[str]:
    base = ["p", "q", "r", "s", "t", "u", "v", "w"]
    if n <= len(base):
        return base[:n]
    # fallback
    return [f"x{i+1}" for i in range(n)]

def build_q1(rng: random.Random):
    # OR of several paired conjunctive terms, ask to list terms and denote as m_i ∨ ...
    n = rng.choice([3, 4])
    vars_ = pick_var_names(rng, n)
    k = rng.randint(2, min(4, 2**n - 1))
    indices = sorted(rng.sample(range(2**n), k))
    terms = [conj_term(vars_, index_to_bits(i, n)) for i in indices]
    expr = " ∨ ".join([f"({t})" for t in terms])
    den = "∨".join([f"m{to_hex(i)}" for i in indices])
    problem = (
        f"1：按题干所述“配对合取项/mi”的规则，求公式 {expr} 的配对合取项有哪些？并写出它可记作什么？\n"
        f"要求：答案格式为 [[paired conjunctive terms:...]; [denoted:...]]，多项用逗号分隔。"
    )
    answer = [[f"paired conjunctive terms:{','.join(terms)}"], [f"denoted:{den}"]]
    explanation = (
        f"该式本身就是若干个配对合取项的析取。以变量顺序 {','.join(vars_)} 为准，"
        f"每个真赋值对应二进制并转为十六进制得到 mi："
        + "；".join([f"{terms[j]} 对应 i={indices[j]}(0x{to_hex(indices[j])})" for j in range(len(indices))])
        + f"。故记作 {den}。"
    )
    return problem, answer, explanation

def build_q2(rng: random.Random):
    # AND of several paired disjunctive terms, denote as M_i ∧ ...
    n = rng.choice([3, 4])
    vars_ = pick_var_names(rng, n)
    k = rng.randint(2, min(4, 2**n - 1))
    indices = sorted(rng.sample(range(2**n), k))
    terms = [disj_term(vars_, index_to_bits(i, n)) for i in indices]
    expr = " ∧ ".join([f"({t})" for t in terms])
    den = "∧".join([f"M{to_hex(i)}" for i in indices])
    problem = (
        f"2：按题干所述“配对析取项/Mi”的规则，求公式 {expr} 的配对析取项有哪些？并写出它可记作什么？\n"
        f"要求：答案格式为 [[paired disjunctive terms:...];[denoted:...]]，多项用逗号分隔。"
    )
    answer = [[f"paired disjunctive terms:{','.join(terms)}"], [f"denoted:{den}"]]
    explanation = (
        f"该式是若干配对析取项的合取。以变量顺序 {','.join(vars_)} 为准，"
        f"每个配对析取项的“假赋值”给出二进制并转十六进制得到 Mi："
        + "；".join([f"{terms[j]} 的假赋值索引 i={indices[j]}(0x{to_hex(indices[j])})" for j in range(len(indices))])
        + f"。故记作 {den}。"
    )
    return problem, answer, explanation

def classify_single_m_term(n: int, index: int) -> str:
    # Options: A tautology B contradiction C basic D all-even E all-odd F none
    # For a single minterm: neither tautology nor contradiction; basic iff includes m0 -> only when index=0
    opts = []
    if index == 0:
        opts.append("C")
    # all-even / all-odd depend on included indices set (singleton)
    if index % 2 == 0:
        opts.append("D")
    else:
        opts.append("E")
    if not opts:
        opts = ["F"]
    return "".join(opts)

def build_q3(rng: random.Random):
    n = rng.choice([3, 4])
    vars_ = pick_var_names(rng, n)
    index = rng.randrange(2**n)
    term = conj_term(vars_, index_to_bits(index, n))
    opts = classify_single_m_term(n, index)
    problem = (
        f"3：将公式 {term} 识别为（多选）：\n"
        f"A. 永真式  B. 矛盾式  C. 基本公式(其主析取范式含 m0)  D. 全偶公式  E. 全奇公式  F. 以上都不是。\n"
        f"答案格式 [[AB...]]。"
    )
    answer = [[opts]]
    explanation = (
        f"{term} 本身就是一个配对合取项，对应索引 i={index}(0x{to_hex(index)})。"
        f"它不是永真也不是矛盾；"
        + ("因为 i=0 所以主析取范式包含 m0，属于基本公式；" if index == 0 else "因为 i≠0 所以不包含 m0，不是基本公式；")
        + ("且索引为偶数，故为全偶公式。" if index % 2 == 0 else "且索引为奇数，故为全奇公式。")
    )
    return problem, answer, explanation

def build_q4(rng: random.Random):
    # Give a DNF of minterms; ask whether it is principal DNF or principal CNF; if yes, denote.
    n = rng.choice([3, 4])
    vars_ = pick_var_names(rng, n)
    is_pdnf = rng.random() < 0.75
    if is_pdnf:
        k = rng.randint(1, min(6, 2**n))
        indices = sorted(rng.sample(range(2**n), k))
        terms = [conj_term(vars_, index_to_bits(i, n)) for i in indices]
        expr = " ∨ ".join([f"({t})" for t in terms])
        den = "∨".join([f"m{to_hex(i)}" for i in indices])
        problem = (
            f"4：判断下式是否符合“主析取范式”或“主合取范式”的形式；若符合，写出其记号。\n"
            f"公式：{expr}\n"
            f"答案格式：若符合，[[A];[denoted expression]]；若不符合，[[B]]。"
        )
        answer = [[ "A" ], [ den ]]
        explanation = (
            f"该式是若干“配对合取项”按变量顺序 {','.join(vars_)} 的析取，"
            f"每项每个变量或其否定恰好出现一次，因此符合主析取范式的构成形式。"
            f"对应记号为 {den}。"
        )
        return problem, answer, explanation
    else:
        # Make an expression that fails: e.g., one term missing a variable or duplicates
        # We'll craft at least one "bad" term.
        good_k = rng.randint(1, 3)
        good_indices = sorted(rng.sample(range(2**n), good_k))
        good_terms = [conj_term(vars_, index_to_bits(i, n)) for i in good_indices]
        # bad term: drop last literal
        bits = index_to_bits(rng.randrange(2**n), n)
        bad = "∧".join([lit_str(vars_[j], bits[j] == 1) for j in range(n-1)])
        expr = " ∨ ".join([f"({t})" for t in good_terms] + [f"({bad})"])
        problem = (
            f"4：判断下式是否符合“主析取范式”或“主合取范式”的形式；若符合，写出其记号。\n"
            f"公式：{expr}\n"
            f"答案格式：若符合，[[A];[denoted expression]]；若不符合，[[B]]。"
        )
        answer = [[ "B" ]]
        explanation = (
            f"主析取范式要求每个析取项都是配对合取项：每个变量或其否定必须“恰好出现一次”。"
            f"但项 ({bad}) 缺少变量 {vars_[-1]}（没有出现 {vars_[-1]} 或 ¬{vars_[-1]}），因此不符合。"
        )
        return problem, answer, explanation

def build_q5(rng: random.Random):
    # n variables, tautology and basic form -> PDNF includes all minterms, and includes m0 automatically
    n = rng.choice([4, 5])
    vars_ = pick_var_names(rng, n)
    all_ms = "∨".join([f"m{to_hex(i)}" for i in range(2**n)])
    problem = (
        f"5：已知公式 A 含 {n} 个命题变元（按 {','.join(vars_)} 排列）。若 A 同时是永真式且是基本公式，它应记作什么？\n"
        f"答案格式 [[]]（只写记号表达式）。"
    )
    answer = [[all_ms]]
    explanation = (
        f"永真式的主析取范式必须包含全部 2^{n} 个配对合取项 m0..m{to_hex(2**n-1)}；"
        f"因此记号为它们的析取：{all_ms}。这必然包含 m0，所以也满足“基本公式”。"
    )
    return problem, answer, explanation

def build_q6(rng: random.Random):
    n = rng.choice([4, 5, 6])
    # Count formulas that are both basic and all-even:
    # choose any subset S of even indices such that 0 in S (basic requires m0 included), S nonempty automatically.
    evens = 2**(n-1)
    count = 2**(evens - 1)  # choose subset of evens containing 0
    problem = (
        f"6：已知公式 A 含 {n} 个命题变元。问：有多少个公式同时满足“基本公式(主析取范式含 m0)”且“全偶公式(出现的 mi 的 i 全为偶数)”？\n"
        f"答案为单个整数，格式 [[]]。"
    )
    answer = [[count]]
    explanation = (
        f"{n} 个变元共有 2^{n} 个 mi。偶数索引共有 2^{n-1} 个。"
        f"要全偶，则只能从这些偶数索引中选取出现在主析取范式的 mi；"
        f"要基本，则必须选中 m0。于是其余 (2^{n-1}-1) 个偶索引可自由选/不选，"
        f"共有 2^(2^{n-1}-1) = {count} 种。"
    )
    return problem, answer, explanation

def build_q7(rng: random.Random):
    # Selection problem with 3 variables, generate constraints and compute PDNF minterm indices.
    # Ensure 1-2 members constraint included.
    names = ["A", "B", "C"]
    rng.shuffle(names)
    Aname, Bname, Cname = names
    vars_ = ["p", "q", "r"]  # fixed mapping
    # Template pool for constraints
    # We'll pick 3 constraints plus cardinality 1-2.
    templates = [
        ("p→r", ("imp", ("var","p"), ("var","r")), f"若 {Aname} 去，则 {Cname} 必须去。"),
        ("q→¬r", ("imp", ("var","q"), ("not", ("var","r"))), f"若 {Bname} 去，则 {Cname} 不能去。"),
        ("r→p", ("imp", ("var","r"), ("var","p")), f"若 {Cname} 去，则 {Aname} 必须去。"),
        ("p→¬q", ("imp", ("var","p"), ("not", ("var","q"))), f"若 {Aname} 去，则 {Bname} 不能去。"),
        ("q→p", ("imp", ("var","q"), ("var","p")), f"若 {Bname} 去，则 {Aname} 必须去。"),
        ("¬r→(p∨q)", ("imp", ("not", ("var","r")), ("or", ("var","p"), ("var","q"))), f"若 {Cname} 不去，则 {Aname} 或 {Bname} 至少去一个。"),
        ("¬p→r", ("imp", ("not", ("var","p")), ("var","r")), f"若 {Aname} 不去，则 {Cname} 必须去。"),
    ]
    chosen = rng.sample(templates, 3)

    # Cardinality: select 1-2 out of 3
    # encode: at least 1 and at most 2. Equivalent: (p∨q∨r) ∧ ¬(p∧q∧r)
    at_least_1 = ("or", ("or", ("var","p"), ("var","q")), ("var","r"))
    not_all3 = ("not", ("and", ("and", ("var","p"), ("var","q")), ("var","r")))
    card = ("and", at_least_1, not_all3)

    # Build full ast: (c1) ∧ (c2) ∧ (c3) ∧ card
    ast = card
    cond_strs = []
    for _, c_ast, c_cn in chosen:
        ast = ("and", ast, c_ast)
        cond_strs.append(c_cn)

    # Compute true assignments
    true_is = truth_indices(ast, vars_)

    # Ensure at least 1 scheme and not tautology; if not, resample a bit
    tries = 0
    while (len(true_is) == 0 or len(true_is) == 8) and tries < 50:
        chosen = rng.sample(templates, 3)
        ast = card
        cond_strs = []
        for _, c_ast, c_cn in chosen:
            ast = ("and", ast, c_ast)
            cond_strs.append(c_cn)
        true_is = truth_indices(ast, vars_)
        tries += 1
    if len(true_is) == 0 or len(true_is) == 8:
        # fallback to a known workable set
        chosen = [templates[0], templates[1], templates[5]]
        ast = ("and", ("and", ("and", card, chosen[0][1]), chosen[1][1]), chosen[2][1])
        cond_strs = [c[2] for c in chosen]
        true_is = truth_indices(ast, vars_)

    # Build PDNF expression as minterms
    terms = [conj_term(vars_, index_to_bits(i, 3)) for i in true_is]
    den = "∨".join([f"m{to_hex(i)}" for i in true_is]) if true_is else "(空)"
    # Classification options for formula based on included minterms
    opts = []
    if len(true_is) == 2**3:
        opts.append("A")
    elif len(true_is) == 0:
        opts.append("B")
    if 0 in true_is:
        opts.append("C")
    if true_is and even_set(true_is):
        opts.append("D")
    if true_is and odd_set(true_is):
        opts.append("E")
    if not opts:
        opts = ["F"]
    opt_str = "".join(opts)

    # Build explanation with explicit truth assignments list
    schemes = []
    for i in true_is:
        b = index_to_bits(i, 3)
        # b corresponds to p,q,r
        schemes.append(f"({vars_[0]},{vars_[1]},{vars_[2]})={''.join(str(x) for x in b)} -> m{to_hex(i)}")
    explanation = (
        "把条件写成公式：A := (至少选1人且至多选2人) ∧ " +
        " ∧ ".join([f"({c[0]})" for c in chosen]) +
        "。其中“至少选1人且至多选2人”等价于 (p∨q∨r)∧¬(p∧q∧r)。\n"
        "对 (p,q,r) 的 8 个赋值逐一检验，满足者对应主析取范式中的 mi。满足的赋值为："
        + ("；".join(schemes) if schemes else "无")
        + f"。因此记作 {den}。选项判定：包含 m0 则为基本公式；索引全偶/全奇则为全偶/全奇；全包含/全不包含则为永真/矛盾。"
    )

    problem = (
        f"7：某研究所需从三名骨干研究员 {Aname},{Bname},{Cname} 中选派 1-2 人出国。设\n"
        f"p：{Aname} 去；q：{Bname} 去；r：{Cname} 去。\n"
        f"除“恰选 1-2 人”外，还需满足：\n"
        + "\n".join([f"{i+1}. {cond_strs[i]}" for i in range(3)]) +
        "\n(1) 写出满足条件的可行方案对应的主析取范式记号（用 mi 的析取表示）。\n"
        "(2) 判定该公式属于下列哪几类（多选）：\n"
        "A. 永真式  B. 矛盾式  C. 基本公式  D. 全偶公式  E. 全奇公式  F. 以上都不是。\n"
        "答案格式：[[denoted expression];[options]]"
    )
    answer = [[den], [opt_str]]
    return problem, answer, explanation

# ---------- Master generator ----------

def make_problem(rng: random.Random, idx: int) -> Tuple[str, Any, str]:
    # Mix families to achieve diversity
    families = [build_q1, build_q2, build_q3, build_q4, build_q5, build_q6, build_q7]
    # Weighted choice
    weights = [3, 3, 2, 3, 1, 2, 3]
    total = sum(weights)
    r = rng.randrange(total)
    acc = 0
    chosen = families[-1]
    for f, w in zip(families, weights):
        acc += w
        if r < acc:
            chosen = f
            break
    return chosen(rng)

def normalize_problem_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    out = []
    seen = set()
    attempts = 0
    max_attempts = max(200, count * 50)

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            problem, answer, explanation = make_problem(rng, len(out))
            key = normalize_problem_text(problem)
            if key in seen:
                continue
            # basic sanity checks
            if not isinstance(problem, str) or not problem.strip():
                continue
            if explanation is None or not str(explanation).strip():
                continue
            seen.add(key)
            out.append({"problem": problem, "answer": answer, "explanation": explanation})
        except Exception as e:
            print(f"[gen_error] {e}", file=sys.stderr)
            continue

    if len(out) < count:
        raise RuntimeError(f"Failed to generate enough problems: got {len(out)} of {count}")

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()