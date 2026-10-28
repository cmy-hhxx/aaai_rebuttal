import sys, json, random, string
from typing import List, Dict, Tuple, Any

# -----------------------------
# Core domain: custom alphabet order + sorting words
# We generate tasks where a set of letters are moved to the front of the alphabet
# (preserving their relative order as given), then words are sorted by this custom order.
# Variants:
#  - move 1-4 letters to front
#  - sort ascending or descending
#  - ask for full ordered list or top-k / bottom-k
#  - allow optional case-insensitive rule (but we will render lowercase words to avoid ambiguity)
# -----------------------------

ALPH = string.ascii_lowercase

def build_custom_alphabet(front_letters: List[str]) -> str:
    """Move specified letters to front in the given order, then the remaining letters in normal order."""
    seen = set()
    front = []
    for ch in front_letters:
        if ch not in seen:
            front.append(ch)
            seen.add(ch)
    rest = [c for c in ALPH if c not in seen]
    return "".join(front + rest)

def make_rank_map(custom_alph: str) -> Dict[str, int]:
    return {ch: i for i, ch in enumerate(custom_alph)}

def cmp_key(word: str, rank: Dict[str, int]) -> Tuple:
    # Lexicographic by custom alphabet; tie-breaker by length then normal word to ensure deterministic.
    # Note: actual ordering is determined by custom ranks of characters; shorter word should come first
    # when one is a prefix of another. Using tuple of ranks plus a terminal marker handles it:
    # We'll just use ranks list and append -1 terminal.
    ranks = [rank[c] for c in word]
    return tuple(ranks + [-1, len(word)] + [ord(c) for c in word])

def sort_words(words: List[str], front_letters: List[str], descending: bool) -> List[str]:
    custom = build_custom_alphabet(front_letters)
    rank = make_rank_map(custom)
    sorted_words = sorted(words, key=lambda w: cmp_key(w, rank), reverse=descending)
    return sorted_words

def stable_unique_words(rng: random.Random, n: int, min_len: int, max_len: int) -> List[str]:
    # Generate pronounceable-ish random lowercase words to avoid real-vocabulary dependency.
    # Ensure uniqueness.
    vowels = "aeiou"
    cons = "".join([c for c in ALPH if c not in vowels])
    words = set()
    attempts = 0
    while len(words) < n:
        attempts += 1
        if attempts > 50000:
            raise RuntimeError("生成单词失败：尝试次数过多")
        L = rng.randint(min_len, max_len)
        # alternating pattern with random start
        start_with_vowel = rng.random() < 0.35
        chars = []
        for i in range(L):
            if (i % 2 == 0) == start_with_vowel:
                chars.append(rng.choice(vowels))
            else:
                chars.append(rng.choice(cons))
        # occasionally add a consonant cluster
        if L >= 6 and rng.random() < 0.25:
            pos = rng.randint(1, L - 2)
            chars[pos] = rng.choice(cons)
            chars[pos + 1] = rng.choice(cons)
        w = "".join(chars)
        # avoid too many similar, ensure contains at least one of some letters often
        words.add(w)
    return sorted(words)

def choose_front_letters(rng: random.Random) -> List[str]:
    # Pick 1-4 distinct letters; allow including some that matter in comparisons by ensuring
    # at least one appears in some word set via regeneration check later.
    k = rng.randint(1, 4)
    letters = rng.sample(list(ALPH), k)
    return letters

def ensure_front_letters_relevant(words: List[str], front_letters: List[str]) -> bool:
    s = "".join(words)
    return any(ch in s for ch in front_letters)

def format_problem(words: List[str], front_letters: List[str], descending: bool, query: Dict[str, Any], lang: str) -> str:
    # query types:
    #  - {"type":"full"} -> list all in order
    #  - {"type":"topk","k":k} -> output first k
    #  - {"type":"bottomk","k":k} -> output last k
    move_str = "、".join(front_letters)
    order_str = "降序" if descending else "升序"
    words_str = "，".join(words)
    base = (
        f"给定一组小写单词：{words_str}。\n"
        f"现在按如下规则定义新的字母表顺序：把字母 {move_str} 按给出的先后顺序整体移到字母表最前面，"
        f"其余字母保持原来的相对顺序不变。随后按该新字母表的字典序对这些单词进行{order_str}排序。\n"
    )
    if query["type"] == "full":
        ask = "请写出排序后的完整序列，用英文逗号+空格分隔，例如：word1, word2, word3。"
    elif query["type"] == "topk":
        k = query["k"]
        ask = f"请写出排序后排在最前面的 {k} 个单词，用英文逗号+空格分隔。"
    else:
        k = query["k"]
        ask = f"请写出排序后排在最后面的 {k} 个单词，用英文逗号+空格分隔。"
    return base + ask

