import sys, json, random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional, Set
import itertools

# ----------------------------
# Boolean expression machinery
# ----------------------------

@dataclass(frozen=True)
class Expr:
    op: str
    args: Tuple[Any, ...]  # Any to allow str vars or Expr

def Var(name: str) -> str:
    return name

def Not(a): return Expr("NOT", (a,))
def And(a, b): return Expr("AND", (a, b))
def Or(a, b): return Expr("OR", (a, b))

def expr_vars(e) -> Set[str]:
    if isinstance(e, str):
        return {e}
    vs = set()
    for a in e.args:
        vs |= expr_vars(a)
    return vs

def eval_expr(e, env: Dict[str, bool]) -> bool:
    if isinstance(e, str):
        return env[e]
    if e.op == "NOT":
        return not eval_expr(e.args[0], env)
    if e.op == "AND":
        return eval_expr(e.args[0], env) and eval_expr(e.args[1], env)
    if e.op == "OR":
        return eval_expr(e.args[0], env) or eval_expr(e.args[1], env)
    raise ValueError("unknown op")

def to_str_zh(e) -> str:
    # Render using ¬ ∧ ∨ with parentheses where needed
    if isinstance(e, str):
        return e
    if e.op == "NOT":
        a = e.args[0]
        sa = to_str_zh(a)
        if isinstance(a, Expr) and a.op in ("AND", "OR"):
            return f"¬({sa})"
        return f"¬{sa}"
    a, b = e.args
    sa, sb = to_str_zh(a), to_str_zh(b)
    if e.op == "AND":
        # add parentheses around OR children to avoid ambiguity
        if isinstance(a, Expr) and a.op == "OR":
            sa = f"({sa})"
        if isinstance(b, Expr) and b.op == "OR":
            sb = f"({sb})"
        return f"{sa}∧{sb}"
    if e.op == "OR":
        return f"{sa}∨{sb}"
    raise ValueError("unknown op")

def all_assignments(vars_list: List[str]) -> List[Dict[str, bool]]:
    res = []
    for bits in itertools.product([False, True], repeat=len(vars_list)):
        res.append({v: b for v, b in zip(vars_list, bits)})
    return res

def pm(b: bool) -> str:
    return "+" if b else "-"

def table_for_expr(e, var_order: List[str]) -> List[List[str]]:
    # Returns rows of [I1,...,In,O] in +- symbols.
    rows = []
    for env in all_assignments(var_order):
        ins = [pm(env[v]) for v in var_order]
        out = pm(eval_expr(e, env))
        rows.append(ins + [out])
    return rows

def render_table(var_order: List[str], rows: List[List[str]]) -> str:
    header = var_order + ["O"]
    parts = []
    parts.append("[" + ",".join(header) + "]")
    for r in rows:
        parts.append("[" + ",".join(r) + "]")
    return "[" + ";".join(parts) + "]"

def render_gate_unary() -> str:
    # For NOT gate: [[I,O];[+,-];[-,+]]
    header = ["I", "O"]
    rows = [["+", "-"], ["-", "+"]]
    parts = ["[" + ",".join(header) + "]"] + ["[" + ",".join(r) + "]" for r in rows]
    return "[" + ";".join(parts) + "]"

def render_gate_binary(op: str) -> str:
    # AND / OR: list all 4 combinations in order ++,+-,-+,--
    header = ["I1", "I2", "O"]
    combos = [(True, True), (True, False), (False, True), (False, False)]
    rows = []
    for a, b in combos:
        if op == "AND":
            o = a and b
        elif op == "OR":
            o = a or b
        else:
            raise ValueError
        rows.append([pm(a), pm(b), pm(o)])
    parts = ["[" + ",".join(header) + "]"] + ["[" + ",".join(r) + "]" for r in rows]
    return "[" + ";".join(parts) + "]"

def format_output_value(single_pm: str) -> str:
    return "[[" + single_pm + "]]"

def satisfying_inputs(e, var_order: List[str], desired_out: bool) -> List[List[str]]:
    sols = []
    for env in all_assignments(var_order):
        if eval_expr(e, env) == desired_out:
            sols.append([pm(env[v]) for v in var_order])
    return sols

