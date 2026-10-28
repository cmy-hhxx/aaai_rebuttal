# dyck_language_6.py
import random

PAIR_OPEN_TO_CLOSE = {
    '(': ')',
    '[': ']',
    '{': '}',
    '<': '>',
}
PAIR_CLOSE_TO_OPEN = {v: k for k, v in PAIR_OPEN_TO_CLOSE.items()}
OPEN_SET = set(PAIR_OPEN_TO_CLOSE.keys())
CLOSE_SET = set(PAIR_CLOSE_TO_OPEN.keys())


def _unmatched_stack(prefix: str):
    """
    Return the unmatched opening bracket stack after scanning prefix.
    Raises ValueError if prefix is not a valid bracket prefix over (), [], {}, <>.
    """
    stack = []
    for ch in prefix:
        if ch in OPEN_SET:
            stack.append(ch)
        elif ch in CLOSE_SET:
            if not stack or PAIR_OPEN_TO_CLOSE[stack[-1]] != ch:
                raise ValueError('Invalid prefix sequence: mismatch or premature closing.')
            stack.pop()
        else:
            raise ValueError('Invalid character encountered: {}'.format(ch))
    return stack


def unmatched_count(prefix: str) -> int:
    """Number of unmatched opening brackets after scanning the prefix."""
    return len(_unmatched_stack(prefix))


def dyck_min_completion(prefix: str) -> str:
    """
    Compute the unique completion under closure-only completion:
    Only append the necessary closing brackets to complete the sequence.
    """
    stack = _unmatched_stack(prefix)
    suffix = ''.join(PAIR_OPEN_TO_CLOSE[o] for o in reversed(stack))
    return prefix + suffix


def is_string(x) -> bool:
    """Check if x is a string value."""
    return isinstance(x, str)


def sum_list(lst) -> int:
    """Sum a list of integers without relying on YAML to call Python built-ins."""
    s = 0
    for v in lst:
        s += int(v)
    return s


def get_all_pairs():
    """Return list of all bracket pairs as tuples (open, close)."""
    return [('(', ')'), ('[', ']'), ('{', '}'), ('<', '>')]


def choose_pairs(type_num: int):
    """
    Randomly choose 'type_num' pairs from the four bracket pairs.
    Returns a list of tuples [(open, close), ...].
    """
    all_pairs = get_all_pairs()
    return random.sample(all_pairs, type_num)


def make_charset_order(chosen_pairs):
    """
    Make a random comparison order over characters that appear
    in the chosen pairs. The order is a random permutation of opens and closes
    of the chosen pairs, returned as a list of characters.
    """
    chars = []
    for op, cl in chosen_pairs:
        chars.append(op)
        chars.append(cl)
    random.shuffle(chars)
    return chars


def _gen_balanced_sequence(chosen_pairs, total_len: int) -> str:
    """
    Generate a balanced Dyck sequence of exact length 'total_len' (even),
    using only the chosen_pairs. Ensures never going invalid.
    """
    assert total_len % 2 == 0 and total_len >= 2
    opens_needed = total_len // 2
    closes_needed = total_len // 2
    stack = []
    seq = []

    while opens_needed > 0 or closes_needed > 0:
        if opens_needed == 0:
            top = stack.pop()
            seq.append(PAIR_OPEN_TO_CLOSE[top])
            closes_needed -= 1
            continue

        if closes_needed == 0:
            op, _ = random.choice(chosen_pairs)
            stack.append(op)
            seq.append(op)
            opens_needed -= 1
            continue

        # choose randomly to open or close (prefer open when stack empty)
        if not stack:
            op, _ = random.choice(chosen_pairs)
            stack.append(op)
            seq.append(op)
            opens_needed -= 1
        else:
            if random.random() < 0.55:
                op, _ = random.choice(chosen_pairs)
                stack.append(op)
                seq.append(op)
                opens_needed -= 1
            else:
                top = stack.pop()
                seq.append(PAIR_OPEN_TO_CLOSE[top])
                closes_needed -= 1

    assert not stack
    return ''.join(seq)


def scan_stats(prefix: str):
    """
    Scan prefix and return:
    - max_depth: maximum stack depth observed
    - used_open_types: set of opening bracket types seen anywhere
    - unmatched_open_types: set of opening bracket types remaining on stack
    - has_early_close: whether there exists at least one closing before the end (i.e., not all opens first)
    """
    stack = []
    max_depth = 0
    used_open_types = set()
    has_early_close = False
    for i, ch in enumerate(prefix):
        if ch in OPEN_SET:
            used_open_types.add(ch)
            stack.append(ch)
            if len(stack) > max_depth:
                max_depth = len(stack)
        elif ch in CLOSE_SET:
            if not stack or PAIR_OPEN_TO_CLOSE[stack[-1]] != ch:
                raise ValueError('Invalid prefix sequence during stats scan.')
            stack.pop()
            # if a close occurs before the very end or when any open has occurred before, we mark early close
            if i < len(prefix) - 1:
                has_early_close = True
        else:
            raise ValueError('Invalid character encountered during stats scan.')
    unmatched_open_types = set(stack)
    return {
        'max_depth': max_depth,
        'used_open_types': used_open_types,
        'unmatched_open_types': unmatched_open_types,
        'has_early_close': has_early_close,
    }


