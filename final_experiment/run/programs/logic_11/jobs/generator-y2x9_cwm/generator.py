import sys, json, random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional

# ----------------------------
# Modal logic generator/solver
# ----------------------------

# We implement a small modal truth system compatible with the seed:
# Operators (surface syntax in problems):
#   # : necessity
#   $ : possibility
#   ! : negation
#   + : conjunction
#   - : disjunction
#   = : equivalence
#   > : implication
#
# Truth-modal inference formulas (numbered 1..16) as given in the seed.
#
# Relationship types between modal propositions about same base p:
#   * between #p and $!p; and between #!p and $p  (cannot both true or both false) -> "contradictory"
#   x between #p and #!p                           (cannot both true, can both false) -> "contrary"
#   @ between $p and $!p                           (cannot both false, can both true) -> "subcontrary"
#   % between #p and $p; and between #!p and $!p   (can both true or both false) -> "subalternation-like (independent)"
#
# Semantics used to compute truth values (standard normal modal with at least one accessible world):
# - We model one current world w0 and N other worlds accessible from w0 (including optionally w0 itself).
# - p is a boolean in each world.
# - #p true at w0 iff p is true in all accessible worlds.
# - $p true at w0 iff p is true in at least one accessible world.
# - Negation, conjunction, disjunction, implication, equivalence are classical at w0.
# This semantics validates the given formulas (notably #p -> $p if accessible set non-empty).
#
# We also provide a second independent verification path for some answers:
# - For relationship questions, verify the relationship definition by exhaustive enumeration of all
#   valuations of p across accessible worlds of small size (N=2).
# - For formula mapping questions, verify entailment by brute force enumeration as well.


# ----------------------------
# Parsing and AST
# ----------------------------

@dataclass(frozen=True)
class Node:
    typ: str
    val: Any = None
    left: Optional["Node"] = None
    right: Optional["Node"] = None

def tokenize(s: str) -> List[str]:
    # tokens: #, $, !, +, -, =, >, (, ), identifiers p q r ...
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in ['#', '$', '!', '+', '-', '=', '>', '(', ')']:
            out.append(c)
            i += 1
            continue
        if c.isalpha():
            j = i
            while j < len(s) and s[j].isalpha():
                j += 1
            out.append(s[i:j])
            i = j
            continue
        raise ValueError(f"无法分词: 位置{i}, 字符{c!r}, 输入{s!r}")
    return out

class Parser:
    def __init__(self, tokens: List[str]):
        self.toks = tokens
        self.i = 0

    def peek(self) -> Optional[str]:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def eat(self, tok: str) -> None:
        if self.peek() != tok:
            raise ValueError(f"期待 {tok}, 实得 {self.peek()}")
        self.i += 1

    def parse(self) -> Node:
        node = self.parse_equiv()
        if self.peek() is not None:
            raise ValueError(f"多余token: {self.peek()}")
        return node

    # precedence (low -> high):
    # equivalence '='
    # implication '>'
    # disjunction '-'
    # conjunction '+'
    # unary: # $ !
    # atom: variable or parenthesized
    def parse_equiv(self) -> Node:
        node = self.parse_impl()
        while self.peek() == '=':
            self.eat('=')
            rhs = self.parse_impl()
            node = Node('equiv', None, node, rhs)
        return node

    def parse_impl(self) -> Node:
        node = self.parse_or()
        while self.peek() == '>':
            self.eat('>')
            rhs = self.parse_or()
            node = Node('impl', None, node, rhs)
        return node

    def parse_or(self) -> Node:
        node = self.parse_and()
        while self.peek() == '-':
            self.eat('-')
            rhs = self.parse_and()
            node = Node('or', None, node, rhs)
        return node

    def parse_and(self) -> Node:
        node = self.parse_unary()
        while self.peek() == '+':
            self.eat('+')
            rhs = self.parse_unary()
            node = Node('and', None, node, rhs)
        return node

    def parse_unary(self) -> Node:
        t = self.peek()
        if t in ('#', '$', '!'):
            self.eat(t)
            child = self.parse_unary()
            if t == '!':
                return Node('not', None, child, None)
            elif t == '#':
                return Node('nec', None, child, None)
            else:
                return Node('pos', None, child, None)
        if t == '(':
            self.eat('(')
            node = self.parse_equiv()
            self.eat(')')
            return node
        if t is None:
            raise ValueError("意外结束")
        if t.isalpha():
            self.eat(t)
            return Node('var', t, None, None)
        raise ValueError(f"无法解析token: {t}")

