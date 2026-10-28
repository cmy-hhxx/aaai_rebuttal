import sys, json, string, random
from typing import List, Dict, Tuple, Any

STD = string.ascii_uppercase

# 13 cipher alphabets indexed by key-letter groups (two letters per group)
GROUPS = ["AB","CD","EF","GH","IJ","KL","MN","OP","QR","ST","UV","WX","YZ"]
CIPHER_ALPHABETS = {
    "AB": "NOPQRSTUVWXYZABCDEFGHIJKLM",
    "CD": "ZNOPQRSTUVWXYBCDEFGHIJKLMA",
    "EF": "YZNOPQRSTUVWXCDEFGHIJKLMAB",
    "GH": "XYZNOPQRSTUVWDEFGHIJKLMABC",
    "IJ": "WXYZNOPQRSTUVEFGHIJKLMABCD",
    "KL": "VWXYZNOPQRSTUFGHIJKLMABCDE",
    "MN": "UVWXYZNOPQRSTGHIJKLMABCDEF",
    "OP": "TUVWXYZNOPQRSHIJKLMABCDEFG",
    "QR": "STUVWXYZNOPQRIJKLMABCDEFGH",
    "ST": "RSTUVWXYZNOPQJKLMABCDEFGHI",
    "UV": "QRSTUVWXYZUVWXYZNOPKLMABCDEFGHIJ".replace("ABCDEFGHIJKLMNOPQRSTUVWXYZ", ""),  # placeholder not used
    "WX": "PQRSTUVWXYZNOLMABCDEFGHIJK",
    "YZ": "OPQRSTUVWXYZNMABCDEFGHIJKL",
}

# Fix the UV alphabet from the prompt exactly
CIPHER_ALPHABETS["UV"] = "QRSTUVWXYZYZNOPKLMABCDEFGHIJ".replace("YZNOP", "YZNOP")  # noop to keep deterministic
# Actually set it explicitly (as given in seed)
CIPHER_ALPHABETS["UV"] = "QRSTUVWXYZYZNOPKLMABCDEFGHIJ"
# Wait: The seed rule says:
# UV: QRSTUVWXYZNOPKLMABCDEFGHIJ  (length 26)
# so set that:
CIPHER_ALPHABETS["UV"] = "QRSTUVWXYZYZNOPKLMABCDEFGHIJ"  # incorrect; override again
CIPHER_ALPHABETS["UV"] = "QRSTUVWXYZ"  # temp

# Re-assert all alphabets explicitly and correctly to avoid any accidental corruption.
CIPHER_ALPHABETS = {
    "AB": "NOPQRSTUVWXYZABCDEFGHIJKLM",
    "CD": "ZNOPQRSTUVWXYBCDEFGHIJKLMA",
    "EF": "YZNOPQRSTUVWXCDEFGHIJKLMAB",
    "GH": "XYZNOPQRSTUVWDEFGHIJKLMABC",
    "IJ": "WXYZNOPQRSTUVEFGHIJKLMABCD",
    "KL": "VWXYZNOPQRSTUFGHIJKLMABCDE",
    "MN": "UVWXYZNOPQRSTGHIJKLMABCDEF",
    "OP": "TUVWXYZNOPQRSHIJKLMABCDEFG",
    "QR": "STUVWXYZNOPQRIJKLMABCDEFGH",
    "ST": "RSTUVWXYZNOPQJKLMABCDEFGHI",
    "UV": "QRSTUVWXYZYZNOPKLMABCDEFGHIJ",  # still wrong; set correctly below
    "WX": "PQRSTUVWXYZNOLMABCDEFGHIJK",
    "YZ": "OPQRSTUVWXYZNMABCDEFGHIJKL",
}
# Correct UV per prompt: "QRSTUVWXYZNOPKLMABCDEFGHIJ"
CIPHER_ALPHABETS["UV"] = "QRSTUVWXYZNOPKLMABCDEFGHIJ"

# Map each key letter A-Z to one of the 13 groups.
# Rule interpretation: A/B -> AB, C/D -> CD, ..., Y/Z -> YZ
LETTER_TO_GROUP = {}
for grp in GROUPS:
    LETTER_TO_GROUP[grp[0]] = grp
    LETTER_TO_GROUP[grp[1]] = grp

def validate_alphabets():
    # Ensure all cipher alphabets are valid permutations of A-Z
    sset = set(STD)
    for g, alpha in CIPHER_ALPHABETS.items():
        if len(alpha) != 26 or set(alpha) != sset:
            raise ValueError(f"Cipher alphabet for group {g} invalid: {alpha}")

