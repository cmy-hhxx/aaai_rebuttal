import sys, json, random, re
from typing import List, Tuple, Dict, Any, Optional

BR_OPEN = "([{<"
BR_CLOSE = ")]}>"
PAIR = dict(zip(BR_OPEN, BR_CLOSE))
REV = dict(zip(BR_CLOSE, BR_OPEN))

def render_stack(stack: List[str], style: str) -> str:
    """
    style:
      - "concat": directly concatenate, e.g., "{(["
      - "spaced": join with space, e.g., "{ ( ["
      - "doublebrace_bug": replace "{" with "{{" occasionally (simulates common mistake)
    """
    if style == "spaced":
        return " ".join(stack)
    if style == "doublebrace_bug":
        s = "".join(stack)
        # only affects braces in rendering, not the underlying stack
        return s.replace("{", "{{")
    return "".join(stack)

def correct_pushpop(stack: List[str], ch: str) -> Tuple[bool, List[str]]:
    """Returns (ok, new_stack) under correct Dyck stack processing."""
    st = stack[:]
    if ch in BR_OPEN:
        st.append(ch)
        return True, st
    if ch in BR_CLOSE:
        if not st:
            return False, st
        top = st[-1]
        if PAIR.get(top) != ch:
            return False, st
        st.pop()
        return True, st
    return False, st

def gen_balanced_sequence(rng: random.Random, n_pairs: int, allow_types: List[str]) -> str:
    """
    Generate a balanced bracket sequence with multiple types using a constructive random walk:
    maintain a stack of opens; at each step either open or close validly.
    """
    opens = allow_types
    seq = []
    stack = []
    opens_left = n_pairs
    closes_left = n_pairs
    for _ in range(2 * n_pairs):
        # decide open vs close; must ensure closable if no opens_left or stack empty
        can_open = opens_left > 0
        can_close = bool(stack) and closes_left > 0
        if not can_close:
            choose_open = True
        elif not can_open:
            choose_open = False
        else:
            # bias slightly to opening early, closing later
            # but keep variability
            choose_open = rng.random() < (0.55 if len(stack) < 3 else 0.45)

        if choose_open:
            o = rng.choice(opens)
            seq.append(o)
            stack.append(o)
            opens_left -= 1
        else:
            o = stack.pop()
            seq.append(PAIR[o])
            closes_left -= 1
    return "".join(seq)

def make_segmented_sequence(rng: random.Random) -> str:
    """
    Make a sequence comprised of several balanced segments to mimic realistic inputs like seed.
    """
    types_pool = list(BR_OPEN)
    rng.shuffle(types_pool)
    # choose which bracket types to include this time (2..4)
    k = rng.randint(2, 4)
    allow_types = types_pool[:k]

    seg_count = rng.randint(3, 7)
    segs = []
    total_pairs = 0
    for _ in range(seg_count):
        pairs = rng.randint(1, 6)
        total_pairs += pairs
        segs.append(gen_balanced_sequence(rng, pairs, allow_types))
    # optionally wrap some segments in an outer pair to add nesting variety
    if rng.random() < 0.55:
        outer = rng.choice(allow_types)
        inner = "".join(segs)
        return outer + inner + PAIR[outer]
    return "".join(segs)

def correct_trace(sequence: str) -> List[Tuple[int, str, List[str], bool]]:
    """
    Returns list of steps for each character:
    (step_no, char, correct_stack_after, ok)
    step_no starts at 3 (because Thought 1 and 2 are meta/initial).
    """
    steps = []
    stack = []
    step_no = 3
    for ch in sequence:
        ok, new_stack = correct_pushpop(stack, ch)
        stack = new_stack
        steps.append((step_no, ch, stack[:], ok))
        step_no += 1
    return steps

