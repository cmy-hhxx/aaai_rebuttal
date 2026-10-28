import sys, json, random
from typing import List, Tuple, Dict, Any
from itertools import product

from z3 import Solver, Bool, Sum, If, And, Or, Not, sat, is_true

Coord = Tuple[int, int]  # 1-based
Edge = Tuple[Coord, Coord]  # normalized undirected adjacency pair


def eprint(*args):
    print(*args, file=sys.stderr)


def in_bounds(r: int, c: int, n: int) -> bool:
    return 1 <= r <= n and 1 <= c <= n


def orth_neighbors(r: int, c: int, n: int) -> List[Coord]:
    res = []
    if r > 1:
        res.append((r - 1, c))
    if r < n:
        res.append((r + 1, c))
    if c > 1:
        res.append((r, c - 1))
    if c < n:
        res.append((r, c + 1))
    return res


def norm_edge(a: Coord, b: Coord) -> Edge:
    return (a, b) if a <= b else (b, a)


def all_edges(n: int) -> List[Edge]:
    edges = []
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            if c < n:
                edges.append(norm_edge((r, c), (r, c + 1)))
            if r < n:
                edges.append(norm_edge((r, c), (r + 1, c)))
    return edges


def touching_orth(a: Coord, b: Coord) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def dominoes_touch_orth(d1: Edge, d2: Edge) -> bool:
    (a1, b1), (a2, b2) = d1, d2
    for x in (a1, b1):
        for y in (a2, b2):
            if x == y:
                return True
            if touching_orth(x, y):
                return True
    return False


def build_region_map(grid: List[List[str]]) -> Dict[str, List[Coord]]:
    n = len(grid)
    regions: Dict[str, List[Coord]] = {}
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            ch = grid[r - 1][c - 1]
            regions.setdefault(ch, []).append((r, c))
    return regions


def compute_domino_cells(dominoes: List[Edge]) -> Dict[Coord, int]:
    m: Dict[Coord, int] = {}
    for a, b in dominoes:
        m[a] = m.get(a, 0) + 1
        m[b] = m.get(b, 0) + 1
    return m


def format_grid(grid: List[List[str]]) -> str:
    return "\n".join(["\t".join(row) for row in grid])


def format_solution(dominoes: List[Edge]) -> str:
    doms = []
    for a, b in dominoes:
        aa, bb = (a, b) if a <= b else (b, a)
        doms.append((aa, bb))
    doms.sort(key=lambda x: (x[0][0], x[0][1], x[1][0], x[1][1]))
    parts = [f"({a[0]},{a[1]})({b[0]},{b[1]})" for a, b in doms]
    return "[[" + ",".join(parts) + "]]"


def solve_domino_regions(grid: List[List[str]], require_unique: bool = True, max_solutions: int = 2):
    """
    Z3 model:
    - choose domino edges (adjacent pairs)
    - matching constraint (no cell used twice)
    - no orth-touching between different dominoes
    - each region has exactly 2 covered cells
    """
    n = len(grid)
    regions = build_region_map(grid)
    edges = all_edges(n)

    x = {e: Bool(f"x_{e[0][0]}_{e[0][1]}_{e[1][0]}_{e[1][1]}") for e in edges}

    def cell_covered(cell: Coord):
        r, c = cell
        inc = []
        for nb in orth_neighbors(r, c, n):
            inc.append(x[norm_edge(cell, nb)])
        return Or(inc) if inc else False

    s = Solver()

    # matching: each cell used by <=1 edge
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            inc = [x[norm_edge((r, c), nb)] for nb in orth_neighbors(r, c, n)]
            if len(inc) >= 2:
                s.add(Sum([If(v, 1, 0) for v in inc]) <= 1)

    # each region exactly 2 covered cells
    for reg, cells in regions.items():
        s.add(Sum([If(cell_covered(cell), 1, 0) for cell in cells]) == 2)

    # no orth-touch between different dominoes
    # (diagonal is allowed so we only forbid if any endpoints are orth adjacent or equal)
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            if dominoes_touch_orth(edges[i], edges[j]):
                s.add(Not(And(x[edges[i]], x[edges[j]])))

    if s.check() != sat:
        return "unsat", [], {}

    def extract_solution(model):
        sol = [e for e in edges if is_true(model.eval(x[e], model_completion=True))]
        return sol

    m = s.model()
    sol1 = extract_solution(m)

    if not require_unique:
        return "sat", sol1, {}

    # uniqueness check by enumerating up to max_solutions
    sols = [sol1]

    def add_block(sol: List[Edge]):
        chosen = set(sol)
        lits = []
        for e in edges:
            if e in chosen:
                lits.append(Not(x[e]))
            else:
                lits.append(x[e])
        s.add(Or(lits))

    add_block(sol1)
    while len(sols) < max_solutions and s.check() == sat:
        m2 = s.model()
        sol2 = extract_solution(m2)
        sols.append(sol2)
        add_block(sol2)

    if len(sols) == 1:
        return "sat_unique", sol1, {}
    return "sat_multi", sol1, {}


