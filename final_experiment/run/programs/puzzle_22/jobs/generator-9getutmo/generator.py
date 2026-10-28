import sys, json, random, math
from collections import deque, defaultdict

# ---------- Core utilities ----------

DIRS_8 = [
    (-1, 0, "↑"), (1, 0, "↓"), (0, -1, "←"), (0, 1, "→"),
    (-1, -1, "↖"), (-1, 1, "↗"), (1, -1, "↙"), (1, 1, "↘")
]
ARROW_TO_VEC = {sym: (dr, dc) for dr, dc, sym in DIRS_8}
VEC_TO_ARROW = {(dr, dc): sym for dr, dc, sym in DIRS_8}

def inb(r, c, R, C):
    return 0 <= r < R and 0 <= c < C

def format_grid(grid, start, end):
    """Render grid with arrows; start marked as ◎, end as ★.
    Ensure self-contained rule: arrows in each cell; start/end positions.
    """
    R, C = len(grid), len(grid[0])
    lines = []
    for r in range(R):
        row = []
        for c in range(C):
            ch = grid[r][c]
            if (r, c) == start:
                row.append("◎")
            elif (r, c) == end:
                row.append("★")
            else:
                row.append(ch)
        lines.append(" ".join(row))
    return "\n".join(lines)

def follow_path(grid, start, end, max_steps=10000):
    """Follow arrows deterministically; return path list of cells visited in order (including start and end if reached).
    If loops or exits grid without reaching end, return None.
    """
    R, C = len(grid), len(grid[0])
    r, c = start
    path = [(r, c)]
    seen = {(r, c): 0}
    steps = 0
    while steps < max_steps:
        if (r, c) == end:
            return path
        arrow = grid[r][c]
        if arrow not in ARROW_TO_VEC:
            return None
        dr, dc = ARROW_TO_VEC[arrow]
        nr, nc = r + dr, c + dc
        if not inb(nr, nc, R, C):
            return None
        r, c = nr, nc
        path.append((r, c))
        steps += 1
        if (r, c) in seen:
            # loop
            return None
        seen[(r, c)] = steps
    return None

def compute_inflections(path):
    """Return ordered list of inflection points (cells) along path.
    Define inflection point as a path cell where direction changes compared to previous move.
    We output positions (1..k) for inflection points in encounter order, 0 otherwise.
    Start cell can be an inflection only if direction changes at it (not applicable); we mark changes at the 'turning' cell
    i.e., at path[i] for i>=1 where move into i and move out of i differ.
    End has no outgoing move so it's not marked.
    """
    if not path or len(path) < 3:
        return []
    inflections = []
    # directions between consecutive cells
    dirs = []
    for i in range(1, len(path)):
        r0, c0 = path[i-1]
        r1, c1 = path[i]
        dirs.append((r1-r0, c1-c0))
    # turning at path[i] for i=1..len(path)-2 where dirs[i-1] != dirs[i]
    for i in range(1, len(path)-1):
        if dirs[i-1] != dirs[i]:
            inflections.append(path[i])
    return inflections

def inflection_label_grid(R, C, inflections):
    """Create grid labels with 0 for non-inflection; otherwise 1..k in order of encounter."""
    lab = [[0 for _ in range(C)] for __ in range(R)]
    for idx, (r, c) in enumerate(inflections, start=1):
        lab[r][c] = idx
    return lab

def render_answer_matrix(lab):
    """Return string like [[1 0 2,4 0 5]] with rows separated by comma."""
    rows = []
    for r in lab:
        rows.append(" ".join(str(x) for x in r))
    return "[[" + ",".join(rows) + "]]"

# ---------- Generation families ----------

def generate_snake_path(rng, R, C):
    """Construct a Hamiltonian-like snake path from a start to an end within grid using axis moves."""
    # choose orientation
    horizontal = rng.choice([True, False])
    path = []
    if horizontal:
        for r in range(R):
            cols = list(range(C)) if r % 2 == 0 else list(range(C-1, -1, -1))
            for c in cols:
                path.append((r, c))
    else:
        for c in range(C):
            rows = list(range(R)) if c % 2 == 0 else list(range(R-1, -1, -1))
            for r in rows:
                path.append((r, c))
    # choose a contiguous segment of this snake as actual path to increase variety
    n = len(path)
    seg_len = rng.randint(max(6, min(n, 8)), min(n, max(10, n)))  # allow full too
    if seg_len > n:
        seg_len = n
    start_idx = rng.randint(0, n - seg_len)
    segment = path[start_idx:start_idx+seg_len]
    # pick direction (forward/backward)
    if rng.random() < 0.5:
        segment = list(reversed(segment))
    start = segment[0]
    end = segment[-1]
    return segment, start, end

