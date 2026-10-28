import sys, json, random, itertools, re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set, Any

# We will use sympy for robust boolean simplification and equivalence checking
import sympy as sp


# -----------------------------
# Utilities: parsing/printing
# -----------------------------

VAR_NAMES = ["p", "q", "r", "s", "t"]

def sympy_var(ch: str) -> sp.Symbol:
    return sp.Symbol(ch)

def to_sympy(expr: str, varset: Set[str]) -> sp.Expr:
    """
    Parse our custom syntax into sympy boolean expression.
    Supported operators:
      !  negation
      &  and
      |  or
      >  implication
      =  equivalence
      ⇑ NAND
      ⇓ NOR
      constants: 0,1
    """
    s = expr.strip()

    # Normalize some unicode alternatives if any
    s = s.replace("∣", "|").replace("﹁", "!")

    # Tokenization and shunting-yard
    # Operators precedence: ! highest, then & , then | , then > , then = lowest
    # NAND/NOR treated like binary at same precedence as &/|? We'll map:
    #   A ⇑ B ::=:: !A | !B  (so like OR after negation)
    #   A ⇓ B ::=:: !A & !B  (so like AND after negation)
    # We'll parse them as operators with precedence between & and | doesn't matter if parenthesized;
    # but to be consistent, set ⇑ with precedence like |, ⇓ like &.
    prec = {
        "!": 5,
        "&": 4,
        "⇓": 4,
        "|": 3,
        "⇑": 3,
        ">": 2,
        "=": 1,
    }
    assoc = {
        "!": "right",
        "&": "left",
        "⇓": "left",
        "|": "left",
        "⇑": "left",
        ">": "right",
        "=": "left",
    }

    def is_var(tok: str) -> bool:
        return tok in varset

    # tokenize
    tokens = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in "()!&|>=":
            tokens.append(c)
            i += 1
            continue
        if c in ["⇑", "⇓"]:
            tokens.append(c)
            i += 1
            continue
        if c in "01":
            tokens.append(c)
            i += 1
            continue
        # variable letter
        if re.match(r"[a-zA-Z]", c):
            tokens.append(c)
            i += 1
            continue
        raise ValueError(f"无法解析的字符: {c} in {s}")

    # shunting-yard to RPN
    output = []
    opstack = []

    def pop_op():
        op = opstack.pop()
        output.append(op)

    prev = None
    for tok in tokens:
        if tok == "(":
            opstack.append(tok)
        elif tok == ")":
            while opstack and opstack[-1] != "(":
                pop_op()
            if not opstack:
                raise ValueError("括号不匹配")
            opstack.pop()
        elif tok in prec:
            if tok == "!":
                # unary, push directly with precedence
                while opstack and opstack[-1] in prec:
                    top = opstack[-1]
                    if (prec[top] > prec[tok]) or (prec[top] == prec[tok] and assoc[tok] == "left"):
                        pop_op()
                    else:
                        break
                opstack.append(tok)
            else:
                while opstack and opstack[-1] in prec:
                    top = opstack[-1]
                    if (prec[top] > prec[tok]) or (prec[top] == prec[tok] and assoc[tok] == "left"):
                        pop_op()
                    else:
                        break
                opstack.append(tok)
        else:
            # operand
            if tok == "1":
                output.append(True)
            elif tok == "0":
                output.append(False)
            elif is_var(tok):
                output.append(sympy_var(tok))
            else:
                # allow unknown vars but add anyway
                output.append(sympy_var(tok))
        prev = tok

    while opstack:
        if opstack[-1] in ("(", ")"):
            raise ValueError("括号不匹配")
        pop_op()

    # Evaluate RPN
    st = []
    for tok in output:
        if tok is True or tok is False or isinstance(tok, sp.Symbol):
            st.append(tok)
        elif tok == "!":
            if not st:
                raise ValueError("一元运算符缺少操作数")
            a = st.pop()
            st.append(sp.Not(a))
        else:
            if len(st) < 2:
                raise ValueError(f"二元运算符 {tok} 缺少操作数")
            b = st.pop()
            a = st.pop()
            if tok == "&":
                st.append(sp.And(a, b))
            elif tok == "|":
                st.append(sp.Or(a, b))
            elif tok == ">":
                st.append(sp.Implies(a, b))
            elif tok == "=":
                st.append(sp.Equivalent(a, b))
            elif tok == "⇑":
                # NAND: !A | !B  (as per given rule 15)
                st.append(sp.Or(sp.Not(a), sp.Not(b)))
            elif tok == "⇓":
                # NOR: !A & !B  (as per given rule 16)
                st.append(sp.And(sp.Not(a), sp.Not(b)))
            else:
                raise ValueError(f"未知运算符: {tok}")
    if len(st) != 1:
        raise ValueError("表达式解析失败")
    return st[0]


