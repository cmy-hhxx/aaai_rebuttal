import sys, json, random, re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any

# ----------------------------
# Normative logic core
# ----------------------------

MOD_OBL = "¶"   # obligation
MOD_PER = "§"   # permission
MOD_PRO = "‽"   # prohibition

def neg(prop: str) -> str:
    """prop is like 'p' or '¬p' (single neg allowed here)."""
    return prop[1:] if prop.startswith("¬") else "¬" + prop

def norm(mod: str, prop: str) -> str:
    return f"{mod}{prop}"

RELATIONS = {
    "*": [(norm(MOD_OBL, "p"), norm(MOD_PER, "¬p")),
          (norm(MOD_PRO, "p"), norm(MOD_PER, "p"))],
    "x": [(norm(MOD_OBL, "p"), norm(MOD_PRO, "p"))],
    "@": [(norm(MOD_PER, "p"), norm(MOD_PER, "¬p"))],
    "%": [(norm(MOD_OBL, "p"), norm(MOD_PER, "p")),
          (norm(MOD_PRO, "p"), norm(MOD_PER, "¬p"))],
}
REL_CODE = {"*":"A", "x":"B", "@":"C", "%":"D"}

# Canonical formulas (keep numbering consistent with seed)
FORMULAS = {
    1: "¶p←→¬§¬p",
    2: "‽p←→¬§p",
    3: "§p←→¬‽p",
    4: "§¬p←→¬¶p",
    5: "¶p→¬‽p",
    6: "‽p→¬¶p",
    7: "¬§p→§¬p",
    8: "¬§¬p→§p",
    9: "¶p→§p",
    10:"‽p→§¬p",
    11:"¬§p→¬¶p",
    12:"¬§¬p→¬‽p",
}

# For relationship question, we need map from pair to relation type
def relation_type_for_pair(a: str, b: str) -> Optional[str]:
    # a,b use p placeholder; match by structure
    for rel, pairs in RELATIONS.items():
        for x,y in pairs:
            if (a==x and b==y) or (a==y and b==x):
                return rel
    return None

# ----------------------------
# Text generation helpers (Chinese)
# ----------------------------

@dataclass
class Atom:
    name: str  # p,q,r...
    text: str  # Chinese description

SCENES = [
    "社区管理规定", "校园行为规范", "医院管理办法", "图书馆规则", "地铁乘车守则",
    "博物馆参观须知", "公司合规手册", "考试纪律", "网络平台公约", "公共安全条例",
    "环保倡议与约束", "运动场馆管理制度"
]

# actions with polarity (base is positive; its negation is expressed as "不/未/不进行")
ACTION_POOL = [
    ("在走廊里奔跑", "在走廊里奔跑"),
    ("携带易燃易爆物品进入场所", "携带易燃易爆物品进入场所"),
    ("按规定佩戴口罩", "按规定佩戴口罩"),
    ("在指定区域吸烟", "在指定区域吸烟"),
    ("在图书馆保持安静", "在图书馆保持安静"),
    ("考试中使用手机", "考试中使用手机"),
    ("按时归还借阅图书", "按时归还借阅图书"),
    ("随意丢弃垃圾", "随意丢弃垃圾"),
    ("在地铁内饮食", "在地铁内饮食"),
    ("泄露客户隐私", "泄露客户隐私"),
    ("按流程报销", "按流程报销"),
    ("未经授权复制软件", "未经授权复制软件"),
    ("在馆内触摸展品", "在馆内触摸展品"),
    ("在平台发布虚假信息", "在平台发布虚假信息"),
    ("进行价格欺诈", "进行价格欺诈"),
    ("不履行合同", "不履行合同"),
    ("履行合同", "履行合同"),
    ("虐待老年人", "虐待老年人"),
    ("保护公共财物", "保护公共财物"),
]

NEG_PREFIXES = ["不", "未", "禁止去"]  # for rendering ¬p variants (simple)

def render_neg(text: str, rnd: random.Random) -> str:
    # simple heuristic: try to add "不/未" in front; if already begins with 不/未/禁止/不得, just return "不"+text
    if text.startswith(("不","未","禁止","不得")):
        return "未" + text
    prefix = rnd.choice(NEG_PREFIXES[:2])
    return prefix + text

def format_prop(atom: Atom, is_neg: bool, rnd: random.Random) -> str:
    return render_neg(atom.text, rnd) if is_neg else atom.text

