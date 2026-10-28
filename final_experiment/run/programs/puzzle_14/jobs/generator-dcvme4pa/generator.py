import sys, json, random, itertools
from collections import deque, defaultdict

# ======== Utility / Formatting ========

def fmt_grid(grid):
    # grid: list[list[str]]
    rows = [" ".join(r) for r in grid]
    return "[[" + ",".join(rows) + "]]"

def deep_copy_grid(g):
    return [row[:] for row in g]

def inb(n, r, c):
    return 0 <= r < n and 0 <= c < n

def neighbors4(n, r, c):
    if r > 0: yield (r-1, c)
    if r+1 < n: yield (r+1, c)
    if c > 0: yield (r, c-1)
    if c+1 < n: yield (r, c+1)

# ======== Core modeling for a Nurikabe-like generator ========
# We generate a solved grid with:
# - Islands are connected components of non-wall cells (not 'A')
# - Each island has exactly one hint number cell.
# - Island size equals that hint number.
# - Islands are separated orthogonally: no two different islands touch orthogonally.
# - Walls ('A') contain no 2x2 all-wall block.
# - Walls are connected (one component).
# We then output a puzzle as matrix with numbers for hints, and X for non-hint cells.
# Solver recomputes the unique wall placement from the puzzle via backtracking + checks.

# We'll represent a solution as:
# sol_type[r][c] in {"A","I"}; and hint positions with number on some I cells.
# Puzzle grid uses "X" for non-hint cells, and number strings for hints.

def check_no_2x2_allA(solA, n):
    # solA is bool grid: True if wall
    for r in range(n-1):
        for c in range(n-1):
            if solA[r][c] and solA[r+1][c] and solA[r][c+1] and solA[r+1][c+1]:
                return False
    return True

def comp_cells(n, mask_true):
    # mask_true: function(r,c)->bool
    vis = [[False]*n for _ in range(n)]
    comps = []
    for r in range(n):
        for c in range(n):
            if mask_true(r,c) and not vis[r][c]:
                q=deque([(r,c)])
                vis[r][c]=True
                cells=[]
                while q:
                    x,y=q.popleft()
                    cells.append((x,y))
                    for nx,ny in neighbors4(n,x,y):
                        if mask_true(nx,ny) and not vis[nx][ny]:
                            vis[nx][ny]=True
                            q.append((nx,ny))
                comps.append(cells)
    return comps

def walls_connected(solA, n):
    cells = [(r,c) for r in range(n) for c in range(n) if solA[r][c]]
    if not cells:
        return False
    start = cells[0]
    q=deque([start])
    seen=set([start])
    while q:
        r,c=q.popleft()
        for nr,nc in neighbors4(n,r,c):
            if solA[nr][nc] and (nr,nc) not in seen:
                seen.add((nr,nc))
                q.append((nr,nc))
    return len(seen)==len(cells)

def islands_from_solution(solA, n):
    # returns components of non-wall
    comps = comp_cells(n, lambda r,c: not solA[r][c])
    return comps

def islands_separated(solA, island_id, n):
    # no orth adjacency between different islands
    for r in range(n):
        for c in range(n):
            if solA[r][c]:
                continue
            id1 = island_id[r][c]
            for nr,nc in neighbors4(n,r,c):
                if solA[nr][nc]:
                    continue
                id2 = island_id[nr][nc]
                if id1 != id2:
                    return False
    return True

def assign_island_ids(solA, n):
    comps = islands_from_solution(solA, n)
    island_id = [[-1]*n for _ in range(n)]
    for i, cells in enumerate(comps):
        for r,c in cells:
            island_id[r][c]=i
    return island_id, comps

def compute_puzzle_from_solution(solA, hints, n):
    # hints: dict[(r,c)] = number int
    puzzle = [["X"]*n for _ in range(n)]
    for (r,c), v in hints.items():
        puzzle[r][c]=str(v)
    return puzzle

def render_solution_matrix(solA, hints, n):
    grid = [["A" if solA[r][c] else "X" for c in range(n)] for r in range(n)]
    for (r,c), v in hints.items():
        grid[r][c]=str(v)
    return grid

# ======== Constructive generation ========

def random_island_shape(rng, n, size, occupied, forbidden_adj):
    """
    Create a connected set of 'size' cells on n*n.
    occupied: set of cells already taken by islands
    forbidden_adj: set of cells that cannot be used (because they'd touch other islands orthogonally)
    Returns set of cells or None.
    """
    # Candidate starting positions
    candidates = [(r,c) for r in range(n) for c in range(n)
                  if (r,c) not in occupied and (r,c) not in forbidden_adj]
    rng.shuffle(candidates)
    for start in candidates[:min(len(candidates), 40)]:
        shape = {start}
        frontier = [start]
        # randomized growth
        while len(shape) < size:
            # collect expansion options
            opts=[]
            for (cr,cc) in list(shape):
                for nr,nc in neighbors4(n,cr,cc):
                    if (nr,nc) in shape: 
                        continue
                    if (nr,nc) in occupied or (nr,nc) in forbidden_adj:
                        continue
                    opts.append((nr,nc))
            if not opts:
                break
            # biased choose cells with more room
            rng.shuffle(opts)
            pick = opts[0]
            shape.add(pick)
        if len(shape) == size:
            return shape
    return None