def sympy_to_custom(e: sp.Expr) -> str:
    """
    Convert sympy boolean expression into custom syntax using only ! & | and constants 0/1.
    Parentheses are inserted only when needed by precedence.
    """
    # Simplify to a form that uses And/Or/Not/True/False only
    e = sp.simplify_logic(e, form=None)  # may return True/False
    # In rare cases, simplify_logic may return a symbol etc; handle generically

    prec = {"|": 1, "&": 2, "!": 3}

    def rec(x) -> Tuple[str, int]:
        if x is True:
            return "1", 4
        if x is False:
            return "0", 4
        if isinstance(x, sp.Symbol):
            return str(x), 4
        if isinstance(x, sp.Not):
            a = x.args[0]
            sa, pa = rec(a)
            # ! has highest; parenthesize operand if it's an op with lower/equal precedence than !
            if pa < prec["!"]:
                return f"!({sa})", prec["!"]
            else:
                return f"!{sa}", prec["!"]
        if isinstance(x, sp.And):
            parts = []
            for arg in x.args:
                sa, pa = rec(arg)
                if pa < prec["&"]:
                    sa = f"({sa})"
                parts.append(sa)
            return "&".join(parts), prec["&"]
        if isinstance(x, sp.Or):
            parts = []
            for arg in x.args:
                sa, pa = rec(arg)
                if pa < prec["|"]:
                    sa = f"({sa})"
                parts.append(sa)
            return "|".join(parts), prec["|"]
        # If other form appears, force boolean simplify via to_dnf then convert
        y = sp.simplify_logic(x, form="dnf")
        if y == x:
            # last resort: str
            return str(y), 4
        return rec(y)

    s, _ = rec(e)
    # Use '|' not '∣'
    return s.replace(" ", "")


def remove_implies_custom(expr: str, varset: Set[str]) -> str:
    """
    Remove > by applying equivalence (10): A > B ::=:: !A | B
    then output in custom syntax with only ! & | (no >,=).
    """
    e = to_sympy(expr, varset)
    # replace Implies explicitly: sympy simplification often already does, but ensure:
    e2 = e.replace(sp.Implies, lambda a, b: sp.Or(sp.Not(a), b))
    # Also eliminate Equivalent if any (not expected in this question):
    e2 = e2.replace(sp.Equivalent, lambda a, b: sp.And(sp.Or(sp.Not(a), b), sp.Or(sp.Not(b), a)))
    return sympy_to_custom(e2)


def is_equivalent(expr1: str, expr2: str, varset: Set[str]) -> bool:
    e1 = to_sympy(expr1, varset)
    e2 = to_sympy(expr2, varset)
    # Check equivalence by tautology of XOR false
    # sympy: simplify_logic(Equivalent(e1,e2)) == True
    eq = sp.simplify_logic(sp.Equivalent(e1, e2))
    return bool(eq is True)


def simplify_custom(expr: str, varset: Set[str]) -> str:
    e = to_sympy(expr, varset)
    return sympy_to_custom(e)


