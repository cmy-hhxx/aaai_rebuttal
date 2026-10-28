import sys, json, random
from collections import deque

# ============================================================
# Robust, fast generator for Nurikabe-like puzzles (islands + wall)
# Key: avoid heavy uniqueness proving that can time out.
# We generate instances from a "template family" with a UNIQUE completion
# by construction, and then verify via a lightweight exact enumerator
# on the (small) remaining degrees of freedom.
#
# Output format:
# - problem: Chinese statement with puzzle grid (numbers + X)
# - answer: [[...]] matrix using A (wall), X (island blank), numbers
# - explanation: brief verifiable checks + key structure description
# ============================================================

# -------------------- helpers --------------------

def nbr4(n, r, c):
    if r: yield (r-1, c)
    if r+1 < n: yield (r+1, c)
    if c: yield (r, c-1)
    if c+1 < n: yield (r, c+1)

def fmt_grid(grid):
    return "[[" + ",".join(" ".join(row) for row in grid) + "]]"

def comp_cells(n, is_true):
    vis = [[False]*n for _ in range(n)]
    comps = []
    for r in range(n):
        for c in range(n):
            if is_true(r,c) and not vis[r][c]:
                q = deque([(r,c)])
                vis[r][c] = True
                cells=[]
                while q:
                    x,y=q.popleft()
                    cells.append((x,y))
                    for nx,ny in nbr4(n,x,y):
                        if is_true(nx,ny) and not vis[nx][ny]:
                            vis[nx][ny]=True
                            q.append((nx,ny))
                comps.append(cells)
    return comps

def walls_connected(solA, n):
    walls=[(r,c) for r in range(n) for c in range(n) if solA[r][c]]
    if not walls:
        return False
    q=deque([walls[0]])
    seen=set([walls[0]])
    while q:
        r,c=q.popleft()
        for nr,nc in nbr4(n,r,c):
            if solA[nr][nc] and (nr,nc) not in seen:
                seen.add((nr,nc)); q.append((nr,nc))
    return len(seen)==len(walls)

def no_2x2_walls(solA, n):
    for r in range(n-1):
        for c in range(n-1):
            if solA[r][c] and solA[r+1][c] and solA[r][c+1] and solA[r+1][c+1]:
                return False
    return True

def assign_island_ids(solA, n):
    comps = comp_cells(n, lambda r,c: not solA[r][c])
    iid=[[-1]*n for _ in range(n)]
    for i,cells in enumerate(comps):
        for r,c in cells:
            iid[r][c]=i
    return iid, comps

def render_solution(n, solA, hints):
    grid = [["A" if solA[r][c] else "X" for c in range(n)] for r in range(n)]
    for (r,c),v in hints.items():
        grid[r][c]=str(v)
    return grid

def puzzle_from_hints(n, hints):
    p=[["X"]*n for _ in range(n)]
    for (r,c),v in hints.items():
        p[r][c]=str(v)
    return p

# -------------------- Unique-by-construction family --------------------
# We use a "barcode" wall pattern that forces all non-wall cells to be isolated
# 1-cell islands, except for a few preselected 2-cell islands embedded in corridors.
# This makes the final wall placement unique given the numbers, and allows a
# lightweight exact enumeration over only those corridor choices.
#
# Construction:
# - Start with all walls A.
# - Carve a set of disjoint "island cells" that are separated by walls.
# - Ensure wall region is connected and no 2x2 all-wall (so we must carve
#   occasional holes in walls to break 2x2, which become forced islands).
#
# Since we want a proper puzzle with walls to place, we output only numbers,
# and the solver must decide which X cells are walls. Here, however, almost
# all cells are forced by the numeric islands: each number must match its island
# size; with many 1s, those cells must be islands, and surrounding must be walls
# to prevent adjacency; this heavily constrains the board.
#
# Then we run a small backtracking solver to confirm uniqueness (fast because
# most cells become forced quickly). No Z3.

def build_template(rng, n):
    # Start from checkerboard islands (forces separation), then add a few 2-islands.
    solA = [[True]*n for _ in range(n)]  # True means wall
    island_cells=set()
    # place base 1-islands on checkerboard of even parity
    for r in range(n):
        for c in range(n):
            if (r+c)%2==0:
                solA[r][c]=False
                island_cells.add((r,c))

    # add a few extra carved cells to eliminate 2x2 all-wall blocks:
    # With checkerboard carving, there is no 2x2 all-wall already. Good.
    # Ensure wall connectivity: checkerboard walls are connected for n>=5? Not always.
    # We'll add "bridges" in walls by turning some island cells into walls to connect wall components.
    # But turning an island cell into wall is allowed (it becomes wall), then that cell won't have a hint.
    # However puzzle grid uses X for blanks; we must still remain solvable.
    # We'll instead ensure wall connectivity by carving fewer islands: create a single connected wall backbone.
    #
    # New approach: begin with all walls, carve a connected "maze corridor" of islands (non-walls)
    # that is thin and separated, which keeps walls connected automatically.
    return None  # placeholder not used

