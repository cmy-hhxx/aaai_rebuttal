import sys, json, random
from typing import List, Tuple, Dict, Any, Optional, Set
from itertools import product, combinations

# Minesweeper generator/solver:
# We generate a partially revealed grid with numbers and X (unknown).
# Task: "use one-step logic reasoning" -> interpret as: cells that are forced mines
# by immediate local constraints (a revealed number whose unknown neighbors count equals remaining mines).
#
# We must ensure the reported "必定是地雷" cells are indeed mines in ALL completions
# consistent with the shown numbers AND also derivable by one-step rule.
#
# We'll:
# 1) Sample a full mine layout.
# 2) Compute full numbers.
# 3) Choose a set of revealed numbered cells; others are X.
# 4) Ensure: at least one one-step forced mine exists (non-empty answer).
# 5) Compute forced mines via one-step rule from the shown board.
# 6) Verify forced mines are globally forced (unique) by enumerating all mine assignments
#    on X-cells consistent with revealed numbers (bounded by small grids).
# 7) Output problem, answer (list of (r,c)), explanation.

Coord = Tuple[int, int]

def neighbors(r: int, c: int, R: int, C: int) -> List[Coord]:
    out = []
    for dr in (-1,0,1):
        for dc in (-1,0,1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r+dr, c+dc
            if 0 <= rr < R and 0 <= cc < C:
                out.append((rr, cc))
    return out

def compute_numbers(mines: Set[Coord], R: int, C: int) -> List[List[int]]:
    nums = [[0]*C for _ in range(R)]
    for r in range(R):
        for c in range(C):
            if (r,c) in mines:
                nums[r][c] = -1
            else:
                nums[r][c] = sum((nr,nc) in mines for nr,nc in neighbors(r,c,R,C))
    return nums

def render_board(shown: List[List[Optional[int]]]) -> str:
    # None -> X
    rows = []
    for row in shown:
        parts = []
        for v in row:
            parts.append("X" if v is None else str(v))
        rows.append("  ".join(parts))
    return "\n".join(rows)

def one_step_forced_mines(shown: List[List[Optional[int]]], R: int, C: int) -> Set[Coord]:
    forced = set()
    for r in range(R):
        for c in range(C):
            v = shown[r][c]
            if v is None:
                continue
            unk = []
            known_mines = 0  # none explicitly marked in this task
            for nr,nc in neighbors(r,c,R,C):
                if shown[nr][nc] is None:
                    unk.append((nr,nc))
            remaining = v - known_mines
            if remaining == len(unk) and remaining > 0:
                forced.update(unk)
    return forced

def consistent_with_shown(assign_mines: Set[Coord],
                          shown: List[List[Optional[int]]],
                          R: int, C: int) -> bool:
    # shown reveals only numbers (never mines). So any mine on a revealed cell is invalid.
    for r in range(R):
        for c in range(C):
            if shown[r][c] is not None and (r,c) in assign_mines:
                return False
    # Check every revealed number matches neighbor mines count
    for r in range(R):
        for c in range(C):
            v = shown[r][c]
            if v is None:
                continue
            cnt = 0
            for nr,nc in neighbors(r,c,R,C):
                if (nr,nc) in assign_mines:
                    cnt += 1
            if cnt != v:
                return False
    return True

def enumerate_all_solutions(shown: List[List[Optional[int]]], R: int, C: int,
                            max_unknown: int = 18, max_solutions: int = 20000) -> Optional[List[Set[Coord]]]:
    # Enumerate all mine assignments over unknown cells consistent with constraints.
    # We don't know total mine count; treat each unknown as boolean variable.
    unknowns = [(r,c) for r in range(R) for c in range(C) if shown[r][c] is None]
    if len(unknowns) > max_unknown:
        return None

    # To speed up, build constraints per revealed cell: sum(vars in neighbor unknowns) == v
    revealed = [(r,c,shown[r][c]) for r in range(R) for c in range(C) if shown[r][c] is not None]
    # Precompute for each revealed cell which indices of unknowns affect it
    idx = {cell:i for i,cell in enumerate(unknowns)}
    rel = []
    for r,c,v in revealed:
        inds = []
        for nr,nc in neighbors(r,c,R,C):
            if (nr,nc) in idx:
                inds.append(idx[(nr,nc)])
            else:
                # neighbor is revealed number, cannot be mine per our consistency definition
                pass
        rel.append((inds, v))

    sols = []
    # Backtracking with pruning via partial sums
    assigned = [None]*len(unknowns)  # None/0/1

    # For each constraint, maintain current sum and remaining vars count
    cur_sum = [0]*len(rel)
    rem_cnt = [0]*len(rel)
    for j,(inds,v) in enumerate(rel):
        rem_cnt[j] = len(inds)

    # Map var -> constraints it participates in
    var_to_cons = [[] for _ in range(len(unknowns))]
    for j,(inds,v) in enumerate(rel):
        for i in inds:
            var_to_cons[i].append(j)

    def feasible_after_setting(var_i: int, val: int) -> bool:
        # Update-based feasibility check for impacted constraints:
        for cons_i in var_to_cons[var_i]:
            inds, target = rel[cons_i]
            s = cur_sum[cons_i] + val
            rem = rem_cnt[cons_i] - 1
            # s + min_possible <= target <= s + max_possible
            # min_possible = 0, max_possible = rem
            if target < s or target > s + rem:
                return False
        return True

    def do_set(var_i: int, val: int):
        assigned[var_i] = val
        for cons_i in var_to_cons[var_i]:
            cur_sum[cons_i] += val
            rem_cnt[cons_i] -= 1

    def undo_set(var_i: int, val: int):
        assigned[var_i] = None
        for cons_i in var_to_cons[var_i]:
            cur_sum[cons_i] -= val
            rem_cnt[cons_i] += 1

    # Variable ordering: most constrained first (appears in many constraints)
    order = sorted(range(len(unknowns)), key=lambda i: -len(var_to_cons[i]))

    def backtrack(k: int):
        if len(sols) >= max_solutions:
            return
        if k == len(order):
            # check all constraints exactly met
            for j,(inds,target) in enumerate(rel):
                if cur_sum[j] != target:
                    return
            mines = set()
            for i,(r,c) in enumerate(unknowns):
                if assigned[i] == 1:
                    mines.add((r,c))
            # revealed cells mines already excluded by modeling
            sols.append(mines)
            return
        var_i = order[k]
        # Try 0 then 1 (either order doesn't matter)
        for val in (0,1):
            if feasible_after_setting(var_i, val):
                do_set(var_i, val)
                backtrack(k+1)
                undo_set(var_i, val)

    backtrack(0)
    return sols

def forced_in_all_solutions(solutions: List[Set[Coord]], unknown_cells: List[Coord]) -> Set[Coord]:
    if not solutions:
        return set()
    forced = set(unknown_cells)
    for sol in solutions:
        forced &= sol
    return forced

def build_problem_text(shown: List[List[Optional[int]]], output_language: str) -> str:
    R, C = len(shown), len(shown[0])
    grid_text = render_board(shown)
    if output_language == "zh":
        return (
            f"考虑这个 {R} x {C} 的扫雷网格。你需要根据当前信息，确定所有必定包含地雷的未揭示单元格。\n"
            "规则：\n"
            "1. 数字（0-8）表示周围 8 个相邻单元格中地雷的数量。\n"
            "2. 标记为 X 的单元格是未揭示的。\n"
            "3. 仅使用“一步逻辑推理”：如果某个数字格周围尚未揭示的邻格数量恰好等于该数字要求的地雷数量，"
            "则这些未揭示邻格都必定是地雷。\n"
            "输入网格（行从 0 开始，列从 0 开始）：\n"
            f"{grid_text}\n\n"
            "任务：输出所有必定是地雷的 X 单元格坐标，格式为 (行, 列) 的元组列表，例如 [(0,1),(2,3)]。"
        )
    else:
        # Fallback to Chinese if unspecified/other
        return build_problem_text(shown, "zh")

def make_explanation(shown: List[List[Optional[int]]], forced: Set[Coord], output_language: str) -> str:
    R, C = len(shown), len(shown[0])
    lines = []
    if output_language == "zh":
        lines.append("一步推理依据：对每个已揭示数字格，统计其周围未揭示(X)邻格数。若该数量等于该数字，则这些邻格全为雷。")
        # Provide concrete triggering cells
        for r in range(R):
            for c in range(C):
                v = shown[r][c]
                if v is None:
                    continue
                unk = [(nr,nc) for nr,nc in neighbors(r,c,R,C) if shown[nr][nc] is None]
                if v == len(unk) and v > 0:
                    lines.append(f"例如数字格 ({r},{c})= {v}，其周围未揭示邻格共有 {len(unk)} 个：{unk}，因此这些邻格必定都是地雷。")
        lines.append(f"综合上述可得必定为雷的坐标集合：{sorted(forced)}。")
        return "\n".join(lines)
    else:
        return make_explanation(shown, forced, "zh")

def gen_instance(rng: random.Random, output_language: str) -> Dict[str, Any]:
    # Choose size and mine density with bounded unknown count for enumeration
    # Mostly 4x4 to 6x6
    for _attempt in range(400):
        R, C = rng.choice([(4,4),(4,5),(5,5),(5,6)])
        n = R*C
        # choose mine count
        mine_count = rng.randint(max(3, n//6), max(4, n//4))
        cells = [(r,c) for r in range(R) for c in range(C)]
        mines = set(rng.sample(cells, mine_count))
        nums = compute_numbers(mines, R, C)

        # choose revealed numbers set size so unknowns <= 18 for enumeration
        # ensure revealed cells are not mines and are numbers (0-8)
        safe_cells = [(r,c) for r in range(R) for c in range(C) if (r,c) not in mines]
        # reveal between ~30% and ~60% of safe cells
        reveal_k = rng.randint(max(4, len(safe_cells)//3), max(5, (2*len(safe_cells))//3))
        revealed = set(rng.sample(safe_cells, min(reveal_k, len(safe_cells))))

        shown: List[List[Optional[int]]] = [[None]*C for _ in range(R)]
        for r,c in revealed:
            shown[r][c] = nums[r][c]

        unknowns = [(r,c) for r in range(R) for c in range(C) if shown[r][c] is None]
        if len(unknowns) > 18:
            continue

        forced = one_step_forced_mines(shown, R, C)
        if not forced:
            continue

        # Ensure forced cells are actually mines in the underlying layout (so they are "must be mines" plausible)
        # One-step rule implies they must be mines logically; but the constructed true layout should respect that.
        if not forced.issubset(mines):
            continue

        # Global uniqueness check: forced should be mines in all solutions
        sols = enumerate_all_solutions(shown, R, C, max_unknown=18, max_solutions=20000)
        if sols is None or len(sols) == 0:
            continue
        unknown_cells = [(r,c) for r in range(R) for c in range(C) if shown[r][c] is None]
        globally_forced = forced_in_all_solutions(sols, unknown_cells)

        # We only output mines that are guaranteed AND also derivable in one-step.
        # So require forced == globally_forced intersect forced, and also that forced are truly globally forced.
        if not forced.issubset(globally_forced):
            continue

        # Also avoid trivial "all X are mines"
        if len(forced) >= len(unknown_cells):
            continue

        problem = build_problem_text(shown, output_language)
        answer = sorted(list(forced))
        explanation = make_explanation(shown, forced, output_language)
        return {"problem": problem, "answer": answer, "explanation": explanation}

    raise RuntimeError("生成失败：在采样上限内未能构造出满足条件的扫雷实例。")

def main():
    data = sys.stdin.read()
    try:
        req = json.loads(data)
        seed = int(req["seed"])
        count = int(req["count"])
    except Exception as e:
        print(f"Input error: {e}", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(seed)
    output_language = "zh"
    # NOTE: output_language passed from outer system in prompt; not present in runtime input.
    # Keep default zh as required when unspecified.

    items = []
    seen: Set[str] = set()
    # Generate with resampling; avoid duplicates by problem text
    tries = 0
    while len(items) < count and tries < count * 300:
        tries += 1
        try:
            inst = gen_instance(rng, output_language)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            break
        key = inst["problem"]
        if key in seen:
            continue
        seen.add(key)
        items.append(inst)

    if len(items) != count:
        print(f"Warning: requested {count} but generated {len(items)}.", file=sys.stderr)

    sys.stdout.write(json.dumps(items, ensure_ascii=False))

if __name__ == "__main__":
    main()