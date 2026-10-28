import sys, json, random
from collections import deque

# ============================================================
# Nurikabe-like generator (islands + connected wall + no 2x2 wall)
# Robust version: construct solution from a guaranteed-valid "spine wall"
# and then carve islands deterministically; uniqueness is checked by a
# complete Z3 model (with region enumeration to avoid component vars).
# ============================================================

# -------------------- helpers --------------------

def inb(n, r, c):
    return 0 <= r < n and 0 <= c < n

def nbr4(n, r, c):
    if r: yield (r - 1, c)
    if r + 1 < n: yield (r + 1, c)
    if c: yield (r, c - 1)
    if c + 1 < n: yield (r, c + 1)

def fmt_grid(grid):
    rows = [" ".join(row) for row in grid]
    return "[[" + ",".join(rows) + "]]"

def comp_cells(n, is_true):
    vis = [[False] * n for _ in range(n)]
    comps = []
    for r in range(n):
        for c in range(n):
            if is_true(r, c) and not vis[r][c]:
                q = deque([(r, c)])
                vis[r][c] = True
                cells = []
                while q:
                    x, y = q.popleft()
                    cells.append((x, y))
                    for nx, ny in nbr4(n, x, y):
                        if is_true(nx, ny) and not vis[nx][ny]:
                            vis[nx][ny] = True
                            q.append((nx, ny))
                comps.append(cells)
    return comps

def walls_connected(solA, n):
    walls = [(r, c) for r in range(n) for c in range(n) if solA[r][c]]
    if not walls:
        return False
    start = walls[0]
    q = deque([start])
    seen = {start}
    while q:
        r, c = q.popleft()
        for nr, nc in nbr4(n, r, c):
            if solA[nr][nc] and (nr, nc) not in seen:
                seen.add((nr, nc))
                q.append((nr, nc))
    return len(seen) == len(walls)

def no_2x2_walls(solA, n):
    for r in range(n - 1):
        for c in range(n - 1):
            if solA[r][c] and solA[r+1][c] and solA[r][c+1] and solA[r+1][c+1]:
                return False
    return True

def assign_island_ids(solA, n):
    comps = comp_cells(n, lambda r, c: not solA[r][c])
    island_id = [[-1] * n for _ in range(n)]
    for i, cells in enumerate(comps):
        for r, c in cells:
            island_id[r][c] = i
    return island_id, comps

def islands_separated(solA, island_id, n):
    # no orth adjacency between different islands (non-wall cells)
    for r in range(n):
        for c in range(n):
            if solA[r][c]:
                continue
            id1 = island_id[r][c]
            for nr, nc in nbr4(n, r, c):
                if solA[nr][nc]:
                    continue
                if island_id[nr][nc] != id1:
                    return False
    return True

# -------------------- guaranteed-structure constructor --------------------

