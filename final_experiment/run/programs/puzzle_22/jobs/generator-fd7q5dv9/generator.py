import sys, json, random
from collections import defaultdict

DIRS_8 = [
    (-1, 0, "↑"), (1, 0, "↓"), (0, -1, "←"), (0, 1, "→"),
    (-1, -1, "↖"), (-1, 1, "↗"), (1, -1, "↙"), (1, 1, "↘")
]
ARROW_TO_VEC = {sym: (dr, dc) for dr, dc, sym in DIRS_8}
VEC_TO_ARROW = {(dr, dc): sym for dr, dc, sym in DIRS_8}


def inb(r, c, R, C):
    return 0 <= r < R and 0 <= c < C


def format_grid(grid, start, end):
    R, C = len(grid), len(grid[0])
    lines = []
    for r in range(R):
        row = []
        for c in range(C):
            if (r, c) == start:
                row.append("◎")
            elif (r, c) == end:
                row.append("★")
            else:
                row.append(grid[r][c])
        lines.append(" ".join(row))
    return "\n".join(lines)


def follow_path(grid, start, end, max_steps=10000):
    R, C = len(grid), len(grid[0])
    r, c = start
    path = [(r, c)]
    seen = {(r, c)}
    for _ in range(max_steps):
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
        if (r, c) in seen:
            return None
        seen.add((r, c))
        path.append((r, c))
    return None


def compute_inflections(path):
    # turning at path[i] (1<=i<=len-2) where direction into i differs from direction out of i
    if not path or len(path) < 3:
        return []
    dirs = []
    for i in range(1, len(path)):
        r0, c0 = path[i - 1]
        r1, c1 = path[i]
        dirs.append((r1 - r0, c1 - c0))
    infl = []
    for i in range(1, len(path) - 1):
        if dirs[i - 1] != dirs[i]:
            infl.append(path[i])
    return infl


def inflection_label_grid(R, C, inflections):
    lab = [[0 for _ in range(C)] for __ in range(R)]
    for idx, (r, c) in enumerate(inflections, start=1):
        lab[r][c] = idx
    return lab


def render_answer_matrix(lab):
    rows = []
    for r in lab:
        rows.append(" ".join(str(x) for x in r))
    return "[[" + ",".join(rows) + "]]"


def generate_snake_path(rng, R, C):
    horizontal = rng.choice([True, False])
    base = []
    if horizontal:
        for r in range(R):
            cols = list(range(C)) if r % 2 == 0 else list(range(C - 1, -1, -1))
            for c in cols:
                base.append((r, c))
    else:
        for c in range(C):
            rows = list(range(R)) if c % 2 == 0 else list(range(R - 1, -1, -1))
            for r in rows:
                base.append((r, c))

    n = len(base)
    # robust segment length selection (fixes empty range bug)
    min_len = min(n, 4)  # for tiny grids
    # prefer longer paths, but keep legal
    preferred_low = min(n, 6)
    preferred_high = min(n, max(8, n))  # can be n
    low = min(preferred_low, preferred_high)
    high = max(preferred_low, preferred_high)
    low = max(2, low)
    high = max(low, high)

    seg_len = rng.randint(low, high)
    start_idx = rng.randint(0, n - seg_len)
    segment = base[start_idx:start_idx + seg_len]
    if rng.random() < 0.5:
        segment = list(reversed(segment))
    start = segment[0]
    end = segment[-1]
    return segment, start, end


