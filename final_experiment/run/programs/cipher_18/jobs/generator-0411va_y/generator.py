import sys, json, random
from typing import List, Tuple, Dict, Any

# =========================
# Cardan grille (4x4) cipher generator/solver
# As per seed: a 4x4 grid, a fixed template with 4 holes, rotate CCW 90 degrees each time.
# Fill/read holes in row-major order of the current template orientation.
# Encryption: write plaintext through holes across 4 rotations (pad with '#') then read grid row-major.
# Decryption: write ciphertext row-major to grid, then read holes across 4 rotations.
# =========================

HOLE_TEMPLATE = [
    [0, 0, 0, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 0],
]  # 1 means hole (white)

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
FILLER = "#"

def rot_ccw(mat: List[List[int]]) -> List[List[int]]:
    n = len(mat)
    return [[mat[j][n - 1 - i] for j in range(n)] for i in range(n)]

def hole_positions(mat: List[List[int]]) -> List[Tuple[int,int]]:
    n = len(mat)
    pos = [(r, c) for r in range(n) for c in range(n) if mat[r][c] == 1]
    return pos  # row-major

def encrypt_block(block: str) -> str:
    # block: length <= 16, uppercase letters and/or '#'
    n = 4
    grid = [[None for _ in range(n)] for _ in range(n)]
    tmpl = [row[:] for row in HOLE_TEMPLATE]
    idx = 0
    for _ in range(4):
        for (r, c) in hole_positions(tmpl):
            ch = block[idx] if idx < len(block) else FILLER
            idx += 1
            if grid[r][c] is not None:
                # invalid grille; should not happen
                raise ValueError("Hole overlap detected during encryption.")
            grid[r][c] = ch
        tmpl = rot_ccw(tmpl)
    # Fill any remaining None (shouldn't) with filler to be safe
    for r in range(n):
        for c in range(n):
            if grid[r][c] is None:
                grid[r][c] = FILLER
    return "".join(grid[r][c] for r in range(n) for c in range(n))

def decrypt_block(block: str) -> str:
    if len(block) != 16:
        raise ValueError("Ciphertext block must be length 16.")
    n = 4
    grid = [[None for _ in range(n)] for _ in range(n)]
    k = 0
    for r in range(n):
        for c in range(n):
            grid[r][c] = block[k]
            k += 1
    tmpl = [row[:] for row in HOLE_TEMPLATE]
    out = []
    for _ in range(4):
        for (r, c) in hole_positions(tmpl):
            out.append(grid[r][c])
        tmpl = rot_ccw(tmpl)
    return "".join(out)

def encrypt(plaintext: str) -> str:
    # plaintext uppercase letters only (generator ensures). We will not strip anything else.
    res = []
    for i in range(0, len(plaintext), 16):
        res.append(encrypt_block(plaintext[i:i+16]))
    return "".join(res)

def decrypt(ciphertext: str) -> str:
    if len(ciphertext) % 16 != 0:
        raise ValueError("Ciphertext length must be multiple of 16.")
    res = []
    for i in range(0, len(ciphertext), 16):
        res.append(decrypt_block(ciphertext[i:i+16]))
    return "".join(res)

def check_grille_is_valid() -> None:
    # Ensure holes across 4 rotations cover all 16 cells exactly once.
    tmpl = [row[:] for row in HOLE_TEMPLATE]
    seen = set()
    for _ in range(4):
        for p in hole_positions(tmpl):
            if p in seen:
                raise ValueError("Invalid grille: overlap across rotations.")
            seen.add(p)
        tmpl = rot_ccw(tmpl)
    if len(seen) != 16:
        raise ValueError(f"Invalid grille: covered {len(seen)} cells, expected 16.")

def rand_plaintext(rng: random.Random, min_len: int, max_len: int) -> str:
    L = rng.randint(min_len, max_len)
    return "".join(rng.choice(ALPHABET) for _ in range(L))

def rand_ciphertext(rng: random.Random, blocks_min: int, blocks_max: int, allow_hash: bool=True) -> str:
    b = rng.randint(blocks_min, blocks_max)
    # ciphertext may include '#' because encryption pads with '#'
    chars = ALPHABET + (FILLER if allow_hash else "")
    return "".join(rng.choice(chars) for _ in range(16 * b))

def explain_encrypt(pt: str, ct: str) -> str:
    # Provide a compact, checkable explanation without leaking generator internals
    blocks = (len(pt) + 15) // 16
    pad = blocks * 16 - len(pt)
    return (
        f"使用 4x4 栅格模板（每次逆时针旋转90°，共读/写4轮，每轮4个孔）进行加密。"
        f"明文长度为{len(pt)}，分为{blocks}个16字符分组；最后一组不足用“#”补齐{pad}个字符。"
        f"每组按孔位顺序写入后，按行读取得到16字符密文，拼接得到最终密文：{ct}。"
    )

