import sys, json, math, random
from typing import List, Tuple, Dict, Any, Optional

# We generate RSA-like per-character "encryption/decryption" puzzles:
# Given e,n, the rule says both encryption and decryption use exponent e mod n.
# For the task to be well-defined (invertible as described), we construct instances
# where applying pow(x,e,n) twice returns x for all plaintext character codes used.
#
# Method:
# - Choose primes p,q from a small pool; set n=p*q.
# - Choose exponent e such that e^2 ≡ 1 (mod lcm(p-1,q-1)).
#   Then for any x coprime to n: (x^e)^e ≡ x (mod n).
# - Ensure all plaintext ASCII codes are coprime with n (and ciphertext too).
#
# We then:
# - Part 1: ask to encrypt a generated plaintext.
# - Part 2: ask to decrypt a generated ciphertext list.
# Answer format: [[enc_list]]====[[dec_text]]
#
# Cross-check:
# - Verify encrypt(plaintext) and decrypt(ciphertext) via pow.
# - Verify involution on all used codes: pow(pow(x,e,n),e,n) == x.
# - Ensure uniqueness: deterministic mapping per char, so OK.

PRIMES_POOL = [
    101, 103, 107, 109, 113, 127, 131, 137, 139, 149,
    151, 157, 163, 167, 173, 179, 181, 191, 193, 197,
    199, 211, 223, 227, 229, 233, 239, 241, 251, 257
]

UPPER = [chr(i) for i in range(ord('A'), ord('Z') + 1)]

def lcm(a: int, b: int) -> int:
    return a // math.gcd(a, b) * b

def pick_distinct_primes(rng: random.Random) -> Tuple[int, int]:
    p = rng.choice(PRIMES_POOL)
    q = rng.choice([x for x in PRIMES_POOL if x != p])
    return p, q

def find_involutive_e(rng: random.Random, lam: int) -> int:
    # Need e^2 ≡ 1 (mod lam), and gcd(e, lam) = 1.
    # Trivial solutions: e ≡ 1 or e ≡ -1 mod lam. To add variety, we search others too.
    candidates = set()
    candidates.add(1)
    candidates.add(lam - 1)
    # Also try random odd numbers; keep those satisfying condition.
    for _ in range(5000):
        e = rng.randrange(2, lam - 1)
        if math.gcd(e, lam) != 1:
            continue
        if (e * e) % lam == 1:
            candidates.add(e)
        if len(candidates) >= 8:
            break
    cand_list = sorted(candidates)
    # Prefer non-trivial if available
    non_trivial = [e for e in cand_list if e not in (1, lam - 1)]
    if non_trivial:
        return rng.choice(non_trivial)
    return rng.choice(cand_list)

def encrypt_text(plaintext: str, e: int, n: int) -> List[int]:
    out = []
    for ch in plaintext:
        x = ord(ch)
        out.append(pow(x, e, n))
    return out

def decrypt_nums(cipher_nums: List[int], e: int, n: int) -> str:
    chars = []
    for c in cipher_nums:
        z = pow(c, e, n)
        # Must map back to uppercase letter ASCII
        chars.append(chr(z))
    return "".join(chars)

def all_coprime_ascii(plaintext: str, n: int) -> bool:
    for ch in plaintext:
        if math.gcd(ord(ch), n) != 1:
            return False
    return True

def validate_involution_on_used(plaintext: str, cipher_nums: List[int], e: int, n: int) -> bool:
    # Check pow(pow(x,e),e) = x for all plaintext codes and ciphertext nums (when interpreted mod n)
    for ch in plaintext:
        x = ord(ch)
        if pow(pow(x, e, n), e, n) != x % n:
            return False
    for c in cipher_nums:
        if pow(pow(c % n, e, n), e, n) != c % n:
            return False
    return True

