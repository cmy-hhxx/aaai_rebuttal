# dyck_language_reasoning_errors_6.py
import random
from typing import List, Tuple, Dict, Any

# ----------------------------
# Basic random helper operators
# ----------------------------
def rint(a: int, b: int) -> int:
    """Random integer in [a, b]."""
    return random.randint(a, b)

def min2(a: int, b: int) -> int:
    """Return min(a, b) without using Python's min in YAML."""
    return a if a < b else b

def rbool() -> bool:
    """Random boolean."""
    return random.choice([True, False])

# -----------------------------------
# Rule config generation
# -----------------------------------
_BRACKET_SETS = {
    '[]': ['[', ']'],
    '()': ['(', ')']
}

def _choose_count_types() -> List[str]:
    """Randomly choose count bracket types: [], (), or both."""
    mode = random.choice(['[]', '()', 'both'])
    if mode == '[]':
        return _BRACKET_SETS['[]'][:]
    elif mode == '()':
        return _BRACKET_SETS['()'][:]
    else:
        return _BRACKET_SETS['[]'][:] + _BRACKET_SETS['()'][:]

def _choose_ignore_types(count_types: List[str]) -> List[str]:
    """
    Choose a non-empty subset of count_types to be 'forbidden inside code'.
    """
    candidates = count_types[:]
    random.shuffle(candidates)
    k = rint(1, len(count_types))
    return sorted(candidates[:k])

def _explicit_tokens_text(tokens: List[str]) -> str:
    """Render tokens like ['(', ')'] or ['[', ']'] into a human-readable list."""
    order = []
    if '[' in tokens or ']' in tokens:
        order.extend([t for t in ['[', ']'] if t in tokens])
    if '(' in tokens or ')' in tokens:
        order.extend([t for t in ['(', ')'] if t in tokens])
    if not order:
        return '（无）'
    return '、'.join(f"'{c}'" for c in order)

def make_rule_config() -> Dict[str, Any]:
    """
    Make a randomized rule configuration and its human-readable text.
    """
    count_types = _choose_count_types()
    ignore_types = _choose_ignore_types(count_types)
    delim_len = random.choice([1, 3])

    counted_set_text = _explicit_tokens_text(count_types)
    ignore_set_text = _explicit_tokens_text(ignore_types)

    # Clear, unambiguous, covers both N=1 and N=3:
    rule_text = (
        f"计数集合：{counted_set_text} 与反引号 '`'；"
        f"代码片段内禁用集合：{ignore_set_text}（在代码片段内出现即为违规，但违规字符仍计入步号）；"
        f"本题文本包含 1 或 2 个代码片段；开/闭标记均由连续 {delim_len} 个反引号组成（N 取值为 1 或 3，题目已固定为 {delim_len}）；"
        f"“连续”定义：反引号必须在原文本中相邻出现；一旦其间出现任何字符（包括不计入步骤的字符），即视为不连续；"
        f"连续 m 个反引号将按每 {delim_len} 个为一组依次切换代码状态，剩余不足 {delim_len} 个不切换但仍计入步骤；"
        f"示例：若 N=3，连续出现 7 个反引号会依次切换两次（第1~3个、4~6个），第7个不切换但仍计入步骤；若 N=1，连续出现 7 个反引号会依次切换 7 次；"
        f"括号按字符逐一计数，不考虑配对关系；"
        f"步号计数口径：仅对上述计数集合中的括号与反引号按出现顺序从1开始编号；若不存在任何违规，请输出 -1；其他字符均忽略"
    )

    return {
        'count_types': count_types[:],
        'ignore_types': ignore_types[:],
        'delim_len': delim_len,
        'text': rule_text
    }

# -----------------------------------
# Core logic: token handling and check
# -----------------------------------
def _is_counted(ch: str, cfg: Dict[str, Any]) -> bool:
    """Return True iff ch is a counted token under cfg."""
    if ch == '`':
        return True
    return ch in cfg['count_types']

def tokens_positions(text: str, cfg: Dict[str, Any]) -> List[Tuple[int, str]]:
    """
    Return a list of (pos, ch) for counted tokens under the given rule config.
    pos is 1-based index among counted tokens only.
    """
    toks = []
    count = 0
    for ch in text:
        if _is_counted(ch, cfg):
            count += 1
            toks.append((count, ch))
    return toks

def first_error_step_general(text: str, cfg: Dict[str, Any]) -> int:
    """
    Compute the first error step index under the rule:
    - Count only tokens in cfg['count_types'] and '`'.
    - Code span toggles when encountering cfg['delim_len'] consecutive backticks (adjacent in raw text);
      runs longer than N toggle multiple times, in blocks of N; leftover < N backticks do not toggle.
    - If a bracket from cfg['ignore_types'] appears while in_code is True, that step is the first violation.
    Return the first such step index; if none, return -1.
    """
    in_code = False
    step_idx = 0
    bt_run = 0  # length of current run of consecutive backticks among raw text (adjacency-based)

    def _toggle_if_block():
        nonlocal in_code, bt_run
        while bt_run >= cfg['delim_len']:
            in_code = not in_code
            bt_run -= cfg['delim_len']

    for ch in text:
        if not _is_counted(ch, cfg):
            # Non-counted and not backtick -> reset run (breaks continuity)
            if ch != '`':
                bt_run = 0
            continue

        step_idx += 1

        if ch == '`':
            bt_run += 1
            _toggle_if_block()
            continue

        # Any counted non-backtick resets run (breaks continuity)
        bt_run = 0

        if in_code and ch in cfg['ignore_types']:
            return step_idx

    return -1

