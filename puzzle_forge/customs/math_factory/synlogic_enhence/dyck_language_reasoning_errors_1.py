# dyck_language_reasoning_errors_0.py

import random
import time
from typing import List, Dict, Any, Tuple

# Bracket sets and mappings
OPEN_SET = set("([{<")
CLOSE_SET = set(")]}>")
PAIR_MAP = {')': '(', '}': '{', ']': '[', '>': '<'}
REV_PAIR = {'(': ')', '{': '}', '[': ']', '<': '>'}

# Category labels for opens
CAT_LABEL = {'(': '圆', '{': '花', '[': '方', '<': '尖'}

FILLERS = "abcXYZ012"

def _render_stack(stack: List[str]) -> str:
    """Render the stack as concatenated opens, or '空' if empty."""
    return ''.join(stack) if stack else '空'

def _parse_step_number(step: str) -> int:
    """Parse 'Thought N: ...' -> N; return -1 on failure."""
    try:
        prefix = "Thought "
        idx = step.find(prefix)
        if idx == -1:
            return -1
        idx += len(prefix)
        end = step.find(":", idx)
        if end == -1:
            return -1
        return int(step[idx:end].strip())
    except Exception:
        return -1

def _split_body(step: str) -> str:
    """Return text after 'Thought N:'."""
    try:
        return step.split(":", 1)[1].strip()
    except Exception:
        return step.strip()

def detect_reasoning_errors(input_str: str, raw_thoughts: List[str]) -> List[int]:
    """
    Detect reasoning errors w.r.t. Dyck rules with extended line types.
    Only bracket chars in input_str are considered; others are ignored.
    Returns sorted list of erroneous step numbers.

    Semantic alignment to puzzle text:
    - Only the exact next bracket (at current pointer) may be processed to mutate state.
    - Processing a non-bracket or a bracket different from the pointer target marks error and does not change stack/pointer.
    """
    allowed = set("(){}[]<>")
    char_seq = [c for c in input_str if c in allowed]
    pos = 0
    stack: List[str] = []
    errors: List[int] = []

    def mark_error(step_num: int):
        if step_num not in errors and step_num != -1:
            errors.append(step_num)

    for step in raw_thoughts:
        step_num = _parse_step_number(step)
        body = _split_body(step)

        # Final emptiness assertion (only valid when end and stack empty)
        if "最终栈是空的" in body:
            actual_empty = (pos == len(char_seq) and len(stack) == 0)
            if not actual_empty:
                mark_error(step_num)
            continue

        # Pointer claim
        if body.startswith("指针:"):
            claimed = body.split("指针:", 1)[1].strip()
            try:
                p = int(claimed)
                if p != pos:
                    mark_error(step_num)
            except Exception:
                mark_error(step_num)
            continue

        # Next character prediction
        if body.startswith("下一个字符:"):
            pred = body.split("下一个字符:", 1)[1].strip()
            if pos >= len(char_seq):
                if pred != "终止":
                    mark_error(step_num)
            else:
                if len(pred) != 1 or pred != char_seq[pos]:
                    mark_error(step_num)
            continue

        # Depth claim
        if body.startswith("深度:"):
            claimed = body.split("深度:", 1)[1].strip()
            try:
                k = int(claimed)
                if k != len(stack):
                    mark_error(step_num)
            except Exception:
                mark_error(step_num)
            continue

        # Depth parity claim
        if body.startswith("深度奇偶:"):
            claimed = body.split("深度奇偶:", 1)[1].strip()
            parity = "偶" if (len(stack) % 2 == 0) else "奇"
            if claimed != parity:
                mark_error(step_num)
            continue

        # Top-of-stack category claim
        if body.startswith("栈顶类别:"):
            claimed = body.split("栈顶类别:", 1)[1].strip()
            if len(stack) == 0:
                actual = "空"
            else:
                top = stack[-1]
                actual = CAT_LABEL.get(top, "空")
            if claimed != actual:
                mark_error(step_num)
            continue

        # Only stack report (no char consumed)
        if body.startswith("栈:"):
            claimed = body.split("栈:", 1)[1].strip()
            actual = _render_stack(stack)
            if claimed != actual:
                mark_error(step_num)
            continue

        # Step like 'X ; 栈: Y' (attempt to process one character and then claim stack)
        if ";" in body:
            left, right = body.split(";", 1)
            char = left.strip()
            allowed_set = set("(){}[]<>")

            advance_and_mutate = False

            if char not in allowed_set:
                # Non-bracket processed: error, no state change
                mark_error(step_num)
            else:
                # Compare with next expected bracket
                if pos >= len(char_seq) or char != char_seq[pos]:
                    # Not the next expected: error, no state change
                    mark_error(step_num)
                else:
                    # Correct processing of next bracket
                    advance_and_mutate = True

            if advance_and_mutate:
                if char in OPEN_SET:
                    stack.append(char)
                else:
                    if stack and stack[-1] == PAIR_MAP.get(char, ''):
                        stack.pop()
                    else:
                        # Defensive guard; shouldn't happen for balanced generator
                        mark_error(step_num)
                pos += 1

            # Validate claimed stack display
            claimed_part = right.strip()
            if claimed_part.startswith("栈:"):
                claimed = claimed_part.split("栈:", 1)[1].strip()
            else:
                claimed = claimed_part
            actual = _render_stack(stack)
            if claimed != actual:
                mark_error(step_num)
            continue

        # Any other text: treat as no-op (comment), not an error
        continue

    errors.sort()
    return errors

