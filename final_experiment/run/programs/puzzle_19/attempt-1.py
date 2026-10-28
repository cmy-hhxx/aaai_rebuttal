import sys, json, random
from collections import defaultdict, Counter, deque

# Star Battle puzzle generator/solver
# stdin: {"seed": int, "count": int}
# stdout: JSON array length == count with {"problem":str,"answer":JSON,"explanation":str}
#
# Fixes for previous version:
# - Add strict time/attempt budgeting per puzzle (avoid long searches -> exit -24).
# - Prefer easy-to-solve families: k=1 with connected equal-size regions; occasional k=2 only when N small and solver finds quickly.
# - Use Z3 for solving + uniqueness check (faster and more reliable than pure backtracking here).
# - Keep N in [6..9] mostly to limit complexity and stay within A..I labels.

try:
    import z3
except Exception as e:
    z3 = None


def neighbors8(r, c, N):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < N and 0 <= cc < N:
                yield rr, cc


def neighbors4(r, c, N):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < N and 0 <= cc < N:
            yield rr, cc


def is_connected(cells, N):
    if not cells:
        return False
    start = next(iter(cells))
    q = deque([start])
    vis = {start}
    while q:
        r, c = q.popleft()
        for rr, cc in neighbors4(r, c, N):
            if (rr, cc) in cells and (rr, cc) not in vis:
                vis.add((rr, cc))
                q.append((rr, cc))
    return len(vis) == len(cells)


def region_letters(N):
    # N <= 10 in this generator; keep A..J safe
    return [chr(ord("A") + i) for i in range(N)]


def fmt_grid(grid):
    return "\n".join(" ".join(row) for row in grid)


def coord1(r, c):
    return (r + 1, c + 1)


def sort_coords(coords):
    return sorted(coords, key=lambda x: (x[0], x[1]))


def render_answer_by_region(grid, stars_set):
    N = len(grid)
    reg_to_coords = defaultdict(list)
    for (r, c) in stars_set:
        reg_to_coords[grid[r][c]].append(coord1(r, c))
    for k in list(reg_to_coords.keys()):
        reg_to_coords[k] = sort_coords(reg_to_coords[k])
    labels = sorted(reg_to_coords.keys())
    lines = []
    for lab in labels:
        coords = reg_to_coords[lab]
        lines.append(lab + "".join(f"({r},{c})" for (r, c) in coords))
    return "[[" + "\n".join(lines) + "]]"


def build_problem_text(grid, nstars, lang="zh"):
    N = len(grid)
    intro = (
        "星战（Star Battle）规则：\n"
        "1）在一个 N×N 的网格中，网格被划分为若干区域（用字母标记）。\n"
        f"2）每一行恰好放置 {nstars} 颗星；每一列恰好放置 {nstars} 颗星；每个区域也恰好放置 {nstars} 颗星。\n"
        "3）任意两颗星不能相邻（包括上下左右与对角线相邻）。\n"
        "问题：给出区域字母矩阵，输出每个区域中星的坐标（行、列从 1 开始）。\n"
        "输出要求：按区域字母升序；同一区域若有多颗星，按(行,列)字典序升序列出。\n"
        "输出格式：用双层方括号包裹，各区域之间用换行分隔，例如：\n"
        "[[A(1,1)(2,5)\nB(1,3)\nC(3,7)]]\n\n"
        f"本题：N={N}，每行/列/区域 {nstars} 颗星。\n\n"
        "区域矩阵：\n"
    )
    return intro + fmt_grid(grid)


def random_connected_equal_regions(N, rnd, attempts=200):
    # Grow N connected regions each target size N, labels A.. based on seed order.
    letters = region_letters(N)
    target = N
    allcells = [(r, c) for r in range(N) for c in range(N)]
    for _ in range(attempts):
        grid = [[None] * N for _ in range(N)]
        rnd.shuffle(allcells)
        seeds = allcells[:N]
        fronts = [deque([seeds[i]]) for i in range(N)]
        sizes = [0] * N
        for i, (r, c) in enumerate(seeds):
            grid[r][c] = letters[i]
            sizes[i] = 1
        unassigned = set(allcells[N:])
        stalled = 0
        # Mild bias to avoid weird shapes: prefer adding to smaller regions
        while unassigned and stalled < 6 * N * N:
            progressed = False
            order = list(range(N))
            order.sort(key=lambda i: (sizes[i], rnd.random()))
            for i in order:
                if sizes[i] >= target:
                    continue
                # boundary candidates
                cand = []
                for (r, c) in list(fronts[i]):
                    for rr, cc in neighbors4(r, c, N):
                        if (rr, cc) in unassigned:
                            cand.append((rr, cc))
                if not cand:
                    continue
                rc = rnd.choice(cand)
                r, c = rc
                grid[r][c] = letters[i]
                sizes[i] += 1
                unassigned.remove(rc)
                fronts[i].append(rc)
                progressed = True
            stalled = 0 if progressed else stalled + 1

        if unassigned:
            continue

        # validate
        ok = True
        for lab in letters:
            cells = {(r, c) for r in range(N) for c in range(N) if grid[r][c] == lab}
            if len(cells) != target or not is_connected(cells, N):
                ok = False
                break
        if ok:
            return grid
    return None