def enumerate_violations(text: str, cfg: Dict[str, Any]) -> List[int]:
    """
    Enumerate all step indices where a counted bracket from ignore_types appears while in code.
    """
    in_code = False
    step_idx = 0
    bt_run = 0
    res: List[int] = []

    def _toggle_if_block():
        nonlocal in_code, bt_run
        while bt_run >= cfg['delim_len']:
            in_code = not in_code
            bt_run -= cfg['delim_len']

    for ch in text:
        if not _is_counted(ch, cfg):
            if ch != '`':
                bt_run = 0
            continue

        step_idx += 1

        if ch == '`':
            bt_run += 1
            _toggle_if_block()
            continue

        bt_run = 0

        if in_code and ch in cfg['ignore_types']:
            res.append(step_idx)
    return res

def count_code_spans(text: str, cfg: Dict[str, Any]) -> int:
    """
    Count the number of code spans (contiguous regions with in_code=True) based on adjacency and N-group toggling.
    """
    in_code = False
    bt_run = 0
    spans = 0

    def _toggle_if_block_count_spans():
        nonlocal in_code, bt_run, spans
        while bt_run >= cfg['delim_len']:
            in_code = not in_code
            if in_code:
                spans += 1
            bt_run -= cfg['delim_len']

    for ch in text:
        if not _is_counted(ch, cfg):
            if ch != '`':
                bt_run = 0
            continue

        if ch == '`':
            bt_run += 1
            _toggle_if_block_count_spans()
        else:
            bt_run = 0

    return spans

def verify_unique_answer(text: str, cfg: Dict[str, Any], ans: int) -> bool:
    """
    Verify:
    - Code spans must be 1 or 2 (as stated in the problem environment).
    - If there are violations, ans must equal the first violation (unique by definition).
    - If there is no violation, ans must be -1.
    """
    spans = count_code_spans(text, cfg)
    if spans not in (1, 2):
        return False

    viols = enumerate_violations(text, cfg)
    if not viols:
        return ans == -1
    return viols[0] == ans

# ----------------------------
# Instance generation utilities
# ----------------------------
def _rand_filler() -> str:
    """
    Generate a short filler string using characters that are not counted tokens.
    Avoid: [],(),` (and no consecutive backticks that could form delimiters)
    """
    pool = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-:;,.!@#%^&*=+/?'
    length = random.randint(0, 3)
    return ''.join(random.choice(pool) for _ in range(length))

def _assemble_text_from_tokens(tokens: List[str]) -> str:
    """Interleave tokens with random filler to form a natural-looking string."""
    parts = []
    parts.append(_rand_filler())
    for t in tokens:
        parts.append(t)
        parts.append(_rand_filler())
    return ''.join(parts)

def _allowed_types(count_types: List[str], ignore_types: List[str]) -> List[str]:
    return [t for t in count_types if t not in ignore_types]

def _bt_group(k: int) -> str:
    """Return a single string containing k consecutive backticks."""
    return '`' * max(0, k)

def _delim(delim_len: int) -> str:
    """Return a string representing the delimiter sequence with adjacency preserved."""
    return _bt_group(delim_len)

