import sys, json, random
from typing import List, Tuple, Dict, Any, Optional, Set
from z3 import Solver, Int, And, Or, Distinct, sat

ARROWS = ["↑", "↓", "←", "→", "↖", "↗", "↘", "↙"]
DIRS = {
    "↑": (-1, 0),
    "↓": (1, 0),
    "←": (0, -1),
    "→": (0, 1),
    "↖": (-1, -1),
    "↗": (-1, 1),
    "↘": (1, 1),
    "↙": (1, -1),
}
DIR_LIST = [DIRS[a] for a in ARROWS]
DIR_TO_ARROW = {v: k for k, v in DIRS.items()}


def inb(n, r, c):
    return 0 <= r < n and 0 <= c < n


def ray_length(n: int, grid_dirs: List[List[Tuple[int, int]]], start: Tuple[int, int]) -> int:
    """Length of the maximal arrow chain starting from start, counting visited cells.
    Chain ends if next step goes out of bounds OR repeats a visited cell (cycle).
    """
    r, c = start
    seen = set()
    length = 0
    while True:
        if not inb(n, r, c):
            break
        if (r, c) in seen:
            break
        seen.add((r, c))
        length += 1
        dr, dc = grid_dirs[r][c]
        r, c = r + dr, c + dc
    return length


def compute_numbers(n: int, grid_dirs: List[List[Tuple[int, int]]], starts: List[Tuple[int, int]]) -> Dict[Tuple[int, int], int]:
    return {pos: ray_length(n, grid_dirs, pos) for pos in starts}


def build_z3_model(n: int, starts_to_num: Dict[Tuple[int, int], int], fixed_arrows: Dict[Tuple[int, int], str]):
    """Z3: each cell has a direction (0..7). For each numbered start, enforce chain length equals given.
    Also enforce: from each numbered start, the path does not self-intersect within its length,
    and leaves grid after its length (i.e., next step out of bounds) to make definition unambiguous.
    """
    s = Solver()
    d = [[Int(f"d_{r}_{c}") for c in range(n)] for r in range(n)]
    for r in range(n):
        for c in range(n):
            s.add(And(d[r][c] >= 0, d[r][c] <= 7))

    # fixed arrows
    for (r, c), a in fixed_arrows.items():
        idx = ARROWS.index(a)
        s.add(d[r][c] == idx)

    # helper to step
    def step(r, c, idx):
        dr, dc = DIR_LIST[idx]
        return r + dr, c + dc

    # constraints for each numbered cell
    for (sr, sc), L in starts_to_num.items():
        # positions along the chain: p0..p_{L-1}
        pr = [Int(f"pr_{sr}_{sc}_{i}") for i in range(L)]
        pc = [Int(f"pc_{sr}_{sc}_{i}") for i in range(L)]
        s.add(pr[0] == sr, pc[0] == sc)

        # all inside
        for i in range(L):
            s.add(And(pr[i] >= 0, pr[i] < n, pc[i] >= 0, pc[i] < n))

        # no repeats
        s.add(Distinct([pr[i] * n + pc[i] for i in range(L)]))

        # successor relation for i < L-1
        for i in range(L - 1):
            # (pr[i+1],pc[i+1]) = step(pr[i],pc[i], d[pr[i]][pc[i]])
            # Z3 needs piecewise:
            cases = []
            for idx, (dr, dc) in enumerate(DIR_LIST):
                cases.append(And(d[0][0] == -1))  # dummy placeholder
            # We'll encode with Or over idx matching d at that cell
            ors = []
            for idx, (dr, dc) in enumerate(DIR_LIST):
                ors.append(
                    And(
                        d[pr[i]][pc[i]] == idx,
                        pr[i + 1] == pr[i] + dr,
                        pc[i + 1] == pc[i] + dc,
                    )
                )
            s.add(Or(*ors))

        # after L-1, next step must be out of bounds
        last_r = pr[L - 1]
        last_c = pc[L - 1]
        out_ors = []
        for idx, (dr, dc) in enumerate(DIR_LIST):
            nr = last_r + dr
            nc = last_c + dc
            out_ors.append(
                And(
                    d[last_r][last_c] == idx,
                    Or(nr < 0, nr >= n, nc < 0, nc >= n),
                )
            )
        s.add(Or(*out_ors))

    return s, d


