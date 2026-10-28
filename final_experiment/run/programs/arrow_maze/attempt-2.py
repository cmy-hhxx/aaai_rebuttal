import sys, json, random
from typing import List, Tuple, Dict, Any, Optional, Set
from z3 import Solver, Int, And, Or, Distinct, sat, If

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
ARROW_TO_IDX = {a: i for i, a in enumerate(ARROWS)}


def inb(n: int, r: int, c: int) -> bool:
    return 0 <= r < n and 0 <= c < n


def ray_trace(n: int, grid_dirs: List[List[Tuple[int, int]]], start: Tuple[int, int], limit: int = 10_000):
    """Return (path, out_of_bounds_next, repeated)"""
    r, c = start
    seen = set()
    path = []
    steps = 0
    while True:
        if steps > limit:
            return path, False, True
        if not inb(n, r, c):
            # shouldn't happen: we only step into in-bounds cells
            return path, True, False
        if (r, c) in seen:
            return path, False, True
        seen.add((r, c))
        path.append((r, c))
        dr, dc = grid_dirs[r][c]
        nr, nc = r + dr, c + dc
        if not inb(n, nr, nc):
            return path, True, False
        r, c = nr, nc
        steps += 1


def compute_numbers(n: int, grid_dirs: List[List[Tuple[int, int]]], starts: List[Tuple[int, int]]) -> Dict[Tuple[int, int], int]:
    out = {}
    for pos in starts:
        path, outb, rep = ray_trace(n, grid_dirs, pos)
        if rep:
            # mark as invalid with -1
            out[pos] = -1
        else:
            out[pos] = len(path)
    return out


def z3_dir_delta(idx_expr):
    dr = If(idx_expr == 0, -1,
         If(idx_expr == 1,  1,
         If(idx_expr == 2,  0,
         If(idx_expr == 3,  0,
         If(idx_expr == 4, -1,
         If(idx_expr == 5, -1,
         If(idx_expr == 6,  1,
                         1)))))))
    dc = If(idx_expr == 0,  0,
         If(idx_expr == 1,  0,
         If(idx_expr == 2, -1,
         If(idx_expr == 3,  1,
         If(idx_expr == 4, -1,
         If(idx_expr == 5,  1,
         If(idx_expr == 6,  1,
                        -1)))))))
    return dr, dc


