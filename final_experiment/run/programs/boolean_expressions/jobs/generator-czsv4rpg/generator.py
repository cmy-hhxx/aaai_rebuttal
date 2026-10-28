import sys, json, math, random, itertools, re
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional

# ---------- Utilities ----------

def eprint(*args):
    print(*args, file=sys.stderr)

def to_int_if_close(x):
    # keep integers as int; otherwise keep as float with reasonable repr
    if isinstance(x, bool):
        return x
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        if abs(x - round(x)) < 1e-12:
            return int(round(x))
        return x
    return x

def safe_eval_arith(expr: str) -> float:
    """
    Evaluate an arithmetic expression consisting of numbers, + - * / and parentheses.
    No variables. Uses Python eval with a strict whitelist.
    """
    if not re.fullmatch(r"[0-9\.\+\-\*\/\(\)\s]+", expr):
        raise ValueError(f"Illegal characters in arithmetic expression: {expr}")
    # Prevent accidental '//' etc? We'll allow but not generate.
    return eval(expr, {"__builtins__": None}, {})

def fmt_num(x):
    x = to_int_if_close(x)
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        # trim
        s = f"{x:.12g}"
        return s
    return str(x)

# ---------- Fact bank (Chinese) ----------
# We use facts with known truth values, avoiding ambiguous world knowledge.
FACTS_TRUE = [
    "1 是奇数。",
    "2 是偶数。",
    "7 大于 3。",
    "0 小于 1。",
    "9 的平方根是 3。",
    "24 能被 3 整除。",
    "质数 2 是偶数。",
    "一个三角形的内角和是 180 度。",
    "人类通常有两只眼睛。",
    "一周有 7 天。",
]
FACTS_FALSE = [
    "1 是偶数。",
    "2 是奇数。",
    "3 大于 7。",
    "1 小于 0。",
    "9 的平方根是 4。",
    "25 能被 3 整除。",
    "质数 9 是质数。",
    "一个三角形的内角和是 360 度。",
    "一周有 8 天。",
    "人类通常有三只眼睛。",
]

def pick_fact(rng: random.Random, truth: bool) -> str:
    return rng.choice(FACTS_TRUE if truth else FACTS_FALSE)

# ---------- Expression components ----------

def gen_arith_expr(rng: random.Random, depth: int = 2, avoid_zero_div=True) -> str:
    """
    Generate a random arithmetic expression as a string.
    """
    if depth <= 0:
        # choose small integer
        return str(rng.randint(-12, 12))
    choice = rng.random()
    if choice < 0.35:
        return str(rng.randint(-20, 20))
    elif choice < 0.60:
        # binary op
        op = rng.choice(["+", "-", "*"])
        a = gen_arith_expr(rng, depth - 1, avoid_zero_div)
        b = gen_arith_expr(rng, depth - 1, avoid_zero_div)
        return f"({a} {op} {b})"
    else:
        # division, ensure nonzero denominator
        a = gen_arith_expr(rng, depth - 1, avoid_zero_div)
        b = gen_arith_expr(rng, depth - 1, avoid_zero_div)
        # tweak b if evaluates to 0
        if avoid_zero_div:
            tries = 0
            while tries < 10:
                try:
                    vb = safe_eval_arith(b)
                except Exception:
                    vb = 0
                if abs(vb) > 1e-12:
                    break
                b = gen_arith_expr(rng, depth - 1, avoid_zero_div)
                tries += 1
            # as a last resort
            try:
                vb = safe_eval_arith(b)
            except Exception:
                vb = 0
            if abs(vb) <= 1e-12:
                b = "1"
        return f"({a} / {b})"

