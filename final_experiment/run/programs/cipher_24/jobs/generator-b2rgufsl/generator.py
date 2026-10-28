import sys, json, random
from typing import List, Dict, Any, Tuple

K_DEFAULT = 12

# ---------- Utilities ----------
def rand_upper(rng: random.Random, n: int) -> str:
    return "".join(chr(rng.randint(ord("A"), ord("Z"))) for _ in range(n))

def encrypt(plaintext: str, k: int) -> List[int]:
    return [ord(ch) * k for ch in plaintext]

def decrypt(cipher_nums: List[int], k: int) -> str:
    # Per rule: z = c // k; then ASCII
    return "".join(chr(c // k) for c in cipher_nums)

def fmt_cipher(nums: List[int]) -> str:
    return ",".join(str(x) for x in nums)

def parse_cipher(s: str) -> List[int]:
    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    return [int(p) for p in parts]

def wrap_double_square(s: str) -> str:
    return f"[[{s}]]"

def make_problem_text_zh(mode: str,
                         k: int,
                         plaintext: str = None,
                         ciphertext_str: str = None) -> str:
    # Self-contained description in Chinese, including ASCII mention and integer division.
    intro = (
        "你是一名擅长加密与解密的智能助手。请严格按以下规则计算，并按要求输出。\n\n"
        "【密码规则】\n"
        f"- 常量 k_q_x = {k}\n"
        "- 明文：只包含大写英文字母（A-Z），无空格与标点。\n"
        "- 密文：用英文逗号分隔的一串十进制整数，例如 \"y1,y2,...\"。\n\n"
        "【加密】\n"
        "- 对明文中的每个字母 p：取其 ASCII 十进制码 x=ord(p)，计算 y=x*k_q_x。\n"
        "- 依次输出所有 y，用逗号连接得到密文。\n\n"
        "【解密】\n"
        "- 对密文中的每个整数 c：计算 z = c // k_q_x（// 为整除，去掉小数部分）。\n"
        "- 将 z 视为 ASCII 十进制码，转回字符 p=chr(z)。\n"
        "- 依次连接所有 p 得到明文。\n\n"
    )
    if mode == "enc":
        q = (
            f"问题：对下列明文进行加密，并用双层方括号包裹最终密文。\n"
            f"1) 明文：\"{plaintext}\"\n"
            "输出格式示例：[[12,34,56]]\n"
        )
    else:
        q = (
            f"问题：对下列密文进行解密，并用双层方括号包裹最终明文。\n"
            f"2) 密文：\"{ciphertext_str}\"\n"
            "输出格式示例：[[ABC]]\n"
        )
    return intro + q

def explanation_zh_enc(plaintext: str, k: int, cipher: List[int]) -> str:
    # Provide a few concrete steps and a checksum-like verification.
    steps = []
    show_n = min(3, len(plaintext))
    for i in range(show_n):
        ch = plaintext[i]
        steps.append(f"{ch}: ord={ord(ch)}，乘以{k} 得 {ord(ch)}*{k}={ord(ch)*k}")
    if len(plaintext) > show_n:
        steps.append("其余字符同理。")
    # simple verifiable summary
    total = sum(cipher)
    return (
        "加密过程：对每个字母取 ASCII 十进制码并乘以 k_q_x。\n"
        + "示例计算（前若干位）：\n- " + "\n- ".join(steps) + "\n"
        f"得到密文序列（用逗号连接）。校验：所有密文数之和为 {total}。"
    )

def explanation_zh_dec(cipher_nums: List[int], k: int, plaintext: str) -> str:
    steps = []
    show_n = min(3, len(cipher_nums))
    for i in range(show_n):
        c = cipher_nums[i]
        z = c // k
        steps.append(f"{c}//{k}={z}，chr({z})='{chr(z)}'")
    if len(cipher_nums) > show_n:
        steps.append("其余数字同理。")
    # verify back-encrypt
    reenc = encrypt(plaintext, k)
    ok = (reenc == cipher_nums)
    return (
        "解密过程：对每个数字做整除 c//k_q_x 得到 ASCII 码，再转字符。\n"
        + "示例计算（前若干位）：\n- " + "\n- ".join(steps) + "\n"
        f"得到明文：\"{plaintext}\"。\n"
        f"回代校验：将该明文按加密规则重新加密，结果与给定密文{'一致' if ok else '不一致'}。"
    )

# ---------- Generation Families ----------
def gen_enc_instance(rng: random.Random) -> Dict[str, Any]:
    # Randomize k and length; ensure uppercase letters.
    k = rng.choice([3, 4, 5, 6, 8, 10, 12, 15, 16, 18, 20, 24, 25, 30])
    n = rng.randint(6, 14)
    plaintext = rand_upper(rng, n)
    cipher = encrypt(plaintext, k)
    problem = make_problem_text_zh("enc", k, plaintext=plaintext)
    answer = wrap_double_square(fmt_cipher(cipher))
    explanation = explanation_zh_enc(plaintext, k, cipher)
    return {"problem": problem, "answer": answer, "explanation": explanation}

def gen_dec_instance(rng: random.Random) -> Dict[str, Any]:
    k = rng.choice([3, 4, 5, 6, 8, 10, 12, 15, 16, 18, 20, 24, 25, 30])
    n = rng.randint(6, 14)
    plaintext = rand_upper(rng, n)
    cipher = encrypt(plaintext, k)
    cipher_str = fmt_cipher(cipher)
    problem = make_problem_text_zh("dec", k, ciphertext_str=cipher_str)
    answer = wrap_double_square(plaintext)
    explanation = explanation_zh_dec(cipher, k, plaintext)
    return {"problem": problem, "answer": answer, "explanation": explanation}

def canonical_signature(item: Dict[str, Any]) -> str:
    # Avoid duplicates deterministically based on problem text.
    return item["problem"]

def self_check_item(item: Dict[str, Any]) -> None:
    # Basic correctness checks by re-solving from the rendered problem data is hard;
    # instead verify internal consistency: if answer looks like cipher, validate with explanation rules.
    # We'll parse the item to determine if it's enc or dec.
    prob = item["problem"]
    ans = item["answer"]
    if not (isinstance(prob, str) and prob.strip()):
        raise ValueError("Empty problem")
    if not (isinstance(ans, str) and ans.startswith("[[") and ans.endswith("]]")):
        raise ValueError("Answer not wrapped in double square brackets")
    # Extract k from problem
    marker = "常量 k_q_x = "
    i = prob.find(marker)
    if i == -1:
        raise ValueError("k not found in problem")
    j = prob.find("\n", i)
    k_str = prob[i + len(marker): j].strip()
    k = int(k_str)
    if "1) 明文：" in prob:
        # encryption question
        pfx = '1) 明文："'
        a = prob.find(pfx)
        b = prob.find('"', a + len(pfx))
        plaintext = prob[a + len(pfx): b]
        cipher = encrypt(plaintext, k)
        expected = wrap_double_square(fmt_cipher(cipher))
        if ans != expected:
            raise ValueError("Encryption answer mismatch")
    elif "2) 密文：" in prob:
        pfx = '2) 密文："'
        a = prob.find(pfx)
        b = prob.find('"', a + len(pfx))
        cipher_str = prob[a + len(pfx): b]
        nums = parse_cipher(cipher_str)
        plaintext = decrypt(nums, k)
        expected = wrap_double_square(plaintext)
        if ans != expected:
            raise ValueError("Decryption answer mismatch")
        # Extra: check divisibility for clean ASCII (not required by rule, but for sanity)
        for c in nums:
            if c % k != 0:
                # Still decryptable with //, but may not round-trip; avoid such cases
                raise ValueError("Cipher contains non-multiple of k; rejected by generator constraints")
    else:
        raise ValueError("Unknown problem type")

# ---------- Main ----------
def generate(seed: int, count: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    out = []
    seen = set()
    attempts = 0
    max_attempts = 5000

    # Mix families to create diversity
    while len(out) < count and attempts < max_attempts:
        attempts += 1
        family = rng.choices(["enc", "dec"], weights=[0.5, 0.5], k=1)[0]
        item = gen_enc_instance(rng) if family == "enc" else gen_dec_instance(rng)
        sig = canonical_signature(item)
        if sig in seen:
            continue
        # Self-check correctness
        try:
            self_check_item(item)
        except Exception as e:
            print(f"[stderr] self_check failed: {e}", file=sys.stderr)
            continue
        seen.add(sig)
        out.append(item)

    if len(out) < count:
        raise RuntimeError(f"Failed to generate enough unique items: got {len(out)}/{count} after {attempts} attempts")
    return out

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    res = generate(seed, count)
    json.dump(res, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()