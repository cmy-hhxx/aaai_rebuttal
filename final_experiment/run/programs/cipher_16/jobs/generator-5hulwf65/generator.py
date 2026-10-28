import sys, json, random
from dataclasses import dataclass
from typing import List, Any, Tuple

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def eprint(*args):
    print(*args, file=sys.stderr)


# ---------------- Cipher core (5-line zigzag columns with # padding) ----------------
# Encryption is authoritative. Decryption will be verified by re-simulating encryption
# on candidate plaintext until it matches ciphertext (round-trip check).


def _fill_columns_5(plain: str) -> List[List[str]]:
    rows = [[] for _ in range(5)]
    if not plain:
        return rows
    rows[0].append(plain[0])
    i = 1
    down = True
    while i < len(plain):
        if down:
            rows[0].append('#')
            for r in range(1, 5):
                if i >= len(plain):
                    break
                rows[r].append(plain[i])
                i += 1
        else:
            for r in range(4, 0, -1):
                if i >= len(plain):
                    break
                rows[r].append(plain[i])
                i += 1
            rows[0].append('#')
        down = not down
    return rows


def encrypt5(plain: str) -> str:
    rows = _fill_columns_5(plain)
    return "".join("".join(rows[r]) + "*" for r in range(5))


def validate_cipher_format(cipher: str) -> None:
    if cipher.count("*") != 5 or not cipher.endswith("*"):
        raise ValueError("Cipher must contain exactly 5 '*' and end with '*'.")


def _split_rows(cipher: str) -> List[str]:
    parts = cipher.split("*")
    if len(parts) == 6 and parts[-1] == "":
        parts = parts[:-1]
    if len(parts) != 5:
        raise ValueError("Cipher must split into exactly 5 rows by '*'.")
    return parts


def _cipher_grid(cipher: str) -> Tuple[List[List[str]], int]:
    rows_s = _split_rows(cipher)
    rows = [list(s) for s in rows_s]
    cols = len(rows[0])
    for r in range(1, 5):
        if len(rows[r]) > cols:
            raise ValueError("Invalid ciphertext: some row longer than row1.")
    return rows, cols


def decrypt5(cipher: str) -> str:
    """
    Robust decryption by reconstructing the exact plaintext placement order used in encryption.

    Key idea:
    - Row0 has one char per column (either first plaintext char at col0, or '#' for later columns).
    - Each column type alternates:
        col0: only row0 exists (plaintext[0])
        col1: DOWN column (row0 '#', rows1..4 plaintext chars present maybe)
        col2: UP column (rows4..1 plaintext chars present maybe, row0 '#')
        col3: DOWN, ...
    - Given the 5 row strings, we can traverse columns in this order and collect only the cells
      that were plaintext letters (i.e., all non-None cells except the mandatory '#' in row0 for c>=1).
      Finally remove any '#' (should only be row0 pads) — kept for safety.
    This guarantees encrypt(decrypt(cipher)) == cipher for any cipher produced by encrypt5.
    """
    validate_cipher_format(cipher)
    rows, cols = _cipher_grid(cipher)

    # build grid with None for missing cells
    grid = [[None for _ in range(cols)] for _ in range(5)]
    for r in range(5):
        for c, ch in enumerate(rows[r]):
            grid[r][c] = ch

    out = []
    for c in range(cols):
        if c == 0:
            if grid[0][0] is None:
                raise ValueError("Invalid cipher: missing first cell.")
            # first cell is always plaintext[0]
            out.append(grid[0][0])
            continue

        # column type alternates starting with DOWN at c=1
        is_down = (c % 2 == 1)

        if is_down:
            # row0 is '#', then rows1..4 are plaintext letters (if present)
            for r in range(1, 5):
                if grid[r][c] is not None:
                    out.append(grid[r][c])
        else:
            # rows4..1 are plaintext letters (if present), then row0 is '#'
            for r in range(4, 0, -1):
                if grid[r][c] is not None:
                    out.append(grid[r][c])

        # we intentionally do NOT append grid[0][c] because it is the padding '#'
        # (and it may be present even when plaintext ended).

    return "".join(ch for ch in out if ch != "#")


# ---------------- Problem generation ----------------

@dataclass
class Item:
    problem: str
    answer: Any
    explanation: str


def rand_plain(rng: random.Random, min_len=16, max_len=48) -> str:
    n = rng.randint(min_len, max_len)
    return "".join(rng.choice(LETTERS) for _ in range(n))