# ----------------------------
# Question families
# ----------------------------

def make_q1_symbolize(rnd: random.Random) -> Tuple[str, str, str]:
    """
    Symbolize a combined proposition with 2-3 clauses with modalities.
    Answer: string like [[§p∧‽q]] or [[¶p∧§¬q∧‽r]]
    """
    # choose 2-3 distinct atoms
    letters = list("pqrstuv")
    rnd.shuffle(letters)
    k = rnd.choice([2,2,3])
    chosen = letters[:k]

    actions = rnd.sample(ACTION_POOL, k)
    atoms = [Atom(chosen[i], actions[i][1]) for i in range(k)]

    # assign modalities with some structure variety
    # Ensure not contradictory in surface (allowed).
    modalities = []
    for i in range(k):
        modalities.append(rnd.choice([MOD_OBL, MOD_PER, MOD_PRO]))

    # For each clause also choose negation sometimes (except make language natural)
    negs = []
    for i in range(k):
        if modalities[i] == MOD_PRO:
            # prohibition typically about positive action; allow occasional neg
            negs.append(rnd.random() < 0.15)
        elif modalities[i] == MOD_OBL:
            negs.append(rnd.random() < 0.25)
        else:
            negs.append(rnd.random() < 0.30)

    # Build Chinese statement with connectors
    scene = rnd.choice(SCENES)
    connectors = ["并且", "同时", "但", "然而", "而且"]
    clauses = []
    for atom, mod, is_neg in zip(atoms, modalities, negs):
        act_txt = format_prop(atom, is_neg, rnd)
        if mod == MOD_PER:
            clause = f"允许{act_txt}"
        elif mod == MOD_OBL:
            clause = f"必须{act_txt}"
        else:
            clause = f"禁止{act_txt}"
        clauses.append(clause)

    # make 2-3 clause sentence
    if len(clauses) == 2:
        sent = f"在{scene}中：{clauses[0]}，{rnd.choice(connectors)}{clauses[1]}。"
    else:
        sent = f"在{scene}中：{clauses[0]}，{rnd.choice(connectors)}{clauses[1]}，并且{clauses[2]}。"

    # Define p/q/r statements
    defs = []
    for atom in atoms:
        defs.append(f"令 {atom.name} 表示：“{atom.text}”。")
    defs_txt = "\n".join(defs)

    # Build symbolic answer
    sym_parts = []
    for atom, mod, is_neg in zip(atoms, modalities, negs):
        prop = neg(atom.name) if is_neg else atom.name
        sym_parts.append(norm(mod, prop))
    sym = "∧".join(sym_parts)
    ans = f"[[{sym}]]"

    # Explanation: map each clause to symbol
    exp_lines = [
        "逐句翻译为规范命题：",
    ]
    for atom, mod, is_neg in zip(atoms, modalities, negs):
        prop = neg(atom.name) if is_neg else atom.name
        cn_mod = {"¶":"必须/有义务", "§":"允许/有权", "‽":"禁止"}[mod]
        exp_lines.append(f"- “{cn_mod}{'不' if is_neg else ''}{atom.text}”对应 {norm(mod, prop)}")
    exp = "\n".join(exp_lines)
    problem = (
        "1）将下述命题符号化（使用 ¶ 表示义务，§ 表示许可，‽ 表示禁止；¬ 表示否定；∧ 表示“并且”）。\n\n"
        f"{sent}\n\n"
        f"{defs_txt}\n\n"
        "请按 [[...]] 格式作答。"
    )
    return problem, ans, exp