def format_output(error_steps: List[int]) -> str:
    """Return canonical Python list string of sorted error steps, e.g., '[]' or '[3,7]'."""
    if not error_steps:
        return "[]"
    return "[" + ",".join(str(x) for x in sorted(error_steps)) + "]"

def _choose_bracket_types() -> List[Tuple[str, str]]:
    """Randomly choose a non-empty subset of bracket types."""
    all_types = [('(', ')'), ('{', '}'), ('[', ']'), ('<', '>')]
    k = random.randint(1, 4)
    return random.sample(all_types, k)

def _gen_balanced_sequence(n_pairs: int, types: List[Tuple[str, str]]) -> List[str]:
    """
    Generate a balanced bracket sequence of length 2*n_pairs using the provided types.
    """
    seq: List[str] = []
    stack: List[str] = []
    opens = [t[0] for t in types]
    closes = {t[0]: t[1] for t in types}
    to_open = n_pairs

    total_len = 2 * n_pairs
    for _ in range(total_len):
        can_open = to_open > 0
        can_close = len(stack) > 0
        if can_open and (not can_close or random.random() < 0.6):
            ch_open = random.choice(opens)
            stack.append(ch_open)
            seq.append(ch_open)
            to_open -= 1
        else:
            top = stack.pop()
            seq.append(closes[top])
    return seq

def _insert_fillers(chars: List[str]) -> str:
    """
    Optionally insert non-bracket filler characters around bracket chars.
    These are ignored by the checker.
    """
    use_fillers = random.random() < 0.5
    if not use_fillers:
        return "".join(chars)
    out: List[str] = []
    for c in chars:
        if random.random() < 0.25:
            out.append(random.choice(FILLERS))
        out.append(c)
        if random.random() < 0.25:
            out.append(random.choice(FILLERS))
            if random.random() < 0.2:
                out.append(random.choice(FILLERS))
    return "".join(out)

def _intro_line() -> str:
    templates = [
        "我们应该逐个处理输入并跟踪栈的配置。",
        "我们将依次读取每个字符，并用栈记录括号匹配状态。",
        "逐步扫描输入，维护一个栈来完成括号的匹配。"
    ]
    return random.choice(templates)

def _comment_line() -> str:
    templates = [
        "提示：括号需要成对匹配，保持栈的先进后出特性。",
        "注意：只有括号参与匹配，其他字符忽略不影响栈。",
        "当前仅检查括号匹配关系，其余字符不改变状态。"
    ]
    return random.choice(templates)

