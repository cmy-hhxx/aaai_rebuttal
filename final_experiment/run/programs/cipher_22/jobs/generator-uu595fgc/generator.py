import sys, json, random, string
from typing import List, Tuple, Dict, Any

KEY = b"1234567890ABCDEF"

S_BOX = {
    0x00: 0x0F, 0x01: 0x0A, 0x02: 0x07, 0x03: 0x05,
    0x04: 0x09, 0x05: 0x03, 0x06: 0x0D, 0x07: 0x00,
    0x08: 0x0E, 0x09: 0x08, 0x0A: 0x04, 0x0B: 0x06,
    0x0C: 0x01, 0x0D: 0x02, 0x0E: 0x0B, 0x0F: 0x0C
}

INV_S_BOX = {
    0x0F: 0x00, 0x0A: 0x01, 0x07: 0x02, 0x05: 0x03,
    0x09: 0x04, 0x03: 0x05, 0x0D: 0x06, 0x00: 0x07,
    0x0E: 0x08, 0x08: 0x09, 0x04: 0x0A, 0x06: 0x0B,
    0x01: 0x0C, 0x02: 0x0D, 0x0B: 0x0E, 0x0C: 0x0F
}


def rotl1(b: int) -> int:
    b &= 0xFF
    return ((b << 1) & 0xFF) | ((b >> 7) & 0x01)


def rotr1(b: int) -> int:
    b &= 0xFF
    return ((b >> 1) & 0x7F) | ((b & 0x01) << 7)


def sub_byte(b: int, box: Dict[int, int]) -> int:
    hi = (b >> 4) & 0xF
    lo = b & 0xF
    return ((box[hi] & 0xF) << 4) | (box[lo] & 0xF)


def xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes([x ^ y for x, y in zip(a, b)])


def pad8(data: bytes) -> bytes:
    pad_len = (-len(data)) % 8
    if pad_len:
        data += b"\x00" * pad_len
    return data


def chunks(data: bytes, n: int) -> List[bytes]:
    return [data[i:i + n] for i in range(0, len(data), n)]


def encrypt_bytes(plain: bytes) -> bytes:
    plain_padded = pad8(plain)
    out = bytearray()
    for block in chunks(plain_padded, 8):
        x1 = xor_bytes(block, KEY[:8])
        s = bytes([sub_byte(b, S_BOX) for b in x1])
        p = bytes([rotl1(b) for b in s])
        c = xor_bytes(p, KEY[:8])
        out.extend(c)
    return bytes(out)


def decrypt_bytes(cipher: bytes) -> bytes:
    if len(cipher) % 8 != 0:
        raise ValueError("cipher length must be multiple of 8 bytes")
    out = bytearray()
    for block in chunks(cipher, 8):
        x1 = xor_bytes(block, KEY[:8])
        ip = bytes([rotr1(b) for b in x1])
        s = bytes([sub_byte(b, INV_S_BOX) for b in ip])
        p = xor_bytes(s, KEY[:8])
        out.extend(p)
    # remove trailing \x00 padding
    return bytes(out).rstrip(b"\x00")


def to_hex_upper(data: bytes) -> str:
    return data.hex().upper()


def from_hex(s: str) -> bytes:
    # Accept mixed case input; but questions will present A-F uppercase
    s = s.strip()
    return bytes.fromhex(s)


ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "


def rand_plaintext(rng: random.Random, min_len: int, max_len: int) -> str:
    L = rng.randint(min_len, max_len)
    # avoid all spaces and avoid leading/trailing too many spaces
    while True:
        s = "".join(rng.choice(ALPHABET) for _ in range(L))
        if any(ch != " " for ch in s):
            return s


def make_explanation_encrypt(pt: str, ct_hex: str) -> str:
    b = pt.encode("ascii")
    pad_len = (-len(b)) % 8
    padded_len = len(b) + pad_len
    blocks = padded_len // 8
    return (
        "按题面规则加密：\n"
        f"1) 明文长度={len(b)} 字节，按 8 字节对齐需填充 {pad_len} 个 \\x00，填充后长度={padded_len}，共 {blocks} 个分组。\n"
        "2) 每个 8 字节分组依次执行：与固定 KEY 异或 → S_BOX 对每个字节高/低 4 bit 代换 → 每字节左旋 1 bit → 再与 KEY 异或。\n"
        f"3) 将所有密文字节转为十六进制并拼接，得到：{ct_hex}\n"
    )


def make_explanation_decrypt(ct_hex: str, pt: str) -> str:
    cbytes = from_hex(ct_hex)
    blocks = len(cbytes) // 8
    return (
        "按题面规则解密：\n"
        f"1) 密文为十六进制串，换为字节后长度={len(cbytes)}，共 {blocks} 个 8 字节分组。\n"
        "2) 每分组执行：与 KEY 异或 → 每字节右旋 1 bit（逆置换） → INV_S_BOX 代换 → 再与 KEY 异或。\n"
        "3) 拼接得到明文字节并去除末尾 \\x00 填充。\n"
        f"4) 最终明文：{pt}\n"
    )


