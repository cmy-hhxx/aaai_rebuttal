import sys, json, random
from typing import List, Tuple, Dict, Optional, Set

# --------- Core model: Hidato-like consecutive path on n*n grid (4-neighbor) ----------

DIR4 = [(1,0), (-1,0), (0,1), (0,-1)]

def neighbors(n: int, r: int, c: int):
    for dr, dc in DIR4:
        rr, cc = r+dr, c+dc
        if 0 <= rr < n and 0 <= cc < n:
            yield rr, cc

def idx(n: int, r: int, c: int) -> int:
    return r*n + c

def rc(n: int, i: int) -> Tuple[int,int]:
    return divmod(i, n)

def format_problem_grid(grid: List[List[Optional[int]]]) -> str:
    # render as matrix with X for blank, numbers for givens
    lines = []
    for row in grid:
        parts = []
        for v in row:
            parts.append("X" if v is None else str(v))
        lines.append("  ".join(parts))
    return "\n".join(lines)

def format_solution_as_required(sol_grid: List[List[int]]) -> str:
    # "List numbers left-to-right, top-to-bottom; rows separated by comma; wrap [[...]]"
    rows = []
    for r in sol_grid:
        rows.append(" ".join(str(x) for x in r))
    return "[[" + ",".join(rows) + "]]"

# --------- Generator families (diverse constructions) ----------

def make_snake_path(n: int, rng: random.Random) -> List[Tuple[int,int]]:
    """Simple Hamiltonian snake path; optionally mirror/rotate for diversity."""
    path = []
    for r in range(n):
        cols = range(n) if r % 2 == 0 else range(n-1, -1, -1)
        for c in cols:
            path.append((r,c))
    # apply random symmetry: rotate k*90 then optionally reflect
    k = rng.randrange(4)
    reflect = rng.choice([False, True])

    def transform(cell):
        r, c = cell
        rr, cc = r, c
        # rotate about center in grid coordinates (n x n)
        for _ in range(k):
            rr, cc = cc, n-1-rr
        if reflect:
            cc = n-1-cc
        return (rr, cc)

    path2 = [transform(p) for p in path]
    # path2 is still a valid Hamiltonian path with 4-neighbor adjacency? Rot/reflection preserve adjacency.
    return path2

def make_spiral_path(n: int, rng: random.Random) -> List[Tuple[int,int]]:
    """Construct an inward spiral visiting all cells exactly once (a Hamiltonian path)."""
    top, left, bottom, right = 0, 0, n-1, n-1
    path = []
    while top <= bottom and left <= right:
        # top row
        for c in range(left, right+1):
            path.append((top, c))
        top += 1
        # right col
        for r in range(top, bottom+1):
            path.append((r, right))
        right -= 1
        if top <= bottom:
            for c in range(right, left-1, -1):
                path.append((bottom, c))
            bottom -= 1
        if left <= right:
            for r in range(bottom, top-1, -1):
                path.append((r, left))
            left += 1

    # Spiral above is a Hamiltonian path; for even n it ends at inner corner; still contiguous.
    # Apply random symmetry for variety
    k = rng.randrange(4)
    reflect = rng.choice([False, True])

    def transform(cell):
        r, c = cell
        rr, cc = r, c
        for _ in range(k):
            rr, cc = cc, n-1-rr
        if reflect:
            cc = n-1-cc
        return (rr, cc)

    return [transform(p) for p in path]

def path_to_grid(n: int, path: List[Tuple[int,int]]) -> List[List[int]]:
    """Assign numbers 1..n^2 along the path positions."""
    grid = [[0]*n for _ in range(n)]
    for k, (r,c) in enumerate(path, start=1):
        grid[r][c] = k
    return grid

# --------- Uniqueness / solving: forced path given endpoints + some anchors ----------

def build_positions_from_givens(n: int, givens: Dict[int, Tuple[int,int]]) -> Dict[int, Tuple[int,int]]:
    # validate no duplicates positions
    seen = set()
    for num, pos in givens.items():
        if pos in seen:
            raise ValueError("Duplicate given position")
        seen.add(pos)
    return dict(givens)