def explain_decrypt(ct: str, pt: str) -> str:
    blocks = len(ct) // 16
    return (
        f"使用同一 4x4 模板进行解密。密文长度为{len(ct)}，分为{blocks}个16字符分组。"
        f"每组先按行写入4x4栅格，再按模板孔位读取并每次逆时针旋转90°，连续读取4轮得到16字符明文分组。"
        f"拼接得到最终明文：{pt}（其中“#”表示加密补位字符）。"
    )

def format_problem_encrypt(pt: str) -> str:
    return (
        "按以下规则进行加密（4x4 栅格 + 4孔模板，每次写满4孔后模板逆时针旋转90°，共4轮填满16格；"
        "明文不足16用“#”补齐；填满后按行读取为密文；多于16则分组处理并拼接）。\n\n"
        "模板（▯表示孔）：\n"
        "▮  ▮  ▮  ▮\n"
        "▮  ▮  ▯  ▯\n"
        "▮  ▮  ▮  ▯\n"
        "▯  ▮  ▮  ▮\n\n"
        f"题目：给定明文：\"{pt}\"，求密文。输出格式：[[密文]]"
    )

def format_problem_decrypt(ct: str) -> str:
    return (
        "按以下规则进行解密（与加密相反）：将每16字符密文按行写入4x4栅格；"
        "然后用同一4孔模板读取孔中字符，读完4孔后模板逆时针旋转90°，共读4轮得到16字符明文分组；"
        "多组则拼接。符号“#”为补位字符。\n\n"
        "模板（▯表示孔）：\n"
        "▮  ▮  ▮  ▮\n"
        "▮  ▮  ▯  ▯\n"
        "▮  ▮  ▮  ▯\n"
        "▯  ▮  ▮  ▮\n\n"
        f"题目：给定密文：\"{ct}\"，求明文。输出格式：[[明文]]"
    )

def make_item(rng: random.Random) -> Dict[str, Any]:
    # diversify: sometimes encryption, sometimes decryption; vary lengths and presence of '#'
    kind = rng.choice(["enc", "dec", "enc", "dec", "enc2", "dec2"])
    if kind in ("enc", "enc2"):
        # plaintext length between 1..60; enc2 biases to non-multiple-of-16 to include padding
        if kind == "enc2":
            # force non-multiple of 16 often
            L = rng.randint(5, 55)
            while L % 16 == 0:
                L = rng.randint(5, 55)
            pt = "".join(rng.choice(ALPHABET) for _ in range(L))
        else:
            pt = rand_plaintext(rng, 1, 64)
        ct = encrypt(pt)
        # Cross-check via decrypt
        back = decrypt(ct)
        # back equals padded plaintext (with '#')
        blocks = (len(pt) + 15) // 16
        padded = pt + (FILLER * (blocks * 16 - len(pt)))
        if back != padded:
            raise AssertionError("Encryption/decryption cross-check failed.")
        return {
            "problem": format_problem_encrypt(pt),
            "answer": f"[[{ct}]]",
            "explanation": explain_encrypt(pt, ct),
        }
    else:
        # ciphertext blocks 1..4, include '#' sometimes (more in dec2)
        if kind == "dec2":
            b = rng.randint(2, 4)
            # Ensure at least one '#'
            ct_list = [rng.choice(ALPHABET) for _ in range(16*b)]
            for _ in range(rng.randint(1, 6)):
                ct_list[rng.randrange(16*b)] = FILLER
            ct = "".join(ct_list)
        else:
            ct = rand_ciphertext(rng, 1, 4, allow_hash=True)
        # Ensure multiple of 16 by construction
        pt = decrypt(ct)
        # Cross-check via encrypt (note: encrypt pads; but decrypt output length is multiple of 16 already)
        ct2 = encrypt(pt)  # since len(pt) multiple of 16, no extra padding beyond full blocks
        if ct2 != ct:
            raise AssertionError("Decryption/encryption cross-check failed.")
        return {
            "problem": format_problem_decrypt(ct),
            "answer": f"[[{pt}]]",
            "explanation": explain_decrypt(ct, pt),
        }

def main():
    try:
        check_grille_is_valid()
    except Exception as e:
        print(f"Template validation error: {e}", file=sys.stderr)
        sys.exit(1)

    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    items = []
    seen = set()
    # bounded resampling
    attempts = 0
    max_attempts = 2000
    while len(items) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = make_item(rng)
        except Exception as e:
            print(f"Generation attempt failed: {e}", file=sys.stderr)
            continue
        key = (item["problem"], item["answer"])
        if key in seen:
            continue
        seen.add(key)
        items.append(item)

    if len(items) != count:
        print(f"Failed to generate enough unique items: got {len(items)} of {count}", file=sys.stderr)
        sys.exit(2)

    json.dump(items, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()