def make_q2_relation(rnd: random.Random) -> Tuple[str, str, str]:
    """
    Ask relationship between two pairs. Return [[X];[Y]] with A/B/C/D.
    """
    # choose two relation templates, sometimes different
    rels = rnd.sample(list(RELATIONS.keys()), 2)

    # make two independent pairs with concrete p for each statement
    pairs_rendered = []
    ans_codes = []
    exp_lines = []

    for idx, rel in enumerate(rels, start=1):
        # pick one of the pair patterns in that relation
        pat = rnd.choice(RELATIONS[rel])
        a_pat, b_pat = pat  # e.g. '¶p' and '‽p'
        # pick an action for "p"
        act = rnd.choice(ACTION_POOL)[1]
        scene = rnd.choice(SCENES)
        # render two statements in Chinese according to modality and possible neg
        def render_statement(normpat: str) -> str:
            mod = normpat[0]
            prop = normpat[1:]  # 'p' or '¬p'
            is_neg = prop.startswith("¬")
            act_txt = render_neg(act, rnd) if is_neg else act
            if mod == MOD_OBL:
                return f"在{scene}中，必须{act_txt}。"
            if mod == MOD_PER:
                return f"在{scene}中，允许{act_txt}。"
            return f"在{scene}中，禁止{act_txt}。"

        s1 = render_statement(a_pat)
        s2 = render_statement(b_pat)
        pairs_rendered.append((s1, s2))

        ans_codes.append(REL_CODE[rel])
        # explanation: identify pair pattern
        exp_lines.append(f"（{idx}）对应的命题形式是 {a_pat} 与 {b_pat}，属于 {rel} 关系，因此选 {REL_CODE[rel]}。")

    problem = (
        "2）判断下列两组句子各自属于哪一种规范命题关系。\n"
        "关系选项：A.* 关系  B.x 关系  C.@ 关系  D.% 关系\n\n"
        f"（1）{pairs_rendered[0][0]}\n    {pairs_rendered[0][1]}\n\n"
        f"（2）{pairs_rendered[1][0]}\n    {pairs_rendered[1][1]}\n\n"
        "请按 [[A/B/C/D];[A/B/C/D]] 格式作答。"
    )
    ans = f"[[{ans_codes[0]}];[{ans_codes[1]}]]"
    exp = "\n".join(exp_lines)
    return problem, ans, exp

def make_q3_formula_match(rnd: random.Random) -> Tuple[str, str, str]:
    """
    Given a bidirectional inference between two normative statements, ask which formula number.
    We choose among biconditionals: 1,2,3,4.
    """
    choice = rnd.choice([1,2,3,4])
    # pick action for p
    act = rnd.choice(ACTION_POOL)[1]
    scene = rnd.choice(SCENES)

    # Build the two statements depending on formula
    if choice == 1:
        # ¶p <-> ¬§¬p
        sA = f"在{scene}中，必须{act}。"
        sB = f"在{scene}中，不允许{render_neg(act, rnd)}。"
        exp = f"题干是“¶p 与 ¬§¬p 可相互推出”，对应公式（1）{FORMULAS[1]}。"
    elif choice == 2:
        # ‽p <-> ¬§p
        sA = f"在{scene}中，禁止{act}。"
        sB = f"在{scene}中，不允许{act}。"
        exp = f"题干是“‽p 与 ¬§p 可相互推出”，对应公式（2）{FORMULAS[2]}。"
    elif choice == 3:
        # §p <-> ¬‽p
        sA = f"在{scene}中，允许{act}。"
        sB = f"在{scene}中，并非禁止{act}。"
        exp = f"题干是“§p 与 ¬‽p 可相互推出”，对应公式（3）{FORMULAS[3]}。"
    else:
        # §¬p <-> ¬¶p
        sA = f"在{scene}中，允许{render_neg(act, rnd)}。"
        sB = f"在{scene}中，并非必须{act}。"
        exp = f"题干是“§¬p 与 ¬¶p 可相互推出”，对应公式（4）{FORMULAS[4]}。"

    problem = (
        "3）下述推理是双向成立的（A 可推出 B，B 也可推出 A）。它对应哪一条规范推理公式？\n\n"
        f"A：{sA}\n"
        f"B：{sB}\n\n"
        "请按 [[数字]] 格式作答（数字为公式编号 1-12）。"
    )
    ans = f"[[{choice}]]"
    return problem, ans, exp

def make_q4_infer_from_9_or_10(rnd: random.Random) -> Tuple[str, str, str]:
    """
    Multiple-choice: infer using formula 9 or 10.
    """
    use = rnd.choice([9,10])
    act = rnd.choice(ACTION_POOL)[1]
    scene = rnd.choice(SCENES)

    if use == 9:
        stem = f"在{scene}中，必须{act}。"
        # infer §p
        options = [
            f"A：允许{render_neg(act, rnd)}。",
            f"B：禁止{act}。",
            f"C：允许{act}。",
            f"D：禁止{render_neg(act, rnd)}。"
        ]
        correct = "C"
        exp = f"由公式（9）{FORMULAS[9]}：¶p → §p，因此从“必须{act}”推出“允许{act}”，选 C。"
    else:
        stem = f"在{scene}中，禁止{act}。"
        # infer §¬p
        options = [
            f"A：允许{render_neg(act, rnd)}。",
            f"B：禁止{render_neg(act, rnd)}。",
            f"C：允许{act}。",
            f"D：必须{act}。"
        ]
        correct = "A"
        exp = f"由公式（10）{FORMULAS[10]}：‽p → §¬p，因此从“禁止{act}”推出“允许不{act}”（即允许¬p），选 A。"

    problem = (
        f"4）根据规范推理公式（{use}），从下述命题可以推出哪一项？\n\n"
        f"题干：{stem}\n\n"
        "选项：\n" + "\n".join(options) + "\n\n"
        "请按 [[A/B/C/D]] 格式作答。"
    )
    ans = f"[[{correct}]]"
    return problem, ans, exp