def _rules_desc(types: List[Tuple[str, str]]) -> str:
    """
    Human-readable rules with random phrasing but fixed key points.
    """
    type_str = ''.join([t[0] + REV_PAIR[t[0]] for t in types])
    lead_templates = [
        "使用栈匹配括号：左括号入栈；右括号需与栈顶匹配并出栈；处理完所有括号字符后栈为空。",
        "括号匹配规则：遇到左括号将其压入栈；遇到右括号需与栈顶左括号成对才可弹出；所有括号处理结束时栈应为空。"
    ]
    extras = [
        "仅括号参与验证，非括号字符会被忽略；若某一步试图处理非括号字符，该步判定为错误。",
        f"允许的括号类型为：{type_str}。",
        "指针从0开始，始终指向下一个待处理的括号字符；只有正确处理该字符时才会推进指针并改变栈，处理其他字符不改变状态且视为错误。",
        "栈显示规范：将当前栈中左括号自底到顶按顺序直接拼接；若栈为空，显示为'空'。",
        "栈顶类别采用约定：'('→圆，'{'→花，'['→方，'<'→尖；若栈为空，则类别为'空'。",
        "允许的思考行类型：'栈: <文本>'（仅报告栈）、'<字符> ; 栈: <文本>'（处理一个括号并报告栈）、'深度: K'、'深度奇偶: 偶/奇'、'栈顶类别: <类别>'、'指针: P'、'下一个字符: <字符或终止>'、以及仅在结尾有效的'...最终栈是空的。'。",
        "允许的无操作注释行（如以'提示：'或'注意：'开头），不会改变状态也不构成错误；除此之外未在上面列出的行将被忽略。",
        "步骤编号即 Thought 前缀中的数字，思考步骤之间以竖线（|）分隔。"
    ]
    errors = [
        "若任一步显示的栈与真实栈不一致、试图处理非括号字符、错误的深度/奇偶/栈顶类别/指针/下一个字符断言、或在结尾之前宣称'最终栈是空的'，均为推理错误。"
    ]
    return f"{random.choice(lead_templates)}" + " ".join(extras) + errors[0]

def _eligible_stack_claim_indices(thoughts: List[str]) -> List[int]:
    """
    Return indices (0-based) of thoughts that have '栈:' claims or char steps and are NOT the final statement.
    """
    if not thoughts:
        return []
    idxs = []
    for i, t in enumerate(thoughts):
        body = _split_body(t)
        if "最终栈是空的" in body:
            continue
        if body.startswith("栈:") or ";" in body:
            idxs.append(i)
    return idxs

def _find_extra_claim_indices(thoughts: List[str]) -> List[int]:
    """
    Indices (0-based) of extended claims eligible for wrong mutation:
    '深度:', '深度奇偶:', '栈顶类别:', '指针:', '下一个字符:'.
    """
    idxs = []
    for i, t in enumerate(thoughts):
        body = _split_body(t)
        if "最终栈是空的" in body:
            continue
        if body.startswith("深度:") or body.startswith("深度奇偶:") or body.startswith("栈顶类别:") or body.startswith("指针:") or body.startswith("下一个字符:"):
            idxs.append(i)
    return idxs

def _mutate_claim_text(original: str, allowed_opens: List[str]) -> str:
    """
    Produce a wrong stack text different from original, but still plausible.
    original: e.g., '空' or a string like '{('
    """
    if original == "空":
        return random.choice(allowed_opens)
    s = original
    if len(s) == 1:
        choices = [o for o in allowed_opens if o != s]
        if not choices:
            return s + random.choice(allowed_opens)
        return random.choice(choices)
    if random.random() < 0.5:
        last = s[-1]
        choices = [o for o in allowed_opens if o != last] or allowed_opens
        return s[:-1] + random.choice(choices)
    else:
        return s[:-1] if len(s) > 1 else random.choice(allowed_opens)