def truth_table_equiv(expr1: str, expr2: str, vars_list: List[str]) -> bool:
    """
    Independent check using explicit truth table enumeration (cross-validate).
    """
    e1 = to_sympy(expr1, set(vars_list))
    e2 = to_sympy(expr2, set(vars_list))
    syms = [sympy_var(v) for v in vars_list]
    for vals in itertools.product([False, True], repeat=len(syms)):
        env = dict(zip(syms, vals))
        v1 = bool(e1.subs(env))
        v2 = bool(e2.subs(env))
        if v1 != v2:
            return False
    return True


# -----------------------------
# Build "exactly one true" constraint
# -----------------------------
def exactly_one(vars_list: List[str]) -> str:
    # XOR of all, but expressed with & | !:
    # exactly one true among n:
    # OR_i (vi & AND_{j!=i} !vj)
    terms = []
    for i, vi in enumerate(vars_list):
        parts = [vi]
        for j, vj in enumerate(vars_list):
            if i != j:
                parts.append(f"!{vj}")
        terms.append("&".join(parts))
    return "|".join([f"({t})" if ("|" in t) else t for t in terms])


# -----------------------------
# Logic-story generator (3 persons)
# -----------------------------
@dataclass
class PersonStatement:
    name: str
    statement_expr: str  # expression in p,q,r with ! & |

@dataclass
class StoryInstance:
    cities: List[str]  # mapped to p,q,r
    persons: List[PersonStatement]
    # outcome:
    city_index: int  # 0..2 corresponds to p,q,r true
    roles: Dict[str, str]  # name -> "全对"/"半对"/"全错"


def statement_truth_under_city(stmt_expr: str, true_idx: int) -> bool:
    varset = {"p", "q", "r"}
    e = to_sympy(stmt_expr, varset)
    env = {sympy_var("p"): (true_idx == 0),
           sympy_var("q"): (true_idx == 1),
           sympy_var("r"): (true_idx == 2)}
    return bool(e.subs(env))


def pick_story(rng: random.Random) -> StoryInstance:
    # Choose 3 cities
    base_cities = ["苏州", "上海", "杭州", "南京", "北京", "广州", "成都", "武汉", "西安", "天津", "重庆", "青岛"]
    cities = rng.sample(base_cities, 3)
    # Map p,q,r to cities[0], cities[1], cities[2]
    # Build three persons each making a 2-atom conjunction about membership/non-membership.
    # We'll use only forms like (±p & ±q), (±q & ±r), (±p & ±r) to be "two claims".
    # For each person we know the two subclaims; classify:
    # 全对: both subclaims true; 半对: exactly one true; 全错: none true.
    # We will sample persons, then search a city assignment such that roles are all distinct.
    person_names = rng.sample(["甲", "乙", "丙", "A", "B", "C", "丁", "戊"], 3)

    # Define possible pair templates (variables)
    pairs = [("p", "q"), ("p", "r"), ("q", "r")]

    def make_expr_for_pair(a, b, sa, sb):
        # sa/sb in {+1,-1} meaning var or !var
        pa = a if sa == 1 else f"!{a}"
        pb = b if sb == 1 else f"!{b}"
        return f"{pa}&{pb}"

    # candidate statements set
    candidates = []
    for a, b in pairs:
        for sa in [1, -1]:
            for sb in [1, -1]:
                candidates.append((a, b, sa, sb, make_expr_for_pair(a, b, sa, sb)))

    # Try to find a set of 3 statements and a true city index producing one of each role.
    # Hard cap attempts.
    for _ in range(500):
        chosen = rng.sample(candidates, 3)
        persons = [PersonStatement(person_names[i], chosen[i][4]) for i in range(3)]

        # ensure diversity (not identical)
        if len({p.statement_expr for p in persons}) < 3:
            continue

        for city_idx in [0, 1, 2]:
            # evaluate each statement's two subclaims truth count
            # Since expr is conjunction of two literals, we can count literal truths directly
            roles = {}
            role_set = set()
            ok = True
            for p, cand in zip(persons, chosen):
                a, b, sa, sb, expr = cand
                # literal truth
                def lit_truth(var, sign):
                    v = (city_idx == 0 and var == "p") or (city_idx == 1 and var == "q") or (city_idx == 2 and var == "r")
                    return v if sign == 1 else (not v)
                t1 = lit_truth(a, sa)
                t2 = lit_truth(b, sb)
                cnt = int(t1) + int(t2)
                if cnt == 2:
                    role = "全对"
                elif cnt == 1:
                    role = "半对"
                else:
                    role = "全错"
                roles[p.name] = role
                role_set.add(role)
            if role_set == {"全对", "半对", "全错"}:
                return StoryInstance(cities=cities, persons=persons, city_index=city_idx, roles=roles)

    raise RuntimeError("故事实例生成失败：无法找到满足全对/半对/全错各一人的配置")


