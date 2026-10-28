import sys, json, random, math
from typing import List, Tuple, Dict, Any, Optional

# We only use standard library. (sympy, z3 are allowed but not required.)

OPS = ["+", "-", "*", "%"]

def eval_expr(tokens: List[str]) -> int:
    """
    Evaluate expression with operators + - * % and integer literals (0-9).
    Precedence: % and * before + and - ; left-associative within same precedence.
    Equivalent to Python's precedence for these ops.
    """
    # Shunting-yard to RPN then evaluate.
    prec = {"+": 1, "-": 1, "*": 2, "%": 2}
    output = []
    stack = []
    for tok in tokens:
        if tok.isdigit():
            output.append(tok)
        else:
            # operator
            while stack and stack[-1] in prec and prec[stack[-1]] >= prec[tok]:
                output.append(stack.pop())
            stack.append(tok)
    while stack:
        output.append(stack.pop())

    st = []
    for tok in output:
        if tok.isdigit():
            st.append(int(tok))
        else:
            b = st.pop()
            a = st.pop()
            if tok == "+":
                st.append(a + b)
            elif tok == "-":
                st.append(a - b)
            elif tok == "*":
                st.append(a * b)
            elif tok == "%":
                if b == 0:
                    raise ZeroDivisionError("mod by zero")
                st.append(a % b)
            else:
                raise ValueError("bad op")
    if len(st) != 1:
        raise ValueError("bad expr")
    return st[0]

def tokens_to_str(tokens: List[str]) -> str:
    # Format with spaces around operators for readability
    s = []
    for t in tokens:
        if t in OPS:
            s.append(f" {t} ")
        else:
            s.append(t)
    return "".join(s)

def template_to_problem(template_tokens: List[str], target: int, lang: str) -> str:
    expr_with_q = []
    for t in template_tokens:
        if t == "D":
            expr_with_q.append("?")
        else:
            expr_with_q.append(t)
    expr_str = tokens_to_str(expr_with_q)
    if lang == "zh":
        return (
            f"现给出运算表达式 {expr_str} = {target}，等号左边的数字位置上是问号，"
            f"且每个问号代表 0 - 9 中的一个数字。请你把问号替换成合适数字，完成表达式的还原。\n\n"
            f"请在回答的末尾，将填充完整的运算表达式，放到 [[ 与 ]] 中间，无需其他内容，形如：\n"
            f"[[2 + 4 * 3 - 4 = 10]]"
        )
    else:
        # fallback (still self-contained)
        return (
            f"Given the arithmetic expression {expr_str} = {target}, digits are replaced by question marks on the left side, "
            f"and each '?' stands for a digit 0-9. Replace them to restore a correct expression.\n\n"
            f"At the end of your answer, put the completed expression between [[ and ]], like:\n"
            f"[[2 + 4 * 3 - 4 = 10]]"
        )

def instantiate(template_tokens: List[str], digits: List[int]) -> List[str]:
    out = []
    it = iter(digits)
    for t in template_tokens:
        if t == "D":
            out.append(str(next(it)))
        else:
            out.append(t)
    return out

def gen_template(rng: random.Random, min_digits: int = 8, max_digits: int = 14) -> List[str]:
    """
    Generate token template as sequence of 'D' and operators.
    Ensure at least one % and one of +/-, and includes a couple of * / % to keep style.
    """
    n_digits = rng.randint(min_digits, max_digits)
    # Start with digit
    tokens = ["D"]
    for _ in range(n_digits - 1):
        op = rng.choice(OPS)
        tokens.append(op)
        tokens.append("D")

    # Enforce presence of %
    if "%" not in tokens:
        # replace a random operator (not first digit) with %
        op_positions = [i for i, t in enumerate(tokens) if t in OPS]
        tokens[rng.choice(op_positions)] = "%"

    # Enforce at least one + or -
    if not any(t in ["+", "-"] for t in tokens):
        op_positions = [i for i, t in enumerate(tokens) if t in OPS]
        tokens[rng.choice(op_positions)] = rng.choice(["+", "-"])

    # Encourage some multiplications
    if tokens.count("*") < 2:
        op_positions = [i for i, t in enumerate(tokens) if t in OPS]
        for _ in range(2 - tokens.count("*")):
            tokens[rng.choice(op_positions)] = "*"

    # Keep at least one % after possible replacements
    if "%" not in tokens:
        op_positions = [i for i, t in enumerate(tokens) if t in OPS]
        tokens[rng.choice(op_positions)] = "%"

    return tokens

