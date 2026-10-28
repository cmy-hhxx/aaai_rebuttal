import sys, json, random, string
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def eprint(*args):
    print(*args, file=sys.stderr)


# ---------------- Cipher core (5-line zigzag columns with # padding) ----------------

def _fill_columns_5(plain: str) -> List[List[str]]:
    """
    Encrypt filling:
    - 5 rows
    - place plain[0] at row0, col0
    - then for each next char:
        alternate: downward column, upward column, downward, ...
      Column rule:
        * For downward: row0 gets '#', rows1..4 get next chars in order (up to 4)
        * For upward: rows4..1 get next chars (up to 4), then row0 gets '#'
    - Stop when all plaintext chars are placed (padding '#' may still be placed if a column is started)
    Returns rows as lists of characters (ragged).
    """
    rows = [[] for _ in range(5)]
    if not plain:
        return rows
    rows[0].append(plain[0])
    i = 1
    down = True
    while i < len(plain):
        if down:
            # row0 '#'
            rows[0].append('#')
            # rows1..4 fill with plaintext
            for r in range(1, 5):
                if i >= len(plain):
                    break
                rows[r].append(plain[i])
                i += 1
        else:
            # rows4..1 fill with plaintext
            for r in range(4, 0, -1):
                if i >= len(plain):
                    break
                rows[r].append(plain[i])
                i += 1
            # row0 '#'
            rows[0].append('#')
        down = not down
    return rows


def encrypt5(plain: str) -> str:
    """
    Return ciphertext string containing exactly 5 '*' delimiters (one after each row).
    """
    rows = _fill_columns_5(plain)
    # read line by line, append '*'
    return "".join("".join(rows[r]) + "*" for r in range(5))


def decrypt5(cipher: str) -> str:
    """
    Decrypt:
    - split by '*' into 5 groups (final cipher must have 5 '*' so split gives 6 with last empty)
    - rebuild 5 rows of characters
    - read columns alternately: down first then up, repeatedly, taking available cells.
      Determine number of columns as len(row0). In this cipher construction row0 has one entry for each column.
      For each column c:
        if c==0: take row0[c] only (first position)
        else:
          if down: take row0[c], then rows1..4 at col if exists
          if up: take rows4..1 at col if exists, then row0[c]
      After reconstruction, remove '#' to get plaintext.
    """
    parts = cipher.split("*")
    # Expect 6 parts with last == "" if cipher endswith '*'
    # But be tolerant: if no trailing '*', then parts length should be 5.
    if len(parts) == 6 and parts[-1] == "":
        parts = parts[:-1]
    if len(parts) != 5:
        raise ValueError("Ciphertext must be divisible into exactly 5 groups by '*'.")

    rows = [list(p) for p in parts]
    if not rows[0]:
        return ""

    cols = len(rows[0])
    # basic consistency: other rows length should be <= cols
    for r in range(1, 5):
        if len(rows[r]) > cols:
            raise ValueError("Invalid row lengths for this cipher.")

    out = []
    down = True
    for c in range(cols):
        if c == 0:
            # first position was plain[0] at row0,col0
            out.append(rows[0][c])
            continue
        if down:
            # row0 then 1..4
            if c < len(rows[0]): out.append(rows[0][c])
            for r in range(1, 5):
                if c < len(rows[r]):
                    out.append(rows[r][c])
        else:
            # 4..1 then row0
            for r in range(4, 0, -1):
                if c < len(rows[r]):
                    out.append(rows[r][c])
            if c < len(rows[0]): out.append(rows[0][c])
        down = not down

    return "".join(ch for ch in out if ch != "#")


# Independent cross-check: simulate decryption by rebuilding the exact fill order using row strings
def _decrypt5_crosscheck(cipher: str) -> str:
    parts = cipher.split("*")
    if len(parts) == 6 and parts[-1] == "":
        parts = parts[:-1]
    if len(parts) != 5:
        raise ValueError("Ciphertext must be divisible into exactly 5 groups by '*' (crosscheck).")
    rows = [list(p) for p in parts]
    cols = len(rows[0])
    # Build grid with None for missing
    grid = [[None for _ in range(cols)] for _ in range(5)]
    for r in range(5):
        for c, ch in enumerate(rows[r]):
            grid[r][c] = ch

    # Now replay reading-columns alternation, but only take existing cells in the exact sequence
    out = []
    down = True
    for c in range(cols):
        if c == 0:
            if grid[0][0] is None:
                raise ValueError("Missing first cell.")
            out.append(grid[0][0])
            continue
        if down:
            # row0 then 1..4
            if grid[0][c] is not None: out.append(grid[0][c])
            for r in range(1, 5):
                if grid[r][c] is not None:
                    out.append(grid[r][c])
        else:
            for r in range(4, 0, -1):
                if grid[r][c] is not None:
                    out.append(grid[r][c])
            if grid[0][c] is not None: out.append(grid[0][c])
        down = not down
    return "".join(ch for ch in out if ch != "#")


# ---------------- Problem generation ----------------

@dataclass
class Item:
    problem: str
    answer: Any
    explanation: str


def rand_plain(rng: random.Random, min_len=18, max_len=44) -> str:
    n = rng.randint(min_len, max_len)
    return "".join(rng.choice(LETTERS) for _ in range(n))


def mutate_cipher_by_encrypting_random_plain(rng: random.Random) -> Tuple[str, str]:
    plain = rand_plain(rng)
    cipher = encrypt5(plain)
    return plain, cipher


