import sys, json, random, math
from collections import deque, defaultdict

# -----------------------------
# Word ladder (单词接龙/变形词) generator & solver
# - 仅允许每步改动一个字母
# - 每个中间词必须是有效词（本程序内置词表）
# - 求最少步数（边数），题面要求输出 [[最少步数]]
# - 生成时保证可解、且用独立校验路径交叉验证
# -----------------------------

# A compact but reasonably rich built-in dictionary of 3-5 letter English words.
# Note: We don't rely on external files/network. Words are uppercase internally.
WORDLIST_RAW = """
CAT COT COG DOG DOT DAT BAT BOT BOG BAG DAG DIG FIG FOG LOG LAG LEG LET BET BED BAD DAD
MAD MAT MET MEN MAN CAN CON COP CAP MAP MOP MOM DOD DAD DAB CAB COB COD
HIT HOT HAT HAD HID DID DIT FIT FAT FAD SAD SAP SIP TIP TOP TAP TAD
RAT ROT RAG RIG RIM RAM ROM RUM RUN FUN FAN FIN BIN BIG BAG BUG DUG DOG
PEN PAN PIN PIG PUG RUG RUT BUT BUY BUN SUN SIN SOD SIR SAND HAND HARD HARE HAZE
COLD CORD CARD WARD WARM HARM HARE HERE HERO ZERO ZEST BEST BEAT MEAT SEAT SEAL TEAL TELL TALL TAIL BAIL BALL BELL BELT MELT MALT SALT
SAME SAGE PAGE PAVE PINE PINK SINK SING SONG LONG BONG BANG BUNG HUNG HUNT HINT MINT MIND BIND BINE
RATE RITE RICE RISE ROSE LOSE LOFT LEFT LEAF LEAN LOAN LOAD GOAD GOLD GOLF
FOOD GOOD WOOD MOOD MOLD BOLD SOLD SOLE SALE SAIL MAIL MAIN PAIN GAIN GRAN
FATE DATE DATA BETA META MEGA MEET MEAT HEAT SEAT SEAM TEAM TEAR BEAR BOAR BOAT COAT CHAT THAT WHAT
FISH DISH WISH WASH CASH CASE CASK MASK TASK TUSK DUSK DESK REST BEST BUST MUST MUSE
NOTE NODE MODE MADE MALE MILE MITE BITE BYTE
SPOT SPIT SPAT SLAT SLOT SLOG BLOG BLOT PLOT
CARS BARS BARN WARN WORN WORD WOOD
FORK FORM FROM FROG
TONE TUNE TANK RANK RING KING KIND WIND WINE WIDE
""".strip().split()

def normalize_word(w: str) -> str:
    w = w.strip()
    if not w:
        return w
    # Keep alphabetic only, uppercase
    return "".join([c for c in w.upper() if c.isalpha()])

def build_dictionary():
    words = set()
    for w in WORDLIST_RAW:
        nw = normalize_word(w)
        if 3 <= len(nw) <= 5:
            words.add(nw)
    # Ensure some essential words exist
    essentials = ["MOM", "DAD", "CAT", "DOG", "COLD", "WARM", "FOOD", "GOOD"]
    for e in essentials:
        words.add(e)
    return words

WORDS = build_dictionary()

def neighbors(word, wordset):
    """Generate valid neighbor words differing by exactly one letter."""
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

def bfs_shortest_distance(start, end, wordset):
    """Standard BFS for unweighted shortest path length in edges."""
    if start == end:
        return 0, [start]
    q = deque([start])
    dist = {start: 0}
    parent = {start: None}
    while q:
        cur = q.popleft()
        d = dist[cur]
        for nb in neighbors(cur, wordset):
            if nb not in dist:
                dist[nb] = d + 1
                parent[nb] = cur
                if nb == end:
                    # reconstruct path
                    path = [end]
                    x = end
                    while parent[x] is not None:
                        x = parent[x]
                        path.append(x)
                    path.reverse()
                    return dist[end], path
                q.append(nb)
    return None, None

def bfs_count_shortest_paths(start, end, wordset, max_states=200000):
    """
    Independent check: compute shortest distance and number of shortest paths
    using layered BFS DP (no parent reconstruction).
    """
    if start == end:
        return 0, 1
    q = deque([start])
    dist = {start: 0}
    ways = defaultdict(int)
    ways[start] = 1
    visited_order = 0

    while q:
        cur = q.popleft()
        visited_order += 1
        if visited_order > max_states:
            raise RuntimeError("State exploration limit exceeded in bfs_count_shortest_paths")
        for nb in neighbors(cur, wordset):
            nd = dist[cur] + 1
            if nb not in dist:
                dist[nb] = nd
                ways[nb] = ways[cur]
                q.append(nb)
            else:
                if dist[nb] == nd:
                    ways[nb] += ways[cur]
    return dist.get(end, None), ways.get(end, 0)