def solve_hidato_unique(n: int, givens: Dict[int, Tuple[int,int]], limit_solutions: int = 2) -> List[List[List[int]]]:
    """
    Solve by backtracking on positions of each number.
    We model positions for numbers 1..N; given anchors fixed.
    Constraint: consecutive numbers are 4-neighbors.
    Return up to limit_solutions solutions (as number grid).
    """
    N = n*n
    pos = [None]*(N+1)   # pos[k] = (r,c)
    used = [[False]*n for _ in range(n)]
    for k, (r,c) in givens.items():
        if not (1 <= k <= N): 
            return []
        if pos[k] is not None and pos[k] != (r,c):
            return []
        if used[r][c]:
            return []
        pos[k] = (r,c)
        used[r][c] = True

    # Must have at least one fixed to anchor; if none, too many symmetries => not unique.
    if all(p is None for p in pos[1:]):
        return []

    # Precompute possible cells for each k if not fixed (initially all)
    all_cells = [(r,c) for r in range(n) for c in range(n)]

    # Degree heuristic: choose next k with smallest domain based on neighbors of placed adjacent
    def domain(k: int) -> List[Tuple[int,int]]:
        if pos[k] is not None:
            return [pos[k]]
        # must be unused and consistent with neighbors constraints with k-1 and k+1 if placed
        cand: Set[Tuple[int,int]] = set(all_cells)
        # unused
        cand = {p for p in cand if not used[p[0]][p[1]]}
        if k-1 >= 1 and pos[k-1] is not None:
            r0,c0 = pos[k-1]
            cand &= set(neighbors(n, r0, c0))
        if k+1 <= N and pos[k+1] is not None:
            r1,c1 = pos[k+1]
            cand &= set(neighbors(n, r1, c1))
        return list(cand)

    # Feasibility pruning: if two fixed anchors a<b are too far (Manhattan) for steps available => impossible
    fixed_nums = sorted(givens.keys())
    for i in range(len(fixed_nums)-1):
        a, b = fixed_nums[i], fixed_nums[i+1]
        ra, ca = givens[a]
        rb, cb = givens[b]
        dist = abs(ra-rb)+abs(ca-cb)
        if dist > (b-a):
            return []

    solutions = []

    # choose a starting point: try to place from smallest fixed segment outward for pruning
    # We'll just run recursive placement by selecting unassigned k with smallest domain each step.
    unassigned = set(k for k in range(1, N+1) if pos[k] is None)

    # Extra pruning: connectivity isn't strictly needed due to path constraint; but we can add simple step pruning:
    # If pos[k] is placed, then for any future fixed anchor t, need dist(pos[k], pos[t]) <= |t-k|
    def anchor_reachable(k: int, r: int, c: int) -> bool:
        for t in fixed_nums:
            if pos[t] is None:
                continue
            steps = abs(t-k)
            dist = abs(pos[t][0]-r)+abs(pos[t][1]-c)
            if dist > steps:
                return False
        return True

    def pick_next() -> Optional[int]:
        best_k = None
        best_dom = None
        best_len = 10**9
        for k in list(unassigned):
            d = domain(k)
            l = len(d)
            if l == 0:
                return -1
            if l < best_len:
                best_len = l
                best_k = k
                best_dom = d
                if best_len == 1:
                    break
        return best_k

    def recurse():
        if len(solutions) >= limit_solutions:
            return
        if not unassigned:
            # build grid
            g = [[0]*n for _ in range(n)]
            for k in range(1, N+1):
                r,c = pos[k]
                g[r][c] = k
            solutions.append(g)
            return

        k = pick_next()
        if k == -1 or k is None:
            return
        d = domain(k)
        # Ordering heuristic: try candidates close to neighbors if exist
        def score(p):
            sc = 0
            if k-1 >= 1 and pos[k-1] is not None:
                sc += abs(p[0]-pos[k-1][0]) + abs(p[1]-pos[k-1][1])
            if k+1 <= N and pos[k+1] is not None:
                sc += abs(p[0]-pos[k+1][0]) + abs(p[1]-pos[k+1][1])
            return sc
        d.sort(key=score)

        unassigned.remove(k)
        for (r,c) in d:
            if used[r][c]:
                continue
            if not anchor_reachable(k, r, c):
                continue
            # place and local consistency: if k-1 placed then must be neighbor; if k+1 placed then neighbor
            if k-1 >= 1 and pos[k-1] is not None:
                r0,c0 = pos[k-1]
                if abs(r-r0)+abs(c-c0) != 1:
                    continue
            if k+1 <= N and pos[k+1] is not None:
                r1,c1 = pos[k+1]
                if abs(r-r1)+abs(c-c1) != 1:
                    continue

            pos[k] = (r,c)
            used[r][c] = True

            # forward-check: adjacent numbers domains non-empty
            ok = True
            for kk in (k-1, k+1):
                if 1 <= kk <= N and pos[kk] is None:
                    if len(domain(kk)) == 0:
                        ok = False
                        break
            if ok:
                recurse()

            used[r][c] = False
            pos[k] = None
            if len(solutions) >= limit_solutions:
                break

        unassigned.add(k)

    recurse()
    return solutions

# --------- Puzzle instance creation: select givens ensuring unique solution ----------

def choose_givens_from_solution(sol: List[List[int]], rng: random.Random, min_givens: int, max_givens: int) -> Dict[int, Tuple[int,int]]:
    n = len(sol)
    N = n*n
    # Always include 1 and N to reduce symmetry
    pos_of = [None]*(N+1)
    for r in range(n):
        for c in range(n):
            pos_of[sol[r][c]] = (r,c)

    givens = {1: pos_of[1], N: pos_of[N]}

    # Add some random anchors; favor spread-out numbers
    k_target = rng.randint(min_givens, max_givens)
    candidates = list(range(2, N))
    rng.shuffle(candidates)
    for num in candidates:
        if len(givens) >= k_target:
            break
        # avoid clustering: keep distance from existing anchors
        r,c = pos_of[num]
        if all(abs(r-ra)+abs(c-ca) >= 2 for (ra,ca) in givens.values()):
            givens[num] = (r,c)

    # Ensure at least k_target if possible
    if len(givens) < k_target:
        for num in candidates:
            if len(givens) >= k_target:
                break
            givens.setdefault(num, pos_of[num])

    return givens