def render_solutions_matrix(sols: List[List[str]]) -> str:
    # Format: [[];[];…] where each [] is [+,-,+] etc.
    return "[" + ";".join("[" + ",".join(row) + "]" for row in sols) + "]"

# -------------
# Generators
# -------------

VAR_POOL = ["p", "q", "r", "s", "t"]

def random_expr(rng: random.Random, vars_list: List[str], max_depth: int) -> Any:
    # Generate a reasonably varied boolean expression using NOT/AND/OR.
    # Ensure at least 2 ops overall by biasing toward binary ops when depth allows.
    if max_depth <= 0:
        return rng.choice(vars_list)
    roll = rng.random()
    if roll < 0.25:
        # NOT
        return Not(random_expr(rng, vars_list, max_depth - 1))
    else:
        # binary
        a = random_expr(rng, vars_list, max_depth - 1)
        b = random_expr(rng, vars_list, max_depth - 1)
        if rng.random() < 0.5:
            return And(a, b)
        else:
            return Or(a, b)

def expr_complexity(e) -> int:
    if isinstance(e, str):
        return 0
    return 1 + sum(expr_complexity(a) for a in e.args)

def normalize_var_order(e, chosen_vars: List[str]) -> List[str]:
    # Use chosen_vars order but only those actually used.
    used = expr_vars(e)
    return [v for v in chosen_vars if v in used]

