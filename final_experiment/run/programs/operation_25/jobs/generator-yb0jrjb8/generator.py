import sys, json, random
from typing import List, Tuple, Dict, Any

# --------- Utilities ---------
def mat_add(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]

def mat_scale(k, A):
    return [[k * A[i][j] for j in range(len(A[0]))] for i in range(len(A))]

def mat_mul(A, B):
    n, m, p = len(A), len(A[0]), len(B[0])
    # A: n x m, B: m x p
    return [[sum(A[i][t] * B[t][j] for t in range(m)) for j in range(p)] for i in range(n)]

def mat_transpose(A):
    return [list(row) for row in zip(*A)]

def mat_det_2x2(A):
    return A[0][0]*A[1][1] - A[0][1]*A[1][0]

def mat_trace_2x2(A):
    return A[0][0] + A[1][1]

def mat_to_answer_format_2x2(M):
    # Required format: [[((a,b),(c,d))]]
    return [[((M[0][0], M[0][1]), (M[1][0], M[1][1]))]]

def fmt_matrix_latex(A):
    # 2x2 only
    return "\\[\n\\begin{pmatrix}\n  %d & %d \\\\\n  %d & %d\n\\end{pmatrix}\n\\]" % (A[0][0], A[0][1], A[1][0], A[1][1])

def fmt_matrix_plain_2x2(A):
    return f"(({A[0][0]},{A[0][1]}),({A[1][0]},{A[1][1]}))"

def randint_nontrivial(rng, lo, hi, avoid_all_zero=True):
    while True:
        A = [[rng.randint(lo, hi) for _ in range(2)] for _ in range(2)]
        if not avoid_all_zero:
            return A
        if any(A[i][j] != 0 for i in range(2) for j in range(2)):
            return A

# --------- Problem families ---------
def family_e_linear(rng):
    """
    Define custom op: A€B = pA + qB
    Ask compute A€B for given A,B.
    """
    p = rng.randint(-4, 6)
    q = rng.randint(-4, 6)
    if p == 0 and q == 0:
        p = 1
    A = randint_nontrivial(rng, -5, 7)
    B = randint_nontrivial(rng, -5, 7)
    C = mat_add(mat_scale(p, A), mat_scale(q, B))

    problem = (
        "你将使用一个自定义矩阵运算来计算结果。请严格按规则计算。\n\n"
        "### 运算规则\n"
        f"对任意 2×2 矩阵 A,B，定义：A€B = {p}A + {q}B。\n\n"
        "### 题目\n"
        f"A=\n{fmt_matrix_latex(A)}\n"
        f"B=\n{fmt_matrix_latex(B)}\n"
        "计算 A€B。\n"
        "答案是一个矩阵，请按此形式输出：[[((a,b),(c,d))]]。\n"
    )
    answer = mat_to_answer_format_2x2(C)
    explanation = (
        f"按定义 A€B = {p}A + {q}B。\n"
        f"{p}A = {fmt_matrix_plain_2x2(mat_scale(p, A))}，"
        f"{q}B = {fmt_matrix_plain_2x2(mat_scale(q, B))}。\n"
        f"逐项相加得到 A€B = {fmt_matrix_plain_2x2(C)}。"
    )
    return problem, answer, explanation

def family_e_mix(rng):
    """
    Define custom op: A€B = pA + qB^T
    Ask compute A€B.
    """
    p = rng.randint(-3, 6)
    q = rng.randint(-3, 6)
    if p == 0 and q == 0:
        q = 2
    A = randint_nontrivial(rng, -6, 6)
    B = randint_nontrivial(rng, -6, 6)
    Bt = mat_transpose(B)
    C = mat_add(mat_scale(p, A), mat_scale(q, Bt))

    problem = (
        "下面定义一种新的 2×2 矩阵运算 €，请据此计算。\n\n"
        "### 运算规则\n"
        f"A€B = {p}A + {q}B^T，其中 B^T 表示 B 的转置。\n\n"
        "### 题目\n"
        f"A=\n{fmt_matrix_latex(A)}\n"
        f"B=\n{fmt_matrix_latex(B)}\n"
        "计算 A€B，并按此形式输出：[[((a,b),(c,d))]]。\n"
    )
    answer = mat_to_answer_format_2x2(C)
    explanation = (
        f"先求转置 B^T = {fmt_matrix_plain_2x2(Bt)}。\n"
        f"再算 {p}A = {fmt_matrix_plain_2x2(mat_scale(p, A))}，"
        f"{q}B^T = {fmt_matrix_plain_2x2(mat_scale(q, Bt))}。\n"
        f"逐项相加得到 A€B = {fmt_matrix_plain_2x2(C)}。"
    )
    return problem, answer, explanation

def family_e_with_product(rng):
    """
    Define custom op: A€B = pA + qB + r(AB)
    Ask compute A€B. (2x2)
    """
    p = rng.randint(-2, 5)
    q = rng.randint(-2, 5)
    r = rng.randint(-2, 4)
    if p == 0 and q == 0 and r == 0:
        r = 1
    A = randint_nontrivial(rng, -4, 6)
    B = randint_nontrivial(rng, -4, 6)
    AB = mat_mul(A, B)
    C = mat_add(mat_add(mat_scale(p, A), mat_scale(q, B)), mat_scale(r, AB))

    problem = (
        "请按给定的自定义矩阵运算规则计算。\n\n"
        "### 运算规则\n"
        f"A€B = {p}A + {q}B + {r}(AB)，其中 AB 表示矩阵乘法。\n\n"
        "### 题目\n"
        f"A=\n{fmt_matrix_latex(A)}\n"
        f"B=\n{fmt_matrix_latex(B)}\n"
        "计算 A€B。答案按此形式输出：[[((a,b),(c,d))]]。\n"
    )
    answer = mat_to_answer_format_2x2(C)
    explanation = (
        f"先算乘积 AB = {fmt_matrix_plain_2x2(AB)}。\n"
        f"再算 {p}A = {fmt_matrix_plain_2x2(mat_scale(p, A))}，"
        f"{q}B = {fmt_matrix_plain_2x2(mat_scale(q, B))}，"
        f"{r}(AB) = {fmt_matrix_plain_2x2(mat_scale(r, AB))}。\n"
        f"三者逐项相加得到 A€B = {fmt_matrix_plain_2x2(C)}。"
    )
    return problem, answer, explanation

