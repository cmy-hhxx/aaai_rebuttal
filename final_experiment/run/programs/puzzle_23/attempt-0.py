import sys, json, random
from typing import List, Tuple, Dict, Any, Optional
from itertools import product

# We use z3 as allowed
from z3 import (
    Solver, Bool, Sum, If, And, Or, Not, Implies, sat, is_true
)

Coord = Tuple[int, int]  # (r,c) 1-based for rendering
Edge = Tuple[Coord, Coord]  # undirected adjacency pair, stored with sorted endpoints


def eprint(*args):
    print(*args, file=sys.stderr)


def rc_to_idx(r: int, c: int, n: int) -> int:
    return (r - 1) * n + (c - 1)


def idx_to_rc(idx: int, n: int) -> Coord:
    return (idx // n + 1, idx % n + 1)


def in_bounds(r: int, c: int, n: int) -> bool:
    return 1 <= r <= n and 1 <= c <= n


def norm_edge(a: Coord, b: Coord) -> Edge:
    return (a, b) if a <= b else (b, a)


def orth_neighbors(r: int, c: int, n: int) -> List[Coord]:
    res = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        rr, cc = r + dr, c + dc
        if in_bounds(rr, cc, n):
            res.append((rr, cc))
    return res


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


def build_region_map(grid: List[List[str]]) -> Dict[str, List[Coord]]:
    n = len(grid)
    regions: Dict[str, List[Coord]] = {}
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            ch = grid[r - 1][c - 1]
            regions.setdefault(ch, []).append((r, c))
    return regions


def compute_domino_cells(dominoes: List[Edge]) -> Dict[Coord, int]:
    # return mapping cell -> count times appears
    m: Dict[Coord, int] = {}
    for a, b in dominoes:
        m[a] = m.get(a, 0) + 1
        m[b] = m.get(b, 0) + 1
    return m


def dominoes_touch_orth(d1: Edge, d2: Edge) -> bool:
    # share cell or have orth-adjacent cells -> touching
    (a1, b1), (a2, b2) = d1, d2
    cells1 = [a1, b1]
    cells2 = [a2, b2]
    for x in cells1:
        for y in cells2:
            if x == y:
                return True
            if touching_orth(x, y):
                return True
    return False


def format_grid(grid: List[List[str]]) -> str:
    # tab separated rows
    return "\n".join(["\t".join(row) for row in grid])


def format_solution(dominoes: List[Edge]) -> str:
    # sort by left-to-right or top-to-bottom: use min endpoint (r,c), then max endpoint
    doms = []
    for a, b in dominoes:
        aa, bb = (a, b) if a <= b else (b, a)
        doms.append((aa, bb))
    doms.sort(key=lambda x: (x[0][0], x[0][1], x[1][0], x[1][1]))
    parts = []
    for (r1, c1), (r2, c2) in doms:
        parts.append(f"({r1},{c1})({r2},{c2})")
    return "[[" + ",".join(parts) + "]]"


def solve_puzzle(grid: List[List[str]], require_unique: bool = True, cap_solutions: int = 2):
    """
    Returns (status, solution_dominoes, explanation_data)
    status: "sat_unique" | "sat_multi" | "unsat"
    solution_dominoes: list of edges for a found model (sorted later)
    explanation_data: dict with region_counts etc.
    """
    n = len(grid)
    regions = build_region_map(grid)
    edges = all_edges(n)

    # Variables: x_e indicates domino placed on edge e (adjacent cells)
    x = {}
    for e in edges:
        (r1, c1), (r2, c2) = e
        x[e] = Bool(f"x_{r1}_{c1}_{r2}_{c2}")

    # Helper: whether a cell is covered
    def cell_covered_expr(cell: Coord):
        r, c = cell
        incident = []
        for nb in orth_neighbors(r, c, n):
            e = norm_edge(cell, nb)
            incident.append(x[e])
        if not incident:
            return False
        return Or(incident)

    # Constraint: each cell covered by at most one domino (matching)
    s = Solver()
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            cell = (r, c)
            incident = []
            for nb in orth_neighbors(r, c, n):
                e = norm_edge(cell, nb)
                incident.append(x[e])
            # at most 1 true among incident
            if len(incident) >= 2:
                s.add(Sum([If(v, 1, 0) for v in incident]) <= 1)
            # if len<=1 automatically ok

    # Constraint: exactly 2 cells in each region are covered
    for reg, cells in regions.items():
        s.add(Sum([If(cell_covered_expr(cell), 1, 0) for cell in cells]) == 2)

    # Constraint: dominoes cannot touch each other orthogonally except diagonally allowed.
    # With matching, they don't share cells. Need to forbid orth-adjacent between different dominoes.
    # We enforce: for any two distinct edges e1,e2 that are orth-touching, not both selected.
    edges_list = edges
    # Precompute touching pairs
    touch_pairs = []
    for i in range(len(edges_list)):
        for j in range(i + 1, len(edges_list)):
            e1, e2 = edges_list[i], edges_list[j]
            if dominoes_touch_orth(e1, e2):
                # But if they touch only by sharing an endpoint, matching already prevents;
                # still safe to include.
                touch_pairs.append((e1, e2))
    for e1, e2 in touch_pairs:
        s.add(Not(And(x[e1], x[e2])))

    # Find one solution
    if s.check() != sat:
        return "unsat", [], {"n": n, "regions": {k: len(v) for k, v in regions.items()}}

    m = s.model()
    sol_edges = [e for e in edges if is_true(m.eval(x[e], model_completion=True))]
    # Ensure matching and region counts for explanation
    covered = compute_domino_cells(sol_edges)
    reg_cov_counts = {reg: 0 for reg in regions}
    for reg, cells in regions.items():
        reg_cov_counts[reg] = sum(1 for cell in cells if cell in covered)

    # Check uniqueness by blocking clause(s)
    if require_unique:
        # enumerate up to cap_solutions solutions
        sols = [sol_edges]
        # Add blocking for current solution, search for another
        def block_solution(edge_set: List[Edge]):
            # Block exact same set: at least one variable differs
            terms = []
            chosen = set(edge_set)
            for e in edges:
                if e in chosen:
                    terms.append(Not(x[e]))
                else:
                    terms.append(x[e])
            s.add(Or(terms))

        block_solution(sol_edges)
        while len(sols) < cap_solutions and s.check() == sat:
            m2 = s.model()
            sol2 = [e for e in edges if is_true(m2.eval(x[e], model_completion=True))]
            sols.append(sol2)
            block_solution(sol2)

        if len(sols) == 1:
            status = "sat_unique"
        else:
            status = "sat_multi"
        # return the first solution
    else:
        status = "sat_unique"

    return status, sol_edges, {
        "n": n,
        "region_sizes": {k: len(v) for k, v in sorted(regions.items(), key=lambda kv: kv[0])},
        "region_covered": reg_cov_counts,
        "domino_count": len(sol_edges),
    }


def generate_region_partition(rng: random.Random, n: int, target_regions: int) -> List[List[str]]:
    """
    Generate a connected-ish region partition by random growth (no guarantee connected but tends to be).
    We only need regions as labels; connectivity not required by rule but makes nicer puzzles.
    """
    # Seed region centers
    cells = [(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]
    rng.shuffle(cells)
    k = target_regions
    seeds = cells[:k]
    # Assign each cell to nearest seed with random tie-break
    # Create labels A,B,C,... then a,b,... then AA,...
    labels = []
    alph = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    i = 0
    while len(labels) < k:
        if i < 26:
            labels.append(alph[i])
        else:
            labels.append(alph[(i // 26) - 1] + alph[i % 26])
        i += 1

    def dist(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    assign: Dict[Coord, int] = {}
    for cell in [(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]:
        dmin = None
        best = []
        for i, s in enumerate(seeds):
            d = dist(cell, s)
            if dmin is None or d < dmin:
                dmin = d
                best = [i]
            elif d == dmin:
                best.append(i)
        assign[cell] = rng.choice(best)

    grid = [[None for _ in range(n)] for _ in range(n)]
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            grid[r - 1][c - 1] = labels[assign[(r, c)]]
    return grid  # type: ignore


def generate_case(rng: random.Random, max_tries: int = 300):
    # Choose size and region count
    # Ensure region count <= N*N/2 for feasibility (each region needs 2 covered cells -> 2*regions cells covered)
    for _ in range(max_tries):
        n = rng.choice([5, 6, 7])
        max_regions = (n * n) // 2
        target_regions = rng.randint(max(5, n), min(max_regions, n * 2 + 4))
        grid = generate_region_partition(rng, n, target_regions)

        status, sol_edges, info = solve_puzzle(grid, require_unique=True, cap_solutions=2)
        if status != "sat_unique":
            continue

        # Extra sanity: domino count must equal number of regions (each domino covers 2 cells, total covered = 2*regions)
        regions = build_region_map(grid)
        if len(sol_edges) != len(regions):
            continue

        # Ensure no region label appears too few cells (still solvable but make nicer)
        if min(len(v) for v in regions.values()) < 2:
            continue

        return grid, sol_edges, info

    raise RuntimeError("在给定尝试次数内无法生成满足“唯一解”的题目实例。请更换 seed 或减少 count。")


def make_problem_text(grid: List[List[str]], output_language: str = "zh") -> str:
    n = len(grid)
    grid_txt = format_grid(grid)
    if output_language.lower().startswith("zh"):
        return (
            "你需要在一个 N×N 方格上放置若干个多米诺骨牌（1×2 或 2×1），规则如下：\n"
            "1) 方格被字母划分为若干区域；\n"
            "2) 你可以在一些格子上“涂黑”，每两个相邻涂黑格组成一块多米诺骨牌；骨牌可以跨区域边界；\n"
            "3) 每个区域中恰好有 2 个格子被骨牌覆盖（即该区域恰好有 2 个格子被涂黑）；\n"
            "4) 所有涂黑格都必须属于某一块骨牌；\n"
            "5) 任意两块骨牌不能在上下左右方向接触（允许对角接触）。\n\n"
            f"给定网格（行从 1 到 {n}，列从 1 到 {n}）：\n"
            f"{grid_txt}\n\n"
            "请输出所有骨牌的两个端点坐标，格式为 (行i,列j)(行x,列y)。\n"
            "骨牌列表按“从上到下、从左到右”的顺序排列（按每块骨牌较小端点排序）。\n"
            "不同骨牌用英文逗号分隔，最终整体用双中括号包裹：\n"
            "[[(1,2)(1,3),(2,4)(3,4),...]]"
        )
    else:
        return (
            "Place dominoes (1x2 or 2x1) on an N×N grid partitioned into lettered regions:\n"
            "1) Dominoes may cross region borders.\n"
            "2) Exactly 2 cells in each region are covered by dominoes.\n"
            "3) Every covered (shaded) cell belongs to a domino.\n"
            "4) Dominoes may not touch orthogonally (diagonal touch allowed).\n\n"
            f"Grid (rows 1..{n}, cols 1..{n}):\n{grid_txt}\n\n"
            "Output all domino endpoint coordinates as (r,c)(r,c), sorted top-to-bottom/left-to-right.\n"
            "Separate dominoes with commas and wrap with double brackets like [[...]]."
        )


def make_explanation(grid: List[List[str]], sol_edges: List[Edge], info: Dict[str, Any], output_language: str = "zh") -> str:
    n = len(grid)
    regions = build_region_map(grid)
    covered = compute_domino_cells(sol_edges)

    # Prepare per-region covered coordinates for checkability
    reg_cov_cells: Dict[str, List[Coord]] = {}
    for reg, cells in regions.items():
        cov = [cell for cell in cells if cell in covered]
        cov.sort()
        reg_cov_cells[reg] = cov

    # A short verifiable explanation: list dominoes and show each region has exactly 2 covered cells.
    dom_str = format_solution(sol_edges)

    if output_language.lower().startswith("zh"):
        # show sample of region checks (all regions, but concise)
        reg_lines = []
        for reg in sorted(regions.keys()):
            cov = reg_cov_cells[reg]
            reg_lines.append(f"{reg}: 覆盖 {len(cov)} 格，坐标={cov}")
        return (
            "校验要点：\n"
            f"1) 给出的一组骨牌为：{dom_str}\n"
            f"2) 共 {len(sol_edges)} 块骨牌，覆盖 {2*len(sol_edges)} 个格子；\n"
            "3) 对每个区域统计其被覆盖格子数，均为 2（如下可逐项核对）：\n"
            + "\n".join(reg_lines)
            + "\n4) 任意两块骨牌不共享格且不存在上下左右相邻（对角相邻允许），因此满足“不正交接触”。"
        )
    else:
        reg_lines = []
        for reg in sorted(regions.keys()):
            cov = reg_cov_cells[reg]
            reg_lines.append(f"{reg}: covered {len(cov)} cells, coords={cov}")
        return (
            "Check:\n"
            f"1) Domino set: {dom_str}\n"
            f"2) {len(sol_edges)} dominoes cover {2*len(sol_edges)} cells.\n"
            "3) Each region has exactly 2 covered cells:\n"
            + "\n".join(reg_lines)
            + "\n4) Dominoes do not touch orthogonally (diagonal allowed)."
        )


def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])

    # Additional config passed by outer system (may not exist in stdin)
    # We keep output_language default zh as per requirement.
    output_language = "zh"
    # Allow override if provided
    if isinstance(data, dict) and "output_language" in data:
        output_language = data["output_language"] or "zh"

    rng = random.Random(seed)

    items = []
    seen = set()
    attempts_total = 0
    while len(items) < count:
        attempts_total += 1
        if attempts_total > 2000:
            raise RuntimeError("总体采样次数过多仍未生成足够不重复题目。请更换 seed 或减少 count。")

        grid, sol_edges, info = generate_case(rng)

        # Deduplicate by grid layout string
        key = "\n".join("".join(row) for row in grid)
        if key in seen:
            continue
        seen.add(key)

        problem = make_problem_text(grid, output_language=output_language)
        answer = format_solution(sol_edges)
        explanation = make_explanation(grid, sol_edges, info, output_language=output_language)

        items.append({
            "problem": problem,
            "answer": answer,
            "explanation": explanation
        })

    json.dump(items, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        eprint("ERROR:", repr(ex))
        raise