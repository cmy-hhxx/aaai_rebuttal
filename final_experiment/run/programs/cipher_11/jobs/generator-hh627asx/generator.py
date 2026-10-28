import sys, json, re, random
from typing import List, Tuple, Dict, Any

# ----------------------------
# Four-square style cipher with fixed 5x5 grids (Q removed)
# As in seed: Gird1 & Gird4 are same; Gird2 & Gird3 are custom.
# Encryption:
#   pair (p1,p2):
#     pos1 = position of p1 in Grid1
#     pos2 = position of p2 in Grid4
#     c1 = Grid2[pos1]
#     c2 = Grid3[pos2]
# Decryption:
#   pair (c1,c2):
#     pos1 = position of c1 in Grid2
#     pos2 = position of c2 in Grid3
#     p1 = Grid1[pos1]
#     p2 = Grid4[pos2]
# ----------------------------

GRID1 = [
    list("KLMNO"),
    list("PRSTU"),
    list("VWXYZ"),
    list("ABCDE"),
    list("FGHIJ"),
]
GRID4 = [
    list("KLMNO"),
    list("PRSTU"),
    list("VWXYZ"),
    list("ABCDE"),
    list("FGHIJ"),
]
GRID2 = [
    list("ECHOA"),
    list("BDFGI"),
    list("JKLMN"),
    list("PRSTU"),
    list("VWXYZ"),
]
GRID3 = [
    list("VORTE"),
    list("XABCD"),
    list("FGHIJ"),
    list("KLMNP"),
    list("SUWYZ"),
]

ALPHABET_NO_Q = "ABCDEFGHIKLMNOPRSTUVWXYZ"  # J included, Q removed


def build_pos_map(grid: List[List[str]]) -> Dict[str, Tuple[int, int]]:
    m = {}
    for r in range(5):
        for c in range(5):
            ch = grid[r][c]
            if ch in m:
                raise ValueError(f"Grid has duplicate letter: {ch}")
            m[ch] = (r, c)
    return m


POS1 = build_pos_map(GRID1)
POS2 = build_pos_map(GRID2)
POS3 = build_pos_map(GRID3)
POS4 = build_pos_map(GRID4)


def clean_text(s: str, remove_q: bool) -> str:
    s = re.sub(r"[^A-Za-z]", "", s).upper()
    if remove_q:
        s = s.replace("Q", "")
    return s


def chunk2(s: str) -> List[str]:
    return [s[i:i+2] for i in range(0, len(s), 2)]


def encrypt(plaintext: str) -> str:
    p = clean_text(plaintext, remove_q=True)
    if len(p) % 2 == 1:
        p += "X"
    out = []
    for pair in chunk2(p):
        if len(pair) != 2:
            raise ValueError("Internal chunking error")
        a, b = pair[0], pair[1]
        if a not in POS1 or b not in POS4:
            raise ValueError(f"Plaintext contains letter not in grid (Q removed alphabet). Pair={pair}")
        r1, c1 = POS1[a]
        r2, c2 = POS4[b]
        out.append(GRID2[r1][c1])
        out.append(GRID3[r2][c2])
    return "".join(out)


def decrypt(ciphertext: str) -> str:
    c = clean_text(ciphertext, remove_q=False)
    if len(c) % 2 == 1:
        # Problem statements should ensure even length, but be robust:
        # ignore last char for safety (or could raise). We'll raise to keep strict.
        raise ValueError("Ciphertext length must be even after cleanup.")
    out = []
    for pair in chunk2(c):
        a, b = pair[0], pair[1]
        if a not in POS2 or b not in POS3:
            raise ValueError(f"Ciphertext contains letter not in grid. Pair={pair}")
        r1, c1 = POS2[a]
        r2, c2 = POS3[b]
        out.append(GRID1[r1][c1])
        out.append(GRID4[r2][c2])
    return "".join(out)


def explain_encrypt(plaintext: str, ciphertext: str, show_pairs: int = 3) -> str:
    p_clean = clean_text(plaintext, remove_q=True)
    padded = p_clean + ("X" if len(p_clean) % 2 == 1 else "")
    pairs = chunk2(padded)
    enc_pairs = chunk2(ciphertext)
    k = min(show_pairs, len(pairs))
    lines = []
    lines.append("加密说明（按题面规则）：")
    lines.append(f"1) 清理后明文：{p_clean}")
    if len(p_clean) % 2 == 1:
        lines.append("2) 明文长度为奇数，末尾补X。")
    lines.append(f"3) 分组：{' '.join(pairs)}")
    lines.append("4) 示例映射（取前几组展示）：")
    for i in range(k):
        a, b = pairs[i][0], pairs[i][1]
        r1, c1 = POS1[a]
        r2, c2 = POS4[b]
        c1ch = GRID2[r1][c1]
        c2ch = GRID3[r2][c2]
        lines.append(f"  - {a}{b}: {a}在Gird1位置({r1+1},{c1+1})→Gird2同位={c1ch}; "
                     f"{b}在Gird4位置({r2+1},{c2+1})→Gird3同位={c2ch}; 得到{c1ch}{c2ch}")
    lines.append(f"5) 拼接得到密文：{ciphertext}")
    return "\n".join(lines)


