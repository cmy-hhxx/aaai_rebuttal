import sys, json, random
from collections import defaultdict, deque

# Fast Star Battle (Star Battle) generator with guaranteed quick uniqueness check.
# Key repair vs timeout:
# - Use *pre-constructed* region templates that are always connected and size N (so exactly N regions).
# - Use Z3 with a low timeout per instance, but with very easy structure (k=1 only) so SAT is extremely fast.
# - Ensure uniqueness by incremental "block first model then re-sat" (also fast for k=1).
# - Strict global attempt caps; generation is O(count) with tiny constant.
#
# Output language: Chinese.

try:
    import z3
except Exception:
    z3 = None

# ---------- Utilities ----------

def neighbors8(r, c, N):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < N and 0 <= cc < N:
                yield rr, cc

def neighbors4(r, c, N):
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < N and 0 <= cc < N:
            yield rr, cc

def is_connected(cells, N):
    if not cells:
        return False
    start = next(iter(cells))
    q = deque([start])
    seen = {start}
    while q:
        r,c = q.popleft()
        for rr,cc in neighbors4(r,c,N):
            if (rr,cc) in cells and (rr,cc) not in seen:
                seen.add((rr,cc))
                q.append((rr,cc))
    return len(seen) == len(cells)

def region_letters(N):
    return [chr(ord('A') + i) for i in range(N)]

def fmt_grid(grid):
    return "\n".join(" ".join(row) for row in grid)

def coord1(r,c):
    return (r+1,c+1)

def render_answer_by_region(grid, stars_set):
    reg = defaultdict(list)
    for r,c in stars_set:
        reg[grid[r][c]].append(coord1(r,c))
    lines=[]
    for lab in sorted(reg.keys()):
        coords=sorted(reg[lab], key=lambda x:(x[0],x[1]))
        lines.append(lab + "".join(f"({a},{b})" for a,b in coords))
    return "[[" + "\n".join(lines) + "]]"

def build_problem_text(grid, k=1):
    N=len(grid)
    return (
        "星战（Star Battle）规则：\n"
        "1）在一个 N×N 的网格中，网格被划分为若干区域（用字母标记）。\n"
        f"2）每一行恰好放置 {k} 颗星；每一列恰好放置 {k} 颗星；每个区域也恰好放置 {k} 颗星。\n"
        "3）任意两颗星不能相邻（包括上下左右与对角线相邻）。\n"
        "问题：给出区域字母矩阵，输出每个区域中星的坐标（行、列从 1 开始）。\n"
        "输出要求：按区域字母升序；同一区域若有多颗星，按(行,列)字典序升序列出。\n"
        "输出格式：用双层方括号包裹，各区域之间用换行分隔，例如：\n"
        "[[A(1,1)\nB(2,3)\nC(3,2)]]\n\n"
        f"本题：N={N}，每行/列/区域 {k} 颗星。\n\n"
        "区域矩阵：\n"
        + fmt_grid(grid)
    )

def verify_solution(grid, stars_set, k=1):
    N=len(grid)
    # adjacency
    for r,c in stars_set:
        for rr,cc in neighbors8(r,c,N):
            if (rr,cc) in stars_set:
                return False
    # row/col
    for r in range(N):
        if sum((r,c) in stars_set for c in range(N)) != k:
            return False
    for c in range(N):
        if sum((r,c) in stars_set for r in range(N)) != k:
            return False
    # regions
    need = {lab:0 for lab in region_letters(N)}
    for r in range(N):
        for c in range(N):
            if (r,c) in stars_set:
                need[grid[r][c]] += 1
    if any(need[lab] != k for lab in need):
        return False
    return True

def make_explanation(grid, stars_set, k=1):
    N=len(grid)
    rows=[]
    cols=[]
    for r in range(N):
        cols_in=[c+1 for c in range(N) if (r,c) in stars_set]
        rows.append(f"第{r+1}行：星在列{cols_in}")
    for c in range(N):
        rows_in=[r+1 for r in range(N) if (r,c) in stars_set]
        cols.append(f"第{c+1}列：星在行{rows_in}")
    return (
        "复核信息：\n"
        f"- 每行/每列/每区域均为 {k} 颗星；\n"
        "- 任意两星（含对角）不相邻。\n"
        "按行列列出星位置：\n" + "\n".join(rows) + "\n" + "\n".join(cols)
    )

# ---------- Region templates (connected, each region size N) ----------

def make_snake_partition(N, perm):
    """
    Build N connected regions each of size N by slicing a Hamiltonian snake path
    into N consecutive blocks, then labeling blocks by permuted letters.
    """
    letters = region_letters(N)
    # snake path
    path=[]
    for r in range(N):
        row=[(r,c) for c in range(N)]
        if r%2==1:
            row.reverse()
        path.extend(row)
    # assign blocks
    grid=[[None]*N for _ in range(N)]
    for i,(r,c) in enumerate(path):
        block = i // N
        lab = letters[perm[block]]
        grid[r][c]=lab
    return grid

