import sys, json, random, string
from typing import Dict, List, Tuple, Any, Optional

# -----------------------------
# Morse + pair mapping (fixed by rule)
# -----------------------------
MORSE: Dict[str, str] = {
    'A': '.-',     'B': '-...',   'C': '-.-.',   'D': '-..',
    'E': '.',      'F': '..-.',   'G': '--.',    'H': '....',
    'I': '..',     'J': '.---',   'K': '-.-',    'L': '.-..',
    'M': '--',     'N': '-.',     'O': '---',    'P': '.--.',
    'Q': '--.-',   'R': '.-.',    'S': '...',    'T': '-',
    'U': '..-',    'V': '...-',   'W': '.--',    'X': '-..-',
    'Y': '-.--',   'Z': '--..',
}

PAIR_TO_DIGIT: Dict[str, str] = {
    '..': '5',
    '.-': '4',
    './': '9',
    '-.': '8',
    '--': '6',
    '-/': '7',
    '/.': '3',
    '/-': '1',
    '//': '2',
}
DIGIT_TO_PAIR: Dict[str, str] = {v: k for k, v in PAIR_TO_DIGIT.items()}

ALPHABET = string.ascii_uppercase


def encrypt_plaintext(plaintext: str) -> str:
    # Build morse with / separator between letters
    morse = "/".join(MORSE[ch] for ch in plaintext)
    # Pair up characters
    out = []
    i = 0
    while i + 1 < len(morse):
        pair = morse[i:i+2]
        if pair not in PAIR_TO_DIGIT:
            # Should not happen if rule is consistent
            raise ValueError(f"Unexpected pair {pair!r} in morse stream {morse!r}")
        out.append(PAIR_TO_DIGIT[pair])
        i += 2
    # If odd length, append last char unchanged (non-numeric)
    if i < len(morse):
        out.append(morse[-1])
    return "".join(out)


def decrypt_ciphertext(ciphertext: str) -> str:
    # Convert each digit to pair; if last char is non-digit, leave it unprocessed as-is
    morse_chars = []
    for ch in ciphertext:
        if ch.isdigit():
            if ch not in DIGIT_TO_PAIR:
                raise ValueError(f"Digit {ch} not in mapping")
            morse_chars.append(DIGIT_TO_PAIR[ch])
        else:
            # "not processed" -> append the raw char to morse stream
            morse_chars.append(ch)
    morse = "".join(morse_chars)
    # Split by /
    parts = morse.split("/")
    # Convert each morse part to letter
    inv = {v: k for k, v in MORSE.items()}
    letters = []
    for p in parts:
        if p == "":
            # This would indicate malformed morse (double // in letter boundaries beyond encoding)
            raise ValueError(f"Malformed morse stream split produced empty token: {morse!r}")
        if p not in inv:
            raise ValueError(f"Unknown morse token {p!r} from morse stream {morse!r}")
        letters.append(inv[p])
    return "".join(letters)


def is_valid_plaintext(s: str) -> bool:
    return len(s) > 0 and all('A' <= c <= 'Z' for c in s)


def is_valid_ciphertext(s: str) -> bool:
    # numeric string possibly ending with one non-digit from {'.','-','/'}
    if not s:
        return False
    for c in s[:-1]:
        if not c.isdigit():
            return False
    if s[-1].isdigit():
        return True
    return s[-1] in {'.', '-', '/'}


def make_plaintext(rng: random.Random, min_len: int, max_len: int) -> str:
    n = rng.randint(min_len, max_len)
    return "".join(rng.choice(ALPHABET) for _ in range(n))


def make_ciphertext_from_plaintext(rng: random.Random, min_len: int, max_len: int) -> Tuple[str, str]:
    pt = make_plaintext(rng, min_len, max_len)
    ct = encrypt_plaintext(pt)
    return pt, ct