def format_explanation(words: List[str], front_letters: List[str], descending: bool, sorted_words: List[str], query: Dict[str, Any]) -> str:
    custom = build_custom_alphabet(front_letters)
    # Provide verifiable evidence: show custom alphabet prefix and compare first-differing letters
    # for a couple of adjacent pairs in the returned list.
    prefix = custom[:min(12, len(custom))]
    order_str = "降序" if descending else "升序"
    if query["type"] == "full":
        shown = sorted_words
        label = "完整排序结果"
    elif query["type"] == "topk":
        shown = sorted_words[:query["k"]]
        label = f"取前 {query['k']} 个"
    else:
        shown = sorted_words[-query["k"]:]
        label = f"取后 {query['k']} 个"

    # Pick up to 3 adjacent comparisons within shown (or around boundaries) to demonstrate correctness.
    rank = make_rank_map(custom)
    comparisons = []
    def first_diff(a: str, b: str) -> Tuple[int, str, str]:
        m = min(len(a), len(b))
        for i in range(m):
            if a[i] != b[i]:
                return i, a[i], b[i]
        # one is prefix
        return m, "(结束)", "(结束)"

    check_list = sorted_words
    # select indices for adjacent comparisons
    idxs = []
    if len(check_list) >= 2:
        idxs = [0, len(check_list)//2 - 1, len(check_list)-2]
        idxs = [i for i in idxs if 0 <= i < len(check_list)-1]
        idxs = list(dict.fromkeys(idxs))[:3]

    for i in idxs:
        a, b = check_list[i], check_list[i+1]
        pos, ca, cb = first_diff(a, b)
        if ca == "(结束)" and cb == "(结束)":
            # identical (shouldn't happen due to uniqueness), skip
            continue
        if ca == "(结束)":
            # a is prefix of b
            reason = f"“{a}”是“{b}”的前缀，因此在字典序中更靠前（升序）/更靠后（降序）由整体排序决定。"
        elif cb == "(结束)":
            reason = f"“{b}”是“{a}”的前缀，因此两者比较由前缀规则决定。"
        else:
            ra, rb = rank[ca], rank[cb]
            # In ascending, smaller rank earlier; in descending, larger rank earlier.
            better = "更靠前" if (ra < rb) ^ descending else "更靠后"
            reason = (f"比较相邻的“{a}”与“{b}”：在第 {pos+1} 个字母首次不同，"
                      f"分别是 '{ca}' 与 '{cb}'。在新字母表中 rank('{ca}')={ra}，rank('{cb}')={rb}，"
                      f"按{order_str}排序因此“{a}”应{better}于“{b}”。")
        comparisons.append(reason)

    shown_str = ", ".join(shown)
    exp = (
        f"新字母表为：把 {', '.join(front_letters)} 移到最前面，得到以“{prefix}...”开头的顺序。\n"
        f"{label}：{shown_str}\n"
    )
    if comparisons:
        exp += "校验要点（举例相邻比较）：\n" + "\n".join(f"- {c}" for c in comparisons)
    return exp

def make_query(rng: random.Random, n_words: int) -> Dict[str, Any]:
    # Choose query form; ensure k sensible
    t = rng.random()
    if t < 0.55:
        return {"type": "full"}
    elif t < 0.80:
        k = rng.randint(2, min(5, n_words))
        return {"type": "topk", "k": k}
    else:
        k = rng.randint(2, min(5, n_words))
        return {"type": "bottomk", "k": k}

def answer_for_query(sorted_words: List[str], query: Dict[str, Any]) -> str:
    if query["type"] == "full":
        return ", ".join(sorted_words)
    if query["type"] == "topk":
        return ", ".join(sorted_words[:query["k"]])
    return ", ".join(sorted_words[-query["k"]:])

def validate_unique_answer(words: List[str], front_letters: List[str], descending: bool, query: Dict[str, Any]) -> bool:
    # For deterministic sorting, answer is unique as long as words are unique; still, we can
    # check that there are no ties leading to same ordering ambiguity (not possible here).
    return len(set(words)) == len(words)

def generate_one(rng: random.Random, lang: str) -> Dict[str, Any]:
    # sample size and lengths
    n = rng.randint(6, 10)
    min_len = rng.randint(4, 6)
    max_len = rng.randint(max(min_len + 2, 7), 11)

    # resample to ensure moved letters actually appear (so rule is not vacuous)
    for _ in range(200):
        words = stable_unique_words(rng, n, min_len, max_len)
        front_letters = choose_front_letters(rng)
        if ensure_front_letters_relevant(words, front_letters):
            break
    else:
        raise RuntimeError("无法生成包含前移字母的单词集合")

    descending = rng.random() < 0.55
    query = make_query(rng, n)

    sorted_words = sort_words(words, front_letters, descending)

    # Cross-check: independent verification by explicitly comparing all adjacent pairs
    custom = build_custom_alphabet(front_letters)
    rank = make_rank_map(custom)

    def leq(a: str, b: str) -> bool:
        # a <= b in custom lexicographic
        la, lb = len(a), len(b)
        m = min(la, lb)
        for i in range(m):
            if a[i] != b[i]:
                return rank[a[i]] <= rank[b[i]]
        return la <= lb

    def geq(a: str, b: str) -> bool:
        la, lb = len(a), len(b)
        m = min(la, lb)
        for i in range(m):
            if a[i] != b[i]:
                return rank[a[i]] >= rank[b[i]]
        return la >= lb

    for i in range(len(sorted_words) - 1):
        a, b = sorted_words[i], sorted_words[i + 1]
        ok = geq(a, b) if descending else leq(a, b)
        if not ok:
            raise RuntimeError("内部校验失败：排序结果不满足相邻次序关系")

    if not validate_unique_answer(words, front_letters, descending, query):
        raise RuntimeError("内部校验失败：答案不唯一")

    problem = format_problem(words, front_letters, descending, query, lang)
    answer = answer_for_query(sorted_words, query)
    explanation = format_explanation(words, front_letters, descending, sorted_words, query)
    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    raw = sys.stdin.read()
    try:
        req = json.loads(raw)
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count 必须为正整数")
    except Exception as e:
        print(f"输入JSON解析失败或字段不合法: {e}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    lang = "zh"

    results = []
    seen = set()
    # bounded attempts to avoid infinite loops
    max_attempts = 2000
    attempts = 0
    while len(results) < count and attempts < max_attempts:
        attempts += 1
        item = generate_one(rng, lang)
        # deduplicate by problem text
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    if len(results) < count:
        print(f"生成失败：仅生成 {len(results)}/{count} 道题（已尝试 {attempts} 次）", file=sys.stderr)
        sys.exit(2)

    sys.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()