def gen_cmp(rng: random.Random) -> Tuple[str, bool, str]:
    """
    Generate a comparison phrase in Chinese and its boolean value.
    Returns: (text, value, evidence_text)
    """
    # equality or inequality of arithmetic expressions
    a = gen_arith_expr(rng, depth=rng.randint(1, 3))
    b = gen_arith_expr(rng, depth=rng.randint(1, 3))
    va = safe_eval_arith(a)
    vb = safe_eval_arith(b)

    # Decide whether to force True/False sometimes by constructing b from a
    mode = rng.random()
    if mode < 0.35:
        # make equality true: b = a (possibly wrapped)
        b = f"({a} + 0)"
        vb = safe_eval_arith(b)
    elif mode < 0.55:
        # make inequality true: b = a + k where k != 0
        k = rng.choice([i for i in range(-5, 6) if i != 0])
        b = f"({a} + ({k}))"
        vb = safe_eval_arith(b)
    # else keep random

    kind = rng.choice(["等于", "不等于", "大于", "小于", "大于等于", "小于等于"])
    text = ""
    val = False

    # compute truth
    if kind == "等于":
        val = abs(va - vb) < 1e-12
    elif kind == "不等于":
        val = abs(va - vb) >= 1e-12
    elif kind == "大于":
        val = va > vb + 1e-12
    elif kind == "小于":
        val = va < vb - 1e-12
    elif kind == "大于等于":
        val = va > vb - 1e-12
    elif kind == "小于等于":
        val = va < vb + 1e-12

    # render
    text = f"({a}) {kind} ({b})"
    # evidence numeric substitution for explanation
    evidence = f"{a} = {fmt_num(va)}，{b} = {fmt_num(vb)}，因此“{text}”为{'真' if val else '假'}。"
    return text, val, evidence

def maybe_double_not(rng: random.Random, inner_text: str, inner_val: bool) -> Tuple[str, bool]:
    # sometimes wrap with not not
    r = rng.random()
    if r < 0.35:
        return f"not ({inner_text})", (not inner_val)
    elif r < 0.55:
        return f"not not ({inner_text})", inner_val
    else:
        return inner_text, inner_val

def gen_bool_atom(rng: random.Random) -> Tuple[str, bool, str]:
    """
    Produce a boolean atom: True/False literal, a fact, or an arithmetic comparison.
    Returns: (text, value, evidence)
    """
    t = rng.random()
    if t < 0.20:
        v = rng.choice([True, False])
        return ("True" if v else "False"), v, f"该原子为布尔常量 {v}。"
    elif t < 0.55:
        # fact
        v = rng.choice([True, False])
        fact = pick_fact(rng, v)
        return fact, v, f"该陈述“{fact}”为{'真' if v else '假'}。"
    else:
        cmp_text, cmp_val, evidence = gen_cmp(rng)
        return cmp_text, cmp_val, evidence

def combine(rng: random.Random, a: Tuple[str, bool, str], b: Tuple[str, bool, str]) -> Tuple[str, bool, List[str]]:
    """
    Combine two boolean parts with and/or.
    Returns: (text, value, evidence_lines)
    """
    op = rng.choice(["and", "or"])
    ta, va, ea = a
    tb, vb, eb = b
    if op == "and":
        v = va and vb
    else:
        v = va or vb
    text = f"({ta}) {op} ({tb})"
    evid = [ea, eb, f"使用运算 {op}：结果为 {'真' if v else '假'}。"]
    # optionally wrap with not / not not
    if rng.random() < 0.45:
        text2, v2 = maybe_double_not(rng, text, v)
        if text2 != text:
            evid.append(f"外层取反处理后：表达式“{text2}”为 {'真' if v2 else '假'}。")
        return text2, v2, evid
    return text, v, evid

def gen_expression(rng: random.Random, complexity: int) -> Tuple[str, bool, List[str]]:
    """
    Generate a boolean expression with a given complexity (number of atoms combined).
    """
    atom = gen_bool_atom(rng)
    text, val, ev = atom[0], atom[1], [atom[2]]
    # maybe wrap atom
    if rng.random() < 0.35:
        text2, val2 = maybe_double_not(rng, text, val)
        if text2 != text:
            ev.append(f"对原子加取反/双重取反：表达式“{text2}”为 {'真' if val2 else '假'}。")
        text, val = text2, val2

    parts = (text, val, "\n".join(ev))
    # combine iteratively
    evid_lines = ev[:]
    cur = (text, val, "\n".join(ev))
    for _ in range(complexity - 1):
        nxt = gen_bool_atom(rng)
        comb_text, comb_val, comb_evid = combine(rng, (cur[0], cur[1], cur[2]), nxt)
        cur = (comb_text, comb_val, "\n".join([*evid_lines, *comb_evid]))
        evid_lines = [*evid_lines, *comb_evid]
    return cur[0], cur[1], evid_lines