def repeat_key(key: str, n: int) -> str:
    return (key * (n // len(key) + 1))[:n]

def encrypt(plaintext: str, key: str) -> str:
    key2 = repeat_key(key, len(plaintext))
    out = []
    for p, k in zip(plaintext, key2):
        grp = LETTER_TO_GROUP[k]
        cipher_alpha = CIPHER_ALPHABETS[grp]
        idx = STD.index(p)
        out.append(cipher_alpha[idx])
    return "".join(out)

def decrypt(ciphertext: str, key: str) -> str:
    key2 = repeat_key(key, len(ciphertext))
    out = []
    for c, k in zip(ciphertext, key2):
        grp = LETTER_TO_GROUP[k]
        cipher_alpha = CIPHER_ALPHABETS[grp]
        idx = cipher_alpha.index(c)
        out.append(STD[idx])
    return "".join(out)

def rand_word(rng: random.Random, min_len: int, max_len: int) -> str:
    L = rng.randint(min_len, max_len)
    return "".join(rng.choice(STD) for _ in range(L))

def rand_key(rng: random.Random, min_len: int, max_len: int) -> str:
    L = rng.randint(min_len, max_len)
    return "".join(rng.choice(STD) for _ in range(L))

def make_explanation_encrypt(pt: str, key: str, ct: str) -> str:
    # Show first few steps, but not too long
    key2 = repeat_key(key, len(pt))
    steps = []
    show = min(6, len(pt))
    for i in range(show):
        p, k, c = pt[i], key2[i], ct[i]
        grp = LETTER_TO_GROUP[k]
        idx = STD.index(p)
        steps.append(f"{i+1}) 密钥字母 {k} 属于组 {grp}；{p} 在标准字母表位置 {idx}，替换为 {c}")
    if len(pt) > show:
        steps.append("…（其余位置同理）")
    return (
        "加密思路：将密钥循环到与明文等长；每个位置用该密钥字母所属的双字母组选择对应的替换字母表，"
        "再按标准字母表索引做同位替换。\n"
        + "\n".join(steps)
    )

def make_explanation_decrypt(ct: str, key: str, pt: str) -> str:
    key2 = repeat_key(key, len(ct))
    steps = []
    show = min(6, len(ct))
    for i in range(show):
        c, k, p = ct[i], key2[i], pt[i]
        grp = LETTER_TO_GROUP[k]
        idx = CIPHER_ALPHABETS[grp].index(c)
        steps.append(f"{i+1}) 密钥字母 {k} 属于组 {grp}；{c} 在该组字母表位置 {idx}，还原为 {p}")
    if len(ct) > show:
        steps.append("…（其余位置同理）")
    return (
        "解密思路：将密钥循环到与密文等长；每个位置用该密钥字母所属的双字母组选择对应的替换字母表，"
        "在该替换表中找密文字母的位置，再用同位置的标准字母表字母还原。\n"
        + "\n".join(steps)
    )

def generate_one(rng: random.Random, idx: int) -> Dict[str, Any]:
    # Two-task format like the seed: one encryption + one decryption
    # Add diversity via lengths and key sizes
    pt_len = rng.randint(8, 14)
    ct_len = rng.randint(8, 14)

    pt = rand_word(rng, pt_len, pt_len)
    key1 = rand_key(rng, 4, 8)
    ct1 = encrypt(pt, key1)

    # For decryption task, we generate a random plaintext then encrypt to obtain ciphertext.
    pt2 = rand_word(rng, ct_len, ct_len)
    key2 = rand_key(rng, 3, 7)
    ct2 = encrypt(pt2, key2)
    dec2 = decrypt(ct2, key2)

    # Cross-check with an "independent" verification: direct brute mapping per character
    # (still deterministic; different code path: precompute inverse maps per group)
    inv_maps = {g: {c: STD[i] for i, c in enumerate(alpha)} for g, alpha in CIPHER_ALPHABETS.items()}
    key2rep = repeat_key(key2, len(ct2))
    dec2_check = "".join(inv_maps[LETTER_TO_GROUP[k]][c] for c, k in zip(ct2, key2rep))
    if dec2_check != dec2 or dec2 != pt2:
        raise AssertionError("Decryption cross-check failed")

    # Another check for encryption: verify via inverse mapping back
    back = decrypt(ct1, key1)
    if back != pt:
        raise AssertionError("Encryption invertibility check failed")

    problem = (
        "你是一名擅长加密与解密的助手。请严格按照下述替换密码规则完成两问，并将每问答案用双中括号包裹输出。\n\n"
        "规则摘要（与题目所用规则一致）：\n"
        f"- 标准字母表：{STD}\n"
        "- 共有 13 个替换字母表（由密钥字母所属的双字母组选择）：\n"
        + "\n".join([f"  {g}: {CIPHER_ALPHABETS[g]}" for g in GROUPS]) + "\n"
        "- 将密钥循环重复到与待处理字符串等长；每一位根据该位密钥字母所属组选择替换表。\n"
        "- 加密：明文字母在标准字母表的位置 i -> 替换表位置 i 的字母。\n"
        "- 解密：密文字母在替换表的位置 i -> 标准字母表位置 i 的字母。\n\n"
        f"1）明文：\"{pt}\"\n密钥：{key1}\n请给出加密结果，格式为 [[...]]。\n"
        f"2）密文：\"{ct2}\"\n密钥：{key2}\n请给出解密结果，格式为 [[...]]。"
    )
    answer = f"[[{ct1}]]====[[{dec2}]]"
    explanation = (
        "第 1 问（加密）校验要点：用同一密钥解密应还原回原明文。\n"
        + make_explanation_encrypt(pt, key1, ct1) + "\n\n"
        "第 2 问（解密）校验要点：解密结果再次加密应回到原密文。\n"
        + make_explanation_decrypt(ct2, key2, dec2)
    )
    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    try:
        validate_alphabets()
        raw = sys.stdin.read()
        data = json.loads(raw)
        seed = int(data["seed"])
        count = int(data["count"])
        if count <= 0:
            raise ValueError("count must be a positive integer")
        rng = random.Random(seed)

        res = []
        seen = set()
        attempts = 0
        max_attempts = count * 50

        while len(res) < count and attempts < max_attempts:
            attempts += 1
            item = generate_one(rng, len(res))
            # Deduplicate by (pt,key1,ct2,key2) extracted from problem hash
            sig = item["problem"]
            if sig in seen:
                continue
            seen.add(sig)
            res.append(item)

        if len(res) < count:
            raise RuntimeError(f"生成失败：仅生成 {len(res)}/{count} 道题（尝试 {attempts} 次）")

        sys.stdout.write(json.dumps(res, ensure_ascii=False))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()