def build_solution(rng, n):
    """
    Try to build a full solution with multiple islands and connected walls.
    Returns (solA bool grid, hints dict) or None.
    """
    # choose island sizes
    # keep total island cells moderate so walls exist and can be connected
    max_islands = rng.randint(3, 6) if n <= 6 else rng.randint(4, 7)
    sizes=[]
    # prefer mix of 1..5
    for _ in range(max_islands):
        sizes.append(rng.choice([1,2,2,3,3,4,5]))
    # ensure not too many island cells
    total = sum(sizes)
    cap = int(n*n*0.55)
    attempts=0
    while total > cap and attempts < 20:
        # drop or shrink
        idx = rng.randrange(len(sizes))
        if sizes[idx] > 1:
            sizes[idx] -= 1
        else:
            sizes.pop(idx)
        if not sizes:
            sizes=[rng.choice([1,2,3])]
        total=sum(sizes)
        attempts += 1

    # place island shapes with separation constraint
    occupied=set()
    islands=[]
    for size in sorted(sizes, reverse=True):
        # forbidden cells are those adjacent to already occupied cells (to maintain separation)
        forbidden_adj=set()
        for (r,c) in occupied:
            for nr,nc in neighbors4(n,r,c):
                forbidden_adj.add((nr,nc))
        shape = random_island_shape(rng, n, size, occupied, forbidden_adj)
        if shape is None:
            return None
        islands.append(shape)
        occupied |= shape

    # walls are the rest
    solA = [[True]*n for _ in range(n)]
    for (r,c) in occupied:
        solA[r][c] = False

    # check separation (already enforced by forbidden_adj, but keep)
    island_id, comps = assign_island_ids(solA, n)
    if len(comps) != len(islands):
        return None
    if not islands_separated(solA, island_id, n):
        return None

    # no 2x2 walls and walls connected; if not, tweak by rejecting
    if not check_no_2x2_allA(solA, n):
        return None
    if not walls_connected(solA, n):
        return None

    # place one hint per island: choose a random cell within each island
    hints={}
    for cells in comps:
        size = len(cells)
        pos = rng.choice(cells)
        hints[pos]=size

    return solA, hints

# ======== Solver for uniqueness check ========

def parse_puzzle(puzzle):
    n=len(puzzle)
    hints={}
    for r in range(n):
        for c in range(n):
            s=puzzle[r][c]
            if s != "X":
                hints[(r,c)] = int(s)
    return hints

