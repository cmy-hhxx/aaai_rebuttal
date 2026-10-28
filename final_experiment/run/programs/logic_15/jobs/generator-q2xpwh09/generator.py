import sys, json, random, re
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

# ----------------------------
# Dynamic Logic mini generator
# ----------------------------

@dataclass(frozen=True)
class Rule:
    key: str
    name_zh: str
    letter: str
    template: str  # for explanation

RULES: List[Rule] = [
    Rule("substitution", "代换规则", "A", "若 c 与 d 等价，则 [c]φ 等价于 [d]φ。"),
    Rule("sequence", "顺序规则", "B", "[c1; c2]φ 等价于 [c1][c2]φ。"),
    Rule("choice", "选择规则", "C", "[c1 + c2]φ 等价于 ([c1]φ ∨ [c2]φ)。"),
    Rule("loop", "循环规则", "D", "[c*]φ 等价于 φ ∨ ([c][c*]φ)。"),
    Rule("concurrent", "并发规则", "E", "⟨c1 || c2⟩φ 等价于 ⟨c1⟩⟨c2⟩φ ∨ ⟨c2⟩⟨c1⟩φ。"),
    Rule("interruption", "中断规则", "F", "若 c1 可中断 c2，则 ⟨c1; c2⟩φ 等价于 ⟨c1⟩φ。"),
    Rule("exception", "异常规则", "G", "若 c 可能触发异常 e，则 [c]φ 等价于 ([c]φ ∧ [e]φ)。"),
    Rule("resource", "资源限制规则", "H", "若 c 受资源限制 R，则 [c]φ 等价于 (R ∧ [c]φ)。"),
    Rule("dependency", "依赖规则", "I", "若 c1 依赖 c2，则 [c1]φ 等价于 [c2][c1]φ。"),
    Rule("priority", "优先级规则", "J", "若 c1 优先于 c2，则 ⟨c1; c2⟩φ 等价于 ⟨c1⟩⟨c2⟩φ。"),
    Rule("history", "历史规则", "K", "若 c 的执行依赖历史命令 h，则 [c]φ 等价于 [h][c]φ。"),
    Rule("prediction", "预测规则", "L", "若系统可预测 c 的结果，则 [c]φ 等价于 [predict(c)]φ。"),
]
RULE_BY_KEY = {r.key: r for r in RULES}

def wrap(ans: str) -> str:
    return f"[[{ans}]]"

def maybe_spaces(rng: random.Random) -> str:
    return "" if rng.random() < 0.7 else " "

def cmd_name(rng: random.Random, base: str) -> str:
    # allow small variations like c1, a1, op1 etc. but keep simple tokens
    pools = [
        base,
        base.replace("c", "cmd"),
        base.replace("c", "op"),
        base.replace("c", "a"),
    ]
    return rng.choice(pools)

def prop_name(rng: random.Random) -> str:
    return rng.choice(["φ", "ψ", "p", "q", "安全", "成功", "result为真"])

def atom_R(rng: random.Random) -> str:
    return rng.choice(["R", "资源R", "预算满足", "电量充足", "权限已授予"])

def atom_e(rng: random.Random) -> str:
    return rng.choice(["e", "异常e", "error", "故障e"])

def atom_h(rng: random.Random) -> str:
    return rng.choice(["h", "历史h", "log", "初始化h"])

def simplify_expression(expr: str) -> str:
    # This generator only asks for canonical simplest forms based on given equivalences.
    # We enforce the simplest explicitly per task type.
    return expr

# ----------------------------
# Problem families
# ----------------------------

def make_q_seq_necessity(rng: random.Random) -> Tuple[str, str, str]:
    c1 = cmd_name(rng, "c1")
    c2 = cmd_name(rng, "c2")
    phi = prop_name(rng)
    # simplest: use sequence rule to reduce bracket nesting: [c1;c2]phi -> [c1][c2]phi
    ans = f"[{c1}][{c2}]{phi}"
    problem = (
        "用动态逻辑表示：执行命令序列 {c1}; {c2} 之后，命题 {phi} 必然为真。"
        "要求写出等价变形后的最简形式（尽量减少 [] 和 ⟨⟩ 的出现次数），并用 [[...]] 包裹。"
    ).format(c1=c1, c2=c2, phi=phi)
    explanation = (
        f"由顺序规则：[ {c1}; {c2} ]{phi} ≡ [ {c1} ][ {c2} ]{phi}，"
        f"最简写为 {ans}。"
    ).replace("[ ", "[").replace(" ]", "]")
    return problem, wrap(ans), explanation