def make_problem_encrypt(plain: str) -> Item:
    cipher = encrypt5(plain)
    validate_cipher_format(cipher)
    rows = _fill_columns_5(plain)
    rows_s = ["".join(r) for r in rows]
    expl = (
        "加密：先把首字母放在第1行第1列；之后按列交替：\n"
        "（1）向下列填充：第1行写#，第2~5行依次写入字母；\n"
        "（2）向上列填充：第5~2行依次写入字母，最后第1行写#。\n"
        "逐行读出并在每行末尾加*。\n"
        f"明文：{plain}\n"
        "填充后的5行：\n" + "\n".join([f"第{i+1}行：{rows_s[i]}" for i in range(5)]) + "\n"
        f"密文：{cipher}"
    )
    prob = (
        "【加密题】\n"
        "使用如下5行密码加密：先把明文第1个字母放在第1行第1列；随后每列交替执行：\n"
        "A. 向下列填充：第1行写#，再从第2行到第5行依次写入后续字母；\n"
        "B. 向上列填充：从第5行到第2行依次写入后续字母，最后第1行写#。\n"
        "明文写完即停止。最后按行读出（第1行到第5行），每行末尾加一个*，得到密文（共5个*）。\n\n"
        f"明文：\"{plain}\"\n"
        "求密文。"
    )
    return Item(problem=prob, answer=cipher, explanation=expl)


def make_problem_decrypt(cipher: str) -> Item:
    validate_cipher_format(cipher)
    plain = decrypt5(cipher)

    # round-trip check (this is the real correctness criterion)
    rec = encrypt5(plain)
    if rec != cipher:
        raise AssertionError("Round-trip check failed for decryption.")

    parts = _split_rows(cipher)
    expl = (
        "解密：先按*分成5段作为5行；第1列取第1行的首字符；从第2列起，列类型交替：\n"
        "- 第2列(向下列)：取第2~5行该列字符；\n"
        "- 第3列(向上列)：取第5~2行该列字符；\n"
        "如此交替，最后删除#。\n"
        f"密文：{cipher}\n"
        "分行：\n" + "\n".join([f"第{i+1}行：{parts[i]}" for i in range(5)]) + "\n"
        f"明文：{plain}\n"
        "校验：将明文再次按同规则加密，得到的密文与题目密文一致。"
    )
    prob = (
        "【解密题】\n"
        "使用如下5行密码解密：密文按*分成5段，依次填入第1~5行。明文读取规则为加密的逆过程：\n"
        "- 第1列：只读取第1行；\n"
        "- 从第2列起：第2列按“向下列”读取第2~5行；第3列按“向上列”读取第5~2行；之后继续交替。\n"
        "读出的串删除所有#，即为明文。\n\n"
        f"密文：\"{cipher}\"\n"
        "求明文。"
    )
    return Item(problem=prob, answer=plain, explanation=expl)


def generate_cipher_from_plain(rng: random.Random) -> Tuple[str, str]:
    plain = rand_plain(rng)
    cipher = encrypt5(plain)
    validate_cipher_format(cipher)
    return plain, cipher


def signature(item: Item) -> str:
    return item.problem.splitlines()[-2] + "|" + str(item.answer)


def generate_one(rng: random.Random) -> Item:
    mode = rng.choice(["enc", "dec"])
    if mode == "enc":
        return make_problem_encrypt(rand_plain(rng))
    else:
        _, cipher = generate_cipher_from_plain(rng)
        return make_problem_decrypt(cipher)


def main():
    try:
        req = json.loads(sys.stdin.read())
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count must be positive")
    except Exception as ex:
        eprint("Invalid input JSON. Expected {'seed': int, 'count': int}. Error:", ex)
        sys.exit(1)

    rng = random.Random(seed)
    items: List[Item] = []
    seen = set()

    max_attempts = 20000
    attempts = 0
    while len(items) < count and attempts < max_attempts:
        attempts += 1
        try:
            it = generate_one(rng)
            sig = signature(it)
            if sig in seen:
                continue

            # strict self-checks for both types
            if it.problem.startswith("【加密题】"):
                cipher = it.answer
                validate_cipher_format(cipher)
                # extract plaintext from problem
                plain_line = None
                for line in it.problem.splitlines():
                    if line.startswith("明文："):
                        plain_line = line
                        break
                if plain_line is None:
                    raise AssertionError("Plaintext line not found.")
                plain = plain_line.split("\"", 2)[1]
                if decrypt5(cipher) != plain:
                    raise AssertionError("Encrypt->Decrypt check failed.")
            else:
                # extract cipher from problem
                cipher_line = None
                for line in it.problem.splitlines():
                    if line.startswith("密文："):
                        cipher_line = line
                        break
                if cipher_line is None:
                    raise AssertionError("Ciphertext line not found.")
                cipher = cipher_line.split("\"", 2)[1]
                validate_cipher_format(cipher)
                if encrypt5(it.answer) != cipher:
                    raise AssertionError("Decrypt->Encrypt check failed.")

            seen.add(sig)
            items.append(it)
        except Exception:
            continue

    if len(items) < count:
        eprint(f"Generation failed: only produced {len(items)}/{count} items after {attempts} attempts.")
        sys.exit(2)

    out = [{"problem": it.problem, "answer": it.answer, "explanation": it.explanation} for it in items]
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()