import sys, json, random
from typing import List, Tuple, Dict, Any

LETTERS = ['J', 'D', 'W', 'O', 'T', 'R', 'A', 'C', 'X', 'Q', 'M', 'F', 'Y',
           'E', 'Z', 'G', 'U', 'K', 'P', 'V', 'B', 'S', 'H', 'N', 'L', 'I']
POS = {ch: i for i, ch in enumerate(LETTERS)}

DEFAULT_DECK = [9, 25, 44, 38, 40, 22, 11, 36, 13, 39, 18, 42, 10, 53, 26, 12, 1, 16, 3, 43, 37, 17,
                30, 4, 28, 48, 27, 41, 32, 15, 47, 29, 20, 51, 6, 7, 52, 34, 35, 5, 50, 9, 54, 46, 23, 31,
                24, 14, 8, 33, 2, 49, 45, 21]

JOKER_A = 53
JOKER_B = 54

def move_card_down(deck: List[int], card: int, steps: int) -> None:
    """Move 'card' down by 'steps' positions in a circular way, but it cannot become the first card.
    This matches the Solitaire cipher joker move rules."""
    n = len(deck)
    idx = deck.index(card)
    deck.pop(idx)
    # In the classic rule: moving down wraps around but never to top.
    # Equivalent insertion index computed on the deck after removal.
    # If card was at position idx (0-based) in original deck:
    # new_idx = (idx + steps) % (n-1) in reduced deck, but with special wrap to avoid index 0.
    new_idx = (idx + steps) % (n - 1)
    if new_idx == 0:
        new_idx = 1
    deck.insert(new_idx, card)

def triple_cut(deck: List[int]) -> None:
    a = deck.index(JOKER_A)
    b = deck.index(JOKER_B)
    lo, hi = (a, b) if a < b else (b, a)
    top = deck[:lo]
    middle = deck[lo:hi+1]
    bottom = deck[hi+1:]
    deck[:] = bottom + middle + top

def count_cut(deck: List[int]) -> None:
    bottom = deck[-1]
    cut_val = 53 if bottom in (JOKER_A, JOKER_B) else bottom
    if cut_val <= 0 or cut_val >= len(deck):
        return
    top = deck[:cut_val]
    rest = deck[cut_val:-1]
    deck[:] = rest + top + [deck[-1]]

def keystream_next(deck: List[int]) -> int:
    """Generate next keystream value (1..52 typically, excluding jokers), repeating if joker output."""
    while True:
        move_card_down(deck, JOKER_A, 1)
        move_card_down(deck, JOKER_B, 2)
        triple_cut(deck)
        count_cut(deck)
        top = deck[0]
        top_val = 53 if top in (JOKER_A, JOKER_B) else top
        out = deck[top_val]
        if out in (JOKER_A, JOKER_B):
            continue
        return out

def enc_letter(p: str, y: int) -> str:
    x = POS[p]
    z = (x + (y % 26)) % 26
    return LETTERS[z]

def dec_letter(c: str, y: int) -> str:
    z = POS[c]
    x = (z - (y % 26)) % 26
    return LETTERS[x]

def encrypt(plaintext: str, deck0: List[int]) -> Tuple[str, List[int], List[int]]:
    deck = deck0[:]
    ys = []
    out = []
    for ch in plaintext:
        y = keystream_next(deck)
        ys.append(y)
        out.append(enc_letter(ch, y))
    return "".join(out), deck, ys

def decrypt(ciphertext: str, deck0: List[int]) -> Tuple[str, List[int], List[int]]:
    deck = deck0[:]
    ys = []
    out = []
    for ch in ciphertext:
        y = keystream_next(deck)
        ys.append(y)
        out.append(dec_letter(ch, y))
    return "".join(out), deck, ys

def rand_text(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(LETTERS) for _ in range(n))