# -----------------------------
# Question families
# -----------------------------
def gen_q1(rng: random.Random) -> Tuple[str, Any, str]:
    # remove implications in nested implies expression
    # build random (A > B) > C with A,B,C as variables or negated variables
    vars_ = rng.sample(VAR_NAMES[:5], 3)
    varset = set(vars_)
    def maybe_neg(v):
        return v if rng.random() < 0.6 else f"!{v}"
    A = maybe_neg(vars_[0])
    B = maybe_neg(vars_[1])
    C = maybe_neg(vars_[2])
    expr = f"({A}>{B})>{C}"
    ans = remove_implies_custom(expr, varset)
    problem = (
        "1：使用基本等值式(10) A>B ::=:: !A|B，将下式中所有“>”消去，"
        "并将结果只用 !、&、| 表示：\n"
        f"{expr}\n"
        "答案格式：[[表达式]]（! 优先级最高，仅在必要时加括号）。"
    )
    explanation = (
        f"将外层与内层蕴含都用 !A|B 替换：\n"
        f"({A}>{B})>{C} ::=:: !({A}>{B}) | {C}，且 {A}>{B} ::=:: !{A} | {B}。\n"
        f"代入并化为只含 !,&,| 得：{ans}。"
    )
    return problem, f"[[{ans}]]", explanation


def gen_q2(rng: random.Random) -> Tuple[str, Any, str]:
    # associativity of implication variant
    vars_ = rng.sample(VAR_NAMES[:5], 3)
    varset = set(vars_)
    p, q, r = vars_
    e1 = f"({p}>{q})>{r}"
    e2 = f"{p}>({q}>{r})"
    eq1 = is_equivalent(e1, e2, varset)
    # cross validate by truth table
    eq2 = truth_table_equiv(e1, e2, vars_)
    if eq1 != eq2:
        raise RuntimeError("等价性验证不一致")
    ans = "A" if eq1 else "B"
    problem = (
        "2：在下列符号系统下，判断两式是否等价（等价选A，不等价选B）：\n"
        f"式①：{e1}\n"
        f"式②：{e2}\n"
        "答案格式：[[A]] 或 [[B]]。"
    )
    explanation = (
        "用真值表逐一枚举三个命题的8种赋值可检验是否处处同值。"
        f"结论：{'等价' if eq1 else '不等价'}，因此选 {ans}。"
    )
    return problem, f"[[{ans}]]", explanation


