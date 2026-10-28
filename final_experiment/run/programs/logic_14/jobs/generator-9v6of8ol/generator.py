import sys, json, random, itertools, math, re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any


# -----------------------------
# Helpers for formatting logic
# -----------------------------

def fmt_prop(base: str, arg: Optional[str] = None) -> str:
    if arg is None:
        return base
    return f"{base}({arg})"

def fmt_B(agent: str, p: str) -> str:
    return f"B_{agent}({p})"

def fmt_H(agent: str, p: str) -> str:
    return f"H_{agent}({p})"

def fmt_G(group: str, p: str) -> str:
    return f"G_{group}({p})"

def fmt_not(s: str) -> str:
    # keep simple
    if s.startswith("¬"):
        return s[1:]
    return f"¬{s}"

def fmt_and(a: str, b: str) -> str:
    return f"({a} ∧ {b})"

def fmt_or(a: str, b: str) -> str:
    return f"({a} ∨ {b})"

def fmt_imp(a: str, b: str) -> str:
    return f"({a} → {b})"


# -----------------------------
# Domain content pools (Chinese)
# -----------------------------

AGENTS = ["小明", "小红", "小李", "小王", "小陈", "小周", "小赵", "小孙"]
GROUPS = ["G", "团队T", "小组S", "班级C"]

# Atomic proposition templates (kept factual/neutral as "p" symbols; semantics not used)
PROP_TEMPLATES = [
    ("太阳从东方升起", None),
    ("2+2=4", None),
    ("图书馆今天开门", None),
    ("会议在周三举行", None),
    ("门是锁着的", None),
    ("灯是亮着的", None),
    ("这封邮件已发送", None),
    ("公交车会准点到达", None),
    ("这个盒子里有钥匙", None),
    ("明天下雨", None),
]

# For variety, sometimes use symbol p/q/r instead of natural language
SYM_PROPS = ["p", "q", "r", "s", "t"]


# -----------------------------
# Question families
# -----------------------------

@dataclass
class Item:
    problem: str
    answer: Any
    explanation: str

def pick_distinct(rng: random.Random, pool: List[str], k: int) -> List[str]:
    return rng.sample(pool, k)

def choose_prop(rng: random.Random) -> str:
    if rng.random() < 0.45:
        return rng.choice(SYM_PROPS)
    text, arg = rng.choice(PROP_TEMPLATES)
    return fmt_prop(text, arg)

def render_common_preamble() -> str:
    # concise rule excerpt sufficient to solve; consistent with seed logic
    return (
        "【认知逻辑规则】\n"
        "符号：\n"
        "B_i(p)：个体 i 坚信命题 p；G_G(p)：群体 G 的共同信念；H_i(p)：i 对 p 的怀疑。\n"
        "公理/规则（本题仅用到这些）：\n"
        "1) 信念公理：B_i(p) → p。\n"
        "2) 反身性：B_i(p) → B_i(B_i(p))。\n"
        "3) 传递性（可识别关系 R）：若 iRj 且 B_i(p)，则 B_j(p)。\n"
        "4) 一致信念：B_i(p) ∧ B_i(¬p) → ⊥（不可同时坚信 p 与 ¬p）。\n"
        "5) 怀疑引入：H_i(p) → ¬B_i(p)。\n"
        "6) 怀疑传播：若 iRj 且 H_i(p)，则 H_j(p)。\n"
        "共同信念定义：若 G_G(p) 成立，则对群体内每个成员 i 都有 B_i(p)。\n"
    )

def mcq_block(qnum: int, stem: str, options: List[str]) -> str:
    letters = ["A", "B", "C"]
    s = f"{qnum}：{stem}\n"
    for L, opt in zip(letters, options):
        s += f"{L}. {opt}\n"
    s += "请按格式 [[A/B/C]] 作答。\n"
    return s