def parse_expr(s: str) -> Node:
    return Parser(tokenize(s)).parse()


# ----------------------------
# Evaluation under Kripke-style semantics
# ----------------------------

def eval_node(node: Node, worlds: List[Dict[str, bool]]) -> bool:
    # worlds[0] is w0; all worlds are accessible from w0
    typ = node.typ
    if typ == 'var':
        return worlds[0].get(node.val, False)
    if typ == 'not':
        return not eval_node(node.left, worlds)
    if typ == 'and':
        return eval_node(node.left, worlds) and eval_node(node.right, worlds)
    if typ == 'or':
        return eval_node(node.left, worlds) or eval_node(node.right, worlds)
    if typ == 'impl':
        a = eval_node(node.left, worlds)
        b = eval_node(node.right, worlds)
        return (not a) or b
    if typ == 'equiv':
        a = eval_node(node.left, worlds)
        b = eval_node(node.right, worlds)
        return a == b
    if typ == 'nec':
        # necessity at w0: child true in all accessible worlds (we take all worlds list as accessible)
        for w in worlds:
            if not eval_node_at(node.left, worlds, w):
                return False
        return True
    if typ == 'pos':
        for w in worlds:
            if eval_node_at(node.left, worlds, w):
                return True
        return False
    raise ValueError(f"未知节点类型: {typ}")

def eval_node_at(node: Node, worlds: List[Dict[str, bool]], w: Dict[str, bool]) -> bool:
    # Evaluate formula at arbitrary world w, but with same accessibility set (all worlds accessible).
    # For modal operators, still quantify over 'worlds'.
    typ = node.typ
    if typ == 'var':
        return w.get(node.val, False)
    if typ == 'not':
        return not eval_node_at(node.left, worlds, w)
    if typ == 'and':
        return eval_node_at(node.left, worlds, w) and eval_node_at(node.right, worlds, w)
    if typ == 'or':
        return eval_node_at(node.left, worlds, w) or eval_node_at(node.right, worlds, w)
    if typ == 'impl':
        a = eval_node_at(node.left, worlds, w)
        b = eval_node_at(node.right, worlds, w)
        return (not a) or b
    if typ == 'equiv':
        a = eval_node_at(node.left, worlds, w)
        b = eval_node_at(node.right, worlds, w)
        return a == b
    if typ == 'nec':
        for w2 in worlds:
            if not eval_node_at(node.left, worlds, w2):
                return False
        return True
    if typ == 'pos':
        for w2 in worlds:
            if eval_node_at(node.left, worlds, w2):
                return True
        return False
    raise ValueError(f"未知节点类型: {typ}")

def all_world_assignments(vars_: List[str], n_worlds: int) -> List[List[Dict[str, bool]]]:
    # enumerate all boolean assignments for each var in each world; return list of worlds-lists
    total_bits = len(vars_) * n_worlds
    res = []
    for mask in range(1 << total_bits):
        worlds = []
        bit = 0
        for wi in range(n_worlds):
            w = {}
            for v in vars_:
                w[v] = bool((mask >> bit) & 1)
                bit += 1
            worlds.append(w)
        res.append(worlds)
    return res

def entails(phi: str, psi: str, vars_: List[str], n_worlds: int = 2) -> bool:
    # check validity of phi -> psi over all assignments with at least one world (n_worlds fixed >=1)
    n1 = parse_expr(phi)
    n2 = parse_expr(psi)
    for worlds in all_world_assignments(vars_, n_worlds):
        if eval_node(n1, worlds) and (not eval_node(n2, worlds)):
            return False
    return True