def make_family_A(rng: random.Random) -> Dict[str, Any]:
    # Similar to seed: multi-part with (1) gate table, (2) expression table, (3)(4) evaluate output, (5) find satisfying inputs.
    # Use 2-3 vars expression for table, and 3 vars expression for evaluation and inverse.
    # Part 1: choose gate among NOT/AND/OR with constraint that includes NOT always sometimes.
    gate_type = rng.choice(["NOT", "AND", "OR"])
    if gate_type == "NOT":
        ans1 = render_gate_unary()
    else:
        ans1 = render_gate_binary(gate_type)

    # Part 2: expression E2 over 2 vars, often with outer NOT to mirror seed but varied.
    v2 = rng.sample(VAR_POOL, 2)
    p, q = v2[0], v2[1]
    # choose a structure: ¬(p∧q), ¬(p∨q), (¬p)∨q, (p∧¬q) etc.
    templates = [
        Not(And(p, q)),
        Not(Or(p, q)),
        Or(Not(p), q),
        And(p, Not(q)),
        Or(And(p, q), Not(p)),
        And(Or(p, q), Not(p)),
    ]
    e2 = rng.choice(templates)
    vo2 = [p, q]
    rows2 = table_for_expr(e2, vo2)
    ans2 = render_table(["I1", "I2"], rows2)

    # Part 3: evaluate a binary gate (AND/OR) with given inputs
    gate3 = rng.choice(["AND", "OR"])
    i1 = rng.choice([False, True])
    i2 = rng.choice([False, True])
    out3 = (i1 and i2) if gate3 == "AND" else (i1 or i2)
    ans3 = format_output_value(pm(out3))

    # Part 4: evaluate an expression with 3 inputs
    v3 = rng.sample(VAR_POOL, 3)
    a, b, c = v3
    e4 = rng.choice([
        Or(And(a, b), And(Not(a), c)),
        Or(And(a, Not(b)), c),
        And(Or(a, b), Not(c)),
        Or(And(Not(a), b), And(a, c)),
        Not(Or(And(a, b), c)),
    ])
    vo4 = [a, b, c]
    # sample input assignment
    env4 = {a: rng.choice([False, True]), b: rng.choice([False, True]), c: rng.choice([False, True])}
    out4 = eval_expr(e4, env4)
    ans4 = format_output_value(pm(out4))

    # Part 5: find all inputs making output desired for a 3-var expression
    v5 = rng.sample(VAR_POOL, 3)
    x, y, z = v5
    e5 = rng.choice([
        Or(And(x, y), And(Not(x), Or(y, z))),
        Or(And(x, Or(y, z)), And(Not(y), z)),
        And(Or(x, Not(y)), Or(y, z)),
        Or(Not(And(x, y)), And(y, z)),
        Or(And(Not(x), Not(y)), Or(y, z)),
    ])
    desired_out = rng.choice([False, True])
    sols = satisfying_inputs(e5, [x, y, z], desired_out)
    # ensure multiple solutions; if not, flip desired or resample expression
    tries = 0
    while len(sols) < 2 and tries < 30:
        desired_out = not desired_out
        sols = satisfying_inputs(e5, [x, y, z], desired_out)
        tries += 1
        if len(sols) < 2 and tries % 6 == 0:
            e5 = random_expr(rng, [x, y, z], max_depth=3)
            if expr_complexity(e5) < 2:
                e5 = Or(e5, x)  # bump complexity a bit
            sols = satisfying_inputs(e5, [x, y, z], desired_out)

    # Build problem statement in Chinese.
    problem = []
    problem.append("你将使用“简单电路图/真值表”的记号：输入为 I（单输入）或 I1、I2、…（多输入）；有电为“+”，无电为“-”；输出为 O。")
    problem.append("请严格按指定格式作答。")
    problem.append("")
    problem.append(f"1) 请给出一个 {gate_type} 逻辑门的简单电路图，格式为 [[输入...,O];[...];...].")
    problem.append(f"2) 逻辑表达式 E = {to_str_zh(e2)}。请给出其简单电路图（真值表形式），输入按 I1={p}, I2={q}。")
    problem.append(f"3) 假设一个 {gate3} 逻辑门，I1 为“{pm(i1)}”，I2 为“{pm(i2)}”，输出是什么？格式 [[O]].")
    problem.append(f"4) 逻辑表达式 F = {to_str_zh(e4)}，其中 I1={a}, I2={b}, I3={c}。若 I1 为“{pm(env4[a])}”，I2 为“{pm(env4[b])}”，I3 为“{pm(env4[c])}”，输出是什么？格式 [[O]].")
    problem.append(f"5) 逻辑表达式 G = {to_str_zh(e5)}，其中 I1={x}, I2={y}, I3={z}。若要求输出 O 为“{pm(desired_out)}”，所有满足条件的输入(I1,I2,I3)分别是什么？格式 [[];[];…]。")

    # Answer: join with "====" like seed.
    ans5 = render_solutions_matrix(sols)
    answer = "====".join([ans1, ans2, ans3, ans4, ans5])

    # Explanation with checkable evidence
    exp = []
    exp.append("1) 逻辑门真值表按定义列出。")
    exp.append(f"2) 对 (I1,I2)=({pm(True)},{pm(True)}),({pm(True)},{pm(False)}),({pm(False)},{pm(True)}),({pm(False)},{pm(False)}) 逐一代入 E={to_str_zh(e2)} 得到对应 O，汇总成表。")
    exp.append(f"3) {gate3} 门输出为 I1 { '∧' if gate3=='AND' else '∨' } I2，因此 {pm(i1)} 与 {pm(i2)} 得 O={pm(out3)}。")
    exp.append(f"4) 代入 F={to_str_zh(e4)}：({a},{b},{c})=({pm(env4[a])},{pm(env4[b])},{pm(env4[c])})，计算得到 O={pm(out4)}。")
    exp.append(f"5) 枚举 (I1,I2,I3) 的 8 种取值，筛选使 G={to_str_zh(e5)} 输出为 {pm(desired_out)} 的所有组合。")
    explanation = "\n".join(exp)

    return {"problem": "\n".join(problem), "answer": answer, "explanation": explanation}

