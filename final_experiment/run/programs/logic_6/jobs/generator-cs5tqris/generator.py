import sys, json, random, math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

# We generate first-order logic symbolization tasks similar in skill to the seed:
# quantifiers, connectives, arity, domain-limited vs universal domain, epsilon-delta continuity,
# "some ... than all ..." patterns, and 0-ary predicate encoding for ground facts.
#
# Output language: Chinese (zh) per user request.

# ------------------------- Utilities -------------------------

def jdump(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))

def eprint(*args):
    print(*args, file=sys.stderr)

def choice(rng, seq):
    return seq[rng.randrange(len(seq))]

def unique_name_pool():
    # variable names for quantifiers; include Greek-like epsilon/delta rendered as ε, δ, etc.
    return ["x", "y", "z", "u", "v", "w", "a", "b", "c", "m", "n", "t", "s", "p", "q",
            "ε", "δ", "λ", "η", "α", "β"]

def fmt_quant(q: str, var: str, body: str) -> str:
    # q in {"A","E"}
    return f"{q}{var}{body}"

def paren(s: str) -> str:
    return f"({s})"

# ------------------------- Formula AST -------------------------

@dataclass(frozen=True)
class Term:
    name: str  # variable or constant symbol

@dataclass(frozen=True)
class Pred:
    name: str
    args: Tuple[Term, ...]  # arity can be 0 (then args=())

@dataclass(frozen=True)
class Not:
    f: Any

@dataclass(frozen=True)
class Bin:
    op: str  # "&" "|" "⇒"
    l: Any
    r: Any

@dataclass(frozen=True)
class Quant:
    q: str  # "A" or "E"
    var: str
    body: Any

def term_str(t: Term) -> str:
    return t.name

def pred_str(p: Pred) -> str:
    if len(p.args) == 0:
        return f"{p.name}"
    return f"{p.name}(" + ",".join(term_str(a) for a in p.args) + ")"

def f_str(f) -> str:
    if isinstance(f, Pred):
        return pred_str(f)
    if isinstance(f, Not):
        inner = f_str(f.f)
        # Keep parentheses for non-atomic
        if isinstance(f.f, Pred):
            return f"∼{inner}"
        return f"∼{paren(inner)}"
    if isinstance(f, Bin):
        return f"{paren(f_str(f.l))}{f.op}{paren(f_str(f.r))}"
    if isinstance(f, Quant):
        return fmt_quant(f.q, f.var, f_str(f.body))
    raise TypeError(f"Unknown formula node: {f}")

# ------------------------- Simple model-checker for finite domains -------------------------

# For uniqueness checks, we interpret predicates with given truth tables on a finite domain.
# Not used for epsilon-delta tasks.

def eval_formula(f, dom: List[str], env: Dict[str, str],
                 interp: Dict[str, Any]) -> bool:
    # interp maps predicate name -> function(args)->bool for arity>=1
    # for 0-ary, function([])->bool or boolean
    if isinstance(f, Pred):
        name = f.name
        args = [env.get(a.name, a.name) for a in f.args]  # variable substitution; constants pass through
        val = interp[name]
        if callable(val):
            return bool(val(args))
        # boolean for 0-ary
        return bool(val)
    if isinstance(f, Not):
        return not eval_formula(f.f, dom, env, interp)
    if isinstance(f, Bin):
        if f.op == "&":
            return eval_formula(f.l, dom, env, interp) and eval_formula(f.r, dom, env, interp)
        if f.op == "|":
            return eval_formula(f.l, dom, env, interp) or eval_formula(f.r, dom, env, interp)
        if f.op == "⇒":
            return (not eval_formula(f.l, dom, env, interp)) or eval_formula(f.r, dom, env, interp)
        raise ValueError(f"Unknown op: {f.op}")
    if isinstance(f, Quant):
        if f.q == "A":
            for d in dom:
                env2 = dict(env)
                env2[f.var] = d
                if not eval_formula(f.body, dom, env2, interp):
                    return False
            return True
        if f.q == "E":
            for d in dom:
                env2 = dict(env)
                env2[f.var] = d
                if eval_formula(f.body, dom, env2, interp):
                    return True
            return False
        raise ValueError(f"Unknown quantifier: {f.q}")
    raise TypeError(f"Unknown node: {f}")

# ------------------------- Generation families -------------------------