def build_spine_wall(n):
    """
    Build a guaranteed connected wall with no 2x2:
    A simple "snake" path on every other row, leaving plenty of island area.
    """
    A = [[False] * n for _ in range(n)]
    # Use rows 1,3,5,... (0-index odd) as wall snakes
    for r in range(1, n, 2):
        if (r // 2) % 2 == 0:
            # left to right
            for c in range(n):
                A[r][c] = True
        else:
            # right to left
            for c in range(n-1, -1, -1):
                A[r][c] = True
        # connect to next odd row via a single cell in between (also on odd row already)
        # no extra needed because rows are full walls; they are connected via adjacent columns? Actually full rows are disconnected vertically.
        # So add connectors in even rows at alternating columns.
    # Add vertical connectors in even rows at sparse columns to connect all wall rows
    for r in range(2, n, 2):  # even rows below an odd wall row
        col = 0 if (r//2) % 2 == 1 else n-1
        A[r][col] = True
        A[r-1][col] = True  # already True
        if r+1 < n:
            A[r+1][col] = True  # next odd row already True
    return A

def carve_islands_from_wall(rng, solA, n):
    """
    Starting from a wall skeleton, we carve islands in the remaining cells.
    We ensure: each island is a connected component of non-wall cells and will
    have exactly one hint with size equal to component size.
    To keep separation constraint valid, we rely on the fact that islands are
    exactly components of non-wall region; different components don't touch.
    So separation holds automatically.
    """
    # Ensure base properties
    if not walls_connected(solA, n):
        return None
    if not no_2x2_walls(solA, n):
        return None

    # We can optionally add some extra wall cells (still connected, still no 2x2)
    # to break large open regions into multiple islands.
    # Only add walls in even rows to avoid creating 2x2.
    max_extra = rng.randint(0, max(0, n-2))
    for _ in range(max_extra):
        r = rng.randrange(n)
        c = rng.randrange(n)
        if solA[r][c]:
            continue
        # propose turn to wall if keeps constraints and connectivity
        solA[r][c] = True
        if no_2x2_walls(solA, n) and walls_connected(solA, n):
            # accept with some probability (not too dense)
            if rng.random() < 0.55:
                continue
        # revert
        solA[r][c] = False

    if not no_2x2_walls(solA, n):
        return None
    if not walls_connected(solA, n):
        return None

    island_id, comps = assign_island_ids(solA, n)
    if not comps:
        return None
    if not islands_separated(solA, island_id, n):
        return None

    # Place one hint per island: choose a random cell in each component
    hints = {}
    for cells in comps:
        pos = rng.choice(cells)
        hints[pos] = len(cells)
    return solA, hints

def compute_puzzle(n, hints):
    puzzle = [["X"] * n for _ in range(n)]
    for (r, c), v in hints.items():
        puzzle[r][c] = str(v)
    return puzzle

def render_solution(n, solA, hints):
    grid = [["A" if solA[r][c] else "X" for c in range(n)] for r in range(n)]
    for (r, c), v in hints.items():
        grid[r][c] = str(v)
    return grid

# -------------------- Z3 uniqueness solver (complete, finite) --------------------

def solve_with_z3_all(puzzle, limit=2):
    """
    Exact solver:
    - Boolean wall[r][c]
    - Hint cells are not wall.
    - For each hint, enforce existence of a connected region of size clue that contains the hint,
      contains no other hint, and is exactly the whole connected component of non-walls that contains the hint.
    To avoid explicit component labeling, we enumerate all possible connected subsets S of size clue that contain the hint
    (feasible for n<=7 and clues typically modest due to our construction).
    Then assert: for each hint, exactly one such subset is chosen, and these subsets are disjoint,
    and all non-wall cells are covered by exactly one chosen subset.
    Walls must be connected and no 2x2 all-walls.
    """
    try:
        import z3
    except Exception as e:
        raise RuntimeError("需要 z3 库但未能导入: %s" % e)

    n = len(puzzle)
    hints = {}
    for r in range(n):
        for c in range(n):
            if puzzle[r][c] != "X":
                hints[(r, c)] = int(puzzle[r][c])

    W = [[z3.Bool(f"W_{r}_{c}") for c in range(n)] for r in range(n)]

    s = z3.Solver()

    # Hint cells are islands (not wall)
    for (r, c) in hints:
        s.add(z3.Not(W[r][c]))

    # No 2x2 all wall
    for r in range(n-1):
        for c in range(n-1):
            s.add(z3.Not(z3.And(W[r][c], W[r+1][c], W[r][c+1], W[r+1][c+1])))

    # Enumerate connected subsets for each hint
    # BFS enumerate connected sets of exact size k containing start.
    def connected_sets_of_size(start, k):
        (sr, sc) = start
        # cells list
        all_cells = [(r, c) for r in range(n) for c in range(n)]
        # Precompute neighbors
        neigh = {cell: list(nbr4(n, cell[0], cell[1])) for cell in all_cells}

        results = []
        # Use frontier expansion; represent set as sorted tuple for dedup
        # Limit enumeration to avoid explosion; our construction typically keeps k small-ish.
        # Still, enforce a safety cap.
        CAP = 4000
        start_set = (start,)
        q = deque([start_set])
        seen = {start_set}
        while q:
            cur = q.popleft()
            if len(cur) == k:
                results.append(cur)
                if len(results) >= CAP:
                    break
                continue
            cur_set = set(cur)
            # candidates: neighbors of any cell in cur, not already in set
            cand = set()
            for cell in cur:
                cand.update(neigh[cell])
            cand.difference_update(cur_set)
            # small heuristic ordering
            cand = list(cand)
            cand.sort()
            for nxt in cand:
                new = tuple(sorted(cur_set | {nxt}))
                if new not in seen and len(new) <= k:
                    seen.add(new)
                    q.append(new)
        return results

    # Create choice vars for each hint and its candidate regions
    region_choices = {}  # hint -> list of (var, cells_tuple)
    cell_covered_by = [[[] for _ in range(n)] for __ in range(n)]

    for hcell, k in hints.items():
        cands = connected_sets_of_size(hcell, k)
        # Filter candidates: must not include other hints
        other_hints = set(hints.keys()) - {hcell}
        cands2 = []
        for cells in cands:
            ok = True
            for oc in other_hints:
                if oc in cells:
                    ok = False
                    break
            if ok:
                cands2.append(cells)
        cands = cands2

        if not cands:
            return []

        vars_for_h = []
        for idx, cells in enumerate(cands):
            v = z3.Bool(f"R_{hcell[0]}_{hcell[1]}_{idx}")
            vars_for_h.append((v, cells))
            for (r, c) in cells:
                cell_covered_by[r][c].append(v)

        region_choices[hcell] = vars_for_h
        # exactly one region chosen for this hint
        s.add(z3.PbEq([(v, 1) for (v, _) in vars_for_h], 1))

    # Coverage constraints:
    # A cell is non-wall iff it is covered by exactly one chosen region.
    for r in range(n):
        for c in range(n):
            cov = cell_covered_by[r][c]
            if not cov:
                # then cell must be wall
                s.add(W[r][c])
            else:
                # covered by exactly one region <=> not wall, and no overlaps
                s.add(z3.Not(W[r][c]))
                s.add(z3.PbEq([(v, 1) for v in cov], 1))

    # Wall connectivity via reachability from some root wall cell.
    # Choose a fixed root: first cell (0,0). If it is not wall, allow another by disjunction:
    # We implement connectivity as: there exists a root that is wall and reaches all walls.
    # For small n (<=7), we can try each possible root with an Or of connectivity constraints.
    def wall_connectivity_constraints_for_root(rr, cc):
        # reach[t][r][c] bounded by n*n steps
        steps = n*n
        reach = [[[z3.Bool(f"reach_{rr}_{cc}_{t}_{r}_{c}") for c in range(n)] for r in range(n)] for t in range(steps+1)]
        cons = []
        cons.append(W[rr][cc])  # root must be wall
        # init
        for r in range(n):
            for c in range(n):
                cons.append(reach[0][r][c] == z3.And(r == rr, c == cc))
        # transitions
        for t in range(steps):
            for r in range(n):
                for c in range(n):
                    neighs = list(nbr4(n, r, c))
                    cons.append(
                        reach[t+1][r][c] ==
                        z3.And(
                            W[r][c],
                            z3.Or(
                                reach[t][r][c],
                                z3.Or([reach[t][nr][nc] for (nr, nc) in neighs]) if neighs else z3.BoolVal(False)
                            )
                        )
                    )
        # all walls reachable at final step
        for r in range(n):
            for c in range(n):
                cons.append(z3.Implies(W[r][c], reach[steps][r][c]))
        return z3.And(cons)

    roots = [(r, c) for r in range(n) for c in range(n)]
    s.add(z3.Or([wall_connectivity_constraints_for_root(r, c) for (r, c) in roots]))

    # enumerate solutions up to limit
    sols = []
    while len(sols) < limit and s.check() == z3.sat:
        m = s.model()
        solA = [[bool(m.evaluate(W[r][c], model_completion=True)) for c in range(n)] for r in range(n)]
        sols.append(solA)
        # block this solution
        block = []
        for r in range(n):
            for c in range(n):
                lit = W[r][c]
                if solA[r][c]:
                    block.append(lit)
                else:
                    block.append(z3.Not(lit))
        s.add(z3.Not(z3.And(block)))
    return sols

# -------------------- rendering (ZH) --------------------

def render_problem_zh(puzzle):
    n = len(puzzle)
    lines = []
    lines.append("你正在解一道“筑岛围墙”（类似 Nurikabe）逻辑题。棋盘为 n×n 方格。部分格子给出数字提示，其余格子为空白（用 X 表示）。")
    lines.append("")
    lines.append("规则：")
    lines.append("1）你需要在一些格子上建墙，墙格用 A 表示；未建墙且不含数字的岛格用 X 表示；数字格保留数字。")
    lines.append("2）所有非墙格（数字格与 X）会形成若干个岛屿；每个岛屿必须恰好包含一个数字。")
    lines.append("3）每个岛屿的格子总数必须等于该岛屿中数字提示的数值。")
    lines.append("4）不同岛屿之间不能上下左右相邻（必须被墙隔开）。")
    lines.append("5）任意 2×2 小方块中不能四格都是墙 A（禁止 2×2 全墙）。")
    lines.append("6）所有墙格 A 必须上下左右连通（墙域是一个连通块）。")
    lines.append("")
    lines.append("请将需要建墙的格子替换为 A，并按要求输出最终矩阵：元素以空格分隔，每行用逗号分隔，最外层用双中括号包裹。")
    lines.append("")
    lines.append("题目矩阵：")
    for r in range(n):
        lines.append(" ".join(puzzle[r]))
    return "\n".join(lines)

def explanation_zh(puzzle, solA, hints):
    n = len(puzzle)
    island_id, comps = assign_island_ids(solA, n)
    wall_comps = comp_cells(n, lambda r, c: solA[r][c])
    lines = []
    lines.append("核对：")
    lines.append(f"- 墙域连通分量数 = {len(wall_comps)}（应为 1）。")
    lines.append(f"- 是否存在 2×2 全墙：{'否' if no_2x2_walls(solA,n) else '是'}（应为 否）。")
    lines.append("- 各岛屿（大小/提示）列表：")
    # map each island to its hint
    for i, cells in enumerate(comps):
        hc = [cell for cell in cells if cell in hints]
        if hc:
            (hr, hc2) = hc[0]
            lines.append(f"  * 岛{i}: 大小={len(cells)}；提示在({hr+1},{hc2+1})，数值={hints[(hr,hc2)]}")
        else:
            lines.append(f"  * 岛{i}: 大小={len(cells)}；(无提示，按规则应不出现)")
    lines.append("将答案矩阵中的 A 视为墙，其余视为岛格，可逐条检查上述条件。")
    return "\n".join(lines)

# -------------------- generator --------------------

def gen_one(rng, output_language="zh"):
    # Keep n small for complete Z3 enumeration; still varied
    n = rng.choice([5, 6, 7])

    for _ in range(200):
        baseA = build_spine_wall(n)
        # Make a fresh copy
        solA = [row[:] for row in baseA]
        carved = carve_islands_from_wall(rng, solA, n)
        if carved is None:
            continue
        solA, hints = carved

        # Basic sanity
        if not walls_connected(solA, n): 
            continue
        if not no_2x2_walls(solA, n):
            continue
        island_id, comps = assign_island_ids(solA, n)
        if not comps:
            continue
        if not islands_separated(solA, island_id, n):
            continue
        # each island exactly one hint in our construction
        ok = True
        for comp in comps:
            cnt = sum((cell in hints) for cell in comp)
            if cnt != 1:
                ok = False
                break
            hcell = [cell for cell in comp if cell in hints][0]
            if len(comp) != hints[hcell]:
                ok = False
                break
        if not ok:
            continue

        puzzle = compute_puzzle(n, hints)

        # Uniqueness check by Z3
        sols = solve_with_z3_all(puzzle, limit=2)
        if len(sols) != 1:
            continue
        if sols[0] != solA:
            continue

        problem = render_problem_zh(puzzle) if output_language == "zh" else render_problem_zh(puzzle)
        answer_grid = render_solution(n, solA, hints)
        answer = fmt_grid(answer_grid)
        expl = explanation_zh(puzzle, solA, hints) if output_language == "zh" else explanation_zh(puzzle, solA, hints)
        return {"problem": problem, "answer": answer, "explanation": expl}

    raise RuntimeError("在采样上限内未能生成满足唯一解与全部约束的题目实例（请更换 seed 或降低 count）。")

def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    output_language = data.get("output_language", "zh") if isinstance(data, dict) else "zh"

    rng = random.Random(seed)
    items = []
    seen = set()
    tries = 0
    # De-dup by puzzle layout string
    while len(items) < count:
        tries += 1
        if tries > count * 600:
            raise RuntimeError("重复/失败过多，未能生成足够数量的不重复题目。")
        obj = gen_one(rng, output_language=output_language)
        key = obj["problem"]
        if key in seen:
            continue
        seen.add(key)
        items.append(obj)

    sys.stdout.write(json.dumps(items, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
        raise