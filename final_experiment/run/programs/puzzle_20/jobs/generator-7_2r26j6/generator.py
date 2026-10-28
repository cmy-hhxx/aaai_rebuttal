import sys, json, random, itertools, math, re
from typing import List, Tuple, Dict, Any, Optional

# We will generate "Tents and Trees" puzzles.
# Output language: Chinese (per request), but generator is self-contained and does not call translation APIs.
# Uses z3 (allowed) for solving/uniqueness checks.

try:
    from z3 import (
        Solver, Bool, Sum, If, And, Or, Not, sat, is_true
    )
except Exception as e:
    print("无法导入 z3，请确认环境包含 z3。错误: %r" % (e,), file=sys.stderr)
    raise

# ------------------------------
# Utilities
# ------------------------------

def rand_choice(rng: random.Random, items):
    return items[rng.randrange(len(items))]

def neighbors_orth(r: int, c: int, R: int, C: int):
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        rr, cc = r+dr, c+dc
        if 0 <= rr < R and 0 <= cc < C:
            yield rr, cc

def neighbors_8(r: int, c: int, R: int, C: int):
    for dr in [-1,0,1]:
        for dc in [-1,0,1]:
            if dr == 0 and dc == 0:
                continue
            rr, cc = r+dr, c+dc
            if 0 <= rr < R and 0 <= cc < C:
                yield rr, cc

def format_matrix(mat: List[List[str]]) -> str:
    # Required format:
    # [[row1 comma-separated tokens, row2..., ...]] with spaces between elements in row,
    # different lines separated by comma.
    rows = []
    for r in mat:
        rows.append(" ".join(r))
    return "[[" + ",".join(rows) + "]]"

def stringify_grid_with_constraints(grid: List[List[str]], row_counts: List[int], col_counts: List[int]) -> str:
    # Create a tab-like statement in Chinese, similar to seed but not identical.
    R, C = len(grid), len(grid[0])
    lines = []
    lines.append("给定一个 %d×%d 的网格。T 表示树，X 表示空格。你需要把部分 X 替换为 C（帐篷）。" % (R, C))
    lines.append("规则：每个帐篷必须与某一棵树正交相邻；帐篷之间不能正交或对角相邻；每行/每列帐篷数量必须满足给定数字；并且题目保证唯一解。")
    lines.append("")
    lines.append("网格（每行末尾是该行帐篷数）：")
    for r in range(R):
        lines.append("\t".join(grid[r] + [str(row_counts[r])]))
    lines.append("每列帐篷数（按从左到右）：")
    lines.append("\t".join(str(x) for x in col_counts))
    lines.append("")
    lines.append("输出格式：按从左到右、从上到下输出矩阵，用空格分隔元素、用逗号分隔行，并用双中括号包裹，例如：[[T X,C X]]。")
    return "\n".join(lines)

# ------------------------------
# Z3 model for Tents and Trees
# ------------------------------

class TentsPuzzle:
    def __init__(self, R: int, C: int, trees: List[Tuple[int,int]], row_counts: List[int], col_counts: List[int]):
        self.R = R
        self.C = C
        self.trees = set(trees)
        self.row_counts = row_counts
        self.col_counts = col_counts

    def solve_all_solutions_up_to(self, limit: int = 2):
        """Return up to 'limit' different solutions as matrices of booleans tent[r][c]."""
        R, C = self.R, self.C
        s = Solver()

        tent = [[Bool(f"tent_{r}_{c}") for c in range(C)] for r in range(R)]

        # Trees are not tents
        for (r, c) in self.trees:
            s.add(tent[r][c] == False)

        # Each tent must be adjacent to at least one tree
        for r in range(R):
            for c in range(C):
                if (r, c) in self.trees:
                    continue
                adj_trees = []
                for rr, cc in neighbors_orth(r, c, R, C):
                    if (rr, cc) in self.trees:
                        adj_trees.append(True)
                if not adj_trees:
                    # no adjacent trees -> cannot place tent here
                    s.add(tent[r][c] == False)
                else:
                    # must have at least one adjacent tree if it's a tent
                    ors = []
                    for rr, cc in neighbors_orth(r, c, R, C):
                        if (rr, cc) in self.trees:
                            ors.append(True)
                    # If tent[r][c] then (there exists adjacent tree). Since ors is non-empty and all True,
                    # this is tautological; but keep structurally. Real restriction is enforced by "no-adj-tree => false".
                    s.add(Implies(tent[r][c], Or([True])))

        # Tents cannot touch each other orthogonally or diagonally
        for r in range(R):
            for c in range(C):
                for rr, cc in neighbors_8(r, c, R, C):
                    # enforce only once by ordering
                    if (rr, cc) <= (r, c):
                        continue
                    s.add(Not(And(tent[r][c], tent[rr][cc])))

        # Row/column counts
        for r in range(R):
            s.add(Sum([If(tent[r][c], 1, 0) for c in range(C)]) == self.row_counts[r])
        for c in range(C):
            s.add(Sum([If(tent[r][c], 1, 0) for r in range(R)]) == self.col_counts[c])

        # Additionally, common tents&trees rule: each tree is adjacent to exactly one tent.
        # This is standard for "Tents and Trees" and is necessary for well-defined puzzles/uniqueness.
        for tr, tc in self.trees:
            adj = []
            for rr, cc in neighbors_orth(tr, tc, R, C):
                adj.append(tent[rr][cc])
            # Some trees might be isolated due to borders/other trees; then it's unsat anyway.
            s.add(Sum([If(x, 1, 0) for x in adj]) == 1)

        sols = []
        while len(sols) < limit and s.check() == sat:
            m = s.model()
            sol = [[False]*C for _ in range(R)]
            for r in range(R):
                for c in range(C):
                    sol[r][c] = is_true(m.evaluate(tent[r][c], model_completion=True))
            sols.append(sol)
            # block this solution
            block = []
            for r in range(R):
                for c in range(C):
                    block.append(tent[r][c] != sol[r][c])
            s.add(Or(block))
        return sols

    def solve_unique(self):
        sols = self.solve_all_solutions_up_to(limit=2)
        if len(sols) == 1:
            return True, sols[0]
        elif len(sols) == 0:
            return False, None
        else:
            return False, None

