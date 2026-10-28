import sys, json, random
from typing import List, Tuple, Dict, Any

PERM = (2, 0, 3, 1, 4, 6, 5, 7)
INV_PERM = (1, 3, 0, 2, 4, 6, 5, 7)

def bits_xor(a: str, b: str) -> str:
    return "".join("1" if x != y else "0" for x, y in zip(a, b))

def apply_perm(bits: str, perm: Tuple[int, ...]) -> str:
    # output[i] = input[perm[i]]
    return "".join(bits[perm[i]] for i in range(8))

def inv_apply_perm(bits: str, inv_perm: Tuple[int, ...]) -> str:
    # inverse: output[i] = input[inv_perm[i]]
    return "".join(bits[inv_perm[i]] for i in range(8))

def char_to_bits(c: str) -> str:
    return format(ord(c), "08b")

def bits_to_char(b: str) -> str:
    return chr(int(b, 2))

def encrypt_plaintext(plaintext: str, key: str) -> str:
    out = []
    for c in plaintext:
        b = char_to_bits(c)
        x = bits_xor(b, key)
        p = apply_perm(x, PERM)
        out.append(p)
    return "".join(out)

def decrypt_ciphertext(ciphertext: str, key: str) -> str:
    if len(ciphertext) % 8 != 0:
        raise ValueError("ciphertext length not multiple of 8")
    chars = []
    for i in range(0, len(ciphertext), 8):
        chunk = ciphertext[i:i+8]
        u = inv_apply_perm(chunk, INV_PERM)
        x = bits_xor(u, key)
        chars.append(bits_to_char(x))
    return "".join(chars)

def is_uppercase_AZ(s: str) -> bool:
    return all('A' <= c <= 'Z' for c in s) and len(s) > 0

def random_key(rng: random.Random) -> str:
    # 8-bit binary string, avoid trivial all-0/all-1 most of time
    while True:
        k = "".join(rng.choice("01") for _ in range(8))
        if k not in ("00000000", "11111111"):
            return k

def random_plaintext(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(n))

def format_problem(plaintext: str, ciphertext: str, key: str, variant: int) -> str:
    # variant controls wording / tasks order
    base_rules = (
        "你是一个擅长加密与解密的助手。请严格按以下密码规则进行运算，并按指定格式输出。\n\n"
        "### 密码规则\n"
        "固定密钥（8位二进制串）：\"{key}\"\n"
        "置换表 Perm = (2, 0, 3, 1, 4, 6, 5, 7)\n"
        "逆置换表 InvPerm = (1, 3, 0, 2, 4, 6, 5, 7)\n\n"
        "#### 加密（明文->密文）\n"
        "1) 将每个大写字母按 ASCII 转成 8 位二进制。\n"
        "2) 与固定密钥逐位 XOR。\n"
        "3) 对 XOR 结果按 Perm 做置换：输出第 i 位 = 输入第 Perm[i] 位。\n"
        "4) 将每个字符得到的 8 位结果依次拼接，得到最终密文（仅含 0/1）。\n\n"
        "#### 解密（密文->明文）\n"
        "1) 将密文按 8 位分组。\n"
        "2) 对每组按 InvPerm 做逆置换：输出第 i 位 = 输入第 InvPerm[i] 位。\n"
        "3) 与固定密钥逐位 XOR。\n"
        "4) 将得到的 8 位二进制转十进制，再转 ASCII 字符，拼接得到明文（应为 A-Z）。\n\n"
    ).format(key=key)

    if variant == 0:
        return (
            base_rules
            + "### 问题\n"
            + f"1）明文：\"{plaintext}\"。请给出加密得到的密文，答案用双中括号包裹：[[...]]。\n"
            + f"2）密文：\"{ciphertext}\"。请给出解密得到的明文，答案用双中括号包裹：[[...]]。\n"
        )
    elif variant == 1:
        return (
            base_rules
            + "### 问题\n"
            + f"A）对明文 \"{plaintext}\" 执行加密，输出拼接后的二进制密文（[[...]]）。\n"
            + f"B）对二进制密文 \"{ciphertext}\" 执行解密，输出明文（[[...]]）。\n"
        )
    else:
        return (
            base_rules
            + "### 问题\n"
            + f"（一）加密：明文 = {plaintext}。输出密文（用 [[ ]] 包裹）。\n"
            + f"（二）解密：密文 = {ciphertext}。输出明文（用 [[ ]] 包裹）。\n"
        )