def equiv(phi: str, psi: str, vars_: List[str], n_worlds: int = 2) -> bool:
    return entails(phi, psi, vars_, n_worlds) and entails(psi, phi, vars_, n_worlds)


# ----------------------------
# Modal formula table (1..16)
# ----------------------------

FORMULAS = {
    1: ("#p", "!!$!p".replace("!!", ""), "#p ←→ !$!p"),   # we'll use explicit strings below
}

# We'll store as (lhs, rhs, kind) where kind in {"equiv","impl"}.
FORMULA_SPEC = {
    1: ("#p", "!$!p", "equiv"),
    2: ("$p", "!#!p", "equiv"),
    3: ("#!p", "!$p", "equiv"),
    4: ("$!p", "!#p", "equiv"),
    5: ("#p", "!#!p", "impl"),
    6: ("#!p", "!#p", "impl"),
    7: ("!$p", "$!p", "impl"),
    8: ("!$!p", "$p", "impl"),
    9: ("#p", "$p", "impl"),
    10: ("#!p", "$!p", "impl"),
    11: ("!$p", "!#p", "impl"),
    12: ("!$!p", "!#!p", "impl"),
    13: ("#p", "p", "impl"),
    14: ("#!p", "!p", "impl"),
    15: ("p", "$p", "impl"),
    16: ("!p", "$!p", "impl"),
}

def verify_formula_number(n: int, n_worlds: int = 2) -> bool:
    lhs, rhs, kind = FORMULA_SPEC[n]
    if kind == "equiv":
        return equiv(lhs, rhs, ["p"], n_worlds=n_worlds)
    else:
        return entails(lhs, rhs, ["p"], n_worlds=n_worlds)


# ----------------------------
# Relationship checking
# ----------------------------

REL_OPTIONS = {"A": "*", "B": "x", "C": "@", "D": "%"}
REL_BY_PAIR = {
    ("#p", "$!p"): "A",
    ("$!p", "#p"): "A",
    ("#!p", "$p"): "A",
    ("$p", "#!p"): "A",

    ("#p", "#!p"): "B",
    ("#!p", "#p"): "B",

    ("$p", "$!p"): "C",
    ("$!p", "$p"): "C",

    ("#p", "$p"): "D",
    ("$p", "#p"): "D",
    ("#!p", "$!p"): "D",
    ("$!p", "#!p"): "D",
}

def relationship_letter(expr1: str, expr2: str) -> str:
    if (expr1, expr2) in REL_BY_PAIR:
        return REL_BY_PAIR[(expr1, expr2)]
    raise ValueError(f"不支持的关系对: {expr1}, {expr2}")

def verify_relationship_definition(expr1: str, expr2: str, rel_letter: str, n_worlds: int = 2) -> bool:
    # Verify with brute force using semantics:
    # * : cannot both true, cannot both false
    # x : cannot both true, can both false
    # @ : cannot both false, can both true
    # % : can both true or both false (i.e., both are possible)
    n1, n2 = parse_expr(expr1), parse_expr(expr2)
    both_true = False
    both_false = False
    for worlds in all_world_assignments(["p"], n_worlds):
        t1 = eval_node(n1, worlds)
        t2 = eval_node(n2, worlds)
        if t1 and t2:
            both_true = True
        if (not t1) and (not t2):
            both_false = True
    if rel_letter == "A":
        return (not both_true) and (not both_false)
    if rel_letter == "B":
        return (not both_true) and both_false
    if rel_letter == "C":
        return both_true and (not both_false)
    if rel_letter == "D":
        return both_true and both_false
    return False


# ----------------------------
# Problem families
# ----------------------------

def wrap(ans: str) -> str:
    return f"[[{ans}]]"

