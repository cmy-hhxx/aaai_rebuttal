import sys, json, random, string
from typing import Dict, Tuple, List

# --- Cipher definition (fixed) ---
GRID = [
    list("MZSDP"),
    list("KNFLQ"),
    list("GAOXU"),
    list("WRYVC"),
    list("BTEHI"),
]
ROW_HEADERS = "MKGWB"   # first letter of each row
COL_FOOTERS = "BTEHI"   # last row letters, used as column footers

# Build lookup maps
POS: Dict[str, Tuple[int, int]] = {}
for r in range(5):
    for c in range(5):
        POS[GRID[r][c]] = (r, c)

ROW_INDEX: Dict[str, int] = {ch: i for i, ch in enumerate(ROW_HEADERS)}
COL_INDEX: Dict[str, int] = {ch: j for j, ch in enumerate(COL_FOOTERS)}

ALPHABET_25 = "".join([ch for ch in string.ascii_uppercase if ch != "J"])
ALLOWED_PLAINTEXT_CHARS = set(ALPHABET_25)
ALLOWED_C1 = set(ROW_HEADERS)
ALLOWED_C2 = set(COL_FOOTERS)

def normalize_plaintext(s: str) -> str:
    s = "".join(ch for ch in s.upper() if 'A' <= ch <= 'Z')
    s = s.replace("J", "")  # rule says remove J
    return s

def encrypt(plaintext: str) -> str:
    pt = normalize_plaintext(plaintext)
    out = []
    for ch in pt:
        if ch not in POS:
            # Should not happen due to J removal and grid coverage
            raise ValueError(f"plaintext contains unsupported letter: {ch}")
        r, c = POS[ch]
        out.append(ROW_HEADERS[r])
        out.append(COL_FOOTERS[c])
    return "".join(out)

def decrypt(ciphertext: str) -> str:
    ct = "".join(ch for ch in ciphertext.upper() if 'A' <= ch <= 'Z')
    if len(ct) % 2 != 0:
        raise ValueError("ciphertext length must be even (two letters per plaintext letter).")
    out = []
    for i in range(0, len(ct), 2):
        c1, c2 = ct[i], ct[i+1]
        if c1 not in ROW_INDEX or c2 not in COL_INDEX:
            raise ValueError(f"ciphertext contains invalid pair letters: {c1}{c2}")
        r = ROW_INDEX[c1]
        c = COL_INDEX[c2]
        out.append(GRID[r][c])
    return "".join(out)

def explain_encrypt(pt: str, ct: str, max_show: int = 6) -> str:
    pt_n = normalize_plaintext(pt)
    pairs = []
    for ch in pt_n[:max_show]:
        r, c = POS[ch]
        pairs.append(f"{ch}->({ROW_HEADERS[r]}{COL_FOOTERS[c]})")
    more = "" if len(pt_n) <= max_show else f" …（共{len(pt_n)}个字母）"
    return (
        "加密：逐字母查表，输出“行首字母+列底字母”。\n"
        f"示例映射：{', '.join(pairs)}{more}\n"
        f"得到密文：{ct}"
    )

def explain_decrypt(ct: str, pt: str, max_show: int = 6) -> str:
    ct_n = "".join(ch for ch in ct.upper() if 'A' <= ch <= 'Z')
    pairs = []
    for i in range(0, min(len(ct_n), 2*max_show), 2):
        c1, c2 = ct_n[i], ct_n[i+1]
        r = ROW_INDEX[c1]
        c = COL_INDEX[c2]
        pairs.append(f"{c1}{c2}->{GRID[r][c]}")
    more = "" if len(ct_n) <= 2*max_show else f" …（共{len(ct_n)//2}对）"
    return (
        "解密：每两字母一组，第一字母定行（行首字母），第二字母定列（列底字母），取交叉格字母。\n"
        f"示例映射：{', '.join(pairs)}{more}\n"
        f"得到明文：{pt}"
    )