def make_family_mcq(rng: random.Random) -> Item:
    """
    Generates 6~8 MCQs like the seed, but with varied agents/props and sometimes different query wording.
    Returns answer as '[[X]]====[[Y]]...'
    """
    pre = render_common_preamble()
    a1, a2, a3 = pick_distinct(rng, AGENTS, 3)
    group = rng.choice(GROUPS)
    p = choose_prop(rng)
    q = choose_prop(rng)
    while q == p:
        q = choose_prop(rng)

    # Q1 Belief axiom
    # If B_a1(p) conclude p true
    q1_stem = f"根据信念公理，若 {fmt_B(a1, p)} 成立，可以推出："
    q1_opts = [
        f"{a1} 可能怀疑 {p}",
        f"{p} 为真",
        f"{a1} 并不知道 {p}",
    ]
    ans1 = "B"

    # Q2 Reflexivity
    q2_stem = f"根据反身性公理，若 {fmt_B(a1, p)} 成立，意味着："
    q2_opts = [
        f"{a1} 可能会怀疑 {p}",
        f"{a1} 坚信“自己坚信 {p}”",
        f"群体里其他人都自动知道 {p}",
    ]
    ans2 = "B"

    # Q3 Common belief definition
    q3_stem = f"若 {fmt_G(group, q)} 是群体 {group} 的共同信念，根据定义可推出："
    q3_opts = [
        f"对群体 {group} 中每个成员 i，都有 {fmt_B('i', q)}",
        f"只有 {a1} 坚信 {q}",
        f"{a2} 必然怀疑 {q}",
    ]
    ans3 = "A"

    # Q4 Transitivity via R
    q4_stem = f"已知 {a1}R{a2} 且 {fmt_B(a1, p)}，根据传递性可得 {a2} 对 {p} 的态度是："
    q4_opts = [
        f"{a2} 可能怀疑 {p}",
        f"{a2} 坚信 {p}",
        f"无法确定 {a2} 的态度",
    ]
    ans4 = "B"

    # Q5 Consistent belief
    q5_stem = f"根据一致信念公理，如果出现 {fmt_B(a1, p)} 且 {fmt_B(a1, fmt_not(p))} 同时成立，则说明："
    q5_opts = [
        f"{a1} 的信念是自洽的",
        f"{a1} 的信念中不存在矛盾",
        f"会导出矛盾（⊥），这种组合不可同时成立",
    ]
    ans5 = "C"

    # Q6 Doubt introduction
    q6_stem = f"若 {fmt_H(a3, q)} 成立，根据“怀疑引入”可推出："
    q6_opts = [
        f"{fmt_B(a3, q)}",
        f"{fmt_B(a3, fmt_not(q))}",
        f"{fmt_not(fmt_B(a3, q))}",
    ]
    ans6 = "C"

    # Q7 Doubt spread
    q7_stem = f"若 {a3}R{a2} 且 {fmt_H(a3, q)}，根据“怀疑传播”可推出："
    q7_opts = [
        f"{fmt_B(a2, q)}",
        f"{fmt_B(a2, fmt_not(q))}",
        f"{fmt_H(a2, q)}",
    ]
    ans7 = "C"

    # Q8 expression question (not MCQ): common belief but one doubts
    member = rng.choice([a1, a2, a3])
    q8_stem = (
        f"若 {fmt_G(group, p)} 成立，但个体 {member} 怀疑该命题，即 {fmt_H(member, p)}，"
        f"根据共同信念定义写出可直接陈述的合取表达式：\n"
        "请按格式 [[]] 作答（只写一个逻辑式）。\n"
    )
    ans8 = f"[[{fmt_and(fmt_G(group, p), fmt_H(member, p))}]]"

    problem = (
        pre
        + "\n【问题】\n"
        + mcq_block(1, q1_stem, q1_opts)
        + mcq_block(2, q2_stem, q2_opts)
        + mcq_block(3, q3_stem, q3_opts)
        + mcq_block(4, q4_stem, q4_opts)
        + mcq_block(5, q5_stem, q5_opts)
        + mcq_block(6, q6_stem, q6_opts)
        + mcq_block(7, q7_stem, q7_opts)
        + f"8：{q8_stem}"
    )

    answer = "====".join([f"[[{x}]]" for x in [ans1, ans2, ans3, ans4, ans5, ans6, ans7]]) + "====" + ans8

    explanation = (
        "要点：\n"
        f"1) 由 {fmt_B(a1, p)} 用信念公理 B_i(p)→p，得 {p}。\n"
        f"2) 由反身性 B_i(p)→B_i(B_i(p))，得 {fmt_B(a1, fmt_B(a1, p))}，对应“坚信自己坚信”。\n"
        f"3) 共同信念定义：{fmt_G(group, q)} ⇒ 群体内每个成员都满足 B_i(q)。\n"
        f"4) 传递性：{a1}R{a2} 且 {fmt_B(a1, p)} ⇒ {fmt_B(a2, p)}。\n"
        f"5) 一致信念：{fmt_and(fmt_B(a1, p), fmt_B(a1, fmt_not(p)))} ⇒ ⊥。\n"
        f"6) 怀疑引入：{fmt_H(a3, q)} ⇒ ¬B_{a3}({q})。\n"
        f"7) 怀疑传播：{a3}R{a2} 且 {fmt_H(a3, q)} ⇒ {fmt_H(a2, q)}。\n"
        f"8) 题目要求直接写“共同信念且某人怀疑”的合取：{fmt_and(fmt_G(group, p), fmt_H(member, p))}。"
    )

    # lightweight self-check: ensure answer has 8 parts
    parts = answer.split("====")
    assert len(parts) == 8
    for i in range(7):
        assert re.fullmatch(r"\[\[[ABC]\]\]", parts[i])
    assert parts[7].startswith("[[") and parts[7].endswith("]]")
    return Item(problem=problem, answer=answer, explanation=explanation)