def gen_q3(rng: random.Random) -> Tuple[str, Any, str]:
    # simplify two expressions
    vars_ = rng.sample(VAR_NAMES[:5], 3)
    varset = set(vars_)
    p, q, r = vars_
    # random build with implies, nand, nor
    expr1 = f"!({p}>({p}|{q}))&{r}"
    # expr2 structure ensuring nontrivial
    expr2 = f"{p}&(((({p}|{q})&!{p})>{q}))"
    s1 = simplify_custom(expr1, varset)
    s2 = simplify_custom(expr2, varset)
    # cross-check by truth table equivalence to simplified forms
    if not truth_table_equiv(expr1, s1, vars_):
        raise RuntimeError("化简校验失败 expr1")
    if not truth_table_equiv(expr2, s2, vars_):
        raise RuntimeError("化简校验失败 expr2")
    problem = (
        "3：按题干给定的16条基本等值式（可用(10)(11)(15)(16)等先消去 >,=,⇑,⇓），"
        "对下列公式做等值演绎化到最简（只用 !、&、|、0、1）：\n"
        f"(1) {expr1}\n"
        f"(2) {expr2}\n"
        "答案格式：[[式(1)最简结果];[式(2)最简结果]]。"
    )
    explanation = (
        f"(1) 先将 A>B 替换为 !A|B，可得整体再用德摩根/吸收律化简，最简为 {s1}。\n"
        f"(2) 同理先去掉蕴含再化简，最简为 {s2}。"
    )
    return problem, f"[[{s1}];[{s2}]]", explanation


def gen_q4(rng: random.Random) -> Tuple[str, Any, str]:
    # validity of given equivalences, randomized but structured
    # We'll craft two candidate equivalences; one true, one false with high probability.
    vars_ = rng.sample(VAR_NAMES[:5], 2)
    varset = set(vars_)
    p, q = vars_

    # Eq(1): tautologically true variant: p ::=:: (p&q)|(p&!q)  (always true)
    left1 = p
    right1 = f"({p}&{q})|({p}&!{q})"

    # Eq(2): make a likely-false one: (p&!q)|(!p&q) ::=:: (p|q)&(!(p|q))  (RHS always 0)
    left2 = f"({p}&!{q})|(!{p}&{q})"
    right2 = f"({p}|{q})&!({p}|{q})"

    v1 = is_equivalent(left1, right1, varset)
    v2 = is_equivalent(left2, right2, varset)
    # cross validate
    if v1 != truth_table_equiv(left1, right1, vars_):
        raise RuntimeError("等价式(1)校验不一致")
    if v2 != truth_table_equiv(left2, right2, vars_):
        raise RuntimeError("等价式(2)校验不一致")

    a1 = "A" if v1 else "B"
    a2 = "A" if v2 else "B"

    problem = (
        "4：根据16条基本等值式，判断下列“::=::”是否成立（成立选A，不成立选B）：\n"
        f"(1) {left1}::=::{right1}\n"
        f"(2) {left2}::=::{right2}\n"
        "答案格式：[[A];[A]]（用 ; 分隔两问）。"
    )
    explanation = (
        f"(1) 右边=(p&q)|(p&!q)=p&(q|!q)=p&1=p，故成立。\n"
        f"(2) 右边为 (p|q)&!(p|q)=A&!A=0，而左边是异或型，非恒为0，故不成立。"
    )
    return problem, f"[[{a1}];[{a2}]]", explanation


