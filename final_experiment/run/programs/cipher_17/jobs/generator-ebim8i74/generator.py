import sys, json, math, random, string
from typing import List, Tuple, Dict, Any, Optional

ALPHABET = string.ascii_uppercase

def _chunks(s: str, n: int) -> List[str]:
    return [s[i:i+n] for i in range(0, len(s), n)]

def encrypt_boustro_columns(plaintext: str, width: int = 5) -> str:
    """
    加密：
    1) 按每行最多 width 个字符分行。
    2) 奇数行左->右写；偶数行右->左写（即把该行字符串反转后写入）。
    3) 按列自上而下读，每读一列追加一个 '#'
    注：最后一行可能不足 width，列读时对缺位不输出字符。
    """
    if not plaintext or any(c not in ALPHABET for c in plaintext):
        raise ValueError("plaintext 必须为仅含大写字母且非空的字符串")
    if width <= 0:
        raise ValueError("width 必须为正整数")

    raw_rows = _chunks(plaintext, width)
    rows = []
    for i, r in enumerate(raw_rows, start=1):
        rows.append(r if i % 2 == 1 else r[::-1])

    maxlen = max(len(r) for r in rows)
    out = []
    for col in range(maxlen):
        for r in rows:
            if col < len(r):
                out.append(r[col])
        out.append('#')
    return ''.join(out)

def decrypt_boustro_columns(ciphertext: str, width: int = 5) -> str:
    """
    解密（严格按题面“加密反操作”）：
    - 题面固定“行数=5”。但为了生成器更通用，这里允许任意 width，
      并由密文中 '#' 的数量决定列数；行数固定为 width（与种子一致=5）。
    过程：
    1) 逐字符自上而下写入当前列，遇到 '#' 切到下一列。
       写入时行号从 1..width 循环；若列未满遇到 '#', 则该列剩余行为空。
    2) 得到 width 行的网格后：奇数行按左->右读，偶数行按右->左读，拼接即明文。
    """
    if not ciphertext or any((c not in ALPHABET and c != '#') for c in ciphertext):
        raise ValueError("ciphertext 必须为仅含大写字母与 # 且非空的字符串")
    if width <= 0:
        raise ValueError("width 必须为正整数")
    if '#' not in ciphertext:
        raise ValueError("ciphertext 必须包含分隔符 #")

    # 解析列：遇到 # 结束一列
    cols: List[List[Optional[str]]] = []
    cur: List[Optional[str]] = [None] * width
    row = 0
    for ch in ciphertext:
        if ch == '#':
            cols.append(cur)
            cur = [None] * width
            row = 0
        else:
            if row >= width:
                # 这一列字符数超过行数，题面规则下不应发生
                raise ValueError("ciphertext 某列字符数超过行数(width)，不符合规则")
            cur[row] = ch
            row += 1
    # 题面样例密文一般以 # 结尾；若未以 # 结尾，则 cur 未入列
    # 为了稳健，若 cur 有内容则也入列
    if any(x is not None for x in cur):
        cols.append(cur)

    # 将列转为行字符串
    rows: List[List[str]] = [[] for _ in range(width)]
    for col in cols:
        for r in range(width):
            if col[r] is not None:
                rows[r].append(col[r])
            else:
                # 缺位：该行该列无字符
                pass

    # 还原“写入后的行内容”(即加密时的 rows：奇数行正向，偶数行反向)
    written_rows = [''.join(rows[r]) for r in range(width)]

    # 按 boustrophedon 阅读还原明文：奇数行正读，偶数行反读
    pt_parts = []
    for i, wr in enumerate(written_rows, start=1):
        pt_parts.append(wr if i % 2 == 1 else wr[::-1])
    return ''.join(pt_parts)

def _random_plaintext(rng: random.Random, n: int) -> str:
    return ''.join(rng.choice(ALPHABET) for _ in range(n))

def _validate_encrypt_decrypt_consistency(pt: str, width: int = 5) -> Tuple[str, str]:
    ct = encrypt_boustro_columns(pt, width=width)
    # 解密固定行数=width
    recovered = decrypt_boustro_columns(ct, width=width)
    if recovered != pt:
        raise AssertionError("自检失败：解密未能还原明文")
    return ct, recovered

def _validate_decrypt_encrypt_consistency(ct: str, width: int = 5) -> Tuple[str, str]:
    pt = decrypt_boustro_columns(ct, width=width)
    ct2 = encrypt_boustro_columns(pt, width=width)
    if ct2 != ct:
        raise AssertionError("自检失败：加密未能还原密文")
    return pt, ct2

