import sys, json, random, re
from typing import List, Tuple, Dict, Any

# -----------------------------
# Multitap table (fixed)
# -----------------------------
LETTER_TO_CODE = {
    "A": "2^1", "B": "2^2", "C": "2^3",
    "D": "3^1", "E": "3^2", "F": "3^3",
    "G": "4^1", "H": "4^2", "I": "4^3",
    "J": "5^1", "K": "5^2", "L": "5^3",
    "M": "6^1", "N": "6^2", "O": "6^3",
    "P": "7^1", "Q": "7^2", "R": "7^3", "S": "7^4",
    "T": "8^1", "U": "8^2", "V": "8^3",
    "W": "9^1", "X": "9^2", "Y": "9^3", "Z": "9^4",
}
CODE_TO_LETTER = {v: k for k, v in LETTER_TO_CODE.items()}

CODES = list(CODE_TO_LETTER.keys())
LETTERS = list(LETTER_TO_CODE.keys())

CODE_RE = re.compile(r'^[2-9]\^[1-4]$')

def encrypt_plaintext(pt: str) -> List[str]:
    out = []
    for ch in pt:
        if ch not in LETTER_TO_CODE:
            raise ValueError(f"明文包含非法字符: {ch}")
        out.append(LETTER_TO_CODE[ch])
    return out

def decrypt_codes(code_list: List[str]) -> str:
    out = []
    for c in code_list:
        if c not in CODE_TO_LETTER:
            raise ValueError(f"密文码非法: {c}")
        out.append(CODE_TO_LETTER[c])
    return "".join(out)

def join_codes(code_list: List[str]) -> str:
    # 密文表现形式：直接连在一起，如 3^19^4...
    return "".join(code_list)

def parse_code_string(s: str) -> List[str]:
    # 解析形如 "3^19^46^2" 的字符串为 ["3^1","9^4","6^2"]
    # 因为底数只有一位(2-9)，指数只有一位(1-4)，且无分隔符。
    if len(s) % 3 != 0:
        raise ValueError("密文字符串长度不是3的倍数，无法按 x^y 切分")
    parts = [s[i:i+3] for i in range(0, len(s), 3)]
    for p in parts:
        if not CODE_RE.match(p):
            raise ValueError(f"切分得到非法码: {p}")
        if p not in CODE_TO_LETTER:
            raise ValueError(f"切分得到未定义码: {p}")
    return parts

def rand_plaintext(rng: random.Random, min_len=8, max_len=14) -> str:
    n = rng.randint(min_len, max_len)
    return "".join(rng.choice(LETTERS) for _ in range(n))

def rand_code_list(rng: random.Random, min_len=8, max_len=14) -> List[str]:
    n = rng.randint(min_len, max_len)
    return [rng.choice(CODES) for _ in range(n)]

def make_problem_text(pt: str, ct_str: str, output_language: str) -> str:
    # output_language currently only affects Chinese phrasing required by user.
    # Keep it self-contained with full table and instructions.
    table_lines = [
        "| 字母 | 多击码 |",
        "| --- | --- |",
    ]
    for k in "ABCDEF" + "GHI" + "JKL" + "MNO" + "PQRS" + "TUV" + "WXYZ":
        table_lines.append(f"| {k} | {LETTER_TO_CODE[k]} |")
    table = "\n".join(table_lines)

    # Chinese statement
    return (
        "你需要按照下述“多击码（Multitap）”规则进行加密与解密。\n\n"
        "规则说明：\n"
        "1) 加密：把明文中的每个大写字母替换为表中的多击码（形如 2^1）。\n"
        "2) 解密：把密文按每 3 个字符切分为一个多击码（形如 3^2），再按表还原为大写字母。\n"
        "3) 密文表现形式：把各个多击码直接拼接成一个字符串（不加空格和标点）。\n\n"
        "多击码表：\n"
        f"{table}\n\n"
        "问题：\n"
        f"1) 明文：\"{pt}\"。请给出加密结果，用双中括号包裹，形如 [[...]]。\n"
        f"2) 密文：\"{ct_str}\"。请给出解密结果，用双中括号包裹，形如 [[...]]。\n\n"
        "请按如下格式输出最终答案（中间用四个等号连接）：\n"
        "[[第1问加密结果]]====[[第2问解密结果]]\n"
    )

def solve_instance(pt: str, ct_str: str) -> Tuple[str, str, str]:
    # returns (answer_string, explanation, validation_notes)
    enc_codes = encrypt_plaintext(pt)
    enc_str = join_codes(enc_codes)

    codes2 = parse_code_string(ct_str)
    dec_pt = decrypt_codes(codes2)

    answer = f"[[{enc_str}]]====[[{dec_pt}]]"

    # explanation: concise but checkable
    exp = (
        "第1问：逐字母查表替换为多击码并直接拼接。\n"
        f"明文长度={len(pt)}，对应码序列={enc_codes}，拼接得到 {enc_str}。\n"
        "第2问：将密文每3个字符切分为一个多击码，再逐个查表还原。\n"
        f"切分得到码序列={codes2}，还原得到明文 {dec_pt}。"
    )

    # independent cross-check: decrypt(encrypt(pt)) == pt and encrypt(decrypt(ct)) == ct
    check1 = decrypt_codes(enc_codes) == pt
    check2 = join_codes(encrypt_plaintext(dec_pt)) == ct_str
    if not (check1 and check2):
        raise AssertionError("交叉校验失败：加解密互逆性未通过。")

    return answer, exp, "ok"

def generate_one(rng: random.Random, output_language: str) -> Dict[str, Any]:
    # Create both tasks per item: encrypt a plaintext + decrypt a ciphertext
    pt = rand_plaintext(rng)
    code_list = rand_code_list(rng)
    ct_str = join_codes(code_list)

    # Ensure ciphertext parses and decrypts (it will by construction)
    # Also ensure not trivial duplicate: avoid identical pair sizes too often
    _ = decrypt_codes(parse_code_string(ct_str))

    problem = make_problem_text(pt, ct_str, output_language)
    answer, explanation, _ = solve_instance(pt, ct_str)
    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    output_language = data.get("output_language", "zh")
    rng = random.Random(seed)

    results = []
    seen = set()
    attempts = 0
    max_attempts = count * 50

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        item = generate_one(rng, output_language)
        key = (item["problem"], item["answer"])
        if key in seen:
            continue
        # Basic non-empty checks
        if not item["problem"].strip() or item["answer"] is None or not str(item["answer"]).strip():
            continue
        seen.add(key)
        results.append(item)

    if len(results) < count:
        print(f"生成失败：仅生成 {len(results)}/{count} 道题，尝试次数={attempts}", file=sys.stderr)
        sys.exit(1)

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()