def format_problem(plaintext: str, ciphertext: str, deck: List[int], variant: str) -> str:
    deck_str = ", ".join(map(str, deck))
    common_rule = (
        "你需要按照题面给出的纸牌密钥流算法与字母表映射完成加密/解密。\n\n"
        "字母表（位置从0开始）：\n"
        "LETTERS = ['J','D','W','O','T','R','A','C','X','Q','M','F','Y','E','Z','G','U','K','P','V','B','S','H','N','L','I']\n"
        "即 J->0, D->1, ..., I->25。\n\n"
        "初始牌堆（长度54，53为A Joker，54为B Joker）：\n"
        f"[{deck_str}]\n\n"
        "密钥流生成（每次产生一个值y，并会永久改变牌堆顺序，下一次在新牌堆上继续）：\n"
        "1) 找到A Joker(53)，向下移动1张；若在底部则插入到第二张位置（不能成为第一张）。\n"
        "2) 找到B Joker(54)，向下移动2张；必要时环绕，但不能成为第一张。\n"
        "3) Triple cut：以两张Joker为边界，将顶部段与底部段交换，中间段（含Joker及其间的牌）保持相对顺序。\n"
        "4) Count cut：看底牌，若是Joker则计为53，否则计为其点数v；取出顶端v张插入到倒数第二张之前。\n"
        "5) 看顶牌，若是Joker则计为53，否则计为其点数t；取第(t+1)张牌的点数作为输出；若输出是Joker则丢弃并回到步骤1重来。\n\n"
        "加密：对明文字母p，取x=pos(p)，生成y，算z=(x+y)%26，输出LETTERS[z]。\n"
        "解密：对密文字母c，取z=pos(c)，生成y，算x=(z-y) mod 26，输出LETTERS[x]。\n\n"
    )
    if variant == "both":
        return (common_rule +
                f"问题：\n"
                f"1) 明文：\"{plaintext}\"，请给出加密后的密文（用双中括号包裹，例如[[ABC]]）。\n"
                f"2) 密文：\"{ciphertext}\"，请给出解密后的明文（用双中括号包裹）。\n"
                f"输出格式：[[第1问答案]]====[[第2问答案]]\n")
    elif variant == "enc_only":
        return (common_rule +
                f"问题：\n"
                f"明文：\"{plaintext}\"，请给出加密后的密文（用双中括号包裹，例如[[ABC]]）。\n")
    else:
        return (common_rule +
                f"问题：\n"
                f"密文：\"{ciphertext}\"，请给出解密后的明文（用双中括号包裹，例如[[ABC]]）。\n")

def explanation_for(plaintext: str, ciphertext: str,
                    enc_out: str, dec_out: str,
                    ys_enc: List[int], ys_dec: List[int],
                    variant: str) -> str:
    # Provide checkable evidence: first few keystream values and position arithmetic.
    def show_steps(text_in: str, text_out: str, ys: List[int], mode: str) -> str:
        k = min(5, len(text_in))
        lines = []
        for i in range(k):
            a = text_in[i]
            b = text_out[i]
            y = ys[i] % 26
            if mode == "enc":
                x = POS[a]
                z = POS[b]
                lines.append(f"{i+1}) {a}(x={x}) + y={y} -> z={z} -> {b}")
            else:
                z = POS[a]
                x = POS[b]
                lines.append(f"{i+1}) {a}(z={z}) - y={y} -> x={x} -> {b}")
        return "\n".join(lines)

    parts = []
    if variant in ("both", "enc_only"):
        parts.append("第1问校验要点：给出前若干步(只展示前5个字符)的(y mod 26)与字母位置运算：")
        parts.append(f"前5个密钥流原始值y：{ys_enc[:5]}")
        parts.append(show_steps(plaintext, enc_out, ys_enc, "enc"))
    if variant in ("both", "dec_only"):
        parts.append("第2问校验要点：给出前若干步(只展示前5个字符)的(y mod 26)与字母位置运算：")
        parts.append(f"前5个密钥流原始值y：{ys_dec[:5]}")
        parts.append(show_steps(ciphertext, dec_out, ys_dec, "dec"))
    return "\n".join(parts)

def make_instance(rng: random.Random) -> Dict[str, Any]:
    deck = DEFAULT_DECK[:]  # keep fixed to match seed domain; variability comes from texts & query form
    variant = rng.choices(["both", "enc_only", "dec_only"], weights=[6, 2, 2], k=1)[0]

    # Length variation
    n1 = rng.randint(8, 14)
    n2 = rng.randint(8, 14)

    plaintext = rand_text(rng, n1)
    # For decryption question, choose a ciphertext by encrypting a hidden random plaintext to guarantee validity.
    hidden_plain = rand_text(rng, n2)
    cipher2, _, _ = encrypt(hidden_plain, deck)

    # Solve for asked outputs
    enc_out, _, ys_enc = encrypt(plaintext, deck)
    dec_out, _, ys_dec = decrypt(cipher2, deck)

    problem = format_problem(plaintext, cipher2, deck, variant)

    if variant == "both":
        answer = f"[[{enc_out}]]====[[{dec_out}]]"
        explanation = explanation_for(plaintext, cipher2, enc_out, dec_out, ys_enc, ys_dec, variant)
    elif variant == "enc_only":
        answer = f"[[{enc_out}]]"
        explanation = explanation_for(plaintext, cipher2, enc_out, dec_out, ys_enc, ys_dec, variant)
    else:
        answer = f"[[{dec_out}]]"
        explanation = explanation_for(plaintext, cipher2, enc_out, dec_out, ys_enc, ys_dec, variant)

    # Cross-check: decrypt(encrypt(plaintext)) == plaintext
    back, _, _ = decrypt(enc_out, deck)
    if back != plaintext:
        raise RuntimeError("自检失败：加密后再解密未还原明文。")

    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count must be positive")
    except Exception as e:
        print(f"Invalid input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    out = []
    seen = set()
    attempts = 0
    max_attempts = max(200, count * 30)

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = make_instance(rng)
        except Exception as e:
            print(f"Generation attempt failed: {e}", file=sys.stderr)
            continue

        key = (item["problem"], json.dumps(item["answer"], ensure_ascii=False, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    if len(out) != count:
        print(f"Failed to generate enough unique problems: got {len(out)} / {count}", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()