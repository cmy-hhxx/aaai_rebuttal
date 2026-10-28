import sys, json, random, re
from typing import List, Tuple, Dict, Any, Optional

# -----------------------------
# Polybius square (5x5) and O -> 66 special rule
# -----------------------------
GRID = [
    ["R", "T", "X", "F", "S"],
    ["W", "C", "M", "V", "H"],
    ["Z", "J", "A", "P", "B"],
    ["L", "Q", "Y", "G", "K"],
    ["N", "E", "U", "D", "I"],
]
CHAR_TO_CODE: Dict[str, str] = {}
CODE_TO_CHAR: Dict[str, str] = {}
for r in range(5):
    for c in range(5):
        ch = GRID[r][c]
        code = f"{r+1}{c+1}"
        CHAR_TO_CODE[ch] = code
        CODE_TO_CHAR[code] = ch

SPECIAL_O_CODE = "66"
SPECIAL_O_CHAR = "O"

ALPHABET = [chr(ord('A') + i) for i in range(26)]

# Letters allowed in square are exactly these (25 letters), plus 'O' special-cased.
SQUARE_LETTERS = set(CHAR_TO_CODE.keys())
ALL_PLAINTEXT_LETTERS = set(SQUARE_LETTERS) | {SPECIAL_O_CHAR}

# -----------------------------
# Cipher functions
# -----------------------------
def encrypt_polybius(plaintext: str) -> str:
    """Encrypt uppercase letters (no spaces/punct). O -> 66, others by rowcol."""
    out = []
    for ch in plaintext:
        if ch == SPECIAL_O_CHAR:
            out.append(SPECIAL_O_CODE)
        else:
            if ch not in CHAR_TO_CODE:
                raise ValueError(f"Plaintext contains unsupported letter: {ch}")
            out.append(CHAR_TO_CODE[ch])
    return "".join(out)

def decrypt_polybius(ciphertext: str) -> str:
    """Decrypt string of digits into uppercase letters. 66 -> O, otherwise rowcol."""
    if len(ciphertext) % 2 != 0:
        raise ValueError("Ciphertext length must be even (pairs of digits).")
    out = []
    for i in range(0, len(ciphertext), 2):
        pair = ciphertext[i:i+2]
        if pair == SPECIAL_O_CODE:
            out.append(SPECIAL_O_CHAR)
        else:
            if pair not in CODE_TO_CHAR:
                raise ValueError(f"Ciphertext contains invalid pair: {pair}")
            out.append(CODE_TO_CHAR[pair])
    return "".join(out)

# -----------------------------
# Helpers for generation
# -----------------------------
def rand_plaintext(rng: random.Random, min_len: int, max_len: int, o_prob: float) -> str:
    n = rng.randint(min_len, max_len)
    chars = []
    for _ in range(n):
        if rng.random() < o_prob:
            chars.append("O")
        else:
            # choose from square letters (exclude O which isn't in square anyway)
            chars.append(rng.choice(sorted(SQUARE_LETTERS)))
    # ensure at least one letter from square (always true) and maybe include O sometimes.
    return "".join(chars)

def rand_ciphertext_from_plain(rng: random.Random, min_len: int, max_len: int, o_prob: float) -> Tuple[str, str]:
    pt = rand_plaintext(rng, min_len, max_len, o_prob)
    ct = encrypt_polybius(pt)
    return pt, ct

def rand_ciphertext_direct(rng: random.Random, min_pairs: int, max_pairs: int, include_invalid: bool=False) -> str:
    """
    Generate a valid ciphertext consisting of 2-digit codes: 11..55 plus 66.
    (No invalid pairs). include_invalid kept for future but must be False.
    """
    if include_invalid:
        raise ValueError("This generator must not create invalid ciphertext pairs.")
    n = rng.randint(min_pairs, max_pairs)
    pairs = list(CODE_TO_CHAR.keys()) + [SPECIAL_O_CODE]
    return "".join(rng.choice(pairs) for _ in range(n))

def render_square() -> str:
    # Keep consistent with seed (table-like), in Chinese statement.
    header = "+----+----+----+----+----+----+\n"
    top = "|    | 1  | 2  | 3  | 4  | 5  |\n"
    sep = "+----+----+----+----+----+----+\n"
    rows = []
    for i, row in enumerate(GRID, start=1):
        rows.append(f"| {i}  | " + "  | ".join(row) + "  |\n")
    return header + top + sep + "".join(rows) + header