def explain_decrypt(ciphertext: str, plaintext: str, show_pairs: int = 3) -> str:
    c_clean = clean_text(ciphertext, remove_q=False)
    pairs = chunk2(c_clean)
    dec_pairs = chunk2(plaintext)
    k = min(show_pairs, len(pairs))
    lines = []
    lines.append("解密说明（按题面规则）：")
    lines.append(f"1) 清理后密文：{c_clean}")
    lines.append(f"2) 分组：{' '.join(pairs)}")
    lines.append("3) 示例映射（取前几组展示）：")
    for i in range(k):
        a, b = pairs[i][0], pairs[i][1]
        r1, c1 = POS2[a]
        r2, c2 = POS3[b]
        p1ch = GRID1[r1][c1]
        p2ch = GRID4[r2][c2]
        lines.append(f"  - {a}{b}: {a}在Gird2位置({r1+1},{c1+1})→Gird1同位={p1ch}; "
                     f"{b}在Gird3位置({r2+1},{c2+1})→Gird4同位={p2ch}; 得到{p1ch}{p2ch}")
    lines.append(f"4) 拼接得到明文：{plaintext}")
    return "\n".join(lines)


def rand_text(rng: random.Random, min_len: int, max_len: int, allow_q: bool) -> str:
    # For plaintext we may allow q in raw input; cleanup removes it.
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if allow_q else ALPHABET_NO_Q
    n = rng.randint(min_len, max_len)
    s = "".join(rng.choice(letters) for _ in range(n))
    # Optionally add some spaces/non-letters to test cleanup rendering
    if rng.random() < 0.35:
        # insert 1-3 separators
        seps = [" ", "-", "_", "  "]
        for _ in range(rng.randint(1, 3)):
            pos = rng.randint(0, len(s))
            s = s[:pos] + rng.choice(seps) + s[pos:]
    return s


def rand_cipher_from_plain(rng: random.Random) -> Tuple[str, str]:
    # Generate plaintext, encrypt it
    for _ in range(200):
        plain_raw = rand_text(rng, 8, 18, allow_q=True)
        try:
            c = encrypt(plain_raw)
            # ensure ciphertext non-trivial and length reasonable
            if 8 <= len(c) <= 40 and len(c) % 2 == 0:
                return plain_raw, c
        except Exception:
            continue
    raise RuntimeError("Failed to generate encryptable plaintext within limit.")


def rand_plain_from_cipher(rng: random.Random) -> Tuple[str, str]:
    # Generate plaintext, encrypt it to get ciphertext; then we ask to decrypt ciphertext.
    plain_raw, c = rand_cipher_from_plain(rng)
    p = decrypt(c)
    # p is cleaned+possibly padded plaintext
    return c, p


