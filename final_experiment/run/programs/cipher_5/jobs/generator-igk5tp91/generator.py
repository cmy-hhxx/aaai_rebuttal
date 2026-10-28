import sys, json, random, math
from typing import List, Dict, Tuple, Optional

AFFINE_ALPHABET = "XMJQUDONPRGTVBWFAKSHZCYEIL"
A = 3
B = 5
A_INV = 9
N = 26

pos = {ch: i for i, ch in enumerate(AFFINE_ALPHABET)}


def enc_char(p: str) -> str:
    x = pos[p]
    y = (A * x + B) % N
    return AFFINE_ALPHABET[y]


def dec_char(c: str) -> str:
    y = pos[c]
    x = (A_INV * (y - B)) % N
    return AFFINE_ALPHABET[x]


def encrypt(s: str) -> str:
    return "".join(enc_char(ch) for ch in s)


def decrypt(s: str) -> str:
    return "".join(dec_char(ch) for ch in s)


def rand_plain(rng: random.Random, length: int) -> str:
    # plaintext is uppercase letters in this affine alphabet domain
    return "".join(rng.choice(AFFINE_ALPHABET) for _ in range(length))


def format_problem(plaintext: str, ciphertext: str, variant: int) -> str:
    # variant controls scenario/wording while staying self-contained
    rules = (
        "给定一个仿射替换密码。字母表（affine alphabet）为：\n"
        f"\"{AFFINE_ALPHABET}\"\n"
        "将其中每个字母按其在该字母表中的位置编号（从0开始）。设参数：A=3，B=5，A_inv=9，n=26。\n\n"
        "加密：对明文字母 p，取其位置 x，计算 y=(A*x+B) mod 26，输出位置 y 对应字母。\n"
        "解密：对密文字母 c，取其位置 y，计算 x=A_inv*(y-B) mod 26，输出位置 x 对应字母。\n"
    )

    if variant == 0:
        q = (
            "问题：\n"
            f"1）明文：\"{plaintext}\"。请给出加密结果，用双层方括号包裹，如 [[...]]。\n"
            f"2）密文：\"{ciphertext}\"。请给出解密结果，用双层方括号包裹，如 [[...]]。\n"
        )
    elif variant == 1:
        q = (
            "任务：分别完成一次加密与一次解密。\n"
            f"- 加密输入明文：{plaintext}\n"
            f"- 解密输入密文：{ciphertext}\n"
            "输出格式要求：加密答案写成 [[密文]]，解密答案写成 [[明文]]。\n"
        )
    elif variant == 2:
        q = (
            "请按如下仿射规则处理两段字符串：\n"
            f"（一）将明文 \"{plaintext}\" 加密；\n"
            f"（二）将密文 \"{ciphertext}\" 解密。\n"
            "分别给出结果，均需用双层方括号 [[...]] 包裹。\n"
        )
    else:
        q = (
            "在下述固定字母表与参数下执行仿射变换：\n"
            f"明文待加密：\"{plaintext}\"；密文待解密：\"{ciphertext}\"。\n"
            "请返回两段结果，均用 [[...]] 标注。\n"
        )

    return rules + "\n" + q


def explain_one_mapping(ch: str, is_encrypt: bool) -> str:
    if is_encrypt:
        x = pos[ch]
        y = (A * x + B) % N
        return f"{ch} 的位置 x={x}，y=(3*{x}+5) mod 26 = {y}，对应字母 {AFFINE_ALPHABET[y]}"
    else:
        y = pos[ch]
        x = (A_INV * (y - B)) % N
        return f"{ch} 的位置 y={y}，x=9*({y}-5) mod 26 = {x}，对应字母 {AFFINE_ALPHABET[x]}"


def build_explanation(plaintext: str, ciphertext: str, enc: str, dec: str, rng: random.Random) -> str:
    # Provide short, checkable evidence: show first 2-3 character computations each direction
    k1 = min(3, len(plaintext))
    k2 = min(3, len(ciphertext))
    enc_steps = [explain_one_mapping(plaintext[i], True) for i in range(k1)]
    dec_steps = [explain_one_mapping(ciphertext[i], False) for i in range(k2)]

    return (
        "校验示例（展示前若干字符的计算）：\n"
        "加密：\n- " + "\n- ".join(enc_steps) + f"\n因此整段明文加密得到：{enc}\n\n"
        "解密：\n- " + "\n- ".join(dec_steps) + f"\n因此整段密文解密得到：{dec}\n"
    )


def validate_bijection():
    # Ensure encryption/decryption are inverses on the given alphabet
    for ch in AFFINE_ALPHABET:
        c = enc_char(ch)
        p = dec_char(c)
        if p != ch:
            raise AssertionError("Encrypt/decrypt are not inverses for character: " + ch)


def generate_items(seed: int, count: int) -> List[Dict]:
    rng = random.Random(seed)
    validate_bijection()

    items = []
    seen = set()

    attempts = 0
    max_attempts = 20000

    while len(items) < count and attempts < max_attempts:
        attempts += 1

        # Variety in lengths and wording
        Lp = rng.randint(8, 14)
        Lc = rng.randint(8, 14)

        plaintext = rand_plain(rng, Lp)
        ciphertext = rand_plain(rng, Lc)

        enc = encrypt(plaintext)
        dec = decrypt(ciphertext)

        variant = rng.randint(0, 3)
        problem = format_problem(plaintext, ciphertext, variant)

        # answer format: [[ENC]]====[[DEC]]
        answer = f"[[{enc}]]====[[{dec}]]"

        # Avoid duplicates by core I/O
        key = (plaintext, ciphertext)
        if key in seen:
            continue
        seen.add(key)

        # Cross-check using independent path (table composition)
        # Build explicit mapping tables and apply them
        enc_map = {ch: enc_char(ch) for ch in AFFINE_ALPHABET}
        dec_map = {ch: dec_char(ch) for ch in AFFINE_ALPHABET}
        enc2 = "".join(enc_map[ch] for ch in plaintext)
        dec2 = "".join(dec_map[ch] for ch in ciphertext)
        if enc2 != enc or dec2 != dec:
            raise AssertionError("Cross-check mismatch.")

        explanation = build_explanation(plaintext, ciphertext, enc, dec, rng)

        items.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    if len(items) < count:
        raise RuntimeError(f"生成失败：仅生成 {len(items)}/{count} 题，请更换 seed 或降低 count。")

    return items


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    out = generate_items(seed, count)
    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()