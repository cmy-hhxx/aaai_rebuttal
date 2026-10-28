import sys, json, random, string
from typing import List, Tuple, Dict, Any

REELS = [
    "ABCEIGDJFVUYMHTQKZOLRXSPWN",
    "ACDEHFIJKTLMOUVYGZNPQXRWSB",
    "ADKOMJUBGEPHSCZINXFYQRTVWL",
    "AEDCBIFGJHLKMRUOQVPTNWYXZS",
    "AFNQUKDOPITJBRHCYSLWEMZVXG",
    "AGPOCIXLURNDYZHWBJSQFKVMET",
    "AHXJEZBNIKPVROGSYDULCFMQTW",
    "AIHPJOBWKCVFZLQERYNSUMGTDX",
    "AJDSKQOIVTZEFHGYUNLPMBXWCR",
    "AKELBDFJGHONMTPRQSVZUXYWIC",
    "ALTMSXVQPNOHUWDIZYCGKRFBEJ",
    "AMNFLHQGCUJTBYPZKXISRDVEWO",
    "ANCJILDHBMKGXUZTSWQYVORPFE",
    "AODWPKJVIUQHZCTXBLEGNYRSMF",
    "APBVHIYKSGUENTCXOWFQDRLJZM",
    "AQJNUBTGIMWZRVLXCSHDEOKFPY",
    "ARMYOFTHEUSZJXDPCWGQIBKLNV",
    "ASDMCNEQBOZPLGVJRKYTFUIWXH",
    "ATOJYLFXNGWHVCMIRBSEKUPDZQ",
    "AUTRZXQLYIOVBPESNHJWMDGFCK",
    "AVNKHRGOXEYBFSJMUDQCLZWTIP",
    "AWVSFDLIEBHKNRJQZGMXPUCOTY",
    "AXKWREVDTUFOYHMLSIQNJCPGBZ",
    "AYJPXMVKBQWUGLOSTECHNZFRID",
    "AZDNBUHYFWJLVGRCQMPSOEXTKI",
]

ALPHABET = string.ascii_uppercase
REEL_COUNT = len(REELS)