def render_problem(pt: str, ct: str, lang: str = "zh") -> str:
    # Keep it self-contained: include grid and rules succinctly.
    grid_lines = "\n".join([
        "M Z S D P",
        "K N F L Q",
        "G A O X U",
        "W R Y V C",
        "B T E H I",
    ])
    if lang == "zh":
        return (
            "你需要按如下固定密码规则进行加密/解密（不需要任何外部信息）。\n\n"
            "5x5 字母表（行列从0开始计数）：\n"
            f"{grid_lines}\n\n"
            f"行首标识（每行第1个字母组成）：{ROW_HEADERS}\n"
            f"列底标识（每列最底部字母组成）：{COL_FOOTERS}\n\n"
            "加密：明文仅含大写字母；先去掉非字母字符并删除字母J。对明文每个字母p：\n"
            "1) 在表中找到p的位置(行r,列c)；2) 输出 行首标识[r] + 列底标识[c] 作为两字母密文。\n"
            "将所有两字母密文依次连接得到最终密文。\n\n"
            "解密：密文每两字母(c1,c2)一组：c1确定行（它必须是某行的行首标识），c2确定列（它必须是某列的列底标识），\n"
            "取该行该列交叉处的字母作为明文，连接得到最终明文。\n\n"
            "问题：\n"
            f"1）明文：\"{pt}\"。请给出加密结果，用双中括号包裹：[[...]]\n"
            f"2）密文：\"{ct}\"。请给出解密结果，用双中括号包裹：[[...]]"
        )
    else:
        # Default to Chinese per requirement; keep fallback minimal.
        return render_problem(pt, ct, "zh")

def make_instance(rng: random.Random) -> Tuple[str, str, str, str]:
    # Generate plaintext (no J) and a valid ciphertext (even length, valid symbols)
    pt_len = rng.randint(8, 14)
    pt = "".join(rng.choice(ALPHABET_25) for _ in range(pt_len))

    # For ciphertext, either encrypt another random plaintext or sample valid pairs directly
    mode = rng.choice(["from_pt", "pairs"])
    if mode == "from_pt":
        pt2_len = rng.randint(9, 15)
        pt2 = "".join(rng.choice(ALPHABET_25) for _ in range(pt2_len))
        ct = encrypt(pt2)
    else:
        pairs_n = rng.randint(10, 16)
        ct = "".join(rng.choice(ROW_HEADERS) + rng.choice(COL_FOOTERS) for _ in range(pairs_n))

    return pt, encrypt(pt), ct, decrypt(ct)

def canonical_key(problem: str) -> str:
    # For de-dup: normalize whitespace
    return " ".join(problem.split())

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    output_language = data.get("output_language", "zh")

    results = []
    seen = set()

    attempts = 0
    max_attempts = 2000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            pt, pt_enc, ct, ct_dec = make_instance(rng)

            problem = render_problem(pt, ct, output_language)
            key = canonical_key(problem)
            if key in seen:
                continue

            # Cross-check correctness via inverse properties
            if decrypt(pt_enc) != normalize_plaintext(pt):
                raise AssertionError("encrypt/decrypt inverse check failed on generated plaintext.")
            if encrypt(ct_dec) != "".join(ch for ch in ct.upper() if 'A' <= ch <= 'Z'):
                raise AssertionError("decrypt/encrypt inverse check failed on generated ciphertext.")

            answer = f"[[{pt_enc}]]====[[{ct_dec}]]"
            explanation = (
                explain_encrypt(pt, pt_enc) + "\n\n" + explain_decrypt(ct, ct_dec)
            )

            results.append({
                "problem": problem,
                "answer": answer,
                "explanation": explanation
            })
            seen.add(key)
        except Exception as e:
            print(f"[warn] generation attempt failed: {e}", file=sys.stderr)
            continue

    if len(results) != count:
        raise RuntimeError(f"Unable to generate enough unique problems: got {len(results)} / {count}")

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()