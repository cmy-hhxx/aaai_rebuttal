import sys, json, random, itertools
from typing import List, Tuple, Dict, Any

# Syllogism generator/solver for categorical syllogisms (A,E,I,O) with 4 figures.
# Produces problems in Chinese, self-contained, with computed correct answers.

MOODS_BY_FIGURE = {
    "I":  ["AAA", "EAE", "AII", "EIO"],
    "II": ["AEE", "EAE", "EIO", "AOO"],
    "III":["AII", "EIO", "IAI", "OAO"],
    "IV": ["AEE", "EIO", "IAI"],
}

FIGURE_FORMS = {
    # Each form gives (major, minor, conclusion) as strings using placeholders S,P,M with pattern "X()Y"
    # We'll later fill () with the letter of the proposition type.
    "I":  ("M()P", "S()M", "S()P"),
    "II": ("P()M", "S()M", "S()P"),
    "III":("M()P", "M()S", "S()P"),
    "IV": ("P()M", "M()S", "S()P"),
}

# Quantifier semantics for p1 => p2 forms, interpreted with sets:
# A: All p1 are p2  (p1 ⊆ p2)
# E: No p1 are p2   (p1 ∩ p2 = ∅)
# I: Some p1 are p2 (p1 ∩ p2 ≠ ∅)
# O: Some p1 are not p2 (p1 \ p2 ≠ ∅)
# We will express statements as "∀X⇒Y" etc in text, consistent with seed.

TYPE_TO_TEXT = {
    "A": "∀{x}⇒{y}",
    "E": "∀{x}⇒¬{y}",
    "I": "∃{x}⇒{y}",
    "O": "∃{x}⇒¬{y}",
}

def stmt_text(typ: str, x: str, y: str) -> str:
    return TYPE_TO_TEXT[typ].format(x=x, y=y)

def parse_pattern(pattern: str) -> Tuple[str, str]:
    # "M()P" -> ("M","P")
    left = pattern[0]
    right = pattern[-1]
    return left, right

def build_statements(figure: str, mood: str) -> Tuple[Tuple[str,str,str], Tuple[str,str,str], Tuple[str,str,str]]:
    """
    Return (major_stmt, minor_stmt, concl_stmt) each as (type, left, right) where statement is left()right.
    """
    major_pat, minor_pat, concl_pat = FIGURE_FORMS[figure]
    maj_lr = parse_pattern(major_pat)
    min_lr = parse_pattern(minor_pat)
    con_lr = parse_pattern(concl_pat)
    return (mood[0], maj_lr[0], maj_lr[1]), (mood[1], min_lr[0], min_lr[1]), (mood[2], con_lr[0], con_lr[1])

def all_assignments(n=4):
    # universe size n, sets for S,P,M as subsets of U
    U = list(range(n))
    subs = []
    for mask in range(1<<n):
        s = {U[i] for i in range(n) if (mask>>i)&1}
        subs.append(s)
    for S in subs:
        for P in subs:
            for M in subs:
                yield U, S, P, M

def holds(typ: str, left_set: set, right_set: set) -> bool:
    if typ == "A":
        return left_set.issubset(right_set)
    if typ == "E":
        return left_set.isdisjoint(right_set)
    if typ == "I":
        return len(left_set & right_set) > 0
    if typ == "O":
        return len(left_set - right_set) > 0
    raise ValueError("Unknown type")

def stmt_holds(stmt: Tuple[str,str,str], S:set, P:set, M:set) -> bool:
    typ, l, r = stmt
    mapping = {"S": S, "P": P, "M": M}
    return holds(typ, mapping[l], mapping[r])

def validity_check(figure: str, mood: str, n=4) -> bool:
    major, minor, concl = build_statements(figure, mood)
    for _, S, P, M in all_assignments(n):
        if stmt_holds(major, S, P, M) and stmt_holds(minor, S, P, M):
            if not stmt_holds(concl, S, P, M):
                return False
    return True

def compute_all_valid_pairs() -> List[Tuple[str,str]]:
    pairs = []
    for fig, moods in MOODS_BY_FIGURE.items():
        for mood in moods:
            pairs.append((fig, mood))
    # Cross-check with semantics to ensure internal table is consistent.
    # If any fails, we drop it (shouldn't happen).
    ok = []
    for fig, mood in pairs:
        if validity_check(fig, mood, n=4):
            ok.append((fig, mood))
    return ok

VALID_PAIRS = compute_all_valid_pairs()

def figure_name_zh(fig: str) -> str:
    return {"I":"I", "II":"II", "III":"III", "IV":"IV"}[fig]