def make_family_B(rng: random.Random) -> Dict[str, Any]:
    # Pure table task: given expression with 3 or 4 vars, output truth table in required format.
    n = rng.choice([3, 4])
    vars_list = rng.sample(VAR_POOL, n)
    e = random_expr(rng, vars_list, max_depth=3 if n == 3 else 4)
    # ensure not too trivial
    if expr_complexity(e) < 3:
        e = Or(e, And(vars_list[0], Not(vars_list[1])))
    var_order = vars_list[:]  # as I1..In
    rows = table_for_expr(e, var_order)
    header = [f"I{i+1}" for i in range(n)]
    # render with I1..In rather than actual var names inside header
    # But we must explain mapping.
    table_str = render_table(header, rows)

    problem = []
    problem.append("你将使用“简单电路图/真值表”的记号：I1、I2、…为输入；有电为“+”，无电为“-”；输出为 O。")
    problem.append(f"给定逻辑表达式：H = {to_str_zh(e)}。其中 I1={vars_list[0]}，I2={vars_list[1]}" + (f"，I3={vars_list[2]}" if n>=3 else "") + (f"，I4={vars_list[3]}" if n==4 else "") + "。")
    problem.append("请给出对应的简单电路图（即完整真值表），格式为 [[I1,I2,...,O];[...];...].")
    answer = table_str

    # provide a couple of row checks
    exp = []
    exp.append("按 I1..In 的 2^n 种取值依次代入表达式计算 O。")
    # pick two sample rows to show
    sample_envs = [ {vars_list[i]: (i % 2 == 0) for i in range(n)},
                    {vars_list[i]: (i % 2 == 1) for i in range(n)} ]
    for idx, env in enumerate(sample_envs, 1):
        ins = ",".join(pm(env[v]) for v in vars_list)
        o = pm(eval_expr(e, env))
        exp.append(f"校验样例{idx}：({','.join(vars_list)})=({ins}) 时，O={o}。")
    explanation = "\n".join(exp)

    return {"problem": "\n".join(problem), "answer": answer, "explanation": explanation}

def make_family_C(rng: random.Random) -> Dict[str, Any]:
    # Inverse problem: give expression and require list all inputs yielding O=+ or O=-
    n = rng.choice([2, 3, 4])
    vars_list = rng.sample(VAR_POOL, n)
    e = random_expr(rng, vars_list, max_depth=3 if n <= 3 else 4)
    if expr_complexity(e) < 2:
        e = Not(And(vars_list[0], vars_list[1] if n>1 else vars_list[0]))
    desired = rng.choice([False, True])
    sols = satisfying_inputs(e, vars_list, desired)
    # ensure not empty and not all
    tries = 0
    while (len(sols) == 0 or len(sols) == (2 ** n)) and tries < 40:
        e = random_expr(rng, vars_list, max_depth=3 if n <= 3 else 4)
        desired = rng.choice([False, True])
        sols = satisfying_inputs(e, vars_list, desired)
        tries += 1
    header_map = "，".join([f"I{i+1}={vars_list[i]}" for i in range(n)])
    problem = []
    problem.append("简单电路图记号：输入 I1、I2、…；“+”表示有电，“-”表示无电；输出为 O。")
    problem.append(f"给定逻辑表达式：K = {to_str_zh(e)}（{header_map}）。")
    problem.append(f"若要求输出 O 为“{pm(desired)}”，所有满足条件的输入分别是什么？请按 [[];[];…] 输出（每行对应一组 I1..In）。")
    answer = render_solutions_matrix([[pm(env) for env in [None]]])  # placeholder overwritten below
    answer = render_solutions_matrix(sols)

    exp = []
    exp.append(f"枚举 I1..I{n} 的全部 {2**n} 种取值，计算 K 的输出，筛选输出为 {pm(desired)} 的组合。")
    if sols:
        exp.append("例如第一组满足条件的输入为：" + "[" + ",".join(sols[0]) + "]。")
    explanation = "\n".join(exp)
    return {"problem": "\n".join(problem), "answer": answer, "explanation": explanation}

# ----------------------------
# Validation & de-dup
# ----------------------------

def basic_validate_item(item: Dict[str, Any]) -> None:
    if not isinstance(item.get("problem"), str) or not item["problem"].strip():
        raise ValueError("problem empty")
    if "answer" not in item:
        raise ValueError("missing answer")
    if not isinstance(item.get("explanation"), str) or not item["explanation"].strip():
        raise ValueError("explanation empty")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    makers = [make_family_A, make_family_B, make_family_C]

    out = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        maker = rng.choices(makers, weights=[0.55, 0.25, 0.20], k=1)[0]
        item = maker(rng)
        basic_validate_item(item)

        # De-dup by hashing problem text + answer
        key = (item["problem"].strip(), json.dumps(item["answer"], ensure_ascii=False))
        if key in seen:
            continue
        seen.add(key)

        out.append(item)

    if len(out) < count:
        print(f"Failed to generate enough unique items: {len(out)}/{count}", file=sys.stderr)
        # Still output what we have to avoid silent failure, but spec wants exactly count.
        # So raise to be explicit.
        raise RuntimeError("generation_failed")

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()