def _mutate_extra_claim(body: str) -> str:
    """
    Mutate an extended claim line into a wrong one while keeping format.
    """
    if body.startswith("深度:"):
        try:
            k = int(body.split("深度:", 1)[1].strip())
            choices = [x for x in [k-1, k+1, k+2, max(0, k-2)] if x != k and x >= 0]
            wrong = random.choice(choices) if choices else (k + 1)
            return f"深度: {wrong}"
        except Exception:
            return "深度: 0"
    if body.startswith("深度奇偶:"):
        val = body.split("深度奇偶:", 1)[1].strip()
        wrong = "偶" if val == "奇" else "奇"
        return f"深度奇偶: {wrong}"
    if body.startswith("栈顶类别:"):
        val = body.split("栈顶类别:", 1)[1].strip()
        options = ["圆", "花", "方", "尖", "空"]
        wrongs = [x for x in options if x != val]
        return f"栈顶类别: {random.choice(wrongs)}" if wrongs else "栈顶类别: 空"
    if body.startswith("指针:"):
        try:
            p = int(body.split("指针:", 1)[1].strip())
            wrong = p + random.choice([-2, -1, 1, 2, 3])
            if wrong < 0:
                wrong = 0
            return f"指针: {wrong}"
        except Exception:
            return "指针: 0"
    if body.startswith("下一个字符:"):
        val = body.split("下一个字符:", 1)[1].strip()
        options = list("(){}[]<>") + ["终止"]
        wrongs = [x for x in options if x != val]
        return f"下一个字符: {random.choice(wrongs)}" if wrongs else "下一个字符: 终止"
    return body

def _renumber_thoughts(thoughts: List[str]) -> List[str]:
    """Renumber all 'Thought N:' prefixes into 1..k in order."""
    out = []
    for i, t in enumerate(thoughts, start=1):
        body = _split_body(t)
        out.append(f"Thought {i}: {body}")
    return out

def _inject_wrong_stack_claims(thoughts: List[str], types: List[Tuple[str, str]], max_k: int) -> Tuple[List[str], List[int]]:
    """Inject up to max_k wrong '栈:' claims; return new thoughts and erroneous step numbers before renumber."""
    if max_k <= 0:
        return thoughts[:], []
    allowed_opens = [t[0] for t in types]
    idxs = _eligible_stack_claim_indices(thoughts)
    if not idxs:
        return thoughts[:], []
    k = random.randint(0, min(max_k, len(idxs)))
    if k == 0:
        return thoughts[:], []
    chosen = sorted(random.sample(idxs, k))
    new_thoughts = thoughts[:]
    error_steps: List[int] = []

    for idx in chosen:
        step_num = _parse_step_number(new_thoughts[idx])
        body = _split_body(new_thoughts[idx])
        if body.startswith("栈:"):
            claimed = body.split("栈:", 1)[1].strip()
            wrong = _mutate_claim_text(claimed, allowed_opens)
            new_thoughts[idx] = f"Thought {step_num}: 栈: {wrong}"
            error_steps.append(step_num)
        elif ";" in body:
            left, right = body.split(";", 1)
            claimed_part = right.strip()
            if claimed_part.startswith("栈:"):
                claimed = claimed_part.split("栈:", 1)[1].strip()
            else:
                claimed = claimed_part
            wrong = _mutate_claim_text(claimed, allowed_opens)
            new_thoughts[idx] = f"Thought {step_num}: {left.strip()} ; 栈: {wrong}"
            error_steps.append(step_num)
    return new_thoughts, error_steps

def _inject_wrong_extra_claims(thoughts: List[str], max_k: int) -> List[str]:
    """Inject up to max_k wrong extended claims (深度、奇偶、类别、指针、下一个字符)."""
    if max_k <= 0:
        return thoughts[:]
    idxs = _find_extra_claim_indices(thoughts)
    if not idxs:
        return thoughts[:]
    k = random.randint(0, min(max_k, len(idxs)))
    if k == 0:
        return thoughts[:]
    chosen = sorted(random.sample(idxs, k))
    new_thoughts = thoughts[:]
    for idx in chosen:
        step_num = _parse_step_number(new_thoughts[idx])
        body = _split_body(new_thoughts[idx])
        mutated = _mutate_extra_claim(body)
        new_thoughts[idx] = f"Thought {step_num}: {mutated}"
    return new_thoughts

