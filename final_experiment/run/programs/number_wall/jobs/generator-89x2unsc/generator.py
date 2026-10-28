import sys, json, random
from collections import deque, defaultdict

# ----------------------------
# Nurikabe-style generator/solver
# Cells: numbers are island seeds with required island size.
# Output grid uses:
#   - "A" for wall/sea
#   - "X" for non-number island cell
#   - number for numbered cell
# Constraints:
#   1) Each island has exactly one number; island size equals that number.
#   2) Island cells 4-connected.
#   3) All islands separated by walls (i.e., island cells from different islands are not orthogonally adjacent).
#   4) Walls cannot contain any 2x2 all-wall block.
# (We do NOT require the wall region to be globally connected because seed didn't state it.)
# ----------------------------

def neighbors4(r, c, H, W):
    if r > 0: yield (r-1, c)
    if r+1 < H: yield (r+1, c)
    if c > 0: yield (r, c-1)
    if c+1 < W: yield (r, c+1)

def in_bounds(r, c, H, W):
    return 0 <= r < H and 0 <= c < W

def serialize_problem(H, W, numbers_grid, lang="zh"):
    # numbers_grid: None for empty, else int
    lines = []
    lines.append("放置墙壁（标记为'A'）将网格分割成岛屿。每个岛屿必须恰好包含一个数字，且岛屿中的格子数必须等于该数字。")
    lines.append("")
    # render as simple table
    lines.append(f"网格大小：{H}×{W}（用 X 表示空格，用数字表示已给定的岛屿大小）")
    for r in range(H):
        row = []
        for c in range(W):
            v = numbers_grid[r][c]
            row.append(str(v) if v is not None else "X")
        lines.append(" ".join(row))
    lines.append("")
    lines.append("规则：")
    lines.append("- 每个岛屿必须恰好包含一个数字。")
    lines.append("- 岛屿中的总格子数（包括数字所在格子）必须等于该数字的值。")
    lines.append("- 岛屿内的所有格子必须通过水平或垂直方式相连。")
    lines.append("- 不同岛屿之间不能在水平或垂直方向相邻（必须被墙壁隔开）。")
    lines.append("- 墙壁（'A'）不能形成 2×2 的全墙块。")
    lines.append("")
    lines.append("请输出一个二维列表的解决方案网格；每个位置填入：'A'（墙）、'X'（岛屿非数字格）或数字本身。")
    return "\n".join(lines)

