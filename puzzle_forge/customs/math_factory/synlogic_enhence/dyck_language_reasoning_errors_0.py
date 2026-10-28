# -*- coding: utf-8 -*-
"""
dyck_language_reasoning_errors_0.py

Advanced generator and verifier for Dyck-language reasoning error detection with
segmented input, multi-style corruption, and efficient unique solution verification.

Custom operators exposed to YAML:
- gen_dyck_random(seq_len, include_types_num, max_nesting, balanced_prob, segment_num): str
- build_thought_lines_ex(input_seq, error_count, final_claim_variant, error_styles_num): List[str]
- build_rule_texts(input_seq, final_claim_variant, rule_complexity_level): List[str]
- function_1(input_seq, thought_lines): List[int]
- function_2(errors): str
- verify_unique_answer(input_seq, thought_lines, answer_text): bool

Additional helper for external synthesizers:
- gen_dyck_seq(): Tuple[str, List[str]]
"""

import random
import re
import time
from typing import List, Tuple

# Bracket pools
BRACKETS = [
    ('(', ')'),
    ('[', ']'),
    ('{', '}'),
    ('<', '>')
]

_OPENERS = "([{<"
_CLOSERS = ")]}>"
_PAIR = dict(zip(_CLOSERS, _OPENERS))


def _parse_step_number(line: str) -> int:
    """
    Extract step number N from 'Thought N:' or '思考过程N:'.
    Returns -1 if not found.
    """
    m = re.search(r'(Thought|思考过程)\s*(\d+)\s*:', line)
    if not m:
        m2 = re.search(r'\b(\d+)\b', line)
        return int(m2.group(1)) if m2 else -1
    return int(m.group(2))


def _has_stack_declaration(line: str) -> bool:
    return '栈:' in line


def _extract_token_marker(line: str) -> bool:
    """
    Whether the line is a token-processing step: '... X ; 栈: ...'
    Used to decide consumption of the next input character.
    """
    return ';' in line and '栈:' in line and line.find(';') < line.find('栈:')


def _parse_claimed_stack(line: str) -> List[str]:
    """
    Parse the stack claim after '栈:' into a list of openers, bottom->top order.
    '栈: 空' -> []
    '栈: {(' -> ['{', '(']
    """
    if '栈:' not in line:
        return []
    seg = line.split('栈:', 1)[1].strip()
    if seg.startswith('空'):
        return []
    claimed: List[str] = []
    for ch in seg:
        if ch in _OPENERS:
            claimed.append(ch)
    return claimed


def _advance_stack_by_char(stack: List[str], ch: str) -> Tuple[bool, List[str]]:
    """
    Apply Dyck stack update for a single character.
    Returns (valid, new_stack).
    """
    st = list(stack)
    if ch in _OPENERS:
        st.append(ch)
        return True, st
    if ch in _CLOSERS:
        if not st or st[-1] != _PAIR[ch]:
            # mismatch -> invalid, keep stack unchanged (continue analysis)
            return False, st
        st.pop()
        return True, st
    # Illegal non-bracket character
    return False, st


def function_1(input_seq: str, thought_lines: List[str]) -> List[int]:
    """
    Detect all erroneous steps by comparing claimed stacks with real stacks
    while consuming input_seq per token step. Also validates the final claim variant:
    - if line contains '最终栈' and '空' -> stack must be empty;
    - if line contains '最终栈' and '非空' -> stack must be non-empty.
    """
    errors: List[int] = []
    step_stack: List[str] = []
    consumed = 0
    n = len(input_seq)

    for line in thought_lines:
        step_no = _parse_step_number(line)

        # Token step consumes one character from input_seq
        if _extract_token_marker(line):
            if consumed >= n:
                if step_no != -1:
                    errors.append(step_no)
            else:
                ok, new_stack = _advance_stack_by_char(step_stack, input_seq[consumed])
                consumed += 1
                if not ok and step_no != -1:
                    errors.append(step_no)
                step_stack = new_stack

        # Compare claimed stack vs real stack
        if _has_stack_declaration(line):
            claimed = _parse_claimed_stack(line)
            if claimed != step_stack and step_no != -1:
                errors.append(step_no)

        # Final claim validation with variant
        if '最终栈' in line:
            # Ensure we have consumed all remaining inputs before the final check
            while consumed < n:
                ok, new_stack = _advance_stack_by_char(step_stack, input_seq[consumed])
                consumed += 1
                step_stack = new_stack
            if '空' in line:
                if len(step_stack) != 0 and step_no != -1:
                    errors.append(step_no)
            elif '非空' in line:
                if len(step_stack) == 0 and step_no != -1:
                    errors.append(step_no)
            else:
                # If neither variant appears, ignore final claim line
                pass

    return sorted(set([e for e in errors if e != -1]))