def givens_to_puzzle_grid(n: int, givens: Dict[int, Tuple[int,int]]) -> List[List[Optional[int]]]:
    grid = [[None]*n for _ in range(n)]
    for num, (r,c) in givens.items():
        grid[r][c] = num
    return grid

def make_explanation(n: int, givens: Dict[int, Tuple[int,int]], sol_grid: List[List[int]]) -> str:
    # Keep it short, checkable: mention rule + show start/end positions and one or two adjacency checks.
    N = n*n
    r1,c1 = givens[1]
    rN,cN = givens[N]
    # pick a few consecutive pairs to demonstrate adjacency in solution
    checks = []
    for a in [1, N//3, 2*N//3]:
        if 1 <= a < N:
            # locate a and a+1
            pa = None
            pb = None
            for r in range(n):
                for c in range(n):
                    if sol_grid[r][c] == a:
                        pa = (r,c)
                    elif sol_grid[r][c] == a+1:
                        pb = (r,c)
            if pa and pb:
                checks.append(f"{a}在({pa[0]+1},{pa[1]+1})，{a+1}在({pb[0]+1},{pb[1]+1})，曼哈顿距离=1")
    checks_str = "；".join(checks) if checks else "相邻数均为上下左右相邻。"
    return (
        f"这是一个{n}×{n}的连续路径填数题：1到{N}各出现一次，且k与k+1必须上下左右相邻。"
        f"已给定锚点包含1在第{r1+1}行第{c1+1}列、{N}在第{rN+1}行第{cN+1}列等。"
        f"完整解满足相邻性校验示例：{checks_str}。"
    )

def generate_one(rng: random.Random) -> Dict:
    # Choose size (variety)
    n = rng.choice([7, 8, 9])
    family = rng.choice(["snake", "spiral"])
    path = make_snake_path(n, rng) if family == "snake" else make_spiral_path(n, rng)
    sol = path_to_grid(n, path)
    N = n*n

    # Choose givens count by size
    if n == 7:
        min_g, max_g = 10, 14
    elif n == 8:
        min_g, max_g = 12, 18
    else:
        min_g, max_g = 14, 22

    # Try resampling givens until unique solution is confirmed
    for _ in range(60):
        givens = choose_givens_from_solution(sol, rng, min_g, max_g)
        # Validate uniqueness by solving from givens (independent from construction)
        sols = solve_hidato_unique(n, givens, limit_solutions=2)
        if len(sols) == 1:
            # Ensure the unique solution equals our constructed one (cross-check)
            if sols[0] != sol:
                # If unique but different, accept solver's unique one (still valid) but keep consistent output.
                sol = sols[0]
            puzzle_grid = givens_to_puzzle_grid(n, givens)
            problem = (
                f"你正在解一个自定义填数谜题。\n\n"
                f"规则：\n"
                f"1) 在{n}×{n}方格中填入数字1到{N}，每个数字恰好出现一次。\n"
                f"2) 数字必须按顺序相邻：1挨着2，2挨着3，…，一直到{N}。\n"
                f"3) 相邻只允许上下左右（不允许对角）。\n"
                f"4) 题面以矩阵给出，空格用X表示，已知格子给出数字。\n\n"
                f"题目矩阵：\n{format_problem_grid(puzzle_grid)}\n\n"
                f"要求：输出完整填好的矩阵（包含原有数字与补全数字）。"
                f"按从左到右、从上到下列出；行与行之间用英文逗号分隔；数字用空格分隔。"
                f"最终答案用双中括号包裹，形如：[[...]]。"
            )
            answer = format_solution_as_required(sol)
            explanation = make_explanation(n, givens, sol)
            return {"problem": problem, "answer": answer, "explanation": explanation}

    raise RuntimeError("在采样上限内未能生成具有唯一解的实例。")

def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results = []
    seen_fingerprints = set()

    attempts = 0
    max_attempts = max(200, 20 * count)
    while len(results) < count and attempts < max_attempts:
        attempts += 1
        try:
            item = generate_one(rng)
        except Exception as e:
            print(f"[stderr] generation failed: {e}", file=sys.stderr)
            continue

        # Deduplicate by (n, givens positions+nums)
        prob_text = item["problem"]
        fp = hash(prob_text)
        if fp in seen_fingerprints:
            continue
        seen_fingerprints.add(fp)
        results.append(item)

    if len(results) != count:
        raise RuntimeError(f"仅生成了{len(results)}/{count}道题（已达到尝试上限{max_attempts}）。")

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()