def build_solution_family(rng):
    # Choose n and create a "wall snake" that is connected and 2x2-free,
    # then carve many isolated 1-islands in the remaining cells while keeping wall constraints.
    n = rng.choice([5, 6, 7])
    solA = [[False]*n for _ in range(n)]  # start as all island; we will place walls deterministically
    # Make walls on all odd rows (full), plus a single connector column to avoid 2x2:
    # Full odd rows create 2x2 walls if we add even-row connectors broadly. We keep connectors sparse.
    solA = [[False]*n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            solA[r][c]=False

    # Base wall: "zigzag stripes" leaving single-cell islands between walls
    # Put walls on all cells where r is odd, except alternating holes to avoid 2x2 and create forced structure
    for r in range(n):
        for c in range(n):
            if r % 2 == 1:
                # carve holes at every 2 columns on odd rows
                if c % 3 != 1:
                    solA[r][c] = True

    # Add a vertical wall on column 1 (with holes) to connect stripes
    for r in range(n):
        if r % 3 != 1:
            solA[r][1] = True

    # Ensure walls connected and 2x2-free by patching: remove walls that form 2x2, or add walls to connect.
    # Patch loop bounded.
    for _ in range(50):
        changed=False
        # break 2x2 all walls by flipping one cell to island
        for r in range(n-1):
            for c in range(n-1):
                if solA[r][c] and solA[r+1][c] and solA[r][c+1] and solA[r+1][c+1]:
                    # open one cell (prefer interior)
                    solA[r+1][c+1]=False
                    changed=True
        # If not connected, connect components by adding a short Manhattan bridge of walls
        if not walls_connected(solA, n):
            comps = comp_cells(n, lambda r,c: solA[r][c])
            if len(comps)>=2:
                a = comps[0][0]
                b = comps[1][0]
                ar,ac=a; br,bc=b
                # draw L-shaped bridge
                r=ar
                step = 1 if br>=ar else -1
                while r!=br:
                    solA[r][ac]=True
                    r+=step
                c=ac
                step = 1 if bc>=ac else -1
                while c!=bc:
                    solA[br][c]=True
                    c+=step
                solA[br][bc]=True
                changed=True
        if not changed:
            break

    if not no_2x2_walls(solA, n):
        return None
    if not walls_connected(solA, n):
        return None

    # Now islands are all non-wall components; place one hint per island with value = component size.
    _, comps = assign_island_ids(solA, n)
    if not comps:
        return None

    hints={}
    for comp in comps:
        pos = rng.choice(comp)
        hints[pos]=len(comp)

    return n, solA, hints

# -------------------- Fast backtracking solver for uniqueness --------------------

def solve_all(puzzle, limit=2):
    n=len(puzzle)
    hints={}
    for r in range(n):
        for c in range(n):
            if puzzle[r][c]!="X":
                hints[(r,c)] = int(puzzle[r][c])

    st=[[-1]*n for _ in range(n)]  # -1 unk, 0 island, 1 wall
    for (r,c) in hints:
        st[r][c]=0

    # ordering: most constrained first (near hints)
    cells=[(r,c) for r in range(n) for c in range(n) if (r,c) not in hints]
    def dist_to_hint(rc):
        r,c=rc
        return min(abs(r-hr)+abs(c-hc) for (hr,hc) in hints) if hints else 0
    cells.sort(key=dist_to_hint)

    def violates_2x2_partial():
        for r in range(n-1):
            for c in range(n-1):
                vals=[st[r][c],st[r+1][c],st[r][c+1],st[r+1][c+1]]
                if all(v==1 for v in vals):
                    return True
        return False

    def final_check():
        solA=[[st[r][c]==1 for c in range(n)] for r in range(n)]
        if not no_2x2_walls(solA,n): return False
        if not walls_connected(solA,n): return False
        iid, comps = assign_island_ids(solA,n)
        # each island exactly one hint and size matches
        for comp in comps:
            h=[cell for cell in comp if cell in hints]
            if len(h)!=1: return False
            if len(comp)!=hints[h[0]]: return False
        return True

    def partial_feasible():
        # quick bounds: for each hint, forced island component size cannot exceed clue
        forced = comp_cells(n, lambda r,c: st[r][c]==0)
        cid=[[-1]*n for _ in range(n)]
        for i,comp in enumerate(forced):
            for r,c in comp:
                cid[r][c]=i
        for (hr,hc),clue in hints.items():
            if cid[hr][hc]!=-1:
                if len(forced[cid[hr][hc]])>clue:
                    return False
        return True

    sols=[]
    idx=0

    def bt(k):
        nonlocal idx
        if len(sols)>=limit: return
        if violates_2x2_partial(): return
        if not partial_feasible(): return
        if k==len(cells):
            # assign any remaining unknown? none
            if final_check():
                sols.append([[st[r][c]==1 for c in range(n)] for r in range(n)])
            return
        r,c=cells[k]
        if st[r][c]!=-1:
            bt(k+1); return
        # heuristic: try wall first
        for val in (1,0):
            st[r][c]=val
            bt(k+1)
            st[r][c]=-1
            if len(sols)>=limit: return

    bt(0)
    return sols

# -------------------- rendering --------------------

def render_problem_zh(puzzle):
    n=len(puzzle)
    lines=[]
    lines.append("你正在解一道“筑岛围墙”（类似 Nurikabe）逻辑题。棋盘为 n×n 方格，部分格子给出数字提示，其余格子为空白（X）。")
    lines.append("")
    lines.append("规则：")
    lines.append("1）你需要在一些格子上建墙，墙格用 A 表示；未建墙且不含数字的岛格用 X 表示；数字格保留数字。")
    lines.append("2）所有非墙格会形成若干岛屿；每个岛屿必须恰好包含一个数字。")
    lines.append("3）每个岛屿的格子总数等于该岛屿中数字提示的数值。")
    lines.append("4）不同岛屿之间不能上下左右相邻（必须被墙隔开）。")
    lines.append("5）任意 2×2 小方块中不能四格都是墙 A。")
    lines.append("6）所有墙格 A 必须上下左右连通。")
    lines.append("")
    lines.append("请将需要建墙的格子替换为 A，并按要求输出最终矩阵：元素空格分隔，每行用逗号分隔，最外层用双中括号包裹。")
    lines.append("")
    lines.append("题目矩阵：")
    for row in puzzle:
        lines.append(" ".join(row))
    return "\n".join(lines)

def explanation_zh(solA, hints):
    n=len(solA)
    wall_comps = comp_cells(n, lambda r,c: solA[r][c])
    _, islands = assign_island_ids(solA,n)
    lines=[]
    lines.append("核对摘要：")
    lines.append(f"- 墙域连通分量数：{len(wall_comps)}（应为 1）。")
    lines.append(f"- 2×2 全墙：{'无' if no_2x2_walls(solA,n) else '有'}（应为 无）。")
    lines.append(f"- 岛屿数量：{len(islands)}（每个岛恰好一个数字，且大小等于数字）。")
    # show a few hint positions
    hs=sorted([(r,c,v) for (r,c),v in hints.items()])[:6]
    if hs:
        lines.append("- 部分提示（行,列,数值，1-based）：")
        for r,c,v in hs:
            lines.append(f"  ({r+1},{c+1},{v})")
    return "\n".join(lines)

# -------------------- main generator --------------------

def gen_one(rng, output_language="zh"):
    for _ in range(200):
        built = build_solution_family(rng)
        if built is None:
            continue
        n, solA, hints = built
        puzzle = puzzle_from_hints(n, hints)

        # Uniqueness check with fast backtracking
        sols = solve_all(puzzle, limit=2)
        if len(sols)!=1:
            continue
        if sols[0]!=solA:
            continue

        problem = render_problem_zh(puzzle)
        answer_grid = render_solution(n, solA, hints)
        answer = fmt_grid(answer_grid)
        expl = explanation_zh(solA, hints)
        return {"problem": problem, "answer": answer, "explanation": expl}
    raise RuntimeError("在采样上限内未生成到通过唯一性校验的题目。")

def main():
    data=json.loads(sys.stdin.read())
    seed=int(data["seed"])
    count=int(data["count"])
    output_language=data.get("output_language","zh")
    rng=random.Random(seed)

    items=[]
    seen=set()
    attempts=0
    while len(items)<count:
        attempts += 1
        if attempts > count*500:
            raise RuntimeError("失败/重复过多，无法生成足够题目。")
        obj=gen_one(rng, output_language=output_language)
        key=obj["problem"]
        if key in seen:
            continue
        seen.add(key)
        items.append(obj)

    sys.stdout.write(json.dumps(items, ensure_ascii=False))

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(str(e)+"\n")
        raise