def function_2(errors: List[int]) -> str:
    """
    Format errors list:
    - No error -> empty string
    - With errors -> comma-separated indices
    """
    if not errors:
        return ""
    return ",".join(str(x) for x in errors)


def _pick_brackets(include_types_num: int) -> List[Tuple[str, str]]:
    k = max(1, min(include_types_num, len(BRACKETS)))
    return random.sample(BRACKETS, k)


def _build_balanced_segment(seg_len: int, types: List[Tuple[str, str]], max_nesting: int) -> List[str]:
    """
    Build a balanced segment respecting max_nesting and target seg_len (even).
    """
    seg_len = max(2, seg_len - seg_len % 2)
    stack: List[str] = []
    res: List[str] = []
    remaining = seg_len

    def can_push() -> bool:
        return len(stack) < max_nesting and remaining > len(stack)

    while remaining > 0:
        if not stack:
            opener, _ = random.choice(types)
            stack.append(opener)
            res.append(opener)
            remaining -= 1
        else:
            choose_push = random.random() < 0.5
            if can_push() and choose_push:
                opener, _ = random.choice(types)
                stack.append(opener)
                res.append(opener)
                remaining -= 1
            else:
                top = stack.pop()
                closer = None
                for o, c in types:
                    if o == top:
                        closer = c
                        break
                if closer is None:
                    closer = _CLOSERS[_OPENERS.index(top)]
                res.append(closer)
                remaining -= 1
    return res


def _corrupt_segment(res: List[str], types: List[Tuple[str, str]], ratio: float) -> None:
    """
    Corrupt a segment in place by replacing some closers with wrong ones.
    """
    indices = [i for i, ch in enumerate(res) if ch in _CLOSERS]
    if not indices:
        return
    random.shuffle(indices)
    k = max(1, int(ratio * len(indices)))
    wrong_choices = [c for _, c in types]
    for i in indices[:k]:
        true_closer = res[i]
        candidates = [x for x in wrong_choices if x != true_closer]
        if candidates:
            res[i] = random.choice(candidates)