def wrap2(a: str, b: str) -> str:
    return f"[[{a}];[{b}]]"

def make_symbolization_1(rng: random.Random) -> Tuple[str, str, str]:
    # Single sentence -> one modal formula using p
    templates = [
        ("不可能{pdesc}", "!$p", "“不可能p”等价于“非可能p”，即 !$p。"),
        ("必然不{pdesc}", "#!p", "“必然不p”直接写作 #!p。"),
        ("不必然{pdesc}", "!#p", "“不必然p”写作 !#p。"),
        ("可能不{pdesc}", "$!p", "“可能不p”写作 $!p。"),
        ("必然{pdesc}", "#p", "“必然p”写作 #p。"),
        ("可能{pdesc}", "$p", "“可能p”写作 $p。"),
    ]
    pdesc = rng.choice(["下雨", "系统故障", "考试延期", "航班准点", "该方案可行", "灯是亮的"])
    zh, expr, expl = rng.choice(templates)
    problem = (
        "1：将下列模态命题符号化：\n"
        f"“{zh.format(pdesc=pdesc)}”。\n\n"
        f"设 p 表示“{pdesc}”。\n"
        "请用 [[]] 格式作答。"
    )
    answer = wrap(expr)
    explanation = f"p：{pdesc}。题干为“{zh.format(pdesc=pdesc)}”，符号化为 {expr}。{expl}"
    return problem, answer, explanation

def make_symbolization_2(rng: random.Random) -> Tuple[str, str, str]:
    # Two subquestions with parentheses + outer modal symbols
    # (1) Necessarily (p - !p) or Possibly (p>q) etc.
    # Ensure instruction: "先符号化命题，再用括号括起，最后在括号外加模态符号"
    variant = rng.choice([0, 1, 2])
    if variant == 0:
        # Either p or not p must hold
        ctx = rng.choice(["火星", "密室", "服务器", "考场"])
        pdesc = f"{ctx}存在生命"
        expr1 = "#(p-!p)"
        expl1 = "“必然( p 或 非p )”写作 #(p-!p)。"
    elif variant == 1:
        # Possibly (p+q)
        pdesc = rng.choice(["他提交了作业", "会议如期举行", "列车到站"])
        qdesc = rng.choice(["他通过了课程", "项目验收通过", "乘客顺利出行"])
        expr1 = "$(p+q)"
        expl1 = "“可能( p 且 q )”写作 $(p+q)。"
    else:
        # Necessarily (p>q)
        pdesc = rng.choice(["按下按钮", "输入正确密码", "完成全部测试"])
        qdesc = rng.choice(["门会打开", "系统会解锁", "版本会发布"])
        expr1 = "#(p>q)"
        expl1 = "“必然( 若p则q )”写作 #(p>q)。"

    # second subquestion
    v2 = rng.choice([0, 1, 2])
    if v2 == 0:
        p2 = rng.choice(["小张复习充分", "设备维护到位", "选手发挥稳定"])
        q2 = rng.choice(["他能通过考试", "系统不会宕机", "他能夺冠"])
        expr2 = "$(p>q)"
        expl2 = "“如果p，那么可能q”可表为 $(p>q)（按题干要求将蕴含整体加上可能算子）。"
    elif v2 == 1:
        p2 = rng.choice(["道路结冰", "网络拥堵", "原料短缺"])
        q2 = rng.choice(["可能会堵车", "可能会掉线", "可能会延迟交付"])
        expr2 = "$(p>q)"
        expl2 = "同样按“先括起，再加模态符号”，得到 $(p>q)。"
    else:
        p2 = rng.choice(["他没有带钥匙", "电量不足", "没有权限"])
        q2 = rng.choice(["他进不去房间", "设备无法启动", "无法访问系统"])
        expr2 = "#(!p>q)"
        expl2 = "“必然( 若非p则q )”写作 #(!p>q)。"

    problem = (
        "2：将下列模态命题符号化：\n\n"
        f"(1) {rng.choice(['必然满足以下二者之一：', '必须出现如下二选一情况：'])}"
        f"“{pdesc}”或“并非{pdesc}”。设 p 表示“{pdesc}”。\n"
        f"(2) {rng.choice(['如果', '若'])}“{p2}”，那么{rng.choice(['可能', '有可能'])}“{q2}”。"
        f"设 p 表示“{p2}”，q 表示“{q2}”。\n\n"
        "要求：先符号化命题，再用括号括起，最后在括号外加模态符号。\n"
        "请用 [[];[]] 格式作答。"
    )
    answer = wrap2(expr1, expr2)
    explanation = (
        f"(1) p：{pdesc}，题干是“必然( p 或 非p )”，得 {expr1}。{expl1}\n"
        f"(2) p：{p2}，q：{q2}，按题干格式整体加模态符号，得 {expr2}。{expl2}"
    )
    return problem, answer, explanation