def gen_q5(rng: random.Random) -> Tuple[str, Any, str]:
    # ask to symbolize 3 persons statements with p,q,r exactly one true
    inst = pick_story(rng)
    c0, c1, c2 = inst.cities
    # mapping: p->c0, q->c1, r->c2
    names = [ps.name for ps in inst.persons]
    exprs = [ps.statement_expr for ps in inst.persons]

    # Render natural language from expressions like !p&q:
    city_map = {"p": c0, "q": c1, "r": c2}

    def lit_to_cn(lit: str) -> str:
        neg = lit.startswith("!")
        v = lit[1:] if neg else lit
        return f"王教授不来自{city_map[v]}" if neg else f"王教授来自{city_map[v]}"

    def expr_to_cn(e: str) -> str:
        # e is conjunction of two literals a&b
        parts = e.split("&")
        return "，并且".join(lit_to_cn(p) for p in parts)

    stmts_cn = [expr_to_cn(e) for e in exprs]

    problem = (
        "5：某研讨会茶歇时，三位与会者根据口音猜测王教授来自哪里。他们的说法如下：\n\n"
        f"{names[0]}：{stmts_cn[0]}。\n"
        f"{names[1]}：{stmts_cn[1]}。\n"
        f"{names[2]}：{stmts_cn[2]}。\n\n"
        f"令 p 表示“王教授来自{c0}”，q 表示“王教授来自{c1}”，r 表示“王教授来自{c2}”。并且 p、q、r 中恰有一个为真。\n"
        "请把三个人的陈述分别用只含 p,q,r 与 !,&,| 的公式表示。\n"
        "答案格式：[[第一人];[第二人];[第三人]]。"
    )
    explanation = (
        "每个人的陈述都是两个简单命题的合取（“并且”对应 &，“不”对应 !）。"
        f"因此三式依次为：{exprs[0]}，{exprs[1]}，{exprs[2]}。"
    )
    return problem, f"[[{exprs[0]}];[{exprs[1]}];[{exprs[2]}]]", explanation