def generate_markdown_instance_general(
    pre_plain_len: int,
    code_pre_len: int,
    code_post_len: int,
    post_plain_len: int,
    close_code: bool,
    cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Original single-span generator kept for backward compatibility.
    Ensures delimiter adjacency by inserting a single group token (e.g., '```').
    """
    count_types = cfg['count_types']
    ignore_types = cfg['ignore_types']
    allowed = _allowed_types(count_types, ignore_types)
    delim_len = cfg['delim_len']

    tokens: List[str] = []

    for _ in range(pre_plain_len):
        tokens.append(random.choice(count_types))

    tokens.append(_delim(delim_len))

    if len(allowed) > 0:
        local_pre = min(code_pre_len, 3 + rint(0, 3))
        for _ in range(local_pre):
            tokens.append(random.choice(allowed))

    tokens.append(random.choice(ignore_types))

    local_post = code_post_len
    for _ in range(local_post):
        pick_pool = ignore_types + allowed
        tokens.append(random.choice(pick_pool))

    if close_code:
        tokens.append(_delim(delim_len))

    for _ in range(post_plain_len):
        tokens.append(random.choice(count_types))

    # Add short backtick runs that cannot toggle only when delim_len >= 2
    if delim_len >= 2 and random.random() < 0.3:
        k = rint(1, delim_len - 1)
        tokens.append(_bt_group(k))

    text = _assemble_text_from_tokens(tokens)
    ans = first_error_step_general(text, cfg)

    if ans == -1:
        tokens_fallback = []
        tokens_fallback.extend([random.choice(count_types) for _ in range(max(0, pre_plain_len // 2))])
        tokens_fallback.append(_delim(delim_len))
        tokens_fallback.append(random.choice(ignore_types))
        if close_code:
            tokens_fallback.append(_delim(delim_len))
        text = _assemble_text_from_tokens(tokens_fallback)
        ans = first_error_step_general(text, cfg)

    return {'text': text, 'first_error_step': ans}

def generate_markdown_instance_advanced(
    pre_plain_len: int,
    code1_pre_len: int,
    code1_post_len: int,
    between_plain_len: int,
    code2_pre_len: int,
    code2_post_len: int,
    post_plain_len: int,
    close_code1: bool,
    has_second_span: bool,
    close_code2: bool,
    violation_span: int,
    cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Advanced generator with up to two code spans.
    - violation_span in {1, 2}: which code span will contain the first violating bracket.
    - If has_second_span is False, only first span is generated and violation_span is forced to 1.
    - Ensures no ignored brackets appear before the intended first violation (including between-span area).
    - Ensures delimiter adjacency by emitting group tokens (e.g., '```').
    - Guarantees total code spans in {1,2}.
    """
    count_types = cfg['count_types']
    ignore_types = cfg['ignore_types']
    allowed = _allowed_types(count_types, ignore_types)
    delim_len = cfg['delim_len']

    if not has_second_span:
        violation_span = 1

    # If we intend two spans, force the first one to close to ensure exactly two spans
    close1 = True if has_second_span else close_code1

    tokens: List[str] = []

    # Pre-plain
    for _ in range(pre_plain_len):
        tokens.append(random.choice(count_types))

    # Span 1
    tokens.append(_delim(delim_len))
    if allowed:
        local_pre1 = min(code1_pre_len, 4 + rint(0, 3))
        for _ in range(local_pre1):
            tokens.append(random.choice(allowed))

    if violation_span == 1:
        tokens.append(random.choice(ignore_types))  # first violation occurs here
        for _ in range(code1_post_len):
            pick_pool = ignore_types + allowed
            tokens.append(random.choice(pick_pool))
    else:
        # No violating bracket in span 1
        for _ in range(code1_post_len):
            if allowed:
                tokens.append(random.choice(allowed))

    if close1:
        tokens.append(_delim(delim_len))

    # Between-plain (outside code iff close1 is True; otherwise still in code)
    if close1:
        for _ in range(between_plain_len):
            tokens.append(random.choice(count_types))
    else:
        # Still in code: to avoid premature violation when target is span 2, only place allowed tokens
        for _ in range(between_plain_len):
            if allowed:
                tokens.append(random.choice(allowed))

    # Optional Span 2
    if has_second_span:
        tokens.append(_delim(delim_len))
        if allowed:
            local_pre2 = min(code2_pre_len, 4 + rint(0, 3))
            for _ in range(local_pre2):
                tokens.append(random.choice(allowed))

        if violation_span == 2:
            tokens.append(random.choice(ignore_types))  # first violation occurs here
            for _ in range(code2_post_len):
                pick_pool = ignore_types + allowed
                tokens.append(random.choice(pick_pool))
        else:
            for _ in range(code2_post_len):
                if allowed:
                    tokens.append(random.choice(allowed))

        if close_code2:
            tokens.append(_delim(delim_len))

    # Post-plain
    for _ in range(post_plain_len):
        tokens.append(random.choice(count_types))

    # Add stray short backtick runs (do not toggle) only when delim_len >= 2
    for _ in range(rint(0, 2)):
        if delim_len >= 2 and random.random() < 0.5:
            k = rint(1, delim_len - 1)
            tokens.append(_bt_group(k))

    text = _assemble_text_from_tokens(tokens)
    ans = first_error_step_general(text, cfg)

    # Safety guard: ensure earliest violation is returned; allow -1 if truly none
    viols = enumerate_violations(text, cfg)
    if not viols:
        # Force minimal fallback: open span + one violating bracket
        tokens_fallback = []
        tokens_fallback.extend([random.choice(count_types) for _ in range(pre_plain_len // 2 if pre_plain_len > 0 else 0)])
        tokens_fallback.append(_delim(delim_len))
        tokens_fallback.append(random.choice(ignore_types))
        if close1:
            tokens_fallback.append(_delim(delim_len))
        text = _assemble_text_from_tokens(tokens_fallback)
        ans = first_error_step_general(text, cfg)
    else:
        if ans != viols[0]:
            ans = viols[0]

    # Final guarantee: spans in {1,2}; if not, rebuild minimal valid text
    spans = count_code_spans(text, cfg)
    if spans not in (1, 2):
        tokens_fallback = []
        tokens_fallback.append(_delim(delim_len))
        tokens_fallback.append(random.choice(ignore_types))
        tokens_fallback.append(_delim(delim_len))
        text = _assemble_text_from_tokens(tokens_fallback)
        ans = first_error_step_general(text, cfg)

    return {'text': text, 'first_error_step': ans}