def generate_zigzag_path(rng, R, C):
    start = (rng.randrange(R), rng.randrange(C))
    path = [start]
    used = {start}
    steps_target = rng.randint(5, max(5, (R * C) // 2 + 2))
    last_dir = None
    for _ in range(steps_target):
        r, c = path[-1]
        candidates = []
        for dr, dc, sym in DIRS_8:
            nr, nc = r + dr, c + dc
            if inb(nr, nc, R, C) and (nr, nc) not in used:
                candidates.append((dr, dc))
        if not candidates:
            break
        if last_dir is None:
            dr, dc = rng.choice(candidates)
        else:
            turning = [d for d in candidates if d != last_dir]
            if turning and rng.random() < 0.75:
                dr, dc = rng.choice(turning)
            else:
                dr, dc = rng.choice(candidates)
        nr, nc = r + dr, c + dc
        path.append((nr, nc))
        used.add((nr, nc))
        last_dir = (dr, dc)

    if len(path) < 4:
        return generate_snake_path(rng, R, C)
    end = path[-1]
    return path, start, end


def build_grid_from_path(rng, R, C, path, start, end):
    grid = [[None for _ in range(C)] for __ in range(R)]
    path_set = set(path)

    # along path: each points to next
    for i in range(len(path) - 1):
        r0, c0 = path[i]
        r1, c1 = path[i + 1]
        dr, dc = r1 - r0, c1 - c0
        if (dr, dc) not in VEC_TO_ARROW:
            return None
        grid[r0][c0] = VEC_TO_ARROW[(dr, dc)]

    # end cell still needs an arrow; pick any in-bound arrow
    er, ec = end
    inb_dirs = [sym for dr, dc, sym in DIRS_8 if inb(er + dr, ec + dc, R, C)]
    if not inb_dirs:
        return None
    grid[er][ec] = rng.choice(inb_dirs)

    # non-path cells: choose arrows staying in bounds and (preferably) not entering the path
    for r in range(R):
        for c in range(C):
            if grid[r][c] is not None:
                continue
            safe = []
            for dr, dc, sym in DIRS_8:
                nr, nc = r + dr, c + dc
                if inb(nr, nc, R, C) and (nr, nc) not in path_set:
                    safe.append(sym)
            if not safe:
                return None
            grid[r][c] = rng.choice(safe)

    return grid


def verify_instance(grid, start, end, require_unique_reachers=True):
    R, C = len(grid), len(grid[0])
    path = follow_path(grid, start, end, max_steps=R * C + 10)
    if path is None:
        return None
    if len(set(path)) != len(path):
        return None

    if require_unique_reachers:
        # count how many starts can reach end
        reachers = 0
        for r in range(R):
            for c in range(C):
                p = follow_path(grid, (r, c), end, max_steps=R * C + 10)
                if p is not None:
                    reachers += 1
        if reachers != len(path):
            return None

    infl = compute_inflections(path)
    return path, infl


def make_problem_text(grid, start, end, output_language="zh"):
    R, C = len(grid), len(grid[0])
    grid_txt = format_grid(grid, start, end)
    if output_language == "zh":
        return (
            "下面是一个箭头迷宫。\n"
            "规则：每个格子里有一个箭头（上下左右或对角方向）。从起点◎出发，必须严格沿当前格子的箭头移动到下一个格子，"
            "再按新格子的箭头继续移动；当到达终点★时立刻停止并算成功。\n\n"
            "要求：找出从◎到★的路径上所有“拐点”。拐点定义为：某个格子在路径中既有进入该格子的移动，也有离开该格子的移动，"
            "且这两次移动方向不同。按在路径上出现的先后顺序把拐点编号为1,2,3,...；非拐点位置填0。\n\n"
            "输出格式：按从左到右、从上到下输出矩阵；同一行用空格分隔，不同行用英文逗号`,`分隔；最外层用双中括号包裹。\n"
            f"迷宫大小：{R}行×{C}列\n\n"
            f"{grid_txt}\n"
        )
    else:
        return (
            "Arrow maze. Start at ◎ and follow arrows strictly; stop when reaching ★.\n"
            "Mark inflection cells (turns) where incoming direction differs from outgoing direction, numbered 1..k in order; others 0.\n"
            "Output matrix with spaces, commas between rows, wrapped in [[...]].\n\n"
            f"Size: {R}x{C}\n\n{grid_txt}\n"
        )


def explanation_text(path, infl, output_language="zh"):
    def to1(p): return (p[0] + 1, p[1] + 1)
    path1 = [to1(p) for p in path]
    infl1 = [to1(p) for p in infl]
    if output_language == "zh":
        return (
            "从◎按箭头唯一地前进直到★，得到路径（1-based坐标(行,列)）：\n"
            f"{path1}\n"
            "比较每个中间格子的“进入方向”和“离开方向”，不同则为拐点；拐点依次为：\n"
            f"{infl1}\n"
            "因此在这些格子处分别填1,2,3,...，其余填0。"
        )
    else:
        return f"Path: {path1}\nInflections: {infl1}"


def generate_one(rng, output_language="zh"):
    for _ in range(300):
        R = rng.randint(2, 6)
        C = rng.randint(2, 6)
        family = rng.choice(["snake", "zigzag"])
        if family == "snake":
            path, start, end = generate_snake_path(rng, R, C)
        else:
            path, start, end = generate_zigzag_path(rng, R, C)

        if start == end:
            continue

        grid = build_grid_from_path(rng, R, C, path, start, end)
        if grid is None:
            continue

        ver = verify_instance(grid, start, end, require_unique_reachers=True)
        if ver is None:
            continue
        path2, infl = ver

        lab = inflection_label_grid(R, C, infl)
        ans = render_answer_matrix(lab)

        # label sanity: numbers 1..k each appear once
        k = len(infl)
        nums = []
        for r in range(R):
            for c in range(C):
                if lab[r][c] != 0:
                    nums.append(lab[r][c])
        if sorted(nums) != list(range(1, k + 1)):
            continue

        problem = make_problem_text(grid, start, end, output_language=output_language)
        expl = explanation_text(path2, infl, output_language=output_language)
        return {"problem": problem, "answer": ans, "explanation": expl}

    raise RuntimeError("生成失败：多次尝试仍无法构造满足条件的实例。")


def main():
    try:
        req = json.loads(sys.stdin.read())
        seed = int(req["seed"])
        count = int(req["count"])
        if count <= 0:
            raise ValueError("count必须为正整数")
    except Exception as e:
        print(f"Invalid input JSON: {e}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    output_language = "zh"

    res = []
    seen = set()
    for _ in range(count):
        for _try in range(600):
            item = generate_one(rng, output_language=output_language)
            fp = item["problem"]  # strong enough in practice
            if fp in seen:
                continue
            seen.add(fp)
            res.append(item)
            break
        else:
            print("生成失败：去重后无法达到要求数量。", file=sys.stderr)
            sys.exit(1)

    sys.stdout.write(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()