def inject_errors(
    rng: random.Random,
    trace: List[Tuple[int, str, List[str], bool]],
    max_errors: int = 4
) -> Tuple[List[Tuple[int, str, str]], List[int], str]:
    """
    Build a "Thought" list corresponding to each character step but with some incorrect stack renderings.
    Returns:
      rendered_steps: list of (step_no, char, rendered_stack_string)
      error_steps: list of step_nos that are incorrect
      final_claim_stack_string: what the final thought claims
    Note: We keep the sequence fixed; we only corrupt the reasoning/stack depiction.
    """
    # Decide error count (including potential final summary error)
    err_cnt = rng.randint(0, max_errors)
    # possible error types
    # 1) push wrong open symbol
    # 2) pop when should push
    # 3) keep extra leftover
    # 4) wrong close effect (pop wrong / push ghost)
    # 5) rendering glitch (doublebrace) - counts as error if depiction differs
    # We'll ensure chosen steps are within character steps unless final summary chosen.
    step_nos = [t[0] for t in trace]
    # Choose unique steps to corrupt; reserve possibility to corrupt final summary separately.
    corrupt_final = False
    if err_cnt > 0 and rng.random() < 0.35:
        corrupt_final = True
        err_cnt_steps = err_cnt - 1
    else:
        err_cnt_steps = err_cnt
    corrupt_steps = set(rng.sample(step_nos, k=err_cnt_steps)) if err_cnt_steps > 0 else set()

    # We'll simulate the student's stated stack, starting empty.
    stated_stack: List[str] = []
    rendered_steps: List[Tuple[int, str, str]] = []
    error_steps: List[int] = []

    # choose per-problem rendering style baseline
    base_style = rng.choice(["concat", "spaced"])
    for step_no, ch, correct_after, ok in trace:
        # apply correct transition to stated stack unless we corrupt this step
        before = stated_stack[:]
        if step_no not in corrupt_steps:
            ok2, after2 = correct_pushpop(stated_stack, ch)
            # even if sequence is correct, ok2 should be True; keep it
            stated_stack = after2
            # baseline render
            rendered = render_stack(stated_stack, base_style)
            rendered_steps.append((step_no, ch, rendered))
            continue

        # corrupt this step: choose a corruption that actually changes the depicted stack
        # Try multiple attempts to ensure difference.
        for _ in range(20):
            stated_stack = before[:]  # reset
            etype = rng.choice(["push_wrong", "pop_instead_of_push", "push_instead_of_pop",
                                "pop_wrong_depth", "ghost_append", "render_glitch"])
            if etype == "push_wrong":
                if ch in BR_OPEN:
                    wrong = rng.choice([o for o in BR_OPEN if o != ch])
                    stated_stack.append(wrong)
                else:
                    # if close, pretend it matched and pop (even if it shouldn't) or push opener
                    if stated_stack:
                        stated_stack.pop()
                    else:
                        stated_stack.append(rng.choice(BR_OPEN))
            elif etype == "pop_instead_of_push":
                if ch in BR_OPEN:
                    if stated_stack:
                        stated_stack.pop()
                    else:
                        # can't pop empty; do something else wrong
                        stated_stack.append(rng.choice(BR_OPEN))
                else:
                    # close but instead of popping, push something
                    stated_stack.append(rng.choice(BR_OPEN))
            elif etype == "push_instead_of_pop":
                if ch in BR_CLOSE:
                    stated_stack.append(rng.choice(BR_OPEN))
                else:
                    # open but also push an extra
                    stated_stack.append(ch)
                    stated_stack.append(rng.choice(BR_OPEN))
            elif etype == "pop_wrong_depth":
                if ch in BR_CLOSE and len(stated_stack) >= 2:
                    # pop two instead of one
                    stated_stack.pop()
                    stated_stack.pop()
                else:
                    # fallback: remove top if possible else push
                    if stated_stack:
                        stated_stack.pop()
                    else:
                        stated_stack.append(rng.choice(BR_OPEN))
            elif etype == "ghost_append":
                # perform correct transition then add/remove one random element
                ok2, after2 = correct_pushpop(stated_stack, ch)
                stated_stack = after2
                if rng.random() < 0.5 and stated_stack:
                    stated_stack.pop()
                else:
                    stated_stack.append(rng.choice(BR_OPEN))
            elif etype == "render_glitch":
                # keep correct stack but render in a way that changes textual depiction (counts as error)
                ok2, after2 = correct_pushpop(stated_stack, ch)
                stated_stack = after2
                # Use a glitch style rendering that is different if any '{' exists, else force spacing mismatch
                glitch_style = "doublebrace_bug" if "{" in stated_stack else ("spaced" if base_style == "concat" else "concat")
                rendered = render_stack(stated_stack, glitch_style)
                # Compare to correct textual rendering under base_style
                correct_txt = render_stack(correct_after, base_style)
                if rendered != correct_txt:
                    rendered_steps.append((step_no, ch, rendered))
                    error_steps.append(step_no)
                    break
                else:
                    continue

            # render under base style
            rendered = render_stack(stated_stack, base_style)
            # compute what correct text would be under base style
            correct_txt = render_stack(correct_after, base_style)
            if rendered != correct_txt:
                rendered_steps.append((step_no, ch, rendered))
                error_steps.append(step_no)
                break
        else:
            # If we failed to create a visible difference, fall back to a guaranteed difference:
            ok2, after2 = correct_pushpop(before, ch)
            stated_stack = after2
            rendered = render_stack(stated_stack, "spaced" if base_style == "concat" else "concat")
            rendered_steps.append((step_no, ch, rendered))
            error_steps.append(step_no)

    # final claim about ending
    # correct final stack is whatever correct trace ends with
    correct_final_stack = trace[-1][2] if trace else []
    correct_final_txt = render_stack(correct_final_stack, base_style)
    final_claim = correct_final_txt
    if corrupt_final:
        # make it wrong: claim empty when non-empty or claim non-empty when empty
        if correct_final_stack:
            final_claim = ""  # claim empty
        else:
            # claim one opener left
            final_claim = rng.choice(BR_OPEN)
        # mark an error as a pseudo step "end", but we must output step numbers from Thoughts.
        # We'll encode final summary as Thought (last_step_no+1). This matches the style in seed.
        # Add that to errors.
        last_step_no = trace[-1][0] if trace else 2
        error_steps.append(last_step_no + 1)

    error_steps = sorted(set(error_steps))
    return rendered_steps, error_steps, final_claim

