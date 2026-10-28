# dyck_language_8.py

import random
from typing import List, Tuple

def _pair_maps(bracket_pairs: List[str]):
    """
    Build mapping dicts from a list like ['()','[]','{}','<>'].
    Returns: (open_to_close, close_to_open, opens_set, closes_set)
    """
    open_to_close = {}
    close_to_open = {}
    opens = set()
    closes = set()
    for p in bracket_pairs:
        if not isinstance(p, str) or len(p) != 2:
            raise ValueError("Each bracket pair must be a 2-character string like () or []")
        o, c = p[0], p[1]
        open_to_close[o] = c
        close_to_open[c] = o
        opens.add(o)
        closes.add(c)
    return open_to_close, close_to_open, opens, closes

def format_pairs(bracket_pairs: List[str]) -> str:
    """
    Human-friendly bracket pairs string without quotes, e.g.: () , [] , {} , <>
    """
    return ' , '.join(bracket_pairs)

def pick_bracket_pairs(universe: List[str], min_types: int, max_types: int) -> List[str]:
    """
    Pick a random subset of bracket pairs from universe, size in [min_types, max_types].
    Ensures returned size >= 1 and <= len(universe), and min_types <= size <= max_types.
    """
    if not universe or any((not isinstance(p, str) or len(p) != 2) for p in universe):
        raise ValueError("Universe must be a non-empty list of 2-character strings.")
    low = max(1, min_types)
    high = min(max_types, len(universe))
    if low > high:
        low = high
    k = random.randint(low, high)
    return random.sample(universe, k)

def _gen_segment(length: int, bracket_pairs: List[str], push_bias_percent: int, max_depth: int = 12) -> str:
    """
    Generate a single segment of given length with controlled push bias.
    Ensures:
      - Never underflow stack
      - Any closing matches current top
    """
    open_to_close, _, opens, _ = _pair_maps(bracket_pairs)
    s: List[str] = []
    stack: List[str] = []
    p_push = max(0.0, min(1.0, push_bias_percent / 100.0))
    for _ in range(length):
        can_pop = len(stack) > 0
        can_push = len(stack) < max_depth
        if not can_pop and can_push:
            do_push = True
        elif can_pop and not can_push:
            do_push = False
        else:
            do_push = (random.random() < p_push)
        if do_push:
            pair = random.choice(bracket_pairs)
            o = pair[0]
            s.append(o)
            stack.append(o)
        else:
            # pop: must match top
            top = stack.pop()
            s.append(open_to_close[top])
    return ''.join(s)

def generate_bracket_stream(
    seg_num: int,
    min_seg_len: int,
    max_seg_len: int,
    bracket_pairs: List[str],
    push_bias_percent: int,
    min_types_per_seg: int
) -> str:
    """
    Legacy generator for '#' only. Joins segments by '#', no trailing '#'.
    Kept for backward compatibility with older specs.
    """
    if seg_num <= 0:
        raise ValueError("seg_num must be positive")
    if min_seg_len <= 0 or max_seg_len < min_seg_len:
        raise ValueError("segment length range invalid")
    if not bracket_pairs:
        raise ValueError("bracket_pairs must be non-empty")
    if min_types_per_seg < 1:
        min_types_per_seg = 1
    max_depth = max(2, min(20, max_seg_len))
    segs: List[str] = []
    for _ in range(seg_num):
        # Repeat until type diversity requirement is met
        for _attempt in range(1000):
            L = random.randint(min_seg_len, max_seg_len)
            seg = _gen_segment(L, bracket_pairs, push_bias_percent, max_depth=max_depth)
            opens_used = set(ch for ch in seg if ch in [p[0] for p in bracket_pairs])
            if len(opens_used) >= min_types_per_seg:
                segs.append(seg)
                break
        else:
            L = random.randint(min_seg_len, max_seg_len)
            segs.append(_gen_segment(L, bracket_pairs, push_bias_percent, max_depth=max_depth))
    return '#'.join(segs)