def make_plaintext_from_ciphertext(rng: random.Random, min_letters: int, max_letters: int) -> Tuple[str, str]:
    # Generate plaintext, encrypt to ciphertext; then ask to decrypt ciphertext (guaranteed decodable)
    pt = make_plaintext(rng, min_letters, max_letters)
    ct = encrypt_plaintext(pt)
    # Optionally spice: sometimes append a single non-digit tail by ensuring odd-length morse happens naturally
    # Odd-length morse happens when total morse length is odd.
    # We'll just accept ct as produced.
    return ct, pt


def explain_encrypt(pt: str, ct: str) -> str:
    morse = "/".join(MORSE[ch] for ch in pt)
    # show first few pairs to keep explanation short and checkable
    pairs = [morse[i:i+2] for i in range(0, len(morse)-1, 2)]
    mapped = [PAIR_TO_DIGIT[p] for p in pairs]
    tail = morse[-1] if len(morse) % 2 == 1 else ""
    preview_k = min(8, len(pairs))
    exp = []
    exp.append(f"先将明文逐字转为摩斯码并用“/”分隔：{morse}")
    if pairs:
        exp.append(f"按顺序每2个字符分组（展示前{preview_k}组）："
                   f"{' '.join(pairs[:preview_k])}"
                   + ("" if len(pairs) <= preview_k else " ..."))
        exp.append(f"按映射表转为数字（对应前{preview_k}组）："
                   f"{' '.join(mapped[:preview_k])}"
                   + ("" if len(mapped) <= preview_k else " ..."))
    if tail:
        exp.append(f"因摩斯码总长度为奇数，最后剩余字符“{tail}”不映射，直接追加到密文末尾。")
    exp.append(f"得到密文：{ct}")
    return "\n".join(exp)


def explain_decrypt(ct: str, pt: str) -> str:
    # Reconstruct morse for explanation
    morse_chars = []
    for ch in ct:
        if ch.isdigit():
            morse_chars.append(DIGIT_TO_PAIR[ch])
        else:
            morse_chars.append(ch)
    morse = "".join(morse_chars)
    parts = morse.split("/")
    preview_k = min(6, len(parts))
    exp = []
    exp.append(f"将密文数字逐位按表还原为2字符并拼接；若末尾有非数字字符则保留不处理，得到摩斯串：{morse}")
    exp.append(f"按“/”切分为字母摩斯码（展示前{preview_k}段）："
               f"{' | '.join(parts[:preview_k])}"
               + ("" if len(parts) <= preview_k else " ..."))
    exp.append(f"逐段查摩斯表还原得到明文：{pt}")
    return "\n".join(exp)


def render_problem_zh(mode: str, payload: Dict[str, str]) -> str:
    # mode in {"enc", "dec", "both"}
    rule = (
        "给定一种加/解密规则：\n"
        "1) 先把明文（仅大写字母）逐字母替换成摩斯码，并用“/”分隔字母。\n"
        "2) 将得到的整段摩斯码字符串按顺序每2个字符分组；若总长度为奇数，则最后剩下的1个字符不做映射，直接追加到密文末尾。\n"
        "3) 每个2字符分组按下表映射成1位数字：\n"
        "   '..'→5  '.-'→4  './'→9  '-.'→8  '--'→6  '-/'→7  '/.'→3  '/-'→1  '//'→2\n"
        "4) 解密为上述过程的逆过程：数字→2字符分组→拼回摩斯串→按“/”切分→查摩斯表还原字母。\n"
        "摩斯表：A .-  B -...  C -.-.  D -..  E .  F ..-.  G --.  H ....  I ..  J .---  "
        "K -.-  L .-..  M --  N -.  O ---  P .--.  Q --.-  R .-.  S ...  T -  U ..-  "
        "V ...-  W .--  X -..-  Y -.--  Z --..\n"
    )
    if mode == "enc":
        return (
            rule
            + f"\n问题：\n对明文 \"{payload['plaintext']}\" 进行加密。请将密文用双中括号括起来输出，例如 [[密文]]。"
        )
    if mode == "dec":
        return (
            rule
            + f"\n问题：\n对密文 \"{payload['ciphertext']}\" 进行解密。请将明文用双中括号括起来输出，例如 [[明文]]。"
        )
    # both
    return (
        rule
        + "\n问题：\n"
        + f"1) 明文：\"{payload['plaintext']}\"，请加密并用双中括号输出 [[密文]]。\n"
        + f"2) 密文：\"{payload['ciphertext']}\"，请解密并用双中括号输出 [[明文]]。\n"
        + "请按格式输出：[[第1问答案]]====[[第2问答案]]"
    )