def solve_unique_with_z3(grid, k, time_ms=150):
    if z3 is None:
        return None, "z3_not_available"

    N = len(grid)
    letters = sorted(set(ch for row in grid for ch in row))
    regions = defaultdict(list)
    for r in range(N):
        for c in range(N):
            regions[grid[r][c]].append((r, c))

    X = [[z3.Bool(f"x_{r}_{c}") for c in range(N)] for r in range(N)]
    s = z3.Solver()
    s.set("timeout", time_ms)

    # row/col
    for r in range(N):
        s.add(z3.PbEq([(X[r][c], 1) for c in range(N)], k))
    for c in range(N):
        s.add(z3.PbEq([(X[r][c], 1) for r in range(N)], k))

    # region
    for lab in letters:
        cells = regions[lab]
        s.add(z3.PbEq([(X[r][c], 1) for (r, c) in cells], k))

    # adjacency (8-neighbor)
    for r in range(N):
        for c in range(N):
            for rr, cc in neighbors8(r, c, N):
                # enforce not both true; to avoid duplicates only add one direction
                if (rr, cc) > (r, c):
                    s.add(z3.Not(z3.And(X[r][c], X[rr][cc])))

    # Solve first
    if s.check() != z3.sat:
        return None, "unsat_or_timeout"

    m = s.model()
    stars = {(r, c) for r in range(N) for c in range(N) if z3.is_true(m.evaluate(X[r][c], model_completion=True))}

    # Uniqueness: block this exact solution and ask sat again
    block = []
    for r in range(N):
        for c in range(N):
            val = (r, c) in stars
            block.append(X[r][c] if not val else z3.Not(X[r][c]))
    s2 = z3.Solver()
    s2.set("timeout", time_ms)
    s2.append(s.assertions())
    s2.add(z3.Or(block))
    chk = s2.check()
    if chk == z3.sat:
        return None, "multiple_solutions"
    if chk == z3.unknown:
        return None, "uniq_timeout"
    return stars, "unique"


def direct_verify(grid, stars, k):
    N = len(grid)
    # adjacency
    for (r, c) in stars:
        for rr, cc in neighbors8(r, c, N):
            if (rr, cc) in stars:
                return False
    # row/col counts
    for r in range(N):
        if sum((r, c) in stars for c in range(N)) != k:
            return False
    for c in range(N):
        if sum((r, c) in stars for r in range(N)) != k:
            return False
    # regions
    reg = defaultdict(int)
    for (r, c) in stars:
        reg[grid[r][c]] += 1
    for lab in region_letters(N):
        if reg[lab] != k:
            return False
    return True


def make_explanation(grid, stars, k):
    N = len(grid)
    row_list = []
    for r in range(N):
        cols = [c + 1 for c in range(N) if (r, c) in stars]
        row_list.append(f"第{r+1}行星所在列：{cols}（共{k}颗）")
    col_list = []
    for c in range(N):
        rows = [r + 1 for r in range(N) if (r, c) in stars]
        col_list.append(f"第{c+1}列星所在行：{rows}（共{k}颗）")
    return (
        "复核摘要：\n"
        f"- 每行/每列/每区域均恰好 {k} 颗星；\n"
        "- 任意两星（含对角）不相邻。\n"
        "按行、按列列出星位置便于逐条检查：\n"
        + "\n".join(row_list) + "\n"
        + "\n".join(col_list)
    )


def generate_one(rnd):
    # Budgeted retries to avoid long runtime
    # Primary: k=1 (fast, high success). Occasionally attempt k=2 with small N.
    for _ in range(60):
        if rnd.random() < 0.18:
            N = rnd.choice([6, 7])
            k = 2
            z3_timeout = 220
        else:
            N = rnd.choice([6, 7, 8, 9])
            k = 1
            z3_timeout = 140

        grid = random_connected_equal_regions(N, rnd, attempts=80)
        if grid is None:
            continue

        stars, status = solve_unique_with_z3(grid, k, time_ms=z3_timeout)
        if stars is None:
            continue
        if not direct_verify(grid, stars, k):
            continue

        problem = build_problem_text(grid, k, lang="zh")
        answer = render_answer_by_region(grid, stars)
        explanation = make_explanation(grid, stars, k)
        return problem, answer, explanation

    return None


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rnd = random.Random(seed)

    out = []
    seen = set()
    total_attempts = 0
    max_total_attempts = 5000

    while len(out) < count and total_attempts < max_total_attempts:
        total_attempts += 1
        got = generate_one(rnd)
        if got is None:
            continue
        problem, answer, explanation = got
        # Dedup by region matrix only (strip the header to avoid trivial differences)
        key = problem.split("区域矩阵：\n", 1)[-1]
        if key in seen:
            continue
        seen.add(key)
        out.append({"problem": problem, "answer": answer, "explanation": explanation})

    if len(out) != count:
        print(f"生成失败：仅生成 {len(out)}/{count} 题（尝试 {total_attempts} 次）。可更换 seed 或减少 count。", file=sys.stderr)
        raise SystemExit(2)

    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()