import sys, json, random, hashlib, string

HEX_LOWER = "0123456789abcdef"

KEY_HEX = "73ef2a4edd7a7fbf07fd5f6faf99674dc0c25a025fd74c221f4c35849e5c0fb3"
KEY_BYTES = bytes.fromhex(KEY_HEX)


def xor_bytes(data: bytes, key: bytes) -> bytes:
    out = bytearray(len(data))
    kl = len(key)
    for i, b in enumerate(data):
        out[i] = b ^ key[i % kl]
    return bytes(out)


def encrypt_upper_plaintext_to_hex(plaintext: str) -> str:
    # plaintext: uppercase letters only, no spaces/punctuation
    data = plaintext.encode("ascii")
    enc = xor_bytes(data, KEY_BYTES)
    return enc.hex()


def decrypt_hex_to_upper_plaintext(cipher_hex: str) -> str:
    data = bytes.fromhex(cipher_hex)
    dec = xor_bytes(data, KEY_BYTES)
    return dec.decode("ascii")


def is_upper_letters(s: str) -> bool:
    return len(s) > 0 and all("A" <= c <= "Z" for c in s)


def is_lower_hex(s: str) -> bool:
    return len(s) > 0 and all(c in HEX_LOWER for c in s)


def format_problem(plain: str, cipher: str, language: str = "zh") -> str:
    # Keep rules self-contained and consistent.
    if language == "zh":
        return (
            "你是一名擅长加密与解密的助手。请严格按如下密码规则进行计算，并按指定格式输出。\n\n"
            "【密码规则】\n"
            "1) 明文：仅由大写英文字母 A-Z 组成，不含空格与标点。\n"
            "2) 密文：小写十六进制字符串（0-9 与 a-f）。\n"
            "3) 密钥：对字符串 \"SECRET_KEY\" 做 SHA-256 得到十六进制：\n"
            f"   {KEY_HEX}\n"
            "   将该十六进制转为 32 字节作为密钥字节序列。\n"
            "4) 加密：将明文按 ASCII 编码为字节序列；逐字节与密钥循环对齐后做 XOR；结果转为十六进制小写输出。\n"
            "5) 解密：将密文十六进制转为字节序列；逐字节与同一密钥循环 XOR；结果按 ASCII 解码得到明文。\n\n"
            "【问题】\n"
            f"1) 明文：\"{plain}\"\n"
            "   请给出对应密文，使用双层方括号包裹，例如 [[...]]。\n"
            f"2) 密文：\"{cipher}\"\n"
            "   请给出对应明文，使用双层方括号包裹，例如 [[...]]。\n\n"
            "请仅输出形如：[[第1问答案]]====[[第2问答案]]"
        )
    else:
        # Fallback English (not expected per user's setting).
        return (
            "Follow the cipher rules and output in the required format.\n"
            f"Key SHA-256(\"SECRET_KEY\") = {KEY_HEX}\n"
            f"1) Plaintext: \"{plain}\" (output ciphertext as [[...]]).\n"
            f"2) Ciphertext: \"{cipher}\" (output plaintext as [[...]]).\n"
            "Output only: [[ans1]]====[[ans2]]"
        )