def build_z3_model(n: int, starts_to_num: Dict[Tuple[int, int], int], fixed_arrows: Dict[Tuple[int, int], str]):
    """
    Fast encoding using one-step transition constraints with Or over concrete cells.
    To keep it fast:
      - only n=5
      - number of starts small (4..7)
      - lengths moderate (2..9)
    """
    s = Solver()
    d = [[Int(f"d_{r}_{c}") for c in range(n)] for r in range(n)]
    for r in range(n):
        for c in range(n):
            s.add(And(d[r][c] >= 0, d[r][c] <= 7))
    for (r, c), a in fixed_arrows.items():
        s.add(d[r][c] == ARROW_TO_IDX[a])

    # Precompute per-cell delta expressions once
    dr_expr = [[None] * n for _ in range(n)]
    dc_expr = [[None] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            dr_expr[r][c], dc_expr[r][c] = z3_dir_delta(d[r][c])

    for (sr, sc), L in starts_to_num.items():
        pr = [Int(f"pr_{sr}_{sc}_{i}") for i in range(L)]
        pc = [Int(f"pc_{sr}_{sc}_{i}") for i in range(L)]
        s.add(pr[0] == sr, pc[0] == sc)

        for i in range(L):
            s.add(And(pr[i] >= 0, pr[i] < n, pc[i] >= 0, pc[i] < n))

        s.add(Distinct([pr[i] * n + pc[i] for i in range(L)]))

        for i in range(L - 1):
            # tie (pr[i],pc[i]) to concrete (r,c)
            alts = []
            for r in range(n):
                for c in range(n):
                    alts.append(
                        And(
                            pr[i] == r,
                            pc[i] == c,
                            pr[i + 1] == pr[i] + dr_expr[r][c],
                            pc[i + 1] == pc[i] + dc_expr[r][c],
                        )
                    )
            s.add(Or(*alts))

        # last step must go out of bounds
        alts_out = []
        i = L - 1
        for r in range(n):
            for c in range(n):
                nr = pr[i] + dr_expr[r][c]
                nc = pc[i] + dc_expr[r][c]
                alts_out.append(
                    And(
                        pr[i] == r,
                        pc[i] == c,
                        Or(nr < 0, nr >= n, nc < 0, nc >= n),
                    )
                )
        s.add(Or(*alts_out))

    return s, d


def solve_unique(n: int, starts_to_num: Dict[Tuple[int, int], int], fixed_arrows: Dict[Tuple[int, int], str], timeout_ms: int = 900) -> Tuple[bool, Optional[List[List[str]]]]:
    s, d = build_z3_model(n, starts_to_num, fixed_arrows)
    s.set("timeout", timeout_ms)
    if s.check() != sat:
        return False, None
    m = s.model()
    sol1 = [[ARROWS[m.eval(d[r][c]).as_long()] for c in range(n)] for r in range(n)]

    # block and check for second solution (with small timeout)
    block = [d[r][c] != m.eval(d[r][c]) for r in range(n) for c in range(n)]
    s.add(Or(*block))
    s.set("timeout", timeout_ms)
    if s.check() == sat:
        return False, None
    return True, sol1


def render_problem(n: int, starts_to_num: Dict[Tuple[int, int], int], fixed_arrows: Dict[Tuple[int, int], str], output_language: str) -> str:
    grid = [["X" for _ in range(n)] for _ in range(n)]
    for (r, c), L in starts_to_num.items():
        grid[r][c] = str(L)
    for (r, c), a in fixed_arrows.items():
        if (r, c) not in starts_to_num:
            grid[r][c] = a

    if output_language != "zh":
        output_language = "zh"

    desc = []
    desc.append(f"你需要完成一个 {n} x {n} 的箭头迷宫。")
    desc.append("网格中：")
    desc.append(" - \"X\" 表示需要你填入一个箭头（↑、↓、←、→、↖、↗、↘、↙）。")
    desc.append(" - 数字表示一个“起点格”。")
    if fixed_arrows:
        desc.append(" - 另有少量格子预先给出箭头，必须保持不变。")
    desc.append("")
    desc.append("规则：")
    desc.append("1) 每个格子最终都恰好包含 1 个箭头。")
    desc.append("2) 从某个起点格出发，按该格箭头指向移动到下一个格，再按新格箭头继续移动，形成一条“箭头串”。")
    desc.append("3) 该起点的数字等于：从起点开始依次经过的格子数量，直到下一步将走出网格为止。")
    desc.append("4) 额外约束：对每个起点，其箭头串在走出网格之前不得重复经过同一个格子（不允许形成回路/自交）。")
    desc.append("")
    desc.append("请填写完整网格，并在答案中给出最终二维数组（数字格保留数字，其余填箭头；预填箭头也需保留）：")
    desc.append(json.dumps(grid, ensure_ascii=False, indent=2))
    return "\n".join(desc)


def render_answer_grid(n: int, arrow_grid: List[List[str]], starts_to_num: Dict[Tuple[int, int], int]) -> List[List[str]]:
    out = [[arrow_grid[r][c] for c in range(n)] for r in range(n)]
    for (r, c), L in starts_to_num.items():
        out[r][c] = str(L)
    return out


def format_explanation(n: int, arrow_grid: List[List[str]], starts_to_num: Dict[Tuple[int, int], int], fixed_arrows: Dict[Tuple[int, int], str]) -> str:
    dirs = [[DIRS[arrow_grid[r][c]] for c in range(n)] for r in range(n)]
    lines = []
    if fixed_arrows:
        ok = all(arrow_grid[r][c] == a for (r, c), a in fixed_arrows.items())
        lines.append(f"预填箭头一致性检查：{'通过' if ok else '失败'}。")
    for (sr, sc), L in sorted(starts_to_num.items()):
        path, outb, rep = ray_trace(n, dirs, (sr, sc))
        lines.append(f"起点({sr+1},{sc+1}) 数字={L}：路径={[(r+1,c+1) for r,c in path]}，长度={len(path)}，出界={outb}，重复={rep}。")
    lines.append("以上逐一核对可验证：每个起点的路径长度等于数字，且出界前无重复经过格子。")
    return "\n".join(lines)


def random_full_arrow_grid(rng: random.Random, n: int) -> List[List[str]]:
    return [[rng.choice(ARROWS) for _ in range(n)] for _ in range(n)]


def pick_positions(rng: random.Random, n: int, k: int) -> List[Tuple[int, int]]:
    allpos = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(allpos)
    return allpos[:k]


def generate_one(rng: random.Random, output_language: str) -> Dict[str, Any]:
    # Keep it fast to avoid timeout
    n = 5
    starts_k = rng.randint(4, 7)
    fixed_k = rng.randint(0, 2)

    for _ in range(500):
        base = random_full_arrow_grid(rng, n)
        base_dirs = [[DIRS[base[r][c]] for c in range(n)] for r in range(n)]

        starts = pick_positions(rng, n, starts_k)
        starts_to_num = compute_numbers(n, base_dirs, starts)

        # reject if any start produces cycle under base (since our public rule forbids repeat before exit)
        if any(L == -1 for L in starts_to_num.values()):
            continue

        # keep lengths moderate for solvability/performance
        if any(L < 2 or L > 9 for L in starts_to_num.values()):
            continue

        non_start = [(r, c) for r in range(n) for c in range(n) if (r, c) not in starts_to_num]
        rng.shuffle(non_start)
        fixed_positions = non_start[:fixed_k]
        fixed_arrows = {(r, c): base[r][c] for (r, c) in fixed_positions}

        ok, solved_grid = solve_unique(n, starts_to_num, fixed_arrows, timeout_ms=900)
        if not ok:
            continue

        # independent simulation cross-check
        solved_dirs = [[DIRS[solved_grid[r][c]] for c in range(n)] for r in range(n)]
        nums2 = compute_numbers(n, solved_dirs, list(starts_to_num.keys()))
        if nums2 != starts_to_num:
            continue
        if any(solved_grid[r][c] != a for (r, c), a in fixed_arrows.items()):
            continue

        problem = render_problem(n, starts_to_num, fixed_arrows, output_language)
        answer_grid = render_answer_grid(n, solved_grid, starts_to_num)
        explanation = format_explanation(n, solved_grid, starts_to_num, fixed_arrows)
        return {"problem": problem, "answer": answer_grid, "explanation": explanation}

    raise RuntimeError("生成失败：在采样上限内未找到满足唯一解与校验的实例。")


def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    output_language = data.get("output_language", "zh")

    rng = random.Random(seed)
    items = []
    seen: Set[str] = set()

    attempts = 0
    while len(items) < count and attempts < count * 120:
        attempts += 1
        try:
            obj = generate_one(rng, output_language)
        except Exception as e:
            print(str(e), file=sys.stderr)
            continue
        if obj["problem"] in seen:
            continue
        seen.add(obj["problem"])
        items.append(obj)

    if len(items) != count:
        raise RuntimeError(f"未能生成足够数量的题目：需要 {count}，实际 {len(items)}。")

    sys.stdout.write(json.dumps(items, ensure_ascii=False))


if __name__ == "__main__":
    main()