def format_problem_zh(pt: str, ct: str, ask_encrypt: bool, ask_decrypt: bool) -> str:
    rules = (
        "你需要按如下密码规则进行加密/解密，并严格按题目格式输出。\n\n"
        "### 密码规则（Polybius 方阵 + 特例）\n\n"
        "Polybius_square：\n"
        "```\n"
        f"{render_square()}"
        "```\n"
        "加密：\n"
        "- 输入：只含大写字母、无空格无标点的明文。\n"
        "- 对每个明文字母 p：\n"
        "  - 若 p 在方阵中，用其“行号列号”(从 1 开始计数)替换，例如行3列3记为 33。\n"
        "  - 特别地，字母 O 不在方阵中，规定替换为 66。\n"
        "解密：\n"
        "- 输入：由数字组成的密文串，按每两位一组读取。\n"
        "- 若两位数为 66，解为字母 O；否则按(行,列)在方阵中取对应字母。\n\n"
        "### 问题\n"
    )
    parts = [rules]
    idx = 1
    if ask_encrypt:
        parts.append(f"{idx}）明文：\"{pt}\"\n请给出加密后的密文，并用双层方括号包裹，例如：[[密文]]。\n")
        idx += 1
    if ask_decrypt:
        parts.append(f"{idx}）密文：\"{ct}\"\n请给出解密后的明文，并用双层方括号包裹，例如：[[明文]]。\n")
    return "\n".join(parts).strip()

def compute_answer(pt: str, ct: str, ask_encrypt: bool, ask_decrypt: bool) -> Any:
    out_parts = []
    if ask_encrypt:
        out_parts.append(f"[[{encrypt_polybius(pt)}]]")
    if ask_decrypt:
        out_parts.append(f"[[{decrypt_polybius(ct)}]]")
    if len(out_parts) == 1:
        return out_parts[0]
    return "====".join(out_parts)

def explanation_zh(pt: str, ct: str, ask_encrypt: bool, ask_decrypt: bool) -> str:
    expl = []
    if ask_encrypt:
        # show a few mapped pairs for audit
        mapped = []
        for ch in pt[:min(6, len(pt))]:
            code = SPECIAL_O_CODE if ch == "O" else CHAR_TO_CODE[ch]
            mapped.append(f"{ch}->{code}")
        ell = "..." if len(pt) > 6 else ""
        expl.append(
            "加密校验：按方阵把每个字母替换为(行号列号)，其中 O 特例为 66。"
            f" 例如前几位：{', '.join(mapped)}{ell}，拼接得到密文。"
        )
    if ask_decrypt:
        pairs = [ct[i:i+2] for i in range(0, len(ct), 2)]
        shown = pairs[:min(6, len(pairs))]
        mapped = []
        for p in shown:
            mapped.append(f"{p}->{('O' if p=='66' else CODE_TO_CHAR[p])}")
        ell = "..." if len(pairs) > 6 else ""
        expl.append(
            "解密校验：密文按每两位一组；66 解为 O，其它按(行,列)取方阵字母。"
            f" 例如前几组：{', '.join(mapped)}{ell}，拼接得到明文。"
        )
    return "\n".join(expl).strip()

# -----------------------------
# Validation / uniqueness checks
# -----------------------------
def validate_roundtrip(pt: str, ct: str) -> None:
    # encryption-decryption consistency
    enc = encrypt_polybius(pt)
    if enc != ct:
        raise AssertionError("Internal mismatch: encrypt(plaintext) != ciphertext")
    dec = decrypt_polybius(ct)
    if dec != pt:
        raise AssertionError("Internal mismatch: decrypt(ciphertext) != plaintext")

def validate_ciphertext(ct: str) -> None:
    if not re.fullmatch(r"\d+", ct or ""):
        raise ValueError("Ciphertext must be digits only.")
    if len(ct) % 2 != 0:
        raise ValueError("Ciphertext must have even length.")
    for i in range(0, len(ct), 2):
        pair = ct[i:i+2]
        if pair != SPECIAL_O_CODE and pair not in CODE_TO_CHAR:
            raise ValueError(f"Invalid pair in ciphertext: {pair}")