def problem_text_zh(fig: str, mood: str, variant: int, rng: random.Random) -> Tuple[str, Any, str]:
    major, minor, concl = build_statements(fig, mood)
    # Render the first part as: 给定逻辑陈述: <major>, <minor> ⇒ <concl>。判断图式与式
    major_txt = stmt_text(major[0], major[1], major[2])
    minor_txt = stmt_text(minor[0], minor[1], minor[2])
    concl_txt = stmt_text(concl[0], concl[1], concl[2])

    # Second part: fill parentheses in a displayed syllogism with one missing quantifier letter.
    # We'll decide which line to hide (major/minor/conclusion) depending on variant.
    hide_idx = variant % 3  # 0 major,1 minor,2 concl
    pats = FIGURE_FORMS[fig]
    lines = [pats[0], pats[1], f"∴{pats[2]}"]
    mood_letters = [mood[0], mood[1], mood[2]]

    def fill_line(pat: str, typ_letter: str) -> str:
        return pat.replace("()", f"({typ_letter})")

    # Build fill-in with one blank as "()"
    fill_lines = []
    for i, pat in enumerate(lines):
        core_pat = pat
        prefix = ""
        if core_pat.startswith("∴"):
            prefix = "∴"
            core_pat = core_pat[1:]
        if i == hide_idx:
            filled = core_pat  # keep ()
        else:
            filled = fill_line(core_pat, mood_letters[i])
        fill_lines.append(prefix + filled)

    # Ask also to identify figure+mood.
    # Additionally, to diversify, sometimes ask for both missing letters in two blanks (harder).
    two_blanks = (variant % 7 == 0)
    if two_blanks:
        # hide one more line different from hide_idx
        hide2 = (hide_idx + 1 + rng.randrange(2)) % 3
        fill_lines2 = []
        for i, pat in enumerate(lines):
            core_pat = pat
            prefix = ""
            if core_pat.startswith("∴"):
                prefix = "∴"
                core_pat = core_pat[1:]
            if i == hide_idx or i == hide2:
                filled = core_pat
            else:
                filled = fill_line(core_pat, mood_letters[i])
            fill_lines2.append(prefix + filled)
        fill_lines = fill_lines2
        # answer for second part becomes list of two letters in line order
        blanks = [(hide_idx, mood_letters[hide_idx]), (hide2, mood_letters[hide2])]
        blanks.sort()
        second_answer = [b[1] for b in blanks]
        second_expl = f"按该图式与式({mood})，第{blanks[0][0]+1}行应填{blanks[0][1]}，第{blanks[1][0]+1}行应填{blanks[1][1]}。"
    else:
        second_answer = mood_letters[hide_idx]
        second_expl = f"按该图式与式({mood})，第{hide_idx+1}行括号应填 {mood_letters[hide_idx]}。"

    problem = (
        "下面使用一种自定义的范畴三段论表示法（只用 S,P,M 三个项）。\n"
        "命题类型定义：\n"
        "A: ∀p1⇒p2\n"
        "E: ∀p1⇒¬p2\n"
        "I: ∃p1⇒p2\n"
        "O: ∃p1⇒¬p2\n\n"
        "问题1：给定逻辑陈述：\n"
        f"{major_txt}, {minor_txt} ⇒ {concl_txt}\n"
        "判断该论证对应的三段论「格」（Figure）与「式」（Mood），按格式 [[I/II/III/IV];[Mood]] 作答。\n\n"
        "问题2：在下面的标准三段论格式中，把括号 () 填成正确的命题类型字母（A/E/I/O）。\n"
        + "\n".join(fill_lines) + "\n"
        "按格式 [[...];[...]] 作答（第二问若有两个空，请用一个列表给出两个字母，按从上到下出现的空的顺序）。"
    )

    answer = [[fig], [mood]]
    answer2 = second_answer
    full_answer = f"{answer}===={answer2}"

    # Explanation: show mapping to figure form + mood and quick semantic check (subset/disjoint etc) for A/E/I/O.
    # Keep concise and verifiable: show major/minor/concl patterns for that figure.
    maj_pat, min_pat, con_pat = FIGURE_FORMS[fig]
    explanation = (
        f"问题1：该论证的两前提与结论分别是 {maj_pat}、{min_pat}、{con_pat} 的结构，"
        f"因此属于第 {figure_name_zh(fig)} 格；三句话的类型依次为 {mood[0]}{mood[1]}{mood[2]}，所以式为 {mood}。\n"
        f"（对应文本：{major_txt}；{minor_txt}；{concl_txt}。）\n"
        f"问题2：{second_expl}"
    )
    return problem, full_answer, explanation

def make_instance(rng: random.Random, idx: int) -> Dict[str, Any]:
    # Choose a valid pair, but also ensure distribution variety.
    fig, mood = rng.choice(VALID_PAIRS)
    variant = rng.randrange(30)
    problem, answer, explanation = problem_text_zh(fig, mood, variant, rng)
    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
        seed = int(req["seed"])
        count = int(req["count"])
    except Exception as e:
        print(f"Invalid input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if count <= 0:
        print("[]")
        return

    rng = random.Random(seed)

    out = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        item = make_instance(rng, len(out))
        key = item["problem"]
        if key in seen:
            continue
        # Basic non-empty checks
        if not item["problem"].strip() or not str(item["answer"]).strip() or not item["explanation"].strip():
            continue
        seen.add(key)
        out.append(item)

    if len(out) < count:
        print(f"Generation failed: produced {len(out)}/{count} after {attempts} attempts.", file=sys.stderr)
        # Still output what we have to be explicit? Spec: must output exactly count items.
        # We'll raise to avoid silent underfill.
        raise RuntimeError(f"Could not generate enough unique problems: {len(out)}/{count}")

    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()