# ---------- Problem generator ----------

def make_problem(rng: random.Random, idx: int) -> Dict[str, Any]:
    # decide option count
    opt_count = rng.choice([4, 5, 6])
    labels = [chr(ord('A') + i) for i in range(opt_count)]

    # ensure at least one true and one false for interest
    # generate expressions, then if all same truth, flip one with "not (...)"
    exprs = []
    truths = []
    evid_map = {}
    for lab in labels:
        complexity = rng.randint(1, 3)  # number of combinations
        text, val, evid_lines = gen_expression(rng, complexity)
        exprs.append((lab, text))
        truths.append(val)
        evid_map[lab] = (val, evid_lines)

    if all(truths) or (not any(truths)):
        # flip one deterministically using rng
        k = rng.randrange(opt_count)
        lab, text = exprs[k]
        val, evid_lines = evid_map[lab]
        new_text = f"not ({text})"
        new_val = (not val)
        exprs[k] = (lab, new_text)
        evid_map[lab] = (new_val, evid_lines + [f"为保证题目有真有假，将该项外层加 not：结果变为 {'真' if new_val else '假'}。"])

    true_labels = [lab for lab in labels if evid_map[lab][0] is True]
    answer_str = ",".join(true_labels) if true_labels else "无"

    # Render problem (Chinese)
    lines = []
    lines.append("请评估以下布尔表达式，选择其中为真（True）的选项：")
    lines.append("")
    for lab, text in exprs:
        lines.append(f"{lab}. {text}")
    lines.append("")
    lines.append("哪些选项的表达式值为真？请列出所有为真的选项标识，用逗号分隔；如果都为假，请回答“无”。")

    problem = "\n".join(lines)

    # Explanation: provide brief per-option evaluation summary with key evidence.
    expl = []
    expl.append("逐项判断：")
    for lab, text in exprs:
        val, evid_lines = evid_map[lab]
        # pick 2-4 evidence lines to keep concise but checkable
        chosen = []
        # include any numeric evidence lines if exist
        for s in evid_lines:
            if "因此" in s or "布尔常量" in s or "使用运算" in s or "外层取反处理后" in s:
                chosen.append(s)
        # fallback
        if not chosen:
            chosen = evid_lines[:]
        chosen = chosen[:4]
        expl.append(f"- {lab}: {text} 为{'真' if val else '假'}。")
        for s in chosen[:3]:
            expl.append(f"  - {s}")

    expl.append(f"因此为真的选项是：{answer_str}。")

    return {
        "problem": problem,
        "answer": answer_str,
        "explanation": "\n".join(expl)
    }

def canonical_signature(item: Dict[str, Any]) -> str:
    # Normalize by stripping spaces to avoid trivial duplicates
    p = re.sub(r"\s+", " ", item["problem"]).strip()
    return p

def main():
    raw = sys.stdin.read()
    try:
        inp = json.loads(raw)
    except Exception as e:
        eprint("Invalid JSON input:", e)
        sys.exit(1)

    seed = int(inp.get("seed", 0))
    count = int(inp.get("count", inp.get("target_count", 20)))
    if count <= 0:
        eprint("count must be positive")
        sys.exit(1)

    rng = random.Random(seed)

    out = []
    seen = set()
    max_tries = count * 50
    tries = 0
    while len(out) < count and tries < max_tries:
        tries += 1
        item = make_problem(rng, len(out))
        sig = canonical_signature(item)
        if sig in seen:
            continue
        # basic sanity checks
        if not item["problem"].strip() or item["answer"] is None or item["explanation"] is None:
            continue
        seen.add(sig)
        out.append(item)

    if len(out) < count:
        eprint(f"Generation failed: produced {len(out)}/{count} after {tries} tries.")
        sys.exit(2)

    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=None))

if __name__ == "__main__":
    main()