def format_problem_encrypt_only(pt: str) -> str:
    return (
        "你需要按以下分组密码规则进行**加密**，输出十六进制密文（A-F 需大写），并用双中括号包裹答案。\n\n"
        "固定参数：\n"
        "- KEY = b'1234567890ABCDEF'\n"
        "- S_BOX（对每字节高 4 bit 与低 4 bit 分别代换后再拼接）：\n"
        "  0x0->0xF, 0x1->0xA, 0x2->0x7, 0x3->0x5,\n"
        "  0x4->0x9, 0x5->0x3, 0x6->0xD, 0x7->0x0,\n"
        "  0x8->0xE, 0x9->0x8, 0xA->0x4, 0xB->0x6,\n"
        "  0xC->0x1, 0xD->0x2, 0xE->0xB, 0xF->0xC\n\n"
        "加密步骤（对整段明文）：\n"
        "1) 若明文（ASCII，大写字母与空格）长度不是 8 字节倍数，用 \\x00 进行尾部填充到 8 的倍数。\n"
        "2) 按 8 字节分组；每组依次：\n"
        "   a. 分组与 KEY（取前 8 字节）逐字节 XOR\n"
        "   b. 每字节做 S_BOX 代换（高/低 4 bit 分别代换）\n"
        "   c. 每字节循环左移 1 bit\n"
        "   d. 结果再与 KEY（取前 8 字节）逐字节 XOR\n"
        "3) 所有密文字节转为十六进制并拼接（A-F 大写）。\n\n"
        f"明文：\"{pt}\"\n\n"
        "请给出密文：[[...]]\n"
    )


def format_problem_decrypt_only(ct_hex: str) -> str:
    return (
        "你需要按以下分组密码规则进行**解密**，输出明文（ASCII，大写字母与空格），并用双中括号包裹答案。\n\n"
        "固定参数：\n"
        "- KEY = b'1234567890ABCDEF'\n"
        "- INV_S_BOX（S_BOX 的逆代换，亦对高/低 4 bit 分别代换后再拼接）：\n"
        "  0xF->0x0, 0xA->0x1, 0x7->0x2, 0x5->0x3,\n"
        "  0x9->0x4, 0x3->0x5, 0xD->0x6, 0x0->0x7,\n"
        "  0xE->0x8, 0x8->0x9, 0x4->0xA, 0x6->0xB,\n"
        "  0x1->0xC, 0x2->0xD, 0xB->0xE, 0xC->0xF\n\n"
        "解密步骤（对整段密文）：\n"
        "1) 将十六进制串转为字节；按 8 字节分组（每组对应 16 个十六进制字符）。\n"
        "2) 每组依次：\n"
        "   a. 分组与 KEY（取前 8 字节）逐字节 XOR\n"
        "   b. 每字节循环右移 1 bit（逆置换）\n"
        "   c. 每字节做 INV_S_BOX 代换（高/低 4 bit 分别代换）\n"
        "   d. 结果再与 KEY（取前 8 字节）逐字节 XOR\n"
        "3) 将得到的字节按 ASCII 解码，并去掉末尾所有 \\x00 填充。\n\n"
        f"密文：\"{ct_hex}\"\n\n"
        "请给出明文：[[...]]\n"
    )


def format_problem_both(pt: str, ct_hex: str) -> str:
    return (
        "下面给出同一套分组密码的规则。你需要分别完成 1) 加密 与 2) 解密。\n"
        "所有十六进制输出要求 A-F 大写；答案格式为：\n"
        "[[第1问答案]]====[[第2问答案]]\n\n"
        "固定参数：\n"
        "- KEY = b'1234567890ABCDEF'\n"
        "- S_BOX：0x0->0xF, 0x1->0xA, 0x2->0x7, 0x3->0x5, 0x4->0x9, 0x5->0x3, 0x6->0xD, 0x7->0x0, 0x8->0xE, 0x9->0x8, 0xA->0x4, 0xB->0x6, 0xC->0x1, 0xD->0x2, 0xE->0xB, 0xF->0xC\n"
        "- INV_S_BOX：0xF->0x0, 0xA->0x1, 0x7->0x2, 0x5->0x3, 0x9->0x4, 0x3->0x5, 0xD->0x6, 0x0->0x7, 0xE->0x8, 0x8->0x9, 0x4->0xA, 0x6->0xB, 0x1->0xC, 0x2->0xD, 0xB->0xE, 0xC->0xF\n\n"
        "加密：明文 ASCII（仅大写字母与空格），末尾用 \\x00 填充到 8 字节倍数；按 8 字节分组：XOR KEY → S_BOX 代换（高/低 4bit）→ 每字节左旋 1bit → XOR KEY；最后转十六进制拼接。\n"
        "解密：十六进制转字节后按 8 字节分组：XOR KEY → 每字节右旋 1bit → INV_S_BOX 代换 → XOR KEY；ASCII 解码后去除末尾 \\x00。\n\n"
        f"1) 明文：\"{pt}\"\n"
        f"2) 密文：\"{ct_hex}\"\n"
    )