def all_words_by_length(wordset):
    m = defaultdict(list)
    for w in wordset:
        m[len(w)].append(w)
    return m

WORDS_BY_LEN = all_words_by_length(WORDS)

def format_problem_zh(start, end, require_unique=False, extra_note=None):
    uniq_line = ""
    if require_unique:
        uniq_line = "（保证最短路径步数是唯一的。）\n"
    note_line = ""
    if extra_note:
        note_line = extra_note.strip() + "\n"
    problem = (
        "你正在玩一个“单词接龙”变形游戏，规则如下：\n"
        "1）给定起始单词与目标单词，二者长度相同。\n"
        "2）每一步只能改变一个字母，且每一步得到的中间单词必须是一个有效英文单词。\n"
        "3）目标是用最少步数从起始单词变到目标单词。\n"
        "问题：从「{s}」变到「{t}」最少需要多少步？\n"
        "{uniq}"
        "{note}"
        "请将答案写成双中括号形式，例如 [[3]]。\n"
    ).format(s=start, t=end, uniq=uniq_line, note=note_line)
    return problem

def format_explanation_zh(start, end, dist, path, unique_paths_count=None):
    # Provide a concrete shortest path as verifiable evidence
    # Also mention Hamming differences can be lower bound.
    def hamming(a, b):
        return sum(1 for x, y in zip(a, b) if x != y)
    lb = hamming(start, end)
    path_str = " → ".join(path) if path else "(无路径)"
    uniq_part = ""
    if unique_paths_count is not None:
        uniq_part = f"；最短路径条数（独立计数）= {unique_paths_count}"
    exp = (
        f"下界校验：起始词与目标词的不同字母数= {lb}，因此最少步数 ≥ {lb}。\n"
        f"用 BFS 找到的一条最短变换序列为：{path_str}。\n"
        f"该序列包含 {len(path)-1} 次单字母替换，所以最少步数 ≤ {len(path)-1}。\n"
        f"综合可得最少步数 = {dist}{uniq_part}。"
    )
    return exp

def choose_pair_with_constraints(rng, length, min_dist, max_dist, require_unique, max_tries=5000):
    candidates = WORDS_BY_LEN[length]
    if len(candidates) < 10:
        raise RuntimeError("Dictionary too small for this length")
    for _ in range(max_tries):
        start = rng.choice(candidates)
        end = rng.choice(candidates)
        if start == end:
            continue
        # quick lower bound check via hamming
        ham = sum(1 for a, b in zip(start, end) if a != b)
        if ham > max_dist:
            continue
        # compute distance/path
        dist, path = bfs_shortest_distance(start, end, WORDS)
        if dist is None:
            continue
        if not (min_dist <= dist <= max_dist):
            continue
        # independent verification + uniqueness if requested
        dist2, ways = bfs_count_shortest_paths(start, end, WORDS)
        if dist2 != dist:
            continue
        if require_unique and ways != 1:
            continue
        return start, end, dist, path, ways
    raise RuntimeError("Failed to sample a suitable word pair within try limit")

def generate_one(rng, idx):
    # Variety knobs
    length = rng.choice([3, 3, 3, 4, 4, 5])  # bias to 3-4
    require_unique = rng.random() < 0.35
    # distance targets depend on length
    if length == 3:
        min_dist, max_dist = (2, 4) if not require_unique else (2, 5)
    elif length == 4:
        min_dist, max_dist = (3, 6) if not require_unique else (3, 7)
    else:
        min_dist, max_dist = (3, 7) if not require_unique else (3, 8)

    start, end, dist, path, ways = choose_pair_with_constraints(
        rng, length, min_dist, max_dist, require_unique
    )

    # Small scene variation note
    extra_note = None
    if rng.random() < 0.4:
        extra_note = "提示：每一步只能改动一个字母（位置任选），且中间词必须在英文词表中。"
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
    # bounded resampling to avoid duplicates
    attempts = 0
    max_attempts = count * 200
    while len(res) < count and attempts < max_attempts:
        attempts += 1
        item = generate_one(rng, len(res))
        key = (item["problem"], item["answer"])
        if key in seen:
            continue
        seen.add(key)
        # basic sanity checks
        if not item["problem"].strip() or item["answer"] is None or item["explanation"] is None:
            continue
        res.append(item)

    if len(res) != count:
        print(f"Generation failed: produced {len(res)} / {count} items after {attempts} attempts.", file=sys.stderr)
        sys.exit(1)

    json.dump(res, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()