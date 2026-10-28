import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

# ---------- Utilities ----------

def mat_shape(M: List[List[int]]) -> Tuple[int, int]:
    r = len(M)
    c = len(M[0]) if r > 0 else 0
    return r, c

def mat_check_rect(M: List[List[int]]) -> None:
    if not M or not M[0]:
        raise ValueError("空矩阵不允许")
    c = len(M[0])
    for row in M:
        if len(row) != c:
            raise ValueError("矩阵不是长方形（各行长度不同）")

def mat_zip_op(A: List[List[int]], B: List[List[int]], op) -> List[List[int]]:
    mat_check_rect(A); mat_check_rect(B)
    ra, ca = mat_shape(A)
    rb, cb = mat_shape(B)
    if (ra, ca) != (rb, cb):
        raise ValueError("矩阵维度不一致，无法逐元素运算")
    return [[op(A[i][j], B[i][j]) for j in range(ca)] for i in range(ra)]

def mat_max(A, B):
    return mat_zip_op(A, B, max)

def mat_min(A, B):
    return mat_zip_op(A, B, min)

def mat_add(A, B):
    return mat_zip_op(A, B, lambda x, y: x + y)

def mat_absdiff(A, B):
    return mat_zip_op(A, B, lambda x, y: abs(x - y))

def mat_to_answer_format(M: List[List[int]]) -> Any:
    # 要求外层为 [[...]]，内部为按行的 tuple 组成的 tuple，例如: [[((a,b),(c,d))]]
    rows = []
    for row in M:
        rows.append(tuple(row))
    return [[tuple(rows)]]

def mat_to_latex(M: List[List[int]]) -> str:
    mat_check_rect(M)
    lines = []
    for row in M:
        lines.append("  " + " & ".join(str(x) for x in row) + r" \\")
    if lines:
        lines[-1] = lines[-1].rstrip(" \\")  # 最后一行不强制需要 \\，但保持美观
    body = "\n".join(lines)
    return "\\[\n\\begin{pmatrix}\n" + body + "\n\\end{pmatrix}\n\\]"

def pick_dims(rng: random.Random) -> Tuple[int, int]:
    # 以 2x2 为主，但允许 2x3、3x2、3x3
    choices = [(2,2), (2,2), (2,2), (2,3), (3,2), (3,3)]
    return rng.choice(choices)

def sample_matrix(rng: random.Random, r: int, c: int, lo: int, hi: int) -> List[List[int]]:
    return [[rng.randint(lo, hi) for _ in range(c)] for _ in range(r)]

def ensure_nontrivial(A, B, kind: str) -> bool:
    # 避免题目过于无聊：确保至少有一处产生“变化”或“区别”
    if kind == "max":
        # 至少有一个位置 B > A 且至少一个位置 A > B
        gt = 0
        lt = 0
        for i in range(len(A)):
            for j in range(len(A[0])):
                if A[i][j] > B[i][j]:
                    gt += 1
                elif A[i][j] < B[i][j]:
                    lt += 1
        return gt > 0 and lt > 0
    if kind == "min":
        gt = 0
        lt = 0
        for i in range(len(A)):
            for j in range(len(A[0])):
                if A[i][j] > B[i][j]:
                    gt += 1
                elif A[i][j] < B[i][j]:
                    lt += 1
        return gt > 0 and lt > 0
    if kind == "add":
        # 至少有一个非零元素
        for row in A:
            for x in row:
                if x != 0:
                    return True
        for row in B:
            for x in row:
                if x != 0:
                    return True
        return False
    if kind == "absdiff":
        # 至少有一个位置不同
        for i in range(len(A)):
            for j in range(len(A[0])):
                if A[i][j] != B[i][j]:
                    return True
        return False
    return True

def compute_and_explain(A, B, op_name: str) -> Tuple[List[List[int]], str]:
    if op_name == "max":
        C = mat_max(A, B)
        op_cn = "逐元素取较大值（max）"
        rule = "(A ⊙ B)_{ij} = max(A_{ij}, B_{ij})"
    elif op_name == "min":
        C = mat_min(A, B)
        op_cn = "逐元素取较小值（min）"
        rule = "(A ⊙ B)_{ij} = min(A_{ij}, B_{ij})"
    elif op_name == "add":
        C = mat_add(A, B)
        op_cn = "逐元素相加（+）"
        rule = "(A ⊙ B)_{ij} = A_{ij} + B_{ij}"
    elif op_name == "absdiff":
        C = mat_absdiff(A, B)
        op_cn = "逐元素取绝对差（|·|）"
        rule = "(A ⊙ B)_{ij} = |A_{ij} - B_{ij}|"
    else:
        raise ValueError("未知运算类型")

    # 简短可核验说明：给出规则 + 至少若干位置的示例计算
    r, c = mat_shape(A)
    samples = []
    # 取最多 4 个位置做示例
    positions = [(0,0), (0, c-1), (r-1, 0), (r-1, c-1)]
    seen = set()
    for (i, j) in positions:
        if (i, j) in seen:
            continue
        seen.add((i, j))
        a, b, val = A[i][j], B[i][j], C[i][j]
        if op_name == "max":
            s = f"位置({i+1},{j+1})：max({a},{b})={val}"
        elif op_name == "min":
            s = f"位置({i+1},{j+1})：min({a},{b})={val}"
        elif op_name == "add":
            s = f"位置({i+1},{j+1})：{a}+{b}={val}"
        else:
            s = f"位置({i+1},{j+1})：|{a}-{b}|={val}"
        samples.append(s)
        if len(samples) >= 4:
            break

    explanation = (
        f"按定义做{op_cn}：{rule}。"
        + (" 示例：" + "；".join(samples) + "。")
        + " 将每个位置都按同样规则计算即可得到结果矩阵。"
    )
    return C, explanation