def gen_plaintext(rng: random.Random, length: int) -> str:
    # Avoid too repetitive strings; ensure at least 6 distinct letters if length allows
    if length <= 6:
        return "".join(rng.choice(UPPER) for _ in range(length))
    distinct_needed = min(8, max(6, length // 2))
    letters = rng.sample(UPPER, distinct_needed)
    rest = [rng.choice(UPPER) for _ in range(length - distinct_needed)]
    arr = letters + rest
    rng.shuffle(arr)
    return "".join(arr)

def gen_instance(rng: random.Random) -> Dict[str, Any]:
    # Choose modulus and exponent
    for attempt in range(2000):
        p, q = pick_distinct_primes(rng)
        n = p * q
        lam = lcm(p - 1, q - 1)
        e = find_involutive_e(rng, lam)

        # Choose lengths and texts
        L1 = rng.randrange(8, 15)   # plaintext length for encryption question
        L2 = rng.randrange(9, 16)   # plaintext length for generating ciphertext for decryption question

        pt1 = gen_plaintext(rng, L1)
        pt2 = gen_plaintext(rng, L2)

        if not all_coprime_ascii(pt1, n):
            continue
        if not all_coprime_ascii(pt2, n):
            continue

        ct1 = encrypt_text(pt1, e, n)
        ct2 = encrypt_text(pt2, e, n)

        # Ensure decryption maps to uppercase letters (i.e., z is uppercase ASCII)
        # Since pt2 are uppercase, decrypt(ct2)=pt2 if involution holds.
        dec2 = decrypt_nums(ct2, e, n)
        if dec2 != pt2:
            continue

        # Validate involution on used values
        if not validate_involution_on_used(pt1, ct1, e, n):
            continue
        if not validate_involution_on_used(pt2, ct2, e, n):
            continue

        # Format ciphertext string with commas (no spaces)
        ct2_str = ",".join(str(x) for x in ct2)

        # Also check ct2 numbers are in [0, n-1]
        if any((x < 0 or x >= n) for x in ct2):
            continue

        return {
            "p": p, "q": q, "n": n, "e": e,
            "plaintext_ask": pt1,
            "cipher_for_decrypt": ct2_str,
            "enc_answer": ct1,
            "dec_answer": pt2
        }
    raise RuntimeError("生成失败：无法在尝试次数内构造满足自反解密条件的参数(e,n)。")

def render_problem(inst: Dict[str, Any], language: str) -> str:
    e = inst["e"]
    n = inst["n"]
    pt = inst["plaintext_ask"]
    ct = inst["cipher_for_decrypt"]

    # Chinese statement, self-contained and consistent with the seed's rule (using ^ as multiplication/pow wording).
    # We keep "x^e mod n" but clarify it's exponentiation mod.
    return (
        "你是一名擅长加密与解密的助手。请严格按照下面的密码规则完成两问，并按要求输出格式。\n\n"
        "### 密码规则\n\n"
        "**加密：**\n"
        "- 输入：明文为不含空格与标点的英文大写字母串。\n"
        "- 输出：密文为用英文逗号`,`分隔的一串数字，例如 \"y1,y2,…\"。\n"
        "- 参数：e = {e}，n = {n}。\n"
        "- 步骤：对明文中每个字母 p：\n"
        "  1) 取其 ASCII 十进制码 x。\n"
        "  2) 计算 y = x^e mod n（这里表示模幂运算）。\n"
        "  3) 该 y 即该字母对应的密文数字。\n"
        "  最终用逗号连接所有 y 得到密文。\n\n"
        "**解密：**\n"
        "- 输入：密文为用逗号分隔的一串数字。\n"
        "- 输出：明文为英文大写字母串。\n"
        "- 参数：e = {e}，n = {n}。\n"
        "- 步骤：对密文中每个数字 c：\n"
        "  1) 计算 z = c^e mod n（模幂运算）。\n"
        "  2) 将 z 视为 ASCII 十进制码并转成对应的大写字母。\n"
        "  最终拼接得到明文。\n\n"
        "### 问题\n"
        "1) 明文：\"{pt}\"。请给出加密结果，外层用双中括号包裹，例如：[[1,2,3]]。\n"
        "2) 密文：\"{ct}\"。请给出解密结果，外层用双中括号包裹，例如：[[ABC]]。\n"
    ).format(e=e, n=n, pt=pt, ct=ct)

def render_explanation(inst: Dict[str, Any]) -> str:
    e, n = inst["e"], inst["n"]
    pt1 = inst["plaintext_ask"]
    ct1 = inst["enc_answer"]
    ct2_str = inst["cipher_for_decrypt"]
    pt2 = inst["dec_answer"]

    # Provide checkable evidence: show first 2-3 character computations for each part.
    show_k = min(3, len(pt1))
    enc_snips = []
    for i in range(show_k):
        ch = pt1[i]
        x = ord(ch)
        y = ct1[i]
        enc_snips.append(f"{ch}(x={x}) -> y = {x}^{e} mod {n} = {y}")
    # For decryption show first 3 numbers
    ct2_list = [int(s) for s in ct2_str.split(",") if s]
    show_k2 = min(3, len(ct2_list))
    dec_snips = []
    for i in range(show_k2):
        c = ct2_list[i]
        z = pow(c, e, n)
        dec_snips.append(f"c={c} -> z = {c}^{e} mod {n} = {z} -> '{chr(z)}'")

    return (
        "要点：逐字符做模幂运算。\n"
        "（1）加密示例校验（展示前几位）：\n- " + "\n- ".join(enc_snips) + "\n"
        f"因此明文 \"{pt1}\" 的密文为 {ct1}。\n\n"
        "（2）解密示例校验（展示前几位）：\n- " + "\n- ".join(dec_snips) + "\n"
        f"因此密文 \"{ct2_str}\" 解密得到 \"{pt2}\"。\n"
    )

def format_answer(inst: Dict[str, Any]) -> str:
    enc = inst["enc_answer"]
    dec = inst["dec_answer"]
    return f"[[{','.join(str(x) for x in enc)}]]====[[{dec}]]"

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])

    rng = random.Random(seed)

    results = []
    seen = set()

    # bounded attempts to avoid infinite loops
    max_total_attempts = max(2000, count * 200)

    attempts = 0
    while len(results) < count and attempts < max_total_attempts:
        attempts += 1
        inst = gen_instance(rng)
        # Deduplicate by (e,n,plaintext_ask,cipher_for_decrypt)
        key = (inst["e"], inst["n"], inst["plaintext_ask"], inst["cipher_for_decrypt"])
        if key in seen:
            continue
        seen.add(key)

        problem = render_problem(inst, "zh")
        answer = format_answer(inst)
        explanation = render_explanation(inst)

        # final sanity checks
        # - verify encryption and decryption correctness
        enc_check = encrypt_text(inst["plaintext_ask"], inst["e"], inst["n"])
        if enc_check != inst["enc_answer"]:
            print("内部校验失败：加密不一致", file=sys.stderr)
            continue
        ct2_list = [int(s) for s in inst["cipher_for_decrypt"].split(",") if s]
        dec_check = decrypt_nums(ct2_list, inst["e"], inst["n"])
        if dec_check != inst["dec_answer"]:
            print("内部校验失败：解密不一致", file=sys.stderr)
            continue

        results.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    if len(results) != count:
        raise RuntimeError(f"未能生成足够题目：需要 {count}，实际 {len(results)}。")

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()