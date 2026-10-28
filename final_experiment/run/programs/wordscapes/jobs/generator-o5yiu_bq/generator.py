import sys, json, random
from typing import List, Tuple, Dict, Any, Optional

# We will generate small crossword-fill problems on a grid with:
# - blocked cells (0) which must be rendered as spaces " "
# - fillable cells (X) which must be filled with letters
# Provide a set of across and down words; all must be placed exactly once.
# Then solve to produce the completed grid (unique checked).

LETTERS = "abcdefghijklmnopqrstuvwxyz"

def rng_choice(rng: random.Random, seq):
    return seq[rng.randrange(len(seq))]

def grid_to_strings(grid_mask: List[List[str]]) -> str:
    # Render mask as in prompt style: "0        X ..."
    lines = []
    for row in grid_mask:
        lines.append("        ".join(row))
    return "\n".join(lines)

def find_slots(mask: List[List[str]]) -> Tuple[List[Tuple[str,int,List[Tuple[int,int]]]], List[Tuple[str,int,List[Tuple[int,int]]]]]:
    """
    Return across_slots, down_slots.
    Each slot: (dir, length, cells[(r,c)...]) where length>=2 and cells are X positions.
    A slot is maximal contiguous run of X in that direction.
    """
    R, C = len(mask), len(mask[0])
    across = []
    for r in range(R):
        c = 0
        while c < C:
            if mask[r][c] == "X" and (c == 0 or mask[r][c-1] != "X"):
                # start
                cells = []
                cc = c
                while cc < C and mask[r][cc] == "X":
                    cells.append((r, cc))
                    cc += 1
                if len(cells) >= 2:
                    across.append(("across", len(cells), cells))
                c = cc
            else:
                c += 1
    down = []
    for c in range(C):
        r = 0
        while r < R:
            if mask[r][c] == "X" and (r == 0 or mask[r-1][c] != "X"):
                cells = []
                rr = r
                while rr < R and mask[rr][c] == "X":
                    cells.append((rr, c))
                    rr += 1
                if len(cells) >= 2:
                    down.append(("down", len(cells), cells))
                r = rr
            else:
                r += 1
    return across, down

def slot_intersections(slots: List[Tuple[str,int,List[Tuple[int,int]]]]) -> Dict[Tuple[int,int], List[int]]:
    m: Dict[Tuple[int,int], List[int]] = {}
    for i, (_, _, cells) in enumerate(slots):
        for cell in cells:
            m.setdefault(cell, []).append(i)
    return m