def build_explanation_encrypt(plaintext: str, key: str, ciphertext: str, max_show: int = 2) -> str:
    # show first 1-2 chars derivation for auditability
    lines = []
    lines.append("加密校验（展示前若干字符的中间结果）：")
    show = min(len(plaintext), max_show)
    for idx in range(show):
        c = plaintext[idx]
        b = char_to_bits(c)
        x = bits_xor(b, key)
        p = apply_perm(x, PERM)
        lines.append(f"- 字符 {idx+1}：'{c}' ASCII二进制={b}，XOR密钥={x}，置换后={p}")
    lines.append(f"最终密文为以上每组8位的拼接，共 {len(plaintext)} 组，长度 {len(ciphertext)} 位。")
    return "\n".join(lines)

def build_explanation_decrypt(ciphertext: str, key: str, plaintext: str, max_show: int = 2) -> str:
    lines = []
    lines.append("解密校验（展示前若干分组的中间结果）：")
    groups = len(ciphertext) // 8
    show = min(groups, max_show)
    for idx in range(show):
        chunk = ciphertext[idx*8:(idx+1)*8]
        u = inv_apply_perm(chunk, INV_PERM)
        x = bits_xor(u, key)
        c = bits_to_char(x)
        lines.append(f"- 分组 {idx+1}：密文块={chunk}，逆置换后={u}，XOR密钥后={x}，得到字符='{c}'")
    lines.append(f"最终明文为各字符拼接，共 {groups} 个字符。")
    return "\n".join(lines)

def make_instance(rng: random.Random, attempt: int) -> Dict[str, Any]:
    # Choose variant family: both tasks in one; key randomized per instance
    key = random_key(rng)

    # plaintext for encryption task
    n1 = rng.randint(6, 14)
    pt1 = random_plaintext(rng, n1)
    ct1 = encrypt_plaintext(pt1, key)

    # plaintext for decryption task -> generate a ciphertext
    n2 = rng.randint(6, 14)
    pt2 = random_plaintext(rng, n2)
    ct2 = encrypt_plaintext(pt2, key)

    # Ensure decryption output is uppercase A-Z (it will be, by construction)
    dec2 = decrypt_ciphertext(ct2, key)
    if dec2 != pt2 or not is_uppercase_AZ(dec2):
        raise AssertionError("construction/decryption mismatch")

    # Cross-check encryption-decryption consistency on pt1 as well
    back1 = decrypt_ciphertext(ct1, key)
    if back1 != pt1:
        raise AssertionError("encrypt/decrypt mismatch")

    variant = rng.randint(0, 2)
    problem = format_problem(pt1, ct2, key, variant)

    answer = f"[[{ct1}]]====[[{dec2}]]"

    explanation = (
        build_explanation_encrypt(pt1, key, ct1, max_show=2)
        + "\n\n"
        + build_explanation_decrypt(ct2, key, dec2, max_show=2)
        + "\n\n"
        + "答案格式说明：第一部分为对题目中“明文”加密得到的密文；第二部分为对题目中“密文”解密得到的明文，二者用 ==== 连接。"
    )

    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results: List[Dict[str, Any]] = []
    seen = set()
    max_attempts = 5000

    attempts = 0
    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = make_instance(rng, attempts)
        except Exception as e:
            print(f"[warn] generation failed on attempt {attempts}: {e}", file=sys.stderr)
            continue

        # Deduplicate by problem text
        h = item["problem"]
        if h in seen:
            continue
        seen.add(h)

        # Basic validity checks
        if not item["problem"] or not isinstance(item["problem"], str):
            continue
        if "====" not in item["answer"]:
            continue
        if not item["explanation"]:
            continue

        results.append(item)

    if len(results) != count:
        raise RuntimeError(f"Unable to generate required count={count}, got {len(results)} after {attempts} attempts")

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()