def generate_zigzag_path(rng, R, C):
    """Create a zigzag with diagonal moves allowed: alternate between diagonal and straight."""
    # pick start not too close to border to allow diagonal variations
    start = (rng.randrange(R), rng.randrange(C))
    # build path by random legal steps with bias to create turns
    path = [start]
    used = {start}
    steps = rng.randint(7, R*C // 2 + 6)
    last_dir = None
    for _ in range(steps):
        r, c = path[-1]
        candidates = []
        for dr, dc, sym in DIRS_8:
            nr, nc = r+dr, c+dc
            if inb(nr, nc, R, C) and (nr, nc) not in used:
                candidates.append((dr, dc))
        if not candidates:
            break
        # prefer turning
        if last_dir is None:
            dr, dc = rng.choice(candidates)
        else:
            turning = [d for d in candidates if d != last_dir]
            if turning and rng.random() < 0.75:
                dr, dc = rng.choice(turning)
            else:
                dr, dc = rng.choice(candidates)
        nr, nc = r+dr, c+dc
        path.append((nr, nc))
        used.add((nr, nc))
        last_dir = (dr, dc)
    if len(path) < 6:
        # fallback to snake
        return generate_snake_path(rng, R, C)
    end = path[-1]
    return path, start, end

def build_grid_from_path(rng, R, C, path, start, end, allow_diagonal=True):
    """Assign arrows so that from each path cell except end points to next.
    For non-path cells, assign arrows that do not enter the path (or create harmless cycles) to avoid alternative reaching end/start.
    """
    grid = [[None for _ in range(C)] for __ in range(R)]
    path_set = set(path)

    # set arrows along path
    for i in range(len(path)-1):
        r0, c0 = path[i]
        r1, c1 = path[i+1]
        dr, dc = r1-r0, c1-c0
        if (dr, dc) not in VEC_TO_ARROW:
            return None
        grid[r0][c0] = VEC_TO_ARROW[(dr, dc)]
    # end points to itself via an arrow that leads out but we must keep in-grid; choose any arrow but irrelevant
    # However rule forces move; to make reaching end "win", we treat arriving at ★ as terminal.
    # Still we provide an arrow in end cell to satisfy "each cell has an arrow".
    er, ec = end
    # choose an arrow that stays in bounds if possible
    end_dirs = [(dr, dc, sym) for dr, dc, sym in DIRS_8 if inb(er+dr, ec+dc, R, C)]
    grid[er][ec] = rng.choice(end_dirs)[2]

    # non-path cells: point to themselves via a 2-cycle or to boundary loops, but ensure from any such cell cannot reach end
    # Simple strategy: make all non-path cells point "↑" if possible else "↓", which tends to exit boundary loops,
    # but must stay in grid always; so choose arrow that stays in bounds.
    # Additionally avoid arrows that step into path to prevent other starts reaching end.
    for r in range(R):
        for c in range(C):
            if grid[r][c] is not None:
                continue
            safe_dirs = []
            for dr, dc, sym in DIRS_8:
                nr, nc = r+dr, c+dc
                if inb(nr, nc, R, C) and (nr, nc) not in path_set:
                    safe_dirs.append(sym)
            if not safe_dirs:
                # if surrounded by path, allow stepping into non-end path? better resample
                return None
            grid[r][c] = rng.choice(safe_dirs)
    return grid

def verify_instance(grid, start, end, require_unique=True):
    """Verify path from start reaches end and compute inflections. Optionally ensure uniqueness:
    since movement deterministic, uniqueness means: from start it reaches end (always unique if reaches).
    We additionally ensure no other cell reaches end to reduce ambiguity in interpretation.
    """
    R, C = len(grid), len(grid[0])
    path = follow_path(grid, start, end)
    if path is None:
        return None
    # ensure deterministic path doesn't revisit cells
    if len(set(path)) != len(path):
        return None
    # optional: ensure start isn't reachable from elsewhere? not needed
    if require_unique:
        # check count of cells that eventually reach end is exactly len(path) maybe plus end-only from itself
        reaches_end = 0
        for r in range(R):
            for c in range(C):
                p = follow_path(grid, (r, c), end, max_steps=R*C+5)
                if p is not None:
                    reaches_end += 1
        # At minimum, all path cells reach end; for stricter uniqueness, require exactly len(path)
        if reaches_end != len(path):
            return None
    infl = compute_inflections(path)
    return path, infl

def make_problem_text(grid, start, end, output_language="zh"):
    R, C = len(grid), len(grid[0])
    grid_txt = format_grid(grid, start, end)
    if output_language == "zh":
        return (
            "下面是一个箭头迷宫。\n"
            "规则：在每个格子中都有一个箭头（上下左右或对角）。从起点◎出发，必须严格按照当前格子的箭头移动到下一个格子，"
            "再按新格子的箭头继续移动；到达终点★即算成功。\n\n"
            "要求：请找出从◎到★的路径上所有“拐点”（相邻两步的移动方向发生改变的那个格子），按在路径上出现的先后顺序编号为1,2,3,...；"
            "不在拐点位置填0。\n"
            "输出格式：按从左到右、从上到下输出一个矩阵；同一行用空格分隔，不同行用英文逗号`,`分隔；最外层用双中括号包裹。\n"
            f"迷宫大小：{R}行×{C}列\n\n"
            f"{grid_txt}\n"
        )
    else:
        # fallback simple English
        return (
            "Arrow maze. Start at ◎ and follow the arrow in each cell strictly; reaching ★ wins.\n"
            "Mark inflection (turn) cells where the move direction changes between consecutive steps, numbered 1..k in order; others 0.\n"
            "Output matrix left-to-right, top-to-bottom; spaces between entries, commas between rows, wrapped as [[...]].\n\n"
            f"Size: {R}x{C}\n\n{grid_txt}\n"
        )

def explanation_text(path, infl, R, C, output_language="zh"):
    # Provide compact verifiable evidence: list the path coordinates (1-indexed) and inflection coordinates.
    # Coordinates in (row,col) 1-based.
    def to1(p): return (p[0]+1, p[1]+1)
    path1 = [to1(p) for p in path]
    infl1 = [to1(p) for p in infl]
    if output_language == "zh":
        return (
            "按箭头从起点依次移动可得到唯一路径（用1-based坐标表示为(行,列)）：\n"
            f"{path1}\n"
            "对相邻两步的方向作比较，方向发生改变的位置即为拐点；拐点依次为：\n"
            f"{infl1}\n"
            "因此这些格子在矩阵中依次标为1,2,3,...，其余为0。"
        )
    else:
        return f"Path (1-based (r,c)): {path1}\nInflections: {infl1}"

# ---------- Main generator ----------

def generate_one(rng, output_language="zh"):
    # choose size and family
    for attempt in range(200):
        R = rng.randint(2, 6)
        C = rng.randint(2, 6)
        family = rng.choice(["snake", "zigzag"])
        if family == "snake":
            path, start, end = generate_snake_path(rng, R, C)
        else:
            path, start, end = generate_zigzag_path(rng, R, C)

        # ensure end different from start
        if start == end:
            continue

        grid = build_grid_from_path(rng, R, C, path, start, end)
        if grid is None:
            continue

        ver = verify_instance(grid, start, end, require_unique=True)
        if ver is None:
            continue
        path2, infl = ver

        lab = inflection_label_grid(R, C, infl)
        ans = render_answer_matrix(lab)

        problem = make_problem_text(grid, start, end, output_language=output_language)
        expl = explanation_text(path2, infl, R, C, output_language=output_language)

        # quick internal consistency check: recompute from labels
        # ensure labels are 1..k exactly once each
        k = len(infl)
        seen = []
        for r in range(R):
            for c in range(C):
                v = lab[r][c]
                if v != 0:
                    seen.append(v)
        if sorted(seen) != list(range(1, k+1)):
            continue

        return {"problem": problem, "answer": ans, "explanation": expl}

    raise RuntimeError("生成失败：在尝试次数上限内未能构造出满足条件的迷宫实例。")

def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data)
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count must be positive")
    except Exception as e:
        print(f"Invalid input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    output_language = "zh"

    res = []
    seen_fingerprints = set()
    # generate with dedup by fingerprint of grid + start/end
    for i in range(count):
        for attempt in range(400):
            item = generate_one(rng, output_language=output_language)
            # fingerprint
            prob = item["problem"]
            # stable fingerprint: take the grid lines after size line
            fp = prob.splitlines()[-(prob.splitlines()[::-1].index("") + 1):] if "" in prob.splitlines() else prob
            fp = item["answer"] + "\n" + item["problem"]
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)
            res.append(item)
            break
        else:
            raise RuntimeError("生成失败：重复过多或无法在上限内生成足够不同的题目。")

    sys.stdout.write(json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    main()