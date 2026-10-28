import sys, json, random
from typing import List, Tuple, Dict, Any

# --------- Core generator ---------

def mat_to_latex(M: List[List[int]]) -> str:
    # Render as LaTeX pmatrix
    rows = ["  " + " & ".join(str(x) for x in row) for row in M]
    body = " \\\\\n".join(rows)
    return "\\[\n\\begin{pmatrix}\n" + body + "\n\\end{pmatrix}\n\\]"

def mat_to_answer_format(M: List[List[int]]) -> str:
    # Required format: [[((a,b),(c,d))]] for 2x2
    (a, b), (c, d) = M
    return f"[[(({a},{b}),({c},{d}))]]"

def elemwise_power(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    out = []
    for i in range(2):
        row = []
        for j in range(2):
            row.append(int(pow(A[i][j], B[i][j])))
        out.append(row)
    return out

def sample_matrix_A(rng: random.Random) -> List[List[int]]:
    # Keep bases mostly small to avoid huge numbers in output.
    # Allow some 0/1 to create edge-cases (0^0 excluded by B constraints below).
    def sample_base():
        # Weighted: more in 2..9, some in 0..1, occasional in 10..12
        p = rng.random()
        if p < 0.10:
            return rng.randint(0, 1)
        elif p < 0.95:
            return rng.randint(2, 9)
        else:
            return rng.randint(10, 12)

    A = [[sample_base(), sample_base()],
         [sample_base(), sample_base()]]
    return A

def sample_matrix_B(rng: random.Random, A: List[List[int]]) -> List[List[int]]:
    # Exponents: allow 0..5, but avoid 0^0 case.
    # Also avoid too large results: if base>=10, limit exponent to <=3.
    B = [[0, 0], [0, 0]]
    for i in range(2):
        for j in range(2):
            base = A[i][j]
            max_e = 5
            if base >= 10:
                max_e = 3
            e = rng.randint(0, max_e)
            if base == 0 and e == 0:
                # avoid undefined/ambiguous 0^0 in typical school arithmetic
                e = rng.randint(1, max_e) if max_e >= 1 else 1
            B[i][j] = e
    return B

def problem_text(A: List[List[int]], B: List[List[int]], variant: int, lang: str = "zh") -> str:
    assert lang == "zh"
    # Several phrasings / scenarios (L1)
    A_ltx = mat_to_latex(A)
    B_ltx = mat_to_latex(B)

    if variant == 0:
        return (
            "你是一名擅长计算自定义矩阵运算的助手。下面给出一个自定义运算规则，请按规则计算。\n\n"
            "### 运算规则\n"
            "对同型矩阵 A 与 B，定义 A&B 为逐元素幂运算：\n"
            "(A & B)_{ij} = A_{ij}^{B_{ij}}。\n\n"
            "### 题目\n"
            "给定\n"
            f"1: A=\n{A_ltx}\n"
            f"B=\n{B_ltx}\n"
            "计算 A&B。\n"
            "答案是一个 2×2 矩阵，请写成这种形式：[[((a,b),(c,d))]]。\n"
        )
    elif variant == 1:
        return (
            "请根据如下定义计算一个新的矩阵运算。\n\n"
            "定义：若 A、B 为 2×2 矩阵，则 A&B 表示把对应位置的元素做幂：\n"
            "A&B = [[A_{11}^{B_{11}}, A_{12}^{B_{12}}],[A_{21}^{B_{21}}, A_{22}^{B_{22}}]]。\n\n"
            "已知\n"
            f"A=\n{A_ltx}\n"
            f"B=\n{B_ltx}\n"
            "求 A&B，并按 [[((a,b),(c,d))]] 输出。\n"
        )
    elif variant == 2:
        return (
            "自定义运算 “&” 作用于两个同型矩阵：在每个位置 (i,j) 上，把 A_{ij} 作为底数、B_{ij} 作为指数，计算 A_{ij}^{B_{ij}}。\n\n"
            "现在给出 2×2 矩阵\n"
            f"A=\n{A_ltx}\n"
            f"B=\n{B_ltx}\n"
            "请计算 A&B，按 [[((a,b),(c,d))]] 形式作答。\n"
        )
    else:
        return (
            "设 “&” 为一种逐元素运算：对矩阵 A、B，(A&B)_{ij}=A_{ij}^{B_{ij}}。\n\n"
            "给定\n"
            f"A=\n{A_ltx}\n"
            f"B=\n{B_ltx}\n"
            "求 A&B（2×2），用 [[((a,b),(c,d))]] 表示。\n"
        )

def explanation_text(A: List[List[int]], B: List[List[int]], C: List[List[int]], lang: str = "zh") -> str:
    assert lang == "zh"
    parts = []
    for i in range(2):
        for j in range(2):
            parts.append(f"位置({i+1},{j+1})：{A[i][j]}^{B[i][j]}={C[i][j]}")
    return "按定义逐元素计算幂：\n" + "；".join(parts) + "。"

def generate_one(rng: random.Random, lang: str) -> Dict[str, Any]:
    # sample until passes sanity checks
    for _ in range(200):
        A = sample_matrix_A(rng)
        B = sample_matrix_B(rng, A)
        C = elemwise_power(A, B)

        # Additional validation: ensure numbers are not astronomically large
        # (keep output readable)
        max_val = max(C[0][0], C[0][1], C[1][0], C[1][1])
        if max_val > 10**6:
            continue

        variant = rng.randint(0, 3)
        prob = problem_text(A, B, variant, lang=lang)
        ans = mat_to_answer_format(C)
        expl = explanation_text(A, B, C, lang=lang)

        # Cross-check (independent-ish): recompute with explicit multiplication loop for power
        # without using pow directly (still deterministic).
        C2 = [[1, 1], [1, 1]]
        ok = True
        for i in range(2):
            for j in range(2):
                base, exp = A[i][j], B[i][j]
                val = 1
                # exp is small (<=5), so loop is safe
                for _k in range(exp):
                    val *= base
                if exp == 0:
                    val = 1  # by convention for nonzero base; we avoided 0^0
                if base == 0 and exp > 0:
                    val = 0
                if val != C[i][j]:
                    ok = False
                    break
                C2[i][j] = val
            if not ok:
                break
        if not ok:
            continue

        return {"problem": prob, "answer": ans, "explanation": expl}

    raise RuntimeError("在采样上限内未能生成满足约束的题目实例。")

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        print(f"输入不是合法 JSON：{e}", file=sys.stderr)
        raise

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))
    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        raise SystemExit(1)

    rng = random.Random(seed)

    # language is fixed by user request in this run; generator keeps it internal
    lang = "zh"

    out = []
    seen = set()
    # Avoid duplicates by (A,B) signature
    for _ in range(count * 50):
        if len(out) >= count:
            break
        item = generate_one(rng, lang=lang)
        sig = item["problem"]
        if sig in seen:
            continue
        seen.add(sig)
        out.append(item)

    if len(out) != count:
        print(f"生成数量不足：需要 {count}，实际 {len(out)}", file=sys.stderr)
        raise SystemExit(2)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()