def solve_crossword(mask: List[List[str]], across_words: List[str], down_words: List[str]) -> List[Dict[str, Any]]:
    """
    Backtracking exact cover-ish solver.
    Assign each slot a word of matching length, all words used exactly once per direction list.
    Intersections must match letters.
    Return list of solutions (each solution has filled grid).
    """
    across_slots, down_slots = find_slots(mask)
    # quick checks
    aw_by_len: Dict[int, List[str]] = {}
    for w in across_words:
        aw_by_len.setdefault(len(w), []).append(w)
    dw_by_len: Dict[int, List[str]] = {}
    for w in down_words:
        dw_by_len.setdefault(len(w), []).append(w)

    for _, L, _ in across_slots:
        if L not in aw_by_len:
            return []
    for _, L, _ in down_slots:
        if L not in dw_by_len:
            return []

    # Precompute candidate lists per slot
    across_cands = []
    for _, L, _ in across_slots:
        across_cands.append(list(aw_by_len[L]))
    down_cands = []
    for _, L, _ in down_slots:
        down_cands.append(list(dw_by_len[L]))

    R, C = len(mask), len(mask[0])
    # grid letters assignment
    grid = [[None if mask[r][c] == "X" else " " for c in range(C)] for r in range(R)]

    used_across = set()
    used_down = set()
    assign_across: List[Optional[str]] = [None]*len(across_slots)
    assign_down: List[Optional[str]] = [None]*len(down_slots)

    # For propagation: map cell->(across slot idx, pos), (down slot idx, pos)
    cell_to_across = {}
    for i, (_, _, cells) in enumerate(across_slots):
        for pos, cell in enumerate(cells):
            cell_to_across[cell] = (i, pos)
    cell_to_down = {}
    for i, (_, _, cells) in enumerate(down_slots):
        for pos, cell in enumerate(cells):
            cell_to_down[cell] = (i, pos)

    # choose next unassigned slot with minimum remaining candidates considering current grid constraints
    def valid_word_for_slot(word: str, cells: List[Tuple[int,int]]) -> bool:
        for k, (r,c) in enumerate(cells):
            ch = word[k]
            cur = grid[r][c]
            if cur is not None and cur != ch:
                return False
        return True

    def place_word(word: str, cells: List[Tuple[int,int]]):
        changed = []
        for k, (r,c) in enumerate(cells):
            if grid[r][c] is None:
                grid[r][c] = word[k]
                changed.append((r,c))
        return changed

    def unplace(changed):
        for r,c in changed:
            grid[r][c] = None

    solutions = []

    def backtrack():
        # if all assigned
        if all(a is not None for a in assign_across) and all(d is not None for d in assign_down):
            # build filled grid
            filled = []
            for r in range(R):
                row = []
                for c in range(C):
                    if mask[r][c] == "0":
                        row.append(" ")
                    else:
                        row.append(grid[r][c])
                filled.append(row)
            solutions.append({"grid": filled, "across": list(assign_across), "down": list(assign_down)})
            return
        # select next slot
        best = None  # (is_across, idx, candidates)
        # across unassigned
        for i, slot in enumerate(across_slots):
            if assign_across[i] is not None:
                continue
            _, _, cells = slot
            cands = []
            for w in across_cands[i]:
                if w in used_across:
                    continue
                if valid_word_for_slot(w, cells):
                    cands.append(w)
            if best is None or len(cands) < len(best[2]):
                best = (True, i, cands)
                if len(cands) == 0:
                    break
        # down unassigned
        if best is None or len(best[2]) > 0:
            for i, slot in enumerate(down_slots):
                if assign_down[i] is not None:
                    continue
                _, _, cells = slot
                cands = []
                for w in down_cands[i]:
                    if w in used_down:
                        continue
                    if valid_word_for_slot(w, cells):
                        cands.append(w)
                if best is None or len(cands) < len(best[2]):
                    best = (False, i, cands)
                    if len(cands) == 0:
                        break
        if best is None:
            return
        is_across, idx, cands = best
        if len(cands) == 0:
            return
        # deterministic order (stable) to ensure reproducibility; but input randomization already handled in generation.
        for w in cands:
            if is_across:
                _, _, cells = across_slots[idx]
                assign_across[idx] = w
                used_across.add(w)
                changed = place_word(w, cells)
                backtrack()
                unplace(changed)
                used_across.remove(w)
                assign_across[idx] = None
            else:
                _, _, cells = down_slots[idx]
                assign_down[idx] = w
                used_down.add(w)
                changed = place_word(w, cells)
                backtrack()
                unplace(changed)
                used_down.remove(w)
                assign_down[idx] = None

    backtrack()
    return solutions

def mask_from_template(template_name: str, rng: random.Random) -> List[List[str]]:
    """
    Provide several mask families to increase diversity.
    All are small (4x4 to 6x6), with enough slots.
    """
    if template_name == "T4_seedlike":
        # 4x4 with a vertical column and bottom row, like the seed but not identical necessarily.
        # We'll randomize which column is the "spine" and length patterns.
        spine_col = rng.randrange(1, 3)  # 1 or 2
        mask = [["0","0","0","0"] for _ in range(4)]
        # last row 3 Xs
        for c in range(1, 4):
            mask[3][c] = "X"
        # spine down 4 Xs at spine_col
        for r in range(4):
            mask[r][spine_col] = "X"
        # top-right X to create another down slot sometimes
        mask[0][3] = "X"
        # ensure consistent: if spine_col==2, leave (0,1) as 0 etc
        return mask
    elif template_name == "Plus5":
        # 5x5 plus shape
        mask = [["0"]*5 for _ in range(5)]
        mid = 2
        for c in range(5):
            mask[mid][c] = "X"
        for r in range(5):
            mask[r][mid] = "X"
        # add two extra X to make more slots
        mask[1][1] = "X"
        mask[3][3] = "X"
        return mask
    elif template_name == "Stairs5":
        # 5x5 stair corridors creating multiple length-2/3 slots
        mask = [["0"]*5 for _ in range(5)]
        coords = [(0,4),(1,3),(2,2),(3,1),(4,0)]
        for r,c in coords:
            mask[r][c] = "X"
        # add adjacent to create runs
        for r,c in coords:
            if c-1 >= 0: mask[r][c-1] = "X"
            if r+1 < 5: mask[r+1][c] = "X"
        return mask
    else:
        # 6x6 ring with cross
        mask = [["0"]*6 for _ in range(6)]
        for i in range(6):
            mask[0][i] = "X"
            mask[5][i] = "X"
            mask[i][0] = "X"
            mask[i][5] = "X"
        for i in range(1,5):
            mask[3][i] = "X"
            mask[i][2] = "X"
        return mask