def make_problem_encrypt(rng: random.Random, plain: str) -> Item:
    cipher = encrypt5(plain)
    # explanation: show 5 rows and final cipher
    rows = _fill_columns_5(plain)
    rows_s = ["".join(r) for r in rows]
    expl = (
        "加密：按规则用5行交替“向下列填充/向上列填充”写入；行0在每列补一个#。\n"
        f"明文：{plain}\n"
        "填充后5行分别为：\n"
        + "\n".join([f"第{i+1}行：{rows_s[i]}" for i in range(5)]) + "\n"
        f"逐行读出并在每行末尾加*，得到密文：{cipher}"
    )
    prob = (
        "【加密题】\n"
        "给定一种5行列交替填充密码：先把明文第1个字母放在第1行第1列；之后每一“列”交替执行：\n"
        "1) 向下列填充：第1行写#，再从第2行到第5行依次写入后续明文字母；\n"
        "2) 向上列填充：从第5行到第2行依次写入后续明文字母，最后第1行写#。\n"
        "直到明文写完。最后按行从第1行到第5行依次读出，每行末尾加一个*，形成密文（总共应有5个*）。\n\n"
        f"明文：\"{plain}\"\n"
        "请写出密文。"
    )
    return Item(problem=prob, answer=cipher, explanation=expl)


def make_problem_decrypt(rng: random.Random, cipher: str) -> Item:
    plain = decrypt5(cipher)
    # cross-check
    plain2 = _decrypt5_crosscheck(cipher)
    if plain != plain2:
        raise AssertionError("Decryption cross-check mismatch.")
    parts = cipher.split("*")
    if len(parts) == 6 and parts[-1] == "":
        parts = parts[:-1]
    rows_s = parts
    expl = (
        "解密：先按*把密文分成5段，依次作为第1~5行；再按列交替（先向下读一列、再向上读一列……）读出，最后去掉#。\n"
        f"密文：{cipher}\n"
        "分行结果：\n" + "\n".join([f"第{i+1}行：{rows_s[i]}" for i in range(5)]) + "\n"
        f"去#后得到明文：{plain}"
    )
    prob = (
        "【解密题】\n"
        "给定一种5行列交替填充密码。密文用*分隔为5行：第1段是第1行，第2段是第2行……第5段是第5行。\n"
        "把5行还原后，从第1列开始按列交替读取：第1列只读第1行；从第2列起，先读一列“向下”（第1行→第5行），再读一列“向上”（第5行→第1行），如此交替。读出的串中删除所有#，得到明文。\n\n"
        f"密文：\"{cipher}\"\n"
        "请写出明文。"
    )
    return Item(problem=prob, answer=plain, explanation=expl)


def validate_cipher_format(cipher: str) -> None:
    # exactly 5 '*' and endswith '*'
    if cipher.count("*") != 5:
        raise ValueError("Cipher must contain exactly 5 '*' delimiters.")
    if not cipher.endswith("*"):
        raise ValueError("Cipher must end with '*' (so that 5 rows are clearly terminated).")


def generate_one(rng: random.Random, idx: int) -> Item:
    # Create either encryption or decryption task, with some variety in lengths
    mode = rng.choice(["enc", "dec", "enc", "dec", "enc"])  # slight bias to enc
    if mode == "enc":
        plain = rand_plain(rng, 16, 48)
        return make_problem_encrypt(rng, plain)
    else:
        plain, cipher = mutate_cipher_by_encrypting_random_plain(rng)
        validate_cipher_format(cipher)
        return make_problem_decrypt(rng, cipher)


def item_signature(item: Item) -> str:
    # prevent near-duplicates: hash by (answer, first 120 chars of problem)
    return f"{str(item.answer)}|{item.problem[:120]}"


def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data)
        seed = int(req["seed"])
        count = int(req["count"])
    except Exception as ex:
        eprint("Invalid input JSON. Expected {'seed': int, 'count': int}. Error:", ex)
        sys.exit(1)

    rng = random.Random(seed)
    items: List[Item] = []
    seen = set()

    max_attempts = 2000
    attempts = 0
    while len(items) < count and attempts < max_attempts:
        attempts += 1
        try:
            it = generate_one(rng, len(items))
            sig = item_signature(it)
            if sig in seen:
                continue
            # quick self-check: ensure encryption/decryption invert on relevant cases
            if isinstance(it.answer, str) and it.answer.count("*") == 5 and it.answer.endswith("*"):
                # seems like ciphertext answer; check decrypt(encrypt(plain)) on the plain in explanation if present
                pass
            # If this is an encryption task, verify answer by decrypting it back
            if it.problem.startswith("【加密题】"):
                cipher = it.answer
                validate_cipher_format(cipher)
                back = decrypt5(cipher)
                # extract plain from problem line
                # safer: recompute from explanation known plain
                # We stored plain in explanation line "明文：..."
                marker = "明文："
                pos = it.explanation.find(marker)
                if pos != -1:
                    plain_line = it.explanation[pos + len(marker):].splitlines()[0].strip()
                    plain = plain_line
                    if back != plain:
                        raise AssertionError("Encrypt->Decrypt self-check failed.")
            else:
                # decryption task: verify by re-encrypting
                # cipher in problem: between quotes after 密文：
                # easier: take from explanation "密文："
                marker = "密文："
                pos = it.explanation.find(marker)
                if pos != -1:
                    cipher_line = it.explanation[pos + len(marker):].splitlines()[0].strip()
                    cipher = cipher_line
                    validate_cipher_format(cipher)
                    rec = encrypt5(it.answer)
                    if rec != cipher:
                        raise AssertionError("Decrypt->Encrypt self-check failed.")

            seen.add(sig)
            items.append(it)
        except Exception as ex:
            # resample
            continue

    if len(items) < count:
        eprint(f"Generation failed: only produced {len(items)}/{count} items after {attempts} attempts.")
        sys.exit(2)

    out = [{"problem": it.problem, "answer": it.answer, "explanation": it.explanation} for it in items]
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()