def _find_char_step_indices(thoughts: List[str]) -> List[int]:
    """Indices (0-based) whose body is of form 'X ; 栈: ...'."""
    idxs = []
    for i, t in enumerate(thoughts):
        body = _split_body(t)
        if ";" in body:
            idxs.append(i)
    return idxs

def _insert_invalid_char_steps(thoughts: List[str], max_k: int) -> List[str]:
    """
    Insert up to max_k invalid-char processing steps after random char steps.
    Each inserted line: 'Thought N: Z ; 栈: <same-as-prev>' where Z in FILLERS.
    Do not change stack or pointer; detection will flag that step only.
    """
    if max_k <= 0:
        return thoughts[:]
    char_idxs = _find_char_step_indices(thoughts)
    if not char_idxs:
        return thoughts[:]
    k = random.randint(0, min(max_k, len(char_idxs)))
    if k == 0:
        return thoughts[:]
    chosen = sorted(random.sample(char_idxs, k))
    new_thoughts: List[str] = []
    for i, t in enumerate(thoughts):
        new_thoughts.append(t)
        if i in chosen:
            body = _split_body(t)
            left, right = body.split(";", 1)
            claimed_part = right.strip()
            if claimed_part.startswith("栈:"):
                claimed_stack = claimed_part.split("栈:", 1)[1].strip()
            else:
                claimed_stack = claimed_part
            filler_char = random.choice(FILLERS)
            step_num = _parse_step_number(t)
            new_thoughts.append(f"Thought {step_num}: {filler_char} ; 栈: {claimed_stack}")
    return new_thoughts

def _insert_premature_final(thoughts: List[str], max_k: int) -> List[str]:
    """
    Insert up to max_k premature '最终栈是空的' assertions before the final line.
    These are guaranteed errors, non-invasive to state.
    """
    if max_k <= 0 or len(thoughts) < 3:
        return thoughts[:]
    k = random.randint(0, max_k)
    if k == 0:
        return thoughts[:]
    n = len(thoughts)
    positions = list(range(1, n - 1))
    if not positions:
        return thoughts[:]
    chosen = sorted(random.sample(positions, min(k, len(positions))))
    new_thoughts: List[str] = []
    for i, t in enumerate(thoughts):
        new_thoughts.append(t)
        if i in chosen:
            step_num = _parse_step_number(t)
            prefix = random.choice(["现在，我们已经到达结尾。", "至此，我们处理完所有字符。", "到这里，所有括号均已检查完毕。"])
            new_thoughts.append(f"Thought {step_num}: {prefix}最终栈是空的。")
    return new_thoughts

def _build_correct_thoughts(bracket_str: str, types: List[Tuple[str, str]]) -> List[str]:
    """
    Build the canonical correct step-by-step thoughts with richer claims and comments.
    """
    allowed = set("(){}[]<>")
    char_seq = [c for c in bracket_str if c in allowed]
    thoughts: List[str] = []
    step_no = 1
    thoughts.append(f"Thought {step_no}: {_intro_line()}")
    step_no += 1
    stack: List[str] = []
    pos = 0
    thoughts.append(f"Thought {step_no}: 栈: {_render_stack(stack)}")
    step_no += 1

    for c in char_seq:
        if c in OPEN_SET:
            stack.append(c)
        else:
            if stack and stack[-1] == PAIR_MAP.get(c, ''):
                stack.pop()
        pos += 1
        thoughts.append(f"Thought {step_no}: {c} ; 栈: {_render_stack(stack)}")
        step_no += 1

        if random.random() < 0.35:
            thoughts.append(f"Thought {step_no}: 深度: {len(stack)}")
            step_no += 1
        if random.random() < 0.35:
            parity = "偶" if (len(stack) % 2 == 0) else "奇"
            thoughts.append(f"Thought {step_no}: 深度奇偶: {parity}")
            step_no += 1
        if random.random() < 0.35:
            cat = "空" if not stack else CAT_LABEL.get(stack[-1], "空")
            thoughts.append(f"Thought {step_no}: 栈顶类别: {cat}")
            step_no += 1
        if random.random() < 0.35:
            thoughts.append(f"Thought {step_no}: 指针: {pos}")
            step_no += 1
        if random.random() < 0.35:
            nxt = "终止" if pos >= len(char_seq) else char_seq[pos]
            thoughts.append(f"Thought {step_no}: 下一个字符: {nxt}")
            step_no += 1
        if random.random() < 0.25:
            thoughts.append(f"Thought {step_no}: 栈: {_render_stack(stack)}")
            step_no += 1
        if random.random() < 0.2:
            thoughts.append(f"Thought {step_no}: {_comment_line()}")
            step_no += 1

    final_prefixes = [
        "现在，我们已经到达结尾。",
        "至此，我们处理完所有字符。",
        "到这里，所有括号均已检查完毕。"
    ]
    final_preamble = random.choice(final_prefixes)
    thoughts.append(f"Thought {step_no}: {final_preamble}最终栈是空的。")
    return thoughts