def make_family_entailment(rng: random.Random) -> Item:
    """
    Single-query derivation: given a small set of premises, ask which conclusions are derivable.
    Still multiple choice, but different structure from seed.
    """
    pre = render_common_preamble()
    a, b, c = pick_distinct(rng, AGENTS, 3)
    p = choose_prop(rng)
    group = rng.choice(GROUPS)

    # Build premises
    # Ensure exactly one correct option among A/B/C
    premises = []
    # always include common belief -> B_a(p)
    premises.append(f"{fmt_G(group, p)}")
    # include that a is member of group in narrative (not formal)
    # include aRb to enable transitivity on belief from a to b, but we need B_a(p) from common belief
    premises.append(f"{a}R{b}")
    # include doubt of c to derive not belief
    premises.append(f"{fmt_H(c, p)}")

    stem = (
        "给定如下前提（均可用上方规则推理）：\n"
        + "；".join(premises)
        + "。\n问：下面哪个结论必然可推出？"
    )

    # Derivable:
    # From G_group(p) => B_a(p) (since a is member as stated), then with aRb => B_b(p).
    # From H_c(p) => ¬B_c(p).
    # Choose one as correct, make others not entailed.
    correct = rng.choice(["A", "B", "C"])
    if correct == "A":
        optA = f"{fmt_B(b, p)}"
        optB = f"{fmt_B(c, p)}"
        optC = f"{fmt_H(b, p)}"
        explain = (
            f"由 {fmt_G(group, p)}（共同信念定义）得 {fmt_B(a, p)}；"
            f"再由 {a}R{b} 与传递性，推出 {fmt_B(b, p)}。"
        )
    elif correct == "B":
        optA = f"{fmt_B(c, p)}"
        optB = f"{fmt_not(fmt_B(c, p))}"
        optC = f"{fmt_B(b, fmt_not(p))}"
        explain = f"由怀疑引入：{fmt_H(c, p)} → ¬B_{c}({p})，故可推出 {fmt_not(fmt_B(c, p))}。"
    else:
        optA = f"{fmt_H(b, p)}"
        optB = f"{fmt_B(b, fmt_not(p))}"
        optC = f"{fmt_not(fmt_B(c, p))}"
        explain = f"由怀疑引入：{fmt_H(c, p)} → ¬B_{c}({p})，故可推出 {fmt_not(fmt_B(c, p))}。"

    problem = (
        pre
        + "\n【问题】\n"
        + mcq_block(1, stem, [optA, optB, optC])
    )
    answer = f"[[{correct}]]"
    explanation = "推理： " + explain

    assert re.fullmatch(r"\[\[[ABC]\]\]", answer)
    return Item(problem=problem, answer=answer, explanation=explanation)


