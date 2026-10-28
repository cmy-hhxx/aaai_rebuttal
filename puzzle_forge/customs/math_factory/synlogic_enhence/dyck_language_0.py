# dyck_language_1.py
import random
from typing import List, Sequence

# Core bracket maps
_OPEN_TO_CLOSE = {
    '(': ')',
    '[': ']',
    '{': '}',
    '<': '>',
}
_CLOSE_TO_OPEN = {v: k for k, v in _OPEN_TO_CLOSE.items()}

# Pool for allowed types selection
_TYPES_POOL = ['(', '[', '{', '<']

def pick_bracket_types(min_types: int, max_types: int) -> List[str]:
    min_types = max(1, int(min_types))
    max_types = max(min_types, int(max_types))
    max_types = min(max_types, len(_TYPES_POOL))
    k = random.randint(min_types, max_types)
    return random.sample(_TYPES_POOL, k)

def types_human_readable(allowed_types: Sequence[str]) -> str:
    # 为避免在 desc 中插入后被当作变量占位符解析，花括号统一使用双花括号
    name_map = {
        '(': '圆括号 ()',
        '[': '方括号 []',
        '{': '花括号 {{}}',
        '<': '尖括号 <>',
    }
    ordered = [t for t in _TYPES_POOL if t in allowed_types]
    parts = [name_map[t] for t in ordered]
    return '、'.join(parts)

def rand_float(a: float, b: float) -> float:
    lo = min(a, b)
    hi = max(a, b)
    return random.uniform(lo, hi)

def _gen_balanced_core(pairs: int, opens_set: Sequence[str]) -> str:
    """生成严格平衡的括号串，长度为 2 * pairs。"""
    s: List[str] = []
    stack: List[str] = []
    opens_used = 0
    closes_used = 0
    while opens_used < pairs or closes_used < pairs:
        can_open = opens_used < pairs
        can_close = closes_used < pairs and len(stack) > 0
        if not can_close and can_open:
            op = random.choice(opens_set)
            stack.append(op)
            s.append(op)
            opens_used += 1
        elif not can_open and can_close:
            top = stack.pop()
            s.append(_OPEN_TO_CLOSE[top])
            closes_used += 1
        else:
            # 随机选择开或闭，但保持不使栈为负
            if random.random() < 0.6:
                op = random.choice(opens_set)
                stack.append(op)
                s.append(op)
                opens_used += 1
            else:
                top = stack.pop()
                s.append(_OPEN_TO_CLOSE[top])
                closes_used += 1
    return ''.join(s)