def gen_q6(rng: random.Random) -> Tuple[str, Any, str]:
    # full story: determine true city and who is fully/half/wrong
    inst = pick_story(rng)
    c0, c1, c2 = inst.cities
    city_true = [c0, c1, c2][inst.city_index]

    persons = inst.persons
    # We will name them A/B/C in problem text but keep mapping to actual statements.
    labels = ["A", "B", "C"]
    mapping = dict(zip(labels, persons))

    # Build B1,B2,B3 etc for each person automatically from their two-literal conjunction
    # Statement: L1 & L2
    # entirely correct: L1 & L2
    # partially correct: (L1 & !L2) | (!L1 & L2)
    # entirely incorrect: !L1 & !L2
    def split_literals(expr: str) -> Tuple[str, str]:
        parts = expr.split("&")
        if len(parts) != 2:
            raise ValueError("需要两个文字的合取")
        return parts[0], parts[1]

    def negate_lit(lit: str) -> str:
        return lit[1:] if lit.startswith("!") else "!" + lit

    def make_triple(expr: str) -> Tuple[str, str, str]:
        l1, l2 = split_literals(expr)
        all_correct = f"{l1}&{l2}"
        half = f"({l1}&{negate_lit(l2)})|({negate_lit(l1)}&{l2})"
        all_wrong = f"{negate_lit(l1)}&{negate_lit(l2)}"
        return all_correct, half, all_wrong

    triples = {}
    for lab, ps in mapping.items():
        triples[lab] = make_triple(ps.statement_expr)

    # encode Professor's remark: one all correct, one half, one all wrong
    # E = OR over all permutations assignment
    labs = labels
    def conj(a, b, c): return f"({a})&({b})&({c})"
    terms = []
    for perm in itertools.permutations(labs, 3):
        lab_all, lab_half, lab_wrong = perm
        allc = triples[lab_all][0]
        half = triples[lab_half][1]
        wrong = triples[lab_wrong][2]
        terms.append(conj(allc, half, wrong))
    E = "|".join([f"({t})" for t in terms])

    # plus exactly one true city
    X = exactly_one(["p", "q", "r"])
    E_total = f"({E})&({X})"

    varset = {"p", "q", "r"}
    simplified = simplify_custom(E_total, varset)

    # Determine unique city by enumerating p,q,r one-hot
    sats = []
    for idx in [0, 1, 2]:
        env = {sympy_var("p"): (idx == 0), sympy_var("q"): (idx == 1), sympy_var("r"): (idx == 2)}
        ok = bool(to_sympy(E_total, varset).subs(env))
        if ok:
            sats.append(idx)
    if sats != [inst.city_index]:
        raise RuntimeError("故事求解不唯一或不一致")

    # Determine which label is which role
    inv = {}
    for lab, ps in mapping.items():
        inv[ps.name] = lab
    # roles stored by actual name -> 全对/半对/全错
    lab_role = {}
    for lab, ps in mapping.items():
        lab_role[lab] = inst.roles[ps.name]

    who_all = [lab for lab in labs if lab_role[lab] == "全对"][0]
    who_half = [lab for lab in labs if lab_role[lab] == "半对"][0]
    who_wrong = [lab for lab in labs if lab_role[lab] == "全错"][0]

    # Build problem text in Chinese based on statements
    city_map = {"p": c0, "q": c1, "r": c2}

    def lit_to_cn(lit: str) -> str:
        neg = lit.startswith("!")
        v = lit[1:] if neg else lit
        return f"不来自{city_map[v]}" if neg else f"来自{city_map[v]}"

    def stmt_to_cn(expr: str) -> str:
        l1, l2 = split_literals(expr)
        return f"王教授{lit_to_cn(l1)}，并且王教授{lit_to_cn(l2)}"

    sA = stmt_to_cn(mapping["A"].statement_expr)
    sB = stmt_to_cn(mapping["B"].statement_expr)
    sC = stmt_to_cn(mapping["C"].statement_expr)

    problem = (
        "6：三人根据口音判断王教授来自哪里（且三地中恰有一地为真）：\n\n"
        f"Person A：{sA}。\n"
        f"Person B：{sB}。\n"
        f"Person C：{sC}。\n\n"
        f"令 p 表示“来自{c0}”，q 表示“来自{c1}”，r 表示“来自{c2}”，且 p、q、r 恰有一个为真。\n"
        "王教授说：“你们之中有一人全对，一人半对（两句话恰对一句），一人全错。”\n\n"
        "定义：对某人陈述 L1&L2，\n"
        "全对：L1&L2；半对：(L1&!L2)|(!L1&L2)；全错：!L1&!L2。\n"
        "将三人的情况合并成逻辑条件后求解王教授来自哪里，并指出谁全对/半对/全错。\n"
        "答案格式：[[城市];[全对:A/B/C];[半对:A/B/C];[全错:A/B/C]]。"
    )

    answer = f"[[{city_true}];[全对:{who_all}];[半对:{who_half}];[全错:{who_wrong}]]"

    explanation = (
        "将三人的陈述写成 L1&L2 形式，再分别写出“全对/半对/全错”的逻辑式；\n"
        "再把“恰一人全对、恰一人半对、恰一人全错”写成所有排列的析取，并与“p,q,r 恰有一真”合取。\n"
        f"化简后的关键条件可写为：{simplified}。\n"
        f"在 p,q,r 的三种一真赋值下逐一代入，仅 {['p','q','r'][inst.city_index]} 为真时满足，因此王教授来自{city_true}。\n"
        f"同时可由两句命题在该赋值下的真值个数确定：全对={who_all}，半对={who_half}，全错={who_wrong}。"
    )
    return problem, answer, explanation


# -----------------------------
# Dispatcher and generation
# -----------------------------
def generate_one(rng: random.Random, idx: int) -> Dict[str, Any]:
    # Mix families
    families = [gen_q1, gen_q2, gen_q3, gen_q4, gen_q5, gen_q6]
    # Weight: ensure story questions appear but not dominate
    weights = [2, 2, 2, 2, 1, 1]
    choice = rng.choices(families, weights=weights, k=1)[0]
    problem, answer, explanation = choice(rng)

    if not isinstance(problem, str) or not problem.strip():
        raise RuntimeError("生成了空题面")
    if explanation is None or not isinstance(explanation, str):
        raise RuntimeError("解释缺失")
    return {"problem": problem, "answer": answer, "explanation": explanation}


def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        print(f"输入不是合法JSON: {e}", file=sys.stderr)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))
    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = count * 50

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng, len(results))
        except Exception as e:
            print(f"生成失败(将重试): {e}", file=sys.stderr)
            continue

        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    if len(results) < count:
        print(f"仅生成 {len(results)}/{count} 道题（已达重试上限）", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()