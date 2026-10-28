import sys, json, random
from typing import List, Dict, Any, Tuple, Optional

OPS = ["+", "-", "*", "%"]

def eval_expr(tokens: List[str]) -> int:
    """Evaluate expression with precedence (*,%) > (+,-), left-associative."""
    prec = {"+": 1, "-": 1, "*": 2, "%": 2}
    out = []
    st = []
    for tok in tokens:
        if tok.isdigit():
            out.append(tok)
        else:
            while st and prec.get(st[-1], 0) >= prec[tok]:
                out.append(st.pop())
            st.append(tok)
    while st:
        out.append(st.pop())

    vs = []
    for tok in out:
        if tok.isdigit():
            vs.append(int(tok))
        else:
            b = vs.pop()
            a = vs.pop()
            if tok == "+":
                vs.append(a + b)
            elif tok == "-":
                vs.append(a - b)
            elif tok == "*":
                vs.append(a * b)
            elif tok == "%":
                if b == 0:
                    raise ZeroDivisionError
                vs.append(a % b)
            else:
                raise ValueError
    return vs[0]

def tokens_to_str(tokens: List[str]) -> str:
    s = []
    for t in tokens:
        if t in OPS:
            s.append(f" {t} ")
        else:
            s.append(t)
    return "".join(s)

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
        f"Fill digits into '?' in {expr_str} = {target}.\n\n"
        f"Put the completed expression between [[ and ]]."
    )

def instantiate(template_tokens: List[str], digits: List[int]) -> List[str]:
    it = iter(digits)
    return [str(next(it)) if t == "D" else t for t in template_tokens]

def gen_template(rng: random.Random) -> List[str]:
    """
    Fixed-shape template (7 digits) for fast uniqueness checking by enumeration:
      D - D + D % D * C1 % D * C2 % C3 % D % D
    """
    C1 = str(rng.choice([1, 2, 3, 4, 5]))
    C2 = str(rng.choice([2, 3, 4, 5, 6, 7]))
    C3 = str(rng.choice([2, 3, 4, 5, 6, 7, 8, 9]))
    return ["D", "-", "D", "+", "D", "%", "D", "*", C1, "%", "D", "*", C2, "%", C3, "%", "D", "%", "D"]

def denom_digit_indices(template: List[str]) -> Tuple[int, ...]:
    digit_positions = [i for i, t in enumerate(template) if t == "D"]
    denom = []
    for i, t in enumerate(template):
        if t == "%" and i + 1 < len(template) and template[i + 1] == "D":
            denom.append(digit_positions.index(i + 1))
    return tuple(sorted(set(denom)))

def find_unique_solution_fast(template: List[str], target: int) -> Optional[List[int]]:
    """
    Enumerate all assignments for 7 digits with pruning:
    - digits after '%' cannot be 0
    Stops once >=2 solutions found. Returns the unique solution or None.
    Typical runtime is small; worst-case bounded by ~7.3 million evaluations.
    """
    k = sum(1 for t in template if t == "D")  # should be 7
    denoms = set(denom_digit_indices(template))

    sols = 0
    unique_sol = None
    digits = [0] * k

    def rec(i: int) -> None:
        nonlocal sols, unique_sol
        if sols >= 2:
            return
        if i == k:
            try:
                v = eval_expr(instantiate(template, digits))
            except ZeroDivisionError:
                return
            if v == target:
                sols += 1
                if sols == 1:
                    unique_sol = digits.copy()
            return
        start = 1 if i in denoms else 0
        for d in range(start, 10):
            digits[i] = d
            rec(i + 1)
            if sols >= 2:
                return

    rec(0)
    return unique_sol if sols == 1 else None

def sample_solution_digits(rng: random.Random, template: List[str]) -> List[int]:
    k = sum(1 for t in template if t == "D")
    denoms = set(denom_digit_indices(template))
    ds = []
    for i in range(k):
        ds.append(rng.randint(1, 9) if i in denoms else rng.randint(0, 9))
    return ds

def make_instance(rng: random.Random, lang: str) -> Dict[str, Any]:
    """
    Make an instance with a guaranteed unique solution quickly by:
    - sampling template+digits to get a target
    - uniqueness-checking by fast capped enumeration (stop after 2 solutions)
    """
    for _ in range(400):
        template = gen_template(rng)
        sol_digits = sample_solution_digits(rng, template)
        try:
            target = eval_expr(instantiate(template, sol_digits))
        except ZeroDivisionError:
            continue
        if not (-30 <= target <= 30):
            continue

        unique = find_unique_solution_fast(template, target)
        if unique is None:
            continue

        inst_tokens = instantiate(template, unique)
        # cross-check
        if eval_expr(inst_tokens) != target:
            continue

        filled = tokens_to_str(inst_tokens)
        answer_expr = f"{filled} = {target}"
        problem = template_to_problem(template, target, lang)
        explanation = (
            "把问号依次替换成下面等式中的数字即可。可校验：将这些数字代入后，"
            "按运算优先级（先 * 与 %，后 + 与 -）从左到右计算，左边结果恰为目标值。\n\n"
            f"[[{answer_expr}]]"
        )
        return {"problem": problem, "answer": f"[[{answer_expr}]]", "explanation": explanation}

    raise RuntimeError("Failed to build instance under attempt limit.")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    lang = data.get("output_language", "zh")

    rng = random.Random(seed)
    out = []
    seen = set()

    # Hard runtime control: limit total attempts
    max_total_attempts = count * 30
    attempts = 0
    while len(out) < count and attempts < max_total_attempts:
        attempts += 1
        item = make_instance(rng, lang)
        if item["problem"] in seen:
            continue
        seen.add(item["problem"])
        out.append(item)

    if len(out) != count:
        print(f"Generation failed: produced {len(out)}/{count} within limits.", file=sys.stderr)
        raise SystemExit(1)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()