def generate_one(rng: random.Random, seen: set) -> Dict[str, Any]:
    # Choose family: enc-only / dec-only / both
    mode = rng.choices(["enc", "dec", "both"], weights=[4, 4, 2], k=1)[0]

    # Scale sizes a bit
    if mode == "both":
        pt1 = make_plaintext(rng, 8, 14)
        ct1 = encrypt_plaintext(pt1)
        ct2, pt2 = make_plaintext_from_ciphertext(rng, 8, 14)
        signature = ("both", pt1, ct2)
        if signature in seen:
            raise ValueError("duplicate")
        seen.add(signature)
        problem = render_problem_zh("both", {"plaintext": pt1, "ciphertext": ct2})
        answer = f"[[{ct1}]]====[[{pt2}]]"
        explanation = "第1问：\n" + explain_encrypt(pt1, ct1) + "\n\n第2问：\n" + explain_decrypt(ct2, pt2)
        # Cross-check
        if decrypt_ciphertext(ct1) != pt1:
            raise AssertionError("encrypt/decrypt mismatch on q1")
        if encrypt_plaintext(pt2) != ct2:
            raise AssertionError("encrypt/decrypt mismatch on q2")
        return {"problem": problem, "answer": answer, "explanation": explanation}

    if mode == "enc":
        pt, ct = make_ciphertext_from_plaintext(rng, 8, 18)
        signature = ("enc", pt)
        if signature in seen:
            raise ValueError("duplicate")
        seen.add(signature)
        problem = render_problem_zh("enc", {"plaintext": pt})
        answer = f"[[{ct}]]"
        explanation = explain_encrypt(pt, ct)
        if decrypt_ciphertext(ct) != pt:
            raise AssertionError("encrypt/decrypt mismatch")
        return {"problem": problem, "answer": answer, "explanation": explanation}

    # dec
    ct, pt = make_plaintext_from_ciphertext(rng, 8, 18)
    signature = ("dec", ct)
    if signature in seen:
        raise ValueError("duplicate")
    seen.add(signature)
    problem = render_problem_zh("dec", {"ciphertext": ct})
    answer = f"[[{pt}]]"
    explanation = explain_decrypt(ct, pt)
    if encrypt_plaintext(pt) != ct:
        raise AssertionError("encrypt/decrypt mismatch")
    return {"problem": problem, "answer": answer, "explanation": explanation}


def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 1))
    if count <= 0:
        print("count must be positive", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    seen = set()
    out: List[Dict[str, Any]] = []

    # Bounded resampling
    attempts = 0
    max_attempts = 2000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng, seen)
            # basic sanity checks
            if not isinstance(item.get("problem"), str) or not item["problem"].strip():
                raise AssertionError("empty problem")
            if not isinstance(item.get("explanation"), str) or not item["explanation"].strip():
                raise AssertionError("empty explanation")
            out.append(item)
        except ValueError:
            # duplicate -> resample
            continue
        except Exception as e:
            print(f"Generation error at attempt {attempts}: {e}", file=sys.stderr)
            continue

    if len(out) != count:
        print(f"Failed to generate enough items: got {len(out)} / {count} after {attempts} attempts",
              file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()