def pick_marker_set() -> List[str]:
    """
    Randomly choose a marker subset from ['#','!','*','?'], always include '#'.
    Size is 2~4 to ensure multi-rule interplay.
    """
    base = ['#', '!', '*', '?']
    # Always include '#'
    others = ['!', '*', '?']
    k = random.randint(2, 4)  # total size
    chosen = ['#']
    pool = others[:]
    random.shuffle(pool)
    while len(chosen) < k and pool:
        chosen.append(pool.pop())
    return chosen

def format_markers(marker_types: List[str]) -> str:
    """
    Human-friendly marker set display, e.g.: # , ! , * , ?
    """
    return ' , '.join(marker_types)

def describe_rules(marker_types: List[str]) -> str:
    """
    Produce concise Chinese rule explanation, only listing rules for present marker types.
    """
    parts = []
    if '#' in marker_types:
        parts.append('井号输出最短合法补全 使用前缀C:')
    if '!' in marker_types:
        parts.append('叹号输出当前未闭合层数 使用前缀D:')
    if '*' in marker_types:
        parts.append('星号输出当前未闭合的不同开括号字符种类数 使用前缀B:')
    if '?' in marker_types:
        parts.append('问号输出若此刻立即闭合所需的下一个右括号 栈空则E:EMPTY 使用前缀E:')
    if not parts:
        return '本题仅包含井号标记 每个井号处输出最短合法补全 使用前缀C:'
    return '本题包含如下标记规则 ' + ' 且 '.join(parts)

def generate_stream_with_markers(
    seg_num: int,
    min_seg_len: int,
    max_seg_len: int,
    bracket_pairs: List[str],
    push_bias_percent: int,
    min_types_per_seg: int,
    marker_types: List[str]
) -> str:
    """
    Original mixed-marker generator: append a random marker after each segment.
    """
    if seg_num <= 0:
        raise ValueError("seg_num must be positive")
    if min_seg_len <= 0 or max_seg_len < min_seg_len:
        raise ValueError("segment length range invalid")
    if not bracket_pairs:
        raise ValueError("bracket_pairs must be non-empty")
    if not marker_types:
        raise ValueError("marker_types must be non-empty")
    if min_types_per_seg < 1:
        min_types_per_seg = 1
    max_depth = max(2, min(20, max_seg_len))
    out = []
    for _ in range(seg_num):
        for _attempt in range(1000):
            L = random.randint(min_seg_len, max_seg_len)
            seg = _gen_segment(L, bracket_pairs, push_bias_percent, max_depth=max_depth)
            opens_used = set(ch for ch in seg if ch in [p[0] for p in bracket_pairs])
            if len(opens_used) >= min_types_per_seg:
                break
        else:
            L = random.randint(min_seg_len, max_seg_len)
            seg = _gen_segment(L, bracket_pairs, push_bias_percent, max_depth=max_depth)
        out.append(seg)
        out.append(random.choice(marker_types))
    return ''.join(out)

def generate_stream_with_markers_kcover(
    seg_num: int,
    min_seg_len: int,
    max_seg_len: int,
    bracket_pairs: List[str],
    push_bias_percent: int,
    min_types_per_seg: int,
    marker_types: List[str],
    require_marker_kinds: int
) -> str:
    """
    Advanced generator: ensures at least `require_marker_kinds` distinct markers are used
    across the whole stream. One marker appended after each segment.
    """
    if seg_num <= 0:
        raise ValueError("seg_num must be positive")
    if min_seg_len <= 0 or max_seg_len < min_seg_len:
        raise ValueError("segment length range invalid")
    if not bracket_pairs:
        raise ValueError("bracket_pairs must be non-empty")
    if not marker_types:
        raise ValueError("marker_types must be non-empty")
    if require_marker_kinds < 1 or require_marker_kinds > len(marker_types):
        require_marker_kinds = min(max(1, require_marker_kinds), len(marker_types))
    if min_types_per_seg < 1:
        min_types_per_seg = 1

    max_depth = max(2, min(20, max_seg_len))
    out = []
    # Choose coverage set
    coverage = set()
    need = require_marker_kinds
    pool = marker_types[:]
    random.shuffle(pool)
    while len(coverage) < need and pool:
        coverage.add(pool.pop())

    # Pre-assign the first `len(coverage)` segments to contain all coverage markers
    assigned_markers = list(coverage)
    # Remaining segments random
    while len(assigned_markers) < seg_num:
        assigned_markers.append(random.choice(marker_types))
    random.shuffle(assigned_markers)

    for i in range(seg_num):
        for _attempt in range(1000):
            L = random.randint(min_seg_len, max_seg_len)
            seg = _gen_segment(L, bracket_pairs, push_bias_percent, max_depth=max_depth)
            opens_used = set(ch for ch in seg if ch in [p[0] for p in bracket_pairs])
            if len(opens_used) >= min_types_per_seg:
                break
        else:
            L = random.randint(min_seg_len, max_seg_len)
            seg = _gen_segment(L, bracket_pairs, push_bias_percent, max_depth=max_depth)
        out.append(seg)
        out.append(assigned_markers[i])
    return ''.join(out)

