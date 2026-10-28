import sys, json, random
from collections import deque, defaultdict

# -----------------------------
# Word ladder (单词接龙/变形词) generator & solver
# 内置词表；不依赖外部文件/网络
# -----------------------------

WORDLIST_RAW = """
CAT COT COG DOG DOT DAT BAT BOT BOG BAG DAG DIG FIG FOG LOG LAG LEG LET BET BED BAD DAD
MAD MAT MET MEN MAN CAN CON COP CAP MAP MOP MOM DOD DAB CAB COB COD
HIT HOT HAT HAD HID DID DIT FIT FAT FAD SAD SAP SIP TIP TOP TAP TAD
RAT ROT RAG RIG RIM RAM ROM RUM RUN FUN FAN FIN BIN BIG BUG DUG
PEN PAN PIN PIG PUG RUG RUT BUT BUN SUN SIN SOD SIR
COLD CORD CARD WARD WARM HARM HARE HERE HERO ZERO ZEST BEST BEAT MEAT SEAT SEAL TEAL TELL TALL TAIL BAIL BALL BELL BELT MELT MALT SALT
SAME SAGE PAGE PAVE PINE PINK SINK SING SONG LONG BONG BANG BUNG HUNG HUNT HINT MINT MIND BIND BINE
RATE RITE RICE RISE ROSE LOSE LOFT LEFT LEAF LEAN LOAN LOAD GOAD GOLD GOLF
FOOD GOOD WOOD MOOD MOLD BOLD SOLD SOLE SALE SAIL MAIL MAIN PAIN GAIN
FATE DATE DATA BETA META MEET MEAT HEAT SEAT SEAM TEAM TEAR BEAR BOAR BOAT COAT CHAT THAT WHAT
FISH DISH WISH WASH CASH CASE CASK MASK TASK TUSK DUSK DESK REST
NOTE NODE MODE MADE MALE MILE MITE BITE BYTE
SPOT SPIT SPAT SLAT SLOT SLOG BLOG BLOT PLOT
CARS BARS BARN WARN WORN WORD
FORK FORM FROM FROG
TONE TUNE TANK RANK RING KING KIND WIND WINE WIDE
""".strip().split()

def normalize_word(w: str) -> str:
    w = w.strip()
    return "".join([c for c in w.upper() if c.isalpha()])

def build_dictionary():
    words = set()
    for w in WORDLIST_RAW:
        nw = normalize_word(w)
        if 3 <= len(nw) <= 5:
            words.add(nw)
    # essentials
    for e in ["MOM", "DAD", "CAT", "DOG", "COLD", "WARM", "FOOD", "GOOD"]:
        words.add(e)
    return words

WORDS = build_dictionary()

def all_words_by_length(wordset):
    m = defaultdict(list)
    for w in wordset:
        m[len(w)].append(w)
    return m

WORDS_BY_LEN = all_words_by_length(WORDS)

def neighbors(word, wordset):
    res = []
    L = len(word)
    for i in range(L):
        orig = word[i]
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if ch == orig:
                continue
            cand = word[:i] + ch + word[i+1:]
            if cand in wordset:
                res.append(cand)
    return res

def bfs_shortest_distance_and_path(start, end, wordset):
    if start == end:
        return 0, [start]
    q = deque([start])
    dist = {start: 0}
    parent = {start: None}
    while q:
        cur = q.popleft()
        for nb in neighbors(cur, wordset):
            if nb in dist:
                continue
            dist[nb] = dist[cur] + 1
            parent[nb] = cur
            if nb == end:
                path = [end]
                x = end
                while parent[x] is not None:
                    x = parent[x]
                    path.append(x)
                path.reverse()
                return dist[end], path
            q.append(nb)
    return None, None

def bfs_distance_and_count_shortest_paths(start, end, wordset, max_states=200000):
    if start == end:
        return 0, 1
    q = deque([start])
    dist = {start: 0}
    ways = defaultdict(int)
    ways[start] = 1
    popped = 0
    while q:
        cur = q.popleft()
        popped += 1
        if popped > max_states:
            raise RuntimeError("State exploration limit exceeded")
        for nb in neighbors(cur, wordset):
            nd = dist[cur] + 1
            if nb not in dist:
                dist[nb] = nd
                ways[nb] = ways[cur]
                q.append(nb)
            elif dist[nb] == nd:
                ways[nb] += ways[cur]
    return dist.get(end, None), ways.get(end, 0)