def build_problem_text(sequence: str, rendered_steps: List[Tuple[int, str, str]], final_claim: str, output_language: str) -> str:
    assert output_language == "zh"
    lines = []
    lines.append("你是一位精通 Dyck 语言的专家，需要根据 Dyck 语言规则检查括号序列的配对推理是否正确。")
    lines.append("")
    lines.append(f"输入：{sequence}")
    lines.append("Thought 1: 我们应该逐个处理输入并跟踪栈的配置。")
    lines.append("Thought 2: 栈：空")
    for step_no, ch, stxt in rendered_steps:
        # normalize empty rendering
        st_show = "空" if stxt == "" else stxt
        lines.append(f"Thought {step_no}: {ch} ; 栈: {st_show}")
    # final summary thought number = last step + 1
    last_step = rendered_steps[-1][0] if rendered_steps else 2
    final_show = "空" if final_claim == "" else final_claim
    lines.append(f"Thought {last_step+1}: 现在，我们已经到达结尾。最终栈是{final_show}。")
    lines.append("问题：这个序列中有推理错误吗？如果没有错误，请直接输出空字符串\"\"；如果有错误，请直接输出错误步骤的编号，错误出现在\"Thought N\"中。")
    lines.append("")
    lines.append("附加条件：如果有多个错误，请按格式输出：1,3,9")
    return "\n".join(lines)