def solve_puzzle_all(puzzle, limit=2):
    """
    Backtracking solver.
    Variables: each cell is wall(A)=1 or island=0.
    Constraints:
      - Hint cells are island.
      - Island components: each component must have exactly one hint and size equals that hint.
      - Different islands cannot touch orthogonally: i.e., if two non-wall cells adjacent then must be same component.
        (This is naturally satisfied by component definition; but we must prevent two components adjacent -> impossible by definition.
         Since components are maximal, adjacent non-walls always same component, so this constraint is inherent.)
      - Walls: connected.
      - No 2x2 all wall.
    We search over assignments using incremental pruning:
      - Enforce hint cells are island.
      - Use 2x2 pruning on walls.
      - Use island size upper bounds during partial assignment via flood fill on "definitely island" and "possibly island".
    Returns list of solutions (each solution is solA bool grid) up to limit.
    """
    n=len(puzzle)
    hints=parse_puzzle(puzzle)
    # state: -1 unknown, 0 island, 1 wall
    st=[[-1]*n for _ in range(n)]
    for (r,c),v in hints.items():
        st[r][c]=0

    # precompute cell order: prefer near hints, then others
    def score(cell):
        r,c=cell
        if (r,c) in hints: return -999
        # distance to nearest hint
        dmin=10**9
        for hr,hc in hints:
            d=abs(hr-r)+abs(hc-c)
            if d<dmin: dmin=d
        return dmin
    order=[(r,c) for r in range(n) for c in range(n) if (r,c) not in hints]
    order.sort(key=score)

    sols=[]

    def violates_2x2(st):
        for r in range(n-1):
            for c in range(n-1):
                vals=[st[r][c],st[r+1][c],st[r][c+1],st[r+1][c+1]]
                if all(v==1 for v in vals):
                    return True
        return False

    def partial_island_feasible():
        # For each hint, compute min/max possible size for its component
        # using cells that are not forced wall, and not crossing forced walls.
        # Additionally, if a forced island cell is not reachable from any hint => infeasible.
        # Also prevent two hints being connected through non-wall-possible corridor of forced-island cells:
        # If two hints are already connected via forced island cells (st==0), infeasible.
        # Finally, ensure component max size >= clue and min size <= clue.
        # Build graph where passable means st != 1 (unknown or island)
        passable = lambda r,c: st[r][c] != 1
        forced_island = lambda r,c: st[r][c] == 0

        # connectivity among forced islands: check if any forced island component contains >=2 hints
        comps_forced = comp_cells(n, forced_island)
        for comp in comps_forced:
            cnt=0
            for cell in comp:
                if cell in hints:
                    cnt += 1
                    if cnt >= 2:
                        return False

        # for each hint, compute reachable region in passable graph, but cannot pass through other hints cell? actually hints are islands so allowed.
        # max size is size of reachable passable component containing hint, but excluding cells that are forced island of a different hint component? unknown.
        # We'll approximate using passable component; and min size is size of forced island component containing hint.
        # If any forced island cell not connected to any hint through passable cells => could belong to some island without hint -> impossible
        # However unknown cells could become wall to separate, so only forced island cells matter.
        # Each forced island cell must be connected to at least one hint via forced island path? Actually island cells in final must connect to some hint.
        # If a forced island cell currently not connected to any hint through forced island, it could connect later via making unknowns island,
        # so it's still feasible. So skip that.

        # compute min sizes from forced island components
        comp_id=[[-1]*n for _ in range(n)]
        for i, comp in enumerate(comps_forced):
            for r,c in comp:
                comp_id[r][c]=i
        min_size_by_hint={}
        for (hr,hc), clue in hints.items():
            cid=comp_id[hr][hc]
            min_sz = 1 if cid==-1 else len(comps_forced[cid])
            min_size_by_hint[(hr,hc)]=min_sz
            if min_sz > clue:
                return False

        # compute max sizes by passable components
        comps_pass = comp_cells(n, passable)
        comp_pass_id=[[-1]*n for _ in range(n)]
        for i, comp in enumerate(comps_pass):
            for r,c in comp:
                comp_pass_id[r][c]=i
        max_size_by_hint={}
        for (hr,hc), clue in hints.items():
            pid=comp_pass_id[hr][hc]
            max_sz = len(comps_pass[pid])
            # crude upper bound: if passable component contains another hint, they must be separated by walls eventually
            # possible as unknowns can become walls. keep as is.
            max_size_by_hint[(hr,hc)]=max_sz
            if max_sz < clue:
                return False

        return True

    def finalize_and_check():
        # build solA
        solA=[[st[r][c]==1 for c in range(n)] for r in range(n)]
        # check no unknowns
        for r in range(n):
            for c in range(n):
                if st[r][c] == -1:
                    return False
        # check no 2x2 wall
        if not check_no_2x2_allA(solA, n):
            return False
        # walls connected
        if not walls_connected(solA, n):
            return False
        # islands components and clue match
        island_id, comps = assign_island_ids(solA, n)
        # each island has exactly one hint and size equals clue
        for comp in comps:
            hint_cells=[cell for cell in comp if cell in hints]
            if len(hint_cells)!=1:
                return False
            clue = hints[hint_cells[0]]
            if len(comp)!=clue:
                return False
        # also every hint is in some island (true)
        return True

    def choose_next():
        # pick unassigned cell with heuristic: try to avoid breaking clue feasibility
        best=None
        best_deg=-1
        for r,c in order:
            if st[r][c] != -1: 
                continue
            # degree of constraints: count assigned neighbors
            deg=0
            for nr,nc in neighbors4(n,r,c):
                if st[nr][nc] != -1:
                    deg += 1
            if deg > best_deg:
                best_deg=deg
                best=(r,c)
        if best is None:
            # maybe only hints exist
            for r in range(n):
                for c in range(n):
                    if st[r][c]==-1:
                        return (r,c)
            return None
        return best

    def backtrack():
        if len(sols) >= limit:
            return
        if violates_2x2(st):
            return
        if not partial_island_feasible():
            return
        cell = choose_next()
        if cell is None:
            if finalize_and_check():
                sols.append([[st[r][c]==1 for c in range(n)] for r in range(n)])
            return
        r,c = cell

        # Branching order: try wall first to keep islands tight; but avoid forcing hint impossibility
        for val in (1,0):
            st[r][c]=val
            backtrack()
            st[r][c]=-1
            if len(sols) >= limit:
                return

    backtrack()
    return sols

# ======== Problem statement rendering (ZH) ========