def solve_unique(n: int, starts_to_num: Dict[Tuple[int, int], int], fixed_arrows: Dict[Tuple[int, int], str]) -> Tuple[bool, Optional[List[List[str]]], str]:
    s, d = build_z3_model(n, starts_to_num, fixed_arrows)
    if s.check() != sat:
        return False, None, "无解"

    m = s.model()
    sol1 = [[ARROWS[m.eval(d[r][c]).as_long()] for c in range(n)] for r in range(n)]

    # uniqueness: block this full assignment
    block = []
    for r in range(n):
        for c in range(n):
            block.append(d[r][c] != m.eval(d[r][c]))
    s.add(Or(*block))
    unique = (s.check() != sat)
    if not unique:
        return False, None, "多解"
    return True, sol1, "唯一解"


def render_problem(n: int, starts_to_num: Dict[Tuple[int, int], int], fixed_arrows: Dict[Tuple[int, int], str], output_language: str) -> str:
    # Build grid with "X" for blanks, numbers for starts, and arrows for fixed arrows (given).
    grid = [["X" for _ in range(n)] for _ in range(n)]
    for (r, c), L in starts_to_num.items():
        grid[r][c] = str(L)
    for (r, c), a in fixed_arrows.items():
        # only show fixed arrow if it's not a numbered cell
        if (r, c) not in starts_to_num:
            grid[r][c] = a

    # Description: define ray chain length as number of visited cells following arrows until leaving grid,
    # and require that for numbered cells the chain does not revisit a cell before leaving.
    if output_language == "zh":
        desc = []
        desc.append(f"你需要完成一个 {n} x {n} 的箭头迷宫。")
        desc.append("网格中：")
        desc.append(" - \"X\" 表示需要你填入一个箭头（↑、↓、←、→、↖、↗、↘、↙）。")
        desc.append(" - 数字表示一个“起点格”。")
        if fixed_arrows:
            desc.append(" - 另外有少量格子已预先给出箭头，必须保持不变。")
        desc.append("")
        desc.append("规则（请按下面的公开规则理解并求解）：")
        desc.append("1) 每个格子最终都恰好包含 1 个箭头（预填箭头也算）。")
        desc.append("2) 从某个起点格出发，按该格箭头指向移动到下一个格，再按新格箭头继续移动，如此形成一条“箭头串”。")
        desc.append("3) 该起点对应的数字等于：从起点开始依次经过的格子数量，直到下一步将走出网格为止。")
        desc.append("4) 额外约束：对每个起点，其箭头串在走出网格之前不得重复经过同一个格子（即起点射线不允许在网格内形成回路/自交）。")
        desc.append("")
        desc.append("请填完整网格。按如下二维数组格式作答（数字格保留数字，预填箭头保留箭头，其余填箭头）：")
        desc.append(json.dumps(grid, ensure_ascii=False, indent=2))
        return "\n".join(desc)

    # default Chinese
    return render_problem(n, starts_to_num, fixed_arrows, "zh")


def render_answer_grid(n: int, arrow_grid: List[List[str]], starts_to_num: Dict[Tuple[int, int], int]) -> List[List[str]]:
    out = [[arrow_grid[r][c] for c in range(n)] for r in range(n)]
    for (r, c), L in starts_to_num.items():
        out[r][c] = str(L)
    return out