def extract_words_from_solution(mask: List[List[str]], filled: List[List[str]]) -> Tuple[List[str], List[str]]:
    across_slots, down_slots = find_slots(mask)
    across_words = []
    for _, _, cells in across_slots:
        across_words.append("".join(filled[r][c] for r,c in cells))
    down_words = []
    for _, _, cells in down_slots:
        down_words.append("".join(filled[r][c] for r,c in cells))
    return across_words, down_words

def make_random_filled_grid(mask: List[List[str]], rng: random.Random) -> List[List[str]]:
    R, C = len(mask), len(mask[0])
    filled = []
    for r in range(R):
        row = []
        for c in range(C):
            if mask[r][c] == "0":
                row.append(" ")
            else:
                row.append(rng_choice(rng, LETTERS))
        filled.append(row)
    return filled

def build_problem(output_language: str, mask: List[List[str]], across_words: List[str], down_words: List[str]) -> str:
    # In Chinese as requested; keep format instructions similar to seed but not identical.
    grid_txt = grid_to_strings(mask)
    return (
        "完成下面的填字游戏（crossword）。\n"
        f"横向单词（从左到右）：{','.join(across_words)}\n"
        f"纵向单词（从上到下）：{','.join(down_words)}\n"
        "网格（X=需要填字母的位置，0=空格位置）：\n"
        f"{grid_txt}\n\n"
        "规则：\n"
        "1) 只能在 X 处填写字母；0 处保持为空格。\n"
        "2) 横向单词按行从左到右读取；纵向单词按列从上到下读取。\n"
        "3) 单词交叉处字母必须一致。\n"
        "4) 请输出完成后的网格，格式为 [[row1, row2, ...]]，每格用字符串表示；0 位置用 \" \"。\n"
        "5) 例如：[[\"C\",\"A\",\"T\"],[\" \",\" \",\" \"],[\"D\",\"O\",\"G\"]]\n"
    )

def explanation_cn(mask: List[List[str]], solution_grid: List[List[str]], across_words: List[str], down_words: List[str]) -> str:
    # Provide verifiable evidence: list extracted across/down from the filled grid.
    aw2, dw2 = extract_words_from_solution(mask, solution_grid)
    return (
        "把解填入所有 X 后，可逐行/逐列读出：\n"
        f"- 横向得到：{','.join(aw2)}（应与题目给定的横向单词集合一致）\n"
        f"- 纵向得到：{','.join(dw2)}（应与题目给定的纵向单词集合一致）\n"
        "同时所有 0 位置均保持为空格 \" \"."
    )

def generate_one(rng: random.Random, output_language: str) -> Dict[str, Any]:
    templates = ["T4_seedlike", "Plus5", "Stairs5", "Ring6"]
    for _attempt in range(200):
        tname = rng_choice(rng, templates)
        mask = mask_from_template(tname, rng)
        across_slots, down_slots = find_slots(mask)
        # Require at least 1 across and 1 down, and manageable number of slots
        if len(across_slots) == 0 or len(down_slots) == 0:
            continue
        if len(across_slots) + len(down_slots) > 12:
            continue

        # Construct a filled grid, then derive words from it.
        # Then ensure the resulting puzzle has a unique solution when only those words are given.
        filled = make_random_filled_grid(mask, rng)
        across_words, down_words = extract_words_from_solution(mask, filled)

        # Add diversity: sometimes shuffle order of word lists in the statement.
        aw = list(across_words)
        dw = list(down_words)
        rng.shuffle(aw)
        rng.shuffle(dw)

        sols = solve_crossword(mask, aw, dw)
        if len(sols) != 1:
            continue

        sol_grid = sols[0]["grid"]

        # Cross-check: extracted words from solution grid should match given lists as multisets
        aw_check, dw_check = extract_words_from_solution(mask, sol_grid)
        if sorted(aw_check) != sorted(aw):
            continue
        if sorted(dw_check) != sorted(dw):
            continue

        problem = build_problem(output_language, mask, aw, dw)
        expl = explanation_cn(mask, sol_grid, aw, dw)
        return {"problem": problem, "answer": sol_grid, "explanation": expl}

    raise RuntimeError("在采样上限内未能生成可唯一求解的填字题实例。")

def main():
    data = json.load(sys.stdin)
    seed = int(data["seed"])
    count = int(data["count"])
    output_language = "zh"
    rng = random.Random(seed)

    results = []
    seen = set()
    # avoid duplicates by hashing problem text
    for i in range(count):
        for _ in range(300):
            item = generate_one(rng, output_language)
            h = item["problem"]
            if h in seen:
                continue
            seen.add(h)
            results.append(item)
            break
        else:
            raise RuntimeError("生成题目时重复过多或失败，无法满足数量要求。")

    json.dump(results, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise