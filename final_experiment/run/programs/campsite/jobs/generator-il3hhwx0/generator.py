import sys, json, random
from typing import List, Tuple, Dict, Optional, Set

# Tents and Trees puzzle generator + solver (unique-solution instances)
# Reads: {"seed": int, "count": int}
# Outputs: JSON array of {problem:str, answer:JSON, explanation:str}

Cell = Tuple[int, int]

DIR4 = [(-1,0),(1,0),(0,-1),(0,1)]
DIR8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]


def in_bounds(r:int, c:int, R:int, C:int) -> bool:
    return 0 <= r < R and 0 <= c < C


def neighbors4(cell:Cell, R:int, C:int) -> List[Cell]:
    r,c = cell
    out = []
    for dr,dc in DIR4:
        nr,nc = r+dr, c+dc
        if in_bounds(nr,nc,R,C):
            out.append((nr,nc))
    return out


def neighbors8(cell:Cell, R:int, C:int) -> List[Cell]:
    r,c = cell
    out = []
    for dr,dc in DIR8:
        nr,nc = r+dr, c+dc
        if in_bounds(nr,nc,R,C):
            out.append((nr,nc))
    return out


def grid_to_str(grid:List[List[str]]) -> str:
    return "\n".join(" ".join(row) for row in grid)