def make_relationship(rng: random.Random) -> Tuple[str, str, str]:
    pairs = [
        ("#p", "$!p", "A"),
        ("#p", "#!p", "B"),
        ("$p", "$!p", "C"),
        ("#p", "$p", "D"),
        ("#!p", "$p", "A"),
        ("#!p", "$!p", "D"),
    ]
    (e1a, e1b, rel1) = rng.choice(pairs)
    (e2a, e2b, rel2) = rng.choice(pairs)
    # verify via brute force (independent check)
    if not verify_relationship_definition(e1a, e1b, rel1):
        raise RuntimeError("关系校验失败1")
    if not verify_relationship_definition(e2a, e2b, rel2):
        raise RuntimeError("关系校验失败2")

    sents = {
        "#p": "必然p",
        "$p": "可能p",
        "#!p": "必然非p",
        "$!p": "可能非p",
    }
    pdesc1 = rng.choice(["该航班准点", "系统安全", "比赛会下雨", "房间里有人"])
    pdesc2 = rng.choice(["项目按期交付", "机器正常运转", "考试顺利进行", "会议如期开始"])

    problem = (
        "3：判断下列每一组句子之间的关系类型。\n\n"
        "关系选项：\n"
        "A. * 关系（不能同真，也不能同假）\n"
        "B. x 关系（不能同真，但可以同假）\n"
        "C. @ 关系（不能同假，但可以同真）\n"
        "D. % 关系（可以同真，也可以同假）\n\n"
        f"(1) 设 p 表示“{pdesc1}”。句子1：“{sents[e1a].replace('p', pdesc1)}”；句子2：“{sents[e1b].replace('p', pdesc1)}”。\n"
        f"(2) 设 p 表示“{pdesc2}”。句子1：“{sents[e2a].replace('p', pdesc2)}”；句子2：“{sents[e2b].replace('p', pdesc2)}”。\n\n"
        "请用 [[A/B/C/D];[A/B/C/D]] 格式作答。"
    )
    answer = wrap2(rel1, rel2)
    explanation = (
        f"(1) 对应形式 {e1a} 与 {e1b}，按定义属于选项 {rel1}。\n"
        f"(2) 对应形式 {e2a} 与 {e2b}，按定义属于选项 {rel2}。"
    )
    return problem, answer, explanation