def render_problem_zh(puzzle):
    n=len(puzzle)
    lines=[]
    lines.append("你正在解一道自定义“筑岛围墙”类逻辑题。棋盘为 n×n 方格。部分格子给出数字提示，其余格子为空白（用 X 表示）。")
    lines.append("")
    lines.append("规则：")
    lines.append("1）你需要在某些格子上建墙，墙格用 A 表示；未建墙且不含数字的岛格仍用 X 表示；数字格保留数字。")
    lines.append("2）所有非墙格（数字格与 X）会形成若干个“岛屿”，每个岛屿必须只包含且恰好包含一个数字。")
    lines.append("3）每个岛屿的格子总数必须等于该岛屿中数字提示的数值。")
    lines.append("4）不同岛屿之间不能上下左右相邻（只能被墙隔开）。")
    lines.append("5）墙格（A）组成的区域中不允许出现任意 2×2（或更大）全是墙的实心矩形；等价地说：任意 2×2 小方块中不能四格都是 A。")
    lines.append("6）所有墙格必须上下左右连通（形成一条连续的整体墙域）。")
    lines.append("")
    lines.append("输入给定为矩阵，X 表示未给数字的格子。请将需要建墙的格子替换为 A，并按题目要求输出最终矩阵。")
    lines.append("")
    lines.append("请按从左到右、从上到下输出每个元素；元素以空格分隔，每行用逗号分隔；最外层用双中括号包裹。")
    lines.append("")
    lines.append("题目矩阵：")
    for r in range(n):
        lines.append(" ".join(puzzle[r]))
    return "\n".join(lines)

def explanation_zh(puzzle, solA, hints):
    n=len(puzzle)
    # Provide verifiable checks: list islands sizes and hint positions, wall properties
    island_id, comps = assign_island_ids(solA, n)
    # map island -> hint and size
    info=[]
    for i, cells in enumerate(comps):
        hint_cells=[cell for cell in cells if cell in hints]
        h = hint_cells[0]
        info.append((i, len(cells), h, hints[h]))
    info.sort(key=lambda x: (x[2][0], x[2][1]))
    # wall count and connectivity proof by component count
    wall_cells=[(r,c) for r in range(n) for c in range(n) if solA[r][c]]
    wall_comps = comp_cells(n, lambda r,c: solA[r][c])
    # check 2x2 violations count
    bad2=[]
    for r in range(n-1):
        for c in range(n-1):
            if solA[r][c] and solA[r+1][c] and solA[r][c+1] and solA[r+1][c+1]:
                bad2.append((r,c))

    lines=[]
    lines.append("校验要点（基于给定答案矩阵）：")
    lines.append(f"- 墙格数量：{len(wall_cells)}；墙域连通分量数：{len(wall_comps)}（必须为 1）。")
    lines.append(f"- 2×2 全墙块数量：{len(bad2)}（必须为 0）。")
    lines.append("- 岛屿逐一核对（列出：岛屿大小 = 提示数，且每岛仅一个提示）：")
    for i, sz, (hr,hc), clue in info:
        lines.append(f"  * 岛屿{i}: 大小{sz}；提示格在({hr+1},{hc+1})，提示数{clue}。")
    lines.append("- 不同岛屿不相邻：由最终矩阵中岛屿之间均被 A 隔开可逐格检查。")
    lines.append("以上各条同时满足则为有效解。")
    return "\n".join(lines)

# ======== Generator wrapper ========

def gen_one(rng, output_language="zh"):
    # choose size with variety
    n = rng.choice([5,5,6,6,7])
    # attempt build and ensure unique solvable
    for _ in range(200):
        built = build_solution(rng, n)
        if built is None:
            continue
        solA, hints = built
        puzzle = compute_puzzle_from_solution(solA, hints, n)

        # Uniqueness via solver
        sols = solve_puzzle_all(puzzle, limit=2)
        if len(sols) != 1:
            continue
        # ensure the found solution matches our constructed one (cross-check)
        found = sols[0]
        if found != solA:
            continue

        problem = render_problem_zh(puzzle) if output_language == "zh" else render_problem_zh(puzzle)
        answer_grid = render_solution_matrix(solA, hints, n)
        answer = fmt_grid(answer_grid)
        expl = explanation_zh(puzzle, solA, hints) if output_language == "zh" else explanation_zh(puzzle, solA, hints)
        return {"problem": problem, "answer": answer, "explanation": expl}
    raise RuntimeError("在给定采样上限内未能生成满足唯一解与全部约束的题目实例。")

def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    # try to read language from possible outer harness; default zh
    output_language = "zh"
    # allow optional in stdin
    if isinstance(data, dict) and "output_language" in data:
        output_language = data["output_language"] or "zh"

    items=[]
    seen=set()
    tries=0
    # Deduplicate by puzzle text (numbers layout)
    while len(items) < count:
        tries += 1
        if tries > count * 400:
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