def gen_incomplete_seq(target_len: int,
                       allowed_types: Sequence[str],
                       noise_prob: float,
                       min_unmatched: int) -> str:
    """先生成平衡核心串，再强制追加 k 个开括号，保证至少一个未匹配开括号。"""
    allowed_types = list(allowed_types) or ['(']
    opens_set = [t for t in allowed_types if t in _OPEN_TO_CLOSE] or ['(']
    target_len = max(12, int(target_len))
    min_unmatched = max(1, int(min_unmatched))

    # 选择需要留下的未匹配开括号数量 k
    max_k = max(1, min(min_unmatched + 6, target_len // 2))
    k = random.randint(min_unmatched, max_k)

    # 平衡部分的对数，尽量让总长度接近 target_len
    pairs_core = max(4, (target_len - k) // 2)
    core = _gen_balanced_core(pairs_core, opens_set)

    # 追加 k 个开括号，确保未匹配开括号数为 k
    tail_opens = ''.join(random.choice(opens_set) for _ in range(k))
    seq = core + tail_opens

    # 噪声注入（仅字母，保证不影响括号匹配）
    def inject_noise(s: str, prob: float) -> str:
        if prob <= 0:
            return s
        letters = 'abcdefghijklmnopqrstuvwxyz'
        out: List[str] = []
        for ch in s:
            if random.random() < prob:
                out.append(random.choice(letters))
            out.append(ch)
            if random.random() < (prob * 0.5):
                out.append(random.choice(letters))
        if random.random() < prob * 0.7:
            out.append(random.choice(letters))
        return ''.join(out)

    seq_with_noise = inject_noise(seq, max(0.0, float(noise_prob)))

    # 兜底：若未匹配数意外不达标，追加一个开括号
    if unmatched_count(seq_with_noise) < 1:
        seq_with_noise += random.choice(opens_set)

    return seq_with_noise

def complete_brackets(seq: str) -> str:
    stack: List[str] = []
    for ch in seq:
        if ch in _OPEN_TO_CLOSE:
            stack.append(ch)
        elif ch in _CLOSE_TO_OPEN:
            if stack and stack[-1] == _CLOSE_TO_OPEN[ch]:
                stack.pop()
            else:
                # mismatch or extraneous closer
                return seq
        else:
            continue
    completion = ''.join(_OPEN_TO_CLOSE[op] for op in reversed(stack))
    return seq + completion

def is_balanced(seq: str) -> bool:
    stack: List[str] = []
    for ch in seq:
        if ch in _OPEN_TO_CLOSE:
            stack.append(ch)
        elif ch in _CLOSE_TO_OPEN:
            if not stack or stack[-1] != _CLOSE_TO_OPEN[ch]:
                return False
            stack.pop()
        else:
            continue
    return len(stack) == 0

def seq_length(s: str) -> int:
    return len(s)

def unmatched_count(seq: str) -> int:
    stack: List[str] = []
    for ch in seq:
        if ch in _OPEN_TO_CLOSE:
            stack.append(ch)
        elif ch in _CLOSE_TO_OPEN:
            if stack and stack[-1] == _CLOSE_TO_OPEN[ch]:
                stack.pop()
            else:
                return -1
        else:
            continue
    return len(stack)

def has_prefix(full: str, prefix: str) -> bool:
    return isinstance(full, str) and isinstance(prefix, str) and full.startswith(prefix)

# =========================
# Batch and formatting utils
# =========================

def pick_types_list(n: int, min_types: int, max_types: int) -> List[List[str]]:
    n = max(1, int(n))
    out: List[List[str]] = []
    for _ in range(n):
        out.append(pick_bracket_types(min_types, max_types))
    return out

def rand_int_list(n: int, lo: int, hi: int) -> List[int]:
    n = max(1, int(n))
    lo = int(lo)
    hi = max(lo, int(hi))
    return [random.randint(lo, hi) for _ in range(n)]

def rand_float_list(n: int, a: float, b: float) -> List[float]:
    n = max(1, int(n))
    lo = min(float(a), float(b))
    hi = max(float(a), float(b))
    return [random.uniform(lo, hi) for _ in range(n)]

def gen_many_incomplete(base_lens: Sequence[int],
                        allowed_types_list: Sequence[Sequence[str]],
                        noise_probs: Sequence[float],
                        min_unmatched_list: Sequence[int]) -> List[str]:
    m = min(len(base_lens), len(allowed_types_list), len(noise_probs), len(min_unmatched_list))
    res: List[str] = []
    for i in range(m):
        res.append(gen_incomplete_seq(base_lens[i], allowed_types_list[i], noise_probs[i], min_unmatched_list[i]))
    return res

def complete_many(seq_list: Sequence[str]) -> List[str]:
    return [complete_brackets(s) for s in seq_list]

def needed_closers_list(seq_list: Sequence[str]) -> List[int]:
    return [max(0, unmatched_count(s)) for s in seq_list]

def validate_completion_batch(given_list: Sequence[str], completed_list: Sequence[str]) -> bool:
    if len(given_list) != len(completed_list):
        return False
    for g, c in zip(given_list, completed_list):
        if not isinstance(g, str) or not isinstance(c, str):
            return False
        if not has_prefix(c, g):
            return False
        if not is_balanced(c):
            return False
        uc = unmatched_count(g)
        if uc < 1:
            return False
        # Minimality: appended closers count equals unmatched_count(g)
        if (len(c) - len(g)) != uc:
            return False
    return True

def join_with_sep(items: Sequence[str], sep: str) -> str:
    return (sep or '').join([str(x) for x in items])

def join_int_list(items: Sequence[int], sep: str) -> str:
    return (sep or '').join([str(int(x)) for x in items])

def types_human_list(allowed_types_list: Sequence[Sequence[str]]) -> List[str]:
    return [types_human_readable(t) for t in allowed_types_list]

def join_types_for_desc(types_texts: Sequence[str]) -> str:
    # "第i段 可用括号类型为 <text>"；之间用分号连接
    parts: List[str] = []
    for i, t in enumerate(types_texts, start=1):
        parts.append(f"第{i}段 可用括号类型为 {t}")
    return '；'.join(parts)

def list_len_int(lst: Sequence) -> int:
    return int(len(lst))

# =========================
# Advanced aggregation & verification
# =========================

def appended_suffix(seq: str) -> str:
    comp = complete_brackets(seq)
    if len(comp) < len(seq):
        return ''
    return comp[len(seq):]

def appended_suffixes_list(seq_list: Sequence[str]) -> List[str]:
    return [appended_suffix(s) for s in seq_list]

def total_appended_counts(seq_list: Sequence[str]) -> List[int]:
    # Return counts for closers in fixed order: [')', ']', '}', '>']
    order = [')', ']', '}', '>']
    counts = {ch: 0 for ch in order}
    for s in seq_list:
        suf = appended_suffix(s)
        for ch in suf:
            if ch in counts:
                counts[ch] += 1
    return [counts[ch] for ch in order]

def sum_of_squares(int_list: Sequence[int]) -> int:
    return sum(int(x) * int(x) for x in int_list)

def verify_suffixes(given_list: Sequence[str], suffix_list: Sequence[str]) -> bool:
    if len(given_list) != len(suffix_list):
        return False
    for g, suf in zip(given_list, suffix_list):
        if appended_suffix(g) != suf:
            return False
        c = complete_brackets(g)
        if not has_prefix(c, g):
            return False
        if not is_balanced(c):
            return False
    return True

def check_counts_csv(given_list: Sequence[str], csv_str: str) -> bool:
    try:
        parts = [p.strip() for p in str(csv_str).split(',')]
        nums = [int(p) for p in parts if p != '']
    except Exception:
        return False
    if len(nums) != 4:
        return False
    target = total_appended_counts(given_list)
    return nums == target

def verify_uniqueness(given_list: Sequence[str]) -> bool:
    # 确定性最小补全唯一性：每段在末尾追加的闭括号序列由栈唯一决定
    for g in given_list:
        uc = unmatched_count(g)
        if uc < 1:
            return False
        suf = appended_suffix(g)
        if len(suf) != uc:
            return False
        # 重放栈得到期望后缀，并比对
        stack: List[str] = []
        for ch in g:
            if ch in _OPEN_TO_CLOSE:
                stack.append(ch)
            elif ch in _CLOSE_TO_OPEN:
                if stack and stack[-1] == _CLOSE_TO_OPEN[ch]:
                    stack.pop()
                else:
                    return False
            else:
                continue
        expected = ''.join(_OPEN_TO_CLOSE[x] for x in reversed(stack))
        if expected != suf:
            return False
    return True

def all_unmatched_positive(seq_list: Sequence[str]) -> bool:
    # Ensure every given segment needs at least one appended closer
    return all(unmatched_count(s) >= 1 for s in seq_list)

def suffix_lengths_equal(needed_counts: Sequence[int], suffix_list: Sequence[str]) -> bool:
    """Ensure each needed count equals the length of the corresponding appended suffix."""
    if len(needed_counts) != len(suffix_list):
        return False
    lengths = [len(str(s)) for s in suffix_list]
    try:
        counts = [int(x) for x in needed_counts]
    except Exception:
        return False
    return counts == lengths

# =========================
# Helpers for final packing
# =========================

def to_str(x) -> str:
    return str(x)

def check_final_pack(given_list: Sequence[str], final_str: str) -> bool:
    """校验最终汇总答案：p1====p2====p3====p4====p5，与各部分结果一致。"""
    try:
        parts = str(final_str).split('====')
        if len(parts) != 5:
            return False
        p1, p2, p3, p4, p5 = parts
        comp_join = join_with_sep(complete_many(given_list), '|')
        need_csv = join_int_list(needed_closers_list(given_list), ',')
        suf_join = join_with_sep(appended_suffixes_list(given_list), '|')
        counts_csv = join_int_list(total_appended_counts(given_list), ',')
        sumsq = sum_of_squares(needed_closers_list(given_list))
        return (p1 == comp_join and
                p2 == need_csv and
                p3 == suf_join and
                p4 == counts_csv and
                p5 == str(sumsq))
    except Exception:
        return False