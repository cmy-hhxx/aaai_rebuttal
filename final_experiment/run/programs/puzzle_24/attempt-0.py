import sys, json, random
from typing import List, Tuple, Dict, Optional, Any

# We generate crossword-fill puzzles on an X/0 grid.
# X: cell to fill with a letter; 0: block.
# Across words fill left->right along contiguous X-runs in a row.
# Down words fill top->bottom along contiguous X-runs in a column.
# Crossings must match. We output filled grid row-wise.

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def grid_runs_across(grid: List[List[int]]) -> List[List[Tuple[int,int]]]:
    runs = []
    R, C = len(grid), len(grid[0])
    for r in range(R):
        c = 0
        while c < C:
            if grid[r][c] == 1:
                start = c
                cells = []
                while c < C and grid[r][c] == 1:
                    cells.append((r,c))
                    c += 1
                # treat any run length >=1 as a word slot
                runs.append(cells)
            else:
                c += 1
    return runs

def grid_runs_down(grid: List[List[int]]) -> List[List[Tuple[int,int]]]:
    runs = []
    R, C = len(grid), len(grid[0])
    for c in range(C):
        r = 0
        while r < R:
            if grid[r][c] == 1:
                cells = []
                while r < R and grid[r][c] == 1:
                    cells.append((r,c))
                    r += 1
                runs.append(cells)
            else:
                r += 1
    return runs

def stringify_word(w: str) -> str:
    # Keep letters without spaces inside; puzzle expects words like ACT
    return w

def render_grid_template(grid: List[List[int]]) -> str:
    # Render with spaces similar to seed: "X        X" etc.
    # We'll render with 8 spaces between entries to improve readability.
    sep = "        "
    lines = []
    for row in grid:
        parts = [("X" if v==1 else "0") for v in row]
        lines.append(sep.join(parts))
    return "\n".join(lines)

def format_answer_grid(filled: List[List[Optional[str]]], grid: List[List[int]]) -> str:
    # Answer: [[row1, row2, ...]] where each row is "A B 0" tokens separated by space,
    # rows separated by comma.
    rows = []
    for r in range(len(grid)):
        toks = []
        for c in range(len(grid[0])):
            if grid[r][c] == 0:
                toks.append("0")
            else:
                toks.append(filled[r][c])
        rows.append(" ".join(toks))
    return "[[" + ",".join(rows) + "]]"

def solve_by_constraints(grid: List[List[int]], across_words: List[str], down_words: List[str]) -> Optional[List[List[str]]]:
    # Backtracking assignment of words to runs in given order.
    across_slots = grid_runs_across(grid)
    down_slots = grid_runs_down(grid)

    if len(across_slots) != len(across_words) or len(down_slots) != len(down_words):
        return None
    # length match
    for slot, w in zip(across_slots, across_words):
        if len(slot) != len(w): 
            return None
    for slot, w in zip(down_slots, down_words):
        if len(slot) != len(w):
            return None

    R, C = len(grid), len(grid[0])
    filled = [[None for _ in range(C)] for _ in range(R)]

    # Prepare constraints mapping from cell to (slot, index). But easier: place words sequentially with checks.
    placements = []
    for slot, w in zip(across_slots, across_words):
        placements.append((slot, w))
    for slot, w in zip(down_slots, down_words):
        placements.append((slot, w))

    # deterministic order: put longer slots first to reduce ambiguity, but keep stable tie-break.
    order = sorted(range(len(placements)), key=lambda i: (-len(placements[i][0]), i))
    placed = [False]*len(placements)

    def can_place(slot, w):
        for i,(r,c) in enumerate(slot):
            ch = w[i]
            if filled[r][c] is not None and filled[r][c] != ch:
                return False
        return True

    def do_place(slot, w):
        changed = []
        for i,(r,c) in enumerate(slot):
            ch = w[i]
            if filled[r][c] is None:
                filled[r][c] = ch
                changed.append((r,c))
        return changed

    def undo(changed):
        for r,c in changed:
            filled[r][c] = None

    def dfs(k):
        if k == len(order):
            # ensure all X filled
            for r in range(R):
                for c in range(C):
                    if grid[r][c] == 1 and filled[r][c] is None:
                        return False
            return True
        idx = order[k]
        slot, w = placements[idx]
        if not can_place(slot, w):
            return False
        changed = do_place(slot, w)
        if dfs(k+1):
            return True
        undo(changed)
        return False

    ok = dfs(0)
    if not ok:
        return None
    # filled guaranteed non-None on X
    return [[filled[r][c] if grid[r][c]==1 else "0" for c in range(C)] for r in range(R)]

def enumerate_solutions_count(grid: List[List[int]], across_words: List[str], down_words: List[str], limit: int = 3) -> int:
    # Count solutions up to limit (for uniqueness check).
    across_slots = grid_runs_across(grid)
    down_slots = grid_runs_down(grid)
    if len(across_slots) != len(across_words) or len(down_slots) != len(down_words):
        return 0
    for slot, w in zip(across_slots, across_words):
        if len(slot) != len(w): 
            return 0
    for slot, w in zip(down_slots, down_words):
        if len(slot) != len(w):
            return 0

    R, C = len(grid), len(grid[0])
    filled = [[None for _ in range(C)] for _ in range(R)]

    placements = []
    for slot, w in zip(across_slots, across_words):
        placements.append((slot, w))
    for slot, w in zip(down_slots, down_words):
        placements.append((slot, w))
    order = sorted(range(len(placements)), key=lambda i: (-len(placements[i][0]), i))

    def can_place(slot, w):
        for i,(r,c) in enumerate(slot):
            ch = w[i]
            if filled[r][c] is not None and filled[r][c] != ch:
                return False
        return True

    def do_place(slot, w):
        changed = []
        for i,(r,c) in enumerate(slot):
            ch = w[i]
            if filled[r][c] is None:
                filled[r][c] = ch
                changed.append((r,c))
        return changed

    def undo(changed):
        for r,c in changed:
            filled[r][c] = None

    count = 0

    def dfs(k):
        nonlocal count
        if count >= limit:
            return
        if k == len(order):
            # full fill?
            for r in range(R):
                for c in range(C):
                    if grid[r][c] == 1 and filled[r][c] is None:
                        return
            count += 1
            return
        idx = order[k]
        slot, w = placements[idx]
        if not can_place(slot, w):
            return
        changed = do_place(slot, w)
        dfs(k+1)
        undo(changed)

    dfs(0)
    return count

def make_family(rng: random.Random):
    # Multiple families with different fixed grid patterns; words constructed from a hidden full letter grid.
    families = []

    # Family A: 3x3 like seed
    gridA = [
        [1,1,1],
        [0,1,0],
        [0,1,0],
    ]
    families.append(("A", gridA))

    # Family B: 3x4 with two across runs and one down run crossing
    # X X 0 X
    # 0 X 0 X
    # 0 X X X
    gridB = [
        [1,1,0,1],
        [0,1,0,1],
        [0,1,1,1],
    ]
    families.append(("B", gridB))

    # Family C: 4x4 plus-shape
    # 0 X 0 0
    # X X X 0
    # 0 X 0 0
    # 0 X 0 0
    gridC = [
        [0,1,0,0],
        [1,1,1,0],
        [0,1,0,0],
        [0,1,0,0],
    ]
    families.append(("C", gridC))

    # Family D: 4x5 with more slots
    # X X X 0 X
    # 0 X 0 0 X
    # X X 0 X X
    # X 0 0 X 0
    gridD = [
        [1,1,1,0,1],
        [0,1,0,0,1],
        [1,1,0,1,1],
        [1,0,0,1,0],
    ]
    families.append(("D", gridD))

    fam = rng.choice(families)
    return fam

def sample_letter_grid(rng: random.Random, grid: List[List[int]]) -> List[List[Optional[str]]]:
    R, C = len(grid), len(grid[0])
    filled = [[None for _ in range(C)] for _ in range(R)]
    for r in range(R):
        for c in range(C):
            if grid[r][c] == 1:
                filled[r][c] = rng.choice(LETTERS)
    return filled

def derive_words_from_filled(grid: List[List[int]], filled: List[List[Optional[str]]]) -> Tuple[List[str], List[str]]:
    across_slots = grid_runs_across(grid)
    down_slots = grid_runs_down(grid)
    across_words = []
    down_words = []
    for slot in across_slots:
        w = "".join(filled[r][c] for r,c in slot)
        across_words.append(w)
    for slot in down_slots:
        w = "".join(filled[r][c] for r,c in slot)
        down_words.append(w)
    return across_words, down_words