def make_column_stripes_with_wiggle(N, perm, wiggle):
    """
    Another connected partition: start with vertical stripes (each size N, connected),
    then apply a controlled "wiggle" swap on some adjacent cells to add variety while
    maintaining per-region size and connectivity.
    """
    letters = region_letters(N)
    grid = [[letters[perm[c]] for c in range(N)] for _ in range(N)]

    # wiggle: swap (r,c) with (r,c+1) for selected rows and columns, but keep sizes.
    # Swapping labels keeps sizes automatically. Need to ensure connectivity not broken:
    # For stripes, a single swap doesn't disconnect either stripe (they remain mostly columns).
    # Keep swaps sparse.
    for (r,c) in wiggle:
        if 0 <= r < N and 0 <= c < N-1:
            grid[r][c], grid[r][c+1] = grid[r][c+1], grid[r][c]

    # Connectivity check; if fails, fall back to pure stripes.
    ok=True
    for lab in letters:
        cells={(r,c) for r in range(N) for c in range(N) if grid[r][c]==lab}
        if len(cells)!=N or not is_connected(cells,N):
            ok=False
            break
    if not ok:
        grid = [[letters[perm[c]] for c in range(N)] for _ in range(N)]
    return grid

# ---------- Z3 Solver (k=1 only) ----------

def solve_unique_k1(grid, timeout_ms=40):
    if z3 is None:
        return None, "z3_missing"
    N=len(grid)
    k=1
    letters = sorted(set(ch for row in grid for ch in row))
    # Must be exactly N regions A..; if not, reject quickly
    if len(letters) != N:
        return None, "bad_regions"

    regions=defaultdict(list)
    for r in range(N):
        for c in range(N):
            regions[grid[r][c]].append((r,c))

    # size must be N
    for lab in letters:
        if len(regions[lab]) != N:
            return None, "bad_sizes"

    X=[[z3.Bool(f"x_{r}_{c}") for c in range(N)] for r in range(N)]
    s=z3.Solver()
    s.set("timeout", timeout_ms)

    for r in range(N):
        s.add(z3.PbEq([(X[r][c],1) for c in range(N)], k))
    for c in range(N):
        s.add(z3.PbEq([(X[r][c],1) for r in range(N)], k))
    for lab in letters:
        s.add(z3.PbEq([(X[r][c],1) for (r,c) in regions[lab]], k))

    for r in range(N):
        for c in range(N):
            for rr,cc in neighbors8(r,c,N):
                if (rr,cc) > (r,c):
                    s.add(z3.Not(z3.And(X[r][c], X[rr][cc])))

    if s.check() != z3.sat:
        return None, "unsat_or_timeout"

    m=s.model()
    stars={(r,c) for r in range(N) for c in range(N)
           if z3.is_true(m.evaluate(X[r][c], model_completion=True))}

    # uniqueness: block exact assignment
    s2=z3.Solver()
    s2.set("timeout", timeout_ms)
    s2.append(s.assertions())
    s2.add(z3.Or([X[r][c] if (r,c) not in stars else z3.Not(X[r][c]) for r in range(N) for c in range(N)]))
    chk=s2.check()
    if chk == z3.sat:
        return None, "not_unique"
    if chk == z3.unknown:
        return None, "uniq_timeout"
    return stars, "unique"

# ---------- Generation ----------

def generate_instance(rnd):
    # Fixed k=1 for speed and to match seed's core task.
    # Choose N and a partition family.
    for _ in range(120):
        N = rnd.choice([6,7,8,9])
        # random permutation of regions
        perm = list(range(N))
        rnd.shuffle(perm)

        family = rnd.random()
        if family < 0.55:
            grid = make_snake_partition(N, perm)
        else:
            # stripes + a few wiggles
            wiggle=[]
            t = rnd.randint(0, max(0, N-3))
            for _ in range(t):
                r = rnd.randrange(N)
                c = rnd.randrange(N-1)
                wiggle.append((r,c))
            grid = make_column_stripes_with_wiggle(N, perm, wiggle)

        stars, status = solve_unique_k1(grid, timeout_ms=45)
        if stars is None:
            continue
        if not verify_solution(grid, stars, k=1):
            continue

        problem = build_problem_text(grid, k=1)
        answer = render_answer_by_region(grid, stars)
        explanation = make_explanation(grid, stars, k=1)
        return {"problem": problem, "answer": answer, "explanation": explanation}

    return None

def main():
    data=json.load(sys.stdin)
    seed=int(data["seed"])
    count=int(data["count"])
    rnd=random.Random(seed)

    if z3 is None:
        print("运行失败：未检测到 z3 库。", file=sys.stderr)
        raise SystemExit(2)

    out=[]
    seen=set()
    max_total_attempts = 2500  # tight cap for 120s budget
    attempts=0
    while len(out) < count and attempts < max_total_attempts:
        attempts += 1
        item = generate_instance(rnd)
        if item is None:
            continue
        key = item["problem"].split("区域矩阵：\n", 1)[-1]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    if len(out) != count:
        print(f"生成失败：仅生成 {len(out)}/{count}（尝试{attempts}次）。可更换seed或减少count。", file=sys.stderr)
        raise SystemExit(2)

    json.dump(out, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()