def make_q_possibility(rng: random.Random) -> Tuple[str, str, str]:
    c = cmd_name(rng, "c")
    phi = prop_name(rng)
    ans = f"⟨{c}⟩{phi}"
    problem = (
        "用动态逻辑表示：执行命令 {c} 之后，命题 {phi} 可能为真。"
        "请用 [[...]] 包裹。"
    ).format(c=c, phi=phi)
    explanation = f"“可能”为可能算子，直接写作 {ans}。"
    return problem, wrap(ans), explanation

def make_q_choice_necessity_simplest(rng: random.Random) -> Tuple[str, str, str]:
    c1 = cmd_name(rng, "c1")
    c2 = cmd_name(rng, "c2")
    phi = prop_name(rng)
    # simplest: expand choice into OR of boxes
    ans = f"([{c1}]{phi} ∨ [{c2}]{phi})"
    problem = (
        "用动态逻辑表示：在选择执行 {c1} 或 {c2} 之后，命题 {phi} 必然为真。"
        "要求写出等价变形后的最简形式（减少 []/⟨⟩），并用 [[...]] 包裹。"
    ).format(c1=c1, c2=c2, phi=phi)
    explanation = (
        f"由选择规则：[ {c1} + {c2} ]{phi} ≡ ([{c1}]{phi} ∨ [{c2}]{phi})，"
        f"因此答案为 {ans}。"
    ).replace("[ ", "[").replace(" ]", "]")
    return problem, wrap(ans), explanation

def make_q_loop_belief(rng: random.Random) -> Tuple[str, str, str]:
    c = cmd_name(rng, "c")
    phi = prop_name(rng)
    # simplest after equivalence? The loop rule expands to phi ∨ ([c][c*]phi) which has more operators.
    # So simplest is to keep [c*]phi.
    ans = f"[{c}*]{phi}"
    subject = rng.choice(["Alice", "小明", "研究员", "机器人"])
    problem = (
        f"{subject} 坚信：循环命令 {c}* 会一直执行直到命题 {phi} 成立。"
        "用动态逻辑写出这种“必然成立”的表达式。"
        "要求写出等价变形后的最简形式（减少 []/⟨⟩），并用 [[...]] 包裹。"
    )
    explanation = (
        f"“循环执行后必然满足”直接用必然算子作用于循环程序表示为 {ans}。"
        f"若展开循环规则会得到 {phi} ∨ ([{c}][{c}*]{phi})，更复杂，因此最简保留 {ans}。"
    )
    return problem, wrap(ans), explanation

def make_q_substitution_equiv(rng: random.Random) -> Tuple[str, str, str]:
    c = cmd_name(rng, "c")
    d = cmd_name(rng, "d")
    phi = prop_name(rng)
    ans = f"[{d}]{phi}"
    problem = (
        "已知命令 {c} 与 {d} 等价（满足代换规则）。问：[ {c} ]{phi} 等价于什么？"
        "请用 [[...]] 包裹。"
    ).format(c=c, d=d, phi=phi)
    explanation = f"由代换规则，等价命令可互换：[ {c} ]{phi} ≡ [ {d} ]{phi}。".replace("[ ", "[").replace(" ]", "]")
    return problem, wrap(ans), explanation

def make_q_concurrent(rng: random.Random) -> Tuple[str, str, str]:
    c1 = cmd_name(rng, "c1")
    c2 = cmd_name(rng, "c2")
    phi = prop_name(rng)
    # simplest: the concurrent rule gives a disjunction of two nested diamonds.
    ans = f"(⟨{c1}⟩⟨{c2}⟩{phi} ∨ ⟨{c2}⟩⟨{c1}⟩{phi})"
    extra = rng.choice([
        "且二者互不影响命题的真值。",
        "并且它们对命题真假没有副作用。",
        "且并发执行不会改变命题的判定条件。",
    ])
    problem = (
        "根据并发规则：若 {c1} 与 {c2} 可并发执行，{extra} 写出表达式 ⟨{c1} || {c2}⟩{phi} 的等价最简形式，"
        "并用 [[...]] 包裹。"
    ).format(c1=c1, c2=c2, phi=phi, extra=extra)
    explanation = (
        f"由并发规则：⟨{c1} || {c2}⟩{phi} ≡ ⟨{c1}⟩⟨{c2}⟩{phi} ∨ ⟨{c2}⟩⟨{c1}⟩{phi}，"
        f"因此答案为 {ans}。"
    )
    return problem, wrap(ans), explanation