def _rules_desc_with_types(types: List[Tuple[str, str]]) -> str:
    return _rules_desc(types)

def generate_instance() -> Dict[str, Any]:
    """
    Generate a full instance with enhanced randomness and aligned rules text.
    """
    for _ in range(50):
        types = _choose_bracket_types()
        n_pairs = random.randint(6, 20)
        chars = _gen_balanced_sequence(n_pairs, types)
        bracket_str = _insert_fillers(chars)

        thoughts_ok = _build_correct_thoughts(bracket_str, types)

        max_total_err = random.choice([0, 1, 2, 3, 4])
        wrong_claim_quota = random.randint(0, min(2, max_total_err))
        remain = max_total_err - wrong_claim_quota
        invalid_char_quota = random.randint(0, min(2, remain))
        remain -= invalid_char_quota
        premature_final_quota = random.randint(0, min(2, remain))
        remain -= premature_final_quota
        extra_claim_wrong_quota = max(0, remain)

        thoughts_1, _ = _inject_wrong_stack_claims(thoughts_ok, types, wrong_claim_quota)
        thoughts_2 = _insert_invalid_char_steps(thoughts_1, invalid_char_quota)
        thoughts_3 = _insert_premature_final(thoughts_2, premature_final_quota)
        thoughts_4 = _inject_wrong_extra_claims(thoughts_3, extra_claim_wrong_quota)
        thoughts_final = _renumber_thoughts(thoughts_4)

        detected = detect_reasoning_errors(bracket_str, thoughts_final)
        rules_desc = _rules_desc_with_types(types)

        return {
            "input_str": bracket_str,
            "thoughts": thoughts_final,
            "rules_desc": rules_desc,
            "answer_list": detected[:],
            "answer_str": format_output(detected)
        }

    # Fallback: no errors
    types = [('(', ')'), ('{', '}'), ('[', ']')]
    chars = _gen_balanced_sequence(8, types)
    bracket_str = _insert_fillers(chars)
    thoughts_ok = _build_correct_thoughts(bracket_str, types)
    rules_desc = _rules_desc_with_types(types)
    detected = detect_reasoning_errors(bracket_str, thoughts_ok)
    return {
        "input_str": bracket_str,
        "thoughts": thoughts_ok,
        "rules_desc": rules_desc,
        "answer_list": detected[:],
        "answer_str": format_output(detected)
    }

def scenario_get(scenario: Dict[str, Any], key: str) -> Any:
    """Safe dict getter for YAML formulas."""
    return scenario.get(key)

def join_thoughts(thoughts: List[str]) -> str:
    """Join all thoughts into a single line for compact display."""
    return " | ".join(thoughts)

def validate_instance_with_string(input_str: str, raw_thoughts: List[str], ans_str: str) -> bool:
    """
    Validate correctness: recompute error steps and compare to provided answer string.
    Also time-bound to ensure efficiency (< 180 seconds).
    """
    start = time.time()
    recomputed = format_output(detect_reasoning_errors(input_str, raw_thoughts))
    ok = (recomputed == ans_str)
    return ok and ((time.time() - start) < 180.0)