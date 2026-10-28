import sys, json, random
from typing import List, Tuple, Optional, Dict, Any

OPEN_TO_CLOSE = {'(': ')', '[': ']', '{': '}', '<': '>'}
CLOSE_TO_OPEN = {v: k for k, v in OPEN_TO_CLOSE.items()}
OPENERS = set(OPEN_TO_CLOSE.keys())
CLOSERS = set(CLOSE_TO_OPEN.keys())
ALL_BRACKETS = list(OPEN_TO_CLOSE.keys()) + list(CLOSE_TO_OPEN.keys())


def first_error_position(seq: str) -> int:
    """
    Return -1 if legal.
    If illegal: return 1-based index of first error;
    if no mid-stream error but stack non-empty at end: return len(seq)+1.
    """
    stack: List[str] = []
    for i, ch in enumerate(seq, start=1):
        if ch in OPENERS:
            stack.append(ch)
        elif ch in CLOSERS:
            if not stack:
                return i
            top = stack[-1]
            if OPEN_TO_CLOSE[top] != ch:
                return i
            stack.pop()
        else:
            # Not expected in this generator; treat as error
            return i
    if stack:
        return len(seq) + 1
    return -1


def is_balanced(seq: str) -> bool:
    return first_error_position(seq) == -1


def explain_check(seq: str, err_pos: int) -> str:
    """
    Provide concise, verifiable explanation.
    """
    n = len(seq)
    if err_pos == -1:
        # Provide a brief invariant and summary
        return (
            "从左到右用栈匹配四类括号 < >、( )、[ ]、{ }。\n"
            "扫描过程中每遇到左括号入栈，遇到右括号必须与栈顶左括号同类并出栈；全程未出现空栈遇右括号或类型不匹配，且末尾栈为空，因此序列合法，答案为 -1。"
        )
    if err_pos == n + 1:
        # Unclosed at end
        return (
            "从左到右用栈匹配括号，扫描到末尾时没有出现“空栈遇右括号”或“类型不匹配”的中途错误。\n"
            f"但扫描完 {n} 个字符后栈仍非空，说明存在未闭合的左括号。按题意此时错误位置记为末尾的下一个位置，即 {n+1}。"
        )

    # Mid-stream error: show local context and reason
    ch = seq[err_pos - 1]
    prefix = seq[:err_pos]
    # simulate to retrieve stack state just before error
    stack: List[str] = []
    reason = ""
    for i, c in enumerate(seq, start=1):
        if i == err_pos:
            if c in CLOSERS:
                if not stack:
                    reason = f"第 {err_pos} 位是右括号“{c}”，但此前栈为空，属于未匹配的右括号。"
                else:
                    top = stack[-1]
                    expected = OPEN_TO_CLOSE[top]
                    if expected != c:
                        reason = f"第 {err_pos} 位是右括号“{c}”，但栈顶左括号为“{top}”，期望闭合为“{expected}”，发生类型/顺序不匹配。"
                    else:
                        # Should not happen for error position, but keep safe
                        reason = f"第 {err_pos} 位与栈顶匹配（此分支理论上不会作为首个错误）。"
            elif c in OPENERS:
                # If an opener is the first error, it must be due to non-bracket char; but keep generic
                reason = f"第 {err_pos} 位字符“{c}”导致不合法。"
            else:
                reason = f"第 {err_pos} 位字符“{c}”不是有效括号字符。"
            break

        if c in OPENERS:
            stack.append(c)
        elif c in CLOSERS:
            if not stack:
                # earlier error, but then err_pos wouldn't be first
                break
            top = stack[-1]
            if OPEN_TO_CLOSE[top] != c:
                break
            stack.pop()
        else:
            break

    # show a small window around the error
    L = max(1, err_pos - 8)
    R = min(n, err_pos + 8)
    window = seq[L-1:R]
    caret = " " * (err_pos - L) + "^"
    return (
        "用栈从左到右检查括号匹配。\n"
        f"局部片段（第 {L}~{R} 位）：{window}\n"
        f"                      {caret}\n"
        f"{reason}\n"
        f"因此首个错误位置为 {err_pos}（以 1 为起始索引）。"
    )


def random_balanced_sequence(rng: random.Random, length: int) -> str:
    """
    Construct a balanced sequence of exact even length using a simple random process:
    At each step choose to open if possible, otherwise close; ensure we can finish.
    """
    if length % 2 != 0:
        raise ValueError("Balanced sequence length must be even.")
    seq: List[str] = []
    stack: List[str] = []
    opens_used = 0
    max_opens = length // 2

    for i in range(length):
        remaining = length - i
        # Must be able to close everything we open:
        # if we open now, stack grows by 1 so we need at least (len(stack)+1) closes later
        can_open = opens_used < max_opens and (remaining - 1) >= (len(stack) + 1)
        can_close = len(stack) > 0

        # Bias to open early, close later
        if can_open and (not can_close or rng.random() < 0.60):
            o = rng.choice(list(OPEN_TO_CLOSE.keys()))
            seq.append(o)
            stack.append(o)
            opens_used += 1
        else:
            # close
            top = stack.pop()
            seq.append(OPEN_TO_CLOSE[top])

    assert not stack
    return "".join(seq)