def make_q_rule_mc(rng: random.Random, target_key: str, stem: str) -> Tuple[str, str, str]:
    # Multiple-choice asking which rule applies
    rule = RULE_BY_KEY[target_key]
    options = [(r.letter, r.name_zh) for r in RULES]
    opts_text = "\n".join([f"{letter}. {name}" for letter, name in options])
    problem = (
        stem
        + "\n\n下列哪一条规则最匹配上述描述？\n\n"
        + opts_text
        + "\n\n请用 [[A/B/C/...]] 格式作答（只填字母）。"
    )
    explanation = f"题干描述对应“{rule.name_zh}”，因此选 {rule.letter}。规则表述：{rule.template}"
    return problem, wrap(rule.letter), explanation

def make_q_exception_rule(rng: random.Random) -> Tuple[str, str, str]:
    c = cmd_name(rng, rng.choice(["c", "c1", "op1"]))
    e = atom_e(rng)
    phi = prop_name(rng)
    stem = (
        f"执行命令 {c} 后“可能触发异常 {e}”。现在要把“执行 {c} 后 {phi} 必然为真”的断言写成等价形式，"
        f"需要同时考虑异常分支。"
    )
    # If asked as expression, we'd give ([c]φ ∧ [e]φ); but here MC asks rule.
    return make_q_rule_mc(rng, "exception", stem)

def make_q_resource_rule(rng: random.Random) -> Tuple[str, str, str]:
    c = cmd_name(rng, rng.choice(["c", "c2", "cmd"]))
    R = atom_R(rng)
    phi = prop_name(rng)
    stem = (
        f"某系统中，命令 {c} 的执行受资源条件 {R} 限制。"
        f"某人确信：一旦 {R} 满足，执行 {c} 将保证 {phi} 为真。"
    )
    return make_q_rule_mc(rng, "resource", stem)

def make_q_dependency_rule(rng: random.Random) -> Tuple[str, str, str]:
    c1 = cmd_name(rng, "c1")
    c2 = cmd_name(rng, "c2")
    phi = prop_name(rng)
    # ask for simplified equivalence
    ans = f"[{c2}][{c1}]{phi}"
    problem = (
        "已知命令 {c1} 的执行依赖于 {c2}。请将 [ {c1} ]{phi} 写成等价的最简形式，并用 [[...]] 包裹。"
    ).format(c1=c1, c2=c2, phi=phi)
    explanation = f"由依赖规则：[ {c1} ]{phi} ≡ [ {c2} ][ {c1} ]{phi}，故为 {ans}。".replace("[ ", "[").replace(" ]", "]")
    return problem, wrap(ans), explanation

def make_q_history_rule(rng: random.Random) -> Tuple[str, str, str]:
    c = cmd_name(rng, "c")
    h = atom_h(rng)
    phi = prop_name(rng)
    ans = f"[{h}][{c}]{phi}"
    problem = (
        "已知命令 {c} 的执行依赖某个历史命令 {h}（即必须先发生 {h}）。"
        "将 [ {c} ]{phi} 写成等价的最简形式，并用 [[...]] 包裹。"
    ).format(c=c, h=h, phi=phi)
    explanation = f"由历史规则：[ {c} ]{phi} ≡ [ {h} ][ {c} ]{phi}，因此为 {ans}。".replace("[ ", "[").replace(" ]", "]")
    return problem, wrap(ans), explanation

def make_q_prediction_rule(rng: random.Random) -> Tuple[str, str, str]:
    c = cmd_name(rng, "c")
    phi = prop_name(rng)
    ans = f"[predict({c})]{phi}"
    problem = (
        "若系统可以预测命令 {c} 的执行结果。把“执行 {c} 后 {phi} 必然为真”写成等价的最简形式，并用 [[...]] 包裹。"
    ).format(c=c, phi=phi)
    explanation = f"由预测规则：[ {c} ]{phi} ≡ [ predict({c}) ]{phi}，因此答案为 {ans}。".replace("[ ", "[").replace(" ]", "]")
    return problem, wrap(ans), explanation