def solve_encrypt(pt: str) -> str:
    ct = encrypt_bytes(pt.encode("ascii"))
    return to_hex_upper(ct)


def solve_decrypt(ct_hex: str) -> str:
    pt = decrypt_bytes(from_hex(ct_hex)).decode("ascii")
    # enforce output alphabet; if not, raise
    for ch in pt:
        if ch not in ALPHABET:
            raise ValueError("decrypted plaintext contains invalid characters")
    return pt


def self_check_roundtrip(pt: str) -> None:
    ct_hex = solve_encrypt(pt)
    back = solve_decrypt(ct_hex)
    if back != pt:
        raise AssertionError("roundtrip mismatch")


def gen_case(rng: random.Random) -> Dict[str, Any]:
    mode = rng.choices(
        ["enc", "dec", "both"],
        weights=[0.40, 0.40, 0.20],
        k=1
    )[0]

    # choose length bands to diversify padding / block counts
    band = rng.choices(
        ["short", "exact8", "two_blocks", "three_blocks"],
        weights=[0.35, 0.20, 0.30, 0.15],
        k=1
    )[0]
    if band == "short":
        min_len, max_len = 1, 15
    elif band == "exact8":
        min_len, max_len = 8, 8
    elif band == "two_blocks":
        min_len, max_len = 9, 16
    else:
        min_len, max_len = 17, 24

    pt1 = rand_plaintext(rng, min_len, max_len)
    self_check_roundtrip(pt1)

    if mode == "enc":
        ct_hex = solve_encrypt(pt1)
        # cross-check by decrypting
        if solve_decrypt(ct_hex) != pt1:
            raise AssertionError("encrypt/decrypt cross-check failed")
        problem = format_problem_encrypt_only(pt1)
        answer = f"[[{ct_hex}]]"
        explanation = make_explanation_encrypt(pt1, ct_hex)
        return {"problem": problem, "answer": answer, "explanation": explanation}

    if mode == "dec":
        # generate ciphertext by encrypting a fresh plaintext, maybe different band
        pt2 = rand_plaintext(rng, min_len, max_len)
        self_check_roundtrip(pt2)
        ct_hex2 = solve_encrypt(pt2)
        # cross-check by encrypting decrypted result
        if solve_encrypt(solve_decrypt(ct_hex2)) != ct_hex2:
            raise AssertionError("decrypt/encrypt cross-check failed")
        problem = format_problem_decrypt_only(ct_hex2)
        answer = f"[[{pt2}]]"
        explanation = make_explanation_decrypt(ct_hex2, pt2)
        return {"problem": problem, "answer": answer, "explanation": explanation}

    # both
    ct_hex1 = solve_encrypt(pt1)
    if solve_decrypt(ct_hex1) != pt1:
        raise AssertionError("both: enc check failed")

    pt3 = rand_plaintext(rng, min_len, max_len)
    self_check_roundtrip(pt3)
    ct_hex3 = solve_encrypt(pt3)

    problem = format_problem_both(pt1, ct_hex3)
    answer = f"[[{ct_hex1}]]====[[{pt3}]]"
    explanation = (
        "第1问按加密流程计算得到密文；第2问按解密流程还原明文。\n\n"
        "第1问校验：将第1问密文再按解密流程处理，应还原为原明文。\n"
        f"- 明文：{pt1}\n"
        f"- 密文：{ct_hex1}\n\n"
        "第2问校验：将第2问解出的明文再按加密流程处理，应回到原密文。\n"
        f"- 密文：{ct_hex3}\n"
        f"- 明文：{pt3}\n"
    )
    return {"problem": problem, "answer": answer, "explanation": explanation}


def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        print(f"输入不是合法 JSON：{e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(req, dict) or "seed" not in req or "count" not in req:
        print("输入 JSON 需包含 seed 与 count 字段", file=sys.stderr)
        sys.exit(1)

    seed = req["seed"]
    count = req["count"]
    if not isinstance(seed, int) or not isinstance(count, int) or count <= 0:
        print("seed 必须是整数；count 必须是正整数", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)

    out = []
    seen = set()
    max_attempts = 2000
    attempts = 0
    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = gen_case(rng)
        except Exception as e:
            # resample on generation failure
            continue
        sig = (item["problem"], item["answer"])
        if sig in seen:
            continue
        # basic non-empty checks
        if not item["problem"].strip() or item["answer"] is None or not str(item["answer"]).strip():
            continue
        seen.add(sig)
        out.append(item)

    if len(out) < count:
        print(f"生成失败：仅生成 {len(out)}/{count} 道题（尝试 {attempts} 次）", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()