def build_explanation(grid: List[List[int]], across_words: List[str], down_words: List[str], solved: List[List[str]]) -> str:
    # Provide verifiable evidence: list each slot and the letters placed, plus a couple crossing checks.
    across_slots = grid_runs_across(grid)
    down_slots = grid_runs_down(grid)

    lines = []
    lines.append("按规则：先确定每一段连续的 X 是一个待填单词位（横向/纵向），把给定单词依次填入，对交叉格要求字母相同。")
    lines.append("横向单词位与填入：")
    for i,(slot,w) in enumerate(zip(across_slots, across_words), start=1):
        cells = "->".join([f"({r+1},{c+1})" for r,c in slot])
        lines.append(f"  横{i}: {cells} 填 {w}")
    lines.append("纵向单词位与填入：")
    for i,(slot,w) in enumerate(zip(down_slots, down_words), start=1):
        cells = "->".join([f"({r+1},{c+1})" for r,c in slot])
        lines.append(f"  纵{i}: {cells} 填 {w}")

    # show a few crossing checks
    crosses = []
    # map cells to letters from across and down implied
    # Build dict from across
    for slot, w in zip(across_slots, across_words):
        for k,(r,c) in enumerate(slot):
            crosses.append((r,c,w[k],"across"))
    # We will check cells that appear in both across and down slots by scanning
    cell_ac = {}
    for slot, w in zip(across_slots, across_words):
        for k,(r,c) in enumerate(slot):
            cell_ac[(r,c)] = w[k]
    cell_dn = {}
    for slot, w in zip(down_slots, down_words):
        for k,(r,c) in enumerate(slot):
            cell_dn[(r,c)] = w[k]
    inter = sorted(set(cell_ac.keys()) & set(cell_dn.keys()))
    if inter:
        lines.append("交叉校验（同一格横纵字母一致）：")
        for (r,c) in inter[:4]:
            lines.append(f"  格({r+1},{c+1})：横={cell_ac[(r,c)]}，纵={cell_dn[(r,c)]}，一致")
    lines.append("因此得到的完整填字矩阵如下（按从左到右、从上到下输出，0 为阻隔格）。")
    return "\n".join(lines)

def make_problem_text(output_language: str, grid: List[List[int]], across_words: List[str], down_words: List[str]) -> str:
    # Only Chinese required by user.
    header = []
    header.append("你需要完成一个简化填字游戏（crossword）填充。规则：")
    header.append("1) 题面给出由 X 和 0 组成的矩阵；X 表示要填字母的格，0 表示阻隔格（不填字母）。")
    header.append("2) 给出横向(across)与纵向(down)单词列表：横向从左到右填入每一段连续 X；纵向从上到下填入每一段连续 X。")
    header.append("3) 单词在交叉处共享字母，交叉格字母必须一致。")
    header.append("问题：根据给定单词填满所有 X。")
    header.append("")
    header.append("单词列表：")
    header.append("across: " + "，".join(stringify_word(w) for w in across_words))
    header.append("down: " + "，".join(stringify_word(w) for w in down_words))
    header.append("")
    header.append("矩阵：")
    header.append(render_grid_template(grid))
    header.append("")
    header.append("输出格式要求：答案按“从左到右、从上到下”给出；元素用空格分隔、行与行用逗号分隔；整体再用双层方括号包裹。")
    return "\n".join(header)

def generate_one(rng: random.Random, output_language: str, max_tries: int = 200) -> Dict[str, Any]:
    for _ in range(max_tries):
        fam_name, grid = make_family(rng)
        filled_letters = sample_letter_grid(rng, grid)
        across_words, down_words = derive_words_from_filled(grid, filled_letters)

        solved_grid = solve_by_constraints(grid, across_words, down_words)
        if solved_grid is None:
            continue

        # uniqueness check (up to 2)
        sol_count = enumerate_solutions_count(grid, across_words, down_words, limit=2)
        if sol_count != 1:
            continue

        # Prepare answer in required format
        # solved_grid currently contains "0" for blocks; convert to letters for X
        R, C = len(grid), len(grid[0])
        filled_out = [[None for _ in range(C)] for _ in range(R)]
        for r in range(R):
            for c in range(C):
                if grid[r][c] == 1:
                    filled_out[r][c] = solved_grid[r][c]
        answer = format_answer_grid(filled_out, grid)
        problem = make_problem_text(output_language, grid, across_words, down_words)
        explanation = build_explanation(grid, across_words, down_words, solved_grid)

        return {"problem": problem, "answer": answer, "explanation": explanation}

    raise RuntimeError("生成失败：在最大尝试次数内未找到满足可解且唯一解的实例。")

def main():
    data = json.loads(sys.stdin.read())
    seed = int(data["seed"])
    count = int(data["count"])
    rng = random.Random(seed)

    # output_language comes from the caller context in this environment; default zh
    output_language = "zh"

    results = []
    seen = set()
    attempts = 0
    # Avoid duplicates by hashing (grid + words)
    while len(results) < count:
        attempts += 1
        if attempts > 5000:
            raise RuntimeError("生成失败：去重与唯一解约束下重采样次数过多。")
        item = generate_one(rng, output_language)
        sig = (item["problem"])
        if sig in seen:
            continue
        seen.add(sig)
        results.append(item)

    sys.stdout.write(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e), file=sys.stderr)
        raise