def solution_to_output_grid(H, W, numbers_grid, islands_cells, sea_cells):
    # islands_cells: dict seed_pos -> set of cells
    # sea_cells: set of cells
    out = [[None]*W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if (r,c) in sea_cells:
                out[r][c] = "A"
            else:
                num = numbers_grid[r][c]
                if num is not None:
                    out[r][c] = num
                else:
                    out[r][c] = "X"
    return out

def check_no_2x2_sea(H, W, sea):
    for r in range(H-1):
        for c in range(W-1):
            if (r,c) in sea and (r+1,c) in sea and (r,c+1) in sea and (r+1,c+1) in sea:
                return False
    return True

def check_islands(H, W, numbers_grid, out_grid):
    # Validate constraints against produced grid.
    # out_grid entries are "A","X",or int.
    sea = set()
    island = set()
    seeds = {}
    for r in range(H):
        for c in range(W):
            v = out_grid[r][c]
            if v == "A":
                sea.add((r,c))
            else:
                island.add((r,c))
                if isinstance(v, int):
                    seeds[(r,c)] = v

    # seeds must match given numbers
    for r in range(H):
        for c in range(W):
            given = numbers_grid[r][c]
            v = out_grid[r][c]
            if given is None:
                if isinstance(v, int):
                    return False, "空格出现了额外数字"
            else:
                if v != given:
                    return False, "给定数字被改变"
    # no 2x2 sea
    if not check_no_2x2_sea(H, W, sea):
        return False, "出现 2×2 全墙块"

    # island separation: no adjacent cells belonging to different islands
    # We need to assign each island cell to exactly one seed component (since each island has exactly one number).
    # We'll find connected components of non-sea cells.
    seen = set()
    comps = []
    for cell in island:
        if cell in seen: continue
        q = deque([cell]); seen.add(cell)
        comp = set([cell])
        while q:
            u = q.popleft()
            for v in neighbors4(u[0],u[1],H,W):
                if v in island and v not in seen:
                    seen.add(v); q.append(v); comp.add(v)
        comps.append(comp)

    # each comp must contain exactly one seed, and size equals that seed number
    for comp in comps:
        comp_seeds = [pos for pos in comp if pos in seeds]
        if len(comp_seeds) != 1:
            return False, "某个岛屿连通块数字数量不为1"
        s = comp_seeds[0]
        req = seeds[s]
        if len(comp) != req:
            return False, "某个岛屿大小不等于数字"
    # also ensure different comps are not adjacent directly is already implied by components definition;
    # but could have adjacent across sea? adjacency is only orthogonal; if two non-sea components touch orthogonally they'd be one comp.
    # So OK.
    return True, "OK"

# ----------------------------
# Constructive generator: place islands as non-touching polyominoes with given sizes,
# then fill the rest as sea while enforcing no 2x2 sea by turning some sea cells into size-1 islands if needed is not allowed.
# So instead we generate island layout first and then ensure sea has no 2x2 by adjusting layout (resampling).
# ----------------------------

def random_polyomino(rng, H, W, start, size, blocked, no_touch):
    """
    Build a connected set of 'size' cells including start.
    blocked: cells that cannot be used (already occupied by other islands or reserved sea constraints)
    no_touch: set of cells that cannot be adjacent to this polyomino (to keep islands separated);
             We'll enforce that any chosen cell must not be adjacent to other-island cells.
    Returns set or None.
    """
    poly = {start}
    frontier = [start]
    # maintain candidate expansions
    for _ in range(size-1):
        cand = []
        for cell in list(poly):
            for nb in neighbors4(cell[0], cell[1], H, W):
                if nb in poly: 
                    continue
                if nb in blocked:
                    continue
                # avoid touching other islands: chosen cell must not be adjacent to any forbidden "no_touch" cells
                ok = True
                for nb2 in neighbors4(nb[0], nb[1], H, W):
                    if nb2 in no_touch:
                        ok = False
                        break
                if not ok:
                    continue
                cand.append(nb)
        if not cand:
            return None
        nb = rng.choice(cand)
        poly.add(nb)
    return poly

def compute_forbidden_touch(island_cells):
    # cells that are part of islands; other islands must not be adjacent orthogonally to these
    return set(island_cells)

def build_instance(rng):
    # sample size family
    # Keep moderate sizes so existence is likely.
    H, W = rng.choice([(5,5),(5,6),(6,6),(6,7)])
    N = rng.choice([3,4,4,5])  # number of islands
    # choose island sizes; include variety, avoid too big.
    sizes = []
    for _ in range(N):
        sizes.append(rng.choice([2,3,3,4,4,5,6]))
    # ensure sum not too close to full grid so sea exists
    total = sum(sizes)
    if total > H*W - max(4, (H*W)//5):
        # reduce by resampling small
        sizes = [rng.choice([2,3,4,5]) for _ in range(N)]
        total = sum(sizes)
    # Place islands one by one
    occupied = set()
    islands = {}
    seeds = []
    # try multiple attempts
    for attempt in range(400):
        occupied.clear()
        islands.clear()
        seeds.clear()
        ok = True
        # random order (place larger first helps)
        order = sorted(range(N), key=lambda i: -sizes[i])
        for idx in order:
            size = sizes[idx]
            # choose a seed position not occupied and not adjacent to occupied (to help separation)
            candidates = []
            for r in range(H):
                for c in range(W):
                    cell = (r,c)
                    if cell in occupied: 
                        continue
                    # seed cell itself must not be adjacent to occupied to prevent immediate touching
                    touch = False
                    for nb in neighbors4(r,c,H,W):
                        if nb in occupied:
                            touch = True
                            break
                    if touch:
                        continue
                    candidates.append(cell)
            if not candidates:
                ok = False
                break
            rng.shuffle(candidates)
            placed = None
            seed = None
            # attempt a few candidate seeds
            for cand_seed in candidates[:min(60,len(candidates))]:
                # forbid adjacency to existing islands
                no_touch = compute_forbidden_touch(occupied)
                poly = random_polyomino(rng, H, W, cand_seed, size, occupied, no_touch)
                if poly is None:
                    continue
                # additionally ensure resulting poly doesn't touch existing occupied (already enforced by no_touch check)
                placed = poly
                seed = cand_seed
                break
            if placed is None:
                ok = False
                break
            islands[seed] = placed
            seeds.append(seed)
            occupied |= placed

        if not ok:
            continue

        # Now sea is remaining cells
        sea = {(r,c) for r in range(H) for c in range(W)} - occupied

        # Check sea 2x2 constraint; if violated, resample whole instance
        if not check_no_2x2_sea(H, W, sea):
            continue

        # Also ensure each island has exactly one seed (by construction) and seed is inside
        # Build numbers grid
        numbers_grid = [[None]*W for _ in range(H)]
        for seed in islands:
            numbers_grid[seed[0]][seed[1]] = len(islands[seed])

        # Create output grid
        out_grid = solution_to_output_grid(H, W, numbers_grid, islands, sea)
        valid, _ = check_islands(H, W, numbers_grid, out_grid)
        if not valid:
            continue

        # Uniqueness check: We want the puzzle to have a unique solution.
        # We'll implement a backtracking solver over island assignments with pruning; stop after 2 solutions.
        sol_count = count_solutions(numbers_grid, limit=2)
        if sol_count != 1:
            continue

        return H, W, numbers_grid, out_grid

    raise RuntimeError("生成失败：在采样上限内未找到满足条件且唯一解的实例。")

# ----------------------------
# Solver for uniqueness counting
# Approach:
# - Enumerate for each seed all possible connected shapes (polyominoes) of given size that:
#   * stay in grid
#   * do not include other seeds
# - Then choose one shape per seed such that:
#   * shapes disjoint
#   * shapes not orthogonally adjacent between different seeds (separated by sea)
# - Remaining cells are sea and must have no 2x2 all-sea.
# Count solutions up to limit.
# ----------------------------

def enumerate_shapes_for_seed(H, W, seed, size, all_seeds_set):
    forbidden = set(all_seeds_set) - {seed}

    # BFS over connected sets by adding boundary cells
    shapes = []
    start = frozenset([seed])
    q = [start]
    seen = {start}
    while q:
        shape = q.pop()
        if len(shape) == size:
            shapes.append(set(shape))
            continue
        # candidate expansions: neighbors of current shape
        boundary = set()
        for (r,c) in shape:
            for nb in neighbors4(r,c,H,W):
                if nb in shape: 
                    continue
                boundary.add(nb)
        for nb in boundary:
            if nb in forbidden:
                continue
            # keep within grid already
            newshape = frozenset(set(shape) | {nb})
            if newshape in seen:
                continue
            # connectivity ensured by adding neighbor
            seen.add(newshape)
            q.append(newshape)
    return shapes

def shapes_touch(shape1, shape2, H, W):
    # orthogonal adjacency
    for (r,c) in shape1:
        for nb in neighbors4(r,c,H,W):
            if nb in shape2:
                return True
    return False

def any_2x2_all_sea_from_shapes(H, W, occupied):
    sea = {(r,c) for r in range(H) for c in range(W)} - occupied
    return not check_no_2x2_sea(H, W, sea)

def count_solutions(numbers_grid, limit=2):
    H = len(numbers_grid); W = len(numbers_grid[0])
    seeds = []
    for r in range(H):
        for c in range(W):
            if isinstance(numbers_grid[r][c], int):
                seeds.append((r,c))
    all_seeds = set(seeds)
    req = {s: numbers_grid[s[0]][s[1]] for s in seeds}

    # enumerate shapes
    shapes_by_seed = {}
    for s in seeds:
        shapes = enumerate_shapes_for_seed(H, W, s, req[s], all_seeds)
        # prune shapes that would force touching another seed cell by adjacency (since that other seed must be in other island)
        pruned = []
        for sh in shapes:
            ok = True
            for t in all_seeds - {s}:
                # if shape includes t already eliminated, but adjacency also forbidden
                if shapes_touch(sh, {t}, H, W):
                    ok = False
                    break
            if ok:
                pruned.append(sh)
        shapes_by_seed[s] = pruned
        if not pruned:
            return 0

    # order seeds by fewest shapes
    order = sorted(seeds, key=lambda s: len(shapes_by_seed[s]))
    used = set()
    chosen = {}
    sol = 0

    # precompute for speed: for each seed, each shape's forbidden-touch cells are its cells
    def backtrack(i):
        nonlocal sol, used, chosen
        if sol >= limit:
            return
        if i == len(order):
            # check sea 2x2
            if not any_2x2_all_sea_from_shapes(H, W, used):
                sol += 1
            return
        s = order[i]
        for sh in shapes_by_seed[s]:
            # disjoint
            if any(cell in used for cell in sh):
                continue
            # no touch with already chosen other islands
            bad = False
            for other_seed, other_shape in chosen.items():
                if shapes_touch(sh, other_shape, H, W):
                    bad = True
                    break
            if bad:
                continue
            # accept
            chosen[s] = sh
            added = list(sh)
            for cell in added:
                used.add(cell)
            backtrack(i+1)
            for cell in added:
                used.remove(cell)
            del chosen[s]
            if sol >= limit:
                return

    backtrack(0)
    return sol

# ----------------------------
# Explanation builder
# ----------------------------

def build_explanation(problem_numbers, solution_grid):
    H = len(problem_numbers); W = len(problem_numbers[0])
    # Summarize each island size and verify counts quickly.
    seeds = []
    for r in range(H):
        for c in range(W):
            if isinstance(problem_numbers[r][c], int):
                seeds.append((r,c,problem_numbers[r][c]))
    # Count sea and check 2x2 in explanation.
    sea = {(r,c) for r in range(H) for c in range(W) if solution_grid[r][c] == "A"}
    ok2x2 = check_no_2x2_sea(H,W,sea)
    # component sizes
    island_cells = {(r,c) for r in range(H) for c in range(W) if solution_grid[r][c] != "A"}
    seen=set()
    comps=[]
    for cell in island_cells:
        if cell in seen: continue
        q=deque([cell]); seen.add(cell); comp=set([cell])
        while q:
            u=q.popleft()
            for v in neighbors4(u[0],u[1],H,W):
                if v in island_cells and v not in seen:
                    seen.add(v); q.append(v); comp.add(v)
        comps.append(comp)
    # map comp -> seed
    seed_map={}
    for comp in comps:
        comp_seeds=[]
        for (r,c,_) in seeds:
            if (r,c) in comp:
                comp_seeds.append((r,c))
        seed_map[tuple(sorted(comp))] = comp_seeds

    lines=[]
    lines.append("校验要点（基于给出的解答网格）：")
    lines.append(f"- 墙格 'A' 不存在 2×2 全墙块：{('是' if ok2x2 else '否')}")
    lines.append(f"- 非墙格分成 {len(comps)} 个互不连通的岛屿连通块；每块均为上下左右连通。")
    for comp in sorted(comps, key=lambda s: (len(s), sorted(s)[0])):
        comp_seeds = seed_map[tuple(sorted(comp))]
        lines.append(f"  * 某连通块大小={len(comp)}，其中数字格位置={comp_seeds}")
    lines.append("这些连通块与题面数字一一对应（每块恰含一个数字且块大小等于该数字），并且不同岛屿之间不会正交相邻。")
    return "\n".join(lines)

# ----------------------------
# Main generation loop with dedup
# ----------------------------

def grid_signature(numbers_grid):
    # signature for dedup by problem statement (numbers positions/sizes)
    H = len(numbers_grid); W = len(numbers_grid[0])
    items=[]
    for r in range(H):
        for c in range(W):
            v = numbers_grid[r][c]
            if v is not None:
                items.append((r,c,v))
    return (H,W,tuple(items))

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results=[]
    seen=set()
    attempts=0
    max_attempts = 2000

    while len(results) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"在尝试 {max_attempts} 次后仍未生成足够题目（已生成 {len(results)}/{count}）。")
        try:
            H,W,numbers_grid,sol_grid = build_instance(rng)
        except RuntimeError as e:
            # resample
            continue
        sig = grid_signature(numbers_grid)
        if sig in seen:
            continue
        seen.add(sig)

        problem = serialize_problem(H,W,numbers_grid,lang="zh")
        answer = sol_grid
        explanation = build_explanation(numbers_grid, sol_grid)

        # final safety check
        ok, msg = check_islands(H,W,numbers_grid,answer)
        if not ok:
            print("内部校验失败：" + msg, file=sys.stderr)
            continue

        results.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e), file=sys.stderr)
        raise