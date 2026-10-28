import sys, json, random, string
from typing import List, Dict, Tuple, Any

ENC_TABLE = {
    'A': '!', 'B': '@', 'C': '#', 'D': '$',
    'E': '%', 'F': '^', 'G': '&', 'H': '*',
    'I': '(', 'J': ')', 'K': '_', 'L': '+',
    'M': '=', 'N': '~', 'O': '?', 'P': '/',
    'Q': '0', 'R': ':', 'S': ';', 'T': '<',
    'U': '>', 'V': '1', 'W': '2', 'X': '3',
    'Y': '4', 'Z': '5'
}
DEC_TABLE = {v: k for k, v in ENC_TABLE.items()}

LETTERS = string.ascii_uppercase
SYMS = ''.join(ENC_TABLE[c] for c in LETTERS)

def enc(plaintext: str) -> str:
    return ''.join(ENC_TABLE[ch] for ch in plaintext)

def dec(ciphertext: str) -> str:
    return ''.join(DEC_TABLE[ch] for ch in ciphertext)

def rand_plain(rng: random.Random, n: int) -> str:
    return ''.join(rng.choice(LETTERS) for _ in range(n))

def rand_cipher(rng: random.Random, n: int) -> str:
    return ''.join(rng.choice(SYMS) for _ in range(n))

def fmt_answer_two_parts(a: str, b: str) -> str:
    return f"[[{a}]]====[[{b}]]"

def build_explanation_encrypt(plaintext: str, ciphertext: str, show_steps: int = 6) -> str:
    pairs = []
    for i, ch in enumerate(plaintext[:show_steps]):
        pairs.append(f"{ch}→{ENC_TABLE[ch]}")
    more = "" if len(plaintext) <= show_steps else f"（后续同理，共{len(plaintext)}个字符）"
    return (
        "加密规则：逐字符用映射表替换。\n"
        f"明文：{plaintext}\n"
        f"前{min(show_steps,len(plaintext))}步示例： " + "，".join(pairs) + f"{more}\n"
        f"得到密文：{ciphertext}"
    )

def build_explanation_decrypt(ciphertext: str, plaintext: str, show_steps: int = 6) -> str:
    pairs = []
    for i, ch in enumerate(ciphertext[:show_steps]):
        pairs.append(f"{ch}→{DEC_TABLE[ch]}")
    more = "" if len(ciphertext) <= show_steps else f"（后续同理，共{len(ciphertext)}个字符）"
    return (
        "解密规则：逐字符用映射表的反向映射替换。\n"
        f"密文：{ciphertext}\n"
        f"前{min(show_steps,len(ciphertext))}步示例： " + "，".join(pairs) + f"{more}\n"
        f"得到明文：{plaintext}"
    )

def make_problem(rng: random.Random) -> Dict[str, Any]:
    # Two-part task like seed: part1 encrypt plaintext; part2 decrypt ciphertext.
    # Vary lengths and optionally insert small narrative variations (still self-contained).
    n1 = rng.randint(8, 14)
    n2 = rng.randint(8, 14)

    plaintext = rand_plain(rng, n1)
    ciphertext_for_decrypt = rand_cipher(rng, n2)

    encrypted = enc(plaintext)
    decrypted = dec(ciphertext_for_decrypt)

    # Render in Chinese as requested, keep rules explicit & self-contained.
    # Ensure no spaces/punct in plaintext; ciphertext is from symbol set only.
    problem = (
        "你需要按照下述替换密码规则完成加密与解密。请严格逐字符替换。\n\n"
        "【映射表 encryption_table】\n"
        "A→!，B→@，C→#，D→$，E→%，F→^，G→&，H→*，\n"
        "I→(，J→)，K→_，L→+，M→=，N→~，O→?，P→/，\n"
        "Q→0，R→:，S→;，T→<，U→>，V→1，W→2，X→3，Y→4，Z→5。\n\n"
        "【加密】明文为仅含大写字母的字符串：将每个字母替换为表中对应符号，得到密文。\n"
        "【解密】密文为仅由上述符号构成的字符串：将每个符号替换回对应大写字母，得到明文。\n\n"
        f"1）明文：\"{plaintext}\"\n"
        "请给出加密结果，用双层方括号括起：例如 [[密文]]。\n\n"
        f"2）密文：\"{ciphertext_for_decrypt}\"\n"
        "请给出解密结果，用双层方括号括起：例如 [[明文]]。\n\n"
        "注意：最终答案请按如下格式输出（中间用四个等号连接）：\n"
        "[[第1问答案]]====[[第2问答案]]"
    )

    answer = fmt_answer_two_parts(encrypted, decrypted)

    explanation = (
        build_explanation_encrypt(plaintext, encrypted, show_steps=rng.randint(4, 7))
        + "\n\n"
        + build_explanation_decrypt(ciphertext_for_decrypt, decrypted, show_steps=rng.randint(4, 7))
        + "\n\n"
        "校验：加密与解密均为一一映射（26个字母对应26个不同符号），因此逐字符替换结果唯一。"
    )

    # Internal consistency checks (no external API)
    assert dec(enc(plaintext)) == plaintext
    assert enc(dec(ciphertext_for_decrypt)) == ciphertext_for_decrypt

    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data)
    except Exception as e:
        print(f"输入不是合法JSON：{e}", file=sys.stderr)
        sys.exit(1)

    seed = int(req.get("seed", 0))
    count = int(req.get("count", 0))
    if count <= 0:
        print("count 必须为正整数", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)

    items: List[Dict[str, Any]] = []
    seen = set()
    max_tries = count * 50

    tries = 0
    while len(items) < count and tries < max_tries:
        tries += 1
        obj = make_problem(rng)

        # Deduplicate by (plaintext,ciphertext) embedded in problem string.
        key = obj["problem"]
        if key in seen:
            continue
        seen.add(key)
        items.append(obj)

    if len(items) < count:
        print(f"生成失败：仅生成{len(items)}/{count}题（已尝试{tries}次）", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(items, ensure_ascii=False))

if __name__ == "__main__":
    main()