def make_formula_mapping(rng: random.Random) -> Tuple[str, str, str]:
    # Ask: from statement infer another, which formula number matches
    # Use only forms present in 1..16 to avoid ambiguity.
    candidates = [
        (13, "#p", "p"),
        (14, "#!p", "!p"),
        (9, "#p", "$p"),
        (10, "#!p", "$!p"),
        (11, "!$p", "!#p"),
        (8, "!$!p", "$p"),
        (7, "!$p", "$!p"),
        (5, "#p", "!#!p"),
        (6, "#!p", "!#p"),
        (15, "p", "$p"),
        (16, "!p", "$!p"),
    ]
    num, lhs, rhs = rng.choice(candidates)
    if not verify_formula_number(num):
        raise RuntimeError("公式有效性校验失败")

    # render into Chinese sentence with p meaning
    pdesc = rng.choice(["他会迟到", "系统会崩溃", "灯会亮", "合同会生效", "队伍会获胜"])
    # sentence templates for lhs/rhs
    def render(e: str) -> str:
        if e == "#p": return f"“{pdesc}是必然的”"
        if e == "$p": return f"“{pdesc}是可能的”"
        if e == "!#p": return f"“{pdesc}不是必然的”"
        if e == "!$p": return f"“{pdesc}是不可能的”"
        if e == "p": return f"“{pdesc}”"
        if e == "!p": return f"“并非{pdesc}”"
        if e == "#!p": return f"“必然并非{pdesc}”"
        if e == "$!p": return f"“可能并非{pdesc}”"
        if e == "!#!p": return f"“并非(必然并非{pdesc})”"
        if e == "!$!p": return f"“并非(可能并非{pdesc})”"
        return e.replace("p", pdesc)

    problem = (
        "4：下列推理对应哪一条“真值模态推理公式”（编号1-16）？\n\n"
        f"设 p 表示“{pdesc}”。已知 {render(lhs)}，可推出 {render(rhs)}。\n\n"
        "请用 [[number]] 格式作答。"
    )
    answer = wrap(str(num))
    explanation = f"该推理的形式是 {lhs} → {rhs}，与编号 {num} 的公式一致。"
    return problem, answer, explanation

def make_mcq_formula9(rng: random.Random) -> Tuple[str, str, str]:
    # specifically about formula 9 (#p -> $p), but vary story
    subj = rng.choice(["小林", "小周", "小王", "小陈"])
    event = rng.choice(["夺冠", "通过面试", "成功发布产品", "赢得比赛"])
    problem = (
        "5：根据真值模态推理公式9（#p → $p），由“"
        f"{subj}必然{event}”可以推出什么？\n\n"
        "A. 他可能" + event + "。\n"
        "B. 他必然" + event + "。\n"
        "C. 他不可能" + event + "。\n"
        "D. 他永远不会" + event + "。\n\n"
        "请用 [[A/B/C/D]] 格式作答。"
    )
    answer = wrap("A")
    explanation = "公式9是 #p → $p：由“必然p”可推出“可能p”。因此选 A。"
    return problem, answer, explanation

# ----------------------------
# Assembly: produce 20 questions, each item is one of the above types
# ----------------------------

def generate_one(rng: random.Random) -> Dict[str, Any]:
    makers = [make_symbolization_1, make_symbolization_2, make_relationship, make_formula_mapping, make_mcq_formula9]
    weights = [3, 3, 2, 2, 1]
    maker = rng.choices(makers, weights=weights, k=1)[0]
    p, a, e = maker(rng)
    return {"problem": p, "answer": a, "explanation": e}

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count 必须为正整数")
    except Exception as ex:
        print(f"输入JSON解析失败: {ex}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)

    # Self-check: ensure formula table is valid under our semantics
    # (lightweight, deterministic)
    for n in range(1, 17):
        ok = verify_formula_number(n)
        if not ok:
            print(f"内部校验失败：公式 {n} 在当前语义下不成立", file=sys.stderr)
            sys.exit(2)

    items = []
    seen = set()
    attempts = 0
    max_attempts = count * 40

    while len(items) < count and attempts < max_attempts:
        attempts += 1
        obj = generate_one(rng)
        key = obj["problem"]
        if key in seen:
            continue
        # basic non-empty checks
        if not obj["problem"].strip() or obj["answer"] in (None, "") or obj["explanation"] is None:
            continue
        seen.add(key)
        items.append(obj)

    if len(items) < count:
        print(f"生成失败：在 {attempts} 次尝试后仅生成 {len(items)}/{count} 题（去重后不足）", file=sys.stderr)
        sys.exit(3)

    sys.stdout.write(json.dumps(items, ensure_ascii=False))

if __name__ == "__main__":
    main()