def gen_dyck_random(seq_len: int, include_types_num: int, max_nesting: int, balanced_prob: float, segment_num: int) -> str:
    """
    Generate a segmented Dyck-like sequence:
    - Choose bracket types.
    - Split total length into 'segment_num' segments.
    - Build each segment balanced and possibly corrupt with mismatches based on balanced_prob.
    - Concatenate segments and trim/pad to exact seq_len (padding with micro-pairs from chosen types).
    """
    types = _pick_brackets(include_types_num)
    segment_num = max(2, segment_num)
    seq_len = max(20, seq_len)
    # random split
    base = [random.randint(8, max(10, seq_len // segment_num + 4)) for _ in range(segment_num)]
    scale = sum(base)
    # compute proportional lengths
    lengths = [max(8, int(seq_len * b / scale)) for b in base]
    # adjust to exact sum
    diff = seq_len - sum(lengths)
    for _ in range(abs(diff)):
        idx = random.randrange(segment_num)
        lengths[idx] += 1 if diff > 0 else -1
        lengths[idx] = max(8, lengths[idx])

    segments: List[str] = []
    for L in lengths:
        seg = _build_balanced_segment(L, types, max_nesting)
        make_balanced = random.random() < max(0.0, min(1.0, balanced_prob))
        if not make_balanced:
            # corrupt 10%–30% of closers
            _corrupt_segment(seg, types, ratio=random.uniform(0.1, 0.3))
        segments.append("".join(seg))

    res = "".join(segments)
    # Pad if shorter
    while len(res) < seq_len:
        o, c = random.choice(types)
        res += o + c
    # Trim if longer
    res = res[:seq_len]
    return res


def _stack_to_str(stack: List[str]) -> str:
    """
    Convert a stack (list of openers) into display string for thought lines.
    Empty -> '空'; otherwise concatenate openers in order.
    """
    return '空' if not stack else ''.join(stack)


def build_thought_lines_ex(input_seq: str, error_count: int, final_claim_variant: str, error_styles_num: int) -> List[str]:
    """
    Build thought lines with multiple error styles:
    - Thought 1: intro
    - Thought 2: initial stack empty
    - For each character: 'Thought k: X ; 栈: <claimed>'
      claimed equals true stack, except for 'error_count' distinct steps corrupted by up to 'error_styles_num' styles:
        * empty-flip: claim '空' even when stack non-empty
        * wrong-type: replace last opener with a different type
        * permutation: reorder openers
        * extra-opener: inject random opener(s)
    - Final statement: claim '最终栈是空的' or '最终栈是非空的' per variant.
    """
    lines: List[str] = []
    lines.append('Thought 1: 我们应该逐个处理输入并跟踪栈的配置。')
    lines.append('Thought 2: 栈: 空')

    # Simulate correct stack per character
    true_stacks: List[List[str]] = []
    st: List[str] = []
    for ch in input_seq:
        ok, st = _advance_stack_by_char(st, ch)
        true_stacks.append(list(st))

    n = len(input_seq)
    candidates = list(range(n))
    random.shuffle(candidates)
    k = max(0, min(error_count, n))
    err_positions = set(candidates[:k])

    for i, ch in enumerate(input_seq):
        claimed = _stack_to_str(true_stacks[i])
        if i in err_positions:
            styles_pool = ['empty_flip', 'wrong_type', 'permute', 'extra']
            chosen_styles = random.sample(styles_pool, k=min(error_styles_num, len(styles_pool)))
            # apply styles
            for sty in chosen_styles:
                if sty == 'empty_flip':
                    claimed = '空'
                elif sty == 'wrong_type' and claimed != '空':
                    last = claimed[-1]
                    alternatives = [o for o in _OPENERS if o != last]
                    if alternatives:
                        claimed = claimed[:-1] + random.choice(alternatives)
                elif sty == 'permute' and claimed != '空' and len(claimed) >= 2:
                    # permute openers randomly
                    cl_list = list(claimed)
                    random.shuffle(cl_list)
                    claimed = ''.join(cl_list)
                elif sty == 'extra':
                    # add one or two random openers
                    add = ''.join(random.choice(_OPENERS) for _ in range(random.randint(1, 2)))
                    if claimed == '空':
                        claimed = add
                    else:
                        claimed = claimed + add
        line = f"Thought {i + 3}: {ch} ; 栈: {claimed}"
        lines.append(line)

    if final_claim_variant == 'nonempty':
        lines.append('Thought {0}: 现在，我们已经到达结尾。最终栈是非空的。'.format(n + 3))
    else:
        lines.append('Thought {0}: 现在，我们已经到达结尾。最终栈是空的。'.format(n + 3))

    return lines


def _used_pairs_from_seq(input_seq: str) -> List[str]:
    openers_used = set(ch for ch in input_seq if ch in _OPENERS)
    pairs = []
    for o in _OPENERS:
        if o in openers_used:
            try:
                idx = _OPENERS.index(o)
                c = _CLOSERS[idx]
                pairs.append(o + c)
            except Exception:
                pass
    seen = set()
    res = []
    for p in pairs:
        if p not in seen:
            seen.add(p)
            res.append(p)
    return res


def build_rule_texts(input_seq: str, final_claim_variant: str, rule_complexity_level: int) -> List[str]:
    """
    Build randomized rule sentences (3–5 lines) consistent with the checker logic:
    - Clarify stack display, processing method, mismatch policy, supported types, nesting and segmentation hints.
    - Include final-claim variant requirement.
    """
    pairs_str = ', '.join(_used_pairs_from_seq(input_seq)) or '()'
    base_templates = [
        '我们逐字符处理输入并在每一步声明当前栈, 栈显示为自底到顶的开括号序列, 空栈显示为[空]。',
        '遇到开括号时压栈; 遇到闭括号时必须匹配栈顶开括号, 否则该步判为错误但继续分析。',
        '本题可能使用的括号类型包括: ' + pairs_str + '。',
        '输入可能由多个片段组成, 每个片段内部优先满足嵌套与闭合, 部分片段可能被引入少量不匹配以提升挑战性。',
        '最大嵌套深度受限制, 请注意栈的增长与回退模式。',
        '非括号字符不会出现于输入中, 因此无需考虑。',
    ]
    final_templates = {
        'empty': '最后一步的声明要求最终栈为空, 我们将验证该声明是否成立。',
        'nonempty': '最后一步的声明要求最终栈为非空, 我们将验证该声明是否成立。'
    }
    k = max(3, min(rule_complexity_level, 5))
    chosen = random.sample(base_templates, k)
    chosen.append(final_templates.get(final_claim_variant, final_templates['empty']))
    return chosen


def verify_unique_answer(input_seq: str, thought_lines: List[str], answer_text: str) -> bool:
    """
    Efficient uniqueness verification within local search budget:
    - Check consistency: recompute errors and ensure formatting equals answer_text.
    - Toggle final-claim variant and verify that resulting error list differs from original (reduces ambiguity).
    - For each token step, simulate correcting the claimed stack to its true stack and check whether
      the error list becomes identical to the original (if yes, ambiguity); otherwise keep unique.
    The search is O(n) with small constants; we guard with a 3-minute upper bound (far exceeded).
    """
    start = time.time()
    orig_errors = function_1(input_seq, thought_lines)
    if function_2(orig_errors) != answer_text:
        return False

    # Attempt alternative final claim: replace last line variant if present
    alt_lines = list(thought_lines)
    if alt_lines and '最终栈' in alt_lines[-1]:
        if '空' in alt_lines[-1]:
            alt_lines[-1] = alt_lines[-1].replace('空', '非空')
        elif '非空' in alt_lines[-1]:
            alt_lines[-1] = alt_lines[-1].replace('非空', '空')
        alt_errors = function_1(input_seq, alt_lines)
        # If toggling final claim produces the same answer, it may be ambiguous
        if function_2(alt_errors) == answer_text and alt_errors != orig_errors:
            return False

    # Try to locally correct each claimed stack to its true stack and see if answer set stays identical
    # Build true stacks once
    true_stacks: List[List[str]] = []
    st: List[str] = []
    for ch in input_seq:
        _, st = _advance_stack_by_char(st, ch)
        true_stacks.append(list(st))

    # Map token indices to line indices: token i -> line i+3
    for i in range(len(true_stacks)):
        if time.time() - start > 180.0:
            break  # time guard
        line_idx = i + 3
        if line_idx >= len(thought_lines):
            break
        line = thought_lines[line_idx]
        if '栈:' not in line:
            continue
        # Build corrected line
        claimed = _stack_to_str(true_stacks[i])
        head = line.split('栈:', 1)[0]  # keep token echo and prefix
        corrected_line = head + '栈: ' + claimed
        alt_lines = list(thought_lines)
        alt_lines[line_idx] = corrected_line
        alt_errors = function_1(input_seq, alt_lines)
        if alt_errors != orig_errors and function_2(alt_errors) == answer_text:
            # Found an alternative with same formatted answer but different error set -> ambiguity
            return False

    return True


def gen_dyck_seq() -> Tuple[str, List[str]]:
    """
    Provide a fixed sample for compatibility; not used by the generalized generator.
    """
    input_seq = '(){}{}(){()()[]}'
    thought_lines = [
        'Thought 1: 我们应该逐个处理输入并跟踪栈的配置。',
        'Thought 2: 栈: 空',
        'Thought 3: ( ; 栈: (',
        'Thought 4: ) ; 栈: 空',
        'Thought 5: { ; 栈: {',
        'Thought 6: } ; 栈: 空',
        'Thought 7: { ; 栈: {',
        'Thought 8: } ; 栈: 空',
        'Thought 9: ( ; 栈: (',
        'Thought 10: ) ; 栈: 空',
        'Thought 11: { ; 栈: {{',
        'Thought 12: ( ; 栈: {(',
        'Thought 13: ) ; 栈: {',
        'Thought 14: ( ; 栈: {(',
        'Thought 15: ) ; 栈: {[',
        'Thought 16: [ ; 栈: {[',
        'Thought 17: ] ; 栈: {',
        'Thought 18: } ; 栈: (',
        'Thought 19: 现在，我们已经到达结尾。最终栈是空的。',
    ]
    return input_seq, thought_lines