def _make_problem_encrypt(pt: str, ct: str, width: int = 5, variant: int = 0) -> Dict[str, Any]:
    # 题面中文且自包含，给出规则与任务
    rule = (
        "加密规则：\n"
        f"- 每行最多 {width} 个字母；从第1行起计数。\n"
        "- 先把明文分行书写：奇数行从左到右写；偶数行从右到左写（等价于该行字符串反转后写入）。\n"
        "- 再按“列”读取：从第1列开始，每列自上而下读取所有存在的字母，读完该列后追加一个“#”。\n"
        "- 直到所有列读完，得到密文。\n"
    )
    if variant == 0:
        ask = f"请对明文进行加密，输出形如 [[密文]]。\n明文：\"{pt}\"\n"
    else:
        ask = f"按上述规则加密下列明文，并用双中括号输出：[[...]]。\n明文为：{pt}\n"
    explanation = (
        "校验要点：\n"
        f"- 明文长度={len(pt)}，每行最多{width}个字母。\n"
        f"- 生成的密文按列读取，并以“#”分隔每一列。\n"
        f"- 结果密文为：{ct}\n"
    )
    return {
        "problem": rule + "\n任务：\n" + ask,
        "answer": f"[[{ct}]]",
        "explanation": explanation
    }

def _make_problem_decrypt(ct: str, pt: str, width: int = 5, variant: int = 0) -> Dict[str, Any]:
    rule = (
        "解密规则（为加密的反过程，行数固定为 5 行）：\n"
        f"- 将密文从左到右读取，按“列”自上而下依次写入 5 行；遇到“#”则切换到下一列继续写。\n"
        "- 写完后得到一个5行的字母表格（某些列可能不满5个字母）。\n"
        "- 最后按行读出明文：奇数行从左到右读；偶数行从右到左读；依次拼接得到明文。\n"
        "注意：密文仅包含大写字母与分隔符“#”。\n"
    )
    if width != 5:
        # 题面强调5行，这里保持一致；width 在本生成器中固定用5
        raise ValueError("本题面解密固定为5行，width必须为5")

    if variant == 0:
        ask = f"请解密下列密文，输出形如 [[明文]]。\n密文：\"{ct}\"\n"
    else:
        ask = f"根据上述规则还原明文，并用双中括号输出：[[...]]。\n给定密文：{ct}\n"

    explanation = (
        "校验要点：\n"
        f"- 将密文按“#”切分为若干列，每列从上到下填入5行。\n"
        f"- 得到行内容后，按“奇行正读、偶行反读”拼接。\n"
        f"- 解得明文为：{pt}\n"
    )
    return {
        "problem": rule + "\n任务：\n" + ask,
        "answer": f"[[{pt}]]",
        "explanation": explanation
    }

def generate_one(rng: random.Random, seen: set) -> Dict[str, Any]:
    width = 5  # 与种子一致：最大每行5，加密；解密固定5行
    # 两个题型：加密 or 解密
    mode = rng.choice(["enc", "dec"])

    # 控制规模：行数不固定（由长度决定），长度尽量让列数>=2 且不太短
    if mode == "enc":
        n = rng.randint(18, 45)
        pt = _random_plaintext(rng, n)
        ct, _ = _validate_encrypt_decrypt_consistency(pt, width=width)
        key = ("enc", pt)
        if key in seen:
            raise ValueError("重复实例")
        seen.add(key)
        return _make_problem_encrypt(pt, ct, width=width, variant=rng.randint(0, 1))

    else:
        # 生成一个明文 -> 密文，然后出密文让解密
        n = rng.randint(15, 40)
        pt = _random_plaintext(rng, n)
        ct, _ = _validate_encrypt_decrypt_consistency(pt, width=width)

        # 为了多样性，偶尔裁剪掉末尾最后一列后的 #？不允许：题面允许不以#结尾但更易歧义；
        # 这里保持标准：总是以#结尾。
        if not ct.endswith('#'):
            ct += '#'

        # 再做逆向一致性校验（独立路径：先解密再加密比对）
        pt2, ct2 = _validate_decrypt_encrypt_consistency(ct, width=width)
        if pt2 != pt or ct2 != ct:
            raise AssertionError("交叉核验失败")

        key = ("dec", ct)
        if key in seen:
            raise ValueError("重复实例")
        seen.add(key)
        return _make_problem_decrypt(ct, pt, width=width, variant=rng.randint(0, 1))

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results = []
    seen = set()
    max_tries = 20000
    tries = 0
    while len(results) < count and tries < max_tries:
        tries += 1
        try:
            item = generate_one(rng, seen)
            # 基本非空检查
            if not item["problem"] or "answer" not in item or item["explanation"] is None:
                raise AssertionError("渲染结果缺字段或为空")
            results.append(item)
        except Exception as e:
            # 失败重采样；真实错误信息写stderr但不中断，除非超限
            print(f"[warn] resample due to: {type(e).__name__}: {e}", file=sys.stderr)

    if len(results) != count:
        raise RuntimeError(f"生成失败：仅生成 {len(results)}/{count} 题（尝试次数={tries}）")

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()