def family_query_entry(rng):
    """
    Define op: A€B = pA + qB (or with transpose), but query a specific entry.
    Answer is a number.
    """
    variant = rng.choice(["linear", "transpose"])
    p = rng.randint(-5, 7)
    q = rng.randint(-5, 7)
    if p == 0 and q == 0:
        p = 2
    A = randint_nontrivial(rng, -6, 6)
    B = randint_nontrivial(rng, -6, 6)

    if variant == "linear":
        C = mat_add(mat_scale(p, A), mat_scale(q, B))
        rule_text = f"A€B = {p}A + {q}B"
        extra = ""
    else:
        Bt = mat_transpose(B)
        C = mat_add(mat_scale(p, A), mat_scale(q, Bt))
        rule_text = f"A€B = {p}A + {q}B^T"
        extra = "（其中 B^T 为转置）"

    i, j = rng.choice([(0,0),(0,1),(1,0),(1,1)])
    val = C[i][j]
    pos_text = ["(1,1)","(1,2)","(2,1)","(2,2)"][[ (0,0),(0,1),(1,0),(1,1) ].index((i,j))]

    problem = (
        "下面给出一个自定义矩阵运算 €。请计算指定位置的元素值。\n\n"
        "### 运算规则\n"
        f"{rule_text}{extra}，A,B 均为 2×2 矩阵。\n\n"
        "### 题目\n"
        f"A=\n{fmt_matrix_latex(A)}\n"
        f"B=\n{fmt_matrix_latex(B)}\n"
        f"设 C = A€B。求 C 的第 {pos_text} 个元素（按行列从 1 开始编号）。\n"
        "只输出一个整数。\n"
    )
    explanation = (
        f"由定义先得到 C=A€B = {fmt_matrix_plain_2x2(C)}，"
        f"因此第 {pos_text} 个元素为 {val}。"
    )
    return problem, val, explanation

def family_det_trace(rng):
    """
    Define op: A€B = pA + qB. Query det(A€B) or tr(A€B).
    Answer is an integer.
    """
    p = rng.randint(-4, 6)
    q = rng.randint(-4, 6)
    if p == 0 and q == 0:
        q = 1
    A = randint_nontrivial(rng, -5, 5)
    B = randint_nontrivial(rng, -5, 5)
    C = mat_add(mat_scale(p, A), mat_scale(q, B))

    query = rng.choice(["det", "tr"])
    if query == "det":
        ans = mat_det_2x2(C)
        qtext = "行列式 det(C)"
        explain_tail = f"det(C) = {C[0][0]}*{C[1][1]} - {C[0][1]}*{C[1][0]} = {ans}。"
    else:
        ans = mat_trace_2x2(C)
        qtext = "迹 tr(C)（对角线元素之和）"
        explain_tail = f"tr(C) = {C[0][0]} + {C[1][1]} = {ans}。"

    problem = (
        "请根据自定义运算计算一个 2×2 矩阵的特征量。\n\n"
        "### 运算规则\n"
        f"A€B = {p}A + {q}B。\n\n"
        "### 题目\n"
        f"A=\n{fmt_matrix_latex(A)}\n"
        f"B=\n{fmt_matrix_latex(B)}\n"
        "设 C = A€B。求 " + qtext + "。\n"
        "只输出一个整数。\n"
    )
    explanation = (
        f"先算 C = {p}A + {q}B = {fmt_matrix_plain_2x2(C)}。\n"
        + explain_tail
    )
    return problem, ans, explanation

# --------- Generation controller ---------
FAMILIES = [
    family_e_linear,
    family_e_mix,
    family_e_with_product,
    family_query_entry,
    family_det_trace,
]

def make_item(rng) -> Dict[str, Any]:
    fam = rng.choice(FAMILIES)
    problem, answer, explanation = fam(rng)
    assert isinstance(problem, str) and problem.strip()
    assert explanation is None or isinstance(explanation, str)
    return {"problem": problem, "answer": answer, "explanation": explanation}

def signature_of_item(item: Dict[str, Any]) -> str:
    # Basic dedup: normalize whitespace in problem
    p = " ".join(item["problem"].split())
    return p

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    if count <= 0:
        raise ValueError("count 必须为正整数")
    rng = random.Random(seed)

    items: List[Dict[str, Any]] = []
    seen = set()
    max_tries = 50 * count + 200
    tries = 0

    while len(items) < count and tries < max_tries:
        tries += 1
        item = make_item(rng)
        sig = signature_of_item(item)
        if sig in seen:
            continue
        seen.add(sig)
        items.append(item)

    if len(items) < count:
        print(f"生成失败：仅生成 {len(items)}/{count} 道题（已尝试 {tries} 次）", file=sys.stderr)
        raise SystemExit(2)

    json.dump(items, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()