def solve_unique_for_template(
    template_tokens: List[str],
    target: int,
    max_solutions: int = 3
) -> Tuple[bool, List[int], int]:
    """
    Brute force search for digit assignments with pruning via randomization is handled outside.
    Returns: (is_unique, digits_solution, num_found (capped at max_solutions))
    """
    # Count digits
    k = sum(1 for t in template_tokens if t == "D")

    # We do DFS with early evaluation not trivial due to precedence; so do full eval at leaf.
    # To keep budget, we will use randomized sampling outside and limited full enumeration here only for smaller k.
    # If k is small enough, do full enumeration; else refuse.
    if k > 10:
        return (False, [], 0)

    found = []
    # full enumeration 10^k may still be big; set hard cap.
    total = 10 ** k
    if total > 200000:
        return (False, [], 0)

    digits = [0] * k
    def rec(i: int):
        if len(found) >= max_solutions:
            return
        if i == k:
            try:
                val = eval_expr(instantiate(template_tokens, digits))
            except ZeroDivisionError:
                return
            if val == target:
                found.append(digits.copy())
            return
        for d in range(10):
            digits[i] = d
            rec(i + 1)
            if len(found) >= max_solutions:
                return

    rec(0)
    if len(found) == 1:
        return (True, found[0], 1)
    return (False, (found[0] if found else []), len(found))

def find_instance(rng: random.Random, lang: str) -> Dict[str, Any]:
    """
    Construct a problem instance:
    - Generate a template of digits/operators.
    - Randomly assign digits (with mod denominators forced nonzero) to create a target value.
    - Then verify uniqueness (only for manageable size). If not unique, resample.
    """
    # attempt loops with caps
    for _attempt in range(5000):
        template = gen_template(rng, 8, 14)
        k = sum(1 for t in template if t == "D")

        # Prefer manageable k for uniqueness check; else generate a "find one solution" style? But spec expects standard answer.
        # We'll enforce k <= 10 by regenerating.
        if k > 10:
            continue

        # Create digits with mod denominators non-zero.
        # Identify positions of digits that are right operands of '%'
        # template alternates D op D op D ... so digit indices correspond to positions 0,2,4,...
        digit_positions = [i for i, t in enumerate(template) if t == "D"]
        right_operand_digit_indices = set()
        for i, t in enumerate(template):
            if t == "%" and i + 1 < len(template) and template[i + 1] == "D":
                # the digit after this % is right operand
                # find which digit index it is
                pos = i + 1
                di = digit_positions.index(pos)
                right_operand_digit_indices.add(di)

        digits = []
        for di in range(k):
            if di in right_operand_digit_indices:
                digits.append(rng.randint(1, 9))
            else:
                digits.append(rng.randint(0, 9))

        # compute target
        try:
            target = eval_expr(instantiate(template, digits))
        except ZeroDivisionError:
            continue

        # Ensure target in a reasonable range for readability
        if not (-50 <= target <= 50):
            continue

        # Check uniqueness by complete enumeration (for small k and within budget)
        unique, sol, num_found = solve_unique_for_template(template, target, max_solutions=3)
        if not unique:
            continue

        # Cross-validate by re-evaluating the found solution
        inst_tokens = instantiate(template, sol)
        try:
            check_val = eval_expr(inst_tokens)
        except ZeroDivisionError:
            continue
        if check_val != target:
            continue

        expr_filled = tokens_to_str(inst_tokens)
        problem = template_to_problem(template, target, lang)
        answer = expr_filled + f" = {target}"
        explanation = (
            "将问号依次替换为下列数字即可使等式成立。代入并按运算优先级（先 % 与 *，后 + 与 -）计算，"
            f"等号左边的结果为 {target}。\n\n"
            f"[[{answer}]]"
        )
        # As requested: answer should be JSON value; keep it as string with filled expression (without extra text)
        return {
            "problem": problem,
            "answer": f"[[{answer}]]",
            "explanation": explanation
        }

    raise RuntimeError("Failed to generate a valid unique instance within attempt limit.")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    lang = data.get("output_language", "zh")

    rng = random.Random(seed)
    out = []
    seen = set()

    # bounded resampling for uniqueness of problems
    for _ in range(count * 50):
        if len(out) >= count:
            break
        item = find_instance(rng, lang)
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    if len(out) != count:
        print(f"Only generated {len(out)} items out of requested {count}.", file=sys.stderr)
        # hard fail to respect interface
        raise SystemExit(1)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()