def make_problem(rng: random.Random, idx: int, used: set) -> Dict[str, Any]:
    # Mix question styles: sometimes provide both tasks, sometimes only one.
    style = rng.choices(
        population=["both", "encrypt_only", "decrypt_only"],
        weights=[0.55, 0.25, 0.20],
        k=1
    )[0]

    # Generate core data
    plain_raw, c_from_plain = rand_cipher_from_plain(rng)
    c_for_decrypt, p_from_cipher = rand_plain_from_cipher(rng)

    # Ensure decryption ciphertext differs from encryption ciphertext sometimes
    if rng.random() < 0.6 and c_for_decrypt == c_from_plain:
        c_for_decrypt, p_from_cipher = rand_plain_from_cipher(rng)

    # Build prompt in Chinese, self-contained, with grids.
    grids_txt = (
        "四个5×5方阵（不包含字母Q），按行列从1开始计数：\n"
        "Gird1：\n"
        "K L M N O\nP R S T U\nV W X Y Z\nA B C D E\nF G H I J\n"
        "Gird2：\n"
        "E C H O A\nB D F G I\nJ K L M N\nP R S T U\nV W X Y Z\n"
        "Gird3：\n"
        "V O R T E\nX A B C D\nF G H I J\nK L M N P\nS U W Y Z\n"
        "Gird4：\n"
        "K L M N O\nP R S T U\nV W X Y Z\nA B C D E\nF G H I J\n"
    )

    rule_txt = (
        "规则：\n"
        "1) 清理文本：去掉空格与非字母字符，转为大写；对“明文”额外删除所有字母Q。\n"
        "2) 加密：若清理后的明文长度为奇数，末尾补X；然后两两分组(p1p2)。\n"
        "   - 在Gird1中找到p1的位置(r,c)，取Gird2同位置的字母作为密文字母c1。\n"
        "   - 在Gird4中找到p2的位置(r,c)，取Gird3同位置的字母作为密文字母c2。\n"
        "   - 每组得到c1c2，拼接成最终密文。\n"
        "3) 解密：将密文两两分组(c1c2)。\n"
        "   - 在Gird2中找到c1的位置(r,c)，取Gird1同位置字母作为明文字母p1。\n"
        "   - 在Gird3中找到c2的位置(r,c)，取Gird4同位置字母作为明文字母p2。\n"
        "   - 拼接得到最终明文（注意：若原明文为奇数长度，加密时可能补了X）。\n"
        "输出格式：把最终结果用双中括号括起来，例如[[ABCDEF]]。\n"
    )

    if style == "both":
        problem = (
            f"题目{idx}：请根据下面方阵与规则完成加密与解密。\n\n"
            f"{grids_txt}\n{rule_txt}\n"
            f"(1) 明文：\"{plain_raw}\"\n"
            f"请给出加密结果：[[...]]\n"
            f"(2) 密文：\"{c_for_decrypt}\"\n"
            f"请给出解密结果：[[...]]\n"
        )
        enc_ans = c_from_plain
        dec_ans = p_from_cipher
        answer = f"[[{enc_ans}]]====[[{dec_ans}]]"
        explanation = (
            explain_encrypt(plain_raw, enc_ans, show_pairs=3)
            + "\n\n"
            + explain_decrypt(c_for_decrypt, dec_ans, show_pairs=3)
        )
        key = ("both", plain_raw, c_for_decrypt)
    elif style == "encrypt_only":
        problem = (
            f"题目{idx}：请根据下面方阵与规则完成加密。\n\n"
            f"{grids_txt}\n{rule_txt}\n"
            f"明文：\"{plain_raw}\"\n"
            f"请给出加密结果（双中括号）：[[...]]\n"
        )
        enc_ans = c_from_plain
        answer = f"[[{enc_ans}]]"
        explanation = explain_encrypt(plain_raw, enc_ans, show_pairs=4)
        key = ("enc", plain_raw)
    else:
        problem = (
            f"题目{idx}：请根据下面方阵与规则完成解密。\n\n"
            f"{grids_txt}\n{rule_txt}\n"
            f"密文：\"{c_for_decrypt}\"\n"
            f"请给出解密结果（双中括号）：[[...]]\n"
        )
        dec_ans = p_from_cipher
        answer = f"[[{dec_ans}]]"
        explanation = explain_decrypt(c_for_decrypt, dec_ans, show_pairs=4)
        key = ("dec", c_for_decrypt)

    if key in used:
        return None
    used.add(key)

    # Cross-check correctness with independent round-trip invariants
    try:
        if style in ("both", "encrypt_only"):
            # decrypt(encrypt(cleaned+padded)) equals cleaned+padded
            p_clean = clean_text(plain_raw, remove_q=True)
            if len(p_clean) % 2 == 1:
                p_clean += "X"
            if decrypt(c_from_plain) != p_clean:
                raise AssertionError("Round-trip check failed for encryption item.")
        if style in ("both", "decrypt_only"):
            # encrypt(decrypt(cipher)) equals cipher (after clean)
            c_clean = clean_text(c_for_decrypt, remove_q=False)
            if encrypt(decrypt(c_clean)) != c_clean:
                raise AssertionError("Round-trip check failed for decryption item.")
    except Exception as e:
        raise

    return {"problem": problem.strip(), "answer": answer, "explanation": explanation.strip()}


def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data)
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count must be positive")
    except Exception as e:
        print(f"Invalid input JSON. Expect {{\"seed\": int, \"count\": positive int}}. Error: {e}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)

    res = []
    used = set()
    attempts = 0
    max_attempts = 5000

    while len(res) < count and attempts < max_attempts:
        attempts += 1
        item = make_problem(rng, len(res) + 1, used)
        if item is None:
            continue
        # Basic non-empty checks
        if not item["problem"] or item["answer"] is None or item["explanation"] is None:
            continue
        res.append(item)

    if len(res) < count:
        print(f"Generation failed: only produced {len(res)}/{count} after {attempts} attempts.", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()