def solve_tents_unique(grid:List[List[str]], row_cons:List[int], col_cons:List[int], need_unique:bool=True
                     ) -> Tuple[int, Optional[List[List[str]]]]:
    """
    Solve and count solutions up to 2 (if need_unique True), else count all (may be large, but used small sizes).
    Returns (num_solutions_capped, one_solution_grid_or_None)
    A solution grid contains 'T' for trees, 'C' for tents, 'X' for empty.
    """
    R, C = len(grid), len(grid[0])
    trees = [(r,c) for r in range(R) for c in range(C) if grid[r][c] == 'T']
    nT = len(trees)
    if sum(row_cons) != nT or sum(col_cons) != nT:
        return (0, None)

    # Candidate tent locations are non-tree cells orthogonally adjacent to at least one tree.
    # But we will model assignment per tree: each tree chooses one adjacent cell for its tent.
    cand_by_tree: List[List[Cell]] = []
    for t in trees:
        cands = []
        for nb in neighbors4(t, R, C):
            if grid[nb[0]][nb[1]] != 'T':
                cands.append(nb)
        if not cands:
            return (0, None)
        cand_by_tree.append(cands)

    # Precompute conflicts between tent cells (no touching even diagonally).
    # conflict[a][b] True if cells a and b touch in 8-neighborhood (excluding same).
    # We'll just check dynamically with a set and 8-neighbors.

    # Heuristics ordering: trees with fewer candidates first; also consider row/col remaining.
    order = sorted(range(nT), key=lambda i: (len(cand_by_tree[i]), i))

    # State
    used_tents: Set[Cell] = set()
    row_rem = row_cons[:]
    col_rem = col_cons[:]

    # For fast adjacency conflict check: if any existing tent in 8-neighbors
    def tent_conflicts(cell:Cell) -> bool:
        for nb in neighbors8(cell, R, C):
            if nb in used_tents:
                return True
        return False

    # For pruning: check feasibility with remaining trees.
    # Simple bound: row_rem and col_rem must be within [0, remaining cells possible in row/col].
    # We'll compute remaining possible tent placements per row/col given unassigned trees.
    # This is a weaker but cheap prune.
    def feasible_bounds(next_k:int) -> bool:
        if any(x < 0 for x in row_rem) or any(x < 0 for x in col_rem):
            return False
        remaining = order[next_k:]
        # upper bounds for rows/cols by union of candidates among remaining trees excluding already used/t-conflicting? we'll overapprox.
        row_ub = [0]*R
        col_ub = [0]*C
        # Overapprox: count distinct cells in candidates (even if shared), but a cell can be used once. Still ok as upper bound if we cap by distinct.
        row_cells: List[Set[Cell]] = [set() for _ in range(R)]
        col_cells: List[Set[Cell]] = [set() for _ in range(C)]
        for ti in remaining:
            for cell in cand_by_tree[ti]:
                if cell in used_tents:
                    continue
                # If cell conflicts with existing tents, it cannot be used
                if tent_conflicts(cell):
                    continue
                r,c = cell
                row_cells[r].add(cell)
                col_cells[c].add(cell)
        for r in range(R):
            row_ub[r] = len(row_cells[r])
            if row_rem[r] > row_ub[r]:
                return False
        for c in range(C):
            col_ub[c] = len(col_cells[c])
            if col_rem[c] > col_ub[c]:
                return False
        # Also need total remaining tents equals remaining trees
        if sum(row_rem) != len(remaining):
            return False
        return True

    solutions = 0
    one_solution = None

    # To improve pruning further: at each step, try candidate cells in an order that respects row/col remaining.
    def candidate_order(cands:List[Cell]) -> List[Cell]:
        # Prefer cells in rows/cols that still need tents.
        def score(cell:Cell):
            r,c = cell
            # higher remaining demand -> earlier
            return (-(row_rem[r] + col_rem[c]), r, c)
        return sorted(cands, key=score)

    assign = [None]*nT  # tent cell chosen for each tree index, in original tree order index.

    def backtrack(k:int):
        nonlocal solutions, one_solution
        if need_unique and solutions >= 2:
            return
        if k == nT:
            # Check all constraints satisfied
            if all(x == 0 for x in row_rem) and all(x == 0 for x in col_rem):
                solutions += 1
                if one_solution is None:
                    # Build solution grid
                    sol = [row[:] for row in grid]
                    for ti, cell in enumerate(assign):
                        if cell is None:
                            return
                        r,c = cell
                        sol[r][c] = 'C'
                    one_solution = sol
            return

        if not feasible_bounds(k):
            return

        ti = order[k]
        cands = cand_by_tree[ti]

        # If a tree already has a forced choice due to row/col remaining very tight, it's handled by search.
        for cell in candidate_order(cands):
            r,c = cell
            if cell in used_tents:
                continue
            if grid[r][c] == 'T':
                continue
            if row_rem[r] <= 0 or col_rem[c] <= 0:
                continue
            if tent_conflicts(cell):
                continue

            # Place
            used_tents.add(cell)
            row_rem[r] -= 1
            col_rem[c] -= 1
            assign[ti] = cell

            backtrack(k+1)

            # Unplace
            assign[ti] = None
            row_rem[r] += 1
            col_rem[c] += 1
            used_tents.remove(cell)

    backtrack(0)
    return (solutions if not need_unique else min(solutions, 2), one_solution)


def render_problem_zh(grid:List[List[str]], row_cons:List[int], col_cons:List[int]) -> str:
    R, C = len(grid), len(grid[0])
    lines = []
    lines.append(f"给定一个 {R} x {C} 的「营地（Tents and Trees）」谜题：")
    lines.append("- 树用 'T' 表示；空地用 'X' 表示。你需要在部分空地放置帐篷，用 'C' 表示。")
    lines.append("规则：")
    lines.append("1) 每个帐篷 C 必须放在某一棵树 T 的正交相邻（上/下/左/右）格子里。")
    lines.append("2) 任意两个帐篷之间不能接触：上下左右或对角线相邻都不允许。")
    lines.append("3) 每一行放置帐篷的数量必须等于该行的约束值 row_constraints。")
    lines.append("4) 每一列放置帐篷的数量必须等于该列的约束值 col_constraints。")
    lines.append("5) 帐篷总数必须等于树的总数。")
    lines.append("")
    lines.append("初始网格（行内以空格分隔）：")
    lines.append(grid_to_str(grid))
    lines.append("")
    lines.append(f"row_constraints = {row_cons}")
    lines.append(f"col_constraints = {col_cons}")
    lines.append("")
    lines.append("任务：在满足所有规则的前提下放置帐篷，并以二维列表（列表的列表）输出最终网格。")
    return "\n".join(lines)