def validate_plaintext(pt: str) -> None:
    if not re.fullmatch(r"[A-Z]+", pt or ""):
        raise ValueError("Plaintext must be uppercase letters only.")
    for ch in pt:
        if ch not in ALL_PLAINTEXT_LETTERS:
            raise ValueError(f"Unsupported plaintext letter: {ch}")

# -----------------------------
# Instance generation (multiple families)
# -----------------------------
def gen_instance(rng: random.Random) -> Dict[str, Any]:
    """
    Generate one problem; may ask:
    - only encryption
    - only decryption
    - both (two subquestions)
    """
    family = rng.choices(
        population=["both", "enc_only", "dec_only"],
        weights=[0.45, 0.30, 0.25],
        k=1
    )[0]

    # sizes vary by family
    if family == "both":
        pt1 = rand_plaintext(rng, 8, 14, o_prob=0.18)
        validate_plaintext(pt1)
        ct1 = encrypt_polybius(pt1)

        ct2 = rand_ciphertext_direct(rng, 9, 14)
        validate_ciphertext(ct2)
        pt2 = decrypt_polybius(ct2)

        problem = format_problem_zh(pt1, ct2, ask_encrypt=True, ask_decrypt=True)
        answer = f"[[{ct1}]]====[[{pt2}]]"
        expl = (
            explanation_zh(pt1, ct2, ask_encrypt=True, ask_decrypt=True)
        )
        # Cross-checks (independent paths: encrypt then decrypt and direct decrypt)
        if decrypt_polybius(ct1) != pt1:
            raise AssertionError("Cross-check failed on encryption part.")
        if encrypt_polybius(pt2) != ct2:
            raise AssertionError("Cross-check failed on decryption part.")
        return {"problem": problem, "answer": answer, "explanation": expl}

    if family == "enc_only":
        pt = rand_plaintext(rng, 10, 18, o_prob=0.22)
        validate_plaintext(pt)
        ct = encrypt_polybius(pt)
        # Cross-check: decrypt back
        if decrypt_polybius(ct) != pt:
            raise AssertionError("Cross-check failed: decrypt(encrypt(pt)) != pt")
        problem = format_problem_zh(pt, "", ask_encrypt=True, ask_decrypt=False)
        answer = f"[[{ct}]]"
        expl = explanation_zh(pt, "", ask_encrypt=True, ask_decrypt=False)
        return {"problem": problem, "answer": answer, "explanation": expl}

    # dec_only
    ct = rand_ciphertext_direct(rng, 10, 18)
    validate_ciphertext(ct)
    pt = decrypt_polybius(ct)
    # Cross-check: encrypt back
    if encrypt_polybius(pt) != ct:
        raise AssertionError("Cross-check failed: encrypt(decrypt(ct)) != ct")
    problem = format_problem_zh("", ct, ask_encrypt=False, ask_decrypt=True)
    answer = f"[[{pt}]]"
    expl = explanation_zh("", ct, ask_encrypt=False, ask_decrypt=True)
    return {"problem": problem, "answer": answer, "explanation": expl}

def signature(item: Dict[str, Any]) -> str:
    # prevent duplicates by hashing normalized problem content
    return item["problem"].strip()

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
    except Exception as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 0))
    if count <= 0:
        print("count must be a positive integer", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)

    results: List[Dict[str, Any]] = []
    seen = set()

    max_attempts = 20000
    attempts = 0
    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = gen_instance(rng)
            sig = signature(item)
            if sig in seen:
                continue
            # final sanity: problem non-empty, answer present
            if not isinstance(item.get("problem"), str) or not item["problem"].strip():
                raise AssertionError("Empty problem.")
            # answer can be string; keep as JSON value (string)
            if "answer" not in item:
                raise AssertionError("Missing answer.")
            if not isinstance(item.get("explanation"), str) or not item["explanation"].strip():
                raise AssertionError("Empty explanation.")
            seen.add(sig)
            results.append(item)
        except Exception as e:
            # resample
            continue

    if len(results) < count:
        print(f"Generation failed: only generated {len(results)}/{count} after {attempts} attempts.", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()