def inject_error(seq: str, rng: random.Random, mode: str) -> Tuple[str, int]:
    """
    Given a (typically balanced) sequence, inject a specific type of error and return (new_seq, error_pos).
    Modes:
      - 'mismatch': change a closing bracket to a different closing bracket at a position where it's a close.
      - 'early_close': change an opener early into a closer when stack would be empty => error there.
      - 'unclosed_end': delete one closing bracket and append a random opener (keep length) so end has unclosed.
    Ensure computed first_error_position matches intended.
    """
    n = len(seq)
    seq_list = list(seq)

    if mode == 'mismatch':
        # find a closing position that is not the first char
        close_positions = [i for i, ch in enumerate(seq_list) if ch in CLOSERS]
        rng.shuffle(close_positions)
        for idx in close_positions:
            original = seq_list[idx]
            # change to different closer
            choices = [c for c in CLOSERS if c != original]
            seq_list[idx] = rng.choice(choices)
            new_seq = "".join(seq_list)
            err = first_error_position(new_seq)
            if err == idx + 1:
                return new_seq, err
            # revert and try again
            seq_list[idx] = original
        raise RuntimeError("Failed to inject mismatch error.")

    if mode == 'early_close':
        # Force an early unmatched closing bracket at some position where prefix stack would be empty.
        # The earliest guaranteed way: set first character to a closing bracket.
        seq_list[0] = rng.choice(list(CLOSERS))
        new_seq = "".join(seq_list)
        err = first_error_position(new_seq)
        if err == 1:
            return new_seq, err
        raise RuntimeError("Failed to inject early_close error.")

    if mode == 'unclosed_end':
        # Make the sequence have no mid error but end with unclosed: easiest by turning the last char into an opener.
        # Need to avoid creating mid error: replacing last char with an opener never creates earlier mismatch.
        seq_list[-1] = rng.choice(list(OPENERS))
        new_seq = "".join(seq_list)
        err = first_error_position(new_seq)
        if err == n + 1:
            return new_seq, err
        # If not, try a different opener at end (should almost always work)
        for _ in range(10):
            seq_list[-1] = rng.choice(list(OPENERS))
            new_seq = "".join(seq_list)
            err = first_error_position(new_seq)
            if err == n + 1:
                return new_seq, err
        raise RuntimeError("Failed to inject unclosed_end error.")

    raise ValueError(f"Unknown mode: {mode}")


def make_problem_text(seq: str, length: int, style: str, lang: str = "zh") -> str:
    assert lang == "zh"
    if style == "expert":
        return (
            "你是一个括号语言专家，需要分析括号的闭合情况。\n"
            f"这是一个包含4种括号（< >、( )、[ ]、{{ }}）的序列，总长度为{length}。"
            "请找出第一个出现错误的位置（以1为起始索引）。\n"
            "错误定义为第一个破坏预期匹配规则的字符：\n"
            "1) 遇到右括号但当前没有可匹配的左括号；或\n"
            "2) 右括号与最近未闭合的左括号类型不一致（顺序/类型错误）。\n"
            "如果扫描过程中没有错误，但末尾仍存在未闭合的左括号，则错误位置认为是在序列末尾的下一个位置。\n"
            "如果序列合法，输出 -1；否则输出第一个错误的位置编号。\n\n"
            f"括号序列：{seq}"
        )
    if style == "ops":
        return (
            "请按“栈匹配括号”的规则检查以下括号串是否有效。四种括号：< >、( )、[ ]、{ }。\n"
            f"串长为{length}。返回值定义：\n"
            "- 若完全匹配且全部闭合，输出 -1；\n"
            "- 若存在首个错误字符，输出它的 1-based 位置；\n"
            "- 若无中途错误但最终还有未闭合左括号，输出 {length+1}（即末尾下一个位置）。\n\n"
            f"括号序列：{seq}"
        )
    # default
    return (
        "给定一个仅由 < > ( ) [ ] { } 组成的括号序列。按从左到右匹配规则找首个错误位置（1-based）：\n"
        "空栈遇右括号或闭合类型不匹配都算错误；若全程无错误但末尾仍有未闭合左括号，则错误位置为末尾下一位；若完全合法输出 -1。\n\n"
        f"序列：{seq}"
    )


def generate_one(rng: random.Random) -> Dict[str, Any]:
    # L3规模变化：长度在 24~44 且为偶数
    length = rng.choice([24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44])
    base = random_balanced_sequence(rng, length)

    family = rng.choices(
        population=["valid", "mismatch", "early_close", "unclosed_end"],
        weights=[0.25, 0.35, 0.15, 0.25],
        k=1
    )[0]

    if family == "valid":
        seq = base
        ans = -1
    else:
        mode = family
        seq, ans = inject_error(base, rng, mode)

    # Cross-check (independent-ish): compute again by manual simulation in this function
    ans2 = first_error_position(seq)
    if ans2 != ans:
        raise AssertionError(f"Answer mismatch: intended {ans}, computed {ans2}")

    style = rng.choice(["expert", "ops", "plain"])
    problem = make_problem_text(seq, length, style, lang="zh")
    explanation = explain_check(seq, ans)

    return {"problem": problem, "answer": ans, "explanation": explanation}


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results: List[Dict[str, Any]] = []
    seen = set()
    attempts = 0
    max_attempts = max(2000, count * 50)

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        item = generate_one(rng)
        key = item["problem"]
        if key in seen:
            continue
        # basic non-empty checks
        if not item["problem"] or item["explanation"] is None:
            continue
        seen.add(key)
        results.append(item)

    if len(results) < count:
        print(f"Failed to generate enough unique problems: {len(results)}/{count}", file=sys.stderr)
        sys.exit(1)

    json.dump(results, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()