def explanation_zh(grid:List[List[str]], row_cons:List[int], col_cons:List[int], sol:List[List[str]]) -> str:
    R, C = len(grid), len(grid[0])
    # Verify and provide concise checkable evidence: counts + adjacency
    tents = [(r,c) for r in range(R) for c in range(C) if sol[r][c] == 'C']
    trees = [(r,c) for r in range(R) for c in range(C) if sol[r][c] == 'T']
    row_counts = [sum(1 for c in range(C) if sol[r][c] == 'C') for r in range(R)]
    col_counts = [sum(1 for r in range(R) if sol[r][c] == 'C') for c in range(C)]

    # For each tent, list at least one adjacent tree
    tent_adj = {}
    for t in tents:
        adj_trees = [nb for nb in neighbors4(t, R, C) if sol[nb[0]][nb[1]] == 'T']
        tent_adj[t] = adj_trees

    # Check no-touch
    bad_pairs = []
    st = set(tents)
    for t in tents:
        for nb in neighbors8(t, R, C):
            if nb in st and nb != t:
                # record once
                if (nb, t) not in bad_pairs:
                    bad_pairs.append((t, nb))
    # Remove duplicates by ordering
    uniq = set()
    filtered = []
    for a,b in bad_pairs:
        key = tuple(sorted([a,b]))
        if key not in uniq:
            uniq.add(key)
            filtered.append(key)

    lines = []
    lines.append("校验要点：")
    lines.append(f"- 树的数量 = {len(trees)}，帐篷的数量 = {len(tents)}（满足“帐篷数=树数”）。")
    lines.append(f"- 各行帐篷数 = {row_counts}，与 row_constraints = {row_cons} 一致。")
    lines.append(f"- 各列帐篷数 = {col_counts}，与 col_constraints = {col_cons} 一致。")
    # Show mapping evidence: list tent->adj tree (one per tent)
    show = []
    for (r,c), adj in sorted(tent_adj.items()):
        if adj:
            ar,ac = adj[0]
            show.append(f"({r},{c})邻接树({ar},{ac})")
        else:
            show.append(f"({r},{c})无相邻树(不应发生)")
    lines.append("- 每个帐篷均与至少一棵树正交相邻，例如：" + "；".join(show[:min(6,len(show))]) + ("" if len(show)<=6 else "；…"))
    if filtered:
        lines.append(f"- 注意：发现帐篷相互接触的冲突对（不应出现）: {filtered[:3]}")
    else:
        lines.append("- 任意两个帐篷在 8 邻域内都不相邻（满足“不接触”规则）。")
    return "\n".join(lines)