def format_explanation(n: int, arrow_grid: List[List[str]], starts_to_num: Dict[Tuple[int, int], int], fixed_arrows: Dict[Tuple[int, int], str], output_language: str) -> str:
    # Provide verifiable evidence: list each start and its path coordinates and length, plus fixed-arrow check.
    dirs = [[DIRS[arrow_grid[r][c]] for c in range(n)] for r in range(n)]
    lines = []
    if output_language == "zh":
        if fixed_arrows:
            ok = all(arrow_grid[r][c] == a for (r, c), a in fixed_arrows.items())
            lines.append(f"预填箭头一致性检查：{'通过' if ok else '失败'}。")
        for (sr, sc), L in sorted(starts_to_num.items()):
            path = []
            r, c = sr, sc
            seen = set()
            while True:
                if not inb(n, r, c) or (r, c) in seen:
                    break
                seen.add((r, c))
                path.append((r, c))
                dr, dc = dirs[r][c]
                r, c = r + dr, c + dc
            # next step out of bounds is required by our solving constraints
            lines.append(f"起点({sr+1},{sc+1}) 的数字={L}：路径(1基坐标)={[(r+1,c+1) for (r,c) in path]}，长度={len(path)}。")
        lines.append("将每个起点的路径长度与题面数字对照，均相等；且每条路径在出界前不重复经过格子。")
        return "\n".join(lines)
    return format_explanation(n, arrow_grid, starts_to_num, fixed_arrows, "zh")


def random_full_arrow_grid(rng: random.Random, n: int) -> List[List[str]]:
    return [[rng.choice(ARROWS) for _ in range(n)] for _ in range(n)]


def pick_positions(rng: random.Random, n: int, k: int) -> List[Tuple[int, int]]:
    allpos = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(allpos)
    return allpos[:k]


def generate_one(rng: random.Random, output_language: str) -> Dict[str, Any]:
    # Choose size and counts
    n = rng.choice([5, 6])
    starts_k = rng.randint(max(4, n - 1), min(n + 3, n * n // 2))
    fixed_k = rng.randint(0, max(0, n - 3))

    # Attempt construct + ensure unique solvable
    for _ in range(200):
        base = random_full_arrow_grid(rng, n)
        base_dirs = [[DIRS[base[r][c]] for c in range(n)] for r in range(n)]
        starts = pick_positions(rng, n, starts_k)
        starts_to_num = compute_numbers(n, base_dirs, starts)

        # Filter out too-long/too-short extremes to keep puzzle reasonable
        # want lengths between 2 and 2n roughly
        if any(L < 2 or L > 2 * n + 2 for L in starts_to_num.values()):
            continue

        # choose some fixed arrows not on numbered cells
        non_start = [(r, c) for r in range(n) for c in range(n) if (r, c) not in starts_to_num]
        rng.shuffle(non_start)
        fixed_positions = non_start[:fixed_k]
        fixed_arrows = {(r, c): base[r][c] for (r, c) in fixed_positions}

        ok, solved_grid, why = solve_unique(n, starts_to_num, fixed_arrows)
        if not ok:
            continue

        # Cross-check numerically using independent simulation
        solved_dirs = [[DIRS[solved_grid[r][c]] for c in range(n)] for r in range(n)]
        nums2 = compute_numbers(n, solved_dirs, list(starts_to_num.keys()))
        if nums2 != starts_to_num:
            continue
        # fixed check
        if any(solved_grid[r][c] != a for (r, c), a in fixed_arrows.items()):
            continue

        problem = render_problem(n, starts_to_num, fixed_arrows, output_language)
        answer_grid = render_answer_grid(n, solved_grid, starts_to_num)
        explanation = format_explanation(n, solved_grid, starts_to_num, fixed_arrows, output_language)
        return {
            "problem": problem,
            "answer": answer_grid,
            "explanation": explanation
        }

    raise RuntimeError("生成失败：在采样上限内未找到满足唯一解与校验的实例。")


def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    # output_language passed via user request in outer system; keep default zh if absent.
    # Here we accept it if embedded by caller; otherwise zh.
    output_language = data.get("output_language", "zh")

    rng = random.Random(seed)
    items = []
    seen_problems: Set[str] = set()

    attempts = 0
    while len(items) < count and attempts < count * 50:
        attempts += 1
        try:
            obj = generate_one(rng, output_language)
        except Exception as e:
            print(str(e), file=sys.stderr)
            continue
        # de-dup by problem text
        if obj["problem"] in seen_problems:
            continue
        seen_problems.add(obj["problem"])
        items.append(obj)

    if len(items) != count:
        raise RuntimeError(f"未能生成足够数量的题目：需要 {count}，实际 {len(items)}。")

    sys.stdout.write(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()