def solve_errors_from_text(sequence: str, rendered_steps: List[Tuple[int, str, str]], final_claim: str) -> List[int]:
    """
    Independently compute which Thought steps are wrong by comparing against correct processing.
    Treat stack textual format as exact (after mapping '空' -> '').
    """
    trace = correct_trace(sequence)
    # map step_no -> correct stack string in both concat and spaced? No: the problem's depiction uses one format.
    # But in generation we already used a single base format; here we infer the format by observing any non-empty stack render.
    # We'll just compare to the provided rendered strings exactly, using the same base by deriving from the first non-empty:
    provided = {sno: stxt for sno, _, stxt in rendered_steps}

    # Determine whether stacks are spaced format
    spaced = any((" " in v) for v in provided.values())
    base_style = "spaced" if spaced else "concat"

    errors = []
    for step_no, ch, correct_after, ok in trace:
        correct_txt = render_stack(correct_after, base_style)
        if provided.get(step_no, None) != correct_txt:
            errors.append(step_no)

    # final summary step number:
    last_step = trace[-1][0] if trace else 2
    final_step_no = last_step + 1
    correct_final_stack = trace[-1][2] if trace else []
    correct_final_txt = render_stack(correct_final_stack, base_style)
    if final_claim != correct_final_txt:
        errors.append(final_step_no)

    return sorted(set(errors))

def make_one(rng: random.Random, output_language: str) -> Dict[str, Any]:
    # Generate a valid balanced sequence; ensure includes at least 2 bracket types for interest.
    for _ in range(200):
        seq = make_segmented_sequence(rng)
        # quick sanity: it should be balanced under correct processing
        tr = correct_trace(seq)
        if tr and all(ok for (_, _, _, ok) in tr) and tr[-1][2] == []:
            # ensure at least 2 types appear
            types_used = set([c for c in seq if c in BR_OPEN])
            if len(types_used) >= 2:
                trace = tr
                break
    else:
        raise RuntimeError("生成平衡序列失败")

    rendered_steps, err_steps, final_claim = inject_errors(rng, trace, max_errors=4)

    # Cross-validate by independently solving from the rendered data
    solved = solve_errors_from_text(seq, rendered_steps, final_claim)
    if solved != err_steps:
        # If mismatch due to rare format inference, force to solved as source of truth.
        err_steps = solved

    problem = build_problem_text(seq, rendered_steps, final_claim, output_language)
    answer = "" if len(err_steps) == 0 else ",".join(str(x) for x in err_steps)

    # Provide a short, checkable explanation: show the first few mismatching steps and the correct stack there.
    trace_map = {sno: st for (sno, _, st, _) in trace}
    provided_map = {sno: stxt for (sno, _, stxt) in rendered_steps}
    # infer style
    spaced = any((" " in v) for v in provided_map.values())
    base_style = "spaced" if spaced else "concat"

    if not err_steps:
        explanation = "按 Dyck 栈规则逐步处理，所有步骤给出的栈状态都与正确栈一致，且最终栈为空，因此没有推理错误。"
    else:
        parts = []
        for sno in err_steps[:3]:
            if sno in trace_map:
                correct_txt = render_stack(trace_map[sno], base_style)
                got = provided_map.get(sno, "(缺失)")
                parts.append(f"Thought {sno}：正确栈应为{('空' if correct_txt=='' else correct_txt)}，但题中给出{('空' if got=='' else got)}。")
            else:
                # final summary
                last_sno = max(trace_map.keys()) if trace_map else 2
                final_step = last_sno + 1
                if sno == final_step:
                    correct_final = render_stack([], base_style)  # should be empty for balanced seq
                    parts.append(f"Thought {sno}：序列平衡时最终栈应为空，但题中最终栈声明不一致。")
        explanation = "错误步骤编号为：" + ",".join(map(str, err_steps)) + "。示例核对：" + " ".join(parts)

    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    raw = sys.stdin.read()
    try:
        obj = json.loads(raw)
        seed = int(obj["seed"])
        count = int(obj["count"])
    except Exception as e:
        print(f"输入 JSON 解析失败：{e}", file=sys.stderr)
        sys.exit(1)
    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    output_language = "zh"

    items = []
    seen = set()
    attempts = 0
    # ensure diversity and avoid duplicates
    while len(items) < count and attempts < 5000:
        attempts += 1
        it = make_one(rng, output_language)
        key = (it["problem"], json.dumps(it["answer"], ensure_ascii=False))
        if key in seen:
            continue
        seen.add(key)
        items.append(it)

    if len(items) < count:
        print(f"生成不足：需要 {count}，实际 {len(items)}。", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(items, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()