def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)

def format_problem_zh(start, end, require_unique=False, extra_note=None):
    uniq_line = "（保证“最少步数”这个数值是唯一确定的。）\n" if require_unique else ""
    note_line = (extra_note.strip() + "\n") if extra_note else ""
    return (
        "你正在玩一个“单词接龙”变形游戏，规则如下：\n"
        "1）给定起始单词与目标单词（长度相同）。\n"
        "2）每一步只能改变一个字母；改变后得到的单词必须是有效英文单词。\n"
        "3）用最少步数从起始词变到目标词。\n"
        f"问题：从「{start}」变到「{end}」最少需要多少步？\n"
        f"{uniq_line}"
        f"{note_line}"
        "请将答案写成双中括号形式，例如 [[3]]。\n"
    )

def format_explanation_zh(start, end, dist, path, unique_paths_count=None):
    lb = hamming(start, end)
    path_str = " → ".join(path)
    uniq_part = f"；并且最短路径条数（独立计数）= {unique_paths_count}" if unique_paths_count is not None else ""
    return (
        f"下界校验：{start} 与 {end} 的不同字母数= {lb}，因此最少步数 ≥ {lb}。\n"
        f"给出一条达到该最少步数的变换：{path_str}。\n"
        f"该序列进行了 {len(path)-1} 次单字母替换，因此最少步数 ≤ {len(path)-1}。\n"
        f"所以最少步数 = {dist}{uniq_part}。"
    )

def choose_pair_with_constraints(rng, length_choices, min_dist, max_dist, require_unique, max_tries=8000):
    # length_choices: list of allowed lengths, we will sample among those that are feasible
    feasible_lengths = [L for L in length_choices if len(WORDS_BY_LEN.get(L, [])) >= 2]
    if not feasible_lengths:
        raise RuntimeError("No feasible word lengths in dictionary")

    for _ in range(max_tries):
        L = rng.choice(feasible_lengths)
        candidates = WORDS_BY_LEN[L]
        start = rng.choice(candidates)
        end = rng.choice(candidates)
        if start == end:
            continue

        ham = hamming(start, end)
        if ham > max_dist:
            continue

        dist, path = bfs_shortest_distance_and_path(start, end, WORDS)
        if dist is None or not (min_dist <= dist <= max_dist):
            continue

        dist2, ways = bfs_distance_and_count_shortest_paths(start, end, WORDS)
        if dist2 != dist:
            continue
        if require_unique and ways != 1:
            continue

        return start, end, dist, path, ways

    raise RuntimeError("Failed to sample a suitable word pair within try limit")

def generate_one(rng):
    # Avoid 5-letter because the built-in list may be sparse depending on filtering
    length_choices = [3, 4]  # robust

    require_unique = (rng.random() < 0.35)
    # set distance bands to keep it solvable within our small dictionary
    if rng.random() < 0.6:
        min_dist, max_dist = 2, 4
    else:
        min_dist, max_dist = 3, 6

    start, end, dist, path, ways = choose_pair_with_constraints(
        rng, length_choices, min_dist, max_dist, require_unique
    )

    extra_note = None
    if rng.random() < 0.4:
        extra_note = "注意：只能改一个字母（位置任选），且每一步都必须仍然是英文单词。"

    problem = format_problem_zh(start, end, require_unique=require_unique, extra_note=extra_note)
    answer = f"[[{dist}]]"
    explanation = format_explanation_zh(start, end, dist, path, unique_paths_count=(ways if require_unique else None))
    return {"problem": problem, "answer": answer, "explanation": explanation}

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    res = []
    seen = set()
    attempts = 0
    max_attempts = max(2000, count * 300)

    while len(res) < count and attempts < max_attempts:
        attempts += 1
        item = generate_one(rng)
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        if not item["problem"].strip():
            continue
        res.append(item)

    if len(res) != count:
        print(f"Generation failed: produced {len(res)} / {count} after {attempts} attempts.", file=sys.stderr)
        sys.exit(1)

    json.dump(res, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()