def Implies(a, b):
    return Or(Not(a), b)

# ------------------------------
# Puzzle construction
# ------------------------------

def compute_counts_from_solution(sol: List[List[bool]]) -> Tuple[List[int], List[int]]:
    R, C = len(sol), len(sol[0])
    row = [sum(1 for c in range(C) if sol[r][c]) for r in range(R)]
    col = [sum(1 for r in range(R) if sol[r][c]) for c in range(C)]
    return row, col

def tents_to_answer_matrix(tree_grid: List[List[bool]], tent_sol: List[List[bool]]) -> List[List[str]]:
    R, C = len(tree_grid), len(tree_grid[0])
    out = []
    for r in range(R):
        row = []
        for c in range(C):
            if tree_grid[r][c]:
                row.append("T")
            else:
                row.append("C" if tent_sol[r][c] else "X")
        out.append(row)
    return out

def generate_solution_layout(rng: random.Random, R: int, C: int, tent_count_target: int) -> Optional[Tuple[List[List[bool]], List[List[bool]]]]:
    """
    Construct (trees, tents) by pairing tents with trees:
    - Place tents with no adjacency (8-neighborhood).
    - For each tent, place exactly one adjacent tree cell (also not overlapping other trees/tents).
    Returns boolean grids (tree_grid, tent_grid).
    """
    tree = [[False]*C for _ in range(R)]
    tent = [[False]*C for _ in range(R)]

    # Candidate cells for tents
    cells = [(r,c) for r in range(R) for c in range(C)]
    rng.shuffle(cells)

    placed = []
    for (r,c) in cells:
        if len(placed) >= tent_count_target:
            break
        # cannot place on existing
        if tree[r][c] or tent[r][c]:
            continue
        # cannot be adjacent to other tents (8-dir)
        ok = True
        for rr, cc in neighbors_8(r, c, R, C):
            if tent[rr][cc]:
                ok = False
                break
        if not ok:
            continue
        # needs at least one adjacent free cell for a tree
        adj = [(rr,cc) for rr,cc in neighbors_orth(r,c,R,C) if not tree[rr][cc] and not tent[rr][cc]]
        if not adj:
            continue

        # Tent placed
        tent[r][c] = True
        placed.append((r,c))

        # Place its tree in one adjacent cell; prefer cells that won't break future placements
        rng.shuffle(adj)
        chosen = None
        for (tr, tc) in adj:
            # It's OK for trees to be adjacent to anything; but avoid putting tree where it would remove all tree-options for other tents?
            # Keep simple: choose first.
            chosen = (tr, tc)
            break
        if chosen is None:
            tent[r][c] = False
            placed.pop()
            continue
        tr, tc = chosen
        tree[tr][tc] = True

    if len(placed) < max(3, tent_count_target * 3 // 4):
        return None

    # Validate: each tree adjacent to exactly one tent and each tent adjacent to exactly one tree (by construction trees may touch multiple tents if unlucky)
    # Fix by rejecting if any tree is adjacent to !=1 tent.
    for r in range(R):
        for c in range(C):
            if tree[r][c]:
                adj_t = sum(1 for rr,cc in neighbors_orth(r,c,R,C) if tent[rr][cc])
                if adj_t != 1:
                    return None
    # Each tent must have at least one adjacent tree (true), but could have multiple adjacent trees. That's allowed by rule 3,
    # but combined with "each tree exactly one tent" still OK. We'll accept.

    return tree, tent

def boolgrid_to_tree_positions(tree_grid: List[List[bool]]) -> List[Tuple[int,int]]:
    pos = []
    for r in range(len(tree_grid)):
        for c in range(len(tree_grid[0])):
            if tree_grid[r][c]:
                pos.append((r,c))
    return pos

def make_puzzle(rng: random.Random) -> Optional[Dict[str, Any]]:
    # Vary sizes and densities
    size_choices = [(5,8),(6,8),(6,9),(7,9),(7,10),(8,8)]
    R, C = rand_choice(rng, size_choices)

    # pick target number of tents
    max_tents = (R*C)//4
    tent_target = rng.randint(max(5, min(8, max_tents//2)), max(8, min(max_tents, 14)))

    layout = None
    for _ in range(80):
        layout = generate_solution_layout(rng, R, C, tent_target)
        if layout is not None:
            break
    if layout is None:
        return None

    tree_grid, tent_sol = layout
    trees = boolgrid_to_tree_positions(tree_grid)
    row_counts, col_counts = compute_counts_from_solution(tent_sol)

    # Build puzzle instance and check uniqueness via Z3
    puzzle = TentsPuzzle(R, C, trees, row_counts, col_counts)
    ok, unique_sol = puzzle.solve_unique()
    if not ok:
        return None

    # Cross-check solution equals constructed tent_sol (independent verification)
    if unique_sol is None:
        return None
    if unique_sol != tent_sol:
        # Sometimes counts+trees force a different unique tent placement than constructed; still valid, but we want internal consistency for explanation.
        tent_sol = unique_sol

    # Render grid with T/X only
    grid = [["T" if tree_grid[r][c] else "X" for c in range(C)] for r in range(R)]

    problem_text = stringify_grid_with_constraints(grid, row_counts, col_counts)

    answer_mat = tents_to_answer_matrix(tree_grid, tent_sol)
    answer_str = format_matrix(answer_mat)

    # Build a concise, checkable explanation: show row/col sums and a couple of forced placements derived from constraints
    # We'll include: total tents, row_counts, col_counts, and verify each tree has exactly one adjacent tent by listing counts.
    total_tents = sum(row_counts)
    tree_adj_counts = []
    for (tr, tc) in sorted(trees):
        adj = [(rr,cc) for rr,cc in neighbors_orth(tr,tc,R,C)]
        adj_tents = [(rr,cc) for (rr,cc) in adj if tent_sol[rr][cc]]
        tree_adj_counts.append(((tr,tc), adj_tents))

    expl_lines = []
    expl_lines.append(f"解的校验要点：")
    expl_lines.append(f"1) 总帐篷数 = 各行之和 = {total_tents}，各列之和也为 {sum(col_counts)}，两者一致。")
    expl_lines.append(f"2) 行约束 = {row_counts}；列约束 = {col_counts}。答案矩阵中每行/每列的 C 数量与之相等。")
    # Provide evidence for a few trees
    sample_k = min(6, len(tree_adj_counts))
    rng_local = random.Random((R*1000 + C)*1000003 + total_tents)  # deterministic based on instance, not global randomness
    idxs = list(range(len(tree_adj_counts)))
    rng_local.shuffle(idxs)
    idxs = idxs[:sample_k]
    expl_lines.append(f"3) 树-帐篷相邻性（示例抽查 {sample_k} 棵树）：每棵树正交相邻恰好 1 个帐篷。")
    for i in idxs:
        (tr,tc), adj_t = tree_adj_counts[i]
        expl_lines.append(f"   树({tr+1},{tc+1}) 相邻帐篷位置: " + ", ".join(f"({r+1},{c+1})" for r,c in adj_t))
    expl_lines.append("4) 任意两顶帐篷在 8 邻域内不相邻；并且每顶帐篷都与至少一棵树正交相邻。")
    explanation = "\n".join(expl_lines)

    return {
        "problem": problem_text,
        "answer": answer_str,
        "explanation": explanation
    }

# ------------------------------
# Main generate
# ------------------------------

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    results = []
    seen = set()

    attempts = 0
    max_attempts = 4000

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        item = make_puzzle(rng)
        if item is None:
            continue
        # deduplicate by problem text hash (stable)
        key = item["problem"]
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    if len(results) < count:
        print(f"生成失败：只生成了 {len(results)}/{count} 题。请尝试更换 seed 或降低 count。", file=sys.stderr)

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()