class Generator:
    def __init__(self, rng: random.Random, lang: str = "zh"):
        self.rng = rng
        self.lang = lang
        self.used_problems = set()

    def gen(self, target_count: int) -> List[Dict[str, Any]]:
        out = []
        attempts = 0
        while len(out) < target_count and attempts < target_count * 200:
            attempts += 1
            fam = self.rng.random()
            if fam < 0.22:
                item = self.family_zero_ary()
            elif fam < 0.50:
                item = self.family_domain_variants()
            elif fam < 0.72:
                item = self.family_some_than_all()
            else:
                item = self.family_eps_delta()
            if item is None:
                continue
            key = item["problem"]
            if key in self.used_problems:
                continue
            self.used_problems.add(key)
            out.append(item)
        if len(out) < target_count:
            raise RuntimeError(f"生成失败：仅生成 {len(out)}/{target_count} 道题（尝试 {attempts} 次）。")
        return out

    # -------- Family 1: 0-ary predicate encoding for ground facts --------
    def family_zero_ary(self) -> Optional[Dict[str, Any]]:
        rng = self.rng
        # Choose numbers/constants and predicates
        # We'll ask two subquestions: (1) "Only a has property P, and b has property Q"
        # (2) "If R(c,d) then R(e,f)" with binary predicate.
        nums = rng.sample(list(range(2, 21)), 6)
        a, b, c, d, e, f = nums
        # Ensure distinct for nicer reading
        if len({a, b, c, d, e, f}) < 6:
            return None

        Pname = choice(rng, ["Prime", "Even", "Odd", "PerfectSquare"])
        Qname = choice(rng, ["Composite", "MultipleOf3", "MultipleOf5", "NotPrime"])

        # Define unary predicates in text; but symbolization uses 0-ary predicates F(2), etc.
        # We'll keep predicate symbol F for P and H for Q to follow style, but still 0-ary.
        # Important: seed had a slightly nonstandard "only 2 is prime" encoded as F(4)⇒F(2).
        # We will build a logically correct 0-ary encoding using implication from each other
        # constant in a small listed domain. So we must provide the listed domain explicitly.

        # We'll create a finite explicit domain of listed constants to make "only a" meaningful.
        domain = sorted(rng.sample(list(range(2, 31)), rng.randint(4, 6)))
        if a not in domain:
            domain[rng.randrange(len(domain))] = a
        if b not in domain:
            domain[rng.randrange(len(domain))] = b
        domain = sorted(set(domain))
        if len(domain) < 4:
            return None

        # Create 0-ary predicates: F(k) means "k has property P"
        # "Only a has P" over this explicit domain means:
        # F(a) & ∧_{x in domain, x != a} (F(x) ⇒ F(a)) AND also (F(a) ⇒ F(x))? No.
        # Correct: for each x != a: F(x) ⇒ x=a. But with 0-ary, we cannot express equality.
        # However we can encode "if F(x) then F(a)" AND include ¬F(x) for x!=a, but negations are allowed.
        # We'll use: F(a) & ∧_{x!=a} ∼F(x). This is clean with 0-ary atoms.
        # Additionally, "b has Q" is just G(b).
        # We'll also ask a second separate implication with binary predicate R as 0-ary atoms R(c,d).
        # Use G(x,y): x>y style.

        # Build formula strings directly in required notation.
        atoms_not = [f"∼F({x})" for x in domain if x != a]
        part1 = f"F({a})"
        if atoms_not:
            part1 = paren(part1 + "&" + "&".join(atoms_not))
        part1 = part1 + "&" + f"G({b})"

        part2 = f"H({c},{d})⇒H({e},{f})"

        problem = (
            "1：在一阶逻辑中，用 0-元谓词（即不含个体变元的谓词原子，例如 F(2)、H(5,3)）符号化下列命题。\n"
            f"（1）在给定的个体常元集合 D = {{{', '.join(map(str, domain))}}} 中，只有 {a} 具有性质 P，且 {b} 具有性质 Q。\n"
            f"    规定：用 0-元原子 F(n) 表示“n 具有性质 P”；用 0-元原子 G(n) 表示“n 具有性质 Q”。\n"
            f"（2）若 {c} 与 {d} 满足关系 R，则 {e} 与 {f} 满足关系 R。\n"
            f"    规定：用 0-元原子 H(x,y) 表示“x 与 y 满足关系 R”。\n"
            "请按格式 [[...];[...]] 作答。"
        )

        answer = [[part1], [part2]]
        explanation = (
            f"（1）“只有 {a} 具有 P”在显式有限域 D 上可写成：F({a}) 且对每个 x∈D 且 x≠{a} 有 ∼F(x)；再与“{b} 具有 Q”即 G({b}) 合取。\n"
            f"（2）直接用蕴含：H({c},{d})⇒H({e},{f})."
        )
        return {"problem": problem, "answer": answer, "explanation": explanation}

    # -------- Family 2: Domain-limited vs universal domain (needs M(x)) --------
    def family_domain_variants(self) -> Optional[Dict[str, Any]]:
        rng = self.rng
        # Choose two statements types: universal and existential about a class
        subjects = [
            ("学生", "S(x)", "学生"),
            ("医生", "D(x)", "医生"),
            ("猫", "C(x)", "猫"),
            ("行星", "P(x)", "行星"),
        ]
        subj_cn, subj_pred, subj_name = choice(rng, subjects)
        prop1 = choice(rng, [("会游泳", "W(x)"), ("会呼吸", "B(x)"), ("是哺乳动物", "Mamm(x)"), ("会写字", "Write(x)")])
        prop2 = choice(rng, [("左撇子", "Lh(x)"), ("戴眼镜", "Gl(x)"), ("会说两种语言", "Bi(x)"), ("喜欢音乐", "Mu(x)")])
        # Ensure different predicates
        if prop1[1] == prop2[1]:
            return None

        # In domain D1 = set of subj, no need to predicate subj.
        # In domain D2 = universal, need subj_pred (rename to M(x) in statement).
        # We'll provide M(x) name as K(x) in text? But keep "M(x)" as class predicate.
        class_pred = "M(x)"
        # We'll render: (a) AxF(x), ExG(x)
        # (b) Ax(M(x)⇒F(x)), Ex(M(x)&G(x))
        F = prop1[1]
        G = prop2[1]

        ans_a1 = f"Ax{F}"
        ans_a2 = f"Ex{G}"
        ans_b1 = f"Ax({class_pred}⇒{F})"
        ans_b2 = f"Ex({class_pred}&{G})"

        problem = (
            "在两种不同的个体域设定下，符号化下列命题。\n"
            f"命题（1）所有{subj_cn}{prop1[0]}。\n"
            f"命题（2）有些{subj_cn}具有性质“{prop2[0]}”。\n\n"
            "（a）个体域 D1 仅包含所有该类对象（只包含该类对象本身）。\n"
            f"    令 F(x)：x{prop1[0]}；令 G(x)：x{prop2[0]}。\n"
            "    问：（1）（2）分别如何表示？\n\n"
            "（b）个体域 D2 为全体对象（宇宙域）。\n"
            f"    为区分该类对象，引入 M(x)：x 是{subj_name}。\n"
            f"    仍令 F(x)：x{prop1[0]}；G(x)：x{prop2[0]}。\n"
            "    问：（1）（2）分别如何表示？\n\n"
            "请按格式 [[...];[...];[...];[...]] 作答，顺序依次为 (a)(1),(a)(2),(b)(1),(b)(2)。"
        )
        answer = [[ans_a1], [ans_a2], [ans_b1], [ans_b2]]
        explanation = (
            "（a）当个体域只包含该类对象时，不必再用“是该类对象”的谓词筛选：全称用 AxF(x)，存在用 ExG(x)。\n"
            "（b）当个体域是宇宙域时，需要先用 M(x) 限定讨论对象：全称为 Ax(M(x)⇒F(x))，存在为 Ex(M(x)&G(x))。"
        )
        return {"problem": problem, "answer": answer, "explanation": explanation}

    # -------- Family 3: "Some A are R than all B" with universal domain --------
    def family_some_than_all(self) -> Optional[Dict[str, Any]]:
        rng = self.rng
        animals = [
            ("兔子", "乌龟", "跑得比…快", "F(x)", "G(y)", "H(x,y)"),
            ("猎豹", "羚羊", "跑得比…快", "F(x)", "G(y)", "H(x,y)"),
            ("鹰", "鸽子", "飞得比…快", "F(x)", "G(y)", "H(x,y)"),
            ("鲸", "海豚", "游得比…快", "F(x)", "G(y)", "H(x,y)"),
        ]
        a_cn, b_cn, rel_cn, Fp, Gp, Hp = choice(rng, animals)
        # Sometimes ask stronger version: "存在一个A，使得对所有B，..." vs "有些A..."
        variant = choice(rng, ["some", "exists_one"])
        if variant == "some":
            # Ex(F(x) & Ay(G(y) ⇒ H(x,y)))
            ans = f"Ex({Fp}&Ay({Gp}⇒{Hp}))"
            stmt_cn = f"有些{a_cn}{rel_cn}所有{b_cn}。"
        else:
            # Ex(F(x) & Ay(G(y)⇒H(x,y))) is same; but we can add uniqueness? too hard.
            # Instead ask: "存在一个A，使得它不慢于任何B" with allowed L(x,y) as equal
            # We introduce L for equal, and use (H|L).
            stmt_cn = f"存在一只{a_cn}，使得它{rel_cn}或同样快于任何{b_cn}。"
            ans = f"Ex({Fp}&Ay({Gp}⇒({Hp}|L(x,y))))"

        problem = (
            "使用宇宙域（个体域为“所有对象”）符号化下列命题。\n"
            f"命题：{stmt_cn}\n\n"
            f"令 F(x)：x 是{a_cn}；G(y)：y 是{b_cn}；H(x,y)：x 相对 y 满足关系“{rel_cn}”。\n"
            "若题目中出现“或同样快”，再令 L(x,y)：x 与 y 同样快。\n"
            "请按格式 [[...]] 作答。"
        )
        answer = [[ans]]
        explanation = (
            "用存在量词选出那只（或那些）满足条件的 A：Ex(...)\n"
            "再用全称量词覆盖所有 B：Ay(G(y)⇒ ... )，并把“A 是该类对象”与比较关系合取。"
        )
        return {"problem": problem, "answer": answer, "explanation": explanation}

    # -------- Family 4: epsilon-delta continuity-like schema --------
    def family_eps_delta(self) -> Optional[Dict[str, Any]]:
        rng = self.rng
        # Create variants: continuity, uniform continuity, limit definition
        variant = choice(rng, ["continuity", "limit_at_a", "uniform_continuity"])
        # predicates per instruction style
        # L(t): t>0, M(x,y,z): |x-y|<z, N(x,y,z): |f(x)-f(y)|<z
        if variant == "continuity":
            # For every ε>0 exists δ>0 such that for all x: |x-x0|<δ ⇒ |f(x)-f(x0)|<ε
            ans = "Aε(L(ε)⇒(Eδ(L(δ)&Ax(M(x,x0,δ)⇒N(x,x0,ε)))))"
            stmt = "在实数域 R 上，符号化“f 在 x0 处连续”的 ε-δ 定义：对每个 ε>0，存在 δ>0，使得对所有 x，若 |x-x0|<δ，则 |f(x)-f(x0)|<ε。"
        elif variant == "limit_at_a":
            # limit x->a f(x)=b
            # For every ε>0 exists δ>0 such that for all x: 0<|x-a|<δ ⇒ |f(x)-b|<ε
            # Need extra predicate K(x,y,z): 0<|x-y|<z. We'll define via L and M plus not equal; but no equality.
            # We'll introduce Q(x,y): x≠y as primitive (allowed as predicate).
            ans = "Aε(L(ε)⇒(Eδ(L(δ)&Ax((Q(x,a)&M(x,a,δ))⇒N2(x,b,ε)))))"
            stmt = "在实数域 R 上，符号化极限定义：lim_{x→a} f(x)=b，即对每个 ε>0，存在 δ>0，使得对所有 x，若 0<|x-a|<δ，则 |f(x)-b|<ε。"
        else:
            # uniform continuity: for every ε>0 exists δ>0 such that for all x,y: |x-y|<δ ⇒ |f(x)-f(y)|<ε
            ans = "Aε(L(ε)⇒(Eδ(L(δ)&AxAy(M(x,y,δ)⇒N(x,y,ε)))))"
            stmt = "在实数域 R 上，符号化“一致连续”的 ε-δ 定义：对每个 ε>0，存在 δ>0，使得对所有 x,y，若 |x-y|<δ，则 |f(x)-f(y)|<ε。"

        problem = (
            "使用个体域为实数集 R，按给定谓词符号化下列命题。\n"
            f"{stmt}\n\n"
            "约定：L(t)：t>0；M(x,y,z)：|x-y|<z；N(x,y,z)：|f(x)-f(y)|<z。\n"
            "若题目出现 |f(x)-b|<ε，则另引入 N2(x,b,ε)：|f(x)-b|<ε；\n"
            "若题目出现 x≠a，则另引入 Q(x,a)：x≠a。\n"
            "请按格式 [[...]] 作答。"
        )
        answer = [[ans]]
        explanation = (
            "按 ε-δ 句式嵌套量词：先对 ε 作全称 Aε，并用 L(ε) 约束 ε>0；\n"
            "再存在一个正数 δ：Eδ(L(δ)&...)；最后用全称量化 x（或 x,y）并写出蕴含条件。"
        )
        return {"problem": problem, "answer": answer, "explanation": explanation}

# ------------------------- Main -------------------------

def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    gen = Generator(rng, lang="zh")
    items = gen.gen(count)

    # Basic self-check: non-empty fields and formatting brackets present
    for i, it in enumerate(items):
        assert isinstance(it["problem"], str) and it["problem"].strip()
        assert "answer" in it
        assert isinstance(it["explanation"], str) and it["explanation"].strip()
        # Ensure requested bracketed answer shape appears as list nesting
        # (We keep answer as JSON arrays, not a single string.)
    jdump(items)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        eprint("ERROR:", repr(e))
        raise