def gen_valid_prefix(chosen_pairs, min_len: int, max_len: int, target_unmatched: int) -> str:
    """
    Generate a valid prefix that:
    - is a proper prefix of some balanced sequence,
    - length in [min_len, max_len],
    - has exactly 'target_unmatched' unmatched opens,
    - and satisfies complexity constraints:
      * uses at least two different opening types overall,
      * has max stack depth >= 2,
      * has at least one early closing action (nontrivial structure).
    Strategy:
    - Generate a balanced sequence with length L where L - target_unmatched in [min_len, max_len].
    - Cut off the last 'target_unmatched' closing brackets, leaving that many unmatched opens.
    - Check complexity constraints; if fail, resample.
    """
    if min_len < 1:
        min_len = 1
    if max_len < min_len:
        max_len = min_len

    candidates = []
    for L in range(min_len + target_unmatched, max_len + target_unmatched + 1):
        if L % 2 == 0:
            candidates.append(L)
    if not candidates:
        base = min_len + target_unmatched
        if base % 2 == 1:
            base += 1
        candidates = [base]

    # attempt multiple times to satisfy complexity constraints
    for _try in range(300):
        L = random.choice(candidates)
        full = _gen_balanced_sequence(chosen_pairs, L)
        if target_unmatched > 0:
            prefix = full[:-target_unmatched]
        else:
            prefix = full
        # Validate prefix and constraints
        _ = _unmatched_stack(prefix)
        if len(_) != target_unmatched:
            continue
        stats = scan_stats(prefix)
        # must use at least two opening types overall (seen anywhere, not just unmatched tail)
        if len(stats['used_open_types']) < 2:
            continue
        # minimum nesting depth
        if stats['max_depth'] < 2:
            continue
        # ensure some early closing happened to avoid trivial all-opens-then-all-closes prefix
        if not stats['has_early_close'] and target_unmatched > 0:
            continue
        return prefix

    # Fallback: relax early close but keep correctness to avoid dead loops
    for _try in range(300):
        L = random.choice(candidates)
        full = _gen_balanced_sequence(chosen_pairs, L)
        if target_unmatched > 0:
            prefix = full[:-target_unmatched]
        else:
            prefix = full
        _ = _unmatched_stack(prefix)
        if len(_) != target_unmatched:
            continue
        stats = scan_stats(prefix)
        if len(stats['used_open_types']) < 2:
            continue
        if stats['max_depth'] < 2:
            continue
        return prefix

    # As a last resort, return any valid prefix (extremely rare)
    L = random.choice(candidates)
    full = _gen_balanced_sequence(chosen_pairs, L)
    prefix = full[:-target_unmatched] if target_unmatched > 0 else full
    _ = _unmatched_stack(prefix)
    return prefix


def completed_length(prefix: str) -> int:
    """Length of the completed sequence after minimal closure-only completion."""
    comp = dyck_min_completion(prefix)
    return len(comp)


def suffix_counts_list(prefix: str, charset_order):
    """
    Backward compatibility helper:
    Return counts of newly appended right brackets aligned to right brackets
    in 'charset_order'.
    """
    return suffix_counts_list_mode(prefix, None, charset_order, 'closers')


def _suffix_counts_by_closers_order(suffix: str, charset_order):
    cnt = {}
    for ch in suffix:
        if ch in CLOSE_SET:
            cnt[ch] = cnt.get(ch, 0) + 1
    closers_in_order = [ch for ch in charset_order if ch in CLOSE_SET]
    res = []
    for c in closers_in_order:
        res.append(cnt.get(c, 0))
    return res


def _suffix_counts_by_opens_order(suffix: str, charset_order):
    """
    Order by the sequence of left brackets in charset_order.
    Count the matching closers for each open in that order.
    """
    cnt = {}
    for ch in suffix:
        if ch in CLOSE_SET:
            cnt[ch] = cnt.get(ch, 0) + 1
    opens_in_order = [ch for ch in charset_order if ch in OPEN_SET]
    res = []
    for o in opens_in_order:
        c = PAIR_OPEN_TO_CLOSE[o]
        res.append(cnt.get(c, 0))
    return res


def _suffix_counts_by_pairs_open_first(suffix: str, charset_order, chosen_pairs):
    """
    Deduplicate by the first-appearance order of left brackets in charset_order
    that are present in chosen_pairs. Count the corresponding closers.
    """
    cnt = {}
    for ch in suffix:
        if ch in CLOSE_SET:
            cnt[ch] = cnt.get(ch, 0) + 1
    chosen_opens = set(op for op, _ in (chosen_pairs or [])) if chosen_pairs else OPEN_SET
    order_unique_opens = []
    seen = set()
    for ch in charset_order:
        if ch in OPEN_SET and ch in chosen_opens and ch not in seen:
            seen.add(ch)
            order_unique_opens.append(ch)
    res = []
    for o in order_unique_opens:
        c = PAIR_OPEN_TO_CLOSE[o]
        res.append(cnt.get(c, 0))
    return res


