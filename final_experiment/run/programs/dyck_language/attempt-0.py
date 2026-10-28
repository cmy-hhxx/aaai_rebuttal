import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

BRACKETS = {
    "(": ")",
    "[": "]",
    "{": "}",
    "<": ">",
}
CLOSERS = {v: k for k, v in BRACKETS.items()}
OPENERS = list(BRACKETS.keys())
CLOSER_FOR = BRACKETS

def is_balanced(s: str) -> bool:
    stack = []
    for ch in s:
        if ch in BRACKETS:
            stack.append(ch)
        elif ch in CLOSERS:
            if not stack or stack[-1] != CLOSERS[ch]:
                return False
            stack.pop()
        else:
            return False
    return len(stack) == 0

def completion_for_prefix(prefix: str) -> Optional[str]:
    """Return the minimal completion (closing-only suffix) to balance prefix, or None if prefix invalid."""
    stack = []
    for ch in prefix:
        if ch in BRACKETS:
            stack.append(ch)
        elif ch in CLOSERS:
            if not stack or stack[-1] != CLOSERS[ch]:
                return None
            stack.pop()
        else:
            return None
    # close in reverse order
    return "".join(CLOSER_FOR[ch] for ch in reversed(stack))

def generate_prefix(rng: random.Random,
                    min_len: int = 14,
                    max_len: int = 44,
                    max_depth: int = 10,
                    allow_early_closers: bool = True,
                    must_have_types: int = 3) -> str:
    """
    Generate a bracket prefix that is a valid prefix of some balanced string.
    It may include closers, but never invalidly.
    Ensure at least `must_have_types` distinct bracket types appear among openers.
    """
    target_len = rng.randint(min_len, max_len)
    stack: List[str] = []
    out: List[str] = []
    used_types = set()

    # Bias to start with an opener to avoid trivial cases
    first = rng.choice(OPENERS)
    out.append(first)
    stack.append(first)
    used_types.add(first)

    while len(out) < target_len:
        depth = len(stack)
        # Decide action: open or close (if possible)
        # Keep within max_depth; also avoid always closing too early.
        can_close = depth > 0 and allow_early_closers
        can_open = depth < max_depth

        # If nearing end, prefer leaving some opens to make completion non-empty
        remaining = target_len - len(out)
        # If remaining is small, avoid forced closures dominating: keep some opens.
        open_bias = 0.60
        if depth == 0:
            p_open = 1.0
        elif not can_open:
            p_open = 0.0
        elif not can_close:
            p_open = 1.0
        else:
            p_open = open_bias

        # Encourage introducing new types until must_have_types reached
        if len(used_types) < must_have_types and can_open:
            # Increase chance to open
            p_open = max(p_open, 0.75)

        if rng.random() < p_open:
            # open
            opener = rng.choice(OPENERS)
            out.append(opener)
            stack.append(opener)
            used_types.add(opener)
        else:
            # close top
            opener = stack.pop()
            out.append(CLOSER_FOR[opener])

    # Ensure it's not already balanced (so completion is non-empty) in most cases.
    # If balanced, append an extra opener to force a non-empty completion.
    comp = completion_for_prefix("".join(out))
    if comp is None:
        # should not happen, but guard
        return generate_prefix(rng, min_len, max_len, max_depth, allow_early_closers, must_have_types)
    if comp == "":
        opener = rng.choice(OPENERS)
        out.append(opener)
    return "".join(out)

def format_problem(prefix: str, lang: str = "zh") -> str:
    if lang == "zh":
        return (
            "补全下面的括号序列，使其成为一个“括号完全匹配”的完整序列。\n"
            "支持的括号类型：小括号 ()，中括号 []，大括号 {}，尖括号 <>。\n"
            "要求：只能在末尾追加字符（不能改动或插入），使得所有括号都正确闭合且匹配。\n\n"
            f"给定序列：\n{prefix}\n\n"
            "请直接输出补全后的完整序列（不需要额外说明）。"
        )
    # fallback
    return (
        "Complete the bracket sequence by appending characters at the end only, "
        "so that all brackets are properly matched and closed.\n\n"
        f"Sequence:\n{prefix}\n"
    )

def explanation_text(prefix: str, completion: str, lang: str = "zh") -> str:
    # Provide checkable, concrete evidence: show remaining stack (as openers) and closers to add.
    # Compute stack for explanation.
    stack = []
    for ch in prefix:
        if ch in BRACKETS:
            stack.append(ch)
        else:
            # valid by construction
            stack.pop()
    remaining_openers = "".join(stack)
    if lang == "zh":
        return (
            "从左到右扫描给定序列：遇到左括号入栈，遇到右括号则必须与栈顶左括号类型匹配并出栈。\n"
            f"扫描结束后，栈中剩余未闭合的左括号（自底到顶）为：{remaining_openers if remaining_openers else '（空）'}。\n"
            f"因此需要按“栈顶到栈底”的逆序依次补上对应右括号：{completion if completion else '（无需补全）'}。\n"
            f"最终完整序列为：{prefix + completion}"
        )
    return (
        f"Unclosed openers after scanning: {remaining_openers}. "
        f"Append closers in reverse order: {completion}. "
        f"Full: {prefix + completion}"
    )

def make_item(rng: random.Random, lang: str = "zh") -> Dict[str, Any]:
    # Try several times to meet diversity constraints and validity.
    for _ in range(200):
        prefix = generate_prefix(
            rng,
            min_len=rng.randint(10, 18),
            max_len=rng.randint(30, 60),
            max_depth=rng.randint(6, 12),
            allow_early_closers=True,
            must_have_types=rng.randint(2, 4),
        )
        comp = completion_for_prefix(prefix)
        if comp is None:
            continue
        full = prefix + comp
        if not is_balanced(full):
            continue
        # Non-trivial: prefer completion length between 1 and 18
        if len(comp) == 0 or len(comp) > 24:
            continue
        # Prefer having at least 2 bracket types overall
        types_used = set([ch for ch in prefix if ch in BRACKETS])
        if len(types_used) < 2:
            continue

        problem = format_problem(prefix, lang)
        answer = full
        explanation = explanation_text(prefix, comp, lang)
        return {"problem": problem, "answer": answer, "explanation": explanation}
    raise RuntimeError("生成失败：在给定次数内未能生成满足条件的题目。")

def main():
    data = sys.stdin.read()
    try:
        inp = json.loads(data)
        seed = int(inp["seed"])
        count = int(inp["count"])
        if count <= 0:
            raise ValueError("count 必须为正整数")
    except Exception as e:
        print(f"输入 JSON 解析/校验失败: {e}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)

    # Language: prefer user-specified; default zh
    # The execution harness doesn't pass output_language; keep zh as default.
    lang = "zh"

    items: List[Dict[str, Any]] = []
    seen_prefixes = set()
    seen_full = set()

    # bounded resampling to avoid duplicates
    attempts = 0
    max_attempts = max(2000, count * 200)
    while len(items) < count and attempts < max_attempts:
        attempts += 1
        item = make_item(rng, lang)
        # de-dup by both prefix and full string
        prefix = item["problem"].split("给定序列：\n", 1)[1].split("\n\n", 1)[0]
        full = item["answer"]
        if prefix in seen_prefixes or full in seen_full:
            continue
        seen_prefixes.add(prefix)
        seen_full.add(full)
        items.append(item)

    if len(items) < count:
        print(f"警告：在 {attempts} 次尝试后仅生成 {len(items)}/{count} 题。", file=sys.stderr)

    sys.stdout.write(json.dumps(items, ensure_ascii=False))

if __name__ == "__main__":
    main()