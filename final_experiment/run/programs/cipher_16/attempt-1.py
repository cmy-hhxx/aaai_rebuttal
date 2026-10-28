import sys, json, random
from dataclasses import dataclass
from typing import List, Any, Tuple

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def eprint(*args):
    print(*args, file=sys.stderr)


# ---------------- Cipher core (5-line zigzag columns with # padding) ----------------

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


def decrypt5(cipher: str) -> str:
    parts = cipher.split("*")
    if len(parts) == 6 and parts[-1] == "":
        parts = parts[:-1]
    if len(parts) != 5:
        raise ValueError("Ciphertext must be divisible into exactly 5 groups by '*'.")

    rows = [list(p) for p in parts]
    if not rows[0]:
        return ""

    cols = len(rows[0])
    for r in range(1, 5):
        if len(rows[r]) > cols:
            raise ValueError("Invalid ciphertext row lengths for this cipher.")

    out = []
    down = True
    for c in range(cols):
        if c == 0:
            out.append(rows[0][c])
            continue
        if down:
            if c < len(rows[0]): out.append(rows[0][c])
            for r in range(1, 5):
                if c < len(rows[r]):
                    out.append(rows[r][c])
        else:
            for r in range(4, 0, -1):
                if c < len(rows[r]):
                    out.append(rows[r][c])
            if c < len(rows[0]): out.append(rows[0][c])
        down = not down

    return "".join(ch for ch in out if ch != "#")


def decrypt5_crosscheck(cipher: str) -> str:
    parts = cipher.split("*")
    if len(parts) == 6 and parts[-1] == "":
        parts = parts[:-1]
    if len(parts) != 5:
        raise ValueError("Ciphertext must be divisible into exactly 5 groups by '*' (crosscheck).")
    rows = [list(p) for p in parts]
    cols = len(rows[0])
    grid = [[None for _ in range(cols)] for _ in range(5)]
    for r in range(5):
        for c, ch in enumerate(rows[r]):
            grid[r][c] = ch

    out = []
    down = True
    for c in range(cols):
        if c == 0:
            if grid[0][0] is None:
                raise ValueError("Missing first cell.")
            out.append(grid[0][0])
            continue
        if down:
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


def validate_cipher_format(cipher: str) -> None:
    if cipher.count("*") != 5:
        raise ValueError("Cipher must contain exactly 5 '*'.")
    if not cipher.endswith("*"):
        raise ValueError("Cipher must end with '*'.")


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
        "加密步骤：先将首字母放在第1行第1列；之后按列交替“向下列填充/向上列填充”，"
        "且每列第1行位置用#补位（向下时先#，向上时最后#）。\n"
        f"明文：{plain}\n"
        "5行结果：\n" + "\n".join([f"第{i+1}行：{rows_s[i]}" for i in range(5)]) + "\n"
        f"逐行加*读出密文：{cipher}"
    )
    prob = (
        "【加密题】\n"
        "使用如下5行密码加密：先把明文第1个字母放在第1行第1列；随后每一列交替执行：\n"
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
    plain2 = decrypt5_crosscheck(cipher)
    if plain != plain2:
        raise AssertionError("Decryption cross-check mismatch.")

    parts = cipher.split("*")
    if len(parts) == 6 and parts[-1] == "":
        parts = parts[:-1]
    expl = (
        "解密步骤：按*切成5段依次作为第1~5行；再从第1列开始按列交替读取：第1列只读第1行；"
        "第2列起依次“向下读一列(第1行→第5行) / 向上读一列(第5行→第1行)”交替；最后删除#。\n"
        f"密文：{cipher}\n"
        "分行：\n" + "\n".join([f"第{i+1}行：{parts[i]}" for i in range(5)]) + "\n"
        f"去#得到明文：{plain}"
    )
    prob = (
        "【解密题】\n"
        "使用如下5行密码解密：密文按*分成5段，依次填入第1~5行。然后从第1列开始按列交替读取：\n"
        "- 第1列：只读取第1行；\n"
        "- 从第2列起：先向下读一列(第1行→第5行)，再向上读一列(第5行→第1行)，如此交替。\n"
        "读取得到的串删除所有#，即为明文。\n\n"
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
    # stable signature to avoid duplicates
    return item.problem.splitlines()[-2] + "|" + str(item.answer)


def generate_one(rng: random.Random) -> Item:
    mode = rng.choice(["enc", "dec"])
    if mode == "enc":
        plain = rand_plain(rng)
        return make_problem_encrypt(plain)
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
        it = generate_one(rng)
        sig = signature(it)
        if sig in seen:
            continue

        # strict self-checks
        if it.problem.startswith("【加密题】"):
            cipher = it.answer
            validate_cipher_format(cipher)
            back = decrypt5(cipher)
            # extract plaintext from problem line containing 明文
            # line: 明文："XXXX"
            plain_line = None
            for line in it.problem.splitlines():
                if line.startswith("明文："):
                    plain_line = line
                    break
            if plain_line is None:
                raise AssertionError("Plaintext line not found.")
            plain = plain_line.split("\"", 2)[1]
            if back != plain:
                raise AssertionError("Encrypt->Decrypt self-check failed.")
        else:
            # decryption task: verify re-encrypt
            cipher_line = None
            for line in it.problem.splitlines():
                if line.startswith("密文："):
                    cipher_line = line
                    break
            if cipher_line is None:
                raise AssertionError("Ciphertext line not found.")
            cipher = cipher_line.split("\"", 2)[1]
            validate_cipher_format(cipher)
            rec = encrypt5(it.answer)
            if rec != cipher:
                raise AssertionError("Decrypt->Encrypt self-check failed.")
            # also cross-check decrypt again
            if decrypt5_crosscheck(cipher) != it.answer:
                raise AssertionError("Cross-check failed.")

        seen.add(sig)
        items.append(it)

    if len(items) < count:
        eprint(f"Generation failed: only produced {len(items)}/{count} items after {attempts} attempts.")
        sys.exit(2)

    out = [{"problem": it.problem, "answer": it.answer, "explanation": it.explanation} for it in items]
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()