def build_maps(reels: List[str]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Return (enc_map_list, dec_map_list) for each reel."""
    enc_maps = []
    dec_maps = []
    for r in reels:
        if sorted(r) != list(ALPHABET):
            raise ValueError("Invalid reel: must be a permutation of A-Z")
        enc = {}
        dec = {}
        n = len(r)
        for i, ch in enumerate(r):
            enc[ch] = r[(i + 1) % n]
            dec[ch] = r[(i - 1) % n]
        enc_maps.append(enc)
        dec_maps.append(dec)
    return enc_maps, dec_maps

ENC_MAPS, DEC_MAPS = build_maps(REELS)

def encrypt(plaintext: str) -> str:
    if not plaintext or any(c not in ALPHABET for c in plaintext):
        raise ValueError("Plaintext must be non-empty uppercase A-Z only.")
    out = []
    for i, p in enumerate(plaintext):
        reel_idx = i % REEL_COUNT
        out.append(ENC_MAPS[reel_idx][p])
    return "".join(out)

def decrypt(ciphertext: str) -> str:
    if not ciphertext or any(c not in ALPHABET for c in ciphertext):
        raise ValueError("Ciphertext must be non-empty uppercase A-Z only.")
    out = []
    for i, c in enumerate(ciphertext):
        reel_idx = i % REEL_COUNT
        out.append(DEC_MAPS[reel_idx][c])
    return "".join(out)

def rand_text(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(ALPHABET) for _ in range(n))

def make_problem_variant(rng: random.Random) -> Dict[str, Any]:
    """
    Generate one self-contained problem with two sub-questions:
    1) Encrypt given plaintext
    2) Decrypt given ciphertext
    Return JSON object: {problem, answer, explanation}
    """
    # Choose lengths with variability; ensure not too short.
    len1 = rng.randint(8, 16)
    len2 = rng.randint(8, 16)

    # Generate plaintext and ciphertext by construction (guarantees solvable).
    plaintext = rand_text(rng, len1)
    ciphertext_for_decrypt = rand_text(rng, len2)

    enc_ans = encrypt(plaintext)
    dec_ans = decrypt(ciphertext_for_decrypt)

    # Cross-check with inverse relationship using independent property tests:
    # decrypt(encrypt(x)) == x and encrypt(decrypt(y)) == y for these instances.
    # This uses both functions, but verifies the cipher bijection at the instance level.
    if decrypt(enc_ans) != plaintext:
        raise AssertionError("Internal check failed: decrypt(encrypt(plaintext)) mismatch")
    if encrypt(dec_ans) != ciphertext_for_decrypt:
        raise AssertionError("Internal check failed: encrypt(decrypt(ciphertext)) mismatch")

    # Build concise, checkable explanation: show first few character mappings with reel numbers.
    def explain_encrypt_steps(pt: str, ct: str, k: int = 4) -> str:
        k = min(k, len(pt))
        lines = []
        for i in range(k):
            reel_idx = i % REEL_COUNT
            r = REELS[reel_idx]
            p = pt[i]
            c = ct[i]
            pos = r.index(p)
            nxt = r[(pos + 1) % 26]
            lines.append(f"  第{i+1}位用转轮{reel_idx+1}：在该转轮中 {p} 的下一字母是 {nxt}，因此密文字母为 {c}。")
        if len(pt) > k:
            lines.append(f"  后续位置同理，转轮按 1→2→…→25→1 循环。")
        return "\n".join(lines)

    def explain_decrypt_steps(ct: str, pt: str, k: int = 4) -> str:
        k = min(k, len(ct))
        lines = []
        for i in range(k):
            reel_idx = i % REEL_COUNT
            r = REELS[reel_idx]
            c = ct[i]
            p = pt[i]
            pos = r.index(c)
            prev = r[(pos - 1) % 26]
            lines.append(f"  第{i+1}位用转轮{reel_idx+1}：在该转轮中 {c} 的前一字母是 {prev}，因此明文字母为 {p}。")
        if len(ct) > k:
            lines.append(f"  后续位置同理，转轮按 1→2→…→25→1 循环。")
        return "\n".join(lines)

    problem = (
        "你需要按照如下“转轮替换”密码规则完成加密与解密。\n\n"
        "规则摘要（与题目中给出的转轮一致）：\n"
        "- 有 25 个转轮（Reel1~Reel25），每个转轮是一串包含 A~Z 的排列。\n"
        "- 加密：从 Reel1 开始，第 i 个字符使用 Reel((i-1) mod 25 + 1)。在该转轮上找到明文字母，替换为其“下一个”字母（末尾回到开头）。\n"
        "- 解密：同样的转轮选择规则，但把密文字母替换为其“上一个”字母（开头回到末尾）。\n\n"
        f"问题：\n"
        f"1）明文：\"{plaintext}\"  请给出加密结果，用双中括号包裹，例如 [[...]]。\n"
        f"2）密文：\"{ciphertext_for_decrypt}\"  请给出解密结果，用双中括号包裹，例如 [[...]]。\n"
    )

    answer_str = f"[[{enc_ans}]]====[[{dec_ans}]]"

    explanation = (
        "加密与解密均按位置轮换转轮（第1位Reel1，第2位Reel2，…，第25位Reel25，第26位回到Reel1）。\n\n"
        "（1）加密校验示例（展示前几位）：\n"
        f"{explain_encrypt_steps(plaintext, enc_ans)}\n\n"
        "（2）解密校验示例（展示前几位）：\n"
        f"{explain_decrypt_steps(ciphertext_for_decrypt, dec_ans)}\n\n"
        "一致性自检：对本题生成的字符串满足 decrypt(encrypt(明文))=明文 且 encrypt(decrypt(密文))=密文。"
    )

    return {"problem": problem, "answer": answer_str, "explanation": explanation}

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))
    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)

    results = []
    seen = set()
    max_tries = 2000
    tries = 0

    while len(results) < count and tries < max_tries:
        tries += 1
        obj = make_problem_variant(rng)
        key = (obj["problem"], obj["answer"])
        if key in seen:
            continue
        seen.add(key)
        results.append(obj)

    if len(results) < count:
        print(f"生成失败：仅生成 {len(results)}/{count} 道（已尝试 {tries} 次）", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()