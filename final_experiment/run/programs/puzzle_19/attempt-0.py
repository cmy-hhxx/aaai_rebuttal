import sys, json, random, itertools
from collections import defaultdict, Counter, deque

# Star Battle puzzle generator/solver
# Reads: {"seed": int, "count": int}
# Outputs: JSON array of objects: {problem:str, answer:JSON, explanation:str}
#
# Uses only stdlib. (z3/sympy allowed but not required.)
#
# Core idea:
# - Generate region grids (letters) for size N x N with fixed n stars per row/col/region.
# - Ensure regions are connected and there are exactly N regions, each with size N (so total N^2).
# - Solve with exact backtracking + constraint propagation and verify uniqueness.
# - Return coordinates per region in alphabetical order.

# ---------------- Utilities ----------------

def neighbors8(r, c, N):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < N and 0 <= cc < N:
                yield rr, cc

def neighbors4(r, c, N):
    for dr, dc in ((1,0), (-1,0), (0,1), (0,-1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < N and 0 <= cc < N:
            yield rr, cc

def is_connected(cells, N):
    # cells: set of (r,c)
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

def fmt_grid(grid):
    # grid as list[list[str]]
    return "\n".join(" ".join(row) for row in grid)

def region_letters(N):
    # Up to 26 for simplicity; keep N <= 10 here.
    letters = [chr(ord('A') + i) for i in range(N)]
    return letters

def coord1(r, c):
    return (r + 1, c + 1)

def sort_coords(coords):
    return sorted(coords, key=lambda x: (x[0], x[1]))

def render_answer_by_region(grid, stars):
    # stars: set (r,c)
    N = len(grid)
    reg_to_coords = defaultdict(list)
    for (r, c) in stars:
        reg_to_coords[grid[r][c]].append(coord1(r,c))
    # order alphabetically by region label
    for k in reg_to_coords:
        reg_to_coords[k] = sort_coords(reg_to_coords[k])
    labels = sorted(reg_to_coords.keys())
    lines = []
    for lab in labels:
        coords = reg_to_coords[lab]
        part = lab + "".join(f"({r},{c})" for (r,c) in coords)
        lines.append(part)
    return "[[" + "\n".join(lines) + "]]"

# ---------------- Solver ----------------

class StarBattleSolver:
    def __init__(self, grid, nstars):
        self.grid = grid
        self.N = len(grid)
        self.k = nstars
        # Map region label -> list of cells
        self.regions = defaultdict(list)
        for r in range(self.N):
            for c in range(self.N):
                self.regions[grid[r][c]].append((r,c))
        self.region_labels = sorted(self.regions.keys())
        # Precompute adjacency mask
        self.adj8 = [[set() for _ in range(self.N)] for __ in range(self.N)]
        for r in range(self.N):
            for c in range(self.N):
                self.adj8[r][c] = set(neighbors8(r,c,self.N))
        # Ordering of cells for backtracking: prefer constrained cells
        self.cells = [(r,c) for r in range(self.N) for c in range(self.N)]

    def solve_all(self, max_solutions=2):
        N, k = self.N, self.k
        # State
        stars = set()
        banned = set()  # cells not allowed due to adjacency to stars
        row_cnt = [0]*N
        col_cnt = [0]*N
        reg_cnt = {lab:0 for lab in self.region_labels}

        # For fast region lookup
        cell_region = {}
        for lab, cells in self.regions.items():
            for rc in cells:
                cell_region[rc] = lab

        # domain for each cell: undecided initially
        undecided = set(self.cells)

        # Heuristic: choose next cell based on remaining quota tightness in its row/col/region
        def score_cell(rc):
            r, c = rc
            lab = cell_region[rc]
            # higher means more constrained
            return (row_cnt[r], col_cnt[c], reg_cnt[lab])

        # Feasibility checks
        def can_place(rc):
            r, c = rc
            if rc in stars: return False
            if rc in banned: return False
            if row_cnt[r] >= k or col_cnt[c] >= k: return False
            lab = cell_region[rc]
            if reg_cnt[lab] >= k: return False
            return True

        def quick_bound_ok():
            # Check if any row/col/region cannot reach k given remaining available cells
            # available = undecided cells not banned and not already star
            # But we also must consider adjacency; banned already accounts adjacency to placed stars.
            # This bound is coarse but effective.
            # Rows
            for r in range(N):
                need = k - row_cnt[r]
                if need < 0:
                    return False
                if need == 0:
                    continue
                avail = 0
                for c in range(N):
                    rc = (r,c)
                    if rc in stars: continue
                    if rc in banned: continue
                    lab = cell_region[rc]
                    if reg_cnt[lab] >= k:  # region full
                        continue
                    if col_cnt[c] >= k:    # column full
                        continue
                    avail += 1
                if avail < need:
                    return False
            # Cols
            for c in range(N):
                need = k - col_cnt[c]
                if need < 0:
                    return False
                if need == 0:
                    continue
                avail = 0
                for r in range(N):
                    rc = (r,c)
                    if rc in stars: continue
                    if rc in banned: continue
                    lab = cell_region[rc]
                    if reg_cnt[lab] >= k:
                        continue
                    if row_cnt[r] >= k:
                        continue
                    avail += 1
                if avail < need:
                    return False
            # Regions
            for lab in self.region_labels:
                need = k - reg_cnt[lab]
                if need < 0:
                    return False
                if need == 0:
                    continue
                avail = 0
                for rc in self.regions[lab]:
                    if rc in stars: continue
                    if rc in banned: continue
                    r,c = rc
                    if row_cnt[r] >= k or col_cnt[c] >= k:
                        continue
                    avail += 1
                if avail < need:
                    return False
            return True

        # Deterministic propagation: if a row/col/region needs all remaining avail cells => force them stars;
        # if it needs 0 => force none, but we don't track explicit none; it's okay.
        def forced_moves():
            forced = set()
            # Row forces
            for r in range(N):
                need = k - row_cnt[r]
                if need <= 0:
                    continue
                avail_cells = []
                for c in range(N):
                    rc = (r,c)
                    if can_place(rc):
                        avail_cells.append(rc)
                if len(avail_cells) == need:
                    forced.update(avail_cells)
            # Col forces
            for c in range(N):
                need = k - col_cnt[c]
                if need <= 0:
                    continue
                avail_cells = []
                for r in range(N):
                    rc = (r,c)
                    if can_place(rc):
                        avail_cells.append(rc)
                if len(avail_cells) == need:
                    forced.update(avail_cells)
            # Region forces
            for lab in self.region_labels:
                need = k - reg_cnt[lab]
                if need <= 0:
                    continue
                avail_cells = []
                for rc in self.regions[lab]:
                    if can_place(rc):
                        avail_cells.append(rc)
                if len(avail_cells) == need:
                    forced.update(avail_cells)
            return forced

        # apply placement
        def place(rc):
            r, c = rc
            stars.add(rc)
            # update counts
            row_cnt[r] += 1
            col_cnt[c] += 1
            lab = cell_region[rc]
            reg_cnt[lab] += 1
            # ban adjacency including itself? itself is star; keep banned separate
            newly_banned = set(self.adj8[r][c])
            newly_banned.add(rc)  # treat star cell as not placeable further
            added = newly_banned - banned
            banned.update(newly_banned)
            return added

        def unplace(rc, added_banned):
            r, c = rc
            stars.remove(rc)
            row_cnt[r] -= 1
            col_cnt[c] -= 1
            lab = cell_region[rc]
            reg_cnt[lab] -= 1
            # recompute banned accurately is hard; instead maintain banned as multiset counts
            # We'll implement proper multiset counts rather than set rolling.
            raise RuntimeError("unplace should not be used in this set-based variant")

        # Use multiset for banned due to backtracking
        ban_count = Counter()
        def is_banned(rc):
            return ban_count[rc] > 0

        def can_place2(rc):
            r,c = rc
            if rc in stars: return False
            if is_banned(rc): return False
            if row_cnt[r] >= k or col_cnt[c] >= k: return False
            lab = cell_region[rc]
            if reg_cnt[lab] >= k: return False
            return True

        def place2(rc):
            r,c = rc
            stars.add(rc)
            row_cnt[r]+=1
            col_cnt[c]+=1
            lab = cell_region[rc]
            reg_cnt[lab]+=1
            impacted = set(self.adj8[r][c])
            impacted.add(rc)
            for x in impacted:
                ban_count[x] += 1

        def unplace2(rc):
            r,c = rc
            stars.remove(rc)
            row_cnt[r]-=1
            col_cnt[c]-=1
            lab = cell_region[rc]
            reg_cnt[lab]-=1
            impacted = set(self.adj8[r][c])
            impacted.add(rc)
            for x in impacted:
                ban_count[x] -= 1
                if ban_count[x] == 0:
                    del ban_count[x]

        def quick_bound_ok2():
            for r in range(N):
                need = k - row_cnt[r]
                if need < 0: return False
                if need == 0: continue
                avail = 0
                for c in range(N):
                    rc=(r,c)
                    if rc in stars: continue
                    if is_banned(rc): continue
                    lab = cell_region[rc]
                    if reg_cnt[lab] >= k or col_cnt[c] >= k:
                        continue
                    avail += 1
                if avail < need: return False
            for c in range(N):
                need = k - col_cnt[c]
                if need < 0: return False
                if need == 0: continue
                avail = 0
                for r in range(N):
                    rc=(r,c)
                    if rc in stars: continue
                    if is_banned(rc): continue
                    lab = cell_region[rc]
                    if reg_cnt[lab] >= k or row_cnt[r] >= k:
                        continue
                    avail += 1
                if avail < need: return False
            for lab in self.region_labels:
                need = k - reg_cnt[lab]
                if need < 0: return False
                if need == 0: continue
                avail = 0
                for rc in self.regions[lab]:
                    if rc in stars: continue
                    if is_banned(rc): continue
                    r,c=rc
                    if row_cnt[r] >= k or col_cnt[c] >= k:
                        continue
                    avail += 1
                if avail < need: return False
            return True

        def forced_moves2():
            forced=set()
            # row
            for r in range(N):
                need=k-row_cnt[r]
                if need<=0: continue
                avail=[]
                for c in range(N):
                    rc=(r,c)
                    if can_place2(rc):
                        avail.append(rc)
                if len(avail)==need:
                    forced.update(avail)
            # col
            for c in range(N):
                need=k-col_cnt[c]
                if need<=0: continue
                avail=[]
                for r in range(N):
                    rc=(r,c)
                    if can_place2(rc):
                        avail.append(rc)
                if len(avail)==need:
                    forced.update(avail)
            # region
            for lab in self.region_labels:
                need=k-reg_cnt[lab]
                if need<=0: continue
                avail=[]
                for rc in self.regions[lab]:
                    if can_place2(rc):
                        avail.append(rc)
                if len(avail)==need:
                    forced.update(avail)
            return forced

        solutions=[]

        # Precompute region list per cell for ordering
        def pick_next_cell():
            # choose row/col/region with largest need/least availability, then pick a candidate cell in it.
            best = None
            best_list = None  # candidates
            # consider rows
            for r in range(N):
                need = k-row_cnt[r]
                if need <= 0: continue
                cand=[(r,c) for c in range(N) if can_place2((r,c))]
                if not cand: return None, None
                key=(len(cand), -need, 0, r)
                if best is None or key < best:
                    best=key; best_list=cand
            # cols
            for c in range(N):
                need = k-col_cnt[c]
                if need <= 0: continue
                cand=[(r,c) for r in range(N) if can_place2((r,c))]
                if not cand: return None, None
                key=(len(cand), -need, 1, c)
                if best is None or key < best:
                    best=key; best_list=cand
            # regions
            for idx,lab in enumerate(self.region_labels):
                need = k-reg_cnt[lab]
                if need <= 0: continue
                cand=[rc for rc in self.regions[lab] if can_place2(rc)]
                if not cand: return None, None
                key=(len(cand), -need, 2, idx)
                if best is None or key < best:
                    best=key; best_list=cand
            if best_list is None:
                return None, None
            # within candidate list choose most constrained cell (by row/col/region current fills)
            best_cell = min(best_list, key=lambda rc: (-score_cell(rc)[0]-score_cell(rc)[1]-score_cell(rc)[2], rc[0], rc[1]))
            return best_cell, best_list

        def done():
            # all quotas met
            return all(x==k for x in row_cnt) and all(x==k for x in col_cnt) and all(reg_cnt[lab]==k for lab in self.region_labels)

        def dfs():
            if len(solutions) >= max_solutions:
                return
            # propagate forced moves iteratively
            forced_stack=[]
            while True:
                if not quick_bound_ok2():
                    # undo forced
                    for rc in reversed(forced_stack):
                        unplace2(rc)
                    return
                forced = forced_moves2()
                forced = [rc for rc in forced if rc not in stars]  # avoid repeats
                if not forced:
                    break
                # Check forced are mutually non-adjacent; if conflict -> fail
                # Place in a deterministic order to ensure reproducibility
                forced = sorted(forced)
                for rc in forced:
                    if not can_place2(rc):
                        for rr in reversed(forced_stack):
                            unplace2(rr)
                        return
                    place2(rc)
                    forced_stack.append(rc)

            if done():
                solutions.append(set(stars))
                for rc in reversed(forced_stack):
                    unplace2(rc)
                return

            cell, cand_list = pick_next_cell()
            if cell is None:
                for rc in reversed(forced_stack):
                    unplace2(rc)
                return

            # Branch: try placing star on some candidates, but to keep complete, we need also consider "not star" choices.
            # Instead we branch by choosing one candidate to be a star among a set; however exactness requires binary decisions.
            # We'll do binary: try place at chosen cell; else forbid it by temporary ban (ban_count increment on itself only)
            # But forbid must be reversible.
            rc = cell

            # Try place
            if can_place2(rc):
                place2(rc)
                dfs()
                unplace2(rc)
                if len(solutions) >= max_solutions:
                    for x in reversed(forced_stack):
                        unplace2(x)
                    return

            # Try not place: forbid rc (only) for this branch
            ban_count[rc] += 1
            dfs()
            ban_count[rc] -= 1
            if ban_count[rc] == 0:
                del ban_count[rc]

            # undo forced
            for x in reversed(forced_stack):
                unplace2(x)

        dfs()
        return solutions

# ---------------- Region grid generators ----------------

def latin_region_grid(N):
    # Region at (r,c) = letters[(r+c)%N] gives exactly N cells per region and connected? Not necessarily.
    # We'll post-fix by performing random swaps and then enforce connectivity by repair, or just use a different scheme.
    letters = region_letters(N)
    grid = [[letters[(r + c) % N] for c in range(N)] for r in range(N)]
    return grid

def stripe_region_grid(N, rnd):
    # Construct N regions each size N, connected, via carving a random Hamiltonian path and slicing into N chunks.
    letters = region_letters(N)
    cells = [(r,c) for r in range(N) for c in range(N)]
    # Create a simple snake path then apply random reversals/rotations on segments to vary
    path=[]
    for r in range(N):
        row = [(r,c) for c in range(N)]
        if r%2==1:
            row.reverse()
        path.extend(row)
    # random segment reversals
    for _ in range(3*N):
        a = rnd.randrange(0, N*N)
        b = rnd.randrange(0, N*N)
        if a>b: a,b=b,a
        if b-a >= 2:
            path[a:b] = reversed(path[a:b])
    # Assign chunks
    grid = [[None]*N for _ in range(N)]
    for i, rc in enumerate(path):
        lab = letters[i//N]
        r,c=rc
        grid[r][c]=lab
    return grid

def random_connected_equal_regions(N, rnd, attempts=200):
    # Grow N connected regions each target size N.
    letters = region_letters(N)
    target = N
    for _ in range(attempts):
        grid = [[None]*N for _ in range(N)]
        # pick N distinct seeds
        allcells=[(r,c) for r in range(N) for c in range(N)]
        rnd.shuffle(allcells)
        seeds=allcells[:N]
        fronts=[deque([seeds[i]]) for i in range(N)]
        sizes=[0]*N
        for i,(r,c) in enumerate(seeds):
            grid[r][c]=letters[i]
            sizes[i]=1
        unassigned=set(allcells[N:])
        # grow
        stalled=0
        while unassigned and stalled < 5*N*N:
            progressed=False
            order=list(range(N))
            rnd.shuffle(order)
            for i in order:
                if sizes[i] >= target:
                    continue
                # collect boundary candidates
                cand=[]
                for (r,c) in list(fronts[i]):
                    for rr,cc in neighbors4(r,c,N):
                        if (rr,cc) in unassigned:
                            cand.append((rr,cc))
                if not cand:
                    continue
                rc=rnd.choice(cand)
                r,c=rc
                grid[r][c]=letters[i]
                sizes[i]+=1
                unassigned.remove(rc)
                fronts[i].append(rc)
                progressed=True
            if not progressed:
                stalled += 1
            else:
                stalled=0
        if unassigned:
            continue
        # validate sizes and connectivity
        ok=True
        for i,lab in enumerate(letters):
            cells=set((r,c) for r in range(N) for c in range(N) if grid[r][c]==lab)
            if len(cells)!=target or not is_connected(cells,N):
                ok=False
                break
        if not ok:
            continue
        return grid
    return None

# ---------------- Puzzle generation ----------------

def build_problem_text(grid, nstars, lang="zh"):
    N=len(grid)
    # Provide rule and grid
    if lang=="zh":
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
    else:
        intro = f"N={N}, stars per row/col/region = {nstars}\nGrid:\n"
    return intro + fmt_grid(grid)

def generate_one(rnd, lang="zh"):
    # Choose parameters/family
    # Keep N <= 10 so letters A..J possible
    family = rnd.choice(["stripe", "randomgrow", "latinfix"])
    if family == "stripe":
        N = rnd.choice([6,7,8,9,10])
        k = rnd.choice([1,2]) if N>=7 else 1
        grid = stripe_region_grid(N, rnd)
    elif family == "latinfix":
        N = rnd.choice([6,7,8,9])
        k = 1 if N<=8 else rnd.choice([1,2])
        grid = latin_region_grid(N)
    else:
        N = rnd.choice([6,7,8,9,10])
        k = rnd.choice([1,2]) if N>=7 else 1
        grid = random_connected_equal_regions(N, rnd)
        if grid is None:
            # fallback
            grid = stripe_region_grid(N, rnd)

    # Ensure exactly N regions labels A.. and each size N
    letters = set(region_letters(len(grid)))
    present=set(ch for row in grid for ch in row)
    if present != letters:
        # normalize by remapping if needed
        labs=sorted(present)
        target=region_letters(len(grid))
        mp={labs[i]:target[i] for i in range(min(len(labs),len(target)))}
        for r in range(len(grid)):
            for c in range(len(grid)):
                grid[r][c]=mp.get(grid[r][c], grid[r][c])

    # Solve and require uniqueness
    solver = StarBattleSolver(grid, k)
    sols = solver.solve_all(max_solutions=2)
    if len(sols) != 1:
        return None
    stars = sols[0]

    # Additional cross-check: verify all constraints directly
    N=len(grid)
    # row/col
    for r in range(N):
        if sum((r,c) in stars for c in range(N)) != k:
            return None
    for c in range(N):
        if sum((r,c) in stars for r in range(N)) != k:
            return None
    # region
    reg=defaultdict(int)
    for (r,c) in stars:
        reg[grid[r][c]] += 1
    if any(reg[lab] != k for lab in region_letters(N)):
        return None
    # adjacency
    for (r,c) in stars:
        for rr,cc in neighbors8(r,c,N):
            if (rr,cc) in stars:
                return None

    problem = build_problem_text(grid, k, lang=lang)
    answer_str = render_answer_by_region(grid, stars)

    # explanation: include a compact verifiable check summary (counts & adjacency)
    if lang=="zh":
        # give per-row star positions and per-col counts
        row_list = []
        for r in range(N):
            cols=[c+1 for c in range(N) if (r,c) in stars]
            row_list.append(f"第{r+1}行星列={cols}")
        col_list = []
        for c in range(N):
            rows=[r+1 for r in range(N) if (r,c) in stars]
            col_list.append(f"第{c+1}列星行={rows}")
        explanation = (
            "校验要点：\n"
            f"- 每行/每列/每区域均为 {k} 颗星；\n"
            "- 星之间（含对角）不相邻。\n"
            "按行列给出星的位置便于复核：\n"
            + "\n".join(row_list) + "\n"
            + "\n".join(col_list)
        )
    else:
        explanation = "Verified constraints."

    return {
        "problem": problem,
        "answer": answer_str,
        "explanation": explanation
    }

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rnd = random.Random(seed)

    lang = "zh"  # default as required by user setting; generator doesn't read it at runtime.

    res=[]
    seen=set()
    attempts=0
    max_attempts = 4000

    while len(res) < count and attempts < max_attempts:
        attempts += 1
        item = generate_one(rnd, lang=lang)
        if item is None:
            continue
        # dedup by grid text
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        res.append(item)

    if len(res) < count:
        print(f"生成失败：仅生成 {len(res)}/{count} 题；请更换 seed 或减少 count。", file=sys.stderr)
        # Still output what we have? Spec says must output exactly count; so raise.
        raise SystemExit(2)

    json.dump(res, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()