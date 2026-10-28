import sys, json, random, string
from typing import List, Tuple, Dict, Any, Optional

# ---------------- Cipher core ----------------

TRANSPOSE = [1, 4, 0, 6, 5, 2, 3]  # new columns are [old 1, old 4, old 0, old 6, old 5, old 2, old 3]
WIDTH = 7

# For decryption we need the inverse mapping: given adjusted column j, which original column i did it come from?
# adjusted[j] = original[TRANSPOSE[j]]
# so original[i] = adjusted[inv[i]] where inv[TRANSPOSE[j]] = j
INV = [0] * WIDTH
for j, old_i in enumerate(TRANSPOSE):
    INV[old_i] = j


def chunk(s: str, n: int) -> List[str]:
    return [s[i:i+n] for i in range(0, len(s), n)]


def encrypt(plaintext: str) -> str:
    # plaintext: uppercase letters only, no spaces/punct
    if not plaintext or any(c not in string.ascii_uppercase for c in plaintext):
        raise ValueError("plaintext must be non-empty and uppercase A-Z only")
    # pad with '$' to multiple of WIDTH
    pad = (-len(plaintext)) % WIDTH
    pt = plaintext + ("$" * pad)
    rows = chunk(pt, WIDTH)
    # adjust columns
    out_rows = []
    for r in rows:
        out_rows.append("".join(r[i] for i in TRANSPOSE))
    return "".join(out_rows)


def decrypt(ciphertext: str) -> str:
    if not ciphertext or any(c not in (string.ascii_uppercase + "$") for c in ciphertext):
        raise ValueError("ciphertext must be non-empty and consist of A-Z and '$' only")
    if len(ciphertext) % WIDTH != 0:
        raise ValueError("ciphertext length must be a multiple of 7")
    rows = chunk(ciphertext, WIDTH)
    pt_rows = []
    for r in rows:
        # r is adjusted row; recover original order
        pt_rows.append("".join(r[INV[i]] for i in range(WIDTH)))
    pt = "".join(pt_rows)
    # remove trailing '$'
    return pt.rstrip("$")


# Independent cross-check via explicit grid reconstruction (different code path)
def encrypt_check(plaintext: str) -> str:
    pad = (-len(plaintext)) % WIDTH
    pt = plaintext + ("$" * pad)
    nrows = len(pt) // WIDTH
    # build grid as list of lists
    grid = [list(pt[i*WIDTH:(i+1)*WIDTH]) for i in range(nrows)]
    # permute columns
    new_grid = []
    for r in grid:
        new_r = [None]*WIDTH
        for new_j, old_i in enumerate(TRANSPOSE):
            new_r[new_j] = r[old_i]
        new_grid.append(new_r)
    return "".join("".join(r) for r in new_grid)


def decrypt_check(ciphertext: str) -> str:
    nrows = len(ciphertext) // WIDTH
    grid_adj = [list(ciphertext[i*WIDTH:(i+1)*WIDTH]) for i in range(nrows)]
    # invert permutation by placing characters back to original columns
    grid_orig = []
    for r in grid_adj:
        orig = [None]*WIDTH
        for new_j, old_i in enumerate(TRANSPOSE):
            orig[old_i] = r[new_j]
        grid_orig.append(orig)
    pt = "".join("".join(r) for r in grid_orig)
    return pt.rstrip("$")


# ---------------- Problem generation ----------------

def rand_upper(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(string.ascii_uppercase) for _ in range(n))

def build_explanation_encrypt(pt: str, ct: str) -> str:
    pad = (-len(pt)) % WIDTH
    pt_pad = pt + "$"*pad
    rows = chunk(pt_pad, WIDTH)
    adj_rows = ["".join(r[i] for i in TRANSPOSE) for r in rows]
    expl = []
    expl.append(f"将明文每7个字母一行书写，不足7用$补齐：补了{pad}个$。")
    expl.append("原始分组：")
    expl.append("\n".join(rows))
    expl.append("按列重排顺序[1,4,0,6,5,2,3]得到每行：")
    expl.append("\n".join(adj_rows))
    expl.append("逐行读取得到密文。")
    return "\n".join(expl)

def build_explanation_decrypt(ct: str, pt: str) -> str:
    rows = chunk(ct, WIDTH)
    # show recovered original rows (with potential $)
    orig_rows = []
    for r in rows:
        orig_rows.append("".join(r[INV[i]] for i in range(WIDTH)))
    expl = []
    expl.append("将密文每7个字符一行书写：")
    expl.append("\n".join(rows))
    expl.append("按逆过程把每行恢复到原列序(即取列顺序[2,0,5,6,1,4,3]对应原列0..6)：")
    expl.append("\n".join(orig_rows))
    expl.append("逐行读出并去掉末尾的$。")
    return "\n".join(expl)

def make_one(rng: random.Random) -> Dict[str, Any]:
    # Two tasks per problem: (1) encrypt a plaintext, (2) decrypt a ciphertext
    # Ensure variety: plaintext length between 8 and 30, not multiple of 7 sometimes.
    pt_len = rng.randint(8, 30)
    pt = rand_upper(rng, pt_len)

    ct1 = encrypt(pt)
    # generate a ciphertext by encrypting a different plaintext (so decrypt is meaningful)
    pt2_len = rng.randint(6, 28)
    pt2 = rand_upper(rng, pt2_len)
    ct2 = encrypt(pt2)

    # checks
    if ct1 != encrypt_check(pt):
        raise AssertionError("encrypt cross-check failed")
    if decrypt(ct2) != pt2:
        raise AssertionError("decrypt failed")
    if decrypt_check(ct2) != pt2:
        raise AssertionError("decrypt cross-check failed")

    problem = (
        "你是一个擅长加密/解密的助手。使用如下固定的换位加密规则（每行7列，列重排顺序为[1,4,0,6,5,2,3]，"
        "不足7用$补齐并保留$），完成两问：\n\n"
        f"1）明文：\"{pt}\"。请给出加密后的密文，用双层方括号包裹，例如：[[密文]]。\n"
        f"2）密文：\"{ct2}\"。请给出解密后的明文（去掉末尾补齐用的$），用双层方括号包裹，例如：[[明文]]。"
    )

    answer = f"[[{ct1}]]====[[{pt2}]]"
    explanation = (
        "第1问（加密）要点：\n" + build_explanation_encrypt(pt, ct1) +
        "\n\n第2问（解密）要点：\n" + build_explanation_decrypt(ct2, pt2) +
        "\n\n校验：对同一规则独立实现的加/解密过程进行交叉核对，结果一致。"
    )
    return {"problem": problem, "answer": answer, "explanation": explanation}


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    out = []
    seen = set()
    attempts = 0
    max_attempts = count * 50 + 200

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        item = make_one(rng)
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    if len(out) != count:
        print(f"Failed to generate enough unique problems: got {len(out)} / {count}", file=sys.stderr)
        sys.exit(1)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()