def make_q5_relation_for_formula(rnd: random.Random) -> Tuple[str, str, str]:
    """
    Ask which relationship a formula conforms to. For 7 or 8 -> @ relation.
    We also include 5/6 correspond to x, 9/10 correspond to %, 1/2 correspond to *, etc.
    """
    # map formula to relationship type (by the pair it links most directly)
    # We'll ask about one selected formula among these.
    candidates = [5,6,7,8,9,10]
    fno = rnd.choice(candidates)

    if fno == 5:
        # ¶p -> ¬‽p suggests incompatibility between ¶p and ‽p => x
        rel = "x"
        reasoning = f"公式（5）{FORMULAS[5]} 表明 ¶p 与 ‽p 不能同真，属于 x 关系。"
    elif fno == 6:
        rel = "x"
        reasoning = f"公式（6）{FORMULAS[6]} 表明 ‽p 与 ¶p 不能同真，属于 x 关系。"
    elif fno == 7:
        rel = "@"
        reasoning = f"公式（7）{FORMULAS[7]} 等价于“若非§p，则§¬p”，体现 §p 与 §¬p 不能同假，属于 @ 关系。"
    elif fno == 8:
        rel = "@"
        reasoning = f"公式（8）{FORMULAS[8]} 等价于“若非§¬p，则§p”，体现 §p 与 §¬p 不能同假，属于 @ 关系。"
    elif fno == 9:
        rel = "%"
        reasoning = f"公式（9）{FORMULAS[9]} 给出 ¶p → §p，这对应 ¶p 与 §p 的配对，属于 % 关系。"
    else:
        rel = "%"
        reasoning = f"公式（10）{FORMULAS[10]} 给出 ‽p → §¬p，这对应 ‽p 与 §¬p 的配对，属于 % 关系。"

    problem = (
        "5）下列哪一种“规范命题关系”最符合给定的规范推理公式？\n\n"
        f"给定公式：({fno}) {FORMULAS[fno]}\n\n"
        "选项：A.* 关系  B.x 关系  C.@ 关系  D.% 关系\n\n"
        "请按 [[A/B/C/D]] 格式作答。"
    )
    ans = f"[[{REL_CODE[rel]}]]"
    exp = reasoning
    return problem, ans, exp

# ----------------------------
# Composite problem generator (mix families)
# ----------------------------

FAMILIES = [make_q1_symbolize, make_q2_relation, make_q3_formula_match, make_q4_infer_from_9_or_10, make_q5_relation_for_formula]

def canonicalize_problem_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

def generate_one(rnd: random.Random) -> Dict[str, Any]:
    maker = rnd.choice(FAMILIES)
    problem, answer, explanation = maker(rnd)
    return {"problem": problem, "answer": answer, "explanation": explanation}

def self_check_item(item: Dict[str, Any]) -> None:
    assert isinstance(item.get("problem"), str) and item["problem"].strip()
    assert "answer" in item
    assert isinstance(item.get("explanation"), str) and item["explanation"].strip()
    # format checks for answer
    ans = item["answer"]
    assert isinstance(ans, str)
    assert ans.startswith("[[") and ans.endswith("]]")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rnd = random.Random(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        item = generate_one(rnd)
        key = canonicalize_problem_text(item["problem"])
        if key in seen:
            continue
        try:
            self_check_item(item)
        except Exception as e:
            print(f"[self_check_failed] {e}", file=sys.stderr)
            continue
        seen.add(key)
        results.append(item)

    if len(results) < count:
        raise RuntimeError(f"生成失败：仅生成 {len(results)}/{count} 题（已尝试 {attempts} 次）。")

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()