def suffix_counts_list_mode(prefix: str, chosen_pairs, charset_order, mode: str):
    """
    Return a list of counts of newly appended right brackets aligned per 'mode':
    - 'closers': by right brackets in charset_order
    - 'opens': by left brackets in charset_order, mapping to their closers
    - 'pairs_open': unique left brackets by first appearance in charset_order, mapping to their closers
    """
    comp = dyck_min_completion(prefix)
    suffix = comp[len(prefix):]
    if mode == 'closers':
        return _suffix_counts_by_closers_order(suffix, charset_order)
    elif mode == 'opens':
        return _suffix_counts_by_opens_order(suffix, charset_order)
    elif mode == 'pairs_open':
        return _suffix_counts_by_pairs_open_first(suffix, charset_order, chosen_pairs)
    else:
        # Fallback to closers mode
        return _suffix_counts_by_closers_order(suffix, charset_order)


def validate_unique_completion(prefix: str) -> bool:
    """
    Under closure-only completion rule, the completion is unique:
    at each step append the matched closer for the current stack top.
    We verify prefix validity and return True if valid.
    """
    try:
        _ = _unmatched_stack(prefix)
        return True
    except Exception:
        return False


def validate_puzzle_uniqueness(prefix: str, chosen_pairs, charset_order, mode: str) -> bool:
    """
    Fast, deterministic uniqueness and consistency check:
    - prefix is a valid Dyck prefix (no invalid steps)
    - completion is unique and non-empty (target_unmatched >= 1 guaranteed by YAML)
    - counts sum equals suffix length
    - complexity thresholds: at least two opening types seen, max depth >= 2
    - all characters in prefix belong to chosen_pairs universe
    Runtime negligible compared to 3 minutes budget.
    """
    try:
        # prefix validity and uniqueness of completion
        st = _unmatched_stack(prefix)
        comp = dyck_min_completion(prefix)
        suffix = comp[len(prefix):]
        if len(suffix) < 1:
            return False

        # charset order only contains characters from chosen_pairs
        chosen_chars = set()
        for op, cl in chosen_pairs:
            chosen_chars.add(op)
            chosen_chars.add(cl)
        for ch in prefix:
            if ch not in chosen_chars:
                return False

        # counts list consistency
        cnts = suffix_counts_list_mode(prefix, chosen_pairs, charset_order, mode)
        if sum_list(cnts) != len(suffix):
            return False

        # complexity thresholds
        stats = scan_stats(prefix)
        if len(stats['used_open_types']) < 2:
            return False
        if stats['max_depth'] < 2:
            return False

        return True
    except Exception:
        return False


def choose_rule_pack():
    """
    Randomly choose a rule pack controlling how query texts are phrased.
    Returns 1, 2, or 3.
    """
    return random.choice([1, 2, 3])


def choose_count_mode():
    """
    Randomly choose a counting mode for q3.
    """
    return random.choice(['closers', 'opens', 'pairs_open'])


def count_mode_label(mode: str):
    """
    Human-readable Chinese label string describing q3 counting mode.
    """
    if mode == 'opens':
        return '按字符顺序中的左括号顺序对应右括号计数'
    elif mode == 'pairs_open':
        return '按字符顺序中首次出现的左括号顺序对应括号对的右括号计数'
    else:
        return '按字符顺序中的右括号顺序'


def make_q1_text(rule_pack: int):
    """
    Generate q1 instruction text with examples, no English quotes.
    """
    base = '在仅允许在末尾追加必要的右括号的规则下补全当前前缀得到合法括号序列'
    if rule_pack == 2:
        base = '仅可在末尾补上所需的右括号使前缀成为合法括号序列'
    elif rule_pack == 3:
        base = '遵循只在末尾逐步补齐右括号的规则得到合法括号序列'
    suffix = ' 答案格式为不含空格的字符串 示例 ()[]<> 或 ()[]{{}}'
    return base + suffix


def make_q2_text(rule_pack: int):
    """
    Generate q2 instruction text, consistent with completed_length.
    """
    if rule_pack == 2:
        base = '请给出补全后的完整括号序列长度'
    elif rule_pack == 3:
        base = '请计算补全完成后序列的总长度'
    else:
        base = '请输出补全后的完整括号序列长度'
    suffix = ' 答案格式为整数 示例 12'
    return base + suffix


def make_q3_text(rule_pack: int, label: str):
    """
    Generate q3 instruction text, including counting mode label.
    """
    if rule_pack == 2:
        base = f'按照{label} 输出此次补全新增的右括号计数列表'
    elif rule_pack == 3:
        base = f'基于{label} 给出补全所新增右括号的计数列表'
    else:
        base = f'按照{label} 输出本次补全新增的右括号计数列表'
    suffix = ' 答案格式为整数列表 示例 [0,2,1]'
    return base + suffix