# ---------- Problem families ----------

class ProblemGenerator:
    def __init__(self, rng: random.Random, output_language: str = "zh"):
        self.rng = rng
        self.lang = output_language or "zh"

    def gen_one(self) -> Dict[str, Any]:
        # 运算族：以 seed 的 max 为主，但扩展到 min/add/absdiff
        op_name = self.rng.choices(
            population=["max", "min", "add", "absdiff"],
            weights=[0.55, 0.15, 0.15, 0.15],
            k=1
        )[0]

        r, c = pick_dims(self.rng)

        # 数值范围：覆盖负数、零、正数
        # 让 max/min 更有意义，范围适中避免太大
        lo, hi = self.rng.choice([(-9, 9), (-5, 12), (0, 15), (-12, 6)])
        A = sample_matrix(self.rng, r, c, lo, hi)
        B = sample_matrix(self.rng, r, c, lo, hi)

        # 适当重采样以避免过于平凡
        for _ in range(60):
            if ensure_nontrivial(A, B, op_name):
                break
            A = sample_matrix(self.rng, r, c, lo, hi)
            B = sample_matrix(self.rng, r, c, lo, hi)

        # 渲染题面：定义符号 ⊙ 并说明逐元素规则
        if op_name == "max":
            rule_text = "定义矩阵运算 A ⊙ B 为逐元素取较大值： (A ⊙ B)_{ij} = max(A_{ij}, B_{ij})。"
        elif op_name == "min":
            rule_text = "定义矩阵运算 A ⊙ B 为逐元素取较小值： (A ⊙ B)_{ij} = min(A_{ij}, B_{ij})。"
        elif op_name == "add":
            rule_text = "定义矩阵运算 A ⊙ B 为逐元素相加： (A ⊙ B)_{ij} = A_{ij} + B_{ij}。"
        else:
            rule_text = "定义矩阵运算 A ⊙ B 为逐元素取绝对差： (A ⊙ B)_{ij} = |A_{ij} - B_{ij}|。"

        C, explanation = compute_and_explain(A, B, op_name)

        # 输出格式要求
        fmt_text = "答案是一个矩阵，请按此 JSON 形式输出：[[((第一行),(第二行),... )]]，其中每一行用圆括号表示。"

        problem = (
            "你需要根据下面给出的自定义矩阵运算规则，计算指定的结果。\n\n"
            f"规则：{rule_text}\n\n"
            "已知：\n"
            f"A =\n{mat_to_latex(A)}\n"
            f"B =\n{mat_to_latex(B)}\n\n"
            "求：A ⊙ B。\n"
            f"{fmt_text}"
        )

        answer = mat_to_answer_format(C)
        return {"problem": problem, "answer": answer, "explanation": explanation}

# ---------- Uniqueness / consistency checks ----------

def canonical_sig(item: Dict[str, Any]) -> str:
    # 防止重复：题面关键信息签名（运算类型、矩阵数据）
    # 通过从 problem 中提取所有整数可能较脆；这里直接从答案对象和题面整体 hash 前的稳定表示
    # 但题面包含 LaTeX，稳定性仍足够；用轻量签名：answer + first 200 chars of problem
    return json.dumps(item["answer"], ensure_ascii=False, sort_keys=True) + "||" + item["problem"][:220]

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        print(f"输入不是合法 JSON：{e}", file=sys.stderr)
        sys.exit(1)

    seed = req.get("seed")
    count = req.get("count")
    if not isinstance(seed, int) or not isinstance(count, int) or count <= 0:
        print("输入 JSON 必须包含 {'seed': int, 'count': 正整数}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    out_lang = req.get("output_language", "zh")  # 兼容但不依赖
    gen = ProblemGenerator(rng, out_lang)

    results = []
    seen = set()
    max_tries = max(200, count * 40)
    tries = 0
    while len(results) < count and tries < max_tries:
        tries += 1
        try:
            item = gen.gen_one()
            sig = canonical_sig(item)
            if sig in seen:
                continue
            # 基本健全性检查
            if not isinstance(item.get("problem"), str) or not item["problem"].strip():
                continue
            # 交叉核验：从题面生成时的 A,B 已用于计算；这里再用 answer 做形状一致性检查
            ans = item["answer"]
            if not (isinstance(ans, list) and len(ans) == 1 and isinstance(ans[0], list) and len(ans[0]) == 1):
                continue
            seen.add(sig)
            results.append(item)
        except Exception as e:
            print(f"生成失败一次：{e}", file=sys.stderr)
            continue

    if len(results) < count:
        print(f"在尝试 {tries} 次后仅生成 {len(results)}/{count} 题，无法满足数量要求。", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()