def completions_for_stream(stream: str, bracket_pairs: List[str]) -> List[str]:
    """
    Compute minimal legal completion only for '#' markers.
    Retained for backward compatibility with older single-rule puzzles.
    This function ignores other markers if present.
    """
    open_to_close, close_to_open, opens, closes = _pair_maps(bracket_pairs)
    res: List[str] = []
    stack: List[str] = []
    for ch in stream:
        if ch == '#':
            compl = ''.join(open_to_close[o] for o in reversed(stack))
            res.append(compl)
            stack = []  # reset for next segment
            continue
        if ch in opens:
            stack.append(ch)
        elif ch in closes:
            if not stack or stack[-1] != close_to_open[ch]:
                raise ValueError("Stream segment contains mismatched closing; generator should avoid this.")
            stack.pop()
        else:
            continue
    return res

def compute_outputs(stream: str, bracket_pairs: List[str], marker_types: List[str]) -> List[str]:
    """
    Unified solver for mixed markers.
    - For '#': output 'C:' + minimal completion
    - For '!': output 'D:' + current depth (nonnegative integer)
    - For '*': output 'B:' + number of distinct open-bracket TYPES currently on stack (by open char)
    - For '?': output 'E:' + next required closing char or 'E:EMPTY' if stack is empty
    After each marker, reset the stack (start new segment).
    """
    open_to_close, close_to_open, opens, closes = _pair_maps(bracket_pairs)
    marker_set = set(marker_types)
    ans: List[str] = []
    stack: List[str] = []
    for ch in stream:
        if ch in marker_set:
            if ch == '#':
                compl = ''.join(open_to_close[o] for o in reversed(stack))
                ans.append('C:' + compl)
            elif ch == '!':
                ans.append('D:' + str(len(stack)))
            elif ch == '*':
                distinct_types = len(set(stack))
                ans.append('B:' + str(distinct_types))
            elif ch == '?':
                if stack:
                    top = stack[-1]
                    ans.append('E:' + open_to_close[top])
                else:
                    ans.append('E:EMPTY')
            else:
                raise ValueError("Unsupported marker encountered: {}".format(ch))
            stack = []
            continue
        if ch in opens:
            stack.append(ch)
        elif ch in closes:
            if not stack or stack[-1] != close_to_open[ch]:
                raise ValueError("Stream segment contains mismatched closing; generator should avoid this.")
            stack.pop()
        else:
            continue
    return ans

def count_markers_in_stream(stream: str, marker_types: List[str]) -> int:
    """
    Count the total number of markers from the given marker_types present in the stream.
    """
    return sum(stream.count(m) for m in set(marker_types))

def validate_completions(stream: str, bracket_pairs: List[str], ans: List[str]) -> bool:
    """
    Backward-compat validation for '#' only. Kept for older specs.
    """
    recomputed = completions_for_stream(stream, bracket_pairs)
    seg_count = stream.count('#')
    return (recomputed == ans) and (len(ans) == seg_count)