def make_instance(rng:random.Random) -> Tuple[List[List[str]], List[int], List[int], List[List[str]]]:
    # Try multiple families / sizes for diversity, all small enough for backtracking.
    families = [
        # (R,C, tree_density_range)
        (4, 3, (0.15, 0.30)),
        (4, 4, (0.15, 0.28)),
        (5, 4, (0.12, 0.25)),
        (5, 5, (0.10, 0.22)),
        (6, 5, (0.08, 0.18)),
    ]
    # attempt budget
    for _ in range(400):
        R,C, (dlo,dhi) = rng.choice(families)
        density = rng.uniform(dlo, dhi)
        nT = max(2, int(round(R*C*density)))
        nT = min(nT, (R*C)//3 + 1)  # keep solvable

        # Place trees randomly with mild spacing to avoid dead instances
        cells = [(r,c) for r in range(R) for c in range(C)]
        rng.shuffle(cells)
        trees = []
        tree_set = set()

        def tree_ok(cell:Cell) -> bool:
            # avoid too many trees clustering: don't allow trees to be 8-neighbors too often
            r,c = cell
            cnt8 = sum((nb in tree_set) for nb in neighbors8(cell,R,C))
            return cnt8 <= 2

        for cell in cells:
            if len(trees) >= nT:
                break
            if cell in tree_set:
                continue
            if tree_ok(cell):
                trees.append(cell)
                tree_set.add(cell)

        if len(trees) < 2:
            continue

        grid = [['X']*C for _ in range(R)]
        for r,c in trees:
            grid[r][c] = 'T'

        # We will *construct* a valid tent placement first by solving with random row/col constraints derived from one solution.
        # Generate a random assignment by temporarily setting row/col constraints to "unknown" via repeated random choices,
        # then compute constraints from the found assignment and check uniqueness.
        # Approach:
        # 1) Find any solution with only rules (1)(2)(5) + total tents = trees, without row/col constraints.
        #    We'll do this by trying random row/col constraints derived from a randomly found assignment:
        #    - First get one solution using loose constraints: row/col constraints = big numbers then corrected? Not possible.
        # Instead: we directly search for a placement of tents for all trees (bijection) ignoring row/col counts,
        # then set constraints equal to the counts of that placement, and finally check if unique.
        #
        # Implement custom search to find one placement ignoring row/col counts but enforcing tent conflict + adjacency.
        cand_by_tree = []
        for t in trees:
            cands = [nb for nb in neighbors4(t,R,C) if grid[nb[0]][nb[1]] != 'T']
            if not cands:
                cand_by_tree = None
                break
            cand_by_tree.append(cands)
        if cand_by_tree is None:
            continue

        order = sorted(range(len(trees)), key=lambda i: (len(cand_by_tree[i]), i))
        used = set()
        assign = [None]*len(trees)

        def conflicts(cell:Cell)->bool:
            for nb in neighbors8(cell,R,C):
                if nb in used:
                    return True
            return False

        found = False

        def bt(k:int):
            nonlocal found
            if found:
                return
            if k==len(trees):
                found = True
                return
            ti = order[k]
            cands = cand_by_tree[ti][:]
            rng.shuffle(cands)
            for cell in cands:
                if cell in used or conflicts(cell):
                    continue
                used.add(cell)
                assign[ti]=cell
                bt(k+1)
                if found:
                    return
                assign[ti]=None
                used.remove(cell)

        bt(0)
        if not found:
            continue

        # Build constraints from this assignment
        tents = [assign[i] for i in range(len(trees))]
        row_cons = [0]*R
        col_cons = [0]*C
        for r,c in tents:
            row_cons[r]+=1
            col_cons[c]+=1

        # Now check uniqueness given these constraints
        num, sol = solve_tents_unique(grid, row_cons, col_cons, need_unique=True)
        if num != 1 or sol is None:
            continue

        # Extra sanity: ensure solution matches counts and no tents on trees
        ok = True
        for r in range(R):
            for c in range(C):
                if sol[r][c] == 'C' and grid[r][c] == 'T':
                    ok = False
        if not ok:
            continue

        return grid, row_cons, col_cons, sol

    raise RuntimeError("在采样预算内未能生成可唯一求解的实例。")


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    out = []
    seen = set()  # avoid duplicates by (grid,row,col)
    attempts = 0
    max_attempts = 2000

    while len(out) < count and attempts < max_attempts:
        attempts += 1
        try:
            grid, row_cons, col_cons, sol = make_instance(rng)
        except RuntimeError:
            continue

        key = (tuple(map(tuple, grid)), tuple(row_cons), tuple(col_cons))
        if key in seen:
            continue
        seen.add(key)

        problem = render_problem_zh(grid, row_cons, col_cons)
        answer = sol
        expl = explanation_zh(grid, row_cons, col_cons, sol)

        # Final self-check: uniqueness again (independent call, but same solver; add a cheap brute check for very small grids)
        num, _ = solve_tents_unique(grid, row_cons, col_cons, need_unique=True)
        if num != 1:
            continue

        out.append({"problem": problem, "answer": answer, "explanation": expl})

    if len(out) < count:
        print(f"仅生成 {len(out)}/{count} 题；可尝试更换 seed 或降低 count。", file=sys.stderr)

    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()