def build_explanation(plain: str, cipher_from_plain: str, cipher: str, plain_from_cipher: str, language: str = "zh") -> str:
    if language == "zh":
        # Provide verifiable evidence: show first few XOR byte computations and cross-check.
        # Show first 3 bytes for each part.
        p_bytes = plain.encode("ascii")
        c1_bytes = bytes.fromhex(cipher_from_plain)
        k = KEY_BYTES

        def byte_triplet_demo(data_bytes, out_bytes, offset=0, n=3):
            items = []
            for i in range(min(n, len(data_bytes))):
                b = data_bytes[i]
                kb = k[(offset + i) % len(k)]
                ob = out_bytes[i]
                items.append(f"第{i+1}字节: 0x{b:02x} XOR 0x{kb:02x} = 0x{ob:02x}")
            return "；".join(items)

        demo1 = byte_triplet_demo(p_bytes, c1_bytes, 0, 3)

        c2_bytes = bytes.fromhex(cipher)
        p2_bytes = plain_from_cipher.encode("ascii")
        demo2 = byte_triplet_demo(c2_bytes, p2_bytes, 0, 3)

        # Cross-check: decrypt(encrypt(plain)) == plain
        cross_plain = decrypt_hex_to_upper_plaintext(cipher_from_plain)
        ok = (cross_plain == plain)

        return (
            "要点：密钥为给定 SHA-256 十六进制转 32 字节，逐字节循环与数据 XOR。\n"
            f"第1问校验示例（展示前3个字节 XOR）：{demo1}。\n"
            f"第2问校验示例（展示前3个字节 XOR）：{demo2}。\n"
            f"一致性检查：对第1问所得密文再解密应还原明文，结果为 \"{cross_plain}\"，"
            f"{'与原明文一致' if ok else '与原明文不一致（生成应被拒绝）'}。"
        )
    else:
        return "XOR with repeating key; verified by decrypt(encrypt(plain)) == plain."


def sample_upper_string(rng: random.Random, min_len: int, max_len: int) -> str:
    n = rng.randint(min_len, max_len)
    alphabet = string.ascii_uppercase
    return "".join(rng.choice(alphabet) for _ in range(n))


def generate_instance(rng: random.Random, language: str = "zh"):
    """
    Create a 2-part task:
    (1) encrypt a plaintext
    (2) decrypt a ciphertext
    Ensure: plaintext is uppercase letters; ciphertext hex lowercase; decryption yields uppercase letters.
    """
    # Part 1 plaintext
    plain = sample_upper_string(rng, 8, 16)
    cipher_from_plain = encrypt_upper_plaintext_to_hex(plain)

    # Part 2: create ciphertext by encrypting another uppercase plaintext, then give ciphertext to decrypt.
    # This ensures decrypted plaintext is valid uppercase letters.
    plain2 = sample_upper_string(rng, 7, 14)
    cipher2 = encrypt_upper_plaintext_to_hex(plain2)

    # Validate formats
    assert is_upper_letters(plain)
    assert is_lower_hex(cipher_from_plain)
    assert is_lower_hex(cipher2)
    assert is_upper_letters(decrypt_hex_to_upper_plaintext(cipher2))

    problem = format_problem(plain, cipher2, language=language)
    answer = f"[[{cipher_from_plain}]]====[[{plain2}]]"
    explanation = build_explanation(plain, cipher_from_plain, cipher2, plain2, language=language)

    # Additional public-consistency checks
    # 1) encrypt->decrypt roundtrip
    if decrypt_hex_to_upper_plaintext(cipher_from_plain) != plain:
        raise ValueError("Roundtrip check failed for part 1.")
    # 2) decrypt(cipher2) must equal plain2
    if decrypt_hex_to_upper_plaintext(cipher2) != plain2:
        raise ValueError("Decryption check failed for part 2.")

    return {"problem": problem, "answer": answer, "explanation": explanation}


def main():
    raw = sys.stdin.read()
    try:
        inp = json.loads(raw)
    except Exception as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    seed = int(inp.get("seed", 0))
    count = int(inp.get("count", 0))
    if count <= 0:
        print("count must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    # Language: prefer user's requested language; default zh
    language = inp.get("output_language", "zh") or "zh"

    rng = random.Random(seed)

    out = []
    seen = set()
    attempts = 0
    max_attempts = 2000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        item = generate_instance(rng, language=language)
        sig = hashlib.sha256((item["problem"] + "\n" + item["answer"]).encode("utf-8")).hexdigest()
        if sig in seen:
            continue
        seen.add(sig)
        out.append(item)

    if len(out) < count:
        print(f"Failed to generate enough unique problems: got {len(out)}/{count}", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()