def validate_outputs(stream: str, bracket_pairs: List[str], marker_types: List[str], ans: List[str]) -> bool:
    """
    Recompute mixed-marker outputs and check equality with provided answer list.
    Also require that answer length equals number of markers in the stream.
    """
    recomputed = compute_outputs(stream, bracket_pairs, marker_types)
    marker_count = sum(stream.count(m) for m in set(marker_types))
    return (recomputed == ans) and (len(ans) == marker_count)

def validate_outputs_strong(stream: str,
                            bracket_pairs: List[str],
                            marker_types: List[str],
                            ans: List[str],
                            expected_count: int,
                            require_marker_kinds: int) -> bool:
    """
    Strong validator:
    - Recompute outputs and check equality
    - Check that the number of answers equals expected_count (computed actual markers)
    - Check that the stream actually uses at least `require_marker_kinds` distinct markers
    - Check token prefix legality and consistency with actual marker set
    """
    recomputed = compute_outputs(stream, bracket_pairs, marker_types)
    if recomputed != ans:
        return False
    # Strict length check against actual expected count
    if len(ans) != expected_count:
        return False
    present = set([m for m in set(marker_types) if m in stream])
    if len(present) < max(1, min(require_marker_kinds, len(marker_types))):
        return False
    allowed_prefix = ('C:', 'D:', 'B:', 'E:')
    for tok in ans:
        if (not isinstance(tok, str)) or (not tok.startswith(allowed_prefix)):
            return False
        # prefix-to-marker consistency
        if tok.startswith('C:') and ('#' not in marker_types):
            return False
        if tok.startswith('D:') and ('!' not in marker_types):
            return False
        if tok.startswith('B:') and ('*' not in marker_types):
            return False
        if tok.startswith('E:') and ('?' not in marker_types):
            return False
    return True

def format_outputs_string(outputs: List[str]) -> str:
    """
    Format outputs list into a bracketed, comma-separated string without quotes.
    Example: ['C:)]', 'D:3'] -> [C:),D:3]
    """
    return '[' + ','.join(outputs) + ']'

def parse_outputs_string(s: str) -> List[str]:
    """
    Parse bracketed, comma-separated string without quotes into a list of tokens.
    Example: [C:),D:3] -> ['C:)', 'D:3']
    Raises ValueError if format is invalid.
    """
    if not isinstance(s, str):
        raise ValueError("Answer must be a string")
    t = s.strip()
    if len(t) < 2 or t[0] != '[' or t[-1] != ']':
        raise ValueError("Answer must be enclosed in square brackets")
    inner = t[1:-1]
    if inner == '':
        return []
    parts = inner.split(',')
    allowed_prefix = ('C:', 'D:', 'B:', 'E:')
    tokens = [p.strip() for p in parts]
    for tok in tokens:
        if not tok.startswith(allowed_prefix):
            raise ValueError("Invalid token prefix in answer: {}".format(tok))
    return tokens

def format_example_for_markers(marker_types: List[str]) -> str:
    """
    Build a format example consistent with the actual marker set.
    Order: '#', '!', '*', '?' if present.
    Tokens are illustrative only and follow the required syntax.
    """
    order = ['#', '!', '*', '?']
    sample = {
        '#': 'C:)',   # minimal completion example
        '!': 'D:3',   # depth example
        '*': 'B:2',   # distinct types example
        '?': 'E:)'    # next closing example
    }
    toks = [sample[m] for m in order if m in marker_types]
    if not toks:
        toks = ['C:)']
    return '[' + ','.join(toks) + ']'

def format_stream_readable(stream: str, marker_types: List[str]) -> str:
    """
    Produce a human-readable segmented view: each segment followed by its marker,
    segments separated by ' | '. This is only for display; the original stream is authoritative.
    """
    marker_set = set(marker_types)
    seg = []
    parts = []
    for ch in stream:
        if ch in marker_set:
            seg.append(ch)
            parts.append(''.join(seg))
            seg = []
        else:
            seg.append(ch)
    # In a well-formed stream, seg should be empty at end (marker after each segment)
    return ' | '.join(parts)