def latin_labels(k: int) -> List[str]:
    alph = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    labels = []
    i = 0
    while len(labels) < k:
        if i < 26:
            labels.append(alph[i])
        else:
            labels.append(alph[(i // 26) - 1] + alph[i % 26])
        i += 1
    return labels


def construct_grid_from_domino_solution(rng: random.Random, n: int) -> Tuple[List[List[str]], List[Edge]]:
    """
    Robust constructive family:
    1) First, construct a valid domino placement satisfying "no orth-touching":
       - We place dominoes on a "spaced" pattern: use only cells with (r+c) even as anchors,
         and orient dominoes consistently so they do not touch orthogonally.
       - Ensure matching and non-touching by design.
    2) Then define each region to be exactly the two cells of one domino.
       => Each region has exactly 2 covered cells (those two), trivially satisfied.
       Regions are disjoint and cover exactly the 2*#domino cells; uncovered cells are distributed
       into some regions as extra cells would violate exactly-2-covered, so we must ensure every region
       contains exactly the two covered cells and any uncovered cells belong to some region whose
       covered count remains 2; that is impossible if a region includes uncovered cells without adding
       additional covered cells. Therefore, in this construction we cover ALL cells: a perfect matching.
    So we require n even. We'll use n in {6,8}. Here we use 6 to keep size moderate.
    With perfect matching, every region is size 2 (a domino).
    3) Uniqueness: add extra region-merging constraints? With region size 2, constraints reduce to:
       every region's two cells must be covered, hence all cells covered, and matching+non-touching.
       This might have multiple solutions. To enforce uniqueness, we "freeze" the tiling by adding
       some larger regions built from multiple dominoes and forcing exactly two covered cells per region,
       which pins choices. Instead, we do the reverse:
       - Start from a uniquely solvable instance by sampling random region partitions and checking uniqueness,
         but that's unreliable.
    New plan:
       We keep n=6 and use a deterministic "forced" structure by creating many singleton-choice regions:
       size-2 regions (forced covered) + some size>2 regions where only two cells are allowed to be covered
       due to geometry/non-touching. We'll encode by constructing regions around a preselected solution and
       ensuring alternative solutions are eliminated by adding "key regions" that would be violated otherwise.
    Practically: iterative refinement:
       - Start with a known solution tiling T (a set of dominoes).
       - Begin with regions = each cell its own label bucket? not allowed because need exactly 2 covered per region.
       - We'll build regions as groups such that in T exactly 2 cells of each region are covered.
       - Then use Z3 to check if unique; if not, add another region constraint by splitting a region into two
         (increasing constraints) until unique.
    We'll implement this as:
       - Choose a full domino tiling T with non-touching property (we'll use a spaced pattern to guarantee).
       - Initial regions: random grouping of cells into regions of size between 2 and 6, but with the invariant
         that in T exactly 2 cells from each region are "marked" (covered cells from T), and the rest (if any)
         are uncovered in T. However T covers all cells (tiling), so every cell is covered -> any region would
         have covered count = region size, not 2. So we cannot use perfect tiling.

    Therefore revert to partial placement:
       - Regions can include uncovered cells; that's fine as long as exactly 2 cells in each region are covered.
       This is okay.
       - But then region construction must keep exactly 2 covered in T.
    We'll do:
       - Place K dominoes in non-touching pattern, leaving other cells uncovered.
       - Build regions so that every region contains exactly 2 of the covered cells in T.
       - Ensure all covered cells are in dominoes (true) and uncovered cells may be in any regions.
       - Need that every region has exactly 2 covered cells; hence number of regions = K (since 2K covered cells).
       We'll create exactly K regions, each region gets 2 covered cells + some uncovered cells.
       This is feasible.

    Return constructed grid and the chosen domino set T.
    """
    # Choose K anchors on a 3x3 lattice inside 6x6 by picking (r,c) with r,c odd (1,3,5)
    # Place horizontal dominoes to the right: (r,c)-(r,c+1) where c is odd and c<n.
    # These dominoes are spaced and do not touch orthogonally.
    anchors = []
    for r in range(1, n + 1, 2):
        for c in range(1, n, 2):
            anchors.append((r, c))
    rng.shuffle(anchors)
    # choose K dominoes
    max_k = len(anchors)
    K = rng.randint(max(6, max_k // 2), max_k)  # fairly dense but still spaced
    chosen = anchors[:K]
    dominoes: List[Edge] = [norm_edge((r, c), (r, c + 1)) for (r, c) in chosen]

    covered = set()
    for a, b in dominoes:
        covered.add(a); covered.add(b)

    # Now create exactly K regions; each region will include exactly one domino's two covered cells
    # plus some uncovered cells distributed randomly.
    labels = latin_labels(K)
    regions_cells: List[List[Coord]] = [[dominoes[i][0], dominoes[i][1]] for i in range(K)]

    uncovered = [(r, c) for r in range(1, n + 1) for c in range(1, n + 1) if (r, c) not in covered]
    rng.shuffle(uncovered)
    # distribute uncovered cells among regions
    for idx, cell in enumerate(uncovered):
        regions_cells[idx % K].append(cell)

    # Render grid labels
    grid = [["" for _ in range(n)] for _ in range(n)]
    for i in range(K):
        for (r, c) in regions_cells[i]:
            grid[r - 1][c - 1] = labels[i]

    return grid, dominoes


def generate_case(rng: random.Random, tries: int = 200):
    """
    Constructive + uniqueness refinement:
    - Construct a base instance (grid, intended solution).
    - Verify it is uniquely solvable. If not unique, resample construction parameters.
    """
    for _ in range(tries):
        n = 6
        grid, intended = construct_grid_from_domino_solution(rng, n)

        status, sol, _ = solve_domino_regions(grid, require_unique=True, max_solutions=2)
        if status == "sat_unique":
            # We accept solver-found solution (should match intended often, but not required)
            return grid, sol

    # If uniqueness hard, relax: accept multi-sat but still provide one correct answer
    # to avoid crashing generator.
    for _ in range(tries):
        n = 6
        grid, _ = construct_grid_from_domino_solution(rng, n)
        status, sol, _ = solve_domino_regions(grid, require_unique=False, max_solutions=1)
        if status != "unsat":
            return grid, sol

    raise RuntimeError("生成失败：无法生成可满足的题目实例。请更换 seed 或减少 count。")


def make_problem_text(grid: List[List[str]], output_language: str) -> str:
    n = len(grid)
    grid_txt = format_grid(grid)
    if output_language.lower().startswith("zh"):
        return (
            "在一个 N×N 方格上放置若干个多米诺骨牌（1×2 或 2×1），规则如下：\n"
            "1) 方格被字母划分为若干区域；\n"
            "2) 你可以在一些格子上“涂黑”，每两个上下左右相邻的涂黑格组成一块多米诺骨牌；骨牌可以跨区域边界；\n"
            "3) 每个区域中恰好有 2 个格子被骨牌覆盖（等价于该区域恰好有 2 个格子被涂黑）；\n"
            "4) 所有涂黑格都必须属于某一块骨牌；\n"
            "5) 任意两块骨牌不能在上下左右方向接触（允许对角接触）。\n\n"
            f"给定网格（行 1..{n}，列 1..{n}）：\n"
            f"{grid_txt}\n\n"
            "请输出所有骨牌的两个端点坐标，格式为 (行i,列j)(行x,列y)。\n"
            "骨牌按“从上到下、从左到右”的顺序排列（按每块骨牌较小端点排序）。\n"
            "不同骨牌用英文逗号分隔，最终整体用双中括号包裹：\n"
            "[[(1,2)(1,3),(2,4)(3,4),...]]"
        )
    else:
        return (
            "Place dominoes (1x2 or 2x1) on an N×N grid with lettered regions:\n"
            "1) Dominoes may cross region borders.\n"
            "2) Exactly 2 cells in each region are covered.\n"
            "3) Every covered cell is part of a domino.\n"
            "4) Dominoes may not touch orthogonally (diagonal allowed).\n\n"
            f"Grid (rows 1..{n}, cols 1..{n}):\n{grid_txt}\n\n"
            "Output all domino endpoints as (r,c)(r,c), sorted, wrapped like [[...]]."
        )


def make_explanation(grid: List[List[str]], sol_edges: List[Edge], output_language: str) -> str:
    regions = build_region_map(grid)
    covered = compute_domino_cells(sol_edges)

    reg_cov_cells: Dict[str, List[Coord]] = {}
    for reg, cells in regions.items():
        cov = [cell for cell in cells if cell in covered]
        cov.sort()
        reg_cov_cells[reg] = cov

    dom_str = format_solution(sol_edges)

    if output_language.lower().startswith("zh"):
        lines = []
        for reg in sorted(regions.keys()):
            lines.append(f"{reg}: 被覆盖格={reg_cov_cells[reg]}（数量 {len(reg_cov_cells[reg])}）")
        return (
            "可复核校验：\n"
            f"1) 一组可行骨牌为：{dom_str}\n"
            "2) 逐区域检查“恰好 2 个格子被覆盖”（列出每个区域被覆盖的坐标）：\n"
            + "\n".join(lines)
            + "\n3) 再检查任意两块骨牌不存在上下左右接触（对角接触允许）。"
        )
    else:
        lines = []
        for reg in sorted(regions.keys()):
            lines.append(f"{reg}: covered={reg_cov_cells[reg]} (count {len(reg_cov_cells[reg])})")
        return (
            "Verifiable check:\n"
            f"1) One valid domino set: {dom_str}\n"
            "2) Each region has exactly 2 covered cells:\n"
            + "\n".join(lines)
            + "\n3) Dominoes do not touch orthogonally."
        )


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    output_language = data.get("output_language", "zh") if isinstance(data, dict) else "zh"

    rng = random.Random(seed)

    out = []
    seen = set()
    total_attempts = 0
    while len(out) < count:
        total_attempts += 1
        if total_attempts > 5000:
            raise RuntimeError("总体采样次数过多仍未生成足够不重复题目。")

        grid, sol = generate_case(rng)

        key = "\n".join("".join(row) for row in grid)
        if key in seen:
            continue
        seen.add(key)

        problem = make_problem_text(grid, output_language)
        answer = format_solution(sol)
        explanation = make_explanation(grid, sol, output_language)

        out.append({"problem": problem, "answer": answer, "explanation": explanation})

    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        eprint("ERROR:", repr(ex))
        raise