def make_family_consistency_check(rng: random.Random) -> Item:
    """
    Ask whether a set of statements is consistent under the axioms.
    Uses only the consistent-belief axiom + doubt intro to create contradictions.
    """
    pre = render_common_preamble()
    a, = pick_distinct(rng, AGENTS, 1)
    p = choose_prop(rng)

    # Construct one of three cases: consistent / inconsistent / insufficient
    case = rng.choice(["inconsistent", "consistent", "unknown"])
    if case == "inconsistent":
        facts = [fmt_B(a, p), fmt_B(a, fmt_not(p))]
        correct = "B"
        reason = f"同时有 {fmt_B(a, p)} 与 {fmt_B(a, fmt_not(p))}，由一致信念公理导出 ⊥，不相容。"
        opts = [
            "相容（无矛盾）",
            "不相容（可推出 ⊥）",
            "无法判断",
        ]
    elif case == "consistent":
        facts = [fmt_H(a, p)]
        # H(a,p) -> ¬B(a,p) doesn't force B(a,¬p)
        correct = "A"
        reason = f"只有 {fmt_H(a, p)}，仅能推出 ¬{fmt_B(a, p)}，并不导致同时坚信 p 与 ¬p，因此相容。"
        opts = [
            "相容（无矛盾）",
            "不相容（可推出 ⊥）",
            "无法判断",
        ]
    else:
        facts = [fmt_not(fmt_B(a, p))]
        correct = "C"
        reason = f"仅给出 ¬{fmt_B(a, p)}，既不说明 {fmt_B(a, p)} 也不说明 {fmt_B(a, fmt_not(p))}，无法据此判定是否会触发一致信念矛盾。"
        opts = [
            "相容（无矛盾）",
            "不相容（可推出 ⊥）",
            "无法判断",
        ]

    stem = "判断下列陈述集合在给定规则下是否相容：\n" + "；".join(facts) + "。"
    problem = pre + "\n【问题】\n" + mcq_block(1, stem, opts)
    answer = f"[[{correct}]]"
    explanation = "依据： " + reason

    assert re.fullmatch(r"\[\[[ABC]\]\]", answer)
    return Item(problem=problem, answer=answer, explanation=explanation)


# -----------------------------
# Generator orchestration
# -----------------------------

def make_one(rng: random.Random) -> Item:
    # mix families for diversity
    r = rng.random()
    if r < 0.55:
        return make_family_mcq(rng)
    elif r < 0.8:
        return make_family_entailment(rng)
    else:
        return make_family_consistency_check(rng)

def normalize_problem_text(s: str) -> str:
    # collapse multiple spaces, keep newlines
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip() + "\n"
    return s

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    items: List[Dict[str, Any]] = []
    seen = set()
    attempts = 0
    max_attempts = max(200, count * 50)

    while len(items) < count and attempts < max_attempts:
        attempts += 1
        try:
            it = make_one(rng)
            it.problem = normalize_problem_text(it.problem)
            key = (it.problem, json.dumps(it.answer, ensure_ascii=False, sort_keys=True))
            if key in seen:
                continue
            seen.add(key)
            items.append({"problem": it.problem, "answer": it.answer, "explanation": it.explanation})
        except AssertionError as e:
            print(f"[gen] assertion failed: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"[gen] error: {type(e).__name__}: {e}", file=sys.stderr)
            continue

    if len(items) < count:
        raise RuntimeError(f"生成失败：仅生成 {len(items)}/{count} 道题（尝试次数 {attempts}）")

    sys.stdout.write(json.dumps(items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()