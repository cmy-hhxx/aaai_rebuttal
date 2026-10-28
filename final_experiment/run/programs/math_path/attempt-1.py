import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

OPS = ["+", "-", "*", "%"]

def eval_expr(tokens: List[str]) -> int:
    """Evaluate with precedence: * and % before + and -, left-associative."""
    prec = {"+": 1, "-": 1, "*": 2, "%": 2}
    output = []
    stack = []
    for tok in tokens:
        if tok.isdigit():
            output.append(tok)
        else:
            while stack and prec.get(stack[-1], 0) >= prec[tok]:
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
    parts = []
    for t in tokens:
        if t in OPS:
            parts.append(f" {t} ")
        else:
            parts.append(t)
    return "".join(parts)

def template_to_problem(template_tokens: List[str], target: int, lang: str) -> str:
    expr_with_q = [("?" if t == "D" else t) for t in template_tokens]
    expr_str = tokens_to_str(expr_with_q)
    if lang == "zh":
        return (
            f"现给出运算表达式 {expr_str} = {target}，等号左边的数字位置上是问号，"
            f"且每个问号代表 0 - 9 中的一个数字。请你把问号替换成合适数字，完成表达式的还原。\n\n"
            f"请在回答的末尾，将填充完整的运算表达式，放到 [[ 与 ]] 中间，无需其他内容，形如：\n"
            f"[[2 + 4 * 3 - 4 = 10]]"
        )
    return (
        f"Fill digits (0-9) into the '?' in {expr_str} = {target} to make it true.\n\n"
        f"Put the completed expression between [[ and ]], e.g. [[2 + 4 * 3 - 4 = 10]]"
    )

def instantiate(template_tokens: List[str], digits: List[int]) -> List[str]:
    out = []
    it = iter(digits)
    for t in template_tokens:
        out.append(str(next(it)) if t == "D" else t)
    return out

def gen_easy_template(rng: random.Random) -> List[str]:
    """
    Create a template that is easy to make uniquely solvable by construction.

    Form:
      D - D + ( D % D ) * C1 % D * C2 % C3 % D % D
    We render without parentheses (since precedence already makes it work):
      D - D + D % D * C1 % D * C2 % C3 % D % D

    Many constants included to keep style close to seed.
    """
    C1 = str(rng.choice([1, 2, 3, 4, 5]))
    C2 = str(rng.choice([2, 3, 4, 5, 6, 7]))
    C3 = str(rng.choice([2, 3, 4, 5, 6, 7, 8, 9]))
    # Ensure enough % and * present; 7 digits total.
    return ["D", "-", "D", "+", "D", "%", "D", "*", C1, "%", "D", "*", C2, "%", C3, "%", "D", "%", "D"]

def solve_with_enumeration(template: List[str], target: int, max_solutions: int = 2) -> List[List[int]]:
    k = sum(1 for t in template if t == "D")
    # k is fixed at 7 in our template
    sols = []
    digits = [0] * k

    # determine which digit indices are mod denominators (right operands of %)
    digit_positions = [i for i, t in enumerate(template) if t == "D"]
    denom_indices = set()
    for i, t in enumerate(template):
        if t == "%" and i + 1 < len(template) and template[i + 1] == "D":
            pos = i + 1
            denom_indices.add(digit_positions.index(pos))

    def rec(i: int):
        if len(sols) >= max_solutions:
            return
        if i == k:
            try:
                if eval_expr(instantiate(template, digits)) == target:
                    sols.append(digits.copy())
            except ZeroDivisionError:
                return
            return
        # keep denominators non-zero
        start = 1 if i in denom_indices else 0
        for d in range(start, 10):
            digits[i] = d
            rec(i + 1)
            if len(sols) >= max_solutions:
                return

    rec(0)
    return sols

def make_unique_instance(rng: random.Random, lang: str) -> Dict[str, Any]:
    """
    Reliable generation strategy:
    - sample a fixed-size template (k=7 digits) so uniqueness check is always feasible (<= 10^7 worst; but we prune denom=0).
    - sample digits, compute target, then enumerate to confirm unique solution.
    - enforce small target range for readability.
    """
    for _ in range(2000):
        template = gen_easy_template(rng)

        # sample a candidate solution first to set the target
        k = sum(1 for t in template if t == "D")
        # compute denom indices
        digit_positions = [i for i, t in enumerate(template) if t == "D"]
        denom_indices = set()
        for i, t in enumerate(template):
            if t == "%" and i + 1 < len(template) and template[i + 1] == "D":
                denom_indices.add(digit_positions.index(i + 1))

        digits = []
        for i in range(k):
            if i in denom_indices:
                digits.append(rng.randint(1, 9))
            else:
                digits.append(rng.randint(0, 9))

        try:
            target = eval_expr(instantiate(template, digits))
        except ZeroDivisionError:
            continue

        # Keep target modest
        if not (-30 <= target <= 30):
            continue

        # Enumerate to ensure uniqueness
        sols = solve_with_enumeration(template, target, max_solutions=2)
        if len(sols) != 1:
            continue

        sol = sols[0]
        inst_tokens = instantiate(template, sol)
        expr_filled = tokens_to_str(inst_tokens)
        answer_expr = f"{expr_filled} = {target}"

        problem = template_to_problem(template, target, lang)
        explanation = (
            "唯一解可通过穷举每个问号取 0-9（其中作为取模 % 的右操作数的问号不能为 0）并逐一代入验证得到。"
            f"该题的可行填法只有一种，代入后等号左边计算结果为 {target}。\n\n"
            f"[[{answer_expr}]]"
        )
        return {"problem": problem, "answer": f"[[{answer_expr}]]", "explanation": explanation}

    raise RuntimeError("Failed to generate a unique instance within attempt limit.")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    lang = data.get("output_language", "zh")

    rng = random.Random(seed)
    out = []
    seen = set()

    for _ in range(count * 200):
        if len(out) >= count:
            break
        item = make_unique_instance(rng, lang)
        if item["problem"] in seen:
            continue
        seen.add(item["problem"])
        out.append(item)

    if len(out) != count:
        print(f"Only generated {len(out)} items out of requested {count}.", file=sys.stderr)
        raise SystemExit(1)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()