def make_q_interruption_rule(rng: random.Random) -> Tuple[str, str, str]:
    c1 = cmd_name(rng, "c1")
    c2 = cmd_name(rng, "c2")
    phi = prop_name(rng)
    ans = f"⟨{c1}⟩{phi}"
    problem = (
        "已知 {c1} 可以中断 {c2}。请把 ⟨{c1}; {c2}⟩{phi} 写成等价的最简形式，并用 [[...]] 包裹。"
    ).format(c1=c1, c2=c2, phi=phi)
    explanation = f"由中断规则：⟨{c1}; {c2}⟩{phi} ≡ ⟨{c1}⟩{phi}，故答案为 {ans}。"
    return problem, wrap(ans), explanation

def make_q_priority_rule(rng: random.Random) -> Tuple[str, str, str]:
    c1 = cmd_name(rng, "c1")
    c2 = cmd_name(rng, "c2")
    phi = prop_name(rng)
    ans = f"⟨{c1}⟩⟨{c2}⟩{phi}"
    problem = (
        "已知 {c1} 的优先级高于 {c2}。请把 ⟨{c1}; {c2}⟩{phi} 写成等价的最简形式，并用 [[...]] 包裹。"
    ).format(c1=c1, c2=c2, phi=phi)
    explanation = f"由优先级规则：⟨{c1}; {c2}⟩{phi} ≡ ⟨{c1}⟩⟨{c2}⟩{phi}，故为 {ans}。"
    return problem, wrap(ans), explanation

# pool of generators with weights
GENS = [
    (make_q_seq_necessity, 10),
    (make_q_possibility, 8),
    (make_q_choice_necessity_simplest, 10),
    (make_q_loop_belief, 8),
    (make_q_substitution_equiv, 8),
    (make_q_concurrent, 10),
    (make_q_exception_rule, 6),
    (make_q_resource_rule, 6),
    (make_q_dependency_rule, 6),
    (make_q_history_rule, 6),
    (make_q_prediction_rule, 6),
    (make_q_interruption_rule, 6),
    (make_q_priority_rule, 6),
]

def weighted_choice(rng: random.Random, items):
    total = sum(w for _, w in items)
    x = rng.uniform(0, total)
    s = 0.0
    for it, w in items:
        s += w
        if x <= s:
            return it
    return items[-1][0]

def normalize_for_dedup(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s

def validate_brackets(ans_wrapped: str) -> bool:
    return ans_wrapped.startswith("[[") and ans_wrapped.endswith("]]") and len(ans_wrapped) >= 4

def self_check_one(problem: str, answer: Any, explanation: str):
    if not isinstance(problem, str) or not problem.strip():
        raise ValueError("problem empty")
    if not isinstance(explanation, str) or not explanation.strip():
        raise ValueError("explanation empty")
    if not isinstance(answer, str) or not validate_brackets(answer):
        raise ValueError("answer must be a [[...]] string")
    # quick sanity: require dynamic logic tokens appear
    if all(tok not in problem for tok in ["[", "⟨", "命题", "动态逻辑", "必然", "可能", "规则"]):
        raise ValueError("problem seems off-domain")

def generate(seed: int, count: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    out = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        gen = weighted_choice(rng, GENS)
        problem, answer, explanation = gen(rng)

        key = normalize_for_dedup(problem)
        if key in seen:
            continue

        try:
            self_check_one(problem, answer, explanation)
        except Exception as e:
            print(f"[generator] discard due to validation error: {e}", file=sys.stderr)
            continue

        seen.add(key)
        out.append({"problem": problem, "answer": answer, "explanation": explanation})

    if len(out) < count:
        raise RuntimeError(f"生成失败：仅生成 {len(out)}/{count} 题。可尝试更换 seed 或降低 count。")

    return out

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        print(f"输入不是合法 JSON：{e}", file=sys.stderr)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))
    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        sys.exit(1)

    try:
        data = generate(seed, count)
    except Exception as e:
        print(f"生成出错：{e}", file=sys.stderr)
        sys.exit(1)

    sys.stdout.write(json.dumps(data, ensure_ascii=False))

if __name__ == "__main__":
    main()